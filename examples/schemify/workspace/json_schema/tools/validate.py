#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema>=4.18", "referencing>=0.35"]
# ///
"""Validate an interlinked JSON Schema data-dictionary package (draft 2020-12).

Prefer `uv run validate.py ...` (uv resolves dependencies). Fallback:
`python3 -m pip install --user "jsonschema>=4.18" referencing`, then
`python3 validate.py ...`. If neither is possible, validation is deferred -
record the debt in the session log; never mark a category validated without
a green run.

Subcommands (all print JSON to stdout; exit 0 only when ok is true):

  check PKG
      Every schema file parses and meta-validates; the $id policy is linted
      (one base, path-mirroring); every $ref in every file resolves; every
      mother conditional names only declared properties and trigger levels.
  data PKG --file F [--table T] [--format json|csv] [--max-errors N]
      Validate a data file against a table's mother schema. CSV columns are
      coerced to numbers only when the schema admits nothing but numbers, so
      string codes keep their leading zeros.
  fixtures PKG [--table T]
      The unit test: examples/toy_valid.json must yield zero findings; every
      examples/toy_invalid.json row must fail on exactly the column named in
      examples/toy_invalid_ledger.json.
  coverage PKG [--inventory PATH]
      Reconcile VARIABLES.csv against the schemas' properties.
  routing PKG [--table T] [--max-findings N]
      Reconcile ROUTING.csv (the routing register) against the mothers'
      conditionals: rule ids, statuses, variables, fixture coverage, and the
      NA-bearing properties no rule or register row accounts for. A missing
      register is reported as skipped, never as an error.
  summary PKG
      check + fixtures + coverage + routing in one rollup with a relay-ready
      headline.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin

SYNTHETIC_BASE = "https://schema.local/"
SKILL_DIR = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {"examples", "tools", "assets", ".git", "node_modules", "__pycache__"}
SCHEMA_HINT_KEYS = {"$schema", "$id", "$defs", "properties", "type", "allOf", "oneOf", "anyOf", "items"}
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"

# Routing register (ROUTING.csv) and the mother conditionals it reconciles with.
ROUTING_COLUMNS = ["id", "table", "trigger", "targets", "rule", "evidence",
                   "source", "decision", "status", "notes"]
ROUTING_STATUSES = ["waiting", "proposed", "confirmed", "encoded", "declined",
                    "not-enforceable"]
ROUTING_EVIDENCE = ["quoted", "implied", "steward", "inferred"]
RULE_ID_RE = re.compile(r"^R\d{3,}$")
DECISION_RE = re.compile(r"^D\d{3,}$")
VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")
# "Skip pattern R012: ...", "Applicability R012: ...", "Tobacco routing R012: ...";
# the id is optional so packages that predate the register still parse.
COMMENT_RE = re.compile(
    r"^(?P<prefix>Skip pattern|Applicability|(?P<domain>[A-Z][^:\n]{0,58}?) routing)"
    r"(?: (?P<id>R\d{3,}))?:\s+(?P<gist>\S.*)", re.S)
# notes column: "waits for: tobacco_history; parity" (the colon is what makes
# it a wait - "waits for the steward" is prose).
WAITS_RE = re.compile(
    r"waits for:\s*([A-Za-z_][A-Za-z0-9_.\-]*(?:\s*[;,]\s*[A-Za-z_][A-Za-z0-9_.\-]*)*)",
    re.I)
NA_TITLE_RE = re.compile(r"not[ -]applicable|\bn/?a\b|structural(ly)?\s+(skip|na)", re.I)
CONDITIONAL_KEYS = {"$comment", "if", "then"}
APPLICATORS_LIST = ("allOf", "anyOf", "oneOf")
APPLICATORS_DICT = ("not", "if", "then", "else")
ALLOF_IF_RE = re.compile(r"^/items/allOf/(\d+)/if$")
ALLOF_ENTRY_RE = re.compile(r"^/items/allOf/\d+(/|$)")
NA_LIST_CAP = 50
MANY_CONDITIONALS = 25  # past this, VALIDATE.md relaxes the per-rule fixture bar


def out(payload, code=0):
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(error, hint):
    out({"ok": False, "error": error, "hint": hint}, 1)


try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError:
    fail(
        "jsonschema and/or referencing are not installed.",
        'Run with `uv run validate.py ...` (preferred), or '
        '`python3 -m pip install --user "jsonschema>=4.18" referencing` and retry. '
        "From a package copy: `python3 -m pip install -r tools/requirements.txt`.",
    )


# ---------------------------------------------------------------- package load


def guard_package_path(pkg):
    pkg = pkg.resolve()
    if (SKILL_DIR / "SKILL.md").exists() and (pkg == SKILL_DIR or SKILL_DIR in pkg.parents):
        fail(
            "Refusing to operate inside the installed skill directory.",
            "Run against the schema package in the steward's repository "
            "(the directory holding the mother *.schema.json files).",
        )
    if not pkg.is_dir():
        fail(
            "Package directory not found: {}".format(pkg),
            "Pass the package root - the directory holding the table directories "
            "and common/defs.json (often json_schema/).",
        )
    return pkg


def load_json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f), None
    except json.JSONDecodeError as exc:
        return None, "line {} column {}: {}".format(exc.lineno, exc.colno, exc.msg)
    except OSError as exc:
        return None, str(exc)


def is_schema_doc(doc):
    return isinstance(doc, dict) and bool(SCHEMA_HINT_KEYS & set(doc))


class Package:
    """Every schema file in the package, cross-registered under every $id base."""

    def __init__(self, pkg):
        self.root = pkg
        self.docs = {}        # relpath (posix str) -> parsed doc
        self.parse_errors = []  # {file, error}
        self.non_schema = []
        for path in sorted(pkg.rglob("*.json")):
            rel = path.relative_to(pkg)
            if any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts):
                continue
            if rel.name == "manifest.json":
                continue
            doc, err = load_json(path)
            if err is not None:
                self.parse_errors.append({"file": str(rel), "error": err})
                continue
            if not is_schema_doc(doc):
                self.non_schema.append(str(rel))
                continue
            self.docs[str(PurePosixPath(rel))] = doc

        self.bases = self._discover_bases()
        self.uri_map = self._build_uri_map()
        self.registry = Registry().with_resources(
            (uri, Resource.from_contents(doc, default_specification=DRAFT202012))
            for uri, doc in self.uri_map.items()
        )

    def _discover_bases(self):
        bases = set()
        for rel, doc in self.docs.items():
            sid = doc.get("$id")
            if isinstance(sid, str) and sid.endswith(rel) and len(sid) > len(rel):
                bases.add(sid[: -len(rel)])
        bases.add(SYNTHETIC_BASE)
        return bases

    def _build_uri_map(self):
        uri_map = {}
        for rel, doc in self.docs.items():
            sid = doc.get("$id")
            if isinstance(sid, str) and sid:
                uri_map.setdefault(sid, doc)
            for base in self.bases:
                uri_map.setdefault(urljoin(base, rel), doc)
        return uri_map

    def mothers(self):
        return {
            PurePosixPath(rel).name[: -len(".schema.json")]: rel
            for rel in self.docs
            if rel.endswith(".schema.json")
        }

    def doc_uri(self, rel):
        return urljoin(SYNTHETIC_BASE, rel)

    def lookup(self, uri):
        """Resolve a URI with optional #/json/pointer fragment to a subschema."""
        base, _, frag = uri.partition("#")
        doc = self.uri_map.get(base)
        if doc is None:
            return None
        node = doc
        if frag and frag != "/":
            for token in frag.strip("/").split("/"):
                token = token.replace("~1", "/").replace("~0", "~")
                if isinstance(node, dict) and token in node:
                    node = node[token]
                elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
                    node = node[int(token)]
                else:
                    return None
        return node

    def deref(self, node, origin_rel, depth=0):
        """Follow $ref chains (bounded) from a node that lives in file origin_rel."""
        while isinstance(node, dict) and isinstance(node.get("$ref"), str) and depth < 8:
            base_doc = self.docs.get(origin_rel, {})
            sid = base_doc.get("$id")
            base_uri = sid if isinstance(sid, str) and sid else self.doc_uri(origin_rel)
            target_uri = urljoin(base_uri, node["$ref"])
            resolved = self.lookup(target_uri)
            if resolved is None:
                return node
            # Track which file the resolved node lives in, for chained relative refs.
            plain = target_uri.partition("#")[0]
            for rel in self.docs:
                if plain.endswith("/" + rel) or plain == urljoin(SYNTHETIC_BASE, rel):
                    origin_rel = rel
                    break
            merged = {k: v for k, v in node.items() if k != "$ref"}
            if merged and not isinstance(resolved, dict):
                return node  # siblings cannot merge into a non-object: leave it unresolved
            node = resolved if not merged else {**resolved, **merged}
            depth += 1
        return node


# ------------------------------------------------------------------- check


