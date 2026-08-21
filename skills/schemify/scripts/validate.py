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
      (one base, path-mirroring); every $ref in every file resolves.
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
  summary PKG
      check + fixtures + coverage in one rollup with a relay-ready headline.
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
        while isinstance(node, dict) and "$ref" in node and depth < 8:
            base_doc = self.docs.get(origin_rel, {})
            base_uri = base_doc.get("$id") or self.doc_uri(origin_rel)
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
    """Map id() of every node inside each mother conditional to (index, $comment)."""
    doc = pkg_obj.docs[mother_rel]
    items = doc.get("items", {})
    entries = items.get("allOf", []) if isinstance(items, dict) else []
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
            conditionals.append({"index": i, "comment": comment})
            collect(entry, (i, comment))
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

        rule = None
        parent = getattr(err, "parent", None)
        for candidate in (err.schema, parent.schema if parent is not None else None):
            if candidate is not None and id(candidate) in cond_ids:
                rule = cond_ids[id(candidate)][1]
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


def row_property_schemas(pkg_obj, mother_rel):
    """properties of the row object: union of every category's properties."""
    doc = pkg_obj.docs[mother_rel]
    items = doc.get("items", {})
    props = {}
    for entry in items.get("allOf", []) if isinstance(items, dict) else []:
        if isinstance(entry, dict) and "$ref" in entry and "if" not in entry:
            resolved = pkg_obj.deref(entry, mother_rel)
            if isinstance(resolved, dict):
                for name, sub in (resolved.get("properties") or {}).items():
                    props[name] = (sub, mother_rel)
    return props


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


def run_coverage(pkg_obj, args):
    inv_path = Path(args.inventory) if args.inventory else pkg_obj.root / "VARIABLES.csv"
    if not inv_path.is_file():
        fail("Variables inventory not found: {}".format(inv_path),
             "Intake writes VARIABLES.csv in the package root - one row per source "
             "variable. Format in VALIDATE.md.")
    with open(inv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in INVENTORY_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            fail("VARIABLES.csv is missing columns: {}.".format(", ".join(missing)),
                 "The fixed header is: {}.".format(",".join(INVENTORY_COLUMNS)))
        inventory = list(reader)

    mothers = pkg_obj.mothers()
    schema_props = {}   # table -> {property: category}
    for table, mother_rel in mothers.items():
        props = {}
        doc = pkg_obj.docs[mother_rel]
        items = doc.get("items", {})
        for entry in items.get("allOf", []) if isinstance(items, dict) else []:
            if isinstance(entry, dict) and "$ref" in entry and "if" not in entry:
                ref = entry["$ref"]
                category = PurePosixPath(ref.partition("#")[0]).stem or "?"
                resolved = pkg_obj.deref(entry, mother_rel)
                if isinstance(resolved, dict):
                    for name in (resolved.get("properties") or {}):
                        props[name] = category
        schema_props[table] = props

    default_table = next(iter(mothers)) if len(mothers) == 1 else None
    totals = {s: 0 for s in INVENTORY_STATUSES}
    bad_status, converted_missing, category_mismatch = [], [], []
    inventoried = {}
    for i, row in enumerate(inventory, start=2):
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
    }


# ------------------------------------------------------------------- summary


def run_summary(pkg_obj, args):
    check = run_check(pkg_obj)
    skipped = []

    class _NS:
        table = None
        inventory = None

    fixtures = None
    if any((pkg_obj.root / "examples").rglob("toy_valid.json")):
        fixtures = run_fixtures(pkg_obj, _NS)
    else:
        skipped.append("fixtures: no examples/toy_valid.json yet - see VALIDATE.md")
    coverage = None
    if (pkg_obj.root / "VARIABLES.csv").is_file():
        coverage = run_coverage(pkg_obj, _NS)
    else:
        skipped.append("coverage: no VARIABLES.csv yet - intake writes it")

    ok = check["ok"] and (fixtures is None or fixtures["ok"]) \
        and (coverage is None or coverage["ok"])
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
    return {
        "ok": ok,
        "package": pkg_obj.root.name,
        "headline": " · ".join(bits),
        "check": check,
        **({"fixtures": fixtures} if fixtures else {}),
        **({"coverage": coverage} if coverage else {}),
        "skipped": skipped,
    }


# ---------------------------------------------------------------------- main


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("check", "data", "fixtures", "coverage", "summary"):
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
              "summary": lambda: run_summary(pkg_obj, args)}[args.cmd]
    result = runner()
    out(result, 0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
