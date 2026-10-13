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
                                              "kind", "value"?, "path"?,
                                              "reason"}]}
    provenance.json                          what x-provenance cites (optional)

Fields and paths. Every record-level property is a field (a column), and so is
every field inside a nested value, named by its path as the data dictionary
writes it: the column as is, then .name (or ["odd name"]), [] for each entry of
a list, .* for each value of a lookup - household[].age, address.city,
labs.*. A field's "shape" is "value", "group" (an object with properties),
"lookup" (an object with an additionalProperties schema), "list" (an array of
values), "entries" (an array of groups) or "mixed" (typed branches of two or
more JSON types); special-code branches beside a group or list leave its shape
as is. A display path puts 1-based positions in the brackets
(household[2].age); a field never has positions.

Subcommands (each also takes --max-findings N, default 200):

check PKG
    Every schema file parses, meta-validates against draft 2020-12 and names
    it in $schema; $ids share one base and mirror their paths; every $ref
    resolves; the house style (SCHEMA-STYLE.md) and the rule grammar
    (SKIP-LOGIC.md) hold, inside nested values too; every x-provenance
    reference is well formed and, when provenance.json exists, names a
    citable source or decision.
    -> {"ok", "package", "files", "tables": [{"table", "mother",
        "categories", "properties" (columns), "fields" (fields inside
        nested values), "rules"}], "counts", "findings", "truncated"}