def run_check(pkg_obj):
    findings_fatal = False
    meta_failed = []
    for rel, doc in sorted(pkg_obj.docs.items()):
        try:
            Draft202012Validator.check_schema(doc)
        except SchemaError as exc:
            meta_failed.append({
                "file": rel,
                "error": exc.message,
                "hint": "Fix the keyword at schema path /{} - the file must be a valid "
                        "draft 2020-12 schema.".format("/".join(str(p) for p in exc.absolute_path)),
            })
    if meta_failed or pkg_obj.parse_errors:
        findings_fatal = True

    # $id policy lint
    problems = []
    seen_ids = {}
    real_bases = sorted(b for b in pkg_obj.bases if b != SYNTHETIC_BASE)
    base_counts = {}
    for rel, doc in pkg_obj.docs.items():
        sid = doc.get("$id")
        if isinstance(sid, str):
            for base in real_bases:
                if sid.startswith(base):
                    base_counts[base] = base_counts.get(base, 0) + 1
                    break
    dominant = max(base_counts, key=base_counts.get) if base_counts else None

    for rel, doc in sorted(pkg_obj.docs.items()):
        schema_field = doc.get("$schema")
        if schema_field != DRAFT_2020_12:
            problems.append({
                "file": rel, "kind": "wrong-draft", "severity": "error",
                "issue": "$schema is {!r}; the house draft is 2020-12.".format(schema_field),
                "hint": 'Set "$schema": "{}" in every file.'.format(DRAFT_2020_12),
            })
        sid = doc.get("$id")
        if not isinstance(sid, str) or not sid:
            problems.append({
                "file": rel, "kind": "missing-id", "severity": "warn",
                "issue": "No $id.",
                "hint": "Give every file an absolute $id: <package base> + its "
                        "package-relative path.",
            })
            continue
        if sid in seen_ids:
            problems.append({
                "file": rel, "kind": "duplicate-id", "severity": "error",
                "issue": "$id {} already used by {}.".format(sid, seen_ids[sid]),
                "hint": "Every file needs a unique $id mirroring its own path.",
            })
        seen_ids.setdefault(sid, rel)
        if not sid.endswith(rel):
            problems.append({
                "file": rel, "kind": "id-path-mismatch", "severity": "warn",
                "issue": "$id does not end with the file's package-relative path ({}).".format(rel),
                "hint": "Set $id to <package base>{} so relative $refs resolve the same "
                        "by path and by $id.".format(rel),
            })
        elif dominant and not sid.startswith(dominant):
            problems.append({
                "file": rel, "kind": "mixed-id-bases", "severity": "warn",
                "issue": "$id base differs from the package's dominant base {} "
                         "({} files).".format(dominant, base_counts.get(dominant, 0)),
                "hint": "Pick ONE non-dereferenceable base per package. Validation "
                        "still works here (files are cross-registered under every "
                        "base), but strict $id resolvers and browser pages break.",
            })
    if any(p["severity"] == "error" for p in problems):
        findings_fatal = True

    # $ref resolution
    checked = 0
    unresolved = []

    def walk_refs(node, rel, base_uri):
        nonlocal checked
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                checked += 1
                target = urljoin(base_uri, ref)
                if pkg_obj.lookup(target) is None:
                    unresolved.append({
                        "file": rel, "ref": ref, "resolved_to": target,
                        "hint": "No file answers to that URI. Is the target file "
                                "missing, is the pointer fragment wrong, or does the "
                                "target's $id not mirror its on-disk path?",
                    })
            for v in node.values():
                walk_refs(v, rel, base_uri)
        elif isinstance(node, list):
            for v in node:
                walk_refs(v, rel, base_uri)

    for rel, doc in sorted(pkg_obj.docs.items()):
        base_uri = doc.get("$id") if isinstance(doc.get("$id"), str) else pkg_obj.doc_uri(rel)
        walk_refs(doc, rel, base_uri)
    if unresolved:
        findings_fatal = True

    # conditionals: declared variables and trigger levels only, house shape
    broken = ({m["file"] for m in meta_failed}
              | {p["file"] for p in pkg_obj.parse_errors})
    conditionals = lint_conditionals(pkg_obj, broken)
    if not conditionals["ok"]:
        findings_fatal = True

    mothers = pkg_obj.mothers()
    if not mothers:
        findings_fatal = True

    return {
        "ok": not findings_fatal,
        "files": len(pkg_obj.docs),
        "tables": sorted(mothers),
        "parse_errors": pkg_obj.parse_errors,
        "meta": {"passed": len(pkg_obj.docs) - len(meta_failed), "failed": meta_failed},
        "ids": {"bases": real_bases, "problems": problems},
        "refs": {"checked": checked, "unresolved": unresolved},
        "conditionals": conditionals,
        **({} if mothers else {
            "error": "No mother file (*.schema.json) found in the package.",
            "hint": "Each table needs <table>/<table>.schema.json - the array-of-objects "
                    "mother schema. See LAYOUT.md.",
        }),
    }


# ------------------------------------------------------- data + fixtures core


def pick_table(pkg_obj, table):
    mothers = pkg_obj.mothers()
    if not mothers:
        fail("No mother file (*.schema.json) found in the package.",
             "Each table needs <table>/<table>.schema.json. See LAYOUT.md.")
    if table is None:
        if len(mothers) == 1:
            table = next(iter(mothers))
        else:
            fail("The package has several tables: {}.".format(", ".join(sorted(mothers))),
                 "Pass --table <name> to say which one this data belongs to.")
    if table not in mothers:
        fail("No table named {!r} (found: {}).".format(table, ", ".join(sorted(mothers))),
             "Table names are the *.schema.json stems.")
    return table, mothers[table]


def conditional_index(pkg_obj, mother_rel):
    """Map id() of every node inside each mother conditional to
    (index, $comment, rule id or None)."""
    doc = pkg_obj.docs[mother_rel]
    entries = allof_entries(doc)
    index = {}

    def collect(node, key):
        index[id(node)] = key
        if isinstance(node, dict):
            for v in node.values():
                collect(v, key)
        elif isinstance(node, list):
            for v in node:
                collect(v, key)

    conditionals = []
    for i, entry in enumerate(entries):
        if isinstance(entry, dict) and "if" in entry:
            comment = entry.get("$comment", "")
            parsed = parse_comment(comment)
            rule_id = parsed["id"] if parsed else None
            conditionals.append({"index": i, "comment": comment, "rule_id": rule_id})
            collect(entry, (i, comment, rule_id))
    return index, conditionals


def summarize_field(pkg_obj, field_schema, origin_rel):
    """One line of what a field admits: bounds and declared codes."""
    numeric, codes = [], []

    def scan(node, depth=0):
        if not isinstance(node, dict) or depth > 6:
            return
        node = pkg_obj.deref(node, origin_rel)
        if not isinstance(node, dict):
            return
        if "const" in node:
            codes.append(node["const"])
        for v in node.get("enum", []) if isinstance(node.get("enum"), list) else []:
            codes.append(v)
        if node.get("type") in ("integer", "number"):
            lo, hi = node.get("minimum"), node.get("maximum")
            if lo is not None or hi is not None:
                numeric.append("{}-{}".format("?" if lo is None else lo, "?" if hi is None else hi))
        if node.get("type") == "string" and "pattern" in node:
            numeric.append("string matching {}".format(node["pattern"]))
        for key in ("oneOf", "anyOf", "allOf"):
            for branch in node.get(key, []) if isinstance(node.get(key), list) else []:
                scan(branch, depth + 1)

    scan(field_schema)
    parts = []
    if numeric:
        parts.append(" or ".join(numeric[:3]))
    if codes:
        shown = ", ".join(repr(c) for c in codes[:8])
        parts.append("declared codes: {}{}".format(shown, ", ..." if len(codes) > 8 else ""))
    return "; ".join(parts)


REQUIRED_RE = re.compile(r"'([^']+)' is a required property")
QUOTED_RE = re.compile(r"'([^']*)'")


def flatten_findings(pkg_obj, table, mother_rel, errors, empties=None):
    """Turn jsonschema errors into per-cell findings the agent can relay."""
    cond_ids, _ = conditional_index(pkg_obj, mother_rel)
    declared = set(row_property_schemas(pkg_obj, mother_rel))
    empties = empties or set()
    findings = []
    for err in errors:
        path = list(err.absolute_path)
        row = path[0] if path and isinstance(path[0], int) else None
        cols = []
        if len(path) >= 2 and isinstance(path[1], str):
            cols = [path[1]]
        elif err.validator == "required":
            cols = REQUIRED_RE.findall(err.message) or [None]
        elif err.validator in ("unevaluatedProperties", "additionalProperties"):
            # 2020-12 collateral: when a category subschema fails, every column it
            # declares stops counting as "evaluated". Only genuinely undeclared
            # columns are real findings here.
            cols = [c for c in QUOTED_RE.findall(err.message) if c not in declared]
            if not cols:
                continue
        else:
            cols = [None]

        rule, rule_id, allof_index = None, None, None
        parent = getattr(err, "parent", None)
        for candidate in (err.schema, parent.schema if parent is not None else None):
            if candidate is not None and id(candidate) in cond_ids:
                allof_index, rule, rule_id = cond_ids[id(candidate)]
                break

        for col in cols:
            hint = None
            if err.validator == "required":
                hint = ("Every column is present in every row - missingness is an "
                        "in-band sentinel code, never an absent key.")
            elif err.validator in ("unevaluatedProperties", "additionalProperties"):
                hint = ("The column is not declared in any category file. Add it to the "
                        "schemas (and VARIABLES.csv) or remove it from the data.")
            elif err.validator in ("anyOf", "oneOf") and col is not None:
                gist = summarize_field(pkg_obj, err.schema, mother_rel)
                hint = "Value must match one of the declared forms{}.".format(
                    " - " + gist if gist else "")
            if row is not None and col is not None and (row, col) in empties:
                hint = ("Empty cell - every column is required and missingness is "
                        "in-band; use the field's sentinel code.")
            findings.append({
                "row": row,
                "column": col,
                "pointer": "/" + "/".join(str(p) for p in path),
                "keyword": err.validator,
                "message": err.message[:400],
                **({"rule": rule} if rule else {}),
                **({"rule_id": rule_id} if rule_id else {}),
                **({"allof_index": allof_index} if allof_index is not None else {}),
                **({"hint": hint} if hint else {}),
                **({"empty_cell": True} if row is not None and col is not None
                   and (row, col) in empties else {}),
            })
    # Prefer routing-attributed findings when several land on one cell.
    findings.sort(key=lambda f: (f["row"] is None, f["row"], f["column"] is None,
                                 f["column"] or "", 0 if f.get("rule") else 1))
    return findings


