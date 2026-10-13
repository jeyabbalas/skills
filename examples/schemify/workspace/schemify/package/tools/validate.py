#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema>=4.18", "referencing>=0.35"]
# ///
"""Validate a schemify package: the draft 2020-12 JSON Schema files that
describe a study's tables, their house style and rules, their toy data, and
data files people bring.

Run with uv, which installs the dependencies:
    uv run validate.py <subcommand> PKG [options]
Without uv:
    python3 -m pip install --user "jsonschema>=4.18" referencing
    python3 validate.py <subcommand> PKG [options]

PKG is the package root, the folder holding schemas/: schemify/package in a
workspace, or the package itself when this file is its tools/validate.py.
    schemas/common/defs.json                 shared $defs (optional)
    schemas/<table>/<table>.schema.json      the mother: one per table folder
    schemas/<table>/categories/<topic>.json  one category file per topic
    toy-data/<table>/valid.json              rows that must all pass
    toy-data/<table>/invalid.json            one seeded violation per row
    toy-data/<table>/invalid-ledger.json     {"violations": [{"row", "column",
                                              "kind", "value"?, "reason"}]}
    provenance.json                          what x-provenance cites (optional)

Subcommands (each also takes --max-findings N, default 200):

check PKG
    Every schema file parses, meta-validates against draft 2020-12 and names
    it in $schema; $ids share one base and mirror their paths; every $ref
    resolves; the house style (SCHEMA-STYLE.md) and the rule grammar
    (SKIP-LOGIC.md) hold; every x-provenance reference is well formed and,
    when provenance.json exists, names a citable source or decision.
    -> {"ok", "package", "files", "tables": [{"table", "mother",
        "categories", "properties", "rules"}], "counts", "findings",
        "truncated"}

rules PKG [--table T]
    Every rule (a rule entry of a mother's items.allOf), normalized:
    {"table", "id", "kind": "skip"|"applicability"|"routing", "domain",
     "index", "file", "pointer", "comment", "reading", "provenance",
     "when": {"any": [{"all": [TEST, ...]}, ...]},
     "then": {"mode": "all"|"any", "effects": [EFFECT, ...]}}
    TEST   {"variable", "test": "eq"|"ne", "value"}
           {"variable", "test": "in"|"nin", "values"}
           {"variable", "test": "range", "type", BOUNDS, "excludes"}
    EFFECT {"variable", "effect": "eq"|"ne", "value"}
           {"variable", "effect": "in", "values"}
           {"variable", "effect": "range", "type", BOUNDS, "excludes",
            "also": [code values still allowed, read through $ref]}
    BOUNDS: whichever of minimum, maximum, exclusiveMinimum and
    exclusiveMaximum the rule states. Entries that do not parse are left out
    and reported in findings, with the codes check gives them.
    -> {"ok", "rules", "variables": {table: {name: {"topic", "file",
        "pointer"}}}, "counts", "findings", "truncated"}

fixtures PKG [--table T]
    For each table with a toy-data folder: every valid.json row passes; each
    invalid.json row fails on exactly the column its ledger case names
    (verdicts: caught, caught-with-extra, missed-wrong-column, missed-passed,
    phantom; failing rows with no case are unledgered); coverage of codes,
    bounds, special codes and rules is reported as warnings.
    -> {"ok", "tables": {table: {"valid": {"rows", "status", "findings"},
        "invalid": {"rows", "cases", "caught", "verdicts", "unledgered"},
        "coverage": {"properties": {"covered", "total"}, "rules": {"fired",
        "unfired", "caught", "uncaught"}}}}, "counts", "findings",
        "truncated"}
    verdict: {"case", "row", "column", "kind", "status", "failed_on"?,
              "rules"?}; a table without toy data is {"skipped": why}

data PKG --file F [--table T] [--format json|csv|tsv] [--max-errors N]
    Validate one data file - a JSON array of row objects, or a CSV or TSV
    export - row by row; CSV and TSV cells are typed the way QuaC types them.
    The schemify agent never runs this on real data; people may run it on
    their own files.
    -> {"ok", "table", "file", "format", "rows", "errors", "by_column",
        "by_rule", "findings", "truncated", "columns"}
    finding: {"row" (0-based record), "column", "keyword", "message",
              "hint", "rule"?, "allof_index"?, "empty_cell"?} - "column" is
              null for a finding about a whole row (a repeated row: "row" is
              the later copy) or the whole file (too few rows: "row" null too)
    columns: {name: {"title", "topic", "allowed"}} for every declared
             property, in table order; "allowed" says what the column takes

summary PKG [--out FILE]
    check + rules + fixtures (when every schema parses, meta-validates and
    resolves) + a provenance census, with a plain-English headline.
    -> {"ok", "headline", "package", "counts", "check", "rules": {"count",
        "by_kind", "by_table"}, "fixtures", "provenance": {"properties",
        "traced", "rules", "by_origin", "needs_review"}, "topics"}
    --out FILE writes the full report there - every finding and verdict, and
    "rules": {"count", "by_kind", "by_table", "items" (every rule, as rules
    prints it), "variables"} - and prints only {"ok", "headline", "package",
    "counts", "findings" (the first 20), "truncated", "topics", "report"}.

A finding of check, rules, fixtures and summary:
    {"severity": "error"|"warning"|"info", "code", "message", "hint",
     "file" (relative to PKG/schemas), "pointer", "table", "topic",
     "variable", "rule"} - keys that do not apply are left out. ok is false
    when any finding is an error.

Output is exactly one JSON object on stdout; diagnostics go to stderr. Every
findings list is capped (--max-findings, or --max-errors for data); counts
are the true totals and "truncated" says when a list was cut.

Exit codes: 0 ok; 1 ran, but the package or data file fails (ok: false);
2 usage or input error: {"ok": false, "error", "hint"}.
"""

import argparse
import csv
import io
import json
import math
import os
import re
import sys
import traceback
from collections import namedtuple
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urldefrag, urljoin, urlsplit

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry
    from referencing.jsonschema import DRAFT202012
except ImportError as _exc:  # main() reports it as one JSON object, exit 2
    Draft202012Validator = Registry = DRAFT202012 = None
    _IMPORT_ERROR = str(_exc)
else:
    _IMPORT_ERROR = None

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
PIP_FALLBACK = 'python3 -m pip install --user "jsonschema>=4.18" referencing'
SYNTHETIC_BASE = "https://schemify.invalid/schemas/"
SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CAP = 200
COMPACT_FINDINGS = 20
WALK_LIMIT = 256
REF_HOPS = 8
TITLE_LIMIT = 60
FULL_CODE_LIST = 12
SEVERITIES = ("error", "warning", "info")
MISSING = object()

SCHEMA_KEYWORDS = frozenset("""
    $schema $id $ref $anchor $dynamicRef $dynamicAnchor $defs definitions
    $comment $vocabulary type const enum properties patternProperties
    additionalProperties unevaluatedProperties required dependentRequired
    dependentSchemas propertyNames minProperties maxProperties items
    prefixItems additionalItems contains minContains maxContains minItems
    maxItems uniqueItems unevaluatedItems allOf anyOf oneOf not if then else
    minimum maximum exclusiveMinimum exclusiveMaximum multipleOf minLength
    maxLength pattern format title description default examples deprecated
    readOnly writeOnly contentEncoding contentMediaType contentSchema
""".split())
SUB_ONE = frozenset(("additionalProperties", "unevaluatedProperties", "items", "contains",
                     "propertyNames", "not", "if", "then", "else", "unevaluatedItems",
                     "contentSchema", "additionalItems"))
SUB_LIST = frozenset(("allOf", "anyOf", "oneOf", "prefixItems", "items"))
SUB_MAP = frozenset(("properties", "patternProperties", "$defs", "definitions",
                     "dependentSchemas"))

X_KEYWORDS = ("x-provenance", "x-value-kind", "x-variable-group", "x-unit", "x-universe",
              "x-derivation", "x-role")
DISCOURAGED = {
    "format": "validators do not assert it by default, so it checks nothing; use an "
              "anchored pattern",
    "default": "a data contract does not document a writer's defaults",
    "examples": "examples live in the toy data",
    "deprecated": "a data contract does not document a writer",
    "readOnly": "a data contract does not document a writer",
    "multipleOf": "it invites precision the source never stated",
    "minLength": "it invites precision the source never stated",
    "maxLength": "it invites precision the source never stated",
    "$anchor": "relative paths plus #/$defs/... are the whole addressing scheme",
    "$dynamicRef": "relative paths plus #/$defs/... are the whole addressing scheme",
}
FORBIDDEN = ("else", "dependentRequired", "dependentSchemas")
CATEGORY_FORBIDDEN = ("if", "then", "else", "allOf", "anyOf", "oneOf", "not",
                      "dependentSchemas", "dependentRequired", "additionalProperties",
                      "unevaluatedProperties")
FACETS = frozenset(("default", "title", "description", "type", "values", "sentinels",
                    "minimum", "maximum", "pattern", "unit", "universe", "derivation"))
REFERENCE_RE = re.compile(r"S[0-9]{2,}(?::[^\n|]+)?|D[0-9]{3,}")
SOURCE_CITABLE = ("active", "approved", "retired")
RULE_KEYS = ("$comment", "x-provenance", "if", "then")
RULE_COMMENT_RE = re.compile(
    r"(Skip pattern|Applicability|[A-Z][A-Za-z]*(?: [A-Za-z]+)* routing) (R[0-9]{3,}): (.+)")
RULE_PREFIX_RE = re.compile(r"(?:Skip pattern|Applicability|[A-Z][A-Za-z]*(?: [A-Za-z]+)* routing)\b")
BOUNDS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")
KIND_WORDS = {"skip": "Skip pattern", "applicability": "Applicability", "routing": "routing"}
LEDGER_KINDS = ("wrong-type", "unknown-level", "range-break", "invented-sentinel",
                "pattern-break", "skip-break", "applicability-break", "routing-break",
                "missing-key", "undeclared-column", "duplicate-row")
DUPLICATE_COLUMN = "*duplicate*"
ROW_COVER = "*row*"
RULE_CODES = frozenset(("rule-shape", "rule-comment", "rule-unguarded", "rule-dangling",
                        "rule-undeclared-code", "trigger-undeclared-level",
                        "range-trigger-sentinel", "skip-shape", "applicability-shape",
                        "missing-twin", "duplicate-rule", "allof-order", "allof-entry"))
BLOCKING_CODES = frozenset(("parse-error", "meta-invalid", "unresolved-ref"))

# jsdd's sentinel guess (json-schema-data-dictionary analyze.ts), and the
# likely-missingness words and negative codes it misses (SCHEMA-STYLE.md).
SENTINEL_WORDS = re.compile(
    r"(missing|unknown|not applicable|not assessed|not collected|not (?:on|in) (?:the )?"
    r"(?:questionnaire|survey|form)\b|no answer|no response|refus|\bdeclined\b|\bdecline to\b|"
    r"do(?:n'?t| not) know\b|prefer not|\bsuppressed\b|inapplicable|\bn\/a\b|skipped?)")
LIKELY_SENTINEL_WORDS = re.compile(
    r"\b(skip|na|dk|not asked|not ascertained|not stated|legitimate skip|valid skip)\b", re.I)
CONVENTIONAL_CODES = frozenset((666, 777, 888, 999, 6666, 7777, 8888, 9999))

# QuaC's text-cell grammar (text-cells.ts): JSON's number literal, ASCII digits.
JSON_NUMBER_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
JSON_TYPES = frozenset(("integer", "number", "string", "boolean", "null", "array", "object"))

Code = namedtuple("Code", "value kind title")


# ------------------------------------------------------------------ basics


class ValidateError(Exception):
    """A problem that stops a subcommand; main() prints {"ok": false, "error",
    "hint"} and exits 2."""

    def __init__(self, error, hint):
        Exception.__init__(self, error)
        self.error = error
        self.hint = hint


class NonFinite(object):
    """NaN, Infinity, or a number too large for a float, read from a file: not
    a JSON value, so it is reported and never validated as a number."""

    __slots__ = ("token",)

    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return self.token

    __str__ = __repr__


def esc(token):
    return str(token).replace("~", "~0").replace("/", "~1")


def unesc(token):
    return token.replace("~1", "/").replace("~0", "~")


def is_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not isinstance(value, float) or math.isfinite(value)


def is_integral(value):
    return is_number(value) and (isinstance(value, int) or value.is_integer())


def number_or_none(value):
    return value if is_number(value) else None


def nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def json_type_of(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "integer" if value.is_integer() else "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return None


def _normalized(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [_normalized(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalized(item) for key, item in value.items()}
    return value


def canonical_json(value):
    """One string per JSON value as uniqueItems compares them: keys sorted,
    1 and 1.0 alike, true and 1 apart."""
    try:
        return json.dumps(_normalized(value), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, default=repr)
    except (TypeError, ValueError, RecursionError):
        return "#unreadable-{}".format(id(value))


def literal_key(value):
    """Hashable identity of a JSON value: 1 == 1.0, true != 1."""
    if isinstance(value, bool):
        return ("b", value)
    if is_number(value):
        return ("n", value)
    if isinstance(value, str):
        return ("s", value)
    if value is None:
        return ("z", None)
    return ("j", canonical_json(value))


def dedupe_values(values):
    seen, out = set(), []
    for value in values:
        key = literal_key(value)
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out


def clip(text, limit=300):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def show(value, limit=60):
    if isinstance(value, NonFinite):
        return value.token
    try:
        text = json.dumps(value, ensure_ascii=False, default=repr)
    except (TypeError, ValueError, RecursionError):
        text = "(unprintable value)"
    return clip(text, limit)


def show_list(values, limit=8):
    shown = ", ".join(show(v) for v in values[:limit])
    return shown + (", …" if len(values) > limit else "")


def joined(values, last="and"):
    shown = [show(v) for v in values]
    return shown[0] if len(shown) == 1 else "{} {} {}".format(", ".join(shown[:-1]), last, shown[-1])


def plural(count, word, many=None):
    return "{} {}".format(count, word if count == 1 else (many or word + "s"))


def cap_first(text):
    return text[:1].upper() + text[1:]


def value_kind(node):
    kind = node.get("x-value-kind") if isinstance(node, dict) else None
    return kind if kind in ("sentinel", "value") else None


def type_names(node):
    kind = node.get("type") if isinstance(node, dict) else None
    names = kind if isinstance(kind, list) else [kind]
    return [name for name in names if isinstance(name, str)]


def is_typed(node):
    return isinstance(node, dict) and "const" not in node and "enum" not in node and (
        "type" in node or "pattern" in node)


def numeric_types(node):
    return set(type_names(node)) & {"integer", "number"}


def within(value, node):
    """Whether a number falls inside a typed branch's bounds and type."""
    if not is_number(value):
        return False
    kinds = numeric_types(node)
    if not kinds or ("number" not in kinds and not is_integral(value)):
        return False
    lo, hi = number_or_none(node.get("minimum")), number_or_none(node.get("maximum"))
    xlo = number_or_none(node.get("exclusiveMinimum"))
    xhi = number_or_none(node.get("exclusiveMaximum"))
    return ((lo is None or value >= lo) and (hi is None or value <= hi)
            and (xlo is None or value > xlo) and (xhi is None or value < xhi))


def guard_keys(node):
    """Codes a typed branch's not: {enum} (or not: {const}) excludes."""
    inner = node.get("not") if isinstance(node, dict) else None
    keys = set()
    if isinstance(inner, dict):
        if isinstance(inner.get("enum"), list):
            keys.update(literal_key(v) for v in inner["enum"])
        if "const" in inner:
            keys.add(literal_key(inner["const"]))
    return keys


def has_scheme(text):
    try:
        return bool(urlsplit(text).scheme)
    except ValueError:
        return False


def safe_join(base, ref):
    try:
        return urldefrag(urljoin(base, ref))[0]
    except ValueError:
        return base


# ------------------------------------------------------------------ JSON in


def _parse_float(text):
    value = float(text)
    return value if math.isfinite(value) else NonFinite(text)


def read_json(path):
    """(value, None), or (None, (problem, line, column)); never raises. NaN,
    Infinity and overflowing numbers come back as NonFinite markers."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        return None, ("could not be read ({})".format(exc.strerror or exc), None, None)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        line = raw[: exc.start].count(b"\n") + 1
        return None, ("is not UTF-8 text (byte 0x{:02X} on line {})".format(
            raw[exc.start], line), line, None)
    try:
        return json.loads(text, parse_constant=NonFinite, parse_float=_parse_float), None
    except json.JSONDecodeError as exc:
        return None, ("is not valid JSON: {} at line {}, column {}".format(
            exc.msg, exc.lineno, exc.colno), exc.lineno, exc.colno)
    except RecursionError:
        return None, ("nests too deeply to read", None, None)
    except ValueError as exc:
        return None, ("could not be read as JSON ({})".format(exc), None, None)


def find_nonfinite(value):
    """(pointer, token) of a NonFinite inside value, or None."""
    stack = [(value, "")]
    while stack:
        node, here = stack.pop()
        if isinstance(node, NonFinite):
            return here, node.token
        if isinstance(node, dict):
            stack.extend((item, here + "/" + esc(key)) for key, item in node.items())
        elif isinstance(node, list):
            stack.extend((item, "{}/{}".format(here, i)) for i, item in enumerate(node))
    return None


# ---------------------------------------------------------------- findings

WHERE_KEYS = ("file", "pointer", "table", "topic", "variable", "rule")


def finding(severity, code, message, hint, **where):
    item = {"severity": severity, "code": code, "message": clip(message), "hint": hint}
    for key in WHERE_KEYS:
        if where.get(key) is not None:
            item[key] = where[key]
    for key in sorted(where):
        if key not in item and where[key] is not None:
            item[key] = where[key]
    return item


def tally(findings):
    counts = dict.fromkeys(SEVERITIES, 0)
    for item in findings:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1
    return counts


def by_severity(findings):
    rank = {name: i for i, name in enumerate(SEVERITIES)}
    return sorted(findings, key=lambda item: rank.get(item.get("severity"), len(rank)))


def cap_list(items, cap):
    if cap is None:
        return list(items), False
    return list(items[:cap]), len(items) > cap


# ------------------------------------------------------------- schema walks


def schema_children(node, pointer):
    """(subschema, pointer) for every object at a schema position of node -
    never into const, enum, default, examples, or x-* values."""
    out = []
    for key, value in node.items():
        if key in SUB_ONE and isinstance(value, dict):
            out.append((value, pointer + "/" + esc(key)))
        elif key in SUB_LIST and isinstance(value, list):
            out.extend((sub, "{}/{}/{}".format(pointer, key, i))
                       for i, sub in enumerate(value) if isinstance(sub, dict))
        elif key in SUB_MAP and isinstance(value, dict):
            out.extend((sub, "{}/{}/{}".format(pointer, esc(key), esc(name)))
                       for name, sub in value.items() if isinstance(sub, dict))
    return out


def iter_schema(root, pointer="", skip=frozenset()):
    """(node, pointer) for every schema object in document order."""
    stack = [(root, pointer, 0)]
    while stack:
        node, here, depth = stack.pop()
        if not isinstance(node, dict) or id(node) in skip:
            continue
        yield node, here
        if depth < WALK_LIMIT:
            stack.extend(reversed([(sub, where, depth + 1)
                                   for sub, where in schema_children(node, here)]))


def crawl_safely(pairs):
    """A crawled registry; resources whose shape referencing cannot crawl (a
    meta-invalid file) are left out rather than sinking the rest."""
    try:
        return Registry().with_resources(pairs).crawl()
    except Exception:  # referencing assumes meta-valid shapes
        pass
    good = []
    for uri, resource in pairs:
        try:
            Registry().with_resource(uri, resource).crawl()
        except Exception:
            continue
        good.append((uri, resource))
    try:
        return Registry().with_resources(good).crawl()
    except Exception:
        return Registry().with_resources(good)


def unresolved_reason(exc):
    name = type(exc).__name__
    return {
        "PointerToNowhere": "the JSON pointer after # leads nowhere in the target file",
        "NoSuchAnchor": "the target file has no such anchor",
        "InvalidAnchor": "the part after # is neither a JSON pointer nor an anchor",
        "NoSuchResource": "no schema file answers to that address",
        "Unretrievable": "no schema file answers to that address",
        "Unresolvable": "no schema file answers to that address",
    }.get(name, "{}: {}".format(name, clip(exc, 100)))


# ----------------------------------------------------------------- package


class Package(object):
    """Every JSON file under PKG/schemas: parsed, classified, and registered
    under its $id and under its path beneath every $id base the package uses,
    so references resolve even when bases are mixed."""

    def __init__(self, root):
        self.root = root
        self.schemas = root / "schemas"
        self.files = []
        self.docs = {}
        self.uri = {}
        self.bases = []
        self.load_findings = []
        self.doc_of = {}
        self.node_at = {}
        self._scan()
        self._register()

    def _scan(self):
        for folder, dirnames, filenames in os.walk(str(self.schemas)):
            dirnames[:] = sorted(name for name in dirnames if not name.startswith("."))
            for name in sorted(filenames):
                if name.endswith(".json") and not name.startswith("."):
                    rel = (Path(folder) / name).relative_to(self.schemas).as_posix()
                    self.files.append(rel)
        self.files.sort()
        for rel in self.files:
            doc, problem = read_json(self.schemas / rel)
            if problem is not None:
                message, line, column = problem
                self.load_findings.append(finding(
                    "error", "parse-error", "{} {}.".format(rel, message),
                    "Make the file strict JSON in UTF-8: check the quote, comma or bracket "
                    "at that position (re-save it as UTF-8 if it is not).",
                    file=rel, line=line, column=column))
                continue
            bad = find_nonfinite(doc)
            if bad is not None:
                self.load_findings.append(finding(
                    "error", "parse-error",
                    "{} holds {} at {}, which is not JSON.".format(rel, bad[1], bad[0] or "/"),
                    "JSON has no NaN or Infinity, and numbers must fit a 64-bit float; "
                    "write the number out, or use a declared code.", file=rel, pointer=bad[0]))
                continue
            if not isinstance(doc, dict) or not SCHEMA_KEYWORDS.intersection(doc):
                self.load_findings.append(finding(
                    "warning", "not-a-schema",
                    "{} is under schemas/ but is not a JSON Schema object.".format(rel),
                    "Everything under schemas/ is a schema file: move this file out, or "
                    "give it its schema keywords.", file=rel))
                continue
            self.docs[rel] = doc

    def _register(self):
        bases = set()
        for rel, doc in self.docs.items():
            own = SYNTHETIC_BASE + quote(rel)
            canonical = own
            sid = doc.get("$id")
            if nonempty_str(sid):
                joined = safe_join(own, sid.strip())
                if joined:
                    canonical = joined
                    if has_scheme(sid.strip()) and joined.endswith("/" + rel):
                        bases.add(joined[: len(joined) - len(rel)])
            self.uri[rel] = canonical
        bases.add(SYNTHETIC_BASE)
        self.bases = sorted(bases)
        pairs = []
        for rel, doc in sorted(self.docs.items()):
            resource = DRAFT202012.create_resource(doc)
            uris = {self.uri[rel], SYNTHETIC_BASE + quote(rel)}
            uris.update(base + quote(rel) for base in bases)
            pairs.extend((uri, resource) for uri in sorted(uris))
            self.doc_of[id(doc)] = rel
            self._index(rel, doc)
        self.registry = crawl_safely(pairs)

    def _index(self, rel, doc):
        stack = [(doc, "")]
        while stack:
            node, here = stack.pop()
            if isinstance(node, dict):
                self.node_at[id(node)] = (rel, here)
                stack.extend((item, here + "/" + esc(key)) for key, item in node.items()
                             if isinstance(item, (dict, list)))
            elif isinstance(node, list):
                self.node_at[id(node)] = (rel, here)
                stack.extend((item, "{}/{}".format(here, i)) for i, item in enumerate(node)
                             if isinstance(item, (dict, list)))

    def lookup(self, base_uri, ref):
        """(Resolved, None) or (None, why) for a $ref written under base_uri."""
        try:
            return self.registry.resolver(base_uri=base_uri).lookup(ref), None
        except Exception as exc:  # Unresolvable, or odd input referencing trips on
            return None, unresolved_reason(exc)

    def lookup_from(self, resolver, ref):
        try:
            return resolver.lookup(ref), None
        except Exception as exc:
            return None, unresolved_reason(exc)

    def resolver(self, base_uri):
        return self.registry.resolver(base_uri=base_uri)


# -------------------------------------------------------------- provenance


class Provenance(object):
    """PKG/provenance.json: the sources and decisions x-provenance may cite."""

    def __init__(self, root):
        self.path = root / "provenance.json"
        self.present = self.path.is_file()
        self.usable = False
        self.sources, self.decisions = {}, {}
        self.findings = []
        if not self.present:
            return
        doc, problem = read_json(self.path)
        where = {"file": "../provenance.json"}
        hint = "Rebuild it with `schemify.py build`; it is written, never edited by hand."
        if problem is not None:
            self.findings.append(finding("error", "parse-error",
                                         "provenance.json {}.".format(problem[0]), hint,
                                         line=problem[1], column=problem[2], **where))
            return
        problems = []
        if not isinstance(doc, dict):
            problems.append("it is not an object")
        else:
            version = doc.get("schemifyProvenance")
            if isinstance(version, bool) or version != 1:
                problems.append("schemifyProvenance is {}, not 1".format(show(version)))
            for key in ("sources", "decisions"):
                if key in doc and not isinstance(doc[key], dict):
                    problems.append("{} is not an object".format(key))
        if problems:
            self.findings.append(finding("error", "provenance-file",
                                         "provenance.json is not in the expected format: {}."
                                         .format("; ".join(problems)), hint, **where))
            return
        self.sources = doc.get("sources") or {}
        self.decisions = doc.get("decisions") or {}
        self.usable = True

    def entry(self, ref_id):
        table = self.sources if ref_id.startswith("S") else self.decisions
        value = table.get(ref_id, MISSING)
        return value if value is MISSING or isinstance(value, dict) else {}

    def origin(self, ref):
        ref_id = ref.split(":", 1)[0]
        if not self.usable:
            return "unknown"
        entry = self.entry(ref_id)
        if entry is MISSING:
            return "unknown"
        if ref_id.startswith("S"):
            kind = entry.get("kind")
            return kind if kind in ("document", "web") else "unknown"
        by = entry.get("by")
        return "person" if by in ("author", "steward") else ("agent" if by == "agent"
                                                             else "unknown")

    def needs_review(self, ref):
        ref_id = ref.split(":", 1)[0]
        if not self.usable or not ref_id.startswith("D"):
            return False
        entry = self.entry(ref_id)
        return entry is not MISSING and entry.get("needsReview") is True


# ---------------------------------------------------------- value profiles


def ref_def_name(ref):
    fragment = ref.partition("#")[2]
    parts = [part for part in fragment.split("/") if part]
    return unesc(parts[-1]) if parts else ""


def normalize_label(text):
    text = text.lower().replace("‘", "'").replace("’", "'").replace("ʼ", "'")
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", text)).strip()


def _label_text(label, description):
    label = (label or "").strip() if isinstance(label, str) else ""
    head = re.sub(r"\([^()]*\)", " ", label).strip()
    letters = re.compile(r"[^\W\d_]")
    if letters.search(head):
        return head
    if letters.search(label):
        return label
    return description if isinstance(description, str) else ""


def jsdd_sentinel(value, label, description=None, ref=None):
    """Would the data dictionary page file this code under missing values?"""
    if ref and SENTINEL_WORDS.search(normalize_label(ref_def_name(ref))):
        return True
    text = _label_text(label, description)
    if text.strip() and SENTINEL_WORDS.search(normalize_label(text)):
        return True
    return is_number(value) and value in CONVENTIONAL_CODES


def likely_sentinel(value, label):
    if isinstance(label, str) and LIKELY_SENTINEL_WORDS.search(normalize_label(label)):
        return True
    return is_number(value) and value < 0


def value_profile(pkg, node, resolver):
    """What a property (or definition) admits: {"form": "codes"|"measure"|
    "other", "codes": [Code], "typed": [typed branch objects]}."""
    profile = {"form": "other", "codes": [], "typed": []}
    hops = 0
    while (isinstance(node, dict) and isinstance(node.get("$ref"), str) and hops < REF_HOPS
           and not any(key in node for key in ("oneOf", "anyOf", "const", "enum", "type"))):
        resolved, _ = pkg.lookup_from(resolver, node["$ref"])
        if resolved is None:
            return profile
        node, resolver = resolved.contents, resolved.resolver
        hops += 1
    if not isinstance(node, dict):
        return profile
    branched = False
    for keyword in ("oneOf", "anyOf"):
        if isinstance(node.get(keyword), list):
            branched = True
            for branch in node[keyword]:
                _profile_branch(pkg, branch, resolver, profile, True)
    if not branched:
        _profile_branch(pkg, node, resolver, profile, False)
    if any(numeric_types(t) for t in profile["typed"]):
        profile["form"] = "measure"
    elif profile["codes"] and not profile["typed"]:
        profile["form"] = "codes"
    return profile


def _profile_branch(pkg, branch, resolver, profile, follow):
    if not isinstance(branch, dict):
        return
    own_kind = value_kind(branch)
    own_title = branch.get("title") if nonempty_str(branch.get("title")) else None
    target = branch
    if follow and isinstance(branch.get("$ref"), str):
        resolved, _ = pkg.lookup_from(resolver, branch["$ref"])
        if resolved is None or not isinstance(resolved.contents, dict):
            return
        target = resolved.contents
    title = own_title or (target.get("title") if nonempty_str(target.get("title")) else None)
    kind = own_kind or value_kind(target)
    if "const" in target:
        profile["codes"].append(Code(target["const"], kind, title))
    elif isinstance(target.get("enum"), list):
        profile["codes"].extend(Code(value, kind, None) for value in target["enum"])
    elif is_typed(target):
        profile["typed"].append(target)


def special_codes(profile):
    """Codes meaning no substantive answer: marked sentinel, or unmarked
    inside a measure (where every code is a special code)."""
    if profile["form"] == "measure":
        return [code for code in profile["codes"] if code.kind != "value"]
    return [code for code in profile["codes"] if code.kind == "sentinel"]


def describe_typed(node):
    kinds = numeric_types(node)
    if kinds:
        noun = "a number" if "number" in kinds else "a whole number"
        lo, hi = number_or_none(node.get("minimum")), number_or_none(node.get("maximum"))
        xlo = number_or_none(node.get("exclusiveMinimum"))
        xhi = number_or_none(node.get("exclusiveMaximum"))
        if lo is not None and hi is not None:
            text = "{} from {} to {}".format(noun, show(lo), show(hi))
        else:
            parts = []
            if lo is not None:
                parts.append("at least {}".format(show(lo)))
            if xlo is not None:
                parts.append("above {}".format(show(xlo)))
            if hi is not None:
                parts.append("at most {}".format(show(hi)))
            if xhi is not None:
                parts.append("below {}".format(show(xhi)))
            text = noun + (" " + " and ".join(parts) if parts else "")
        return text
    names = type_names(node)
    if "string" in names or "pattern" in node:
        return ("text matching {}".format(node["pattern"]) if nonempty_str(node.get("pattern"))
                else "text")
    if "boolean" in names:
        return "true or false"
    return "a value of type {}".format(" or ".join(names)) if names else "a value"


def code_text(code):
    return "{} ({})".format(show(code.value), code.title) if code.title else show(code.value)


def describe_allowed(profile):
    parts = [describe_typed(node) for node in profile["typed"]]
    codes, seen = [], set()
    for code in profile["codes"]:
        if literal_key(code.value) not in seen:
            seen.add(literal_key(code.value))
            codes.append(code)
    if codes:
        listed = ", ".join(code_text(code) for code in codes[:10])
        if len(codes) > 10:
            listed += ", … ({} codes in all)".format(len(codes))
        lead = "one of " if len(codes) > 1 else ""
        parts.append(("or " if parts else "") + lead + listed)
    return ", ".join(parts) if parts else None


def required_values(profile):
    """The values valid.json must show for a property to count as covered."""
    if profile["form"] == "codes":
        codes = profile["codes"]
        if len(codes) <= FULL_CODE_LIST:
            return dedupe_values([code.value for code in codes])
        wanted = [codes[0].value, codes[-1].value]
        wanted.extend(code.value for code in codes if code.kind == "sentinel")
        return dedupe_values(wanted)
    if profile["form"] == "measure":
        wanted = []
        for node in profile["typed"]:
            if numeric_types(node):
                wanted.extend(node[key] for key in ("minimum", "maximum")
                              if is_number(node.get(key)))
        wanted.extend(code.value for code in special_codes(profile))
        return dedupe_values(wanted)
    return None


def json_types(pkg, node, resolver, depth=0, seen=frozenset()):
    """The JSON types a value can have and still pass node, as QuaC derives
    them (value-spec.ts): anyOf/oneOf unite, $ref/allOf/type/const/enum
    intersect; None means unconstrained."""
    if isinstance(node, bool):
        return None if node else set()
    if not isinstance(node, dict) or depth > 12 or id(node) in seen:
        return None
    seen = seen | {id(node)}
    contributions = []
    if isinstance(node.get("$ref"), str):
        resolved, _ = pkg.lookup_from(resolver, node["$ref"])
        contributions.append(None if resolved is None else json_types(
            pkg, resolved.contents, resolved.resolver, depth + 1, seen))
    kind = node.get("type")
    if isinstance(kind, (str, list)):
        names = kind if isinstance(kind, list) else [kind]
        contributions.append({name for name in names if name in JSON_TYPES})
    if "const" in node:
        found = json_type_of(node["const"])
        contributions.append(set() if found is None else {found})
    if isinstance(node.get("enum"), list):
        contributions.append({t for t in map(json_type_of, node["enum"]) if t is not None})
    for keyword in ("anyOf", "oneOf"):
        if isinstance(node.get(keyword), list):
            union, unconstrained = set(), False
            for branch in node[keyword]:
                found = json_types(pkg, branch, resolver, depth + 1, seen)
                if found is None:
                    unconstrained = True
                else:
                    union |= found
            contributions.append(None if unconstrained else union)
    if isinstance(node.get("allOf"), list):
        contributions.extend(json_types(pkg, branch, resolver, depth + 1, seen)
                             for branch in node["allOf"])
    constrained = [c for c in contributions if c is not None]
    if not constrained:
        return None
    result = set(constrained[0])
    for other in constrained[1:]:
        result = intersect_types(result, other)
    return result


def intersect_types(a, b):
    out = {t for t in a if t in b or (t == "integer" and "number" in b)}
    if "number" in a and "integer" in b:
        out.add("integer")
    return out


def read_text_cell(text, types):
    """One non-empty CSV/TSV cell as the JSON value it spells, given the
    column's admitted types (QuaC text-cells.ts); text otherwise."""
    anything = not types

    def allows(name):
        return anything or name in types

    trimmed = text.strip()
    if (allows("number") or allows("integer")) and JSON_NUMBER_RE.fullmatch(trimmed):
        value = None
        if "." not in trimmed and "e" not in trimmed and "E" not in trimmed:
            try:
                value = int(trimmed)
            except ValueError:
                value = None
        if value is None:
            try:
                value = float(trimmed)
            except (ValueError, OverflowError):
                value = None
        if value is None or not is_number(value):
            return text
        if not allows("number") and not is_integral(value) and allows("string"):
            return text
        if isinstance(value, float) and value.is_integer() and allows("integer"):
            return int(value)
        return value
    if allows("boolean") and trimmed.lower() in ("true", "false"):
        return trimmed.lower() == "true"
    if (allows("array") or allows("object")) and trimmed[:1] in ("[", "{"):
        try:
            parsed = json.loads(trimmed, parse_constant=NonFinite, parse_float=_parse_float)
        except (ValueError, RecursionError):
            parsed = MISSING
        if (isinstance(parsed, list) and allows("array")) or (
                isinstance(parsed, dict) and allows("object")):
            return parsed
    return text


# ----------------------------------------------------------------- tables


class Prop(object):
    """One row property, read from its own category file."""

    def __init__(self, an, table, name, rel, topic, schema):
        self.an = an
        self.table = table
        self.name = name
        self.file = rel
        self.topic = topic
        self.schema = schema
        self.pointer = "/properties/" + esc(name)
        self.uri = an.pkg.uri[rel]
        self._validator = None
        self._profile = None
        self._types = MISSING

    def admits(self, value):
        """True/False: does the property's own schema accept value; None when
        that cannot be told (an unresolvable schema)."""
        if self._validator is None:
            target = "{}#{}".format(self.uri, quote(self.pointer, safe="/~"))
            self._validator = Draft202012Validator({"$ref": target},
                                                   registry=self.an.pkg.registry)
        try:
            return bool(self._validator.is_valid(value))
        except Exception:
            return None

    def profile(self):
        if self._profile is None:
            self._profile = value_profile(self.an.pkg, self.schema,
                                          self.an.pkg.resolver(self.uri))
        return self._profile

    def column_types(self):
        if self._types is MISSING:
            self._types = json_types(self.an.pkg, self.schema, self.an.pkg.resolver(self.uri))
        return self._types


class TableModel(object):
    def __init__(self, name, mother):
        self.name = name
        self.mother = mother
        self.doc = None
        self.uri = None
        self.items = None
        self.categories = []
        self.unresolved_categories = []
        self.category_entries = set()
        self.props = {}
        self.rule_entries = []
        self.rules = []
        self.broken = None


class RuleEntry(object):
    """One rule entry of a mother's items.allOf, parsed against the grammar."""

    def __init__(self, model, index, node):
        self.table = model.name
        self.file = model.mother
        self.index = index
        self.pointer = "/items/allOf/{}".format(index)
        self.node = node
        self.id = self.kind = self.domain = self.comment = self.reading = None
        self.provenance = None
        self.when = self.then = self.mode = None
        self.gates = []
        self.targets = []
        self.grammar_ok = True

    def label(self):
        if self.id is None:
            return "the rule at {}".format(self.pointer)
        if self.kind == "routing":
            return "{} ({} routing)".format(self.id, self.domain)
        return "{} ({})".format(self.id, KIND_WORDS.get(self.kind, "rule"))

    def half(self):
        return "{}:{}".format(self.id or "allOf/{}".format(self.index), self.kind or "rule")

    def public(self):
        return {"table": self.table, "id": self.id, "kind": self.kind, "domain": self.domain,
                "index": self.index, "file": self.file, "pointer": self.pointer,
                "comment": self.comment, "reading": self.reading,
                "provenance": self.provenance, "when": self.when, "then": self.then}


# ---------------------------------------------------------------- analysis


TEST_HINT = ('A test is {"const": v}, {"enum": [v1, v2, ...]}, {"not": {"const": v}}, '
             '{"not": {"enum": [...]}}, or {"type": "integer"|"number", "minimum", "maximum", '
             '"exclusiveMinimum", "exclusiveMaximum", "not": {"enum": [sentinels]}} with at '
             'least one bound (SKIP-LOGIC.md, The canonical form).')
EFFECT_HINT = ('An effect is {"const": c}, {"not": {"const": c}}, {"enum": [...]}, or '
               '{"anyOf": [{"type", bounds}, sentinel consts or $refs to them]} - no other '
               'keyword, no nested if, and a $ref only to a sentinel definition '
               '(SKIP-LOGIC.md, The canonical form).')
CLAUSE_HINT = ('Write the if as {"required": [gates], "properties": {gate: test}} - several '
               'gates in one clause all must hold - or {"anyOf": [clause, clause, ...]} for '
               '"any of these" (SKIP-LOGIC.md, The canonical form).')
THEN_HINT = ('Write the then as {"properties": {target: effect, ...}}, or {"anyOf": '
             '[{"required": [t], "properties": {t: effect}}, ...]} for "at least one of these"; '
             'the reverse direction or a second condition is its own rule.')
PROVENANCE_HINT = ('x-provenance maps facets (default, title, description, type, values, '
                   'value:<code>, sentinels, minimum, maximum, pattern, unit, universe, '
                   'derivation) to a reference - S01, S01:<locator> or D014 - or a list of '
                   'them (LEDGER-FORMAT.md, References).')


class Analysis(object):
    """check, kept: every finding plus the models rules, fixtures, data and
    summary build on."""

    def __init__(self, pkg, prov, label):
        self.pkg = pkg
        self.prov = prov
        self.label = label
        self.findings = list(pkg.load_findings) + list(prov.findings)
        self.tables = {}
        self.mother_table = {}
        self.category_table = {}
        self.ref_sites = []
        self.deps = {}
        self.meta_broken = set()
        self.ref_broken = set()
        self.reported = set()
        self.rule_nodes = set()
        self.prop_by_id = {}
        self.def_by_id = {}
        self.prov_ok = {}
        self.prov_refs = []
        self._seen = set()
        self._meta = None

    # -- plumbing

    def add(self, severity, code, message, hint, dedupe=None, **where):
        if dedupe is not None:
            if dedupe in self._seen:
                return
            self._seen.add(dedupe)
        self.findings.append(finding(severity, code, message, hint, **where))

    def owner(self, rel):
        """(table, topic) of a category file, by reference or by its path."""
        if rel in self.category_table:
            return self.category_table[rel]
        parts = rel.split("/")
        if len(parts) == 3 and parts[1] == "categories" and parts[0] in self.tables:
            return parts[0], PurePosixPath(rel).stem
        return None

    def where(self, rel, pointer=None, **extra):
        where = {"file": rel, "pointer": pointer or None}
        owner = self.owner(rel)
        if owner is not None:
            where["table"], where["topic"] = owner
            if pointer and pointer.startswith("/properties/"):
                where["variable"] = unesc(pointer.split("/")[2])
        elif rel in self.mother_table:
            where["table"] = self.mother_table[rel]
        where.update(extra)
        return where

    def locate(self, item):
        """Add table, topic and variable to a finding made before the tables
        were known (parse, meta-schema, $id and $ref findings), and the topic
        of the variable a mother's finding names (rule findings)."""
        rel, extra = item.get("file"), {}
        if rel and "table" not in item and not rel.startswith("../"):
            where = self.where(rel, item.get("pointer"))
            extra = {key: where[key] for key in ("table", "topic", "variable")
                     if where.get(key) is not None}
        model = self.tables.get(item.get("table") or extra.get("table"))
        prop = model.props.get(item.get("variable") or extra.get("variable")) if model else None
        if prop is not None and "topic" not in item and "topic" not in extra:
            extra["topic"] = prop.topic
        if not extra:
            return item
        rest = {key: value for key, value in item.items()
                if key not in ("severity", "code", "message", "hint")}
        rest.update(extra)
        return finding(item["severity"], item["code"], item["message"], item["hint"], **rest)

    def run(self):
        self.lint_meta()
        self.lint_ids()
        self.walk_refs()
        self.build_tables()
        for rel, (table, topic) in sorted(self.category_table.items()):
            self.lint_category(rel, table, topic)
        self.lint_defs()
        for model in self.tables.values():
            for index, node in model.rule_entries:
                self.parse_rule(model, index, node)
            self.check_rule_ids(model)
        self.lint_provenance()
        self.scan_keywords()
        self.findings = [self.locate(item) for item in self.findings]
        if not self.tables:
            self.add("error", "no-tables",
                     "No table found: no folder under schemas/ holds a *.schema.json mother.",
                     "Each table is schemas/<table>/<table>.schema.json, with its category "
                     "files in schemas/<table>/categories/.")
        return self

    def blocking(self, model):
        """Why rows cannot be validated against this table, or None."""
        if model.broken:
            return model.broken
        todo, seen = [model.mother], set()
        while todo:
            rel = todo.pop()
            if rel in seen:
                continue
            seen.add(rel)
            todo.extend(self.deps.get(rel, ()))
        bad = sorted(rel for rel in seen if rel in self.meta_broken or rel in self.ref_broken)
        if bad:
            return "schema errors in {}".format(", ".join(bad))
        try:
            self.pkg.registry.resolver(base_uri=model.uri).lookup("#/items")
        except Exception:
            return "{} cannot be loaded as a schema".format(model.mother)
        return None

    # -- files, ids, references

    def lint_meta(self):
        if self._meta is None:
            self._meta = Draft202012Validator(Draft202012Validator.META_SCHEMA,
                                              format_checker=Draft202012Validator.FORMAT_CHECKER)
        for rel, doc in sorted(self.pkg.docs.items()):
            try:
                errors = sorted(self._meta.iter_errors(doc),
                                key=lambda e: [str(t) for t in e.absolute_path])
            except RecursionError:
                errors = None
            if errors is None:
                self.meta_broken.add(rel)
                self.add("error", "meta-invalid", "{} nests too deeply to check.".format(rel),
                         "Flatten the schema.", **self.where(rel))
            else:
                seen = set()
                for error in errors:
                    pointer = "".join("/" + esc(t) for t in error.absolute_path)
                    if (pointer, error.message) in seen:
                        continue
                    seen.add((pointer, error.message))
                    self.meta_broken.add(rel)
                    self.add("error", "meta-invalid",
                             "{} is not a valid draft 2020-12 schema at {}: {}".format(
                                 rel, pointer or "/", error.message),
                             "Fix that keyword so the file is valid JSON Schema (draft 2020-12).",
                             **self.where(rel, pointer))
            if doc.get("$schema") != DRAFT_2020_12:
                self.add("error", "wrong-draft",
                         "{}: $schema is {}.".format(rel, show(doc.get("$schema"))
                                                     if "$schema" in doc else "missing"),
                         'Set "$schema": "{}" in every file.'.format(DRAFT_2020_12),
                         **self.where(rel, "/$schema"))

    def lint_ids(self):
        seen, bases, base_of = {}, {}, {}
        for rel, doc in sorted(self.pkg.docs.items()):
            sid = doc.get("$id")
            if not nonempty_str(sid):
                self.add("warning", "id-missing", "{} has no $id.".format(rel),
                         "Give it an absolute $id: the package's base followed by its path "
                         "under schemas/ ({}).".format(rel), **self.where(rel))
                continue
            canonical = self.pkg.uri[rel]
            if canonical in seen:
                self.add("error", "duplicate-id",
                         "{} has the $id {} already used by {}.".format(rel, sid, seen[canonical]),
                         "Every file needs its own $id, ending with its own path under schemas/.",
                         **self.where(rel, "/$id"))
            else:
                seen[canonical] = rel
            if not has_scheme(sid.strip()) or not canonical.endswith("/" + rel):
                why = ("is not an absolute URI" if not has_scheme(sid.strip())
                       else "does not end with the file's path under schemas/ ({})".format(rel))
                self.add("warning", "id-path-mismatch", "{}: $id {} {}.".format(rel, sid, why),
                         "Set the $id to <package base>{} so relative $refs resolve the same "
                         "by path and by $id.".format(rel), **self.where(rel, "/$id"))
                continue
            base = canonical[: len(canonical) - len(rel)]
            bases[base] = bases.get(base, 0) + 1
            base_of[rel] = base
        if len(bases) > 1:
            # The base most files use; on a tie, the one the mothers use.
            mothers = {}
            for rel, base in base_of.items():
                if rel.count("/") == 1 and rel.endswith(".schema.json"):
                    mothers[base] = mothers.get(base, 0) + 1
            dominant = sorted(bases, key=lambda b: (-bases[b], -mothers.get(b, 0), b))[0]
            for rel, base in sorted(base_of.items()):
                if base != dominant:
                    self.add("warning", "mixed-id-bases",
                             "{}: $id base {} differs from the package's base {}.".format(
                                 rel, base, dominant),
                             "Use one base (project.json idBase) for every file; validation "
                             "copes, but other tools resolve by $id.", **self.where(rel, "/$id"))

    def walk_refs(self):
        for rel, doc in sorted(self.pkg.docs.items()):
            deps = self.deps.setdefault(rel, set())
            stack = [(doc, "", self.pkg.uri[rel], 0)]
            while stack:
                node, here, base, depth = stack.pop()
                if here and nonempty_str(node.get("$id")):
                    base = safe_join(base, node["$id"].strip())
                ref = node.get("$ref")
                if isinstance(ref, str):
                    resolved, why = self.pkg.lookup(base, ref)
                    if resolved is None:
                        self.ref_broken.add(rel)
                        self.add("error", "unresolved-ref",
                                 "{}: $ref {} does not resolve: {}.".format(rel, show(ref), why),
                                 "Point it at an existing file and definition, written relative "
                                 "to this file (\"../../common/defs.json#/$defs/dont_know\"); "
                                 "every $id must mirror its file's path under schemas/.",
                                 **self.where(rel, here + "/$ref"))
                    else:
                        target = self.pkg.node_at.get(id(resolved.contents))
                        if target is not None:
                            deps.add(target[0])
                        self.ref_sites.append({"file": rel, "pointer": here,
                                               "has_prov": "x-provenance" in node,
                                               "target": id(resolved.contents)})
                if depth < WALK_LIMIT:
                    stack.extend(reversed([(sub, where, base, depth + 1)
                                           for sub, where in schema_children(node, here)]))

    # -- tables

    def build_tables(self):
        found = {}
        for rel in self.pkg.files:
            parts = rel.split("/")
            if len(parts) == 2 and parts[0] != "common" and parts[1].endswith(".schema.json"):
                found.setdefault(parts[0], []).append(rel)
        for table in sorted(found):
            rels = sorted(found[table])
            preferred = "{0}/{0}.schema.json".format(table)
            mother = preferred if preferred in rels else rels[0]
            self.tables[table] = TableModel(table, mother)
            self.mother_table[mother] = table
            if len(rels) > 1:
                self.add("error", "table-layout",
                         "{}/ holds {} *.schema.json files ({}); a table folder holds exactly one "
                         "mother.".format(table, len(rels), ", ".join(rels)),
                         "Keep {} as the mother; move other schemas to categories/ or common/."
                         .format(mother), file=table + "/", table=table)
        mothers = set(self.mother_table)
        for table, model in sorted(self.tables.items()):
            doc = self.pkg.docs.get(model.mother)
            if doc is None:
                model.broken = "{} could not be read as a schema".format(model.mother)
                continue
            model.doc = doc
            model.uri = self.pkg.uri[model.mother]
            self.lint_mother(model)
            self.read_allof(model, mothers)
            self.collect_properties(model)
        for rel in sorted(self.pkg.docs):
            parts = rel.split("/")
            if (len(parts) == 3 and parts[1] == "categories" and parts[0] in self.tables
                    and rel not in self.category_table):
                self.category_table[rel] = (parts[0], PurePosixPath(rel).stem)
                self.add("warning", "orphan-category",
                         "{} is not referenced by {}'s mother.".format(rel, parts[0]),
                         'Add {{"$ref": "categories/{}"}} to the mother\'s items.allOf, before '
                         'the rules - until then its properties are never validated - or delete '
                         'it.'.format(parts[2]), **self.where(rel))

    def lint_mother(self, model):
        doc, rel = model.doc, model.mother

        def shape(message, hint, pointer):
            self.add("error", "mother-shape", "{}: {}".format(rel, message), hint,
                     **self.where(rel, pointer))

        if doc.get("type") != "array":
            shape('the root type is {}; a mother is "type": "array".'.format(
                show(doc.get("type")) if "type" in doc else "missing"),
                'Set "type": "array": the table is an array whose every element is one row.',
                "/type")
        items = doc.get("items")
        if not isinstance(items, dict):
            shape("items is not an object.",
                  'Give items {"type": "object", "title", "allOf": [category $refs, then rules], '
                  '"unevaluatedProperties": false}.', "/items")
            model.broken = "{}'s items is not an object".format(rel)
        else:
            model.items = items
            if items.get("type") != "object":
                shape('items.type is {}; each row is "type": "object".'.format(
                    show(items.get("type")) if "type" in items else "missing"),
                    'Set items "type": "object".', "/items/type")
            if not isinstance(items.get("allOf"), list):
                shape("items.allOf is not an array.",
                      "List the category $refs, then the rules, in items.allOf.",
                      "/items/allOf")
            if items.get("unevaluatedProperties") is not False:
                shape('items lacks "unevaluatedProperties": false.',
                      "Add it: it rejects every column no category declares.",
                      "/items/unevaluatedProperties")
            for key in ("properties", "required", "additionalProperties"):
                if key in items:
                    shape("items carries {}; the row is the union of its categories.".format(key),
                          "Move it into the category files: items holds only type, title, allOf "
                          "and unevaluatedProperties.", "/items/" + key)
        if "minItems" not in doc:
            self.add("warning", "mother-min-items", "{} has no minItems.".format(rel),
                     'Add "minItems": 1 so an empty data file fails.', **self.where(rel))
        lacking = [key for key in ("title", "description") if not nonempty_str(doc.get(key))]
        if lacking:
            self.add("warning", "mother-annotations",
                     "{}'s root has no {}.".format(rel, " or ".join(lacking)),
                     "Give the root a title and a description stating the grain (\"One element "
                     "is one participant-night.\").", **self.where(rel))

    def read_allof(self, model, mothers):
        items = model.items if isinstance(model.items, dict) else {}
        entries = items.get("allOf") if isinstance(items.get("allOf"), list) else []
        first_rule = None
        for i, entry in enumerate(entries):
            where = self.where(model.mother, "/items/allOf/{}".format(i))
            if isinstance(entry, dict) and set(entry) == {"$ref"} and isinstance(entry["$ref"], str):
                if first_rule is not None:
                    self.add("error", "allof-order",
                             "{}: the category $ref at /items/allOf/{} follows the rule at "
                             "/items/allOf/{}.".format(model.mother, i, first_rule),
                             "Put every category $ref first and append the rules after them: "
                             "QuaC and the website address rules by allOf position.", **where)
                ref = entry["$ref"]
                if ref.partition("#")[2]:
                    self.add("error", "allof-entry",
                             "{}: items.allOf[{}] $refs {}, a part of a file, not a category "
                             "file.".format(model.mother, i, show(ref)),
                             'Each category entry is {"$ref": "categories/<topic>.json"}.', **where)
                    continue
                resolved, _ = self.pkg.lookup(model.uri, ref)
                if resolved is None:
                    model.unresolved_categories.append(ref)
                    continue
                target = self.pkg.doc_of.get(id(resolved.contents))
                if target is None or target in mothers or target.startswith("common/"):
                    self.add("error", "allof-entry",
                             "{}: items.allOf[{}] $refs {}, which is not a category file.".format(
                                 model.mother, i, show(ref)),
                             "Point it at a category file (categories/<topic>.json).", **where)
                    continue
                model.category_entries.add(i)
                if target not in model.categories:
                    model.categories.append(target)
                self.category_table.setdefault(target, (model.name, PurePosixPath(target).stem))
            elif isinstance(entry, dict) and ("if" in entry or "then" in entry or "else" in entry
                                              or (isinstance(entry.get("$comment"), str)
                                                  and RULE_PREFIX_RE.match(entry["$comment"]))):
                if first_rule is None:
                    first_rule = i
                model.rule_entries.append((i, entry))
                self.rule_nodes.add(id(entry))
            else:
                self.add("error", "allof-entry",
                         "{}: items.allOf[{}] is neither a category $ref nor a rule.".format(
                             model.mother, i),
                         'Each entry is {"$ref": "categories/<topic>.json"} or a rule with '
                         "$comment, x-provenance, if and then; fold anything else into a "
                         "category file.", **where)

    def collect_properties(self, model):
        for rel in model.categories:
            doc = self.pkg.docs.get(rel)
            props = doc.get("properties") if isinstance(doc, dict) else None
            if not isinstance(props, dict):
                continue
            topic = PurePosixPath(rel).stem
            for name, schema in props.items():
                if name in model.props:
                    continue
                prop = Prop(self, model.name, name, rel, topic, schema)
                model.props[name] = prop
                if isinstance(schema, dict):
                    self.prop_by_id[id(schema)] = prop

    # -- categories, properties, definitions

    def lint_category(self, rel, table, topic):
        doc = self.pkg.docs[rel]

        def shape(message, hint, pointer=None):
            self.add("error", "category-shape", "{}: {}".format(rel, message), hint,
                     **self.where(rel, pointer))

        if doc.get("type") != "object":
            shape('a category is "type": "object" (found {}).'.format(
                show(doc.get("type")) if "type" in doc else "none"),
                'Set "type": "object".', "/type")
        props = doc.get("properties")
        if not isinstance(props, dict):
            shape("it has no properties object.",
                  "A category file holds its topic's properties under properties.", "/properties")
            props = {}
        for key in CATEGORY_FORBIDDEN:
            if key in doc:
                self.reported.add((rel, "/" + esc(key)))
                if key in ("additionalProperties", "unevaluatedProperties"):
                    hint = ("Remove it: the mother's single unevaluatedProperties: false does this, "
                            "and on a category it rejects the other categories' columns.")
                else:
                    hint = ("Rules live in the mother's items.allOf (SKIP-LOGIC.md); a rule inside "
                            "a category makes QuaC report every column of the category whenever "
                            "one fails.")
                shape("it carries {} at its top level.".format(key), hint, "/" + esc(key))
        if props:
            required = doc.get("required") if isinstance(doc.get("required"), list) else []
            missing = [name for name in props if name not in required]
            if missing:
                self.add("error", "required-incomplete",
                         "{}'s required omits {}.".format(rel, ", ".join(missing)),
                         "List every property in required, in properties order: every column is "
                         "present in every row; missingness is a code in the cell.",
                         **self.where(rel, "/required"))
        if "x-variable-group" not in doc:
            self.add("warning", "missing-group", "{} has no x-variable-group.".format(rel),
                     'Add "x-variable-group": "{}" at its top level.'.format(topic),
                     **self.where(rel))
        for name, schema in props.items():
            pointer = "/properties/" + esc(name)
            where = self.where(rel, pointer)
            if not isinstance(schema, dict) or not nonempty_str(schema.get("title")):
                self.add("error", "missing-title", "{} has no title.".format(name),
                         "Give every property a title: the label the data dictionary shows.",
                         **where)
            if not isinstance(schema, dict) or "x-provenance" not in schema:
                self.add("error", "missing-provenance", "{} has no x-provenance.".format(name),
                         'Add "x-provenance": {"default": "S01:<where the source defines it>"}: '
                         "every fact traces to a source or a decision.", **where)
            if isinstance(schema, dict):
                self.lint_value_schema(rel, pointer, schema, name)

    def lint_value_schema(self, rel, pointer, node, owner):
        """Code lists, measures and their special codes, on one property or
        definition (owner names it in messages)."""
        base = self.pkg.uri[rel]
        if "enum" in node:
            self.bare_enum(rel, pointer, owner)
        for keyword in ("oneOf", "anyOf"):
            branches = node.get(keyword)
            if not isinstance(branches, list):
                continue
            consts, typed = [], []
            for j, branch in enumerate(branches):
                where = "{}/{}/{}".format(pointer, keyword, j)
                if not isinstance(branch, dict):
                    continue
                if "enum" in branch:
                    self.bare_enum(rel, where, owner)
                if isinstance(branch.get("$ref"), str):
                    resolved, _ = self.pkg.lookup(base, branch["$ref"])
                    target = resolved.contents if resolved is not None else None
                    if isinstance(target, dict) and "const" in target:
                        site = self.pkg.node_at.get(id(target)) or (rel, where)
                        consts.append({
                            "value": target["const"], "kind": value_kind(branch) or value_kind(target),
                            "title": branch.get("title") if nonempty_str(branch.get("title"))
                            else target.get("title"),
                            "description": target.get("description"),
                            "site": site, "ref": branch["$ref"]})
                    elif is_typed(target):
                        typed.append((target, where))
                elif "const" in branch:
                    consts.append({"value": branch["const"], "kind": value_kind(branch),
                                   "title": branch.get("title"),
                                   "description": branch.get("description"),
                                   "site": (rel, where), "ref": None})
                elif is_typed(branch):
                    typed.append((branch, where))
            for code in consts:
                self.lint_code(code, keyword, bool(typed), owner, rel)
            if keyword == "anyOf":
                self.lint_guards(rel, owner, typed, consts)

    def bare_enum(self, rel, pointer, owner):
        self.add("warning", "bare-enum", "{} uses a bare enum.".format(owner),
                 "Write the codes as a oneOf of {const, title} branches: an enum has nowhere to "
                 "put the labels (a rule's then is the one place enum belongs).",
                 **self.where(rel, pointer + "/enum"))

    def lint_code(self, code, keyword, measured, owner, rel):
        site_rel, site_pointer = code["site"]
        where = self.where(site_rel, site_pointer)
        value, title = code["value"], code["title"]
        shared = site_rel != rel or code["ref"] is not None
        who = ("{} (a shared code used by {})".format(site_pointer.rsplit("/", 1)[-1], owner)
               if shared else owner)
        if not nonempty_str(title):
            self.add("error", "code-without-title",
                     "{}: code {} has no title.".format(who, show(value)),
                     "Give every code its label as the source states it, in title.",
                     dedupe=("code-without-title", site_rel, site_pointer), **where)
        elif len(title) > TITLE_LIMIT:
            self.add("warning", "title-too-long",
                     "{}: the title of code {} is {} characters.".format(who, show(value), len(title)),
                     "Keep code titles to 60 characters or fewer - rule readings quote them; move "
                     "the rest to description.", dedupe=("title-too-long", site_rel, site_pointer),
                     **where)
        if code["kind"] is None and keyword == "anyOf" and measured:
            self.add("error", "sentinel-kind-missing",
                     "{}: special code {}{} sits beside a measurement but has no x-value-kind."
                     .format(who, show(value), " ({})".format(title) if nonempty_str(title) else ""),
                     'Add "x-value-kind": "sentinel" to it (on the branch or its shared '
                     'definition) - or "value" if it is a real answer.',
                     dedupe=("sentinel-kind-missing", site_rel, site_pointer), **where)
        if code["kind"] is None and keyword == "oneOf" and (
                jsdd_sentinel(value, title, code["description"], code["ref"])
                or likely_sentinel(value, title)):
            self.add("warning", "value-kind-ambiguous",
                     "{}: code {}{} looks like a missing-value code but has no x-value-kind."
                     .format(who, show(value), " ({})".format(title) if nonempty_str(title) else ""),
                     'Mark it "x-value-kind": "sentinel" if it means no substantive answer, or '
                     '"value" if it is a real answer; without it the data dictionary page has to '
                     'guess.',
                     dedupe=("value-kind-ambiguous", site_rel, site_pointer), **where)

    def lint_guards(self, rel, owner, typed, consts):
        for node, pointer in typed:
            if not numeric_types(node):
                continue
            guarded = guard_keys(node)
            loose = [code["value"] for code in consts
                     if code["kind"] != "value" and within(code["value"], node)
                     and literal_key(code["value"]) not in guarded]
            if loose:
                loose = dedupe_values(loose)
                self.add("error", "guard-missing",
                         "{}: special code{} {} {} inside the measured range ({}) with no guard."
                         .format(owner, "s" if len(loose) > 1 else "", joined(loose),
                                 "fall" if len(loose) > 1 else "falls", describe_typed(node)),
                         'Add "not": {{"enum": [{}]}} to the typed branch, so no special code '
                         'counts as a measurement.'.format(", ".join(show(v) for v in loose)),
                         **self.where(rel, pointer))

    def lint_defs(self):
        files = sorted(rel for rel in self.pkg.docs
                       if rel == "common/defs.json" or rel in self.category_table)
        for rel in files:
            defs = self.pkg.docs[rel].get("$defs")
            if not isinstance(defs, dict):
                continue
            for name, node in defs.items():
                if not isinstance(node, dict):
                    continue
                pointer = "/$defs/" + esc(name)
                self.def_by_id[id(node)] = (rel, pointer)
                self.lint_value_schema(rel, pointer, node, "$defs/" + name)
                if "x-provenance" in node or not defines_code(node):
                    continue
                uses = [site for site in self.ref_sites if site["target"] == id(node)]
                if uses and all(site["has_prov"] for site in uses):
                    self.add("warning", "missing-provenance",
                             "$defs/{} in {} has no x-provenance; each of its {} uses carries its "
                             "own.".format(name, rel, len(uses)),
                             "Add x-provenance to the definition too, so the code traces where it "
                             "is defined.", **self.where(rel, pointer))
                else:
                    self.add("error", "missing-provenance",
                             "$defs/{} in {} defines a code or pattern but has no x-provenance."
                             .format(name, rel),
                             'Add "x-provenance": {"default": "S01:<where the source defines '
                             'it>"}, as on a property.', **self.where(rel, pointer))

    # -- rules

    def parse_rule(self, model, index, node):
        rule = RuleEntry(model, index, node)
        comment = node.get("$comment")
        match = RULE_COMMENT_RE.fullmatch(comment) if isinstance(comment, str) else None
        if isinstance(comment, str):
            rule.comment = comment
        if match:
            prefix = match.group(1)
            rule.id, rule.reading = match.group(2), match.group(3)
            rule.kind = ("skip" if prefix == "Skip pattern" else
                         "applicability" if prefix == "Applicability" else "routing")
            rule.domain = prefix[: -len(" routing")] if rule.kind == "routing" else None
        model.rules.append(rule)

        def bad(code, message, hint, sub="", variable=None):
            rule.grammar_ok = False
            self.add("error", code, message, hint, file=model.mother, pointer=rule.pointer + sub,
                     table=model.name, variable=variable, rule=rule.id)

        name = rule.label()
        missing = [key for key in RULE_KEYS if key not in node]
        extra = sorted(key for key in node if key not in RULE_KEYS)
        if missing or extra:
            parts = (["lacks " + ", ".join(missing)] if missing else []) + (
                ["has " + ", ".join(extra)] if extra else [])
            hint = "A rule has exactly $comment, x-provenance, if and then (SKIP-LOGIC.md)."
            if "else" in extra:
                hint += " Drop else: the reverse direction is its own rule."
            bad("rule-shape", "{} {}.".format(cap_first(name), " and ".join(parts)), hint)
        if "$comment" in node and match is None:
            bad("rule-comment",
                "{}'s $comment does not begin with a rule label: {}.".format(
                    cap_first(name), show(comment, 70)),
                'Begin it "Skip pattern R001: ", "Applicability R001: " or "<Domain> routing '
                'R001: ", then the plain reading on one line (SKIP-LOGIC.md).', "/$comment")
        if "if" in node:
            rule.when = self.parse_if(rule, node["if"], bad)
        if "then" in node:
            rule.then = self.parse_then(rule, model, node["then"], bad)
        provenance = node.get("x-provenance")
        rule.provenance = provenance if isinstance(provenance, dict) else None
        self.check_rule_meaning(rule, model)

    def parse_if(self, rule, node, bad):
        name = cap_first(rule.label())
        if not isinstance(node, dict):
            bad("rule-shape", "{}'s if is not an object.".format(name), CLAUSE_HINT, "/if")
            return None
        if "anyOf" in node:
            clauses = node["anyOf"]
            if set(node) != {"anyOf"} or not isinstance(clauses, list) or len(clauses) < 2:
                bad("rule-shape", "{}'s if is not one clause or {{\"anyOf\": [two or more clauses]}}."
                    .format(name), CLAUSE_HINT, "/if")
                return None
            parsed = [self.parse_clause(rule, clause, "/if/anyOf/{}".format(k), bad)
                      for k, clause in enumerate(clauses)]
            return None if any(c is None for c in parsed) else {"any": parsed}
        clause = self.parse_clause(rule, node, "/if", bad)
        return None if clause is None else {"any": [clause]}

    def parse_clause(self, rule, node, sub, bad):
        name = cap_first(rule.label())
        if not isinstance(node, dict):
            bad("rule-shape", "{}'s clause at {} is not an object.".format(name, sub), CLAUSE_HINT, sub)
            return None
        keys = set(node)
        if keys != {"required", "properties"}:
            nested = sorted(keys & {"if", "then", "else", "allOf", "anyOf", "oneOf", "not"})
            message = "{}'s clause at {} has {}; a clause is exactly {{\"required\", \"properties\"}}."\
                .format(name, sub, ", ".join(sorted(keys)) or "nothing")
            if nested:
                message += " No {} inside if.".format(", ".join(nested))
            bad("rule-shape", message, CLAUSE_HINT, sub)
            return None
        required, props = node["required"], node["properties"]
        if not isinstance(required, list) or not required or not all(
                isinstance(item, str) for item in required):
            bad("rule-shape", "{}'s clause at {}: required must list the gate names.".format(
                name, sub), CLAUSE_HINT, sub + "/required")
            return None
        if not isinstance(props, dict) or not props:
            bad("rule-shape", "{}'s clause at {}: properties must map each gate to its test."
                .format(name, sub), CLAUSE_HINT, sub + "/properties")
            return None
        ok = True
        if set(required) != set(props):
            untested = [n for n in required if n not in props]
            unrequired = [n for n in props if n not in required]
            parts = []
            if unrequired:
                parts.append("tests {} without requiring {}".format(
                    ", ".join(unrequired), "it" if len(unrequired) == 1 else "them"))
            if untested:
                parts.append("requires {} without testing {}".format(
                    ", ".join(untested), "it" if len(untested) == 1 else "them"))
            bad("rule-unguarded", "{}'s clause at {} {}.".format(name, sub, " and ".join(parts)),
                "List exactly the tested gates in required: without it a row lacking a gate "
                "satisfies the if vacuously and the rule fires on it.", sub)
            ok = False
        tests = []
        for gate, test in props.items():
            pointer = "{}/properties/{}".format(sub, esc(gate))
            parsed = self.parse_test(rule, gate, test, pointer, bad)
            if parsed is None:
                ok = False
                continue
            item = {"variable": gate}
            item.update(parsed)
            tests.append(item)
            rule.gates.append((gate, parsed, pointer))
        return {"all": tests} if ok else None

    def parse_test(self, rule, gate, test, pointer, bad):
        name = cap_first(rule.label())
        if isinstance(test, dict):
            keys = set(test)
            if keys == {"const"}:
                return {"test": "eq", "value": test["const"]}
            if keys == {"enum"}:
                if isinstance(test["enum"], list) and len(test["enum"]) >= 2:
                    return {"test": "in", "values": list(test["enum"])}
                bad("rule-shape", "{}'s test on {} is an enum of fewer than two values.".format(
                    name, gate), 'Use {"const": v} for one value; enum is for two or more.',
                    pointer, gate)
                return None
            if keys == {"not"}:
                inner = test["not"]
                if isinstance(inner, dict) and set(inner) == {"const"}:
                    return {"test": "ne", "value": inner["const"]}
                if (isinstance(inner, dict) and set(inner) == {"enum"}
                        and isinstance(inner["enum"], list) and inner["enum"]):
                    return {"test": "nin", "values": list(inner["enum"])}
            elif "type" in keys:
                found = self.parse_range(rule, gate, test, pointer, bad, "test")
                if found is None:
                    return None
                out = {"test": "range"}
                out.update(found)
                return out
        bad("rule-shape", "{}'s test on {} ({}) is not a rule test.".format(name, gate, show(test)),
            TEST_HINT, pointer, gate)
        return None

    def parse_range(self, rule, gate, node, pointer, bad, what):
        problems = []
        extra = sorted(key for key in node if key not in BOUNDS + ("type", "not"))
        if extra:
            problems.append("has " + ", ".join(extra))
        if node.get("type") not in ("integer", "number"):
            problems.append('its type is {}, not "integer" or "number"'.format(show(node.get("type"))))
        bounds = {}
        for key in BOUNDS:
            if key in node:
                if is_number(node[key]):
                    bounds[key] = node[key]
                else:
                    problems.append("{} is {}, not a number".format(key, show(node[key])))
        if not any(key in node for key in BOUNDS):
            problems.append("states no bound")
        excludes = []
        if "not" in node:
            inner = node["not"]
            if (isinstance(inner, dict) and set(inner) == {"enum"}
                    and isinstance(inner["enum"], list) and inner["enum"]):
                excludes = list(inner["enum"])
            else:
                problems.append('its not is not {"enum": [codes]}')
        if problems:
            bad("rule-shape", "{}'s range {} on {} {}.".format(
                cap_first(rule.label()), what, gate, "; ".join(problems)),
                TEST_HINT if what == "test" else EFFECT_HINT, pointer, gate)
            return None
        out = {"type": node["type"]}
        out.update(bounds)
        out["excludes"] = excludes
        return out

    def parse_then(self, rule, model, node, bad):
        name = cap_first(rule.label())
        if not isinstance(node, dict):
            bad("rule-shape", "{}'s then is not an object.".format(name), THEN_HINT, "/then")
            return None
        keys = set(node)
        effects, ok = [], True
        if keys == {"properties"} and isinstance(node["properties"], dict) and node["properties"]:
            rule.mode = "all"
            for target, effect in node["properties"].items():
                pointer = "/then/properties/" + esc(target)
                parsed = self.parse_effect(rule, model, target, effect, pointer, bad)
                if parsed is None:
                    ok = False
                    continue
                item = {"variable": target}
                item.update(parsed)
                effects.append(item)
                rule.targets.append((target, parsed, pointer))
            return {"mode": "all", "effects": effects} if ok else None
        if keys == {"anyOf"} and isinstance(node["anyOf"], list) and len(node["anyOf"]) >= 2:
            rule.mode = "any"
            for k, alt in enumerate(node["anyOf"]):
                sub = "/then/anyOf/{}".format(k)
                if not (isinstance(alt, dict) and set(alt) == {"required", "properties"}
                        and isinstance(alt["required"], list) and len(alt["required"]) == 1
                        and isinstance(alt["required"][0], str)
                        and isinstance(alt["properties"], dict) and len(alt["properties"]) == 1):
                    bad("rule-shape", "{}'s then.anyOf[{}] is not {{\"required\": [t], "
                        "\"properties\": {{t: effect}}}} for one target t.".format(name, k),
                        THEN_HINT, sub)
                    ok = False
                    continue
                target = next(iter(alt["properties"]))
                if alt["required"][0] != target:
                    bad("rule-unguarded", "{}'s then.anyOf[{}] requires {} but constrains {}."
                        .format(name, k, alt["required"][0], target),
                        "Require the same target the alternative constrains, or a row lacking it "
                        "satisfies the alternative vacuously.", sub, target)
                    ok = False
                    continue
                pointer = "{}/properties/{}".format(sub, esc(target))
                parsed = self.parse_effect(rule, model, target, alt["properties"][target],
                                           pointer, bad)
                if parsed is None:
                    ok = False
                    continue
                item = {"variable": target}
                item.update(parsed)
                effects.append(item)
                rule.targets.append((target, parsed, pointer))
            return {"mode": "any", "effects": effects} if ok else None
        nested = sorted(keys & {"if", "then", "else", "allOf", "oneOf", "not", "$ref"})
        if keys == {"properties"}:
            message = "{}'s then.properties names no target.".format(name)
        elif keys == {"anyOf"}:
            message = "{}'s then.anyOf needs two or more alternatives.".format(name)
        else:
            message = "{}'s then has {}; a then is {{\"properties\": {{...}}}} or {{\"anyOf\": " \
                      "[two or more alternatives]}}.".format(name, ", ".join(sorted(keys)) or "nothing")
        if nested:
            message += " No {} inside then.".format(", ".join(nested))
        bad("rule-shape", message, THEN_HINT, "/then")
        return None

    def parse_effect(self, rule, model, target, effect, pointer, bad):
        name = cap_first(rule.label())
        if isinstance(effect, dict):
            keys = set(effect)
            if keys == {"const"}:
                return {"effect": "eq", "value": effect["const"]}
            if keys == {"not"} and isinstance(effect["not"], dict) and set(effect["not"]) == {"const"}:
                return {"effect": "ne", "value": effect["not"]["const"]}
            if keys == {"enum"} and isinstance(effect["enum"], list) and effect["enum"]:
                return {"effect": "in", "values": list(effect["enum"])}
            if keys == {"anyOf"} and isinstance(effect["anyOf"], list) and effect["anyOf"]:
                return self.parse_narrowing(rule, model, target, effect["anyOf"], pointer, bad)
        bad("rule-shape", "{}'s effect on {} ({}) is not a rule effect.".format(
            name, target, show(effect)), EFFECT_HINT, pointer, target)
        return None

    def parse_narrowing(self, rule, model, target, branches, pointer, bad):
        name = cap_first(rule.label())
        first = branches[0]
        if not isinstance(first, dict) or "type" not in first:
            bad("rule-shape", "{}'s narrowed range on {} does not start with its typed branch."
                .format(name, target), EFFECT_HINT, pointer + "/anyOf/0", target)
            return None
        found = self.parse_range(rule, target, first, pointer + "/anyOf/0", bad, "effect")
        if found is None:
            return None
        also, ok = [], True
        for k, branch in enumerate(branches[1:], 1):
            sub = "{}/anyOf/{}".format(pointer, k)
            if (isinstance(branch, dict) and "const" in branch
                    and set(branch) <= {"const", "title", "x-value-kind", "$comment"}):
                also.append(branch["const"])
                continue
            if isinstance(branch, dict) and set(branch) == {"$ref"} and isinstance(branch["$ref"], str):
                resolved, _ = self.pkg.lookup(model.uri, branch["$ref"])
                if resolved is None:
                    rule.grammar_ok = False  # unresolved-ref already says why
                    ok = False
                    continue
                if isinstance(resolved.contents, dict) and "const" in resolved.contents:
                    also.append(resolved.contents["const"])
                    continue
                bad("rule-shape", "{}'s $ref {} on {} does not point at a sentinel definition (a "
                    "const).".format(name, show(branch["$ref"]), target), EFFECT_HINT, sub, target)
                ok = False
                continue
            bad("rule-shape", "{}'s narrowed range on {}: branch {} is neither a sentinel const nor "
                "a $ref to one.".format(name, target, k), EFFECT_HINT, sub, target)
            ok = False
        if not ok:
            return None
        out = {"effect": "range"}
        out.update(found)
        out["also"] = also
        return out

    def check_rule_meaning(self, rule, model):
        props = model.props
        stand_down = bool(model.unresolved_categories)
        name = cap_first(rule.label())
        where = {"file": model.mother, "table": model.name, "rule": rule.id}
        for gate, test, sub in rule.gates:
            pointer = rule.pointer + sub
            prop = props.get(gate)
            if prop is None:
                if not stand_down:
                    self.add("error", "rule-dangling",
                             "{} tests {}, which no category of {} declares.".format(
                                 name, gate, model.name),
                             "Fix the name, or add the property to its category file - until "
                             "then the rule never fires.", pointer=pointer, variable=gate, **where)
                continue
            values = [test["value"]] if "value" in test else list(test.get("values", []))
            if test["test"] == "range":
                values = []
            for value in dedupe_values(values):
                if prop.admits(value) is False:
                    allowed = describe_allowed(prop.profile())
                    self.add("warning", "trigger-undeclared-level",
                             "{} triggers on {} = {}, which {} does not declare.".format(
                                 name, gate, show(value), gate),
                             "Trigger on a value {} declares{}, or declare the level in its "
                             "category file: a trigger on an undeclared value never fires."
                             .format(gate, " ({})".format(clip(allowed, 160)) if allowed else ""),
                             pointer=pointer, variable=gate, **where)
            if test["test"] == "range":
                excluded = {literal_key(v) for v in test["excludes"]}
                loose = [code.value for code in special_codes(prop.profile())
                         if within(code.value, test) and literal_key(code.value) not in excluded]
                if loose:
                    loose = dedupe_values(loose)
                    self.add("warning", "range-trigger-sentinel",
                             "{}'s range test on {} also admits its special code{} {}.".format(
                                 name, gate, "s" if len(loose) > 1 else "", joined(loose)),
                             'Add "not": {{"enum": [{}]}} to the test, so a respondent coded {} '
                             'does not trigger the rule.'.format(
                                 ", ".join(show(v) for v in loose), joined(loose, "or")),
                             pointer=pointer, variable=gate, **where)
        for target, effect, sub in rule.targets:
            pointer = rule.pointer + sub
            prop = props.get(target)
            if prop is None:
                if not stand_down:
                    self.add("error", "rule-dangling",
                             "{} constrains {}, which no category of {} declares.".format(
                                 name, target, model.name),
                             "Fix the name, or add the property to its category file - until "
                             "then the rule can let an undeclared column through.",
                             pointer=pointer, variable=target, **where)
                continue
            kind = effect["effect"]
            pinned = ([effect["value"]] if kind == "eq" else effect["values"] if kind == "in"
                      else effect["also"] if kind == "range" else [])
            undeclared = set()
            for value in dedupe_values(pinned):
                if prop.admits(value) is False:
                    undeclared.add(literal_key(value))
                    allowed = describe_allowed(prop.profile())
                    self.add("error", "rule-undeclared-code",
                             "{} pins {} to {}, which {} does not declare.".format(
                                 name, target, show(value), target),
                             "Pin a value {} declares{}; otherwise every row the rule applies to "
                             "fails.".format(target, " ({})".format(clip(allowed, 160))
                                             if allowed else ""),
                             pointer=pointer, variable=target, **where)
            if rule.kind == "skip":
                if kind != "eq":
                    self.add("error", "skip-shape",
                             "{} is a Skip pattern, but its effect on {} is not a const pin."
                             .format(name, target),
                             "A Skip pattern pins the structural code: {\"const\": c}, with c "
                             "marked \"x-value-kind\": \"sentinel\". Any other effect is a "
                             "'<Domain> routing' rule.", pointer=pointer, variable=target, **where)
                elif literal_key(effect["value"]) not in undeclared:
                    kinds = [code.kind for code in prop.profile()["codes"]
                             if literal_key(code.value) == literal_key(effect["value"])]
                    if "sentinel" not in kinds:
                        self.add("error", "skip-shape",
                                 "{} pins {} to {}, which {} does not mark \"x-value-kind\": "
                                 "\"sentinel\".".format(name, target, show(effect["value"]), target),
                                 "A Skip pattern pins the structural code: mark that code a "
                                 "sentinel (on its branch or shared definition), or, if the pin "
                                 "is a real value, label the rule '<Domain> routing'.",
                                 pointer=pointer, variable=target, **where)
            elif rule.kind == "applicability" and kind != "ne":
                self.add("error", "applicability-shape",
                         "{} is an Applicability half, but its effect on {} is not "
                         "{{\"not\": {{\"const\": c}}}}.".format(name, target),
                         "The applicability half only forbids the structural code; a then that "
                         "demands a value outlaws honest missingness (SKIP-LOGIC.md, Skip pairs).",
                         pointer=pointer, variable=target, **where)

    def check_rule_ids(self, model):
        first = {}
        for rule in model.rules:
            if rule.id is None:
                continue
            key = (rule.id, rule.kind)
            if key in first:
                self.add("error", "duplicate-rule",
                         "{} has two {} entries in {} ({} and {}).".format(
                             rule.id, KIND_WORDS.get(rule.kind, "rule"), model.name,
                             first[key].pointer, rule.pointer),
                         "Give each rule its own id; a skip/applicability pair shares one id, one "
                         "entry per half.", file=model.mother, pointer=rule.pointer,
                         table=model.name, rule=rule.id)
            else:
                first[key] = rule
        halves = {}
        for (rule_id, kind), rule in first.items():
            halves.setdefault(rule_id, {})[kind] = rule
        for rule_id, kinds in sorted(halves.items()):
            for have, lack in (("skip", "applicability"), ("applicability", "skip")):
                if have in kinds and lack not in kinds:
                    self.add("warning", "missing-twin",
                             "{} has a {} half but no {} half in {}.".format(
                                 rule_id, KIND_WORDS[have], KIND_WORDS[lack], model.name),
                             "Add the twin with the same id, so the rule holds both ways (it "
                             "rides the same x-provenance); a one-directional pin is '<Domain> "
                             "routing'.", file=model.mother, pointer=kinds[have].pointer,
                             table=model.name, rule=rule_id)

    # -- x-provenance

    def lint_provenance(self):
        for rel, doc in sorted(self.pkg.docs.items()):
            for node, here in iter_schema(doc, "", self.rule_nodes):
                if "x-provenance" not in node:
                    continue
                prop = self.prop_by_id.get(id(node))
                if prop is not None and prop.file == rel:
                    codes = lambda prop=prop: [c.value for c in prop.profile()["codes"]]
                    owner = prop.name
                elif id(node) in self.def_by_id:
                    codes = lambda node=node, rel=rel: [c.value for c in value_profile(
                        self.pkg, node, self.pkg.resolver(self.pkg.uri[rel]))["codes"]]
                    owner = "$defs/" + unesc(here.rsplit("/", 1)[-1])
                elif "const" in node:
                    codes = lambda node=node: [node["const"]]
                    owner = "the code at " + here
                else:
                    codes, owner = None, here or rel
                self.lint_provenance_site(rel, here, node["x-provenance"], codes, owner)
        for model in self.tables.values():
            for rule in model.rules:
                if "x-provenance" in rule.node:
                    self.lint_provenance_site(model.mother, rule.pointer, rule.node["x-provenance"],
                                              lambda rule=rule, model=model: rule_codes(rule, model),
                                              rule.label())
        if not self.prov.present:
            self.add("info", "provenance-unchecked",
                     "provenance.json is missing, so x-provenance references were checked for "
                     "form only.",
                     "`schemify.py build` writes provenance.json; rerun after it to check that every "
                     "reference names a citable source or decision.", file="../provenance.json")

    def lint_provenance_site(self, rel, pointer, value, codes, owner):
        at = pointer + "/x-provenance"
        where = self.where(rel, at)
        if self.mother_table.get(rel) and pointer.startswith("/items/allOf/"):
            rule = next((r for m in self.tables.values() for r in m.rules
                         if m.mother == rel and r.pointer == pointer), None)
            if rule is not None:
                where["rule"] = rule.id
        ok = True

        def shape(message, sub=""):
            self.add("error", "provenance-shape", "{}: {}".format(owner, message), PROVENANCE_HINT,
                     **dict(where, pointer=at + sub))

        if not isinstance(value, dict):
            shape("x-provenance is {}, not an object of facet: reference.".format(show(value)))
            self.prov_ok[(rel, pointer)] = False
            return
        if not value:
            shape("x-provenance is empty.")
            self.prov_ok[(rel, pointer)] = False
            return
        for facet, refs in value.items():
            sub = "/" + esc(facet)
            code = MISSING
            if facet.startswith("value:"):
                try:
                    code = json.loads(facet[len("value:"):], parse_constant=NonFinite,
                                      parse_float=_parse_float)
                    if isinstance(code, (dict, list, NonFinite)):
                        raise ValueError(facet)
                except (ValueError, RecursionError):
                    shape("facet {} does not hold a JSON literal (write value:777 or "
                          "value:\"01\").".format(show(facet)), sub)
                    ok, code = False, MISSING
            elif facet not in FACETS:
                shape("{} is not a facet.".format(show(facet)), sub)
                ok = False
            items = [refs] if isinstance(refs, str) else refs if isinstance(refs, list) and refs \
                else None
            if items is None:
                shape("{} maps to {}, not a reference or a non-empty list of them.".format(
                    show(facet), show(refs)), sub)
                ok = False
                continue
            for k, ref in enumerate(items):
                ref_at = sub if isinstance(refs, str) else "{}/{}".format(sub, k)
                if not isinstance(ref, str) or not REFERENCE_RE.fullmatch(ref):
                    shape("{} is not a reference (S01, S01:<locator> or D014).".format(show(ref)),
                          ref_at)
                    ok = False
                    continue
                self.prov_refs.append(ref)
                if not self.check_reference(ref, owner, dict(where, pointer=at + ref_at)):
                    ok = False
            if code is not MISSING and codes is not None:
                declared = {literal_key(v) for v in codes()}
                if literal_key(code) not in declared:
                    self.add("warning", "provenance-unknown-code",
                             "{}: facet {} names a code {} does not declare.".format(
                                 owner, show(facet), owner),
                             "Name a declared code (value:<code> as JSON: value:777, value:\"01\"), "
                             "or remove the facet.", **dict(where, pointer=at + sub))
        self.prov_ok[(rel, pointer)] = ok

    def check_reference(self, ref, owner, where):
        """Resolve one reference against provenance.json; False on an error."""
        if not self.prov.usable:
            return True
        ref_id = ref.split(":", 1)[0]
        entry = self.prov.entry(ref_id)
        if entry is MISSING:
            self.add("error", "provenance-unresolved",
                     "{}: {} is not in provenance.json.".format(owner, ref_id),
                     "Cite a source or decision that exists (`schemify.py show {}`), or record it, "
                     "then rebuild.".format(ref_id), **where)
            return False
        status = entry.get("status")
        if ref_id.startswith("S"):
            if status not in SOURCE_CITABLE:
                self.add("error", "provenance-uncitable",
                         "{}: source {} is {}; only active, approved or retired sources can be "
                         "cited.".format(owner, ref_id, show(status) if status is not None
                                         else "without a status"),
                         "A suggested web source becomes citable once a person approves it; cite "
                         "another source, or a decision, meanwhile.", **where)
                return False
            return True
        if status == "cancelled":
            self.add("error", "provenance-uncitable",
                     "{}: decision {} is cancelled.".format(owner, ref_id),
                     "Cite the decision that replaced it, or the source.", **where)
            return False
        if status == "superseded":
            self.add("warning", "provenance-superseded",
                     "{}: decision {} is superseded.".format(owner, ref_id),
                     "Cite the decision that replaced it (`schemify.py show {}` names it).".format(
                         ref_id), **where)
        return True

    # -- keyword scans

    def scan_keywords(self):
        for rel, doc in sorted(self.pkg.docs.items()):
            for node, here in iter_schema(doc, "", self.rule_nodes):
                for key, value in node.items():
                    at = here + "/" + esc(key)
                    where = self.where(rel, at)
                    if key.startswith("x-"):
                        if key not in X_KEYWORDS:
                            self.add("warning", "unknown-x-keyword",
                                     "{}: {} is not one of the seven x- keywords.".format(rel, key),
                                     "Use x-provenance, x-value-kind, x-variable-group, x-unit, "
                                     "x-universe, x-derivation or x-role; put notes in $comment or "
                                     "description.", **where)
                        elif key == "x-value-kind" and value not in ("sentinel", "value"):
                            self.add("error", "bad-value-kind",
                                     "{}: x-value-kind is {}.".format(rel, show(value)),
                                     'x-value-kind is "sentinel" (no substantive answer) or "value" '
                                     "(a real answer).", **where)
                    if key in DISCOURAGED:
                        self.add("warning", "discouraged-keyword",
                                 "{}: {} at {}.".format(rel, key, here or "/"),
                                 "Drop {}: {} (SCHEMA-STYLE.md, Keywords never used).".format(
                                     key, DISCOURAGED[key]), **where)
                    if key == "type" and (value == "null" or (isinstance(value, list)
                                                              and "null" in value)):
                        self.add("warning", "discouraged-keyword",
                                 '{}: "type": "null" at {}.'.format(rel, here or "/"),
                                 "Missingness is a declared code; null appears only as a const "
                                 "under a recorded convention (SCHEMA-STYLE.md, Sentinels).",
                                 **where)
                    if (rel, at) in self.reported:
                        continue
                    if key in FORBIDDEN:
                        self.add("error", "forbidden-keyword",
                                 "{}: {} at {}.".format(rel, key, here or "/"),
                                 "Every rule is a one-directional if/then in the mother's "
                                 "items.allOf; write the reverse direction as its own rule.",
                                 **where)
                    if key == "if":
                        self.add("error", "conditional-outside-mother",
                                 "{} has an if at {}; conditionals live only in the mother's "
                                 "items.allOf.".format(rel, here or "/"),
                                 "Move it into the mother as a rule entry with $comment, "
                                 "x-provenance, if and then (SKIP-LOGIC.md).", **where)


def defines_code(node):
    if any(key in node for key in ("const", "enum", "pattern")):
        return True
    return any(isinstance(branch, dict) and any(key in branch for key in ("const", "enum", "pattern"))
               for keyword in ("oneOf", "anyOf", "allOf")
               for branch in (node.get(keyword) if isinstance(node.get(keyword), list) else []))


def rule_codes(rule, model):
    values = []
    for name, part, _ in rule.gates + rule.targets:
        prop = model.props.get(name)
        if prop is not None:
            values.extend(code.value for code in prop.profile()["codes"])
        values.extend([part["value"]] if "value" in part else part.get("values", []))
        values.extend(part.get("also", []))
    return values


def open_package(path):
    root = Path(path)
    refuse_skill_dir(root, "a package")
    if not root.exists():
        raise ValidateError("Package folder not found: {}".format(path),
                            "Pass the package root: the folder holding schemas/ (schemify/package "
                            "in a workspace).")
    if not root.is_dir():
        raise ValidateError("{} is a file, not a package folder.".format(path),
                            "Pass the package root: the folder holding schemas/.")
    if not (root / "schemas").is_dir():
        raise ValidateError("{} has no schemas/ folder.".format(path),
                            "Pass the package root: the folder holding schemas/, toy-data/ and "
                            "provenance.json (schemify/package in a workspace).")
    return Package(root)


def refuse_skill_dir(path, what):
    if not (SKILL_DIR / "SKILL.md").is_file():
        return
    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError):
        return
    if resolved == SKILL_DIR or SKILL_DIR in resolved.parents:
        raise ValidateError(
            "Refusing to use {} inside the installed skill folder ({}).".format(what, SKILL_DIR),
            "The skill folder is read-only; point at the package in the workspace "
            "(schemify/package) instead.")


def analyze(path):
    pkg = open_package(path)
    return Analysis(pkg, Provenance(pkg.root), str(path)).run()


def select_tables(an, table):
    if table is None:
        return sorted(an.tables)
    if table not in an.tables:
        raise ValidateError(
            "No table named {} in this package (tables: {}).".format(
                show(table), ", ".join(sorted(an.tables)) or "none"),
            "Table names are the folders under schemas/ that hold a *.schema.json mother.")
    return [table]


# -------------------------------------------------------------- row checks


class RowChecker(object):
    """Validates rows one at a time against a table's items, and turns
    jsonschema's errors into findings a person can act on."""

    def __init__(self, an, model):
        self.an = an
        self.model = model
        self.declared = set(model.props)
        self.validator, self.direct = self.build_validator()
        self.rules = {rule.index: rule for rule in model.rules}
        root = model.doc
        self.min_items = root.get("minItems") if is_integral(root.get("minItems")) else None
        self.unique = root.get("uniqueItems") is True
        self._allowed = {}

    def build_validator(self):
        """A validator for one row, and whether undeclared columns are found
        here rather than by jsonschema. In a house-shaped table "no column
        beyond the categories' properties" is exactly what items'
        unevaluatedProperties: false means, and checking it directly avoids
        jsonschema re-validating every category to collect annotations - most
        of the time a row takes."""
        model, registry = self.model, self.an.pkg.registry
        full = Draft202012Validator({"$ref": model.uri + "#/items"}, registry=registry)
        if not plain_table(self.an, model):
            return full, False
        items = {key: value for key, value in model.items.items()
                 if key != "unevaluatedProperties"}
        items["$id"] = urljoin(model.uri, "__schemify_rows__.json")  # a sibling: same relative refs
        try:
            registry = registry.with_resource(items["$id"], DRAFT202012.create_resource(items))
            return Draft202012Validator(items, registry=registry.crawl()), True
        except Exception:  # fall back to the plain, slower route
            return full, False

    def column_types(self, name):
        prop = self.model.props.get(name)
        return prop.column_types() if prop is not None else {"string"}

    def check_rows(self, rows, empties=frozenset()):
        out = []
        if self.min_items is not None and len(rows) < self.min_items:
            out.append({"row": None, "column": None, "keyword": "minItems",
                        "message": "The file has {}; the table needs at least {}.".format(
                            plural(len(rows), "row"), self.min_items),
                        "hint": "Add rows: an empty or short file fails this table."})
        seen = {} if self.unique else None
        for i, row in enumerate(rows):
            out.extend(self.check_row(row, i, empties))
            if seen is not None:
                key = canonical_json(row)
                first = seen.setdefault(key, i)
                if first != i:
                    out.append({"row": i, "column": None, "keyword": "uniqueItems",
                                "message": "Row {} repeats row {} exactly.".format(i, first),
                                "hint": "The table does not allow two identical rows; remove the "
                                        "repeat."})
        out.sort(key=finding_order)
        return out

    def check_row(self, row, i, empties=frozenset()):
        bad_cells = nonfinite_cells(row)
        try:
            errors = list(self.validator.iter_errors(row))
        except Exception as exc:  # a schema the validator cannot run: reported, never raised
            return [{"row": i, "column": None, "keyword": "error",
                     "message": clip("The validator could not check this row ({}: {}).".format(
                         type(exc).__name__, exc)),
                     "hint": "Run `validate.py check` and fix the schema errors it reports."}]
        out = []
        for error in errors:
            out.extend(self.describe(error, row, i, empties))
        if self.direct and isinstance(row, dict):
            out.extend({"row": i, "column": key, "keyword": "unevaluatedProperties",
                        "message": clip("{} is not a column of this table.".format(key)),
                        "hint": clip(UNDECLARED_HINT.format(key))}
                       for key in row if key not in self.declared)
        if bad_cells:
            out = [item for item in out if item["column"] not in bad_cells]
            for column, token in bad_cells.items():
                out.append({"row": i, "column": column, "keyword": "non-finite",
                            "message": "{} holds {}, which is not a number JSON can hold.".format(
                                column if column is not None else "The row", token),
                            "hint": "JSON has no NaN or Infinity; write the field's missing-value "
                                    "code, or a real number."})
        return out

    def describe(self, error, row, i, empties):
        path = list(error.absolute_path)
        rule = self.attribute(error)
        if path:
            columns = [path[0] if isinstance(path[0], str) else None]
        elif error.validator == "required":
            columns = [self.required_name(error, row)]
        elif error.validator == "unevaluatedProperties":
            if not isinstance(row, dict):
                return []
            # Every column of a failing category is reported as unevaluated too;
            # only the ones no category declares are real.
            columns = [key for key in row if key not in self.declared and repr(key) in error.message]
            if not columns:
                return []
        else:
            columns = [None]
        out = []
        for column in columns:
            empty = column is not None and (i, column) in empties
            item = {"row": i, "column": column, "keyword": error.validator,
                    "message": clip(self.message(error, column, rule, empty)),
                    "hint": clip(self.hint(error, column, rule, empty))}
            if rule is not None:
                if rule.id:
                    item["rule"] = rule.id
                item["allof_index"] = rule.index
            if empty:
                item["empty_cell"] = True
            out.append(item)
        return out

    def attribute(self, error):
        path = list(error.absolute_schema_path)
        while path and path[0] in ("$ref", "items"):
            path.pop(0)
        if len(path) >= 2 and path[0] == "allOf" and isinstance(path[1], int):
            return self.rules.get(path[1])
        return None

    @staticmethod
    def required_name(error, row):
        names = error.validator_value if isinstance(error.validator_value, list) else []
        absent = [name for name in names if isinstance(name, str)
                  and not (isinstance(row, dict) and name in row)]
        for name in absent:
            if "{!r} is a required property".format(name) == error.message:
                return name
        return absent[0] if absent else None

    def allowed(self, column):
        if column not in self._allowed:
            prop = self.model.props.get(column)
            self._allowed[column] = describe_allowed(prop.profile()) if prop is not None else None
        return self._allowed[column]

    def message(self, error, column, rule, empty):
        keyword, value = error.validator, error.instance
        subject = column if column is not None else "The row"
        if keyword == "required":
            return ("The {} cell is empty.".format(column) if empty
                    else "{} is missing.".format(column))
        if keyword == "unevaluatedProperties":
            return "{} is not a column of this table.".format(column)
        if keyword in ("anyOf", "oneOf") and column is None and rule is not None and rule.mode == "any":
            names = ", ".join(name for name, _, _ in rule.targets)
            return "{} needs at least one of {} to hold; none does.".format(
                cap_first(rule.label()), names)
        if keyword == "type":
            if column is None:
                return "The row is {}, not an object.".format(show(value))
            expected = error.validator_value
            expected = " or ".join(expected) if isinstance(expected, list) else expected
            return "{} is {}, which is not of type {}.".format(subject, show(value), expected)
        if keyword == "const":
            return "{} is {}; {} is required here.".format(subject, show(value),
                                                           show(error.validator_value))
        if keyword == "not":
            return "{} is {}, which is not allowed here.".format(subject, show(value))
        if keyword == "enum":
            allowed = error.validator_value if isinstance(error.validator_value, list) else []
            return "{} is {}; allowed here: {}.".format(subject, show(value), show_list(allowed))
        if keyword == "oneOf" and not error.context:
            return "{} is {}, which matches more than one declared value.".format(
                subject, show(value))
        if keyword in ("anyOf", "oneOf"):
            return "{} is {}, which is not an allowed value.".format(subject, show(value))
        if keyword in BOUNDS:
            side = {"minimum": "below the minimum", "maximum": "above the maximum",
                    "exclusiveMinimum": "not above", "exclusiveMaximum": "not below"}[keyword]
            return "{} is {}, {} {}.".format(subject, show(value), side,
                                             show(error.validator_value))
        if keyword == "pattern":
            return "{} is {}, which does not match {}.".format(subject, show(value),
                                                               error.validator_value)
        return "{}: {}".format(subject, error.message)

    def hint(self, error, column, rule, empty):
        keyword = error.validator
        if keyword == "required":
            prop = self.model.props.get(column)
            codes = special_codes(prop.profile()) if prop is not None else []
            lead = ("The cell is empty, but every row needs {}.".format(column) if empty
                    else "Every row needs {}.".format(column))
            if codes:
                return "{} When the value is missing, write one of its missing-value codes: {}.".format(
                    lead, ", ".join(code_text(code) for code in codes[:6]))
            return ("{} The data dictionary gives {} no missing-value code, so ask the data "
                    "steward how a missing value is recorded.".format(lead, column))
        if keyword == "unevaluatedProperties":
            return UNDECLARED_HINT.format(column)
        if rule is not None:
            reading = rule.reading or rule.comment or ""
            return "{} applies to this row{}".format(
                cap_first(rule.label()), ": " + reading if reading else ".")
        if column is None:
            return "Each row is an object of column: value pairs."
        allowed = self.allowed(column)
        if allowed:
            return "Allowed in {}: {}.".format(column, allowed)
        return "Check this value against {}'s definition in the data dictionary.".format(column)


UNDECLARED_HINT = ("{} is not in the data dictionary. Remove the column, or ask for it to be added "
                   "to the schemas.")
CATEGORY_EVALUATORS = ("patternProperties", "additionalProperties", "unevaluatedProperties",
                       "allOf", "anyOf", "oneOf", "if", "then", "else", "dependentSchemas", "$ref",
                       "$dynamicRef")
PLAIN_ITEMS_KEYS = frozenset(("type", "title", "description", "$comment", "allOf",
                              "unevaluatedProperties"))


def plain_table(an, model):
    """Whether a table is house-shaped enough that unevaluatedProperties:
    false means exactly "no column beyond the categories' properties": items
    holds only allOf and annotations, every entry is a resolved category or a
    parsed rule on declared properties, and no category evaluates columns any
    other way."""
    items = model.items
    if (not isinstance(items, dict) or items.get("unevaluatedProperties") is not False
            or not PLAIN_ITEMS_KEYS.issuperset(items) or model.unresolved_categories):
        return False
    rules = {rule.index: rule for rule in model.rules}
    for i, _ in enumerate(items.get("allOf") or []):
        rule = rules.get(i)
        if rule is not None:
            if not rule.grammar_ok or any(name not in model.props
                                          for name, _, _ in rule.gates + rule.targets):
                return False
        elif i not in model.category_entries:
            return False
    return not any(key in an.pkg.docs[rel] for rel in model.categories
                   for key in CATEGORY_EVALUATORS)


def finding_order(item):
    return (-1 if item["row"] is None else item["row"],
            "" if item["column"] is None else item["column"])


def nonfinite_cells(row):
    if isinstance(row, NonFinite):
        return {None: row.token}
    if not isinstance(row, dict):
        found = find_nonfinite(row)
        return {None: found[1]} if found else {}
    cells = {}
    for key, value in row.items():
        found = find_nonfinite(value)
        if found is not None:
            cells[key] = found[1]
    return cells


# ---------------------------------------------------------------- data in


def sniff_format(path):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in (".tsv", ".tab"):
        return "tsv"
    if suffix == ".json":
        return "json"
    try:
        with open(str(path), "rb") as handle:
            head = handle.read(4096).decode("utf-8", "replace").lstrip("﻿").lstrip()
    except OSError:
        return "json"
    if head[:1] in ("[", "{"):
        return "json"
    first = head.splitlines()[0] if head else ""
    return "tsv" if first.count("\t") and first.count("\t") >= first.count(",") else "csv"


def read_data(path, fmt, checker):
    """(rows, empty cells, reading findings, format) for a data file."""
    path = Path(path)
    if not path.is_file():
        raise ValidateError("Data file not found: {}".format(path),
                            "Pass --file with a JSON array of row objects, or a CSV or TSV export.")
    fmt = fmt or sniff_format(path)
    if fmt == "json":
        value, problem = read_json(path)
        if problem is not None:
            raise ValidateError("{} {}.".format(path.name, problem[0]),
                                "The file must be a JSON array of row objects; fix it at that "
                                "position (re-save it as UTF-8 if it is not).")
        if not isinstance(value, list):
            raise ValidateError("{} is not a JSON array.".format(path.name),
                                'The data is a JSON array with one object per row: [{"column": '
                                'value, ...}, ...].')
        return value, frozenset(), [], fmt
    rows, empties, notes = read_delimited(path, "," if fmt == "csv" else "\t", checker)
    return rows, empties, notes, fmt


def read_delimited(path, delimiter, checker):
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValidateError("{} could not be read ({}).".format(path.name, exc.strerror or exc),
                            "Check the path and the file's permissions.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidateError("{} is not UTF-8 text.".format(path.name),
                            "Re-save it as UTF-8 (in Excel: CSV UTF-8).")
    first = next((line for line in text.splitlines() if line.strip()), "")
    if delimiter == "," and first.count(";") > first.count(","):
        raise ValidateError(
            "{} looks semicolon-separated: its header has {} and {}.".format(
                path.name, plural(first.count(";"), "semicolon"), plural(first.count(","), "comma")),
            "Re-export it comma-separated (Excel: CSV UTF-8 (Comma delimited)), save it as TSV, "
            "or convert it to a JSON array and pass --format json.")
    csv.field_size_limit(2 ** 31 - 1)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    grid = []
    try:
        for cells in reader:
            grid.append((reader.line_num, cells))
    except csv.Error as exc:
        raise ValidateError("{} could not be read: {} (line {}).".format(
            path.name, exc, reader.line_num),
            "Check the quoting on that line; a cell holding the delimiter must be quoted.")
    grid = [(line, cells) for line, cells in grid if any(cell.strip() for cell in cells)]
    if not grid:
        return [], frozenset(), []
    names = header_names(grid[0][1])
    width = len(names)
    types = [checker.column_types(name) for name in names]
    null_ok = [kinds is not None and "null" in kinds for kinds in types]
    rows, empties, notes = [], set(), []
    for r, (line, cells) in enumerate(grid[1:]):
        if len(cells) > width:
            notes.append({"row": r, "column": None, "keyword": "csv",
                          "message": "Line {} has {} cells but the header has {}; the extra cells "
                                     "were ignored.".format(line, len(cells), width),
                          "hint": "Quote cells that contain the delimiter, or remove the stray "
                                  "cells."})
        row = {}
        for c, name in enumerate(names):
            cell = cells[c] if c < len(cells) else ""
            if cell == "":
                if null_ok[c]:
                    row[name] = None
                else:
                    empties.add((r, name))
                continue
            row[name] = read_text_cell(cell, types[c])
        rows.append(row)
    return rows, frozenset(empties), notes


def header_names(cells):
    """Header cells as column names, the way QuaC cleans them: trimmed,
    blanks named column_<n>, repeats suffixed _2, _3, ..."""
    names, taken = [], set()
    for i, cell in enumerate(cells):
        name = cell.strip() or "column_{}".format(i + 1)
        if name in taken:
            n = 2
            while "{}_{}".format(name, n) in taken:
                n += 1
            name = "{}_{}".format(name, n)
        taken.add(name)
        names.append(name)
    return names


# ----------------------------------------------------------------- reports


def check_report(an, cap=DEFAULT_CAP):
    findings = by_severity(an.findings)
    counts = tally(findings)
    shown, truncated = cap_list(findings, cap)
    tables = []
    for name, model in sorted(an.tables.items()):
        tables.append({"table": name, "mother": model.mother, "categories": list(model.categories),
                       "properties": len(model.props), "rules": len(model.rules)})
    return {"ok": counts["error"] == 0, "package": an.label, "files": len(an.pkg.files),
            "tables": tables, "counts": counts, "findings": shown, "truncated": truncated}


def rules_report(an, table=None, cap=DEFAULT_CAP):
    names = select_tables(an, table)
    rules, variables = [], {}
    mothers = {an.tables[name].mother: name for name in names}
    for name in names:
        model = an.tables[name]
        rules.extend(rule.public() for rule in model.rules if rule.grammar_ok)
        variables[name] = {prop.name: {"topic": prop.topic, "file": prop.file,
                                       "pointer": prop.pointer}
                           for prop in model.props.values()}
    findings = by_severity([
        item for item in an.findings
        if item.get("file") in mothers and (
            item["code"] in RULE_CODES or item["code"] == "parse-error"
            or str(item.get("pointer", "")).startswith("/items/allOf"))])
    counts = tally(findings)
    shown, truncated = cap_list(findings, cap)
    return {"ok": counts["error"] == 0, "rules": rules, "variables": variables, "counts": counts,
            "findings": shown, "truncated": truncated}


def fixtures_report(an, table=None, cap=DEFAULT_CAP):
    names = select_tables(an, table)
    tables, findings, with_fixtures = {}, [], 0
    coverage = {}
    for name in names:
        model = an.tables[name]
        folder = an.pkg.root / "toy-data" / name
        if not folder.is_dir():
            tables[name] = {"skipped": "no toy-data/{}/ folder yet".format(name)}
            findings.append(finding(
                "info", "fixtures-skipped", "{} has no toy data yet.".format(name),
                "Add valid.json, invalid.json and invalid-ledger.json under toy-data/{}/ "
                "(SKIP-LOGIC.md, Fixtures for every rule).".format(name), table=name))
            continue
        with_fixtures += 1
        blocked = an.blocking(model)
        if blocked:
            tables[name] = {"error": blocked}
            findings.append(finding(
                "error", "schema-errors",
                "{}'s toy data cannot be checked: {}.".format(name, blocked),
                "Run `validate.py check` and fix its parse, meta-schema and $ref errors first.",
                table=name))
            continue
        tables[name], found, coverage[name] = fixture_table(an, model, folder, cap)
        findings.extend(found)
    if with_fixtures == 0:
        findings.append(finding(
            "error", "no-fixtures", "No table has toy data yet.",
            "Add toy-data/<table>/valid.json, invalid.json and invalid-ledger.json: the toy data is "
            "the package's unit test."))
    findings = by_severity(findings)
    counts = tally(findings)
    shown, truncated = cap_list(findings, cap)
    report = {"ok": counts["error"] == 0, "tables": tables, "counts": counts, "findings": shown,
              "truncated": truncated}
    report["_coverage"] = coverage
    report["_all"] = findings
    return report


def fixture_table(an, model, folder, cap):
    base = "../toy-data/{}/".format(model.name)
    checker = RowChecker(an, model)
    findings, files = [], {}
    for fname in ("valid.json", "invalid.json", "invalid-ledger.json"):
        path = folder / fname
        files[fname] = None
        if not path.is_file():
            findings.append(finding(
                "error", "fixture-missing", "toy-data/{}/ has no {}.".format(model.name, fname),
                "Add valid.json (rows that must pass), invalid.json (one seeded violation per row) "
                "and invalid-ledger.json (one case per invalid row).", file=base + fname,
                table=model.name))
            continue
        value, problem = read_json(path)
        if problem is not None:
            findings.append(finding("error", "parse-error", "{} {}.".format(fname, problem[0]),
                                    "Make it strict JSON in UTF-8.", file=base + fname,
                                    table=model.name, line=problem[1], column=problem[2]))
            continue
        expected = dict if fname == "invalid-ledger.json" else list
        if not isinstance(value, expected) or (
                expected is dict and not isinstance(value.get("violations"), list)):
            findings.append(finding(
                "error", "fixture-shape",
                "{} is not {}.".format(fname, 'an object {"violations": [...]}' if expected is dict
                                       else "a JSON array of rows"),
                "Formats: valid.json and invalid.json are arrays of row objects; "
                'invalid-ledger.json is {"violations": [{"row", "column", "kind", "reason"}]}.',
                file=base + fname, table=model.name))
            continue
        files[fname] = value
    out = {}
    valid = files["valid.json"]
    if valid is not None:
        found = checker.check_rows(valid)
        rows = {}
        for item in found:
            rows.setdefault(item["row"], []).append(item)
        for row, items in sorted(rows.items(), key=lambda kv: -1 if kv[0] is None else kv[0]):
            column = next((item["column"] for item in items if item["column"] in model.props), None)
            prop = model.props.get(column) if column else None
            findings.append(finding(
                "error", "valid-fails",
                "valid.json {} fails: {}".format("row {}".format(row) if row is not None
                                                 else "as a whole", items[0]["message"]),
                "Every valid.json row must pass: fix the row, or the schema if the row is right.",
                file=base + "valid.json", pointer="/{}".format(row) if row is not None else None,
                table=model.name, topic=prop.topic if prop else None, variable=column,
                row=row, findings=items[:10]))
        shown, truncated = cap_list(found, cap)
        out["valid"] = {"rows": len(valid), "status": "fail" if found else "pass",
                        "findings": shown}
        if truncated:
            out["valid"]["truncated"] = True
    invalid = files["invalid.json"]
    ledger = files["invalid-ledger.json"]
    caught_rules = set()
    if invalid is not None and ledger is not None:
        out["invalid"] = judge_invalid(model, checker, invalid, ledger["violations"], base,
                                       findings, caught_rules)
        out["invalid"]["unledgered"], cut = cap_list(out["invalid"]["unledgered"], cap)
        if cut:
            out["invalid"]["truncated"] = True
    per_prop = None
    if valid is not None:
        out["coverage"], per_prop = fixture_coverage(an, model, valid, caught_rules,
                                                     "invalid" in out, findings)
    if not out:
        out["error"] = "no readable toy data (see findings)"
    return out, findings, per_prop


def judge_invalid(model, checker, rows, cases, base, findings, caught_rules):
    found = checker.check_rows(rows)
    by_row = {}
    for item in found:
        if item["row"] is not None:
            by_row.setdefault(item["row"], []).append(item)
    verdicts, caught, ledgered = [], 0, set()
    where = {"file": base + "invalid.json", "table": model.name}
    for k, case in enumerate(cases):
        case = case if isinstance(case, dict) else {}
        row, column, kind = case.get("row"), case.get("column"), case.get("kind")
        verdict = {"case": k, "row": row, "column": column, "kind": kind}
        prop = model.props.get(column) if isinstance(column, str) else None
        here = dict(where, pointer="/{}".format(row) if isinstance(row, int) else None,
                    variable=column if prop else None, topic=prop.topic if prop else None)
        if kind not in LEDGER_KINDS:
            findings.append(finding(
                "warning", "unknown-kind",
                "Ledger case {} has kind {}, which is not in the vocabulary.".format(k, show(kind)),
                "Use one of: {}.".format(", ".join(LEDGER_KINDS)),
                **dict(here, file=base + "invalid-ledger.json", pointer="/violations/{}".format(k))))
        if (isinstance(row, bool) or not isinstance(row, int) or not 0 <= row < len(rows)
                or not nonempty_str(column)):
            verdict["status"] = "phantom"
            findings.append(finding(
                "error", "phantom",
                "Ledger case {} names row {} column {}, but invalid.json has {}.".format(
                    k, show(row), show(column), plural(len(rows), "row")),
                "Point the case at a row of invalid.json (rows count from 0) and name its column.",
                **dict(here, file=base + "invalid-ledger.json", pointer="/violations/{}".format(k))))
            verdicts.append(verdict)
            continue
        ledgered.add(row)
        items = by_row.get(row, [])
        covers = [cover_of(item, checker) for item in items]
        union = set().union(*covers) if covers else set()
        failed_on = sorted(name if name != ROW_COVER else "(the row)" for name in union)
        if not items:
            verdict["status"] = "missed-passed"
            findings.append(finding(
                "error", "missed-passed",
                "invalid.json row {} ({} on {}) passes the schemas.".format(row, show(kind), column),
                "The seeded value is legal, or the rule it should trip is missing: check the value "
                "against the data dictionary, and the rule against SKIP-LOGIC.md.", row=row, **here))
        elif column not in union:
            verdict["status"] = "missed-wrong-column"
            verdict["failed_on"] = failed_on
            findings.append(finding(
                "error", "missed-wrong-column",
                "invalid.json row {} fails on {}, not on {}.".format(row, ", ".join(failed_on),
                                                                     column),
                "Fix the ledger case's column, or the seeded value, so they agree.",
                row=row, **here))
        elif all(column in cover for cover in covers):
            verdict["status"] = "caught"
            caught += 1
            rules = sorted({item["rule"] for item, cover in zip(items, covers)
                            if column in cover and item.get("rule")})
            caught_rules.update(item["allof_index"] for item, cover in zip(items, covers)
                                if column in cover and "allof_index" in item)
            if rules:
                verdict["rules"] = rules
        else:
            verdict["status"] = "caught-with-extra"
            verdict["failed_on"] = failed_on
            findings.append(finding(
                "error", "caught-with-extra",
                "invalid.json row {} fails on {} as seeded, but also on {}.".format(
                    row, column, ", ".join(name for name in failed_on if name != column)),
                "Change the row so it breaks only {}: one seeded violation per row.".format(column),
                row=row, **here))
        verdicts.append(verdict)
    unledgered = sorted(row for row in by_row if row not in ledgered)
    for row in unledgered:
        names = sorted({item["column"] or "(the row)" for item in by_row[row]})
        findings.append(finding(
            "error", "unledgered",
            "invalid.json row {} fails ({}) but the ledger has no case for it.".format(
                row, ", ".join(names)),
            "Add a ledger case naming its column and kind, or fix the row.", row=row,
            **dict(where, pointer="/{}".format(row))))
    return {"rows": len(rows), "cases": len(cases), "caught": caught, "verdicts": verdicts,
            "unledgered": unledgered}


def cover_of(item, checker):
    """The columns a finding counts as failing: its own; *duplicate* for a
    repeated row; or, for a row-level 'at least one of' rule, its targets."""
    if item["column"] is not None:
        return {item["column"]}
    if item["keyword"] == "uniqueItems":
        return {DUPLICATE_COLUMN}
    rule = checker.rules.get(item.get("allof_index"))
    if rule is not None and rule.mode == "any" and rule.targets:
        return {name for name, _, _ in rule.targets}
    return {ROW_COVER}


def fixture_coverage(an, model, valid, caught_rules, judged, findings):
    seen = {}
    for row in valid:
        if isinstance(row, dict):
            for key, value in row.items():
                seen.setdefault(key, set()).add(literal_key(value))
    covered, total, per_prop = 0, 0, {}
    for name, prop in model.props.items():
        wanted = required_values(prop.profile())
        if wanted is None:
            continue
        total += 1
        missing = [value for value in wanted if literal_key(value) not in seen.get(name, ())]
        per_prop[name] = not missing
        if missing:
            listed = joined(missing, "or") if len(missing) <= 8 else show_list(missing)
            findings.append(finding(
                "warning", "coverage-gap",
                "valid.json never shows {} = {}.".format(name, listed),
                "Add valid rows using {}, so every declared code (or both bounds and every special "
                "code) is seen to pass.".format(show_list(missing)),
                file=prop.file, pointer=prop.pointer, table=model.name, topic=prop.topic,
                variable=name))
        else:
            covered += 1
    fired, unfired, caught, uncaught = [], [], [], []
    for rule in model.rules:
        if not rule.grammar_ok:
            continue
        label = rule.half()
        test = Draft202012Validator({"$ref": "{}#/items/allOf/{}/if".format(model.uri, rule.index)},
                                    registry=an.pkg.registry)
        hit = False
        for row in valid:
            try:
                if test.is_valid(row):
                    hit = True
                    break
            except Exception:
                break
        where = {"file": model.mother, "pointer": rule.pointer, "table": model.name,
                 "rule": rule.id}
        if hit:
            fired.append(label)
        else:
            unfired.append(label)
            findings.append(finding(
                "warning", "coverage-gap",
                "No valid.json row triggers {}.".format(rule.label()),
                "Add a valid row the rule applies to, so it is seen working.", **where))
        if rule.index in caught_rules:
            caught.append(label)
        else:
            uncaught.append(label)
        if judged and rule.index not in caught_rules:
            findings.append(finding(
                "warning", "coverage-gap",
                "No invalid.json row is caught by {}.".format(rule.label()),
                "Seed an invalid.json row that breaks it and ledger it ({}-break).".format(
                    rule.kind if rule.kind in ("skip", "applicability", "routing") else "routing"),
                **where))
    return ({"properties": {"covered": covered, "total": total},
             "rules": {"fired": fired, "unfired": unfired, "caught": caught,
                       "uncaught": uncaught}}, per_prop)


def public_fixtures(report):
    return {key: value for key, value in report.items() if not key.startswith("_")}


def data_report(an, file, table=None, fmt=None, cap=DEFAULT_CAP):
    if table is None and len(an.tables) != 1:
        raise ValidateError(
            "The package has {}; say which one the file holds.".format(
                plural(len(an.tables), "table")) if an.tables else "The package has no table.",
            "Pass --table <name> ({}).".format(", ".join(sorted(an.tables)) or "none yet"))
    name = select_tables(an, table)[0] if table is not None else next(iter(an.tables))
    model = an.tables[name]
    blocked = an.blocking(model)
    if blocked:
        raise ValidateError("Cannot validate against {}: {}.".format(name, blocked),
                            "Run `validate.py check` and fix its errors first.")
    checker = RowChecker(an, model)
    rows, empties, notes, fmt = read_data(file, fmt, checker)
    findings = sorted(checker.check_rows(rows, empties) + notes, key=finding_order)
    by_column, by_rule = {}, {}
    for item in findings:
        if item["column"] is not None:
            by_column[item["column"]] = by_column.get(item["column"], 0) + 1
        if item.get("rule"):
            by_rule[item["rule"]] = by_rule.get(item["rule"], 0) + 1
    shown, truncated = cap_list(findings, cap)
    columns = {prop.name: {"title": prop.schema.get("title") if isinstance(prop.schema, dict)
                           and nonempty_str(prop.schema.get("title")) else None,
                           "topic": prop.topic, "allowed": checker.allowed(prop.name)}
               for prop in model.props.values()}
    return {"ok": not findings, "table": name, "file": str(file), "format": fmt,
            "rows": len(rows), "errors": len(findings), "by_column": by_column,
            "by_rule": by_rule, "findings": shown, "truncated": truncated, "columns": columns}


def provenance_census(an):
    props = [prop for model in an.tables.values() for prop in model.props.values()]
    traced = sum(1 for prop in props if an.prov_ok.get((prop.file, prop.pointer)))
    rules = sum(1 for model in an.tables.values() for rule in model.rules
                if an.prov_ok.get((model.mother, rule.pointer)))
    by_origin = dict.fromkeys(("document", "web", "person", "agent", "unknown"), 0)
    review = set()
    for ref in an.prov_refs:
        by_origin[an.prov.origin(ref)] += 1
        if an.prov.needs_review(ref):
            review.add(ref.split(":", 1)[0])
    return {"properties": len(props), "traced": traced, "rules": rules, "by_origin": by_origin,
            "needs_review": sorted(review)}


def summary_report(an, out=None, cap=DEFAULT_CAP):
    check = check_report(an, None)
    rules = rules_report(an, None, None)
    blockers = [item for item in an.findings if item["code"] in BLOCKING_CODES
                and item["severity"] == "error" and not item.get("file", "").startswith("../")]
    fixtures = None if blockers or not an.tables else fixtures_report(an, None, None)
    census = provenance_census(an)
    every = by_severity(an.findings + (fixtures["_all"] if fixtures else []))
    counts = tally(every)
    ok = check["ok"] and fixtures is not None and fixtures["ok"]
    by_kind = {"skip": 0, "applicability": 0, "routing": 0}
    by_table = {}
    for rule in rules["rules"]:
        by_kind[rule["kind"]] = by_kind.get(rule["kind"], 0) + 1
        by_table[rule["table"]] = by_table.get(rule["table"], 0) + 1
    rule_counts = {"count": len(rules["rules"]), "by_kind": by_kind, "by_table": by_table}
    headline = make_headline(an, check, rule_counts, fixtures, census, bool(blockers))
    topics = topic_summary(an, every, fixtures)
    fixtures_full = (public_fixtures(fixtures) if fixtures is not None else {
        "skipped": "the schemas have parse, meta-schema or $ref errors" if blockers
        else "the package has no table"})
    if out is not None:
        full = {"ok": ok, "headline": headline, "package": an.label, "counts": counts,
                "check": check, "rules": dict(rule_counts, items=rules["rules"],
                                              variables=rules["variables"]),
                "fixtures": fixtures_full, "provenance": census, "topics": topics}
        write_report(out, full)
        shown, truncated = cap_list(every, COMPACT_FINDINGS)
        return {"ok": ok, "headline": headline, "package": an.label, "counts": counts,
                "findings": shown, "truncated": truncated, "topics": topics, "report": str(out)}
    check_shown, check_truncated = cap_list(by_severity(an.findings), cap)
    compact_check = {"ok": check["ok"], "files": check["files"], "tables": check["tables"],
                     "counts": check["counts"], "findings": check_shown,
                     "truncated": check_truncated}
    if fixtures is not None:
        fixture_findings, fixture_truncated = cap_list(fixtures["_all"], cap)
        compact_fixtures = {"ok": fixtures["ok"], "tables": {}, "counts": fixtures["counts"],
                            "findings": fixture_findings, "truncated": fixture_truncated}
        for name, entry in fixtures["tables"].items():
            if "valid" in entry or "invalid" in entry or "coverage" in entry:
                compact = {}
                if "valid" in entry:
                    compact["valid"] = {"rows": entry["valid"]["rows"],
                                        "status": entry["valid"]["status"]}
                if "invalid" in entry:
                    compact["invalid"] = {key: entry["invalid"][key]
                                          for key in ("rows", "cases", "caught")}
                    compact["invalid"]["unledgered"] = entry["invalid"]["unledgered"][:cap]
                if "coverage" in entry:
                    compact["coverage"] = entry["coverage"]
                compact_fixtures["tables"][name] = compact
            else:
                compact_fixtures["tables"][name] = entry
    else:
        compact_fixtures = fixtures_full
    return {"ok": ok, "headline": headline, "package": an.label, "counts": counts,
            "check": compact_check, "rules": rule_counts, "fixtures": compact_fixtures,
            "provenance": census, "topics": topics}


def make_headline(an, check, rule_counts, fixtures, census, blocked):
    parts = []
    files, errors, warnings = check["files"], check["counts"]["error"], check["counts"]["warning"]
    if files == 0:
        parts.append("no schema files yet")
    elif errors == 0:
        parts.append("{} valid{}".format(plural(files, "schema file"),
                                         " ({})".format(plural(warnings, "warning"))
                                         if warnings else ""))
    else:
        parts.append("{}: {} to fix{}".format(plural(files, "schema file"), plural(errors, "error"),
                                              ", {}".format(plural(warnings, "warning"))
                                              if warnings else ""))
    count = rule_counts["count"]
    parts.append(plural(count, "rule") if count else "no rules")
    if blocked:
        parts.append("toy data not checked until the schema errors are fixed")
    elif fixtures is None or not any("valid" in entry or "invalid" in entry
                                     for entry in fixtures["tables"].values()):
        parts.append("no toy data yet")
    else:
        rows = cases = caught = 0
        unread_valid = unread_invalid = False
        for entry in fixtures["tables"].values():
            if "valid" in entry:
                rows += entry["valid"]["rows"]
            elif "invalid" in entry:
                unread_valid = True
            if "invalid" in entry:
                cases += entry["invalid"]["cases"]
                caught += entry["invalid"]["caught"]
            elif "valid" in entry:
                unread_invalid = True
        failing = len({(item.get("table"), item["row"]) for item in fixtures["_all"]
                       if item["code"] == "valid-fails" and item.get("row") is not None})
        if unread_valid and not rows:
            valid_text = "valid.json unreadable"
        elif failing:
            valid_text = "{}/{} valid rows pass".format(rows - failing, rows)
        else:
            valid_text = "{} pass{}".format(plural(rows, "valid row"), "es" if rows == 1 else "")
        if unread_invalid and not cases:
            seeded = "seeded-error files missing or unreadable"
        elif cases:
            seeded = "{}/{} seeded {} caught".format(caught, cases,
                                                     "error" if cases == 1 else "errors")
        else:
            seeded = "no seeded errors"
        parts.append("toy data: {}, {}".format(valid_text, seeded))
    if census["properties"]:
        text = "provenance: {}/{} traced".format(
            census["traced"], plural(census["properties"], "property", "properties"))
        review = census["needs_review"]
        if review:
            guesses = all(an.prov.entry(ref_id) is not MISSING
                          and an.prov.entry(ref_id).get("kind") == "guess" for ref_id in review)
            noun = plural(len(review), "guess", "guesses") if guesses else plural(
                len(review), "decision")
            text += " ({} {} review)".format(noun, "needs" if len(review) == 1 else "need")
        parts.append(text)
    return " · ".join(parts)


def topic_summary(an, every, fixtures):
    topics = {}
    for name, model in sorted(an.tables.items()):
        per_prop = (fixtures or {}).get("_coverage", {}).get(name)
        for rel in model.categories:
            topic = PurePosixPath(rel).stem
            props = [prop for prop in model.props.values() if prop.file == rel]
            names = {prop.name for prop in props}
            errors = sum(1 for item in every if item.get("table") == name
                         and item.get("topic") == topic and item["severity"] == "error")
            warnings = sum(1 for item in every if item.get("table") == name
                           and item.get("topic") == topic and item["severity"] == "warning")
            prov_errors = any(item.get("file") == rel and item["code"].startswith("provenance-")
                              and item["severity"] == "error" for item in every)
            entry = {"file": rel, "properties": len(props),
                     "rules_targeting": sum(1 for rule in model.rules
                                            if any(t in names for t, _, _ in rule.targets)),
                     "errors": errors, "warnings": warnings,
                     "provenance_ok": not prov_errors and all(
                         an.prov_ok.get((prop.file, prop.pointer)) for prop in props),
                     "coverage": None}
            if per_prop is not None:
                counted = [prop.name for prop in props if prop.name in per_prop]
                entry["coverage"] = {"covered": sum(1 for n in counted if per_prop[n]),
                                     "total": len(counted)}
            topics["{}/{}".format(name, topic)] = entry
    return topics


def write_report(out, report):
    path = Path(out)
    refuse_skill_dir(path, "--out")
    try:
        if path.parent and not path.parent.is_dir():
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dumps(report) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ValidateError("Could not write {} ({}).".format(out, exc.strerror or exc),
                            "Pass --out a path in a folder you can write to.")


# --------------------------------------------------------------------- CLI


def _sanitize(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def dumps(payload, ascii_only=False):
    try:
        return json.dumps(payload, indent=2, ensure_ascii=ascii_only, allow_nan=False, default=str)
    except ValueError:
        return json.dumps(_sanitize(payload), indent=2, ensure_ascii=ascii_only, default=str)


def emit(payload):
    try:
        sys.stdout.write(dumps(payload) + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(dumps(payload, ascii_only=True) + "\n")
    sys.stdout.flush()


class _HelpRequested(Exception):
    def __init__(self, text):
        Exception.__init__(self, text)
        self.text = text


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValidateError("Usage: {}.".format(message),
                            "Run `validate.py --help`; subcommands: check, rules, fixtures, data, "
                            "summary.")

    def print_help(self, file=None):
        raise _HelpRequested(self.format_help())

    def exit(self, status=0, message=None):
        raise ValidateError(message or "Usage error.", "Run `validate.py --help`.")


def _count(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("{!r} is not a whole number".format(text))
    if value < 0:
        raise argparse.ArgumentTypeError("{} is negative".format(value))
    return value


def build_parser():
    parser = _Parser(prog="validate.py", description=__doc__,
                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", parser_class=_Parser)
    sub.required = True
    helps = {"check": "lint the schema files", "rules": "print every rule, normalized",
             "fixtures": "run the toy data", "data": "validate one data file",
             "summary": "everything, with a headline"}
    for name in ("check", "rules", "fixtures", "data", "summary"):
        command = sub.add_parser(name, help=helps[name])
        command.add_argument("package", help="the package root (the folder holding schemas/)")
        command.add_argument("--max-findings", type=_count, default=DEFAULT_CAP,
                             help="cap on each findings list (default 200)")
        if name in ("rules", "fixtures", "data"):
            command.add_argument("--table", help="one table (a folder under schemas/)")
        if name == "data":
            command.add_argument("--file", required=True, help="a JSON, CSV or TSV data file")
            command.add_argument("--format", choices=("json", "csv", "tsv"),
                                 help="default: from the file's extension")
            command.add_argument("--max-errors", type=_count, default=None,
                                 help="cap on the findings list (default 200)")
        if name == "summary":
            command.add_argument("--out", help="write the full report to this JSON file")
    return parser


def dependency_problem():
    if _IMPORT_ERROR is not None:
        return "jsonschema and referencing are not installed ({}).".format(_IMPORT_ERROR)
    try:
        Draft202012Validator({}, registry=Registry())
    except TypeError:
        return "The installed jsonschema is older than 4.18."
    return None


def dispatch(args):
    cap = args.max_findings
    if args.command == "check":
        return check_report(analyze(args.package), cap)
    if args.command == "rules":
        return rules_report(analyze(args.package), args.table, cap)
    if args.command == "fixtures":
        return public_fixtures(fixtures_report(analyze(args.package), args.table, cap))
    if args.command == "data":
        limit = args.max_errors if args.max_errors is not None else cap
        return data_report(analyze(args.package), args.file, args.table, args.format, limit)
    return summary_report(analyze(args.package), args.out, cap)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        try:
            args = build_parser().parse_args(argv)
        except _HelpRequested as wanted:
            emit({"ok": True, "help": wanted.text})
            sys.exit(0)
        problem = dependency_problem()
        if problem is not None:
            raise ValidateError(problem, "Run it with uv (`uv run validate.py ...`), or install "
                                         "the dependencies: {}".format(PIP_FALLBACK))
        result = dispatch(args)
        code = 0 if result.get("ok") else 1
    except ValidateError as exc:
        result, code = {"ok": False, "error": exc.error, "hint": exc.hint}, 2
    except KeyboardInterrupt:
        result, code = {"ok": False, "error": "Interrupted.",
                        "hint": "Run it again; validate.py writes nothing but --out."}, 2
    except Exception as exc:  # never a traceback: one line on stderr, JSON on stdout
        frame = traceback.extract_tb(exc.__traceback__)[-1] if exc.__traceback__ else None
        sys.stderr.write("validate.py: internal error {}: {}{}\n".format(
            type(exc).__name__, exc, " (line {} in {})".format(frame.lineno, frame.name)
            if frame else ""))
        result, code = {"ok": False,
                        "error": "validate.py failed unexpectedly: {}: {}".format(
                            type(exc).__name__, clip(exc, 200)),
                        "hint": "This is a validator bug, not a problem with your files; "
                                "report it with the line printed on stderr."}, 2
    emit(result)
    sys.exit(code)


if __name__ == "__main__":
    main()