rules PKG [--table T]
    Every rule, normalized: a rule entry of a mother's items.allOf (scope
    null), or of a nested object's own allOf - a group's, or a list's items -
    whose scope is that object's path (address, household[]):
    {"table", "id", "kind": "skip"|"applicability"|"routing", "domain",
     "scope", "index" (position in its allOf), "file", "pointer", "comment",
     "reading", "provenance",
     "when": {"any": [{"all": [TEST, ...]}, ...]},
     "then": {"mode": "all"|"any", "effects": [EFFECT, ...]}}
    TEST   {"variable", "test": "eq"|"ne", "value"}
           {"variable", "test": "in"|"nin", "values"}
           {"variable", "test": "includes"|"excludes", "value"} - a list of
            values holds value, or does not ({"contains": {"const": v}},
            {"not": {"contains": {"const": v}}})
           {"variable", "test": "range", "type", BOUNDS, "excludes"}
           {"variable", "test": "present"} - a name in a clause's required
            with no test of its own: the field is in the record or object
    EFFECT {"variable", "effect": "eq"|"ne", "value"}
           {"variable", "effect": "in", "values"}
           {"variable", "effect": "range", "type", BOUNDS, "excludes",
            "also": [code values still allowed, read through $ref]}
           {"variable", "effect": "empty"|"nonempty"} - a list is empty, or
            has at least one entry ({"maxItems": 0}, {"minItems": 1});
            routing rules only
           {"variable", "effect": "count", "minItems"?, "maxItems"?} - a
            list holds that many entries ({"maxItems": 1}: a code that stands
            alone); routing rules only
           {"variable", "effect": "present"|"absent"} - a name in then's
            required, or a target whose effect is false
    A presence test or effect names a field the data may leave out: one its
    object's required omits (a column, its category's).
    "variable" is a field's full path: a nested rule's own names under its
    scope (household[].relation), and a record-level rule's clause on a
    group's fields - {"required": [f], "properties": {f: test}} as the test,
    {"properties": {f: effect}} and/or {"required": [f]} as the effect -
    names group.f (groups only, never a list's entries).
    BOUNDS: whichever of minimum, maximum, exclusiveMinimum and
    exclusiveMaximum the rule states. Entries that do not parse are left out
    and reported in findings, with the codes check gives them.
    -> {"ok", "rules", "variables": {table: {path: {"topic", "file",
        "pointer", "shape", "parent", "title"}}} for every field, columns
        included, "counts", "findings", "truncated"}

fixtures PKG [--table T]
    For each table with a toy-data folder: every valid.json row passes; each
    invalid.json row fails on exactly the column its ledger case names
    (verdicts: caught, caught-with-extra, missed-wrong-column, missed-passed,
    phantom; failing rows with no case are unledgered); coverage of codes,
    bounds, special codes, list lengths and rules is reported as warnings.
    A case's "column" is a column or a field path (household[].age; a
    concrete key under a lookup, labs.ldl, counts as labs.*; "path", a display
    path, is accepted and ignored). A finding covers its field and every
    path enclosing it (household[].age covers household[] and household),
    so a case is caught when every finding of its row covers its column.
    Kinds: wrong-type, unknown-level, range-break, invented-sentinel,
    pattern-break, skip-break, applicability-break, routing-break,
    missing-key (a field left out of a record, group or entry),
    undeclared-column (a column or a field nobody declares), duplicate-row,
    entry-count (too few or too many entries, or a list's contains count),
    duplicate-entry (a repeated entry of a list).
    Coverage counts every field with something to show: codes and bounds as
    always (a list's codes in its entries); a list with its fewest entries
    allowed and one with two or more; a lookup with a name; a field a
    decision lets be left out, left out once; every rule fired (a nested
    rule by some object in its scope) and caught.
    -> {"ok", "tables": {table: {"valid": {"rows", "status", "findings"},
        "invalid": {"rows", "cases", "caught", "verdicts", "unledgered"},
        "coverage": {"properties": {"covered", "total"} (fields of every
        depth), "rules": {"fired", "unfired", "caught", "uncaught"}}}},
        "counts", "findings", "truncated"}
    verdict: {"case", "row", "column", "kind", "status", "failed_on"? (the
              failing findings' fields), "rules"?}; a table without toy data
              is {"skipped": why}

data PKG --file F [--table T] [--format json|csv|tsv] [--max-errors N]
    Validate one data file - a JSON array of row objects, or a CSV or TSV
    export - row by row; CSV and TSV cells are typed the way QuaC types them
    (a cell of a group or list column holds its value as JSON text).
    The schemify agent never runs this on real data; people may run it on
    their own files.
    -> {"ok", "table", "file", "format", "rows", "errors", "by_column",
        "by_rule", "findings", "truncated", "columns", "fields"}
    finding: {"row" (0-based record), "column", "field", "path", "keyword",
              "message", "hint", "rule"?, "allof_index"? (a mother's rule),
              "rule_scope"? (a nested rule's scope), "empty_cell"?} -
              "column" is the record-level key, "path" the display path
              (household[2].age; a missing field's own path; an undeclared
              field's, one finding each; a list's own path for minItems,
              maxItems, uniqueItems and contains), "field" the path without
              positions (household[].age; labs.* for any key of a lookup);
              all three are equal for a column and null for a finding about a
              whole row (a repeated row: "row" is the later copy) or the whole
              file (too few rows: "row" null too)
    columns: {name: {"title", "topic", "allowed"}} for every declared
             property, in table order; "allowed" says what the column takes
    fields: {path: {"title", "topic", "column", "allowed", "shape"}} for
            every field inside a nested value

summary PKG [--out FILE]
    check + rules + fixtures (when every schema parses, meta-validates and
    resolves) + a provenance census, with a plain-English headline.
    -> {"ok", "headline", "package", "counts", "check", "rules": {"count",
        "by_kind", "by_table"}, "fixtures", "provenance": {"properties"
        (every field, nested ones included), "traced", "rules", "by_origin",
        "needs_review"}, "topics": {"<table>/<topic>": {"file", "properties",
        "fields", "rules_targeting", "errors", "warnings", "provenance_ok",
        "coverage"}}}
    --out FILE writes the full report there - every finding and verdict, and
    "rules": {"count", "by_kind", "by_table", "items" (every rule, as rules
    prints it), "variables"} - and prints only {"ok", "headline", "package",
    "counts", "findings" (the first 20), "truncated", "topics", "report"}.

A finding of check, rules, fixtures and summary:
    {"severity": "error"|"warning"|"info", "code", "message", "hint",
     "file" (relative to PKG/schemas), "pointer", "table", "topic",
     "variable" (a field's path), "rule"} - keys that do not apply are left
    out. ok is false when any finding is an error.

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
    "multipleOf": "it invites precision the source never stated, and a decimal step is "
                  "unreliable in validators (72.3 is not a float multiple of 0.1)",
    "minLength": "it invites precision the source never stated; keep it only when a source "
                 "states the limit, cited on x-provenance's minLength facet",
    "maxLength": "it invites precision the source never stated; keep it only when a source "
                 "states the limit, cited on x-provenance's maxLength facet",
    "$anchor": "relative paths plus #/$defs/... are the whole addressing scheme",
    "$dynamicRef": "relative paths plus #/$defs/... are the whole addressing scheme",
    "prefixItems": "positions with meanings are not what dictionaries describe; give each "
                   "value its own named field in a group",
    "unevaluatedItems": "a list states what its entries hold in items",
    "patternProperties": "keys matched by pattern are not what dictionaries describe; a "
                         "lookup states its names with propertyNames",
    "minProperties": "counts of properties are not what dictionaries describe",
    "maxProperties": "counts of properties are not what dictionaries describe",
    "contains": "it constrains a list as a whole: use it on a list (cited on x-provenance's "
                "contains facet) or as a rule's test",
    "minContains": "it constrains a list as a whole: use it on a list beside contains",
    "maxContains": "it constrains a list as a whole: use it on a list beside contains",
}
CONTAINS_KEYS = ("contains", "minContains", "maxContains")
LENGTH_KEYS = ("minLength", "maxLength")
FORBIDDEN = ("else", "dependentRequired", "dependentSchemas")
CATEGORY_FORBIDDEN = ("if", "then", "else", "allOf", "anyOf", "oneOf", "not",
                      "dependentSchemas", "dependentRequired", "additionalProperties",
                      "unevaluatedProperties")
FACETS = frozenset(("default", "title", "description", "type", "values", "sentinels",
                    "minimum", "maximum", "pattern", "unit", "universe", "derivation",
                    "required", "minItems", "maxItems", "uniqueItems", "propertyNames",
                    "contains", "minLength", "maxLength"))
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
                "missing-key", "undeclared-column", "duplicate-row", "entry-count",
                "duplicate-entry")
DUPLICATE_COLUMN = "*duplicate*"
ROW_COVER = "*row*"
RULE_CODES = frozenset(("rule-shape", "rule-comment", "rule-unguarded", "rule-dangling",
                        "rule-undeclared-code", "trigger-undeclared-level",
                        "range-trigger-sentinel", "skip-shape", "applicability-shape",
                        "missing-twin", "duplicate-rule", "allof-order", "allof-entry",
                        "rule-in-shared-shape"))
BLOCKING_CODES = frozenset(("parse-error", "meta-invalid", "unresolved-ref"))

# Nested values. A path names a Field the way the data dictionary (jsdd's
# formatVariablePath) does: the record-level key as is, then .name or
# ["name"], [] for a list's entries, .* for a lookup's values. The class is
# JavaScript's \s, so a name is plain here exactly when it is plain on the
# website (schemify.py holds the same pattern).
NAME_CHARS = r'[^.\[\]"*\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]'
PLAIN_NAME = re.compile(r'(?!/)' + NAME_CHARS + '+')
PATH_STEP = re.compile(r'\.\*|\[\]|\[[0-9]+\]|\["(?:[^"\\]|\\.)*"\]|\.' + NAME_CHARS + '+')
MAX_DEPTH = 6                   # fields at most six levels below their column
FIELD_LIMIT = 10000             # fields inside nested values per table; schemify.py stops there too
SHAPE_KEYS = frozenset(("type", "properties", "items", "prefixItems", "additionalProperties",
                        "anyOf", "oneOf", "allOf", "const", "enum", "not", "if"))
DECISION_RE = re.compile(r"D[0-9]{3,}")
GATHER_LIMIT = 32

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


def joined_plain(names, last="and"):
    names = [str(name) for name in names]
    return names[0] if len(names) == 1 else "{} {} {}".format(", ".join(names[:-1]), last, names[-1])


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


def join_path(parent, name):
    """The path of a field named name inside parent (None: a record-level
    key, kept as is) - jsdd's formatVariablePath."""
    if parent is None:
        return name
    return parent + ("." + name if PLAIN_NAME.fullmatch(name)
                     else "[" + json.dumps(name, ensure_ascii=False) + "]")


def path_ancestors(column, field):
    """column, every path that encloses field, and field itself
    (household[].age -> household, household[], household[].age)."""
    out = {column}
    if not isinstance(field, str) or not field.startswith(column):
        return out
    here, at = column, len(column)
    while at < len(field):
        step = PATH_STEP.match(field, at)
        if step is None:
            break
        here += step.group(0)
        at = step.end()
        out.add(here)
    out.add(field)
    return out


def cites_decision(provenance, facet):
    """Whether x-provenance cites a decision (D...) on facet."""
    refs = provenance.get(facet) if isinstance(provenance, dict) else None
    refs = [refs] if isinstance(refs, str) else refs if isinstance(refs, list) else []
    return any(isinstance(ref, str) and DECISION_RE.fullmatch(ref) for ref in refs)


def json_kinds(node):
    """The JSON types a schema node holds, from its type or else its object
    or array keywords (integer counts as number; null is a special code, not
    a shape)."""
    if not isinstance(node, dict):
        return set()
    kind = node.get("type")
    kinds = ([kind] if isinstance(kind, str) else
             [k for k in kind if isinstance(k, str)] if isinstance(kind, list) else [])
    if not kinds:
        if "properties" in node or "additionalProperties" in node:
            kinds = ["object"]
        elif "items" in node or "prefixItems" in node:
            kinds = ["array"]
    return {"number" if k == "integer" else k for k in kinds if k != "null"}


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
        text = ("text matching {}".format(node["pattern"]) if nonempty_str(node.get("pattern"))
                else "text")
        shortest, longest = node.get("minLength"), node.get("maxLength")
        shortest = int(shortest) if is_integral(shortest) else None
        longest = int(longest) if is_integral(longest) else None
        if shortest is not None and longest is not None:
            text += " of {} to {} characters".format(shortest, longest)
        elif longest is not None:
            text += " of at most {}".format(plural(longest, "character"))
        elif shortest is not None:
            text += " of at least {}".format(plural(shortest, "character"))
        return text
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


def json_types(pkg, node, resolver, depth=0, seen=frozenset(), memo=None):
    """The JSON types a value can have and still pass node, as QuaC derives
    them (value-spec.ts): anyOf/oneOf unite, $ref/allOf/type/const/enum
    intersect; None means unconstrained. A definition reached by many paths
    is read once per depth (memo)."""
    if isinstance(node, bool):
        return None if node else set()
    if not isinstance(node, dict) or depth > 12 or id(node) in seen:
        return None
    memo = {} if memo is None else memo
    if (id(node), depth) in memo:
        return memo[(id(node), depth)]
    seen = seen | {id(node)}
    contributions = []
    if isinstance(node.get("$ref"), str):
        resolved, _ = pkg.lookup_from(resolver, node["$ref"])
        contributions.append(None if resolved is None else json_types(
            pkg, resolved.contents, resolved.resolver, depth + 1, seen, memo))
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
                found = json_types(pkg, branch, resolver, depth + 1, seen, memo)
                if found is None:
                    unconstrained = True
                else:
                    union |= found
            contributions.append(None if unconstrained else union)
    if isinstance(node.get("allOf"), list):
        contributions.extend(json_types(pkg, branch, resolver, depth + 1, seen, memo)
                             for branch in node["allOf"])
    constrained = [c for c in contributions if c is not None]
    result = set(constrained[0]) if constrained else None
    for other in constrained[1:]:
        result = intersect_types(result, other)
    memo[(id(node), depth)] = result
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


class ShapeInfo(object):
    """What a schema node holds: shape "value", "group", "lookup", "list",
    "entries" or "mixed", and the resolved nodes that say so."""

    def __init__(self, node, rel):
        self.shape = "value"
        self.node, self.rel = node, rel      # the shape-bearing node, $refs followed
        self.obj = self.obj_rel = None       # group: its object node
        self.arr = self.arr_rel = None       # list, entries: the array node
        self.items = None                    # ... and its items, as written
        self.items_info = None               # ... and what the items hold
        self.lookup = self.lookup_rel = None  # lookup: its object node
        self.values = None                   # ... and its additionalProperties schema
        self.branches = []                   # every typed branch (two or more kinds: mixed)


class Field(object):
    """One variable: a record-level property (depth 0, a column), or a field
    inside a nested value, named by its path (household[].age)."""

    def __init__(self, an, table, path, rel, pointer, topic, schema, name=None, parent=None,
                 depth=0, top=None):
        self.an = an
        self.table = table
        self.path = path
        self.name = path if name is None else name
        self.parent = parent
        self.depth = depth
        self.top = path if top is None else top
        self.file = rel
        self.pointer = pointer
        self.topic = topic
        self.schema = schema
        self.uri = an.pkg.uri[rel]
        self.shape = "value"
        self.info = None
        self.scope = None          # the object holding it: None for the record, else a path
        self.optional = False      # may be left out of its object (a cited decision says so)
        self.omittable = False     # its object's required leaves it out, cited or not
        self._validator = None
        self._profile = None
        self._item_profile = MISSING
        self._types = MISSING

    def title(self):
        title = self.schema.get("title") if isinstance(self.schema, dict) else None
        return title if nonempty_str(title) else None

    def admits(self, value):
        """True/False: does the field's own schema accept value; None when
        that cannot be told (an unresolvable schema)."""
        if self._validator is None:
            target = "{}#{}".format(self.uri, quote(self.pointer, safe="/~"))
            self._validator = Draft202012Validator({"$ref": target},
                                                   registry=self.an.pkg.registry)
        try:
            return bool(self._validator.is_valid(value))
        except Exception:
            return None

    def admits_item(self, value):
        """Does one entry of this list accept value (None: cannot tell)."""
        items = self.info.items if self.info is not None else None
        return self.an.node_admits(items, value) if items is not None else None

    def profile(self):
        if self._profile is None:
            self._profile = value_profile(self.an.pkg, self.schema,
                                          self.an.pkg.resolver(self.uri))
        return self._profile

    def item_profile(self):
        """The profile of one entry of a list of values, or None."""
        if self._item_profile is MISSING:
            info = self.info
            self._item_profile = None
            if self.shape == "list" and info is not None and info.items is not None:
                self._item_profile = value_profile(self.an.pkg, info.items,
                                                   self.an.pkg.resolver(self.an.pkg.uri[info.arr_rel]))
        return self._item_profile

    def codes(self):
        """The codes the field declares: a list's are its entries'."""
        profile = self.item_profile() if self.shape == "list" else self.profile()
        return [code.value for code in profile["codes"]] if profile else []

    def declared_codes(self):
        """Every code a value:<code> facet may cite: a list's entries' codes and
        the codes beside the list itself (a special code or null in its place)."""
        if self.shape != "list":
            return self.codes()
        return self.codes() + [code.value for code in self.profile()["codes"]]

    def required_values(self):
        profile = self.item_profile() if self.shape == "list" else self.profile()
        return required_values(profile) if profile else None

    def allowed_text(self):
        """What the field takes, in words (the data dictionary's terms)."""
        if self.info is None or self.shape == "value" or (self.shape == "mixed" and not any(
                branch.shape != "value" for branch in self.info.branches)):
            return describe_allowed(self.profile())
        text = self.an.container_text(self.info)
        codes = dedupe_values([code.value for code in self.profile()["codes"]])
        if codes:
            named = {literal_key(code.value): code for code in self.profile()["codes"]}
            listed = ", ".join(code_text(named[literal_key(value)]) for value in codes[:10])
            text += ", or " + ("one of " if len(codes) > 1 else "") + listed
        return text

    def item_allowed_text(self):
        profile = self.item_profile()
        return describe_allowed(profile) if profile else None

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
        self.props = {}            # record-level Fields, by column
        self.fields = {}           # every Field, by path, in schema order
        self.rule_entries = []
        self.nested_entries = []   # (scope, file, object pointer, index, node, uses, topic)
        self.rules = []
        self.broken = None


class RuleEntry(object):
    """One rule entry - of a mother's items.allOf (scope None), or of a
    nested object's allOf (scope: that object's path) - parsed against the
    grammar."""

    def __init__(self, model, index, node, scope=None, rel=None, container=None, topic=None):
        self.table = model.name
        self.scope = scope
        self.file = model.mother if rel is None else rel
        self.index = index
        self.container = "/items" if container is None else container
        self.pointer = "{}/allOf/{}".format(self.container, index)
        self.node = node
        self.topic = topic
        self.id = self.kind = self.domain = self.comment = self.reading = None
        self.provenance = None
        self.when = self.then = self.mode = None
        self.gates = []
        self.targets = []
        self.reach = []            # (group path, pointer, "test"|"effect")
        self.top_vars = set()      # variables named at the record level
        self.grammar_ok = True

    @property
    def key(self):
        return (self.file, self.pointer)

    def label(self):
        if self.id is None:
            return "the rule at {}".format(self.pointer)
        if self.kind == "routing":
            return "{} ({} routing)".format(self.id, self.domain)
        return "{} ({})".format(self.id, KIND_WORDS.get(self.kind, "rule"))

    def half(self):
        if self.id is None and self.scope is not None:
            return "{} allOf/{}:{}".format(self.scope, self.index, self.kind or "rule")
        return "{}:{}".format(self.id or "allOf/{}".format(self.index), self.kind or "rule")

    def where_label(self):
        return "the record" if self.scope is None else self.scope

    def public(self):
        return {"table": self.table, "id": self.id, "kind": self.kind, "domain": self.domain,
                "scope": self.scope, "index": self.index, "file": self.file,
                "pointer": self.pointer, "comment": self.comment, "reading": self.reading,
                "provenance": self.provenance, "when": self.when, "then": self.then}


def rule_field(model, rule, path):
    """The Field a rule's variable names: record-level names among the
    table's columns, every other path among the nested fields."""
    if path in rule.top_vars:
        return model.props.get(path)
    field = model.fields.get(path)
    return field if field is not None and field.depth > 0 else None


# ---------------------------------------------------------------- analysis


TEST_HINT = ('A test is {"const": v}, {"enum": [v1, v2, ...]}, {"not": {"const": v}}, '
             '{"not": {"enum": [...]}}, {"contains": {"const": v}} or {"not": {"contains": '
             '{"const": v}}} on a list, {"type": "integer"|"number", "minimum", "maximum", '
             '"exclusiveMinimum", "exclusiveMaximum", "not": {"enum": [sentinels]}} with at '
             'least one bound, or - on a group - a clause on its fields; a gate in required with '
             'no test tests that a field the data may leave out is present (SKIP-LOGIC.md, The '
             'canonical form).')
EFFECT_HINT = ('An effect is {"const": c}, {"not": {"const": c}}, {"enum": [...]}, '
               '{"anyOf": [{"type", bounds}, sentinel consts or $refs to them]}, {"maxItems": n} '
               'and/or {"minItems": n} on a list, false (a field the data may leave out is left out), '
               'or - on a group - {"properties": {field: effect}} and/or {"required": [fields]} '
               '- no other keyword, no nested if, and a $ref only to a sentinel definition '
               '(SKIP-LOGIC.md, The canonical form).')
CLAUSE_HINT = ('Write the if as {"required": [gates], "properties": {gate: test}} - several '
               'gates in one clause all must hold; a gate in required with no test is present, '
               'for a field the data may leave out - or {"anyOf": [clause, clause, ...]} for '
               '"any of these" (SKIP-LOGIC.md, The canonical form).')
THEN_HINT = ('Write the then as {"properties": {target: effect, ...}}, {"required": [targets '
             'that must be present]} or both, or {"anyOf": [{"required": [t], "properties": '
             '{t: effect}} or {"required": [t]}, ...]} for "at least one of these"; the reverse '
             'direction or a second condition is its own rule.')
REACH_HINT = ("Fields nest at most six levels below a column, so nothing deeper can be named: "
              "test or constrain the group's own fields (SKIP-LOGIC.md, The canonical form).")
PROVENANCE_HINT = ('x-provenance maps facets (default, title, description, type, values, '
                   'value:<code>, sentinels, minimum, maximum, pattern, unit, universe, '
                   'derivation; on nested values required, minItems, maxItems, uniqueItems, '
                   'propertyNames, contains; minLength, maxLength) to a reference - S01, '
                   'S01:<locator> or D014 - or a list of them (LEDGER-FORMAT.md, References).')


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
        self.field_sites = {}      # file -> {pointer: Field}
        self.containers = {}       # id(node) -> nested object, lookup or list node, and its uses
        self.list_nodes = set()    # ids of list and entries array nodes
        self._seen = set()
        self._meta = None
        self._validators = {}
        self._shapes = {}          # (id(node), file, depth) -> ShapeInfo, however many paths

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
        field = self.field_at(rel, pointer)
        if field is not None:
            where["variable"], where["topic"] = field.path, field.topic
            where.setdefault("table", field.table)
        where.update(extra)
        return where

    def field_at(self, rel, pointer):
        """The deepest Field whose node holds pointer in file rel, or None."""
        sites = self.field_sites.get(rel)
        if not sites or not pointer:
            return None
        tokens = pointer.split("/")
        for k in range(len(tokens), 1, -1):
            field = sites.get("/".join(tokens[:k]))
            if field is not None:
                return field
        return None

    def locate(self, item):
        """Add table, topic and variable to a finding made before the tables
        were known (parse, meta-schema, $id and $ref findings), and the topic
        of the variable a mother's finding names (rule findings)."""
        rel, extra = item.get("file"), {}
        if rel and "table" not in item and not rel.startswith("../"):
            where = self.where(rel, item.get("pointer"))
            extra = {key: where[key] for key in ("table", "topic", "variable")
                     if where.get(key) is not None}
        elif rel and item.get("pointer") and "rule" not in item:
            # Attributed before the fields were known: a column, never a nested field.
            field = self.field_at(rel, item["pointer"])
            if field is not None and field.depth > 0 and item.get("variable") in (None, field.top):
                extra = {"variable": field.path, "topic": field.topic}
        model = self.tables.get(item.get("table") or extra.get("table"))
        variable = extra.get("variable") or item.get("variable")
        prop = model.fields.get(variable) if model and isinstance(variable, str) else None
        if prop is not None and "topic" not in item and "topic" not in extra:
            extra["topic"] = prop.topic
        if not extra:
            return item
        rest = {key: value for key, value in item.items()
                if key not in ("severity", "code", "message", "hint")}
        rest.update(extra)
        return finding(item["severity"], item["code"], item["message"], item["hint"], **rest)

    def node_admits(self, node, value):
        """Does the schema node (anywhere in the package) accept value; None
        when that cannot be told."""
        key = id(node)
        if key not in self._validators:
            site = self.pkg.node_at.get(key) if isinstance(node, dict) else None
            self._validators[key] = None if site is None else Draft202012Validator(
                {"$ref": "{}#{}".format(self.pkg.uri[site[0]], quote(site[1], safe="/~"))},
                registry=self.pkg.registry)
        validator = self._validators[key]
        if validator is None:
            return None
        try:
            return bool(validator.is_valid(value))
        except Exception:
            return None

    def run(self):
        self.lint_meta()
        self.lint_ids()
        self.walk_refs()
        self.build_tables()
        self.read_nested_rules()
        self.mark_unreached_rules()
        for rel, (table, topic) in sorted(self.category_table.items()):
            self.lint_category(rel, table, topic)
        self.lint_fields()
        self.lint_defs()
        for model in self.tables.values():
            for index, node in model.rule_entries:
                self.parse_rule(model, index, node)
            for scope, rel, container, index, node, uses, topic in model.nested_entries:
                rule = self.parse_rule(model, index, node, scope, rel, container, topic)
                if len(uses) > 1:
                    self.add("error", "rule-in-shared-shape",
                             "{} is in a shape used at {}, so its scope is not one place.".format(
                                 cap_first(rule.label()), joined_plain(
                                     ["{} ({})".format(s, m.name) if m is not model else s
                                      for m, s, _ in uses])),
                             "Write the shape inline in each use, or keep the rule out: a rule "
                             "among one object's fields lives in exactly one object "
                             "(SKIP-LOGIC.md, Rules inside nested values).",
                             file=rel, pointer=rule.pointer, table=model.name, topic=topic,
                             rule=rule.id)
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

    def read_nested_rules(self):
        """The rules among one group's or entry's own fields: every entry of
        a nested object's allOf (SKIP-LOGIC.md, Rules inside nested values)."""
        for box in self.containers.values():
            if box["kind"] != "object" or not isinstance(box["node"].get("allOf"), list):
                continue
            model, scope, field = box["uses"][0]
            for k, entry in enumerate(box["node"]["allOf"]):
                if is_rule_entry(entry):
                    self.rule_nodes.add(id(entry))
                    model.nested_entries.append((scope, box["rel"], box["pointer"], k, entry,
                                                 box["uses"], field.topic))
                    continue
                self.add("error", "allof-entry",
                         "{}: allOf[{}] is not a rule.".format(scope, k),
                         "A nested value's allOf holds only the rules among its own fields, each "
                         "with $comment, x-provenance, if and then (SKIP-LOGIC.md, Rules inside "
                         "nested values); fold anything else into the object itself.",
                         **self.where(box["rel"], "{}/allOf/{}".format(box["pointer"], k)))

    def mark_unreached_rules(self):
        """A rule in the allOf of a nested object the field walk never reached
        (a category the mother does not reference yet, a shape too deep) sits
        where rules belong: not a conditional outside the mother, and checked
        once the walk reaches it."""
        for doc in self.pkg.docs.values():
            for node, here in iter_schema(doc, "", self.rule_nodes):
                entries = node.get("allOf")
                if here and isinstance(node.get("properties"), dict) and isinstance(entries, list):
                    self.rule_nodes.update(id(entry) for entry in entries if is_rule_entry(entry))

    def collect_properties(self, model):
        for rel in model.categories:
            doc = self.pkg.docs.get(rel)
            props = doc.get("properties") if isinstance(doc, dict) else None
            if not isinstance(props, dict):
                continue
            topic = PurePosixPath(rel).stem
            required = doc.get("required") if isinstance(doc.get("required"), list) else []
            for name, schema in props.items():
                if name in model.props:
                    continue
                prop = Field(self, model.name, name, rel, "/properties/" + esc(name), topic,
                             schema)
                prop.omittable = name not in required
                prop.optional = prop.omittable and cites_decision(
                    schema.get("x-provenance") if isinstance(schema, dict) else None, "required")
                model.props[name] = prop
                model.fields.setdefault(name, prop)
                self.field_sites.setdefault(rel, {}).setdefault(prop.pointer, prop)
                if isinstance(schema, dict):
                    self.prop_by_id[id(schema)] = prop
                self.expand(model, prop, frozenset())

    # -- nested values

    def deref(self, node, rel):
        """(node, file) of the schema a $ref names, when node is a $ref with
        only annotations beside it; followed up to REF_HOPS times."""
        for _ in range(REF_HOPS):
            if not (isinstance(node, dict) and isinstance(node.get("$ref"), str)) or any(
                    key in node for key in SHAPE_KEYS):
                break
            resolved, _ = self.pkg.lookup(self.pkg.uri[rel], node["$ref"])
            target = resolved.contents if resolved is not None else None
            site = self.pkg.node_at.get(id(target)) if isinstance(target, dict) else None
            if site is None:
                break
            node, rel = target, site[0]
        return node, rel

    def typed_branches(self, node, rel):
        """The branches that decide a value's shape: an anyOf's (or oneOf's)
        branches other than special codes (a const, or a $ref to one), each
        followed through $ref; otherwise the node itself."""
        for key in ("anyOf", "oneOf"):
            if isinstance(node.get(key), list):
                out = []
                for branch in node[key]:
                    target, where = self.deref(branch, rel)
                    if isinstance(target, dict) and "const" not in target:
                        out.append((target, where))
                return out
        return [(node, rel)]

    def shape_of(self, node, rel, depth=0):
        """ShapeInfo of a schema node: typed branches of two or more JSON
        types make it mixed; otherwise its first typed branch decides."""
        node, rel = self.deref(node, rel)
        info = ShapeInfo(node, rel)
        if not isinstance(node, dict) or depth > MAX_DEPTH + 2:
            return info
        if (id(node), rel, depth) in self._shapes:
            return self._shapes[(id(node), rel, depth)]
        self._shapes[(id(node), rel, depth)] = info
        branches = self.typed_branches(node, rel)
        info.branches = [self.shape_alone(ShapeInfo(b, r), b, r, depth) for b, r in branches]
        kinds = set().union(*(json_kinds(b) for b, _ in branches)) if branches else set()
        if len(kinds) >= 2:
            info.shape = "mixed"
        elif info.branches:
            first = info.branches[0]
            info.shape = first.shape
            info.obj, info.obj_rel = first.obj, first.obj_rel
            info.arr, info.arr_rel = first.arr, first.arr_rel
            info.items, info.items_info = first.items, first.items_info
            info.lookup, info.lookup_rel, info.values = first.lookup, first.lookup_rel, first.values
        return info

    def shape_alone(self, info, node, rel, depth):
        kinds = json_kinds(node)
        if "object" in kinds:
            if isinstance(node.get("properties"), dict):
                info.shape, info.obj, info.obj_rel = "group", node, rel
            elif isinstance(node.get("additionalProperties"), dict):
                info.shape, info.lookup, info.lookup_rel = "lookup", node, rel
                info.values = node["additionalProperties"]
        elif "array" in kinds:
            info.shape, info.arr, info.arr_rel = "list", node, rel
            if isinstance(node.get("items"), dict):
                info.items = node["items"]
                info.items_info = self.shape_of(info.items, rel, depth + 1)
                if info.items_info.shape == "group":
                    info.shape = "entries"
        return info

    @staticmethod
    def object_nodes(info):
        """(kind, node) for each node holding a value's fields: a group's or a
        lookup's object, or each entry's object for a list of entries."""
        out = []
        for branch in info.branches or [info]:
            if branch.shape == "group":
                out.append(("group", branch.obj))
            elif branch.shape == "lookup":
                out.append(("lookup", branch.lookup))
            elif branch.shape == "entries":
                inner = branch.items_info
                out.extend(("entries", sub.obj) for sub in inner.branches or [inner]
                           if sub.shape == "group")
        return out

    def children_of(self, info, path):
        """[(path, name, node, file, pointer, scope, object node)] one level
        inside a value."""
        out = []
        for kind, node in self.object_nodes(info):
            site = self.pkg.node_at.get(id(node))
            if site is None:
                continue
            rel, here = site
            if kind == "lookup":
                out.append((path + ".*", "*", node["additionalProperties"], rel,
                            here + "/additionalProperties", None, None))
                continue
            scope = path + "[]" if kind == "entries" else path
            for name, child in node["properties"].items():
                out.append((join_path(scope, name), name, child, rel,
                            "{}/properties/{}".format(here, esc(name)), scope, node))
        return out

    def expand(self, model, field, stack):
        """Record the Fields inside field (depth first, schema order). A field
        too deep, or whose shape is one it sits in, is kept but not entered."""
        info = self.shape_of(field.schema, field.file)
        field.info, field.shape = info, info.shape
        self.note_containers(model, field, info)
        kids = self.children_of(info, field.path) if info.shape != "value" else []
        if not kids:
            return
        hint = ("Flatten it: house style nests at most six levels below a column, and a shape "
                "never holds itself (SCHEMA-STYLE.md, Nested values).")
        if id(info.node) in stack:
            self.add("warning", "nesting-too-deep",
                     "{} holds the shape it sits in, so it nests without end; the fields inside "
                     "it are not checked.".format(field.path), hint,
                     dedupe=("nesting-too-deep", model.name, field.path),
                     **self.where(field.file, field.pointer, variable=field.path,
                                  topic=field.topic))
            return
        if field.depth >= MAX_DEPTH:
            self.add("warning", "nesting-too-deep",
                     "{} nests deeper than six levels below its column; the fields inside it are "
                     "not checked.".format(field.path), hint,
                     dedupe=("nesting-too-deep", model.name, field.path),
                     **self.where(field.file, field.pointer, variable=field.path,
                                  topic=field.topic))
            return
        if len(model.fields) - len(model.props) >= FIELD_LIMIT:
            self.add("warning", "nesting-too-deep",
                     "{} reached {} fields inside nested values, so the fields inside {} and past "
                     "it are not checked.".format(model.name, FIELD_LIMIT, field.path),
                     "A shape used at many paths has fields at each of them, and shapes shared "
                     "inside shared shapes multiply: flatten them (SCHEMA-STYLE.md, Nested values).",
                     dedupe=("nesting-too-deep", model.name),
                     **self.where(field.file, field.pointer, variable=field.path,
                                  topic=field.topic))
            return
        stack = stack | {id(info.node)}
        for path, name, node, rel, pointer, scope, obj in kids:
            if path in model.fields:
                continue
            child = Field(self, model.name, path, rel, pointer, field.topic, node, name=name,
                          parent=field.path, depth=field.depth + 1, top=field.top)
            child.scope = scope
            if obj is not None:
                required = obj.get("required") if isinstance(obj.get("required"), list) else []
                child.omittable = name not in required
                child.optional = child.omittable and cites_decision(
                    node.get("x-provenance") if isinstance(node, dict) else None, "required")
            model.fields[path] = child
            self.field_sites.setdefault(rel, {}).setdefault(pointer, child)
            if isinstance(node, dict):
                self.prop_by_id.setdefault(id(node), child)
            self.expand(model, child, stack)

    def note_containers(self, model, field, info):
        """Remember each nested object, lookup and list node, and where it is
        used, for house style and for the rules among one object's fields."""
        def note(node, kind, scope):
            site = self.pkg.node_at.get(id(node))
            if site is None:
                return
            box = self.containers.setdefault(id(node), {
                "node": node, "rel": site[0], "pointer": site[1], "kind": kind, "uses": []})
            if not any(m is model and s == scope for m, s, _ in box["uses"]):
                box["uses"].append((model, scope, field))

        for branch in info.branches or [info]:
            if branch.shape == "group":
                note(branch.obj, "object", field.path)
            elif branch.shape == "lookup":
                note(branch.lookup, "lookup", field.path)
            elif branch.shape in ("list", "entries"):
                self.list_nodes.add(id(branch.arr))
                note(branch.arr, "list", field.path)
                if branch.shape == "entries":
                    inner = branch.items_info
                    for sub in inner.branches or [inner]:
                        if sub.shape == "group":
                            note(sub.obj, "object", field.path + "[]")

    def container_text(self, info, depth=0):
        """What a nested value takes, in words."""
        def names(obj):
            keys = list(obj.get("properties") or {})
            text = ", ".join(keys[:10])
            return text + (", … ({} fields in all)".format(len(keys)) if len(keys) > 10 else "")

        def counts(arr):
            parts = []
            for key, word in (("minItems", "at least"), ("maxItems", "at most")):
                if is_integral(arr.get(key)):
                    parts.append("{} {}".format(word, int(arr[key])))
            if arr.get("uniqueItems") is True:
                parts.append("each at most once")
            if isinstance(arr.get("contains"), dict):
                one, many = match_words(arr["contains"])
                need, low = contains_need(arr)
                parts.append("{} {}".format(need, one if low == 1 and need.startswith(
                    ("exactly", "at least")) else many))
            return " ({})".format(", ".join(parts)) if parts else ""

        def value_text(node, rel):
            inner = self.shape_of(node, rel, depth + 1)
            if inner.shape != "value" and depth < MAX_DEPTH:
                return self.container_text(inner, depth + 1)
            return describe_allowed(value_profile(self.pkg, node, self.pkg.resolver(
                self.pkg.uri[rel]))) or "a value"

        if info.shape == "group":
            return "a group of fields: " + names(info.obj)
        if info.shape == "entries":
            return "a list of entries, each with " + names(info.items_info.obj) + counts(info.arr)
        if info.shape == "list":
            item = (value_text(info.items, info.arr_rel) if isinstance(info.items, dict)
                    else "a value")
            return "a list of values, each " + item + counts(info.arr)
        if info.shape == "lookup":
            names_node, _ = self.deref(info.lookup.get("propertyNames"), info.lookup_rel)
            pattern = names_node.get("pattern") if isinstance(names_node, dict) else None
            lead = "names matching {}".format(pattern) if nonempty_str(pattern) else "any names"
            return "{}, each {}".format(lead, value_text(info.values, info.lookup_rel))
        if info.shape == "mixed" and info.branches and depth < MAX_DEPTH:
            return " or ".join(self.container_text(branch, depth + 1) if branch.shape != "value"
                               else describe_typed(branch.node) for branch in info.branches)
        return describe_allowed(value_profile(self.pkg, info.node, self.pkg.resolver(
            self.pkg.uri[info.rel]))) or "a value"

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
            missing = [name for name in props if name not in required and not cites_decision(
                props[name].get("x-provenance") if isinstance(props[name], dict) else None,
                "required")]
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

    def lint_fields(self):
        """House style inside nested values: every field has a title and
        x-provenance and its codes are linted; every group and entry is
        closed and complete; lists and lookups are well formed. Each node is
        linted once, however many paths use it."""
        done = set()
        for model in self.tables.values():
            for field in model.fields.values():
                node = field.schema
                if field.depth > 0 and id(node) not in done:
                    done.add(id(node))
                    where = self.where(field.file, field.pointer)
                    if not isinstance(node, dict) or not nonempty_str(node.get("title")):
                        self.add("error", "missing-title", "{} has no title.".format(field.path),
                                 "Give every field inside a nested value a title: the label the "
                                 "data dictionary shows.", **where)
                    if not isinstance(node, dict) or "x-provenance" not in node:
                        self.add("error", "missing-provenance",
                                 "{} has no x-provenance.".format(field.path),
                                 'Add "x-provenance": {"default": "S01:<where the source defines '
                                 'it>"}: every fact traces to a source or a decision.', **where)
                    if isinstance(node, dict):
                        self.lint_value_schema(field.file, field.pointer, node, field.path)
                info = field.info
                if field.shape == "list" and isinstance(info.items, dict) and id(info.items) not in done:
                    done.add(id(info.items))
                    site = self.pkg.node_at.get(id(info.items))
                    if site is not None:
                        self.lint_value_schema(site[0], site[1], info.items, field.path)
        for box in self.containers.values():
            if box["kind"] == "object":
                self.lint_object(box)
            elif box["kind"] == "lookup":
                self.lint_lookup(box)
            else:
                self.lint_list(box)

    def box_where(self, box, sub=""):
        """Where a container's finding is: its node, attributed to the
        variable that holds it (even when the node sits in $defs)."""
        field = box["uses"][0][2]
        return self.where(box["rel"], box["pointer"] + sub, variable=field.path, topic=field.topic,
                          table=field.table)

    def lint_object(self, box):
        node = box["node"]
        scope = box["uses"][0][1]
        where = lambda sub="": self.box_where(box, sub)
        if node.get("type") != "object":
            self.add("error", "nested-shape",
                     '{} has properties but is not "type": "object".'.format(scope),
                     'Add "type": "object" - without it a value that is not an object passes '
                     'unchecked - with required and "additionalProperties": false '
                     '(SCHEMA-STYLE.md, Nested values).', **where("/type"))
        props = node["properties"]
        required = node.get("required") if isinstance(node.get("required"), list) else []
        missing = [name for name in props if name not in required and not cites_decision(
            props[name].get("x-provenance") if isinstance(props[name], dict) else None,
            "required")]
        if missing:
            self.add("error", "required-incomplete",
                     "{}: required omits {}.".format(scope, ", ".join(missing)),
                     "List every field in required, in properties order - missingness is a code "
                     "in the cell, never an absent field - unless a person decided the data may "
                     'leave it out: then cite that decision on the field\'s own x-provenance, '
                     '"required": "D0NN".', **where("/required"))
        if node.get("additionalProperties") is not False:
            self.add("error", "nested-open",
                     '{} does not close its fields: "additionalProperties": false is '
                     'missing.'.format(scope),
                     "Add it beside properties: the mother's unevaluatedProperties closes the "
                     "record, not the values inside it, so an undeclared field inside passes "
                     "unnoticed.", **where())

    def lint_lookup(self, box):
        node, rel = box["node"], box["rel"]
        scope = box["uses"][0][1]
        if node.get("type") != "object":
            self.add("error", "nested-shape",
                     '{} is a lookup (an additionalProperties schema) but is not "type": '
                     '"object".'.format(scope),
                     'Add "type": "object": without it a value that is not an object passes '
                     'unchecked (SCHEMA-STYLE.md, Nested values).', **self.box_where(box, "/type"))
        names, _ = self.deref(node.get("propertyNames"), rel)
        if not (isinstance(names, dict) and nonempty_str(names.get("pattern"))):
            self.add("warning", "lookup-names",
                     "{} is a lookup with no propertyNames pattern.".format(scope),
                     'Add "propertyNames": {"pattern": "^...$"} stating the names it takes; a '
                     "lookup whose names are a fixed, known set is a group whose fields may be "
                     "left out (SCHEMA-STYLE.md, Nested values).", **self.box_where(box))

    def lint_list(self, box):
        node, rel = box["node"], box["rel"]
        scope = box["uses"][0][1]
        shape_hint = ('A list is "type": "array" with what each entry holds in items '
                      '(SCHEMA-STYLE.md, Nested values).')
        if node.get("type") != "array":
            self.add("error", "nested-shape", '{} is a list but is not "type": "array".'.format(scope),
                     shape_hint, **self.box_where(box, "/type"))
        items = node.get("items")
        if not isinstance(items, dict):
            self.add("error", "nested-shape",
                     "{} is a list with no items schema saying what each entry holds.".format(scope),
                     shape_hint, **self.box_where(box))
            return
        if self.shape_of(items, rel).shape in ("list", "entries"):
            self.add("warning", "list-of-lists", "{} is a list of lists.".format(scope),
                     "Lists of lists are not house style: they usually mean the source's own "
                     "table - ask how the data is delivered (SCHEMA-STYLE.md, Nested values).",
                     **self.box_where(box, "/items"))
        annotated = [key for key in ("title", "description", "x-provenance") if key in items]
        if annotated:
            self.add("warning", "items-annotation",
                     "{}'s items carries {}.".format(scope, " and ".join(annotated)),
                     "Say it on the list: the data dictionary appends an items title to the "
                     "list's description, and the list's x-provenance covers its entries.",
                     **self.box_where(box, "/items"))

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

    def parse_rule(self, model, index, node, scope=None, rel=None, container=None, topic=None):
        rule = RuleEntry(model, index, node, scope, rel, container, topic)
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
            self.add("error", code, message, hint, file=rule.file, pointer=rule.pointer + sub,
                     table=model.name, topic=rule.topic, variable=variable, rule=rule.id)

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
            rule.when = self.parse_if(rule, model, node["if"], bad)
        if "then" in node:
            rule.then = self.parse_then(rule, model, node["then"], bad)
        provenance = node.get("x-provenance")
        rule.provenance = provenance if isinstance(provenance, dict) else None
        self.check_rule_meaning(rule, model)
        return rule

    def parse_if(self, rule, model, node, bad):
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
            parsed = [self.parse_clause(rule, model, clause, "/if/anyOf/{}".format(k), bad,
                                        rule.scope) for k, clause in enumerate(clauses)]
            return None if any(c is None for c in parsed) else {"any": parsed}
        clause = self.parse_clause(rule, model, node, "/if", bad, rule.scope)
        return None if clause is None else {"any": [clause]}

    def parse_clause(self, rule, model, node, sub, bad, prefix, depth=0):
        """One clause's tests, each on a full path; a test on a group may be a
        clause on the group's own fields. A name in required with no test of
        its own tests that the field is present: only a field the data may
        leave out (its object's required omits it) takes that test."""
        name = cap_first(rule.label())
        if not isinstance(node, dict):
            bad("rule-shape", "{}'s clause at {} is not an object.".format(name, sub), CLAUSE_HINT, sub)
            return None
        if depth > MAX_DEPTH:
            bad("rule-shape", "{}'s clause at {} reaches more than six levels into groups.".format(
                name, sub), REACH_HINT, sub)
            return None
        keys = set(node)
        if keys == {"required"} and isinstance(node["required"], list) and node["required"] and all(
                isinstance(gate, str) for gate in node["required"]):
            always = [join_path(prefix, gate) for gate in node["required"]
                      if self.presence_field(model, prefix, gate) is None]
            if always:
                bad("rule-shape", "{}'s clause at {} only requires {}; a name in required with no "
                    "test tests that the field is present, and {} not a field its object's "
                    "required leaves out.".format(name, sub, ", ".join(always), "that is"
                                                  if len(always) == 1 else "those are"),
                    CLAUSE_HINT, sub)
                return None
        elif keys != {"required", "properties"}:
            nested = sorted(keys & {"if", "then", "else", "allOf", "anyOf", "oneOf", "not"})
            message = "{}'s clause at {} has {}; a clause is exactly {{\"required\", \"properties\"}}."\
                .format(name, sub, ", ".join(sorted(keys)) or "nothing")
            if nested:
                message += " No {} inside if.".format(", ".join(nested))
            bad("rule-shape", message, CLAUSE_HINT, sub)
            return None
        required, props = node["required"], node.get("properties", {})
        if not isinstance(required, list) or not required or not all(
                isinstance(item, str) for item in required):
            bad("rule-shape", "{}'s clause at {}: required must list the gate names.".format(
                name, sub), CLAUSE_HINT, sub + "/required")
            return None
        if not isinstance(props, dict) or (not props and "properties" in node):
            bad("rule-shape", "{}'s clause at {}: properties must map each gate to its test."
                .format(name, sub), CLAUSE_HINT, sub + "/properties")
            return None
        ok = True
        present = [n for n in dict.fromkeys(required)
                   if n not in props and self.presence_field(model, prefix, n) is not None]
        if set(required) != set(props) | set(present):
            untested = [n for n in required if n not in props and n not in present]
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
                "satisfies the if vacuously and the rule fires on it. A name in required with "
                "no test tests that the field is present, which only a field its object's "
                "required leaves out can be (SKIP-LOGIC.md, Fields left out).", sub)
            ok = False
        tests = []
        for gate, test in props.items():
            pointer = "{}/properties/{}".format(sub, esc(gate))
            var = join_path(prefix, gate)
            if prefix is None:
                rule.top_vars.add(var)
            if is_clause(test):
                rule.reach.append((var, pointer, "test"))
                inner = self.parse_clause(rule, model, test, pointer, bad, var, depth + 1)
                if inner is None:
                    ok = False
                else:
                    tests.extend(inner["all"])
                continue
            parsed = self.parse_test(rule, var, test, pointer, bad)
            if parsed is None:
                ok = False
                continue
            item = {"variable": var}
            item.update(parsed)
            tests.append(item)
            rule.gates.append((var, parsed, pointer))
        for gate in present:
            var = join_path(prefix, gate)
            if prefix is None:
                rule.top_vars.add(var)
            tests.append({"variable": var, "test": "present"})
            rule.gates.append((var, {"test": "present"}, "{}/required/{}".format(
                sub, required.index(gate))))
        return {"all": tests} if ok else None

    @staticmethod
    def presence_field(model, prefix, name):
        """The Field name (under prefix) names when the data may leave it out
        of its object - the only kind of field a presence test or effect is
        about - else None."""
        if not isinstance(name, str):
            return None
        field = (model.props.get(name) if prefix is None
                 else model.fields.get(join_path(prefix, name)))
        return field if field is not None and field.omittable else None

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
            if keys == {"contains"} and is_const_only(test["contains"]):
                return {"test": "includes", "value": test["contains"]["const"]}
            if keys == {"not"}:
                inner = test["not"]
                if isinstance(inner, dict) and set(inner) == {"const"}:
                    return {"test": "ne", "value": inner["const"]}
                if (isinstance(inner, dict) and set(inner) == {"enum"}
                        and isinstance(inner["enum"], list) and inner["enum"]):
                    return {"test": "nin", "values": list(inner["enum"])}
                if (isinstance(inner, dict) and set(inner) == {"contains"}
                        and is_const_only(inner["contains"])):
                    return {"test": "excludes", "value": inner["contains"]["const"]}
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
        if keys and keys <= {"required", "properties"}:
            rule.mode = "all"
            effects, ok = self.parse_object_effects(rule, model, node, "/then", bad, rule.scope)
            return {"mode": "all", "effects": effects} if ok else None
        if keys == {"anyOf"} and isinstance(node["anyOf"], list) and len(node["anyOf"]) >= 2:
            rule.mode = "any"
            effects, ok = [], True
            for k, alt in enumerate(node["anyOf"]):
                sub = "/then/anyOf/{}".format(k)
                if (isinstance(alt, dict) and set(alt) == {"required"}
                        and isinstance(alt["required"], list) and len(alt["required"]) == 1
                        and isinstance(alt["required"][0], str)):
                    found, alt_ok = self.parse_object_effects(rule, model, alt, sub, bad, rule.scope)
                    effects.extend(found)
                    ok = ok and alt_ok
                    continue
                if not (isinstance(alt, dict) and set(alt) == {"required", "properties"}
                        and isinstance(alt["required"], list) and len(alt["required"]) == 1
                        and isinstance(alt["required"][0], str)
                        and isinstance(alt["properties"], dict) and len(alt["properties"]) == 1):
                    bad("rule-shape", "{}'s then.anyOf[{}] is not {{\"required\": [t], "
                        "\"properties\": {{t: effect}}}} or {{\"required\": [t]}} for one target t."
                        .format(name, k), THEN_HINT, sub)
                    ok = False
                    continue
                target = next(iter(alt["properties"]))
                if alt["required"][0] != target:
                    bad("rule-unguarded", "{}'s then.anyOf[{}] requires {} but constrains {}."
                        .format(name, k, alt["required"][0], target),
                        "Require the same target the alternative constrains, or a row lacking it "
                        "satisfies the alternative vacuously.", sub, join_path(rule.scope, target))
                    ok = False
                    continue
                found, alt_ok = self.parse_effects(rule, model, alt["properties"],
                                                   sub + "/properties", bad, rule.scope)
                if not alt_ok:
                    ok = False
                    continue
                if len(found) != 1:
                    bad("rule-shape", "{}'s then.anyOf[{}] constrains {} fields; each alternative "
                        "constrains one.".format(name, k, len(found)), THEN_HINT, sub)
                    ok = False
                    continue
                if found[0]["effect"] == "absent":
                    bad("rule-shape", "{}'s then.anyOf[{}] requires {} and leaves it out, so it "
                        "never holds.".format(name, k, found[0]["variable"]), THEN_HINT, sub,
                        found[0]["variable"])
                    ok = False
                    continue
                effects.extend(found)
            return {"mode": "any", "effects": effects} if ok else None
        nested = sorted(keys & {"if", "then", "else", "allOf", "oneOf", "not", "$ref"})
        if keys == {"anyOf"}:
            message = "{}'s then.anyOf needs two or more alternatives.".format(name)
        else:
            message = "{}'s then has {}; a then is {{\"properties\": {{...}}}}, {{\"required\": " \
                      "[...]}} or both, or {{\"anyOf\": [two or more alternatives]}}.".format(
                          name, ", ".join(sorted(keys)) or "nothing")
        if nested:
            message += " No {} inside then.".format(", ".join(nested))
        bad("rule-shape", message, THEN_HINT, "/then")
        return None

    def parse_object_effects(self, rule, model, node, base, bad, prefix, depth=0):
        """(effects, ok) for a then, an "at least one" alternative, or an effect
        reaching into a group: {"properties": {target: effect, ...}} and/or
        {"required": [targets]} - each name in required must be present."""
        name = cap_first(rule.label())
        place = ("then" if base == "/then" else "then.anyOf[{}]".format(base.rsplit("/", 1)[1])
                 if base.startswith("/then/anyOf/") else "effect at " + base)
        effects, ok = [], True
        props = node.get("properties")
        if "properties" in node:
            if not isinstance(props, dict) or not props:
                bad("rule-shape", "{}'s {}.properties names no target.".format(name, place),
                    THEN_HINT, base + "/properties")
                ok = False
            else:
                found, props_ok = self.parse_effects(rule, model, props, base + "/properties",
                                                     bad, prefix, depth)
                effects.extend(found)
                ok = ok and props_ok
        if "required" in node:
            required = node["required"]
            if (not isinstance(required, list) or not required
                    or not all(isinstance(target, str) for target in required)
                    or len(set(required)) != len(required)):
                bad("rule-shape", "{}'s {}.required must list each target that must be present, "
                    "once.".format(name, place), THEN_HINT, base + "/required")
                return effects, False
            for k, target in enumerate(required):
                pointer = "{}/required/{}".format(base, k)
                var = join_path(prefix, target)
                if isinstance(props, dict) and props.get(target) is False:
                    bad("rule-shape", "{} both requires {} and leaves it out, so it never holds."
                        .format(name, var), THEN_HINT, pointer, var)
                    ok = False
                    continue
                if prefix is None:
                    rule.top_vars.add(var)
                effects.append({"variable": var, "effect": "present"})
                rule.targets.append((var, {"effect": "present"}, pointer))
        return effects, ok

    def parse_effects(self, rule, model, props, base, bad, prefix, depth=0):
        """(effects on full paths, ok) for a then's properties; an effect on a
        group may be {"properties": {field: effect}}, {"required": [field]} or
        both, on the group's fields."""
        effects, ok = [], True
        if depth > MAX_DEPTH:
            bad("rule-shape", "{}'s effect at {} reaches more than six levels into groups.".format(
                cap_first(rule.label()), base), REACH_HINT, base)
            return effects, False
        for target, effect in props.items():
            pointer = "{}/{}".format(base, esc(target))
            var = join_path(prefix, target)
            if prefix is None:
                rule.top_vars.add(var)
            if isinstance(effect, dict) and effect and set(effect) <= {"properties", "required"}:
                rule.reach.append((var, pointer, "effect"))
                inner, inner_ok = self.parse_object_effects(rule, model, effect, pointer, bad, var,
                                                            depth + 1)
                effects.extend(inner)
                ok = ok and inner_ok
                continue
            parsed = self.parse_effect(rule, model, var, effect, pointer, bad)
            if parsed is None:
                ok = False
                continue
            item = {"variable": var}
            item.update(parsed)
            effects.append(item)
            rule.targets.append((var, parsed, pointer))
        return effects, ok

    def parse_effect(self, rule, model, target, effect, pointer, bad):
        name = cap_first(rule.label())
        if effect is False:
            return {"effect": "absent"}
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
            if keys and keys <= {"minItems", "maxItems"} and all(
                    is_integral(effect[key]) and effect[key] >= 0 for key in keys):
                low, high = effect.get("minItems"), effect.get("maxItems")
                if keys == {"maxItems"} and high == 0:
                    return {"effect": "empty"}
                if keys == {"minItems"} and low == 1:
                    return {"effect": "nonempty"}
                if low == 0 or (low is not None and high is not None and low > high):
                    bad("rule-shape", "{}'s effect on {} ({}) {}.".format(
                        name, target, show(effect), "says nothing: every list has at least 0 "
                        "entries" if low == 0 else "never holds"), EFFECT_HINT, pointer, target)
                    return None
                out = {"effect": "count"}
                out.update({key: int(effect[key]) for key in ("minItems", "maxItems") if key in effect})
                return out
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
                resolved, _ = self.pkg.lookup(self.pkg.uri[rule.file], branch["$ref"])
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
        stand_down = bool(model.unresolved_categories)
        name = cap_first(rule.label())
        where = {"file": rule.file, "table": model.name, "rule": rule.id, "topic": rule.topic}
        home = ("no category of {} declares".format(model.name) if rule.scope is None
                else "{} does not hold".format(rule.scope))
        blocked = []

        def under(path):
            return any(path.startswith(stop + ".") or path.startswith(stop + "[")
                       for stop in blocked)

        def where_to_add(path):
            return ("add the property to its category file" if path in rule.top_vars
                    else "add the field to its object's properties")

        for group, sub, what in rule.reach:
            if under(group):
                continue
            field = rule_field(model, rule, group)
            if field is None:
                blocked.append(group)
                if not stand_down:
                    self.add("error", "rule-dangling",
                             "{} {} the fields of {}, which {}.".format(
                                 name, "tests" if what == "test" else "constrains", group, home),
                             "Fix the name, or {} - until then the rule {}.".format(
                                 where_to_add(group), "never fires" if what == "test"
                                 else "constrains nothing"),
                             pointer=rule.pointer + sub, variable=group, **where)
                continue
            if field.shape != "group":
                blocked.append(group)
                rule.grammar_ok = False
                kind = {"list": "a list", "entries": "a list of entries", "lookup": "a lookup",
                        "mixed": "a mixed value"}.get(field.shape, "a single value")
                self.add("error", "rule-shape",
                         "{} reaches into {}, which is {}, not a group.".format(name, group, kind),
                         "A rule reaches only into a group's fields; a rule about each entry of a "
                         "list lives in that list's items.allOf (SKIP-LOGIC.md, Rules inside "
                         "nested values)." if field.shape in ("list", "entries")
                         else (TEST_HINT if what == "test" else EFFECT_HINT),
                         pointer=rule.pointer + sub, variable=group, **where)
        for gate, test, sub in rule.gates:
            if under(gate):
                continue
            pointer = rule.pointer + sub
            prop = rule_field(model, rule, gate)
            if prop is None:
                if not stand_down:
                    self.add("error", "rule-dangling",
                             "{} tests {}, which {}.".format(name, gate, home),
                             "Fix the name, or {} - until then the rule never fires.".format(
                                 where_to_add(gate)), pointer=pointer, variable=gate, **where)
                continue
            if test["test"] in ("includes", "excludes"):
                if prop.shape != "list":
                    rule.grammar_ok = False
                    self.add("error", "rule-shape",
                             "{} tests whether {} includes {}, but {} is not a list of values."
                             .format(name, gate, show(test["value"]), gate), TEST_HINT,
                             pointer=pointer, variable=gate, **where)
                elif prop.admits_item(test["value"]) is False:
                    allowed = prop.item_allowed_text()
                    self.add("warning", "trigger-undeclared-level",
                             "{} triggers on {} including {}, which {} does not declare.".format(
                                 name, gate, show(test["value"]), gate),
                             "Trigger on a code {} declares{}, or declare the code in its "
                             "category file: a trigger on an undeclared value never fires."
                             .format(gate, " ({})".format(clip(allowed, 160)) if allowed else ""),
                             pointer=pointer, variable=gate, **where)
                continue
            values = [test["value"]] if "value" in test else list(test.get("values", []))
            if test["test"] == "range":
                values = []
            for value in dedupe_values(values):
                if prop.admits(value) is False:
                    allowed = prop.allowed_text()
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
            if under(target):
                continue
            pointer = rule.pointer + sub
            prop = rule_field(model, rule, target)
            if prop is None:
                if not stand_down:
                    self.add("error", "rule-dangling",
                             "{} constrains {}, which {}.".format(name, target, home),
                             "Fix the name, or {} - until then the rule can let an undeclared "
                             "column through.".format(where_to_add(target)),
                             pointer=pointer, variable=target, **where)
                continue
            kind = effect["effect"]
            if kind in ("present", "absent") and not prop.omittable:
                rule.grammar_ok = False
                if kind == "present":
                    self.add("error", "rule-shape",
                             "{} requires {} to be present, which it always is: its object's "
                             "required lists it.".format(name, target),
                             "A presence effect is for a field the data may leave out (its "
                             "object's required omits it, citing a person's decision). For a field "
                             'always present, forbid the structural code instead: {"not": '
                             '{"const": c}} (SKIP-LOGIC.md, Fields left out).',
                             pointer=pointer, variable=target, **where)
                else:
                    self.add("error", "rule-shape",
                             "{} leaves {} out, but its object's required lists it, so every "
                             "value the rule applies to fails.".format(name, target),
                             'Pin the structural code instead ({"const": c}); or, when the data '
                             "does leave the field out, drop it from required and cite the "
                             "person's decision on its required facet (SKIP-LOGIC.md, Fields "
                             "left out).", pointer=pointer, variable=target, **where)
                continue
            if kind in ("empty", "nonempty", "count") and prop.shape not in ("list", "entries"):
                rule.grammar_ok = False
                self.add("error", "rule-shape",
                         "{} makes {} {}, but {} is not a list.".format(
                             name, target, "an empty list" if kind == "empty"
                             else "a list with at least one entry" if kind == "nonempty"
                             else "a list of so many entries", target),
                         EFFECT_HINT, pointer=pointer, variable=target, **where)
            pinned = ([effect["value"]] if kind == "eq" else effect["values"] if kind == "in"
                      else effect["also"] if kind == "range" else [])
            undeclared = set()
            for value in dedupe_values(pinned):
                if prop.admits(value) is False:
                    undeclared.add(literal_key(value))
                    allowed = prop.allowed_text()
                    self.add("error", "rule-undeclared-code",
                             "{} pins {} to {}, which {} does not declare.".format(
                                 name, target, show(value), target),
                             "Pin a value {} declares{}; otherwise every row the rule applies to "
                             "fails.".format(target, " ({})".format(clip(allowed, 160))
                                             if allowed else ""),
                             pointer=pointer, variable=target, **where)
            if rule.kind == "skip":
                if kind not in ("eq", "absent"):
                    self.add("error", "skip-shape",
                             "{} is a Skip pattern, but its effect on {} is not a const pin."
                             .format(name, target),
                             "A Skip pattern pins the structural code: {\"const\": c}, with c "
                             "marked \"x-value-kind\": \"sentinel\" - or, for a field the "
                             "data leaves out when it was not asked, false. Any other effect is "
                             "a '<Domain> routing' rule.", pointer=pointer, variable=target, **where)
                elif kind == "eq" and literal_key(effect["value"]) not in undeclared:
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
            elif rule.kind == "applicability" and kind not in ("ne", "present"):
                self.add("error", "applicability-shape",
                         "{} is an Applicability half, but its effect on {} is not "
                         "{{\"not\": {{\"const\": c}}}}.".format(name, target),
                         "The applicability half only forbids the structural code - or, for a "
                         "field the data leaves out only when it was not asked, requires it; a "
                         "then that demands a value outlaws honest missingness (SKIP-LOGIC.md, "
                         "Skip pairs).", pointer=pointer, variable=target, **where)

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
                         "entry per half.", file=rule.file, pointer=rule.pointer,
                         table=model.name, topic=rule.topic, rule=rule.id)
            else:
                first[key] = rule
        halves = {}
        for (rule_id, kind), rule in first.items():
            halves.setdefault(rule_id, {})[kind] = rule
        for rule_id, kinds in sorted(halves.items()):
            for have, lack in (("skip", "applicability"), ("applicability", "skip")):
                if have in kinds and lack not in kinds:
                    self.add("warning", "missing-twin",
                             "{} has {} {} half but no {} half in {}.".format(
                                 rule_id, "an" if have == "applicability" else "a",
                                 KIND_WORDS[have], KIND_WORDS[lack], model.name),
                             "Add the twin with the same id, so the rule holds both ways (it "
                             "rides the same x-provenance); a one-directional pin is '<Domain> "
                             "routing', and a presence effect on a variable whose pair is "
                             "coded joins that pair's applicability half (SKIP-LOGIC.md, Fields "
                             "left out).", file=kinds[have].file, pointer=kinds[have].pointer,
                             table=model.name, topic=kinds[have].topic, rule=rule_id)
            if ("skip" in kinds and "applicability" in kinds
                    and kinds["skip"].scope != kinds["applicability"].scope):
                half = kinds["applicability"]
                self.add("error", "duplicate-rule",
                         "{}'s Skip pattern half is in {} but its Applicability half is in {}."
                         .format(rule_id, kinds["skip"].where_label(), half.where_label()),
                         "A pair's two halves state one routing fact in one place: put both in "
                         "the mother's items.allOf, or both in the same object's allOf - or give "
                         "one of them its own id.", file=half.file, pointer=half.pointer,
                         table=model.name, topic=half.topic, rule=rule_id)

    # -- x-provenance

    def lint_provenance(self):
        for rel, doc in sorted(self.pkg.docs.items()):
            for node, here in iter_schema(doc, "", self.rule_nodes):
                if "x-provenance" not in node:
                    continue
                prop = self.prop_by_id.get(id(node))
                if prop is not None and prop.file == rel:
                    codes = prop.declared_codes
                    owner = prop.path
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
                    self.lint_provenance_site(rule.file, rule.pointer, rule.node["x-provenance"],
                                              lambda rule=rule, model=model: rule_codes(rule, model),
                                              rule.label(), rule)
        if not self.prov.present:
            self.add("info", "provenance-unchecked",
                     "provenance.json is missing, so x-provenance references were checked for "
                     "form only.",
                     "`schemify.py build` writes provenance.json; rerun after it to check that every "
                     "reference names a citable source or decision.", file="../provenance.json")

    def lint_provenance_site(self, rel, pointer, value, codes, owner, rule=None):
        at = pointer + "/x-provenance"
        where = self.where(rel, at)
        if rule is not None:
            where["rule"] = rule.id
            if rule.topic is not None:
                where["topic"] = rule.topic
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
                    if key in DISCOURAGED and not (
                            (key in CONTAINS_KEYS and id(node) in self.list_nodes)
                            or (key in LENGTH_KEYS and self.length_cited(rel, here, node, key))):
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
                                 "{} has an if at {}; conditionals live in the mother's "
                                 "items.allOf, or among one group's or entry's fields in that "
                                 "object's allOf (SKIP-LOGIC.md).".format(rel, here or "/"),
                                 "Move it into the mother as a rule entry with $comment, "
                                 "x-provenance, if and then - or, for a rule among one group's "
                                 "or entry's own fields, into that object's allOf "
                                 "(SKIP-LOGIC.md).", **where)

    def length_cited(self, rel, here, node, key):
        """Whether x-provenance cites minLength/maxLength (key) on the node
        that carries it, the field it belongs to, or its $defs entry."""
        if isinstance(node.get("x-provenance"), dict) and key in node["x-provenance"]:
            return True
        field = self.field_at(rel, here)
        if field is not None and isinstance(field.schema, dict) and isinstance(
                field.schema.get("x-provenance"), dict) and key in field.schema["x-provenance"]:
            return True
        parts = here.split("/")
        if len(parts) >= 3 and parts[1] == "$defs":
            defs = self.pkg.docs.get(rel, {}).get("$defs")
            entry = defs.get(unesc(parts[2])) if isinstance(defs, dict) else None
            provenance = entry.get("x-provenance") if isinstance(entry, dict) else None
            return isinstance(provenance, dict) and key in provenance
        return False


def is_const_only(node):
    return isinstance(node, dict) and set(node) == {"const"}


def is_clause(node):
    """Whether a rule's test on a group is a clause on the group's own fields:
    {"required": [...], "properties": {...}}, or {"required": [...]} alone."""
    return isinstance(node, dict) and "required" in node and set(node) <= {"required", "properties"}


def is_rule_entry(entry):
    """Whether an allOf entry is meant as a rule: it has if, then or else, or a
    $comment that begins with a rule label."""
    comment = entry.get("$comment") if isinstance(entry, dict) else None
    return isinstance(entry, dict) and (any(key in entry for key in ("if", "then", "else")) or (
        isinstance(comment, str) and RULE_PREFIX_RE.match(comment) is not None))


def defines_code(node):
    if any(key in node for key in ("const", "enum", "pattern")):
        return True
    return any(isinstance(branch, dict) and any(key in branch for key in ("const", "enum", "pattern"))
               for keyword in ("oneOf", "anyOf", "allOf")
               for branch in (node.get(keyword) if isinstance(node.get(keyword), list) else []))


def rule_codes(rule, model):
    values = []
    for name, part, _ in rule.gates + rule.targets:
        prop = rule_field(model, rule, name)
        if prop is not None:
            values.extend(prop.declared_codes())
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


# Where a finding sits: its column, its display path (household[2].age), its
# field (household[].age), and - for a missing or undeclared field - the
# object holding it, as (display path, field) and the key.
Site = namedtuple("Site", "column path field holder key")
NO_SITE = Site(None, None, None, None, None)


class RowFinding(dict):
    """One finding about a row - the dict that is printed - plus the rule
    entry it comes from (rule_obj), which the toy-data verdicts read."""

    __slots__ = ("rule_obj",)

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.rule_obj = None


class RowChecker(object):
    """Validates rows one at a time against a table's items, and turns
    jsonschema's errors into findings a person can act on."""

    def __init__(self, an, model):
        self.an = an
        self.model = model
        self.declared = set(model.props)
        self.validator, self.direct = self.build_validator()
        self.rules = {rule.index: rule for rule in model.rules if rule.scope is None}
        self.nested = {id(rule.node): rule for rule in model.rules if rule.scope is not None}
        root = model.doc
        self.min_items = root.get("minItems") if is_integral(root.get("minItems")) else None
        self.unique = root.get("uniqueItems") is True
        self._allowed = {}
        self._absent_seen = {}

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
            out.append({"row": None, "column": None, "field": None, "path": None,
                        "keyword": "minItems",
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
                    out.append({"row": i, "column": None, "field": None, "path": None,
                                "keyword": "uniqueItems",
                                "message": "Row {} repeats row {} exactly.".format(i, first),
                                "hint": "The table does not allow two identical rows; remove the "
                                        "repeat."})
        out.sort(key=finding_order)
        return out

    def check_row(self, row, i, empties=frozenset()):
        bad_cells = nonfinite_cells(row)
        self._absent_seen = {}
        try:
            errors = list(self.validator.iter_errors(row))
        except Exception as exc:  # a schema the validator cannot run: reported, never raised
            return [{"row": i, "column": None, "field": None, "path": None, "keyword": "error",
                     "message": clip("The validator could not check this row ({}: {}).".format(
                         type(exc).__name__, exc)),
                     "hint": "Run `validate.py check` and fix the schema errors it reports."}]
        out = []
        for error in errors:
            out.extend(self.describe(error, row, i, empties))
        if self.direct and isinstance(row, dict):
            out.extend({"row": i, "column": key, "field": key, "path": key,
                        "keyword": "unevaluatedProperties",
                        "message": clip("{} is not a column of this table.".format(key)),
                        "hint": clip(UNDECLARED_HINT.format(key))}
                       for key in row if key not in self.declared)
        if bad_cells:
            out = [item for item in out if item["column"] not in bad_cells]
            for column, (token, steps) in bad_cells.items():
                path, field = self.place([column] + steps) if column is not None else (None, None)
                out.append({"row": i, "column": column, "field": field, "path": path,
                            "keyword": "non-finite",
                            "message": "{} holds {}, which is not a number JSON can hold.".format(
                                path if path is not None else "The row", token),
                            "hint": "JSON has no NaN or Infinity; write the field's missing-value "
                                    "code, or a real number."})
        return out

    def describe(self, error, row, i, empties):
        if (error.validator in ("anyOf", "oneOf") and error.context
                and isinstance(error.instance, (list, dict))):
            inner = self.branch_errors(error)
            if inner:
                out = []
                for sub in inner:
                    out.extend(self.describe(sub, row, i, empties))
                return out
        tokens = list(error.absolute_path)
        rule = self.attribute(error)
        sites = (self.absent_sites(error, rule, tokens, row) if is_false_error(error)
                 else self.sites(error, tokens, row))
        scope_path = (self.scope_display(tokens, rule.scope)
                      if rule is not None and rule.scope is not None and tokens else None)
        out = []
        for site in sites:
            empty = (site.column is not None and site.path == site.column
                     and (i, site.column) in empties)
            item = RowFinding()
            item["row"] = i
            item["column"] = site.column
            item["field"] = site.field
            item["path"] = site.path
            item["keyword"] = "false" if is_false_error(error) else error.validator
            item["message"] = clip(self.message(error, site, rule, empty))
            item["hint"] = clip(self.hint(error, site, rule, empty, scope_path))
            if rule is not None:
                if rule.id:
                    item["rule"] = rule.id
                if rule.scope is None:
                    item["allof_index"] = rule.index
                else:
                    item["rule_scope"] = rule.scope
                item.rule_obj = rule
            if empty:
                item["empty_cell"] = True
            out.append(item)
        return out

    def sites(self, error, tokens, row):
        keyword = error.validator
        if not tokens:
            if keyword == "required":
                name = self.required_name(error, row)
                return [Site(name, name, name, None, name)]
            if keyword == "unevaluatedProperties":
                if not isinstance(row, dict):
                    return []
                # Every column of a failing category is reported as unevaluated too;
                # only the ones no category declares are real.
                return [Site(key, key, key, None, key) for key in row
                        if key not in self.declared and repr(key) in error.message]
            return [NO_SITE]
        column = tokens[0] if isinstance(tokens[0], str) else None
        if column is None:
            return [NO_SITE]
        path, field = self.place(tokens)
        if keyword == "required":
            name = self.required_name(error, error.instance)
            if name is None:
                return [Site(column, path, field, None, None)]
            return [Site(column, join_path(path, name), self.step(field, name), (path, field),
                         name)]
        if keyword in ("additionalProperties", "unevaluatedProperties") and isinstance(
                error.instance, dict):
            extras = self.extra_keys(error)
            if extras:
                return [Site(column, join_path(path, key), self.step(field, key), (path, field),
                             key) for key in extras]
            if keyword == "unevaluatedProperties":
                return []
        return [Site(column, path, field, None, None)]

    def absent_sites(self, error, rule, tokens, row):
        """Where a {"t": false} effect found t present. jsonschema names neither
        the field nor the keyword - the error sits on the object, the value
        is t's - so the name comes from the rule's then: the k-th such error
        on one object is its k-th present name, in the then's order."""
        names = false_names(error, rule, row)
        seen = (tuple(tokens), tuple(error.absolute_schema_path))
        k = self._absent_seen.get(seen, 0)
        self._absent_seen[seen] = k + 1
        name = names[min(k, len(names) - 1)] if names else None
        if not tokens:
            return [Site(name, name, name, None, name)] if name is not None else [NO_SITE]
        column = tokens[0] if isinstance(tokens[0], str) else None
        if column is None:
            return [NO_SITE]
        path, field = self.place(tokens)
        if name is None:
            return [Site(column, path, field, None, None)]
        return [Site(column, join_path(path, name), self.step(field, name), (path, field), name)]

    def place(self, tokens):
        """(display path, field) of an instance path: positions count from 1
        in the display and become [] in the field; a lookup's names become .*."""
        path = field = tokens[0]
        for token in tokens[1:]:
            if isinstance(token, int):
                path += "[{}]".format(token + 1)
                field += "[]"
            else:
                path = join_path(path, str(token))
                field = self.step(field, str(token))
        return path, field

    def step(self, field, key):
        return field_step(self.model.fields, field, key)

    def scope_display(self, tokens, scope):
        """The display path of the object a nested rule applies to."""
        path = field = tokens[0]
        if field == scope:
            return path
        for token in tokens[1:]:
            if isinstance(token, int):
                path += "[{}]".format(token + 1)
                field += "[]"
            else:
                path = join_path(path, str(token))
                field = self.step(field, str(token))
            if field == scope:
                return path
        return scope

    def branch_errors(self, error):
        """The errors of the one branch of a failing anyOf/oneOf that takes a
        value of this kind (the list branch, for a list), or None."""
        branches = error.validator_value if isinstance(error.validator_value, list) else []
        want = "array" if isinstance(error.instance, list) else "object"
        matching = []
        for k, branch in enumerate(branches):
            site = self.an.pkg.node_at.get(id(branch)) if isinstance(branch, dict) else None
            target = self.an.deref(branch, site[0])[0] if site is not None else branch
            if want in json_kinds(target):
                matching.append(k)
        if len(matching) != 1:
            return None
        return [sub for sub in error.context
                if sub.relative_schema_path and sub.relative_schema_path[0] == matching[0]] or None

    @staticmethod
    def extra_keys(error):
        schema = error.schema if isinstance(error.schema, dict) else {}
        props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        if error.validator == "unevaluatedProperties":
            return [key for key in error.instance if key not in props and repr(key) in error.message]
        patterns = (schema.get("patternProperties")
                    if isinstance(schema.get("patternProperties"), dict) else {})
        return [key for key in error.instance if key not in props
                and not any(search_quietly(pattern, key) for pattern in patterns)]

    def attribute(self, error):
        path = list(error.absolute_schema_path)
        while path and path[0] in ("$ref", "items"):
            path.pop(0)
        if len(path) >= 2 and path[0] == "allOf" and isinstance(path[1], int):
            rule = self.rules.get(path[1])
            if rule is not None:
                return rule
        return self.nested_rule(error) if self.nested else None

    def nested_rule(self, error):
        """The rule entry of a nested object's allOf that the failing keyword
        sits in, found by walking the schema path from the table's items
        (jsonschema leaves $ref out of the path, so references are followed
        wherever the next step is not the node's own keyword)."""
        pkg = self.an.pkg
        node, rel, found = self.validator.schema, self.model.mother, None
        tokens = list(error.absolute_schema_path)
        i = 0
        while i < len(tokens) and isinstance(node, dict):
            token = tokens[i]
            hops = 0
            while (isinstance(token, str) and token not in node
                   and isinstance(node.get("$ref"), str) and hops < REF_HOPS):
                resolved, _ = pkg.lookup(pkg.uri.get(rel, self.model.uri), node["$ref"])
                target = resolved.contents if resolved is not None else None
                site = pkg.node_at.get(id(target)) if isinstance(target, dict) else None
                if site is None:
                    return found
                node, rel = target, site[0]
                hops += 1
            if not isinstance(token, str) or token not in node:
                break
            value = node[token]
            i += 1
            if token in SUB_MAP and isinstance(value, dict):
                if i >= len(tokens):
                    break
                node = value.get(tokens[i])
                i += 1
            elif isinstance(value, list):
                if i >= len(tokens) or not isinstance(tokens[i], int) or not (
                        0 <= tokens[i] < len(value)):
                    break
                node = value[tokens[i]]
                i += 1
            elif isinstance(value, dict):
                node = value
            else:
                break
            if isinstance(node, dict):
                site = pkg.node_at.get(id(node))
                if site is not None:
                    rel = site[0]
                found = self.nested.get(id(node), found)
        return found

    @staticmethod
    def required_name(error, row):
        names = error.validator_value if isinstance(error.validator_value, list) else []
        absent = [name for name in names if isinstance(name, str)
                  and not (isinstance(row, dict) and name in row)]
        for name in absent:
            if "{!r} is a required property".format(name) == error.message:
                return name
        return absent[0] if absent else None

    def allowed(self, field):
        if field not in self._allowed:
            target = self.model.fields.get(field) if isinstance(field, str) else None
            text = None
            if target is not None:
                text = target.allowed_text()
            elif isinstance(field, str) and field.endswith("[]"):
                owner = self.model.fields.get(field[:-2])
                if owner is not None and owner.shape == "list":
                    text = owner.item_allowed_text()
            self._allowed[field] = text
        return self._allowed[field]

    def message(self, error, site, rule, empty):
        keyword, value = error.validator, error.instance
        subject = site.path if site.path is not None else "The row"
        if is_false_error(error):
            if site.key is None:
                return "{} holds a field that is not allowed here.".format(subject)
            if rule is None:
                return "{} is present, but it may not be here.".format(subject)
            return "{} is present, but {} leaves it out here.".format(subject, rule.label())
        if keyword == "required":
            return ("The {} cell is empty.".format(site.column) if empty
                    else "{} is missing.".format(site.path))
        if keyword in ("additionalProperties", "unevaluatedProperties") and site.holder is not None:
            return "{} is not a field of {}.".format(site.path, owner_name(site.holder[1]))
        if keyword == "unevaluatedProperties":
            return "{} is not a column of this table.".format(site.column)
        if keyword in ("anyOf", "oneOf") and rule is not None and rule.mode == "any" and (
                site.column is None or (rule.scope is not None and site.field == rule.scope)):
            names = ", ".join(name for name, _, _ in rule.targets)
            if site.column is None:
                return "{} needs at least one of {} to hold; none does.".format(
                    cap_first(rule.label()), names)
            return "{} needs at least one of {} to hold in {}; none does.".format(
                cap_first(rule.label()), names, site.path)
        if "propertyNames" in error.absolute_schema_path and isinstance(value, str):
            return "{} has the name {}, which {}.".format(
                subject, show(value), "does not match {}".format(error.validator_value)
                if keyword == "pattern" else "is not an allowed name")
        if keyword == "type":
            if site.column is None:
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
        if keyword in ("minItems", "maxItems") and isinstance(value, list):
            return count_message(subject, keyword, len(value), error.validator_value)
        if keyword == "uniqueItems" and isinstance(value, list):
            return repeat_message(subject, value)
        if keyword in CONTAINS_KEYS and isinstance(value, list):
            return self.contains_message(error, subject)
        if keyword in LENGTH_KEYS and isinstance(value, str) and is_integral(error.validator_value):
            return length_message(subject, keyword, len(value), int(error.validator_value))
        if keyword in ("minProperties", "maxProperties") and isinstance(value, dict) and is_integral(
                error.validator_value):
            limit = int(error.validator_value)
            return "{} has {}; {} {} {} {}.".format(
                subject, plural(len(value), "name"), "at most" if keyword == "maxProperties"
                else "at least", limit, "is" if limit == 1 else "are",
                "allowed" if keyword == "maxProperties" else "required")
        if isinstance(value, (list, dict)):            # never print a whole value's repr
            try:
                whole = repr(value) in error.message
            except Exception:
                whole = True
            if whole:
                return "{} does not meet its {} ({}).".format(subject, keyword,
                                                             show(error.validator_value))
        return "{}: {}".format(subject, error.message)

    def contains_message(self, error, subject):
        schema = error.schema if isinstance(error.schema, dict) else {}
        target = schema.get("contains")
        one, many = match_words(target)
        need, _ = contains_need(schema)
        high = int(schema["maxContains"]) if is_integral(schema.get("maxContains")) else None
        if error.validator == "contains":
            return "{} has no {}; it needs {}.".format(subject, one, need)
        counts = [self.an.node_admits(target, item) for item in error.instance]
        count = None if any(c is None for c in counts) else sum(1 for c in counts if c)
        if error.validator == "maxContains":
            limit = high if high is not None else error.validator_value
            if count is None:
                return "{} has too many {}; at most {} {} allowed.".format(
                    subject, many, limit, "is" if limit == 1 else "are")
            return "{} has {} {}; at most {} {} allowed.".format(
                subject, count, one if count == 1 else many, limit, "is" if limit == 1 else "are")
        if count is None:
            return "{} has too few {}; it needs {}.".format(subject, many, need)
        return "{} has {} {}; it needs {}.".format(subject, count, one if count == 1 else many,
                                                   need)

    def hint(self, error, site, rule, empty, scope_path=None):
        keyword = error.validator
        if rule is not None and (keyword == "required" or is_false_error(error)):
            return self.rule_hint(rule, scope_path)
        if keyword == "required":
            if site.holder is not None:
                field = self.model.fields.get(site.field)
                codes = special_codes(field.profile()) if field is not None else []
                lead = "{} needs {}.".format(site.holder[0], site.key)
                subject = site.field
            else:
                prop = self.model.props.get(site.column)
                codes = special_codes(prop.profile()) if prop is not None else []
                lead = ("The cell is empty, but every row needs {}.".format(site.column) if empty
                        else "Every row needs {}.".format(site.column))
                subject = site.column
            if codes:
                return "{} When the value is missing, write one of its missing-value codes: {}.".format(
                    lead, ", ".join(code_text(code) for code in codes[:6]))
            return ("{} The data dictionary gives {} no missing-value code, so ask the data "
                    "steward how a missing value is recorded.".format(lead, subject))
        if keyword in ("additionalProperties", "unevaluatedProperties") and site.holder is not None:
            return ("{} is not in the data dictionary. Remove the field, or ask for it to be added "
                    "to the schemas.".format(site.field))
        if keyword == "unevaluatedProperties":
            return UNDECLARED_HINT.format(site.column)
        if rule is not None:
            return self.rule_hint(rule, scope_path)
        if site.column is None:
            return "Each row is an object of column: value pairs."
        allowed = self.allowed(site.field)
        if allowed:
            return "Allowed in {}: {}.".format(site.field, allowed)
        return "Check this value against {}'s definition in the data dictionary.".format(site.field)


    @staticmethod
    def rule_hint(rule, scope_path=None):
        reading = rule.reading or rule.comment or ""
        place = "this row" if rule.scope is None else (scope_path or rule.scope)
        return "{} applies to {}{}".format(
            cap_first(rule.label()), place, ": " + reading if reading else ".")


def is_false_error(error):
    """A value a false schema refuses: jsonschema reports it with no keyword."""
    return error.validator is None and error.schema is False


def false_names(error, rule, row):
    """The names a rule's {"t": false} effects find present in the object a
    false-schema error sits on, in the then's order: the properties the
    error's schema path reaches from the rule's then, against the row."""
    path = list(error.absolute_schema_path)
    then = rule.node.get("then") if rule is not None else None
    props = None
    for start in (k for k, token in enumerate(path) if token == "then"):
        node = then
        for token in path[start + 1:]:
            if isinstance(node, dict) and isinstance(token, str) and token in node:
                node = node[token]
            elif isinstance(node, list) and isinstance(token, int) and 0 <= token < len(node):
                node = node[token]
            else:
                node = None
                break
        if isinstance(node, dict):
            props = node
            break
    obj = row
    for token in error.absolute_path:
        if isinstance(obj, dict) and isinstance(token, str) and token in obj:
            obj = obj[token]
        elif isinstance(obj, list) and isinstance(token, int) and 0 <= token < len(obj):
            obj = obj[token]
        else:
            return []
    if not isinstance(props, dict) or not isinstance(obj, dict):
        return []
    return [name for name, sub in props.items() if sub is False and name in obj]


UNDECLARED_HINT = ("{} is not in the data dictionary. Remove the column, or ask for it to be added "
                   "to the schemas.")
CATEGORY_EVALUATORS = ("patternProperties", "additionalProperties", "unevaluatedProperties",
                       "allOf", "anyOf", "oneOf", "if", "then", "else", "dependentSchemas", "$ref",
                       "$dynamicRef")
PLAIN_ITEMS_KEYS = frozenset(("type", "title", "description", "$comment", "allOf",
                              "unevaluatedProperties"))


def owner_name(field):
    """The variable an object belongs to: visits for visits[]."""
    return field[:-2] if isinstance(field, str) and field.endswith("[]") else field


def search_quietly(pattern, text):
    try:
        return re.search(pattern, text) is not None
    except (re.error, TypeError):
        return False


def count_message(subject, keyword, count, limit):
    limit = int(limit) if is_integral(limit) else limit
    have = plural(count, "entry", "entries")
    if keyword == "maxItems":
        if limit == 0:
            return "{} has {}; it must be empty here.".format(subject, have)
        return "{} has {}; at most {} {} allowed.".format(subject, have, limit,
                                                         "is" if limit == 1 else "are")
    return "{} has {}; at least {} {} required.".format(subject, have, limit,
                                                       "is" if limit == 1 else "are")


def repeat_message(subject, items):
    first = {}
    for k, item in enumerate(items):
        key = canonical_json(item)
        if key in first:
            return "{0} repeats an entry ({0}[{1}] is the same as {0}[{2}]).".format(
                subject, k + 1, first[key] + 1)
        first[key] = k
    return "{} repeats an entry.".format(subject)


def length_message(subject, keyword, length, limit):
    if keyword == "maxLength":
        return "{} is {} long; at most {} {} allowed.".format(
            subject, plural(length, "character"), limit, "is" if limit == 1 else "are")
    return "{} is {} long; at least {} {} required.".format(
        subject, plural(length, "character"), limit, "is" if limit == 1 else "are")


def contains_need(schema):
    """("exactly 1" | "at least 2" | "between 1 and 3" | "at most 2", the
    least) for a list's contains with its minContains and maxContains."""
    low = int(schema["minContains"]) if is_integral(schema.get("minContains")) else 1
    high = int(schema["maxContains"]) if is_integral(schema.get("maxContains")) else None
    if high is not None and high == low:
        return "exactly {}".format(low), low
    if high is not None:
        return ("between {} and {}".format(low, high) if low else "at most {}".format(high)), low
    return "at least {}".format(low), low


def match_words(node):
    """("entry with relation = "self"", "entries with ...") for a contains
    schema."""
    if isinstance(node, dict) and "const" in node and set(node) <= {
            "const", "title", "x-value-kind", "$comment"}:
        tail = " equal to {}".format(show(node["const"]))
        return "entry" + tail, "entries" + tail
    if isinstance(node, dict) and set(node) == {"enum"} and isinstance(node["enum"], list):
        tail = " equal to one of {}".format(show_list(node["enum"]))
        return "entry" + tail, "entries" + tail
    props = node.get("properties") if isinstance(node, dict) else None
    if isinstance(props, dict) and props:
        parts = [condition_words(name, test) for name, test in props.items()]
        if all(parts):
            tail = " with " + " and ".join(parts)
            return "entry" + tail, "entries" + tail
    if is_typed(node) and json_kinds(node) <= {"number", "string", "boolean"}:
        text = describe_typed(node)
        return "entry that is " + text, "entries that are " + text
    return "matching entry", "matching entries"


def condition_words(name, test):
    if is_const_only(test):
        return "{} = {}".format(name, show(test["const"]))
    if isinstance(test, dict) and set(test) == {"enum"} and isinstance(test["enum"], list):
        return "{} one of {}".format(name, show_list(test["enum"]))
    if isinstance(test, dict) and set(test) == {"not"} and is_const_only(test["not"]):
        return "{} other than {}".format(name, show(test["not"]["const"]))
    return None


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
    rules = {rule.index: rule for rule in model.rules if rule.scope is None}
    for i, _ in enumerate(items.get("allOf") or []):
        rule = rules.get(i)
        if rule is not None:
            if not rule.grammar_ok or any(rule_field(model, rule, name) is None
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
    """{column: (token, steps inside the cell)} for each NaN or Infinity;
    the column None for a row that is not an object."""
    if isinstance(row, NonFinite):
        return {None: (row.token, [])}
    if not isinstance(row, dict):
        found = find_nonfinite_steps(row)
        return {None: (found[1], [])} if found else {}
    cells = {}
    for key, value in row.items():
        found = find_nonfinite_steps(value)
        if found is not None:
            cells[key] = (found[1], found[0])
    return cells


def find_nonfinite_steps(value):
    """(keys and positions leading to a NonFinite inside value, token), or None."""
    stack = [(value, [])]
    while stack:
        node, steps = stack.pop()
        if isinstance(node, NonFinite):
            return steps, node.token
        if isinstance(node, dict):
            stack.extend((item, steps + [key]) for key, item in node.items())
        elif isinstance(node, list):
            stack.extend((item, steps + [i]) for i, item in enumerate(node))
    return None


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
                       "properties": len(model.props), "fields": len(model.fields) - len(model.props),
                       "rules": len(model.rules)})
    return {"ok": counts["error"] == 0, "package": an.label, "files": len(an.pkg.files),
            "tables": tables, "counts": counts, "findings": shown, "truncated": truncated}


def rules_report(an, table=None, cap=DEFAULT_CAP):
    names = select_tables(an, table)
    rules, variables = [], {}
    mothers = {an.tables[name].mother: name for name in names}
    for name in names:
        model = an.tables[name]
        rules.extend(rule.public() for rule in model.rules if rule.grammar_ok)
        variables[name] = {field.path: {"topic": field.topic, "file": field.file,
                                        "pointer": field.pointer, "shape": field.shape,
                                        "parent": field.parent, "title": field.title()}
                           for field in model.fields.values()}
    nested = {(box["rel"], box["pointer"] + "/allOf") for box in an.containers.values()
              if box["kind"] == "object" and isinstance(box["node"].get("allOf"), list)
              and box["uses"][0][0].name in names}
    findings = by_severity([
        item for item in an.findings
        if (item.get("file") in mothers and (
            item["code"] in RULE_CODES or item["code"] == "parse-error"
            or str(item.get("pointer", "")).startswith("/items/allOf")))
        or any(item.get("file") == rel and (str(item.get("pointer", "")) + "/").startswith(at + "/")
               for rel, at in nested)])
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
            first = next((item for item in items if item["column"] in model.props), None)
            prop = model.props.get(first["column"]) if first else None
            findings.append(finding(
                "error", "valid-fails",
                "valid.json {} fails: {}".format("row {}".format(row) if row is not None
                                                 else "as a whole", items[0]["message"]),
                "Every valid.json row must pass: fix the row, or the schema if the row is right.",
                file=base + "valid.json", pointer="/{}".format(row) if row is not None else None,
                table=model.name, topic=prop.topic if prop else None,
                variable=(first.get("field") or first["column"]) if first else None,
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
        prop = model.fields.get(field_of_column(model, column)) if isinstance(column, str) else None
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
        column = field_of_column(model, column)
        items = by_row.get(row, [])
        pairs = [cover_pairs(item, checker) for item in items]
        covers = [set().union(*(cover for _, cover in each)) for each in pairs]
        failed_on = sorted({name for each in pairs for name, _ in each})
        if not items:
            verdict["status"] = "missed-passed"
            findings.append(finding(
                "error", "missed-passed",
                "invalid.json row {} ({} on {}) passes the schemas.".format(row, show(kind), column),
                "The seeded value is legal, or the rule it should trip is missing: check the value "
                "against the data dictionary, and the rule against SKIP-LOGIC.md.", row=row, **here))
        elif not any(column in cover for cover in covers):
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
            caught_rules.update(rule_of(item, checker).key for item, cover in zip(items, covers)
                                if column in cover and rule_of(item, checker) is not None)
            if rules:
                verdict["rules"] = rules
        else:
            verdict["status"] = "caught-with-extra"
            verdict["failed_on"] = failed_on
            extra = sorted({name for each in pairs for name, cover in each if column not in cover})
            findings.append(finding(
                "error", "caught-with-extra",
                "invalid.json row {} fails on {} as seeded, but also on {}.".format(
                    row, column, ", ".join(extra)),
                "Change the row so it breaks only {}: one seeded violation per row.".format(column),
                row=row, **here))
        verdicts.append(verdict)
    unledgered = sorted(row for row in by_row if row not in ledgered)
    for row in unledgered:
        names = sorted({item.get("field") or item["column"] or "(the row)" for item in by_row[row]})
        findings.append(finding(
            "error", "unledgered",
            "invalid.json row {} fails ({}) but the ledger has no case for it.".format(
                row, ", ".join(names)),
            "Add a ledger case naming its column and kind, or fix the row.", row=row,
            **dict(where, pointer="/{}".format(row))))
    return {"rows": len(rows), "cases": len(cases), "caught": caught, "verdicts": verdicts,
            "unledgered": unledgered}


def field_of_column(model, column):
    """The Field path a ledger case's column names: a concrete key under a
    lookup (labs.ldl) is the lookup's labs.*, a position (household[2]) is
    household[]; anything else is kept as written."""
    if not isinstance(column, str) or column in model.fields:
        return column
    for top in sorted(model.props, key=len, reverse=True):
        if not column.startswith(top) or len(column) == len(top):
            continue
        rest, at, field = column[len(top):], 0, top
        while at < len(rest):
            step = PATH_STEP.match(rest, at)
            if step is None:
                break
            text, at = step.group(0), step.end()
            if text == ".*":
                field += ".*"
            elif text == "[]" or text[1:-1].isdigit():
                field += "[]"
            elif text.startswith("["):
                try:
                    field = field_step(model.fields, field, json.loads(text[1:-1]))
                except ValueError:
                    break
            else:
                field = field_step(model.fields, field, text[1:])
        else:
            return field
    return column


def rule_of(item, checker):
    """The rule entry a row finding comes from, or None."""
    rule = getattr(item, "rule_obj", None)
    if rule is None and item.get("allof_index") is not None:
        rule = checker.rules.get(item["allof_index"])
    return rule


def cover_pairs(item, checker):
    """(name, what it counts as failing) for each name a finding fails on: its
    field, covering its column and every path enclosing it (household[].age
    covers household); *duplicate* for a repeated row; or, for an 'at least
    one of' rule, each of its targets."""
    rule = rule_of(item, checker)
    if item["column"] is None:
        if item["keyword"] == "uniqueItems":
            return [(DUPLICATE_COLUMN, {DUPLICATE_COLUMN})]
        if rule is not None and rule.mode == "any" and rule.targets:
            return [(name, target_cover(checker.model, rule, name)) for name, _, _ in rule.targets]
        return [("(the row)", {ROW_COVER})]
    field = item.get("field") or item["column"]
    cover = path_ancestors(item["column"], field)
    if rule is not None and rule.mode == "any" and rule.scope is not None and field == rule.scope:
        for name, _, _ in rule.targets:
            cover |= target_cover(checker.model, rule, name)
    return [(field, cover)]


def target_cover(model, rule, name):
    field = rule_field(model, rule, name)
    return path_ancestors(field.top, field.path) if field is not None else {name}


def cover_of(item, checker):
    """Every column and path a finding counts as failing."""
    return set().union(*(cover for _, cover in cover_pairs(item, checker)))


def field_step(fields, field, key):
    """The field a key leads to from field: a named field, or a lookup's .*."""
    named = join_path(field, key)
    if named in fields:
        return named
    star = field + ".*"
    return star if star in fields else named


def gather_values(model, rows):
    """What rows show, by field path: the values seen ({path: literal keys},
    a list's entries under path[]), the lengths of its lists, and the objects
    at each path (None: the rows themselves)."""
    seen, lengths, objects = {}, {}, {None: []}

    def walk(value, path, depth):
        seen.setdefault(path, set()).add(literal_key(value))
        if depth >= GATHER_LIMIT:
            return
        if isinstance(value, list):
            lengths.setdefault(path, set()).add(len(value))
            for item in value:
                walk(item, path + "[]", depth + 1)
        elif isinstance(value, dict):
            objects.setdefault(path, []).append(value)
            for key, item in value.items():
                walk(item, field_step(model.fields, path, str(key)), depth + 1)

    for row in rows:
        if isinstance(row, dict):
            objects[None].append(row)
            for key, value in row.items():
                walk(value, key, 0)
    return seen, lengths, objects


def field_gaps(field, seen, lengths, objects):
    """(has requirements, [(message, hint)]) of what valid rows do not show
    for one field."""
    gaps, requires = [], False
    path = field.path
    wanted = field.required_values()
    if wanted is not None:
        requires = True
        key = path + "[]" if field.shape == "list" else path
        missing = [value for value in wanted if literal_key(value) not in seen.get(key, ())]
        if missing:
            listed = joined(missing, "or") if len(missing) <= 8 else show_list(missing)
            if field.shape == "list":
                gaps.append(("valid.json never shows {} in {}.".format(listed, path),
                             "Add valid rows whose {} includes {}, so every declared code is "
                             "seen to pass.".format(path, show_list(missing))))
            else:
                gaps.append(("valid.json never shows {} = {}.".format(path, listed),
                             "Add valid rows using {}, so every declared code (or both bounds and "
                             "every special code) is seen to pass.".format(show_list(missing))))
    if field.shape in ("list", "entries") and field.info is not None:
        arr = field.info.arr
        fewest = int(arr["minItems"]) if is_integral(arr.get("minItems")) else 0
        if "contains" in arr:                       # it holds minContains matches (1 unless said)
            fewest = max(fewest, contains_need(arr)[1])
        most = int(arr["maxItems"]) if is_integral(arr.get("maxItems")) else None
        if most is None or fewest <= most:
            requires = True
            have = lengths.get(path, set())
            if fewest not in have:
                gaps.append(("valid.json never shows {} with {}.".format(
                    path, plural(fewest, "entry", "entries")),
                    "Add a valid row whose {} has the fewest entries allowed ({}), so the short "
                    "end of the list is seen to pass.".format(path, fewest)))
            if (most is None or most >= 2) and not any(n >= 2 for n in have):
                gaps.append(("valid.json never shows {} with two or more entries.".format(path),
                             "Add a valid row whose {} has two or more entries, so a longer list "
                             "is seen to pass.".format(path)))
    if field.shape == "lookup":
        requires = True
        if not any(obj for obj in objects.get(path, ())):
            gaps.append(("valid.json never shows a name in {}.".format(path),
                         "Add a valid row whose {} holds at least one name, so the lookup is seen "
                         "to pass.".format(path)))
    if field.optional:
        requires = True
        if not any(field.name not in obj for obj in objects.get(field.scope, ())):
            gaps.append(("valid.json never leaves out {}.".format(path),
                         "Add a valid row that leaves {} out, so leaving it out - which a decision "
                         "allows - is seen to pass.".format(path)))
    return requires, gaps


def fixture_coverage(an, model, valid, caught_rules, judged, findings):
    seen, lengths, objects = gather_values(model, valid)
    covered, total, per_prop = 0, 0, {}
    for path, field in model.fields.items():
        requires, gaps = field_gaps(field, seen, lengths, objects)
        if not requires:
            continue
        total += 1
        per_prop[path] = not gaps
        if not gaps:
            covered += 1
        for message, hint in gaps:
            findings.append(finding(
                "warning", "coverage-gap", message, hint, file=field.file, pointer=field.pointer,
                table=model.name, topic=field.topic, variable=path))
    fired, unfired, caught, uncaught = [], [], [], []
    for rule in model.rules:
        if not rule.grammar_ok:
            continue
        label = rule.half()
        if rule.scope is None:
            test = Draft202012Validator(
                {"$ref": "{}#/items/allOf/{}/if".format(model.uri, rule.index)},
                registry=an.pkg.registry)
            instances = valid
        else:
            test = Draft202012Validator(
                {"$ref": "{}#{}".format(an.pkg.uri[rule.file],
                                        quote(rule.pointer + "/if", safe="/~"))},
                registry=an.pkg.registry)
            instances = objects.get(rule.scope, [])
        hit = False
        for instance in instances:
            try:
                if test.is_valid(instance):
                    hit = True
                    break
            except Exception:
                break
        where = {"file": rule.file, "pointer": rule.pointer, "table": model.name,
                 "rule": rule.id, "topic": rule.topic}
        if hit:
            fired.append(label)
        else:
            unfired.append(label)
            if rule.scope is None:
                message = "No valid.json row triggers {}.".format(rule.label())
                hint = "Add a valid row the rule applies to, so it is seen working."
            else:
                message = "No valid.json value at {} triggers {}.".format(rule.scope, rule.label())
                hint = ("Add a valid row whose {} satisfies the rule's if, so it is seen "
                        "working.".format(rule.scope))
            findings.append(finding("warning", "coverage-gap", message, hint, **where))
        if rule.key in caught_rules:
            caught.append(label)
        else:
            uncaught.append(label)
        if judged and rule.key not in caught_rules:
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
    fields = {field.path: {"title": field.title(), "topic": field.topic, "column": field.top,
                           "allowed": checker.allowed(field.path), "shape": field.shape}
              for field in model.fields.values() if field.depth > 0}
    return {"ok": not findings, "table": name, "file": str(file), "format": fmt,
            "rows": len(rows), "errors": len(findings), "by_column": by_column,
            "by_rule": by_rule, "findings": shown, "truncated": truncated, "columns": columns,
            "fields": fields}


def provenance_census(an):
    props = [field for model in an.tables.values() for field in model.fields.values()]
    traced = sum(1 for prop in props if an.prov_ok.get((prop.file, prop.pointer)))
    rules = sum(1 for model in an.tables.values() for rule in model.rules
                if an.prov_ok.get(rule.key))
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
            inner = [field for field in model.fields.values()
                     if field.depth > 0 and field.top in names]
            errors = sum(1 for item in every if item.get("table") == name
                         and item.get("topic") == topic and item["severity"] == "error")
            warnings = sum(1 for item in every if item.get("table") == name
                           and item.get("topic") == topic and item["severity"] == "warning")
            prov_errors = any(item.get("file") == rel and item["code"].startswith("provenance-")
                              and item["severity"] == "error" for item in every)
            entry = {"file": rel, "properties": len(props), "fields": len(inner),
                     "rules_targeting": sum(1 for rule in model.rules if any(
                         getattr(rule_field(model, rule, t), "top", None) in names
                         for t, _, _ in rule.targets)),
                     "errors": errors, "warnings": warnings,
                     "provenance_ok": not prov_errors and all(
                         an.prov_ok.get((prop.file, prop.pointer)) for prop in props + inner),
                     "coverage": None}
            if per_prop is not None:
                counted = [prop.path for prop in props + inner if prop.path in per_prop]
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