def validate_rows(pkg_obj, mother_rel, rows):
    root_uri = pkg_obj.doc_uri(mother_rel)
    validator = Draft202012Validator(
        {"$ref": root_uri},
        registry=pkg_obj.registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    return sorted(validator.iter_errors(rows), key=lambda e: list(map(str, e.absolute_path)))


def allof_entries(doc):
    """items.allOf of a mother document as a list - [] for any other shape."""
    items = doc.get("items") if isinstance(doc, dict) else None
    entries = items.get("allOf") if isinstance(items, dict) else None
    return entries if isinstance(entries, list) else []


def row_property_schemas(pkg_obj, mother_rel):
    """properties of the row object: union of every category's properties."""
    doc = pkg_obj.docs[mother_rel]
    props = {}
    for entry in allof_entries(doc):
        if isinstance(entry, dict) and "$ref" in entry and "if" not in entry:
            resolved = pkg_obj.deref(entry, mother_rel)
            if isinstance(resolved, dict) and isinstance(resolved.get("properties"), dict):
                for name, sub in resolved["properties"].items():
                    props[name] = (sub, mother_rel)
    return props


# -------------------------------------------------------------- conditionals


def finding(severity, code, message, hint, **where):
    """One lint or reconciliation finding. Known location keys come first, in a
    fixed order; None values are dropped; any other keyword rides along."""
    item = {"severity": severity, "code": code, "message": message, "hint": hint}
    for key in ("file", "pointer", "line", "table", "rule", "rule_id",
                "allof_index", "variable"):
        if where.get(key) is not None:
            item[key] = where[key]
    for key, val in where.items():
        if key not in item and val is not None:
            item[key] = val
    return item


def parse_comment(comment):
    """Split a conditional's $comment into prefix, kind, register id, and gist.
    None when the comment carries no controlled prefix; id None when the
    prefix carries no R-number (a package that predates the register)."""
    if not isinstance(comment, str):
        return None
    m = COMMENT_RE.match(comment.strip())
    if not m:
        return None
    prefix = m.group("prefix")
    kind = ("skip" if prefix == "Skip pattern"
            else "applicability" if prefix == "Applicability" else "routing")
    return {"prefix": prefix, "kind": kind, "domain": m.group("domain"),
            "id": m.group("id"), "gist": m.group("gist").strip()}


def resolve_ref(pkg_obj, origin_rel, ref):
    """(package-relative file, JSON-pointer fragment) a $ref written in
    origin_rel points at; the file is None when no package doc answers."""
    if not isinstance(ref, str):
        return None, ""
    base_doc = pkg_obj.docs.get(origin_rel, {})
    sid = base_doc.get("$id")
    base_uri = sid if isinstance(sid, str) and sid else pkg_obj.doc_uri(origin_rel)
    plain, _, frag = urljoin(base_uri, ref).partition("#")
    best = None
    for rel in pkg_obj.docs:
        if plain.endswith("/" + rel) or plain == urljoin(SYNTHETIC_BASE, rel):
            if best is None or len(rel) > len(best):
                best = rel
    return best, frag


def _enter(pkg_obj, node, origin_rel):
    """Deref a node for walking; (None, origin) when a $ref does not resolve."""
    if not isinstance(node, dict):
        return None, origin_rel
    if "$ref" not in node:
        return node, origin_rel
    if not isinstance(node["$ref"], str):
        return None, origin_rel
    ref_rel, _ = resolve_ref(pkg_obj, origin_rel, node["$ref"])
    resolved = pkg_obj.deref(node, origin_rel)
    if not isinstance(resolved, dict) or "$ref" in resolved:
        return None, origin_rel
    return resolved, ref_rel or origin_rel


def referenced_names(pkg_obj, node, origin_rel, acc, depth=0):
    """Property names a subschema constrains: keys of properties, entries of
    required, keys of dependentRequired/dependentSchemas - recursing through
    allOf/anyOf/oneOf/not/if/then/else and $ref, never into a property's own
    schema (a target's `not: {const}` names nothing)."""
    if depth > 8:
        return acc
    node, origin_rel = _enter(pkg_obj, node, origin_rel)
    if node is None:
        return acc
    props = node.get("properties")
    if isinstance(props, dict):
        acc.update(str(k) for k in props)
    req = node.get("required")
    if isinstance(req, list):
        acc.update(r for r in req if isinstance(r, str))
    for key in ("dependentRequired", "dependentSchemas"):
        if isinstance(node.get(key), dict):
            acc.update(str(k) for k in node[key])
    for key in APPLICATORS_LIST:
        if isinstance(node.get(key), list):
            for sub in node[key]:
                referenced_names(pkg_obj, sub, origin_rel, acc, depth + 1)
    for key in APPLICATORS_DICT:
        if isinstance(node.get(key), dict):
            referenced_names(pkg_obj, node[key], origin_rel, acc, depth + 1)
    return acc


def trigger_values(pkg_obj, node, origin_rel, acc, depth=0):
    """(name, value) pairs an `if` pins: const/enum on properties.<name>,
    also under its `not` (the complement trigger), through the applicators."""
    if depth > 8:
        return acc
    node, origin_rel = _enter(pkg_obj, node, origin_rel)
    if node is None:
        return acc
    props = node.get("properties")
    if isinstance(props, dict):
        for name, sub in props.items():
            leaves = [sub, sub.get("not") if isinstance(sub, dict) else None]
            for leaf in leaves:
                if not isinstance(leaf, dict):
                    continue
                if "const" in leaf:
                    acc.append((str(name), leaf["const"]))
                if isinstance(leaf.get("enum"), list):
                    acc.extend((str(name), v) for v in leaf["enum"])
    for key in APPLICATORS_LIST:
        if isinstance(node.get(key), list):
            for sub in node[key]:
                trigger_values(pkg_obj, sub, origin_rel, acc, depth + 1)
    for key in APPLICATORS_DICT:
        if isinstance(node.get(key), dict):
            trigger_values(pkg_obj, node[key], origin_rel, acc, depth + 1)
    return acc


def unguarded_triggers(node, acc, depth=0):
    """Names an `if` tests in properties without listing in required at the
    same level - such a trigger is satisfied vacuously by a row lacking it."""
    if not isinstance(node, dict) or depth > 8:
        return acc
    props = node.get("properties")
    if isinstance(props, dict):
        req = node.get("required") if isinstance(node.get("required"), list) else []
        acc.update(str(k) for k in props if k not in req)
    for key in APPLICATORS_LIST:
        if isinstance(node.get(key), list):
            for sub in node[key]:
                unguarded_triggers(sub, acc, depth + 1)
    for key in APPLICATORS_DICT:
        if isinstance(node.get(key), dict):
            unguarded_triggers(node[key], acc, depth + 1)
    return acc


def literal_key(value):
    """Hashable identity of a JSON literal: 1 and 1.0 agree, True and 1 do not."""
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("num", float(value))
    if isinstance(value, (str, type(None))):
        return (type(value).__name__, value)
    return ("json", json.dumps(value, sort_keys=True))


def json_kind(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return "array" if isinstance(value, list) else "object"


def declared_levels(pkg_obj, prop_schema, origin_rel):
    """What a property admits: its declared consts (every oneOf/anyOf branch,
    deref'd) and its open typed branches (a bounded integer, a string pattern)."""
    consts, open_branches = [], []

    def scan(node, depth=0):
        if not isinstance(node, dict) or depth > 6:
            return
        node = pkg_obj.deref(node, origin_rel)
        if not isinstance(node, dict):
            return
        branched = any(isinstance(node.get(k), list) for k in APPLICATORS_LIST)
        if "const" in node:
            consts.append(node["const"])
        elif isinstance(node.get("enum"), list):
            consts.extend(node["enum"])
        elif not branched and (node.get("type") is not None or "pattern" in node):
            t = node.get("type")
            types = [x for x in (t if isinstance(t, list) else [t]) if isinstance(x, str)]
            if not types and "pattern" in node:
                types = ["string"]
            open_branches.append({"types": types, "minimum": node.get("minimum"),
                                  "maximum": node.get("maximum")})
        for key in APPLICATORS_LIST:
            if isinstance(node.get(key), list):
                for branch in node[key]:
                    scan(branch, depth + 1)

    scan(prop_schema)
    return consts, open_branches


def level_declared(value, consts, open_branches):
    key = literal_key(value)
    if any(literal_key(c) == key for c in consts):
        return True
    kind = json_kind(value)
    for branch in open_branches:
        types = set(branch["types"])
        if kind in types or (kind == "integer" and "number" in types):
            if kind in ("integer", "number"):
                lo, hi = branch.get("minimum"), branch.get("maximum")
                lo = lo if isinstance(lo, (int, float)) and not isinstance(lo, bool) else None
                hi = hi if isinstance(hi, (int, float)) and not isinstance(hi, bool) else None
                if (lo is not None and value < lo) or (hi is not None and value > hi):
                    continue
            return True
    return False


def table_properties(pkg_obj, mother_rel):
    """Every row property as (schema, file it lives in, category) - the file
    is the category's, so the property's own $refs deref - plus the category
    $refs that did not resolve (the dangling check stands down for those)."""
    doc = pkg_obj.docs[mother_rel]
    props, unresolved = {}, []
    for entry in allof_entries(doc):
        if isinstance(entry, dict) and "$ref" in entry and "if" not in entry:
            ref = entry["$ref"]
            ref_rel, _ = resolve_ref(pkg_obj, mother_rel, ref)
            resolved = pkg_obj.deref(entry, mother_rel)
            if not isinstance(resolved, dict) or "$ref" in resolved:
                unresolved.append(ref if isinstance(ref, str) else repr(ref))
                continue
            category = PurePosixPath(ref.partition("#")[0]).stem or "?"
            if isinstance(resolved.get("properties"), dict):
                for name, sub in resolved["properties"].items():
                    props[name] = (sub, ref_rel or mother_rel, category)
    return props, unresolved


def table_files(pkg_obj, mother_rel):
    """The mother and every category file it $refs."""
    rels = {mother_rel}
    for entry in allof_entries(pkg_obj.docs.get(mother_rel)):
        if isinstance(entry, dict) and "$ref" in entry and "if" not in entry:
            rel, _ = resolve_ref(pkg_obj, mother_rel, entry["$ref"])
            if rel:
                rels.add(rel)
    return rels


def broken_files(pkg_obj, check=None):
    """Files that failed to parse or meta-validate: read off an earlier check
    report when the caller has one, else by running the meta check here."""
    if check is not None:
        return ({m["file"] for m in check.get("meta", {}).get("failed", [])}
                | {p["file"] for p in check.get("parse_errors", [])})
    broken = {p["file"] for p in pkg_obj.parse_errors}
    for rel, doc in pkg_obj.docs.items():
        try:
            Draft202012Validator.check_schema(doc)
        except SchemaError:
            broken.add(rel)
    return broken


def mother_conditionals(pkg_obj, mother_rel):
    """One record per items.allOf entry that is a conditional - written inline
    or hidden behind a $ref - and the indexes of entries that are neither a
    category $ref nor a conditional."""
    doc = pkg_obj.docs[mother_rel]
    records, unexpected = [], []
    for i, entry in enumerate(allof_entries(doc)):
        hidden, node, origin, ref_target = False, entry, mother_rel, None
        if isinstance(entry, dict) and "if" in entry:
            pass
        elif isinstance(entry, dict) and "$ref" in entry:
            resolved = pkg_obj.deref(entry, mother_rel)
            if not (isinstance(resolved, dict) and "if" in resolved
                    and "properties" not in resolved):
                # A category (a stray `if` in one is conditional-outside-mother's
                # business) or an unresolved ref (table_properties reports it).
                continue
            ref_target = resolve_ref(pkg_obj, mother_rel, entry["$ref"])
            hidden, node, origin = True, resolved, ref_target[0] or mother_rel
        else:
            unexpected.append(i)
            continue
        comment = node.get("$comment")
        parsed = parse_comment(comment)
        targets = referenced_names(pkg_obj, node.get("then"), origin, set())
        referenced_names(pkg_obj, node.get("else"), origin, targets)
        records.append({
            "index": i,
            "pointer": "/items/allOf/{}".format(i),
            "comment": comment if isinstance(comment, str) else None,
            "parsed": parsed,
            "rule_id": parsed["id"] if parsed else None,
            "kind": parsed["kind"] if parsed else None,
            "node": node,
            "origin": origin,
            "hidden": hidden,
            "ref": entry.get("$ref") if hidden else None,
            "ref_target": ref_target,
            "triggers": referenced_names(pkg_obj, node.get("if"), origin, set()),
            "targets": targets,
        })
    return records, unexpected


def find_conditionals_in(doc):
    """JSON pointers of every `if` keyword in a document (keys that are
    property or definition names are never keywords)."""
    found = []
    named = ("properties", "$defs", "definitions", "patternProperties", "dependentSchemas")

    def esc(token):
        return str(token).replace("~", "~0").replace("/", "~1")

    def walk(node, pointer):
        if isinstance(node, dict):
            for key, val in node.items():
                here = pointer + "/" + esc(key)
                if key == "if" and isinstance(val, (dict, bool)):
                    found.append(here)
                if key in named and isinstance(val, dict):
                    for name, sub in val.items():
                        walk(sub, here + "/" + esc(name))
                else:
                    walk(val, here)
        elif isinstance(node, list):
            for i, val in enumerate(node):
                walk(val, pointer + "/" + str(i))

    walk(doc, "")
    return found


def lint_conditionals(pkg_obj, broken=None):
    """Every mother conditional names declared properties and trigger levels,
    has the house shape and a prefixed $comment, and sits where the fixtures
    and pages can address it. Only a dangling variable is an error. `broken`
    is the set of files that failed to parse or meta-validate: a table that
    touches one stands down (check.meta already says what is wrong)."""
    mothers = pkg_obj.mothers()
    mother_rels = set(mothers.values())
    broken = set(broken or ())
    findings, tables, hidden_targets = [], {}, set()
    cmt_hint = ("Every conditional carries a $comment beginning 'Skip pattern R###: ', "
                "'Applicability R###: ', or '<Domain> routing R###: ' - the validator "
                "and the pages show it whenever the rule fires (SKIP-PATTERNS.md).")
    for table, mother_rel in sorted(mothers.items()):
        bad = sorted(table_files(pkg_obj, mother_rel) & broken)
        if bad:
            entry = {"count": 0, "with_id": 0,
                     "skipped": "meta-validation failed - fix check.meta first ({})."
                                .format(", ".join(bad))}
            if mother_rel not in broken:
                records, _ = mother_conditionals(pkg_obj, mother_rel)
                entry["count"] = len(records)
                entry["with_id"] = sum(1 for r in records if r["rule_id"])
            tables[table] = entry
            continue
        props, unresolved = table_properties(pkg_obj, mother_rel)
        records, unexpected = mother_conditionals(pkg_obj, mother_rel)
        entry = {"count": len(records),
                 "with_id": sum(1 for r in records if r["rule_id"])}
        if unresolved:
            entry["skipped"] = ("dangling-variable check stood down: category $ref(s) "
                                "{} did not resolve - fix them first (check.refs)."
                                .format(", ".join(repr(u) for u in unresolved)))
        tables[table] = entry
        where = {"table": table, "file": mother_rel}
        for i in unexpected:
            findings.append(finding(
                "warn", "unexpected-allof-entry",
                "items.allOf[{}] is neither a category $ref nor a conditional.".format(i),
                "Each allOf entry is a category $ref or a {$comment, if, then} "
                "conditional - fold anything else into a category file.",
                pointer="/items/allOf/{}".format(i), allof_index=i, **where))
        by_id = {}
        for rec in records:
            i = rec["index"]
            w = dict(where, pointer=rec["pointer"], allof_index=i, rule=rec["comment"])
            if rec["hidden"]:
                if rec["ref_target"] and rec["ref_target"][0]:
                    hidden_targets.add((rec["ref_target"][0], rec["ref_target"][1] or ""))
                findings.append(finding(
                    "warn", "hidden-conditional",
                    "Conditional {} is reached through $ref {!r} rather than written "
                    "inline.".format(i, rec["ref"]),
                    "Inline it in items.allOf: fixtures, pages, and the routing check "
                    "address a rule by its allOf position, and a $ref'd rule reads as "
                    "a category.", **w))
            if not rec["comment"] or not rec["comment"].strip():
                findings.append(finding(
                    "warn", "missing-comment",
                    "Conditional {} has no $comment.".format(i), cmt_hint, **w))
            elif rec["parsed"] is None:
                findings.append(finding(
                    "warn", "comment-prefix",
                    "Conditional {}'s $comment does not start with a controlled prefix: "
                    "{!r}.".format(i, rec["comment"][:60]), cmt_hint, **w))
            node = rec["node"]
            keys = {k for k in node if k != "$ref"}
            extra = sorted(keys - CONDITIONAL_KEYS)
            if extra or "then" not in node:
                findings.append(finding(
                    "warn", "conditional-shape",
                    "Conditional {} has keys {}; the house shape is $comment, if, then."
                    .format(i, ", ".join(sorted(keys))),
                    "Keep the three keys: the reverse direction is its own conditional, "
                    "never an else, and a then is what makes it a rule (SKIP-PATTERNS.md).",
                    **w))
            unguarded = sorted(unguarded_triggers(node.get("if"), set()))
            if unguarded:
                findings.append(finding(
                    "warn", "conditional-shape",
                    "Conditional {} tests {} in if.properties without listing {} in "
                    "if.required.".format(i, ", ".join(unguarded),
                                          "it" if len(unguarded) == 1 else "them"),
                    "Add the trigger to if.required - without it a row lacking the "
                    "trigger column satisfies the if vacuously and the then fires on "
                    "everyone.", pointer=rec["pointer"] + "/if",
                    **{k: v for k, v in w.items() if k != "pointer"}))
            if not unresolved:
                for side, names in (("if", rec["triggers"]), ("then", rec["targets"])):
                    for name in sorted(names):
                        if name in props:
                            continue
                        findings.append(finding(
                            "error", "dangling-variable",
                            "Conditional {} names {!r}, which no category of {} declares."
                            .format(i, name, table),
                            "Add the property to its category file (and VARIABLES.csv) "
                            "or fix the name. Until then the rule never fires; if it did, "
                            "then.properties would let an undeclared column past "
                            "unevaluatedProperties: false.",
                            pointer=rec["pointer"] + "/" + side, variable=name,
                            **{k: v for k, v in w.items() if k != "pointer"}))
            seen_levels = set()
            for name, value in trigger_values(pkg_obj, node.get("if"), rec["origin"], []):
                if name not in props or (name, literal_key(value)) in seen_levels:
                    continue
                seen_levels.add((name, literal_key(value)))
                sub, origin, _ = props[name]
                consts, open_b = declared_levels(pkg_obj, sub, origin)
                if (consts or open_b) and not level_declared(value, consts, open_b):
                    shown = ", ".join(repr(c) for c in consts[:8])
                    findings.append(finding(
                        "warn", "trigger-undeclared-level",
                        "Conditional {} triggers on {} = {!r}, which is not a declared "
                        "level of {} ({}{}).".format(
                            i, name, value, name, shown or "no declared codes",
                            ", ..." if len(consts) > 8 else ""),
                        "Recode the trigger to a declared const, or declare the level "
                        "in the category file - a trigger on an undeclared level never "
                        "fires (revision drift, most often).",
                        pointer=rec["pointer"] + "/if", variable=name, value=value,
                        **{k: v for k, v in w.items() if k != "pointer"}))
            if rec["kind"] == "applicability":
                then = node.get("then") if isinstance(node.get("then"), dict) else {}
                then_props = then.get("properties") if isinstance(then.get("properties"), dict) else {}
                pinned = sorted(
                    str(n) for n, s in then_props.items()
                    if isinstance(s, dict) and ("const" in s or isinstance(s.get("enum"), list)))
                if pinned:
                    findings.append(finding(
                        "warn", "applicability-substantive",
                        "Conditional {} (Applicability) pins {} to a value; an "
                        "applicability half only forbids the NA code.".format(
                            i, ", ".join(pinned)),
                        "Use not: {const: NA} here; a pinned substantive value is a "
                        "'Skip pattern' or a '<Domain> routing' pin (SKIP-PATTERNS.md "
                        "'Substantive pins').", pointer=rec["pointer"] + "/then",
                        **{k: v for k, v in w.items() if k != "pointer"}))
            if rec["rule_id"]:
                by_id.setdefault(rec["rule_id"], []).append(rec)
        for rid, recs in sorted(by_id.items()):
            kinds = {r["kind"] for r in recs}
            if "routing" in kinds or kinds == {"skip", "applicability"}:
                continue
            have = "Skip pattern" if "skip" in kinds else "Applicability"
            missing = "Applicability" if "skip" in kinds else "Skip pattern"
            findings.append(finding(
                "warn", "missing-twin",
                "{} has a '{}' half but no '{}' half in {}.".format(rid, have, missing, table),
                "Write the twin (SKIP-PATTERNS.md 'Write skips in pairs') so the rule "
                "holds both ways, or use a '<Domain> routing' prefix for a deliberately "
                "one-directional pin.",
                pointer=recs[0]["pointer"], allof_index=recs[0]["index"],
                rule=recs[0]["comment"], rule_id=rid, **where))

    for rel, doc in sorted(pkg_obj.docs.items()):
        if rel in broken:
            continue
        is_mother = rel in mother_rels
        table = next((t for t, m in mothers.items()
                      if rel == m or PurePosixPath(m).parent in PurePosixPath(rel).parents),
                     None)
        for pointer in find_conditionals_in(doc):
            if is_mother and ALLOF_ENTRY_RE.match(pointer):
                continue
            if (rel, pointer[: -len("/if")]) in hidden_targets:
                continue
            findings.append(finding(
                "warn", "conditional-outside-mother",
                "{} carries a conditional at {}; conditionals live only in the "
                "mother's items.allOf.".format(rel, pointer),
                "Move it to <table>/<table>.schema.json under items.allOf with its "
                "$comment - a rule outside the mother has no allOf address for "
                "findings to attribute to, and the pages never show it.",
                file=rel, pointer=pointer, table=table))

    counts = {s: sum(1 for f in findings if f["severity"] == s)
              for s in ("error", "warn", "info")}
    return {
        "ok": counts["error"] == 0,
        "count": sum(t["count"] for t in tables.values()),
        "with_id": sum(t["with_id"] for t in tables.values()),
        "tables": tables,
        "findings": findings,
        "counts": counts,
    }


# ---------------------------------------------------------------------- data


def numeric_only(pkg_obj, field_schema, origin_rel):
    kinds = set()

    def scan(node, depth=0):
        if not isinstance(node, dict) or depth > 6:
            return
        node = pkg_obj.deref(node, origin_rel)
        if not isinstance(node, dict):
            return
        t = node.get("type")
        for tt in ([t] if isinstance(t, str) else t or []):
            kinds.add("num" if tt in ("integer", "number") else tt)
        if "const" in node:
            kinds.add("num" if isinstance(node["const"], (int, float))
                      and not isinstance(node["const"], bool) else "other")
        for v in node.get("enum", []) if isinstance(node.get("enum"), list) else []:
            kinds.add("num" if isinstance(v, (int, float)) and not isinstance(v, bool)
                      else "other")
        for key in ("oneOf", "anyOf", "allOf"):
            for branch in node.get(key, []) if isinstance(node.get(key), list) else []:
                scan(branch, depth + 1)

    scan(field_schema)
    return kinds == {"num"}, kinds


def read_csv_rows(pkg_obj, mother_rel, path):
    props = row_property_schemas(pkg_obj, mother_rel)
    coerce, mixed = {}, []
    for name, (sub, origin) in props.items():
        only_num, kinds = numeric_only(pkg_obj, sub, origin)
        coerce[name] = only_num
        if "num" in kinds and kinds != {"num"}:
            mixed.append({
                "column": name,
                "hint": "The schema admits both numbers and strings here; CSV cannot "
                        "carry that distinction. Validate a JSON export for this "
                        "column, or use the playground page.",
            })
    rows, empties = [], set()
    with open(path, encoding="utf-8-sig", newline="") as f:
        sample = f.readline()
        f.seek(0)
        if sample.count(";") > sample.count(","):
            fail("The file looks semicolon-separated.",
                 "Re-export as comma-separated CSV, or convert to a JSON array of "
                 "objects and pass --format json.")
        for i, raw in enumerate(csv.DictReader(f)):
            row = {}
            for key, val in raw.items():
                if key is None or val is None:
                    continue  # ragged extras / short rows: let `required` fire
                if val == "":
                    row[key] = ""
                    empties.add((i, key))
                elif coerce.get(key):
                    try:
                        row[key] = int(val)
                    except ValueError:
                        try:
                            row[key] = float(val)
                        except ValueError:
                            row[key] = val
                else:
                    row[key] = val
            rows.append(row)
    return rows, empties, mixed


def run_data(pkg_obj, args):
    table, mother_rel = pick_table(pkg_obj, args.table)
    path = Path(args.file)
    if not path.is_file():
        fail("Data file not found: {}".format(path),
             "Pass the path to a JSON array of objects or a CSV export.")
    fmt = args.format or ("csv" if path.suffix.lower() in (".csv", ".tsv") else "json")
    empties, mixed = set(), []
    if fmt == "csv":
        rows, empties, mixed = read_csv_rows(pkg_obj, mother_rel, path)
    else:
        rows, err = load_json(path)
        if err is not None:
            fail("Could not parse {} as JSON: {}".format(path.name, err),
                 "The file must be a JSON array of row objects.")
        if not isinstance(rows, list):
            fail("{} is not a JSON array.".format(path.name),
                 "The table's data contract is an array of row objects - one object "
                 "per row.")
    errors = validate_rows(pkg_obj, mother_rel, rows)
    findings = flatten_findings(pkg_obj, table, mother_rel, errors, empties)
    truncated = len(findings) > args.max_errors
    return {
        "ok": not findings,
        "table": table,
        "file": str(path),
        "format": fmt,
        "rows": len(rows),
        "errors": len(findings),
        "truncated": truncated,
        **({"mixed_columns": mixed} if mixed else {}),
        "findings": findings[: args.max_errors],
    }


# ------------------------------------------------------------------ fixtures


def fixture_paths(pkg_obj, table, multi):
    base = pkg_obj.root / "examples" / (table if multi else "")
    return (base / "toy_valid.json", base / "toy_invalid.json",
            base / "toy_invalid_ledger.json")


def run_fixtures(pkg_obj, args):
    mothers = pkg_obj.mothers()
    if not mothers:
        fail("No mother file (*.schema.json) found in the package.",
             "Each table needs <table>/<table>.schema.json. See LAYOUT.md.")
    multi = len(mothers) > 1
    tables = [args.table] if args.table else sorted(mothers)
    report, all_ok, any_found = {}, True, False
    for table in tables:
        if table not in mothers:
            fail("No table named {!r} (found: {}).".format(table, ", ".join(sorted(mothers))),
                 "Table names are the *.schema.json stems.")
        valid_p, invalid_p, ledger_p = fixture_paths(pkg_obj, table, multi)
        entry = {}
        if not valid_p.is_file():
            entry["skipped"] = ("No {} yet - author the toy fixtures per VALIDATE.md."
                                .format(valid_p.relative_to(pkg_obj.root)))
            report[table] = entry
            continue
        any_found = True
        mother_rel = mothers[table]

        rows, err = load_json(valid_p)
        if err is not None or not isinstance(rows, list):
            fail("Could not parse {}: {}".format(valid_p, err or "not a JSON array"),
                 "toy_valid.json must be a JSON array of row objects.")
        findings = flatten_findings(pkg_obj, table, mother_rel,
                                    validate_rows(pkg_obj, mother_rel, rows))
        entry["valid"] = {
            "file": str(valid_p.relative_to(pkg_obj.root)),
            "rows": len(rows),
            "status": "pass" if not findings else "fail",
            "errors": len(findings),
            **({"findings": findings[:25]} if findings else {}),
        }
        if findings:
            all_ok = False

        if not invalid_p.is_file() or not ledger_p.is_file():
            entry["invalid"] = {"skipped": "toy_invalid.json and its ledger are both "
                                           "required - see VALIDATE.md."}
            all_ok = False
            report[table] = entry
            continue
        bad_rows, err = load_json(invalid_p)
        ledger, lerr = load_json(ledger_p)
        if err or lerr or not isinstance(bad_rows, list) or not isinstance(ledger, dict):
            fail("Could not parse the invalid fixture pair: {}".format(err or lerr),
                 "toy_invalid.json is a JSON array; toy_invalid_ledger.json is an "
                 "object with a violations array. Formats in VALIDATE.md.")
        cases = ledger.get("violations", [])
        bad_findings = flatten_findings(pkg_obj, table, mother_rel,
                                        validate_rows(pkg_obj, mother_rel, bad_rows))
        by_row = {}
        for f in bad_findings:
            if f["row"] is not None:
                by_row.setdefault(f["row"], []).append(f)
        verdicts, caught = [], 0
        fired_cases, fired_conds = {}, {}   # rule id -> rows / -> {allOf index: n}
        for case in cases:
            row, col = case.get("row"), case.get("column")
            v = {"row": row, "column": col, "kind": case.get("kind", "?")}
            if not isinstance(row, int) or row >= len(bad_rows):
                v["status"] = "phantom"
                v["hint"] = "The ledger names row {} but toy_invalid.json has {} rows.".format(
                    row, len(bad_rows))
            elif any(f["column"] == col for f in by_row.get(row, [])):
                v["status"] = "caught"
                caught += 1
                # Which registered rules this seed proved: attribution only.
                fired = sorted({(f["rule_id"], f["allof_index"]) for f in by_row[row]
                                if f["column"] == col and f.get("rule_id")})
                if fired:
                    v["rules"] = sorted({rid for rid, _ in fired})
                    for rid, idx in fired:
                        fired_cases.setdefault(rid, set()).add(row)
                        conds = fired_conds.setdefault(rid, {})
                        conds[str(idx)] = conds.get(str(idx), 0) + 1
            elif by_row.get(row):
                v["status"] = "missed-wrong-column"
                v["failed_on"] = sorted({f["column"] for f in by_row[row] if f["column"]})
                v["hint"] = ("Row {} failed, but not on {!r} - the seed broke something "
                             "else too, or the ledger names the wrong column.").format(row, col)
            else:
                v["status"] = "missed-passed"
                v["hint"] = ("Row {} validated clean. The rule this seed should trip is "
                             "missing (a skip without its applicability twin, most "
                             "often), or the seeded value is actually legal.").format(row)
            verdicts.append(v)
        ledgered = {c.get("row") for c in cases}
        unledgered = sorted(r for r in by_row if r not in ledgered)
        phantoms = [v for v in verdicts if v["status"] == "phantom"]
        entry["invalid"] = {
            "file": str(invalid_p.relative_to(pkg_obj.root)),
            "ledger": str(ledger_p.relative_to(pkg_obj.root)),
            "cases": len(cases),
            "caught": caught,
            "verdicts": verdicts,
            "unledgered_failing_rows": unledgered,
            "rules_fired": {rid: {"cases": len(fired_cases[rid]),
                                  "conditionals": fired_conds.get(rid, {})}
                            for rid in sorted(fired_cases)},
        }
        if caught != len(cases) or unledgered or phantoms:
            all_ok = False
        report[table] = entry
    return {"ok": all_ok and any_found, "tables": report,
            **({} if any_found else {
                "error": "No toy fixtures found in the package.",
                "hint": "Author examples/toy_valid.json, toy_invalid.json, and "
                        "toy_invalid_ledger.json per VALIDATE.md.",
            })}


# ------------------------------------------------------------------ coverage


INVENTORY_COLUMNS = ["variable", "table", "category", "status", "source", "notes"]
INVENTORY_STATUSES = {"pending", "converted", "deferred", "dropped", "added"}


CSV_ENCODING_HINT = ("Re-save it as UTF-8 (Excel: 'CSV UTF-8'); the validator reads "
                     "UTF-8 with or without a BOM.")


def read_csv_table(path, columns, what, format_doc, strict=True, notes=None):
    """A working-state CSV (VARIABLES.csv, ROUTING.csv) as (rows, header):
    row dicts each stamped with a 1-based `_line`, header cells trimmed,
    blank lines skipped and counted in `notes`. fail()s on an unreadable
    file or a missing column; with strict=False returns (None, header) and
    says why in `notes` instead, so a caller that only wants a look can go on."""
    notes = notes if notes is not None else []
    header = []

    def give_up(error, hint):
        if strict:
            fail(error, hint)
        notes.append(error)
        return None, header

    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            header = [c.strip() for c in (reader.fieldnames or []) if c is not None]
            reader.fieldnames = header
            missing = [c for c in columns if c not in header]
            if missing:
                return give_up("{} is missing columns: {}.".format(what, ", ".join(missing)),
                               "The fixed header is: {}. Format in {}.".format(
                                   ",".join(columns), format_doc))
            rows, blank = [], []
            for i, raw in enumerate(reader, start=2):
                if not any((raw.get(c) or "").strip() for c in columns):
                    blank.append(i)   # whitespace, or Excel's trailing ",,,,,," line
                    continue
                raw["_line"] = i
                rows.append(raw)
    except (UnicodeDecodeError, csv.Error, OSError) as exc:
        return give_up("{} could not be read: {}".format(what, exc),
                       "{} Format in {}.".format(CSV_ENCODING_HINT, format_doc))
    if blank:
        notes.append("{} blank line{} ignored (line{} {})".format(
            len(blank), "" if len(blank) == 1 else "s", "" if len(blank) == 1 else "s",
            ", ".join(str(b) for b in blank[:10]) + (", ..." if len(blank) > 10 else "")))
    return rows, header


def load_inventory(pkg_obj, inventory=None, strict=True, notes=None):
    """VARIABLES.csv as (path, rows); each row carries its 1-based `_line`,
    blank lines are skipped. fail()s on a missing, unreadable, or
    column-short file; with strict=False returns (path, None) and explains
    in `notes` instead, so a caller that only wants readiness can go on."""
    inv_path = Path(inventory) if inventory else pkg_obj.root / "VARIABLES.csv"
    notes = notes if notes is not None else []
    if not inv_path.is_file():
        error = "Variables inventory not found: {}".format(inv_path)
        if strict:
            fail(error, "Intake writes VARIABLES.csv in the package root - one row per "
                        "source variable. Format in VALIDATE.md.")
        notes.append(error)
        return inv_path, None
    rows, _ = read_csv_table(inv_path, INVENTORY_COLUMNS, "VARIABLES.csv", "VALIDATE.md",
                             strict=strict, notes=notes)
    return inv_path, rows


def schema_property_index(pkg_obj):
    """table -> {property: category} from every mother's category $refs."""
    mothers = pkg_obj.mothers()
    schema_props = {}   # table -> {property: category}
    for table, mother_rel in mothers.items():
        props = {}
        doc = pkg_obj.docs[mother_rel]
        for entry in allof_entries(doc):
            if isinstance(entry, dict) and "$ref" in entry and "if" not in entry:
                ref = entry["$ref"]
                category = (PurePosixPath(ref.partition("#")[0]).stem or "?"
                            if isinstance(ref, str) else "?")
                resolved = pkg_obj.deref(entry, mother_rel)
                if isinstance(resolved, dict) and isinstance(resolved.get("properties"), dict):
                    for name in resolved["properties"]:
                        props[name] = category
        schema_props[table] = props
    return schema_props


def run_coverage(pkg_obj, args):
    notes = []
    inv_path, inventory = load_inventory(pkg_obj, args.inventory, notes=notes)
    mothers = pkg_obj.mothers()
    schema_props = schema_property_index(pkg_obj)

    default_table = next(iter(mothers)) if len(mothers) == 1 else None
    totals = {s: 0 for s in INVENTORY_STATUSES}
    bad_status, converted_missing, category_mismatch = [], [], []
    inventoried = {}
    for fallback, row in enumerate(inventory, start=2):
        i = row.get("_line", fallback)
        status = (row.get("status") or "").strip()
        table = (row.get("table") or "").strip() or default_table
        var = (row.get("variable") or "").strip()
        cat = (row.get("category") or "").strip()
        if status not in INVENTORY_STATUSES:
            bad_status.append({"line": i, "variable": var, "status": status,
                               "hint": "status must be one of: {}.".format(
                                   ", ".join(sorted(INVENTORY_STATUSES)))})
            continue
        totals[status] += 1
        if table is None:
            bad_status.append({"line": i, "variable": var, "status": status,
                               "hint": "The package has several tables - fill the "
                                       "table column."})
            continue
        inventoried.setdefault(table, {})[var] = status
        props = schema_props.get(table, {})
        if status in ("converted", "added"):
            if var not in props:
                converted_missing.append({
                    "variable": var, "table": table, "category": cat,
                    "hint": "Status says {} but no category file of table {!r} has "
                            "this property.".format(status, table)})
            elif cat and cat != "unassigned" and props[var] != cat:
                category_mismatch.append({
                    "variable": var, "table": table,
                    "inventory": cat, "schema": props[var],
                    "hint": "The inventory and the schemas disagree about the "
                            "category - update whichever is stale."})
        elif var in props:
            converted_missing.append({
                "variable": var, "table": table, "category": cat,
                "hint": "Status is {!r} but the property exists in the schemas - "
                        "flip the status or remove the property.".format(status)})
    not_in_inventory = []
    for table, props in schema_props.items():
        for name, cat in sorted(props.items()):
            if name not in inventoried.get(table, {}):
                not_in_inventory.append({
                    "variable": name, "table": table, "category": cat,
                    "hint": "Add an inventory row - status `added` with the origin in "
                            "source if the schemas introduced it deliberately."})
    problems = {
        "bad_rows": bad_status,
        "converted_missing_from_schema": converted_missing,
        "schema_not_in_inventory": not_in_inventory,
        "category_mismatch": category_mismatch,
    }
    ok = not any(problems.values())
    return {
        "ok": ok,
        "inventory": str(inv_path),
        "totals": {"rows": len(inventory), **totals},
        "schema_properties": sum(len(p) for p in schema_props.values()),
        "problems": problems,
        **({"notes": notes} if notes else {}),
    }


# ------------------------------------------------------------------- routing


class _Args:
    """Defaults for a runner called from another runner (summary, routing)."""
    table = None
    inventory = None
    max_findings = 200

    def __init__(self, **kw):
        self.__dict__.update(kw)


def split_names(cell):
    return [n.strip() for n in cell.split(";") if n.strip()]


def parse_waits(notes):
    """Names after 'waits for' in a notes cell: categories or variables."""
    names = []
    for m in WAITS_RE.finditer(notes or ""):
        names.extend(n.strip() for n in re.split(r"[;,]", m.group(1)) if n.strip())
    return names


def load_routing(pkg_obj, path=None):
    """ROUTING.csv as (path, rows, findings). Each row carries its 1-based
    line, its split names, and `valid` (False once its id or status is
    unusable). fail()s on a missing column - that register is not readable."""
    reg_path = Path(path) if path else pkg_obj.root / "ROUTING.csv"
    findings, rows, seen, notes = [], [], {}, []
    raw_rows, header = read_csv_table(reg_path, ROUTING_COLUMNS, "ROUTING.csv",
                                      "ROUTING-FORMAT.md", strict=True, notes=notes)
    extra = [c for c in header if c not in ROUTING_COLUMNS]
    if extra:
        findings.append(finding(
            "warn", "extra-column",
            "ROUTING.csv carries columns the format does not define: {}."
            .format(", ".join(extra)),
            "Keep the fixed ten-column header; free text belongs in notes "
            "(ROUTING-FORMAT.md).", file=reg_path.name, line=1))
    if notes:
        findings.append(finding(
            "info", "blank-rows",
            "ROUTING.csv: {}.".format("; ".join(notes)),
            "Delete them - Excel leaves trailing ',,,,' rows behind; they are "
            "ignored, but a tidy register has none.", file=reg_path.name))
    for raw in raw_rows:
        i = raw["_line"]
        row = {c: (raw.get(c) or "").strip() for c in ROUTING_COLUMNS}
        row["line"] = i
        row["trigger_names"] = split_names(row["trigger"])
        row["target_names"] = split_names(row["targets"])
        row["names"] = list(dict.fromkeys(row["trigger_names"] + row["target_names"]))
        row["waits"] = parse_waits(row["notes"])
        row["valid"] = True
        w = {"file": reg_path.name, "line": i, "rule_id": row["id"] or None}
        if not RULE_ID_RE.match(row["id"]):
            row["valid"] = False
            findings.append(finding(
                "error", "bad-id",
                "Line {}: id {!r} is not of the form R001.".format(i, row["id"]),
                "Ids are R followed by at least three digits, zero-padded, "
                "scan-and-increment, never reused (ROUTING-FORMAT.md).", **w))
        elif row["id"] in seen:
            row["valid"] = False
            findings.append(finding(
                "error", "duplicate-id",
                "Line {}: id {} is already used on line {}.".format(i, row["id"], seen[row["id"]]),
                "One row per routing fact - a skip/applicability pair shares one row "
                "and one id. Give this row the next free id.", **w))
        else:
            seen[row["id"]] = i
        if row["status"] not in ROUTING_STATUSES:
            row["valid"] = False
            findings.append(finding(
                "error", "bad-status",
                "Line {}: status {!r} is not one of {}.".format(
                    i, row["status"], ", ".join(ROUTING_STATUSES)),
                "Set one of: {} (ROUTING-FORMAT.md).".format(" · ".join(ROUTING_STATUSES)),
                **w))
        if row["evidence"] not in ROUTING_EVIDENCE:
            findings.append(finding(
                "error", "bad-evidence",
                "Line {}: evidence {!r} is not one of {}.".format(
                    i, row["evidence"], ", ".join(ROUTING_EVIDENCE)),
                "Record where the rule came from: the source's words (quoted), a "
                "label or title that implies it (implied), the steward (steward), "
                "or your own expectation (inferred).", **w))
        if row["decision"] and not DECISION_RE.match(row["decision"]):
            findings.append(finding(
                "error", "bad-decision",
                "Line {}: decision {!r} is not a D-number.".format(i, row["decision"]),
                "Cite the DECISIONS.md line as D010, or leave the cell blank where "
                "ROUTING-FORMAT.md allows it.", **w))
        for column, names in (("trigger", row["trigger_names"]),
                              ("targets", row["target_names"])):
            for name in names:
                if not VAR_NAME_RE.match(name):
                    findings.append(finding(
                        "error", "bad-variable-name",
                        "Line {}: {!r} in {} is not a property name.".format(i, name, column),
                        "trigger and targets hold schema property names, ;-separated; "
                        "the gist (nap_yesterday=0 → ...) belongs in the rule column.",
                        variable=name, **w))
        rows.append(row)
    return reg_path, rows, findings


def na_sentinel_properties(pkg_obj, props):
    """The structural-NA heuristic, echoed so it can be audited: $defs whose
    title/description read as not-applicable (and their consts), then every
    row property with a branch that $refs one, is titled so, or carries one
    of those consts."""
    defs, consts = {}, []
    for rel, doc in sorted(pkg_obj.docs.items()):
        for name, sub in (doc.get("$defs") or {}).items() if isinstance(doc.get("$defs"), dict) else []:
            if not isinstance(sub, dict):
                continue
            text = " ".join(str(sub.get(k) or "") for k in ("title", "description"))
            if NA_TITLE_RE.search(text):
                defs["{}#/$defs/{}".format(rel, name)] = sub.get("title") or sub.get("description") or name
                if "const" in sub:
                    consts.append(sub["const"])
                elif isinstance(sub.get("enum"), list):
                    consts.extend(sub["enum"])
    const_keys = {literal_key(c) for c in consts}

    def bearing(node, origin_rel, depth=0):
        if not isinstance(node, dict) or depth > 6:
            return False
        if isinstance(node.get("$ref"), str):
            ref_rel, frag = resolve_ref(pkg_obj, origin_rel, node["$ref"])
            if ref_rel and "{}#{}".format(ref_rel, frag) in defs:
                return True
        node = pkg_obj.deref(node, origin_rel)
        if not isinstance(node, dict):
            return False
        if NA_TITLE_RE.search(str(node.get("title") or "")):
            return True
        if "const" in node and literal_key(node["const"]) in const_keys:
            return True
        for key in APPLICATORS_LIST:
            if isinstance(node.get(key), list):
                if any(bearing(b, origin_rel, depth + 1) for b in node[key]):
                    return True
        return False

    names = [name for name, (sub, origin, _cat) in props.items() if bearing(sub, origin)]
    return {"defs": defs, "consts": consts, "bearing": names}


def run_routing(pkg_obj, args, check=None, fixtures=None):
    """Reconcile ROUTING.csv with the mothers' conditionals: every encoded row
    has its id in a conditional and vice versa, variables agree, the tenet
    holds (no inferred rule encoded without a decision), waiting rows are
    reported ready when their variables convert, encoded rules are tied to
    the fixture cases that fired them, and NA-bearing properties nobody
    routes are listed. `check` and `fixtures` are earlier reports the caller
    already has, so nothing validates twice."""
    table_arg = getattr(args, "table", None)
    max_findings = getattr(args, "max_findings", None) or 200
    mothers = pkg_obj.mothers()
    if not mothers:
        fail("No mother file (*.schema.json) found in the package.",
             "Each table needs <table>/<table>.schema.json. See LAYOUT.md.")
    if table_arg and table_arg not in mothers:
        fail("No table named {!r} (found: {}).".format(table_arg, ", ".join(sorted(mothers))),
             "Table names are the *.schema.json stems.")
    tables = [table_arg] if table_arg else sorted(mothers)
    default_table = next(iter(mothers)) if len(mothers) == 1 else None
    findings, skipped = [], []
    broken = broken_files(pkg_obj, check)

    # the mother side
    per_table, rules_by_id = {}, {}   # rule id -> [(table, record)]
    for table in list(tables):
        mother_rel = mothers[table]
        bad = sorted(table_files(pkg_obj, mother_rel) & broken)
        if bad:
            skipped.append("{}: meta-validation failed - fix check.meta first ({})"
                           .format(table, ", ".join(bad)))
            tables.remove(table)
            continue
        props, unresolved = table_properties(pkg_obj, mother_rel)
        records, _ = mother_conditionals(pkg_obj, mother_rel)
        per_table[table] = {"mother_rel": mother_rel, "props": props,
                            "records": records, "unresolved": unresolved}
        if unresolved:
            skipped.append("{}: category $ref(s) {} did not resolve - the NA, universe, "
                           "and waits checks stood down; fix them first (check.refs)"
                           .format(table, ", ".join(repr(u) for u in unresolved)))
        for rec in records:
            if rec["rule_id"]:
                rules_by_id.setdefault(rec["rule_id"], []).append((table, rec))
    schema_categories = {cat for t in per_table.values() for (_, _, cat) in t["props"].values()}

    # the register
    reg_path = pkg_obj.root / "ROUTING.csv"
    register, rows = None, []
    if reg_path.is_file():
        _, rows, reg_findings = load_routing(pkg_obj, reg_path)
        findings.extend(reg_findings)
        by_status = {s: 0 for s in ROUTING_STATUSES}
        for row in rows:
            if row["status"] in by_status:
                by_status[row["status"]] += 1
        register = {"file": reg_path.name, "rows": len(rows), "by_status": by_status}
    else:
        total = sum(len(t["records"]) for t in per_table.values())
        idless = sum(1 for t in per_table.values() for r in t["records"] if not r["rule_id"])
        skipped.append("register: no ROUTING.csv yet - {} conditional{}, {} without a rule "
                       "id; the skips migrate unit builds it (ROUTING.md)"
                       .format(total, "" if total == 1 else "s", idless))

    # the inventory, for readiness
    inventory, inv_categories, inventory_partial = None, set(), False
    inv_notes = []
    inv_path, inv_rows = load_inventory(pkg_obj, strict=False, notes=inv_notes)
    if inv_rows is None:
        skipped.append("readiness: {} - waiting rows cannot be checked".format(
            "no VARIABLES.csv yet (intake writes it)" if not inv_path.is_file()
            else "; ".join(inv_notes) or "VARIABLES.csv is unreadable"))
    else:
        inventory, untabled = {}, 0
        for r in inv_rows:
            t = (r.get("table") or "").strip() or default_table
            var = (r.get("variable") or "").strip()
            if t is None:
                untabled += 1
                continue
            if not var:
                continue
            inventory.setdefault(t, {})[var] = (r.get("status") or "").strip()
            if (r.get("category") or "").strip():
                inv_categories.add(r["category"].strip())
        if untabled:
            inventory_partial = True
            skipped.append("readiness: {} VARIABLES.csv row{} ha{} no table column (coverage "
                           "says which) - uninventoried names are not reported"
                           .format(untabled, "" if untabled == 1 else "s",
                                   "s" if untabled == 1 else "ve"))
    categories = schema_categories | inv_categories

    # the fixtures, for attribution
    if fixtures is None:
        unresolved_any = [t for t in tables if per_table[t]["unresolved"]]
        if broken:
            skipped.append("fixtures: meta-validation failed ({}) - fix check.meta first"
                           .format(", ".join(sorted(broken))))
        elif unresolved_any:
            skipped.append("fixtures: category $ref(s) of {} did not resolve - fix them "
                           "first (check.refs)".format(", ".join(unresolved_any)))
        elif any((pkg_obj.root / "examples").rglob("toy_valid.json")):
            fixtures = run_fixtures(pkg_obj, _Args(table=table_arg))
        else:
            skipped.append("fixtures: no examples/toy_valid.json yet - encoded rules cannot "
                           "be tied to seeded cases")
    fired = {}
    for table in tables:
        report = (fixtures or {}).get("tables", {}).get(table, {})
        invalid = report.get("invalid", {}) if isinstance(report, dict) else {}
        fired[table] = invalid.get("rules_fired") if "cases" in invalid else None

    # register rows against the mothers
    rules_out, rows_by_id, row_table = {}, {}, {}
    all_ids = {row["id"] for row in rows}
    for row in rows:
        if not row["valid"]:
            continue
        rid, status, evidence, decision = row["id"], row["status"], row["evidence"], row["decision"]
        rows_by_id[rid] = row
        table = row["table"] or default_table
        w = {"file": reg_path.name, "line": row["line"], "rule_id": rid}
        if table is None:
            findings.append(finding(
                "error", "missing-table",
                "Line {}: the package has several tables but the table column is blank."
                .format(row["line"]),
                "Fill the table column - a rule never crosses tables, so every row names "
                "the one it lives in.", **w))
            continue
        if table not in mothers:
            findings.append(finding(
                "error", "unknown-table",
                "Line {}: table {!r} is not a table of this package (found: {})."
                .format(row["line"], table, ", ".join(sorted(mothers))),
                "Table names are the *.schema.json stems.", **w))
            continue
        row_table[rid] = table
        if table not in per_table:
            continue  # outside --table
        w["table"] = table
        props = per_table[table]["props"]
        names = row["names"]

        # the tenet, made mechanical
        if status == "encoded" and evidence == "inferred" and not decision:
            findings.append(finding(
                "error", "unconfirmed-encoded",
                "Line {}: {} is encoded on inferred evidence with no decision.".format(row["line"], rid),
                "An inferred rule reaches the mother only after the steward's yes - cite "
                "that ledger line in decision, or set the status back to proposed with "
                "its open D-line and take the conditional out.", **w))
        if status == "proposed" and not decision:
            findings.append(finding(
                "error", "proposed-undecided",
                "Line {}: {} is proposed but cites no decision.".format(row["line"], rid),
                "The open D-line is the proposal (ELICIT.md: the ledger is the queue) - "
                "open it and cite it here.", **w))
        if not decision and ((status == "encoded" and evidence in ("implied", "steward"))
                             or status in ("confirmed", "declined", "not-enforceable")):
            why = {"confirmed": "records the steward's yes", "declined": "declines it",
                   "not-enforceable": "says why it cannot be enforced",
                   }.get(status, "records the {} reading".format(evidence))
            findings.append(finding(
                "warn", "decision-missing",
                "Line {}: {} is {}{} with no decision.".format(
                    row["line"], rid, status,
                    " on {} evidence".format(evidence) if status == "encoded" else ""),
                "Cite the ledger line that {} - a revisit needs a starting point.".format(why),
                **w))
        if status in ("confirmed", "encoded") and (not row["trigger_names"] or not row["target_names"]):
            blank = [c for c, v in (("trigger", row["trigger_names"]), ("targets", row["target_names"])) if not v]
            findings.append(finding(
                "error", "empty-variables",
                "Line {}: {} is {} but its {} column is blank.".format(
                    row["line"], rid, status, " and ".join(blank)),
                "Name the gate in trigger and the dependents in targets; only a "
                "not-enforceable row may leave the trigger blank.", **w))

        # the mother
        recs = [rec for t, rec in rules_by_id.get(rid, []) if t == table]
        elsewhere = [t for t, rec in rules_by_id.get(rid, []) if t != table]
        if status == "encoded":
            if not recs and not elsewhere:
                findings.append(finding(
                    "error", "unencoded-row",
                    "Line {}: {} is encoded but no conditional in {} carries it."
                    .format(row["line"], rid, table),
                    "Add the id to the conditional's $comment ('Skip pattern {}: ...'), "
                    "or set the status to confirmed and make encoding the next: unit."
                    .format(rid), **w))
            elif recs:
                trig_union = set().union(*[r["triggers"] for r in recs])
                targ_union = set().union(*[r["targets"] for r in recs])
                missing = ([n for n in row["trigger_names"] if n not in trig_union]
                           + [n for n in row["target_names"] if n not in targ_union])
                pointers = ", ".join(r["pointer"] for r in recs)
                if missing:
                    findings.append(finding(
                        "error", "rule-variable-mismatch",
                        "Line {}: {} names {} but its conditional{} at {} do{} not touch "
                        "{}.".format(row["line"], rid, ", ".join(missing),
                                     "" if len(recs) == 1 else "s", pointers,
                                     "es" if len(recs) == 1 else "",
                                     "it" if len(missing) == 1 else "them"),
                        "trigger must be among the if's properties and targets among the "
                        "then's - fix whichever is stale after a rename or recode.",
                        variable=missing[0] if len(missing) == 1 else None,
                        variables=missing if len(missing) > 1 else None, **w))
                unlisted = sorted((trig_union - set(row["trigger_names"]))
                                  | (targ_union - set(row["target_names"])))
                if unlisted:
                    findings.append(finding(
                        "warn", "unlisted-variable",
                        "Line {}: the conditional{} for {} also constrain{} {}, which the "
                        "row does not list.".format(
                            row["line"], "" if len(recs) == 1 else "s", rid,
                            "s" if len(recs) == 1 else "", ", ".join(unlisted)),
                        "List every gate in trigger and every dependent in targets so the "
                        "register reads as the rule's full scope.",
                        variables=unlisted, **w))
                if fired.get(table) is not None:
                    conds = fired[table].get(rid, {}).get("conditionals", {})
                    sev = "info" if len(per_table[table]["records"]) > MANY_CONDITIONALS else "warn"
                    for rec in recs:
                        if str(rec["index"]) in conds:
                            continue
                        prefix = rec["parsed"]["prefix"] if rec["parsed"] else "conditional"
                        findings.append(finding(
                            sev, "rule-unfixtured",
                            "{}'s conditional {} ({}) fired on no seeded case."
                            .format(rid, rec["index"], prefix),
                            "Seed one toy_invalid.json row that trips it and ledger it with "
                            "the id in reason (VALIDATE.md) - a rule no fixture fires is a "
                            "rule nobody has seen work.",
                            file=per_table[table]["mother_rel"], pointer=rec["pointer"],
                            allof_index=rec["index"], rule=rec["comment"], table=table,
                            rule_id=rid, register_line=row["line"]))
        elif status == "confirmed":
            findings.append(finding(
                "warn", "unencoded-confirmed",
                "Line {}: {} is confirmed but not yet encoded.".format(row["line"], rid),
                "Encode it per SKIP-PATTERNS.md and flip the status - never leave a "
                "session here without a next: naming it.", **w))
        elif status == "waiting" and inventory is not None and names:
            statuses = [inventory.get(table, {}).get(n) for n in names]
            if all(s in ("converted", "added") for s in statuses):
                findings.append(finding(
                    "info", "ready",
                    "Line {}: {} is waiting but every variable it names ({}) is converted."
                    .format(row["line"], rid, ", ".join(names)),
                    "Encode it now if the evidence is quoted, implied, or steward; if "
                    "inferred, open its D-line and set the status to proposed.", **w))

        # readiness bookkeeping
        if inventory is not None:
            for name in names:
                st = inventory.get(table, {}).get(name)
                if st is None and inventory_partial:
                    continue  # rows without a table column: the skipped note says so
                if st is None:
                    findings.append(finding(
                        "warn", "variable-uninventoried",
                        "Line {}: {} names {!r}, which VARIABLES.csv does not list."
                        .format(row["line"], rid, name),
                        "Add the inventory row (or fix the spelling) - a name the inventory "
                        "never sees is never reported ready.", variable=name, **w))
                elif st == "dropped":
                    findings.append(finding(
                        "warn", "names-dropped",
                        "Line {}: {} names {!r}, a dropped variable.".format(row["line"], rid, name),
                        "A rule on a dropped variable cannot fire - set the row to "
                        "not-enforceable with the reason, or revisit the drop.",
                        variable=name, **w))
        for name in row["waits"]:
            if per_table[table]["unresolved"]:
                break  # the table's properties are unknown: stood down (skipped says so)
            known = (name in categories or name in props
                     or (inventory is not None and name in inventory.get(table, {})))
            if not known:
                findings.append(finding(
                    "warn", "waits-unknown",
                    "Line {}: {} waits for {!r}, which is neither a category nor a variable."
                    .format(row["line"], rid, name),
                    "Name the category or variable exactly as VARIABLES.csv spells it, so "
                    "the wait clears when it converts.", variable=name, **w))

        rules_out[rid] = {
            "table": table, "status": status, "evidence": evidence,
            "decision": decision or None, "line": row["line"],
            "conditionals": [rec["pointer"] for rec in recs],
            "fixture_cases": (fired.get(table) or {}).get(rid, {}).get("cases", 0),
        }

    # the mothers against the register
    if register is not None:
        for table in tables:
            mother_rel = mothers[table]
            for rec in per_table[table]["records"]:
                w = {"table": table, "file": mother_rel, "pointer": rec["pointer"],
                     "allof_index": rec["index"], "rule": rec["comment"]}
                rid = rec["rule_id"]
                if not rid:
                    findings.append(finding(
                        "warn", "unregistered-rule",
                        "Conditional {} carries no rule id in its $comment.".format(rec["index"]),
                        "Register it in ROUTING.csv and prefix the $comment with the id "
                        "('Skip pattern R001: ...') - the skips migrate unit does this for "
                        "a package that predates the register (ROUTING.md).", **w))
                    continue
                w["rule_id"] = rid
                row = rows_by_id.get(rid)
                if row is not None and rid not in row_table:
                    continue  # its row's table is already an error above
                if row is None:
                    if rid in all_ids:
                        continue  # its row is already an error above
                    findings.append(finding(
                        "error", "unknown-rule-id",
                        "Conditional {} carries {}, which ROUTING.csv does not register."
                        .format(rec["index"], rid),
                        "Add the row (status encoded) with the rule's evidence and "
                        "decision, or fix the id in the $comment.", **w))
                elif row_table.get(rid) != table:
                    findings.append(finding(
                        "error", "wrong-table",
                        "Conditional {} of {} carries {}, but its register row names table "
                        "{!r}.".format(rec["index"], table, rid, row["table"]),
                        "A rule lives in one table - correct the row's table column or "
                        "move the conditional.", **w))
                elif row["status"] != "encoded":
                    findings.append(finding(
                        "error", "misregistered-rule",
                        "Conditional {} carries {}, but its register row says {}."
                        .format(rec["index"], rid, row["status"]),
                        "Set the row to encoded if the rule belongs in the mother; "
                        "otherwise take the conditional out - a declined or waiting rule "
                        "is documented, never enforced.", **w))

    # NA-bearing properties nobody routes
    conditionals_block, na_block = {}, {}
    for table in tables:
        info = per_table[table]
        recs, props = info["records"], info["props"]
        conditionals_block[table] = {
            "count": len(recs),
            "with_id": sum(1 for r in recs if r["rule_id"]),
            "unregistered": sum(1 for r in recs if not r["rule_id"]),
        }
        if info["unresolved"]:
            na_block[table] = {"skipped": "category $ref(s) did not resolve"}
            continue
        targeted = set().union(*[r["targets"] for r in recs]) if recs else set()
        registered = set()
        for row in rows:
            if (row["table"] or default_table) == table:
                registered.update(row["names"])
        na = na_sentinel_properties(pkg_obj, props)
        unrouted = [p for p in na["bearing"] if p not in targeted and p not in registered]
        na_block[table] = {"defs": na["defs"], "consts": na["consts"],
                           "bearing": na["bearing"], "unrouted": unrouted[:NA_LIST_CAP],
                           "truncated": len(unrouted) > NA_LIST_CAP}
        if unrouted:
            findings.append(finding(
                "info", "unrouted-na",
                "{} NA-bearing propert{} of {} appear{} in no rule and no register row: {}{}."
                .format(len(unrouted), "y" if len(unrouted) == 1 else "ies", table,
                        "s" if len(unrouted) == 1 else "",
                        ", ".join(unrouted[:NA_LIST_CAP]),
                        ", ..." if len(unrouted) > NA_LIST_CAP else ""),
                "Each carries a structural-NA branch, so something decides when it "
                "applies - register that rule (waiting, proposed, or encoded), or a row "
                "saying why not (declined, not-enforceable).",
                table=table, file=info["mother_rel"], count=len(unrouted),
                variables=unrouted[:NA_LIST_CAP], truncated=len(unrouted) > NA_LIST_CAP))
        for name, (sub, _origin, _cat) in sorted(props.items()):
            if (isinstance(sub, dict) and "x-universe" in sub
                    and name not in targeted and name not in registered):
                findings.append(finding(
                    "info", "universe-unrouted",
                    "{} states an x-universe but no rule or register row enforces it."
                    .format(name),
                    "Register the rule the universe implies (implied evidence, quoting "
                    "the text), or a row saying why it cannot be enforced.",
                    table=table, file=info["mother_rel"], variable=name))

    counts = {s: sum(1 for f in findings if f["severity"] == s)
              for s in ("error", "warn", "info")}
    # Errors first (stable), so a capped list never hides the reason ok is false.
    rank = {"error": 0, "warn": 1, "info": 2}
    findings.sort(key=lambda f: rank.get(f["severity"], 3))
    return {
        "ok": counts["error"] == 0,
        "register": register,
        "rules": rules_out,
        "conditionals": conditionals_block,
        "na": na_block,
        "findings": findings[:max_findings],
        "truncated": len(findings) > max_findings,
        "counts": counts,
        "skipped": skipped,
    }


# ------------------------------------------------------------------- summary


def run_summary(pkg_obj, args):
    check = run_check(pkg_obj)
    skipped = []

    _NS = _Args()

    fixtures = None
    broken = broken_files(pkg_obj, check)
    if broken:
        skipped.append("fixtures: meta-validation failed ({}) - fix check.meta first"
                       .format(", ".join(sorted(broken))))
    elif check["refs"]["unresolved"]:
        skipped.append("fixtures: {} $ref(s) did not resolve - fix them first (check.refs)"
                       .format(len(check["refs"]["unresolved"])))
    elif any((pkg_obj.root / "examples").rglob("toy_valid.json")):
        fixtures = run_fixtures(pkg_obj, _NS)
    else:
        skipped.append("fixtures: no examples/toy_valid.json yet - see VALIDATE.md")
    coverage = None
    if (pkg_obj.root / "VARIABLES.csv").is_file():
        coverage = run_coverage(pkg_obj, _NS)
    else:
        skipped.append("coverage: no VARIABLES.csv yet - intake writes it")
    routing = None
    cond = check.get("conditionals") or {"count": 0, "with_id": 0,
                                         "counts": {"error": 0, "warn": 0, "info": 0}}
    if (pkg_obj.root / "ROUTING.csv").is_file():
        routing = run_routing(pkg_obj, _NS, check=check, fixtures=fixtures)
    else:
        skipped.append("routing: no ROUTING.csv yet - {} conditional{}, {} without a rule "
                       "id; the skips migrate unit builds the register (ROUTING.md)"
                       .format(cond["count"], "" if cond["count"] == 1 else "s",
                               cond["count"] - cond["with_id"]))

    ok = check["ok"] and (fixtures is None or fixtures["ok"]) \
        and (coverage is None or coverage["ok"]) \
        and (routing is None or routing["ok"])
    bits = ["{} schema files {}".format(check["files"],
                                        "valid" if check["ok"] else "with problems"),
            "{} $id base{}".format(len(check["ids"]["bases"]) or 1,
                                   "" if len(check["ids"]["bases"]) == 1 else "s"),
            "{} refs {}".format(check["refs"]["checked"],
                                "resolve" if not check["refs"]["unresolved"]
                                else "({} unresolved)".format(len(check["refs"]["unresolved"])))]
    if fixtures:
        for table, entry in fixtures["tables"].items():
            if "valid" in entry:
                inv = entry.get("invalid", {})
                bits.append("{}: toy PASS {} · {}/{} seeded violations caught".format(
                    table, entry["valid"]["status"],
                    inv.get("caught", 0), inv.get("cases", 0)))
    if coverage:
        t = coverage["totals"]
        bits.append("coverage {}/{} converted ({} deferred, {} pending)".format(
            t.get("converted", 0) + t.get("added", 0), t["rows"],
            t.get("deferred", 0), t.get("pending", 0)))
    cc = cond["counts"]
    bits.append("{} conditional{} {}".format(
        cond["count"], "" if cond["count"] == 1 else "s",
        "clean" if not (cc["error"] or cc["warn"])
        else "({} error{}, {} warning{})".format(cc["error"], "" if cc["error"] == 1 else "s",
                                                 cc["warn"], "" if cc["warn"] == 1 else "s")))
    if routing:
        bs = routing["register"]["by_status"]
        encoded_rules = [r for r in routing["rules"].values() if r["status"] == "encoded"]
        bits.append("routing {}/{} encoded{} · {} unregistered · {}/{} fixtured".format(
            bs["encoded"], routing["register"]["rows"],
            " · {} proposed".format(bs["proposed"]) if bs["proposed"] else "",
            sum(t["unregistered"] for t in routing["conditionals"].values()),
            sum(1 for r in encoded_rules if r["fixture_cases"]), len(encoded_rules)))
    return {
        "ok": ok,
        "package": pkg_obj.root.name,
        "headline": " · ".join(bits),
        "check": check,
        **({"fixtures": fixtures} if fixtures else {}),
        **({"coverage": coverage} if coverage else {}),
        **({"routing": routing} if routing else {}),
        "skipped": skipped,
    }


# ---------------------------------------------------------------------- main


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("check", "data", "fixtures", "coverage", "routing", "summary"):
        p = sub.add_parser(name)
        p.add_argument("package", help="package root directory")
        if name == "data":
            p.add_argument("--file", required=True)
            p.add_argument("--table")
            p.add_argument("--format", choices=("json", "csv"))
            p.add_argument("--max-errors", type=int, default=200)
        if name == "fixtures":
            p.add_argument("--table")
        if name == "coverage":
            p.add_argument("--inventory")
        if name == "routing":
            p.add_argument("--table")
            p.add_argument("--max-findings", type=int, default=200)
    args = parser.parse_args()

    pkg = guard_package_path(Path(args.package))
    pkg_obj = Package(pkg)
    if not pkg_obj.docs and args.cmd != "check":
        fail("No schema files found under {}.".format(pkg),
             "Run `validate.py check` for details, and see LAYOUT.md for the "
             "package tree.")
    runner = {"check": lambda: run_check(pkg_obj),
              "data": lambda: run_data(pkg_obj, args),
              "fixtures": lambda: run_fixtures(pkg_obj, args),
              "coverage": lambda: run_coverage(pkg_obj, args),
              "routing": lambda: run_routing(pkg_obj, args),
              "summary": lambda: run_summary(pkg_obj, args)}[args.cmd]
    result = runner()
    out(result, 0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
