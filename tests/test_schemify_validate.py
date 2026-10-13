#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pytest>=8", "jsonschema>=4.18", "referencing>=0.35"]
# ///
"""Tests for skills/schemify/scripts/validate.py: check's house-style and
rule-grammar lint, the normalized rules, the toy-data verdicts and coverage,
data-file validation with QuaC's CSV typing, the summary, and the CLI
contract (one JSON object, exit codes 0/1/2, never a traceback).

Run:  uv run tests/test_schemify_validate.py
      (fallback: pip install pytest "jsonschema>=4.18" referencing
       && pytest tests/test_schemify_validate.py)

Every test builds its own package in tmp_path - a small sleep-diary study
with one table, two topics, a skip pair, provenance.json and toy data - and
mutates it; nothing under examples/ is read.
"""

import copy
import csv
import importlib.util
import io
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "schemify" / "scripts" / "validate.py"
DRAFT = "https://json-schema.org/draft/2020-12/schema"
BASE = "https://schemas.example.org/lark/"
MOTHER = "sleep_diary/sleep_diary.schema.json"
PARTICIPANT = "sleep_diary/categories/participant.json"
SLEEP = "sleep_diary/categories/sleep.json"
DEFS = "common/defs.json"
NA = {"$ref": "../../common/defs.json#/$defs/not_applicable"}
DK = {"$ref": "../../common/defs.json#/$defs/dont_know"}
COLUMNS = ["participant_id", "site_id", "age", "chronotype", "sleep_minutes",
           "nap_yesterday", "nap_minutes", "caffeine"]


# ------------------------------------------------------------ the package


def prov(row, **facets):
    out = {"default": "S01:Variables row {}".format(row)}
    out.update(facets)
    return out


def codes(*pairs):
    return [{"const": value, "title": title} for value, title in pairs]


def defs_doc():
    return {
        "$schema": DRAFT, "$id": BASE + DEFS, "title": "LARK — shared definitions",
        "$defs": {
            "not_applicable": {"const": -666, "title": "Not applicable (skipped by design)",
                               "x-value-kind": "sentinel", "x-provenance": prov(2)},
            "dont_know": {"const": -888, "title": "Don't know", "x-value-kind": "sentinel",
                          "x-provenance": prov(2)},
            "participant_id": {"type": "string", "pattern": "^P[0-9]{4}$",
                               "title": "Participant identifier",
                               "x-provenance": prov(1, pattern="D003")},
        },
    }


def participant_doc():
    return {
        "$schema": DRAFT, "$id": BASE + PARTICIPANT, "title": "Participant",
        "description": "Who kept the diary.", "type": "object",
        "x-variable-group": "participant",
        "properties": {
            "participant_id": {"title": "Participant identifier", "x-provenance": prov(1),
                               "x-role": "primary key",
                               "$ref": "../../common/defs.json#/$defs/participant_id"},
            "site_id": {"title": "Study site", "x-provenance": prov(3),
                        "oneOf": codes(("01", "Site 1"), ("02", "Site 2"), ("03", "Site 3"),
                                       ("04", "Site 4"), ("05", "Site 5"))},
            "age": {"title": "Age (years)", "x-provenance": prov(4), "x-unit": "years",
                    "anyOf": [{"type": "integer", "minimum": 18, "maximum": 90}, DK]},
            "chronotype": {"title": "Self-described chronotype", "x-provenance": prov(5),
                           "oneOf": codes((1, "Morning lark"), (2, "Night owl"),
                                          (3, "Neither")) + [DK]},
        },
        "required": ["participant_id", "site_id", "age", "chronotype"],
    }


def sleep_doc():
    return {
        "$schema": DRAFT, "$id": BASE + SLEEP, "title": "Sleep",
        "description": "Nightly sleep and naps from the morning diary.", "type": "object",
        "x-variable-group": "sleep",
        "properties": {
            "sleep_minutes": {"title": "Total sleep last night (minutes)",
                              "x-provenance": prov(6, maximum="D001"), "x-unit": "minutes",
                              "anyOf": [{"type": "integer", "minimum": 0, "maximum": 960}, NA, DK]},
            "nap_yesterday": {"title": "Napped yesterday", "x-provenance": prov(8),
                              "oneOf": codes((0, "No"), (1, "Yes")) + [DK]},
            "nap_minutes": {"title": "Nap duration yesterday (minutes)",
                            "x-provenance": prov(9, maximum="D002"), "x-unit": "minutes",
                            "anyOf": [{"type": "integer", "minimum": 0, "maximum": 600}, NA, DK]},
            "caffeine": {"title": "Caffeine after 2 pm", "x-provenance": prov(10),
                         "oneOf": codes((0, "No"), (1, "Yes"))},
        },
        "required": ["sleep_minutes", "nap_yesterday", "nap_minutes", "caffeine"],
    }


SKIP = {
    "$comment": "Skip pattern R001: no nap yesterday means nap duration is not applicable. "
                "Dictionary row 9: 'Asked only if nap_yesterday=1'.",
    "x-provenance": {"default": "S01:Variables row 9"},
    "if": {"required": ["nap_yesterday"], "properties": {"nap_yesterday": {"const": 0}}},
    "then": {"properties": {"nap_minutes": {"const": -666}}},
}
APPLICABILITY = {
    "$comment": "Applicability R001: a reported nap has a duration or an item-missing code, "
                "never the not-applicable code.",
    "x-provenance": {"default": "S01:Variables row 9"},
    "if": {"required": ["nap_yesterday"], "properties": {"nap_yesterday": {"const": 1}}},
    "then": {"properties": {"nap_minutes": {"not": {"const": -666}}}},
}


def mother_doc():
    return {
        "$schema": DRAFT, "$id": BASE + MOTHER, "title": "LARK — Sleep diary",
        "description": "Array of diary records. One element is one participant-night.",
        "type": "array", "minItems": 1,
        "items": {"type": "object", "title": "Sleep diary record",
                  "allOf": [{"$ref": "categories/participant.json"},
                            {"$ref": "categories/sleep.json"},
                            copy.deepcopy(SKIP), copy.deepcopy(APPLICABILITY)],
                  "unevaluatedProperties": False},
    }


def row(pid, site, age, chrono, sleep, nap_y, nap_m, caffeine):
    return dict(zip(COLUMNS, ("P{:04d}".format(pid), site, age, chrono, sleep, nap_y, nap_m,
                              caffeine)))


VALID = [
    row(1, "01", 18, 1, 0, 0, -666, 0),
    row(2, "02", 90, 2, 960, 1, 0, 1),
    row(3, "03", -888, 3, -666, 1, 600, 0),
    row(4, "04", 45, -888, -888, 1, -888, 1),
    row(5, "05", 60, 1, 420, -888, -666, 0),
    row(6, "01", 33, 2, 480, 0, -666, 1),
    row(7, "02", 71, 3, 390, 1, 45, 0),
    row(8, "03", 25, 1, 510, -888, 30, 1),
    row(9, "04", 52, 2, 455, 0, -666, 0),
    row(10, "05", 38, 3, 300, 1, 20, 1),
]


def invalid_rows():
    base = row(20, "02", 40, 2, 400, 1, 30, 0)
    rows, cases = [], []

    def seed(kind, column, reason, **change):
        r = dict(base, participant_id="P{:04d}".format(21 + len(rows)))
        for key, value in change.items():
            if value is DROP:
                del r[key]
            else:
                r[key] = value
        cases.append({"row": len(rows), "column": column, "kind": kind,
                      "value": change.get(column, None) if change.get(column) is not DROP else None,
                      "reason": reason})
        rows.append(r)

    seed("skip-break", "nap_minutes", "R001: no nap, so the duration must be -666",
         nap_yesterday=0, nap_minutes=30)
    seed("applicability-break", "nap_minutes", "R001: a nap never carries -666",
         nap_yesterday=1, nap_minutes=-666)
    seed("undeclared-column", "mood", "mood is not a column", mood=3)
    seed("missing-key", "caffeine", "every column is present", caffeine=DROP)
    seed("wrong-type", "age", "age is an integer, not text", age="45")
    seed("invented-sentinel", "sleep_minutes", "-999 is not a declared code", sleep_minutes=-999)
    seed("range-break", "nap_minutes", "naps are at most 600 minutes", nap_minutes=700)
    seed("pattern-break", "participant_id", "ids are P and four digits", participant_id="X12")
    seed("unknown-level", "chronotype", "chronotype is 1, 2, 3 or -888", chronotype=4)
    return rows, {"violations": cases}


DROP = object()

PROVENANCE = {
    "schemifyProvenance": 1,
    "sources": {
        "S01": {"kind": "document", "title": "Data dictionary v3", "status": "active"},
        "S02": {"kind": "web", "title": "Consortium page", "status": "suggested"},
        "S03": {"kind": "web", "title": "Protocol", "status": "approved"},
    },
    "decisions": {
        "D001": {"kind": "guess", "question": "Upper bound for sleep?", "answer": "960",
                 "by": "agent", "status": "provisional", "needsReview": True},
        "D002": {"kind": "guess", "question": "Upper bound for naps?", "answer": "600",
                 "by": "agent", "status": "provisional", "needsReview": True},
        "D003": {"kind": "knowledge", "question": "Id format?", "answer": "P + 4 digits",
                 "by": "steward", "status": "answered", "needsReview": False},
        "D004": {"kind": "guess", "question": "Old bound?", "by": "agent",
                 "status": "cancelled"},
        "D005": {"kind": "guess", "question": "Older bound?", "by": "agent",
                 "status": "superseded"},
    },
}


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_package(root):
    """Write the fixture package under root (the PKG folder) and return root."""
    schemas = root / "schemas"
    write_json(schemas / DEFS, defs_doc())
    write_json(schemas / PARTICIPANT, participant_doc())
    write_json(schemas / SLEEP, sleep_doc())
    write_json(schemas / MOTHER, mother_doc())
    write_json(root / "provenance.json", PROVENANCE)
    toy = root / "toy-data" / "sleep_diary"
    write_json(toy / "valid.json", VALID)
    bad, ledger = invalid_rows()
    write_json(toy / "invalid.json", bad)
    write_json(toy / "invalid-ledger.json", ledger)
    return root


# ------------------------------------------------------------------ helpers


@pytest.fixture(scope="session")
def v():
    spec = importlib.util.spec_from_file_location("schemify_validate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True          # leave no __pycache__ in the skill folder
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@pytest.fixture
def pkg(tmp_path):
    return build_package(tmp_path / "package")


def load(pkg, rel):
    return json.loads((pkg / "schemas" / rel).read_text(encoding="utf-8"))


def save(pkg, rel, doc):
    write_json(pkg / "schemas" / rel, doc)


def edit(pkg, rel, fn):
    doc = load(pkg, rel)
    fn(doc)
    save(pkg, rel, doc)


def toy(pkg, name):
    return pkg / "toy-data" / "sleep_diary" / name


def edit_toy(pkg, name, fn):
    doc = json.loads(toy(pkg, name).read_text(encoding="utf-8"))
    fn(doc)
    write_json(toy(pkg, name), doc)


def allof(doc):
    return doc["items"]["allOf"]


def check(v, pkg):
    return v.check_report(v.analyze(pkg), None)


def codes_of(report, severity=None):
    return [f["code"] for f in report["findings"]
            if severity is None or f["severity"] == severity]


def only(report, code):
    found = [f for f in report["findings"] if f["code"] == code]
    assert found, "no {} in {}".format(code, codes_of(report))
    return found


def run_main(v, monkeypatch, capsys, *argv):
    monkeypatch.setattr(sys, "argv", ["validate.py"] + [str(a) for a in argv])
    with pytest.raises(SystemExit) as exc:
        v.main()
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    return exc.value.code, json.loads(captured.out)


def add_rule(pkg, entry):
    edit(pkg, MOTHER, lambda d: allof(d).append(entry))


def rule(comment, if_, then, provenance=None):
    return {"$comment": comment, "x-provenance": provenance or {"default": "S01:Variables row 12"},
            "if": if_, "then": then}


def clause(**tests):
    return {"required": list(tests), "properties": tests}


def write_csv(path, rows, columns=COLUMNS, delimiter=","):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(columns)
    for r in rows:
        writer.writerow(["" if r.get(c) is None else r.get(c) for c in columns])
    path.write_text(buffer.getvalue(), encoding="utf-8")
    return path


# --------------------------------------------------------------- green path


def test_green_check_is_clean(v, pkg):
    report = check(v, pkg)
    assert report["ok"] is True
    assert report["findings"] == [] and report["counts"] == {"error": 0, "warning": 0, "info": 0}
    assert report["files"] == 4 and report["truncated"] is False
    assert report["tables"] == [{"table": "sleep_diary", "mother": MOTHER,
                                 "categories": [PARTICIPANT, SLEEP], "properties": 8,
                                 "rules": 2}]


def test_green_summary_headline(v, pkg):
    report = v.summary_report(v.analyze(pkg))
    assert report["ok"] is True
    assert report["headline"] == ("4 schema files valid · 2 rules · toy data: 10 valid rows pass, "
                                  "9/9 seeded errors caught · provenance: 8/8 properties traced "
                                  "(2 guesses need review)")
    census = report["provenance"]
    assert census["properties"] == 8 and census["traced"] == 8 and census["rules"] == 2
    assert census["needs_review"] == ["D001", "D002"]
    assert census["by_origin"] == {"document": 13, "web": 0, "person": 1, "agent": 2,
                                   "unknown": 0}
    assert report["rules"] == {"count": 2, "by_kind": {"skip": 1, "applicability": 1,
                                                       "routing": 0},
                               "by_table": {"sleep_diary": 2}}
    sleep = report["topics"]["sleep_diary/sleep"]
    assert sleep == {"file": SLEEP, "properties": 4, "rules_targeting": 2, "errors": 0,
                     "warnings": 0, "provenance_ok": True,
                     "coverage": {"covered": 4, "total": 4}}
    assert report["topics"]["sleep_diary/participant"]["coverage"] == {"covered": 3, "total": 3}


def test_green_fixtures_all_caught(v, pkg):
    report = v.fixtures_report(v.analyze(pkg))
    assert report["ok"] is True and report["findings"] == []
    table = report["tables"]["sleep_diary"]
    assert table["valid"] == {"rows": 10, "status": "pass", "findings": []}
    assert table["invalid"]["cases"] == 9 and table["invalid"]["caught"] == 9
    assert table["invalid"]["unledgered"] == []
    assert {x["status"] for x in table["invalid"]["verdicts"]} == {"caught"}
    assert table["invalid"]["verdicts"][0]["rules"] == ["R001"]
    assert table["coverage"] == {
        "properties": {"covered": 7, "total": 7},
        "rules": {"fired": ["R001:skip", "R001:applicability"], "unfired": [],
                  "caught": ["R001:skip", "R001:applicability"], "uncaught": []}}


def test_green_rules_normalized(v, pkg):
    report = v.rules_report(v.analyze(pkg))
    assert report["ok"] is True and report["findings"] == []
    skip, applicability = report["rules"]
    assert skip == {
        "table": "sleep_diary", "id": "R001", "kind": "skip", "domain": None, "index": 2,
        "file": MOTHER, "pointer": "/items/allOf/2", "comment": SKIP["$comment"],
        "reading": SKIP["$comment"].split(": ", 1)[1],
        "provenance": {"default": "S01:Variables row 9"},
        "when": {"any": [{"all": [{"variable": "nap_yesterday", "test": "eq", "value": 0}]}]},
        "then": {"mode": "all", "effects": [{"variable": "nap_minutes", "effect": "eq",
                                             "value": -666}]}}
    assert applicability["kind"] == "applicability" and applicability["index"] == 3
    assert applicability["then"]["effects"] == [{"variable": "nap_minutes", "effect": "ne",
                                                 "value": -666}]
    assert report["variables"]["sleep_diary"]["nap_minutes"] == {
        "topic": "sleep", "file": SLEEP, "pointer": "/properties/nap_minutes"}
    assert len(report["variables"]["sleep_diary"]) == 8


# ------------------------------------------------------- files, ids, refs


def test_parse_error_names_line_and_column(v, pkg):
    (pkg / "schemas" / SLEEP).write_text('{\n  "type": "object",\n  "title" "Sleep"\n}\n',
                                         encoding="utf-8")
    report = check(v, pkg)
    found = only(report, "parse-error")[0]
    assert found["severity"] == "error" and found["file"] == SLEEP
    assert found["line"] == 3 and found["column"] == 11
    assert (found["table"], found["topic"]) == ("sleep_diary", "sleep")
    assert "unresolved-ref" in codes_of(report)          # the mother's $ref to it
    summary = v.summary_report(v.analyze(pkg))
    assert summary["ok"] is False and "skipped" in summary["fixtures"]
    assert "toy data not checked until the schema errors are fixed" in summary["headline"]


def test_non_utf8_and_nan_schema_files(v, pkg):
    (pkg / "schemas" / PARTICIPANT).write_bytes(b'{"title": "Caf\xe9"}')
    (pkg / "schemas" / "common" / "extra.json").write_text('{"$defs": {"x": {"const": NaN}}}',
                                                          encoding="utf-8")
    report = check(v, pkg)
    found = {f["file"]: f["message"] for f in only(report, "parse-error")}
    assert "UTF-8" in found[PARTICIPANT]
    assert "NaN" in found["common/extra.json"]


def test_meta_invalid_and_wrong_draft(v, pkg):
    edit(pkg, SLEEP, lambda d: d["properties"]["nap_minutes"]["anyOf"][0].update(minimum="0"))
    edit(pkg, PARTICIPANT, lambda d: d.update({"$schema": "http://json-schema.org/draft-07/schema#"}))
    report = check(v, pkg)
    meta = only(report, "meta-invalid")
    assert meta[0]["file"] == SLEEP and meta[0]["pointer"] == "/properties/nap_minutes/anyOf/0/minimum"
    assert (meta[0]["table"], meta[0]["topic"], meta[0]["variable"]) == (
        "sleep_diary", "sleep", "nap_minutes")
    assert only(report, "wrong-draft")[0]["file"] == PARTICIPANT
    assert report["ok"] is False
    fixtures = v.fixtures_report(v.analyze(pkg))
    assert only(fixtures, "schema-errors") and fixtures["ok"] is False


def test_id_policy(v, pkg):
    edit(pkg, DEFS, lambda d: d.pop("$id"))
    edit(pkg, PARTICIPANT, lambda d: d.update({"$id": "https://other.example.org/x/" + PARTICIPANT}))
    edit(pkg, SLEEP, lambda d: d.update({"$id": BASE + "sleep_diary/sleep.json"}))
    report = check(v, pkg)
    assert only(report, "id-missing")[0]["severity"] == "warning"
    assert only(report, "mixed-id-bases")[0]["file"] == PARTICIPANT
    assert only(report, "id-path-mismatch")[0]["file"] == SLEEP
    # The participant file still resolves under its own base (cross-registration);
    # sleep.json's mis-mirrored $id breaks its own relative refs.
    assert all(f["file"] == SLEEP for f in only(report, "unresolved-ref"))


def test_duplicate_id(v, pkg):
    edit(pkg, SLEEP, lambda d: d.update({"$id": BASE + PARTICIPANT}))
    found = only(check(v, pkg), "duplicate-id")[0]
    assert found["severity"] == "error" and found["file"] == SLEEP


def test_mixed_bases_still_validate(v, pkg):
    edit(pkg, PARTICIPANT, lambda d: d.update({"$id": "https://other.example.org/x/" + PARTICIPANT}))
    report = check(v, pkg)
    assert report["ok"] is True and codes_of(report) == ["mixed-id-bases"]
    assert v.fixtures_report(v.analyze(pkg))["ok"] is True


def test_refs_resolve_through_referencing(v, pkg):
    def change(d):
        d["$defs"]["dont know"] = {"const": -888, "title": "Don't know", "x-value-kind": "sentinel",
                                   "x-provenance": prov(2), "$anchor": "dk"}
    edit(pkg, DEFS, change)

    def refs(d):
        props = d["properties"]
        props["age"]["anyOf"][1] = {"$ref": "../../common/defs.json#dk"}
        props["chronotype"]["oneOf"][3] = {"$ref": "../../common/defs.json#/$defs/dont%20know"}
        props["site_id"]["$comment"] = "codes as listed"
        props["site_id"]["x-provenance"]["value:\"01\""] = "S01:Codes row 1"
    edit(pkg, PARTICIPANT, refs)
    report = check(v, pkg)
    assert "unresolved-ref" not in codes_of(report)
    assert codes_of(report) == ["discouraged-keyword"]          # the $anchor itself


def test_odd_refs_are_reported_not_raised(v, pkg):
    def change(d):
        props = d["properties"]
        props["sleep_minutes"]["anyOf"].append({"$ref": "#/$defs/missing"})
        props["nap_minutes"]["anyOf"].append({"$ref": "https://example.com/elsewhere.json"})
        props["caffeine"]["not"] = {"$ref": "#"}
        props["nap_yesterday"]["default"] = {"$ref": "#/also/missing"}   # a value, not a schema
        props["nap_yesterday"]["oneOf"][0]["enum"] = [{"$ref": "nope"}]
    edit(pkg, SLEEP, change)
    report = check(v, pkg)
    unresolved = sorted(f["pointer"] for f in only(report, "unresolved-ref"))
    assert unresolved == ["/properties/nap_minutes/anyOf/3/$ref",
                          "/properties/sleep_minutes/anyOf/3/$ref"]


def test_not_a_schema_warning(v, pkg):
    write_json(pkg / "schemas" / "sleep_diary" / "notes.json", {"hello": 1})
    write_json(pkg / "schemas" / "common" / "list.json", [1, 2])
    report = check(v, pkg)
    assert sorted(f["file"] for f in only(report, "not-a-schema")) == [
        "common/list.json", "sleep_diary/notes.json"]
    assert report["ok"] is True


def test_layout_codes(v, pkg):
    save(pkg, "sleep_diary/extra.schema.json", mother_doc())
    save(pkg, "sleep_diary/categories/diet.json", {
        "$schema": DRAFT, "$id": BASE + "sleep_diary/categories/diet.json", "title": "Diet",
        "type": "object", "x-variable-group": "diet", "properties": {}, "required": []})
    report = check(v, pkg)
    layout = only(report, "table-layout")[0]
    assert layout["severity"] == "error" and "sleep_diary/extra.schema.json" in layout["message"]
    assert report["tables"][0]["mother"] == MOTHER
    orphan = only(report, "orphan-category")[0]
    assert orphan["severity"] == "warning" and orphan["file"] == "sleep_diary/categories/diet.json"


def test_no_tables(v, tmp_path):
    write_json(tmp_path / "empty" / "schemas" / DEFS, defs_doc())
    report = check(v, tmp_path / "empty")
    assert report["ok"] is False and codes_of(report, "error") == ["no-tables"]


# ------------------------------------------------------------- house style


def test_mother_shape(v, pkg):
    def change(d):
        d["type"] = "object"
        d["items"]["properties"] = {}
        d["items"].pop("unevaluatedProperties")
        d.pop("minItems")
        d.pop("description")
    edit(pkg, MOTHER, change)
    report = check(v, pkg)
    pointers = sorted(f["pointer"] for f in only(report, "mother-shape"))
    assert pointers == ["/items/properties", "/items/unevaluatedProperties", "/type"]
    assert only(report, "mother-min-items")[0]["severity"] == "warning"
    assert "description" in only(report, "mother-annotations")[0]["message"]


def test_allof_order_and_entry(v, pkg):
    def change(d):
        entries = allof(d)
        entries.append(entries.pop(1))                     # a category after the rules
        entries.append({"properties": {"x": {"type": "string"}}})
    edit(pkg, MOTHER, change)
    report = check(v, pkg)
    assert only(report, "allof-order")[0]["pointer"] == "/items/allOf/3"
    assert only(report, "allof-entry")[0]["pointer"] == "/items/allOf/4"


def test_category_shape_required_and_group(v, pkg):
    def change(d):
        d["additionalProperties"] = False
        d["required"].remove("caffeine")
        d.pop("x-variable-group")
    edit(pkg, SLEEP, change)
    report = check(v, pkg)
    assert only(report, "category-shape")[0]["pointer"] == "/additionalProperties"
    assert "caffeine" in only(report, "required-incomplete")[0]["message"]
    assert only(report, "missing-group")[0]["severity"] == "warning"


def test_property_needs_title_and_provenance(v, pkg):
    def change(d):
        d["properties"]["caffeine"].pop("title")
        d["properties"]["nap_yesterday"].pop("x-provenance")
    edit(pkg, SLEEP, change)
    report = check(v, pkg)
    title = only(report, "missing-title")[0]
    assert (title["variable"], title["topic"], title["table"]) == ("caffeine", "sleep",
                                                                   "sleep_diary")
    missing = only(report, "missing-provenance")[0]
    assert missing["severity"] == "error" and missing["variable"] == "nap_yesterday"


def test_definition_provenance(v, pkg):
    edit(pkg, DEFS, lambda d: d["$defs"]["dont_know"].pop("x-provenance"))
    found = only(check(v, pkg), "missing-provenance")[0]
    assert found["severity"] == "error" and found["pointer"] == "/$defs/dont_know"


def test_definition_provenance_carried_by_every_use_is_a_warning(v, pkg):
    # participant_id's one use is a property that carries its own x-provenance.
    edit(pkg, DEFS, lambda d: d["$defs"]["participant_id"].pop("x-provenance"))
    found = only(check(v, pkg), "missing-provenance")[0]
    assert found["severity"] == "warning" and found["pointer"] == "/$defs/participant_id"


def test_code_titles_and_value_kinds(v, pkg):
    def change(d):
        d["properties"]["caffeine"]["oneOf"][1].pop("title")
        d["properties"]["caffeine"]["oneOf"].append({"const": 9, "title": "Don't know"})
        d["properties"]["nap_yesterday"]["oneOf"][0]["title"] = "No " + "x" * 70
        d["properties"]["nap_yesterday"]["oneOf"].append({"const": -1, "title": "Refused"})
    edit(pkg, SLEEP, change)
    edit(pkg, DEFS, lambda d: d["$defs"]["not_applicable"].pop("x-value-kind"))
    report = check(v, pkg)
    assert only(report, "code-without-title")[0]["pointer"] == "/properties/caffeine/oneOf/1"
    assert only(report, "title-too-long")[0]["severity"] == "warning"
    ambiguous = sorted(f["pointer"] for f in only(report, "value-kind-ambiguous"))
    assert ambiguous == ["/properties/caffeine/oneOf/2", "/properties/nap_yesterday/oneOf/3"]
    kind = only(report, "sentinel-kind-missing")
    assert len(kind) == 1 and kind[0]["file"] == DEFS          # reported once, at the definition
    assert kind[0]["pointer"] == "/$defs/not_applicable"


def test_value_kind_value_silences_ambiguity(v, pkg):
    edit(pkg, SLEEP, lambda d: d["properties"]["caffeine"]["oneOf"].append(
        {"const": 999, "title": "Other", "x-value-kind": "value"}))
    assert "value-kind-ambiguous" not in codes_of(check(v, pkg))


def test_guard_missing(v, pkg):
    def change(d):
        d["properties"]["sleep_minutes"]["anyOf"].append(
            {"const": 888, "title": "Not recorded", "x-value-kind": "sentinel"})
        d["properties"]["sleep_minutes"]["anyOf"][0]["maximum"] = 2000
    edit(pkg, SLEEP, change)
    found = only(check(v, pkg), "guard-missing")[0]
    assert found["pointer"] == "/properties/sleep_minutes/anyOf/0" and "888" in found["message"]
    edit(pkg, SLEEP, lambda d: d["properties"]["sleep_minutes"]["anyOf"][0].update(
        {"not": {"enum": [888]}}))
    assert "guard-missing" not in codes_of(check(v, pkg))


def test_bare_enum_x_keywords_and_value_kind(v, pkg):
    def change(d):
        d["properties"]["caffeine"] = {"title": "Caffeine", "x-provenance": prov(10),
                                       "enum": [0, 1], "x-note": "free text"}
        d["properties"]["nap_yesterday"]["oneOf"][1]["x-value-kind"] = "maybe"
    edit(pkg, SLEEP, change)
    report = check(v, pkg)
    assert only(report, "bare-enum")[0]["severity"] == "warning"
    assert only(report, "unknown-x-keyword")[0]["pointer"] == "/properties/caffeine/x-note"
    assert only(report, "bad-value-kind")[0]["severity"] == "error"


def test_discouraged_and_forbidden_keywords(v, pkg):
    def change(d):
        d["properties"]["caffeine"]["format"] = "int32"
        d["properties"]["caffeine"]["oneOf"].append({"type": "null", "title": "Blank"})
        d["properties"]["nap_minutes"]["dependentRequired"] = {"a": ["b"]}
    edit(pkg, SLEEP, change)
    report = check(v, pkg)
    assert sorted(f["pointer"] for f in only(report, "discouraged-keyword")) == [
        "/properties/caffeine/format", "/properties/caffeine/oneOf/2/type"]
    assert only(report, "forbidden-keyword")[0]["severity"] == "error"


def test_conditional_outside_mother(v, pkg):
    edit(pkg, SLEEP, lambda d: d["properties"]["nap_minutes"].update(
        {"if": {"const": 0}, "then": {"const": 0}}))
    found = only(check(v, pkg), "conditional-outside-mother")[0]
    assert found["pointer"] == "/properties/nap_minutes/if" and found["variable"] == "nap_minutes"


def test_rule_in_category_is_rejected_once(v, pkg):
    edit(pkg, SLEEP, lambda d: d.update(copy.deepcopy({k: SKIP[k] for k in ("if", "then")})))
    report = check(v, pkg)
    shape = sorted(f["pointer"] for f in only(report, "category-shape"))
    assert shape == ["/if", "/then"]
    assert "conditional-outside-mother" not in codes_of(report)


# ------------------------------------------------------------ x-provenance


def test_provenance_shape_and_grammar(v, pkg):
    def change(d):
        p = d["properties"]
        p["caffeine"]["x-provenance"] = "S01"
        p["nap_yesterday"]["x-provenance"] = {"default": "S1:row 8", "colour": "S01",
                                              "title": [], "value:01": "S01"}
        p["sleep_minutes"]["x-provenance"]["value:9"] = "S01:Codes row 2"
        p["nap_minutes"]["x-provenance"] = {}
    edit(pkg, SLEEP, change)
    report = check(v, pkg)
    shapes = sorted(f["pointer"] for f in only(report, "provenance-shape"))
    assert shapes == ["/properties/caffeine/x-provenance",
                      "/properties/nap_minutes/x-provenance",
                      "/properties/nap_yesterday/x-provenance/colour",
                      "/properties/nap_yesterday/x-provenance/default",
                      "/properties/nap_yesterday/x-provenance/title",
                      "/properties/nap_yesterday/x-provenance/value:01"]
    unknown = only(report, "provenance-unknown-code")[0]
    assert unknown["severity"] == "warning" and unknown["variable"] == "sleep_minutes"
    edit(pkg, SLEEP, lambda d: d["properties"]["sleep_minutes"]["x-provenance"].update(
        {"value:-888": ["S01:Codes row 2", "S03:§Missing"]}))
    assert len(only(check(v, pkg), "provenance-unknown-code")) == 1


def test_provenance_resolution(v, pkg):
    def change(d):
        p = d["properties"]
        p["caffeine"]["x-provenance"] = {"default": "S09:row 10"}
        p["nap_yesterday"]["x-provenance"] = {"default": "S02:about"}
        p["sleep_minutes"]["x-provenance"]["maximum"] = "D004"
        p["nap_minutes"]["x-provenance"]["maximum"] = "D005"
    edit(pkg, SLEEP, change)
    report = check(v, pkg)
    assert "S09" in only(report, "provenance-unresolved")[0]["message"]
    uncitable = sorted(f["message"] for f in only(report, "provenance-uncitable"))
    assert any('"suggested"' in m for m in uncitable) and any("cancelled" in m for m in uncitable)
    assert only(report, "provenance-superseded")[0]["severity"] == "warning"
    summary = v.summary_report(v.analyze(pkg))
    assert summary["topics"]["sleep_diary/sleep"]["provenance_ok"] is False
    assert summary["provenance"]["traced"] == 5


def test_missing_provenance_json_is_one_info(v, pkg):
    (pkg / "provenance.json").unlink()
    report = check(v, pkg)
    assert report["ok"] is True and codes_of(report) == ["provenance-unchecked"]
    assert report["findings"][0]["severity"] == "info"
    census = v.summary_report(v.analyze(pkg))["provenance"]
    assert census["by_origin"]["unknown"] == 16 and census["needs_review"] == []


def test_broken_provenance_json(v, pkg):
    write_json(pkg / "provenance.json", {"schemifyProvenance": 2, "sources": []})
    assert "provenance-file" in codes_of(check(v, pkg))


# ------------------------------------------------------------ rule grammar


def test_every_test_form_parses(v, pkg):
    add_rule(pkg, rule(
        "Sleep routing R002: late sleepers with caffeine report sleep.",
        {"anyOf": [clause(chronotype={"enum": [1, 2]}, caffeine={"not": {"const": 0}}),
                   clause(site_id={"not": {"enum": ["04", "05"]}},
                          age={"type": "integer", "minimum": 18, "exclusiveMaximum": 30,
                               "not": {"enum": [-888]}}),
                   clause(nap_yesterday={"const": 1})]},
        {"properties": {"sleep_minutes": {"not": {"const": -666}}}}))
    report = v.rules_report(v.analyze(pkg))
    assert report["ok"] is True
    routing = report["rules"][2]
    assert (routing["id"], routing["kind"], routing["domain"]) == ("R002", "routing", "Sleep")
    assert routing["when"] == {"any": [
        {"all": [{"variable": "chronotype", "test": "in", "values": [1, 2]},
                 {"variable": "caffeine", "test": "ne", "value": 0}]},
        {"all": [{"variable": "site_id", "test": "nin", "values": ["04", "05"]},
                 {"variable": "age", "test": "range", "type": "integer", "minimum": 18,
                  "exclusiveMaximum": 30, "excludes": [-888]}]},
        {"all": [{"variable": "nap_yesterday", "test": "eq", "value": 1}]}]}


def test_every_effect_form_parses(v, pkg):
    add_rule(pkg, rule(
        "Nap routing R003: a nap means a short nap or a missing code.",
        clause(nap_yesterday={"const": 1}),
        {"properties": {
            "nap_minutes": {"anyOf": [{"type": "integer", "minimum": 1, "maximum": 240},
                                      {"$ref": "../common/defs.json#/$defs/dont_know"},
                                      {"const": -666}]},
            "chronotype": {"enum": [1, 2, -888]},
            "caffeine": {"const": 1}}}))
    add_rule(pkg, rule(
        "Sleep routing R004: caffeine means some sleep or a nap is reported.",
        clause(caffeine={"const": 1}),
        {"anyOf": [{"required": ["sleep_minutes"], "properties": {
                       "sleep_minutes": {"not": {"const": -666}}}},
                   {"required": ["nap_minutes"], "properties": {
                       "nap_minutes": {"not": {"const": -666}}}}]}))
    report = v.rules_report(v.analyze(pkg))
    assert report["ok"] is True
    r3, r4 = report["rules"][2:]
    assert r3["then"] == {"mode": "all", "effects": [
        {"variable": "nap_minutes", "effect": "range", "type": "integer", "minimum": 1,
         "maximum": 240, "excludes": [], "also": [-888, -666]},
        {"variable": "chronotype", "effect": "in", "values": [1, 2, -888]},
        {"variable": "caffeine", "effect": "eq", "value": 1}]}
    assert r4["then"]["mode"] == "any"
    assert [e["variable"] for e in r4["then"]["effects"]] == ["sleep_minutes", "nap_minutes"]


@pytest.mark.parametrize("change, pointer", [
    (lambda r: r.update(**{"else": {"properties": {"nap_minutes": {"const": 0}}}}),
     "/items/allOf/2"),
    (lambda r: r.pop("x-provenance"), "/items/allOf/2"),
    (lambda r: r.update(then={"if": clause(caffeine={"const": 1}),
                              "then": {"properties": {"nap_minutes": {"const": -666}}}}),
     "/items/allOf/2/then"),
    (lambda r: r.update(then={"allOf": [{"properties": {"nap_minutes": {"const": -666}}}]}),
     "/items/allOf/2/then"),
    (lambda r: r.update(**{"if": {"allOf": [clause(nap_yesterday={"const": 0})]}}),
     "/items/allOf/2/if"),
    (lambda r: r["then"]["properties"].update(nap_minutes={"$ref": "../common/defs.json#/$defs/"
                                                                   "not_applicable"}),
     "/items/allOf/2/then/properties/nap_minutes"),
    (lambda r: r["if"]["properties"].update(nap_yesterday={"enum": [0]}),
     "/items/allOf/2/if/properties/nap_yesterday"),
    (lambda r: r["if"]["properties"].update(nap_yesterday={"type": "integer"}),
     "/items/allOf/2/if/properties/nap_yesterday"),
])
def test_rule_shape_rejections(v, pkg, change, pointer):
    edit(pkg, MOTHER, lambda d: change(allof(d)[2]))
    report = check(v, pkg)
    shape = only(report, "rule-shape")
    assert shape[0]["pointer"] == pointer and shape[0]["rule"] == "R001"
    assert "forbidden-keyword" not in codes_of(report)
    assert "conditional-outside-mother" not in codes_of(report)
    rules = v.rules_report(v.analyze(pkg))
    assert [r["kind"] for r in rules["rules"]] == ["applicability"]
    assert "rule-shape" in codes_of(rules) and rules["ok"] is False


def test_rule_comment_and_unguarded(v, pkg):
    def change(d):
        allof(d)[2]["$comment"] = "Skip R001: no nap"
        allof(d)[3]["if"] = {"required": ["caffeine"],
                             "properties": {"nap_yesterday": {"const": 1}}}
    edit(pkg, MOTHER, change)
    report = check(v, pkg)
    assert only(report, "rule-comment")[0]["pointer"] == "/items/allOf/2/$comment"
    unguarded = only(report, "rule-unguarded")[0]
    assert unguarded["pointer"] == "/items/allOf/3/if" and unguarded["rule"] == "R001"
    assert "missing-twin" in codes_of(report)         # the skip half no longer has an id


def test_rule_dangling_undeclared_code_and_trigger_level(v, pkg):
    def change(d):
        allof(d)[2]["if"] = clause(nap_yesterdy={"const": 0})
        allof(d)[3]["if"]["properties"]["nap_yesterday"] = {"const": 5}
    edit(pkg, MOTHER, change)
    add_rule(pkg, rule("Nap routing R005: a nap of unknown length.",
                       clause(nap_yesterday={"const": -888}),
                       {"properties": {"nap_minutes": {"const": -999}}}))
    report = check(v, pkg)
    dangling = only(report, "rule-dangling")[0]
    assert dangling["variable"] == "nap_yesterdy" and dangling["severity"] == "error"
    assert dangling["pointer"] == "/items/allOf/2/if/properties/nap_yesterdy"
    level = only(report, "trigger-undeclared-level")[0]
    assert level["severity"] == "warning"
    assert level["pointer"] == "/items/allOf/3/if/properties/nap_yesterday"
    undeclared = only(report, "rule-undeclared-code")[0]
    assert undeclared["rule"] == "R005" and "-999" in undeclared["message"]


def test_range_trigger_sentinel(v, pkg):
    test = {"type": "integer", "maximum": 300}
    add_rule(pkg, rule("Sleep routing R006: short sleepers report caffeine.",
                       clause(sleep_minutes=test),
                       {"properties": {"caffeine": {"const": 1}}}))
    found = only(check(v, pkg), "range-trigger-sentinel")[0]
    assert "-666" in found["message"] and "-888" in found["message"]
    edit(pkg, MOTHER, lambda d: allof(d)[4]["if"]["properties"]["sleep_minutes"].update(
        {"not": {"enum": [-666, -888]}}))
    assert "range-trigger-sentinel" not in codes_of(check(v, pkg))


def test_kind_consistency(v, pkg):
    def change(d):
        allof(d)[2]["then"]["properties"]["nap_minutes"] = {"const": 0}
        allof(d)[3]["then"]["properties"]["nap_minutes"] = {"const": 30}
    edit(pkg, MOTHER, change)
    report = check(v, pkg)
    assert "x-value-kind" in only(report, "skip-shape")[0]["message"]
    applicability = only(report, "applicability-shape")[0]
    assert applicability["pointer"] == "/items/allOf/3/then/properties/nap_minutes"
    assert applicability["topic"] == "sleep"          # rule findings count toward their topic
    topics = v.summary_report(v.analyze(pkg))["topics"]
    assert topics["sleep_diary/sleep"]["errors"] >= 2
    edit(pkg, MOTHER, lambda d: allof(d)[2]["then"]["properties"].update(
        nap_minutes={"not": {"const": -666}}))
    assert "not a const pin" in only(check(v, pkg), "skip-shape")[0]["message"]


def test_missing_twin_and_duplicate_rule(v, pkg):
    edit(pkg, MOTHER, lambda d: allof(d).pop(3))
    twin = only(check(v, pkg), "missing-twin")[0]
    assert twin["severity"] == "warning" and twin["rule"] == "R001"
    add_rule(pkg, copy.deepcopy(SKIP))
    duplicate = only(check(v, pkg), "duplicate-rule")[0]
    assert duplicate["severity"] == "error" and duplicate["pointer"] == "/items/allOf/3"


# ---------------------------------------------------------------- fixtures


def verdicts(v, pkg):
    report = v.fixtures_report(v.analyze(pkg))
    return report, {x["row"]: x for x in report["tables"]["sleep_diary"]["invalid"]["verdicts"]}


def test_caught_with_extra(v, pkg):
    edit_toy(pkg, "invalid.json", lambda rows: rows[4].update(chronotype=7))
    report, by_row = verdicts(v, pkg)
    assert by_row[4]["status"] == "caught-with-extra"
    assert by_row[4]["failed_on"] == ["age", "chronotype"]
    assert only(report, "caught-with-extra")[0]["severity"] == "error" and report["ok"] is False


def test_missed_wrong_column_and_missed_passed(v, pkg):
    def change(ledger):
        ledger["violations"][5]["column"] = "age"
    edit_toy(pkg, "invalid-ledger.json", change)
    edit_toy(pkg, "invalid.json", lambda rows: rows[8].update(chronotype=3))
    report, by_row = verdicts(v, pkg)
    assert by_row[5]["status"] == "missed-wrong-column"
    assert by_row[5]["failed_on"] == ["sleep_minutes"]
    assert by_row[8]["status"] == "missed-passed"
    assert report["tables"]["sleep_diary"]["invalid"]["caught"] == 7


def test_phantom_and_unledgered(v, pkg):
    def change(ledger):
        ledger["violations"][2]["row"] = 99
        ledger["violations"][3]["row"] = "3"
    edit_toy(pkg, "invalid-ledger.json", change)
    report, _ = verdicts(v, pkg)
    table = report["tables"]["sleep_diary"]["invalid"]
    assert [x["status"] for x in table["verdicts"][2:4]] == ["phantom", "phantom"]
    assert table["unledgered"] == [2, 3]
    assert len(only(report, "unledgered")) == 2 and len(only(report, "phantom")) == 2


def test_unknown_ledger_kind_is_a_warning(v, pkg):
    edit_toy(pkg, "invalid-ledger.json", lambda l: l["violations"][0].update(kind="skip-brake"))
    report = v.fixtures_report(v.analyze(pkg))
    assert only(report, "unknown-kind")[0]["severity"] == "warning" and report["ok"] is True


def test_valid_fails_names_the_row(v, pkg):
    edit_toy(pkg, "valid.json", lambda rows: rows[3].update(age=17))
    report = v.fixtures_report(v.analyze(pkg))
    fails = only(report, "valid-fails")[0]
    assert fails["row"] == 3 and fails["variable"] == "age" and fails["topic"] == "participant"
    assert fails["findings"][0]["column"] == "age"
    assert report["tables"]["sleep_diary"]["valid"]["status"] == "fail"
    headline = v.summary_report(v.analyze(pkg))["headline"]
    assert "toy data: 9/10 valid rows pass, 9/9 seeded errors caught" in headline


def test_rule_attribution_through_effect_anyof_ref(v, pkg):
    add_rule(pkg, rule(
        "Nap routing R007: a long sleeper's nap is short or unknown.",
        clause(sleep_minutes={"type": "integer", "minimum": 600, "maximum": 960}),
        {"properties": {"nap_minutes": {"anyOf": [
            {"type": "integer", "minimum": 0, "maximum": 60},
            {"$ref": "../common/defs.json#/$defs/dont_know"},
            {"$ref": "../common/defs.json#/$defs/not_applicable"}]}}}))
    bad = row(40, "01", 30, 1, 700, 1, 90, 0)
    edit_toy(pkg, "invalid.json", lambda rows: rows.append(bad))
    edit_toy(pkg, "invalid-ledger.json", lambda l: l["violations"].append(
        {"row": 9, "column": "nap_minutes", "kind": "routing-break", "reason": "R007"}))
    report, by_row = verdicts(v, pkg)
    assert by_row[9]["status"] == "caught" and by_row[9]["rules"] == ["R007"]
    an = v.analyze(pkg)
    found = v.RowChecker(an, an.tables["sleep_diary"]).check_row(bad, 0)
    assert [(f["column"], f["rule"], f["allof_index"]) for f in found] == [
        ("nap_minutes", "R007", 4)]
    assert "R007:routing" in report["tables"]["sleep_diary"]["coverage"]["rules"]["caught"]


def test_coverage_gaps_are_warnings(v, pkg):
    edit_toy(pkg, "valid.json", lambda rows: rows[1].update(sleep_minutes=950, nap_yesterday=0,
                                                            nap_minutes=-666))
    edit_toy(pkg, "valid.json", lambda rows: [r.update(nap_yesterday=0, nap_minutes=-666)
                                              for r in rows if r["nap_yesterday"] == 1])
    report = v.fixtures_report(v.analyze(pkg))
    assert report["ok"] is True
    gaps = only(report, "coverage-gap")
    assert any(g.get("variable") == "sleep_minutes" and "960" in g["message"] for g in gaps)
    rules = report["tables"]["sleep_diary"]["coverage"]["rules"]
    assert rules["unfired"] == ["R001:applicability"] and rules["fired"] == ["R001:skip"]
    assert report["tables"]["sleep_diary"]["coverage"]["properties"]["covered"] < 7


def test_no_toy_data_is_skipped_but_not_ok(v, pkg):
    import shutil
    shutil.rmtree(str(pkg / "toy-data"))
    report = v.fixtures_report(v.analyze(pkg))
    assert report["tables"]["sleep_diary"] == {"skipped": "no toy-data/sleep_diary/ folder yet"}
    assert only(report, "fixtures-skipped")[0]["severity"] == "info"
    assert report["ok"] is False and "no-fixtures" in codes_of(report)
    assert "no toy data yet" in v.summary_report(v.analyze(pkg))["headline"]


def test_missing_and_misshapen_fixture_files(v, pkg):
    write_json(toy(pkg, "valid.json"), {"rows": VALID})
    report = v.fixtures_report(v.analyze(pkg))
    assert only(report, "fixture-shape")[0]["file"] == "../toy-data/sleep_diary/valid.json"
    assert set(report["tables"]["sleep_diary"]) == {"invalid"}       # no coverage without rows
    assert "coverage-gap" not in codes_of(report)
    summary = v.summary_report(v.analyze(pkg))
    assert summary["ok"] is False
    assert "toy data: valid.json unreadable, 9/9 seeded errors caught" in summary["headline"]
    toy(pkg, "invalid-ledger.json").unlink()
    report = v.fixtures_report(v.analyze(pkg))
    assert only(report, "fixture-missing")[0]["file"] == (
        "../toy-data/sleep_diary/invalid-ledger.json")
    assert report["ok"] is False
    assert report["tables"]["sleep_diary"] == {"error": "no readable toy data (see findings)"}
    assert "no toy data yet" in v.summary_report(v.analyze(pkg))["headline"]


def test_duplicate_row_case(v, pkg):
    edit(pkg, MOTHER, lambda d: d.update(uniqueItems=True))
    clean = row(50, "01", 30, 1, 400, 1, 30, 0)
    edit_toy(pkg, "invalid.json", lambda rows: rows.extend([clean, dict(clean)]))
    edit_toy(pkg, "invalid-ledger.json", lambda l: l["violations"].append(
        {"row": 10, "column": "*duplicate*", "kind": "duplicate-row", "reason": "row 9 again"}))
    report, by_row = verdicts(v, pkg)
    assert by_row[10]["status"] == "caught" and report["ok"] is True


# -------------------------------------------------------------------- data


def data(v, pkg, path, **kw):
    return v.data_report(v.analyze(pkg), path, **kw)


def test_data_json_findings_and_counts(v, pkg, tmp_path):
    rows, _ = invalid_rows()
    path = tmp_path / "data.json"
    write_json(path, VALID + rows)
    report = data(v, pkg, path)
    assert report["ok"] is False and report["rows"] == 19 and report["format"] == "json"
    assert report["errors"] == len(report["findings"]) == 9
    assert [(f["row"], f["column"]) for f in report["findings"]] == [
        (10, "nap_minutes"), (11, "nap_minutes"), (12, "mood"), (13, "caffeine"), (14, "age"),
        (15, "sleep_minutes"), (16, "nap_minutes"), (17, "participant_id"), (18, "chronotype")]
    assert report["by_rule"] == {"R001": 2}
    assert report["by_column"]["nap_minutes"] == 3
    first = report["findings"][0]
    assert first["rule"] == "R001" and first["allof_index"] == 2
    assert first["hint"].startswith("R001 (Skip pattern) applies to this row")
    assert "Allowed in sleep_minutes" in report["findings"][5]["hint"]
    assert list(report["columns"]) == COLUMNS
    assert report["columns"]["age"] == {"title": "Age (years)", "topic": "participant",
                                        "allowed": "a whole number from 18 to 90, or -888 "
                                                   "(Don't know)"}


def test_data_collateral_unevaluated_is_filtered(v, pkg, tmp_path):
    bad = dict(VALID[0], age=12, extra_col="x")
    path = tmp_path / "data.json"
    write_json(path, [bad])
    report = data(v, pkg, path)
    assert sorted((f["column"], f["keyword"]) for f in report["findings"]) == [
        ("age", "anyOf"), ("extra_col", "unevaluatedProperties")]


def test_read_text_cell_mirrors_quac(v):
    read = v.read_text_cell
    integer, number = {"integer"}, {"number"}
    assert read("42", integer) == 42 and type(read("42", integer)) is int
    assert read("2.0", integer) == 2 and type(read("2.0", integer)) is int
    assert type(read("2.0", number)) is float
    assert read("1e2", integer) == 100
    assert read(" 42 ", integer) == 42
    for text in ("007", "+5", ".5", "1,000", "nan", "NaN", "inf", "1_0", "1e400", "  "):
        assert read(text, integer) == text
    assert read("2.5", {"integer", "string"}) == "2.5"
    assert read("2.5", integer) == 2.5
    assert read("01", {"string"}) == "01"
    assert read("TRUE", {"boolean"}) is True and read("true", {"string"}) == "true"
    assert read("[1, 2]", {"array"}) == [1, 2] and read("[1, 2]", {"string"}) == "[1, 2]"
    assert read('{"a": 1}', None) == {"a": 1} and read("42", None) == 42
    assert read("abc", None) == "abc"


def test_data_csv_typing(v, pkg, tmp_path):
    rows = [dict(r) for r in VALID[:3]]
    rows[1]["age"] = "2.0e1"                      # 20.0 -> the int 20
    rows[2]["sleep_minutes"] = "nan"              # text: an error
    rows[0]["caffeine"] = ""                      # empty cell: the key is absent
    path = write_csv(tmp_path / "data.csv", rows)
    report = data(v, pkg, path)
    assert report["format"] == "csv" and report["rows"] == 3
    found = [(f["row"], f["column"], f["keyword"], f.get("empty_cell")) for f in report["findings"]]
    assert found == [(0, "caffeine", "required", True), (2, "sleep_minutes", "anyOf", None)]
    assert "missing-value code" in report["findings"][0]["hint"] or (
        "no missing-value code" in report["findings"][0]["hint"])
    assert "-666 (Not applicable" in report["findings"][1]["hint"]
    an = v.analyze(pkg)
    checker = v.RowChecker(an, an.tables["sleep_diary"])
    parsed, _, _ = v.read_delimited(path, ",", checker)
    assert parsed[0]["site_id"] == "01" and parsed[1]["age"] == 20
    assert parsed[0]["participant_id"] == "P0001" and "caffeine" not in parsed[0]


def test_data_csv_string_codes_and_ref_typed_columns(v, pkg, tmp_path):
    def change(d):
        d["$defs"]["count"] = {"type": "integer", "minimum": 0, "maximum": 20,
                               "x-provenance": prov(11)}
    edit(pkg, DEFS, change)
    edit(pkg, SLEEP, lambda d: d["properties"].update(caffeine={
        "title": "Caffeine drinks", "x-provenance": prov(10),
        "$ref": "../../common/defs.json#/$defs/count"}))
    rows = [dict(VALID[0], caffeine=3, site_id="007")]
    path = write_csv(tmp_path / "data.csv", rows)
    report = data(v, pkg, path)
    assert [(f["column"], f["keyword"]) for f in report["findings"]] == [("site_id", "oneOf")]


def test_data_tsv_uses_tabs(v, pkg, tmp_path):
    path = write_csv(tmp_path / "data.tsv", VALID, delimiter="\t")
    report = data(v, pkg, path)
    assert report["ok"] is True and report["format"] == "tsv" and report["rows"] == 10


def test_data_semicolon_csv_is_refused_with_a_hint(v, pkg, tmp_path, monkeypatch, capsys):
    path = write_csv(tmp_path / "data.csv", VALID, delimiter=";")
    code, out = run_main(v, monkeypatch, capsys, "data", pkg, "--file", path)
    assert code == 2 and out["ok"] is False
    assert "semicolon" in out["error"] and "comma" in out["hint"]


def test_data_nan_in_json_is_one_finding(v, pkg, tmp_path):
    text = json.dumps([VALID[0], VALID[1]]).replace('"age": 90', '"age": NaN', 1)
    path = tmp_path / "data.json"
    path.write_text(text, encoding="utf-8")
    report = data(v, pkg, path)
    assert [(f["row"], f["column"], f["keyword"]) for f in report["findings"]] == [
        (1, "age", "non-finite")]
    assert "NaN" in report["findings"][0]["message"]


def test_data_duplicates_are_linear(v, pkg, tmp_path):
    edit(pkg, MOTHER, lambda d: d.update(uniqueItems=True))
    rows = [dict(VALID[i % 10], participant_id="P{:04d}".format(i % 10000),
                 sleep_minutes=i % 900) for i in range(20000)]
    rows[19999] = dict(rows[5])
    rows[19998] = dict(rows[6], sleep_minutes=float(rows[6]["sleep_minutes"]))  # 1.0 == 1
    path = tmp_path / "big.json"
    write_json(path, rows)
    started = time.time()
    report = data(v, pkg, path)
    elapsed = time.time() - started
    assert elapsed < 10, "20k rows took {:.1f} s".format(elapsed)
    dupes = [(f["row"], f["column"], f["message"]) for f in report["findings"]
             if f["keyword"] == "uniqueItems"]
    assert dupes == [(19998, None, "Row 19998 repeats row 6 exactly."),
                     (19999, None, "Row 19999 repeats row 5 exactly.")]
    assert report["errors"] == 2 and report["by_column"] == {}


def test_direct_undeclared_check_matches_jsonschema(v, pkg, monkeypatch):
    rows, _ = invalid_rows()
    rows += [dict(VALID[0], age=12, extra="x", other=1), dict(VALID[1], chronotype="2"),
             [1], "row", None, dict(VALID[2], nap_minutes=-666, nap_yesterday=0)]
    an = v.analyze(pkg)
    fast = v.RowChecker(an, an.tables["sleep_diary"])
    assert fast.direct is True
    monkeypatch.setattr(v, "plain_table", lambda an, model: False)
    full = v.RowChecker(an, an.tables["sleep_diary"])
    assert full.direct is False
    assert fast.check_rows(rows) == full.check_rows(rows)


def test_unplain_table_falls_back_to_jsonschema(v, pkg, tmp_path):
    edit(pkg, SLEEP, lambda d: d.update(patternProperties={"^note_": {"type": "string"}}))
    an = v.analyze(pkg)
    checker = v.RowChecker(an, an.tables["sleep_diary"])
    assert checker.direct is False
    found = checker.check_rows([dict(VALID[0], note_1="ok", stray=1)])
    assert [(f["column"], f["keyword"]) for f in found] == [("stray", "unevaluatedProperties")]


def test_data_max_errors_truncates_findings_not_counts(v, pkg, tmp_path):
    path = tmp_path / "data.json"
    write_json(path, [dict(VALID[0], age=5) for _ in range(7)])
    report = data(v, pkg, path, cap=3)
    assert report["errors"] == 7 and len(report["findings"]) == 3 and report["truncated"] is True
    assert report["by_column"] == {"age": 7}


def test_data_min_items(v, pkg, tmp_path):
    path = tmp_path / "data.json"
    write_json(path, [])
    report = data(v, pkg, path)
    assert report["findings"][0]["keyword"] == "minItems" and report["ok"] is False


# ----------------------------------------------------------------- summary


def test_summary_out_writes_full_report_and_prints_compact(v, pkg, tmp_path, monkeypatch, capsys):
    out = tmp_path / "reports" / "full.json"
    edit_toy(pkg, "valid.json", lambda rows: rows[1].update(sleep_minutes=950))   # a coverage gap
    code, printed = run_main(v, monkeypatch, capsys, "summary", pkg, "--out", out)
    assert code == 0
    assert set(printed) == {"ok", "headline", "package", "counts", "findings", "truncated",
                            "topics", "report"}
    assert printed["report"] == str(out) and len(printed["findings"]) <= 20
    full = json.loads(out.read_text(encoding="utf-8"))
    assert full["headline"] == printed["headline"]
    assert len(full["rules"]["items"]) == 2 and "sleep_diary" in full["rules"]["variables"]
    assert full["rules"]["count"] == 2
    verdicts_ = full["fixtures"]["tables"]["sleep_diary"]["invalid"]["verdicts"]
    assert len(verdicts_) == 9
    assert full["check"]["truncated"] is False


def test_summary_caps_findings(v, pkg):
    edit(pkg, SLEEP, lambda d: [p.pop("title") for p in d["properties"].values()])
    report = v.summary_report(v.analyze(pkg), cap=2)
    assert len(report["check"]["findings"]) == 2 and report["check"]["truncated"] is True
    assert report["check"]["counts"]["error"] == 4
    assert report["headline"].startswith("4 schema files: 4 errors to fix")


# -------------------------------------------------------------- multi-table


def add_household(pkg):
    cat = "household/categories/home.json"
    save(pkg, cat, {
        "$schema": DRAFT, "$id": BASE + cat, "title": "Home", "type": "object",
        "x-variable-group": "home",
        "properties": {
            "participant_id": {"title": "Participant identifier", "x-provenance": prov(1),
                               "$ref": "../../common/defs.json#/$defs/participant_id"},
            "pets": {"title": "Pets at home", "x-provenance": prov(20),
                     "oneOf": codes((0, "No"), (1, "Yes")) + [DK]},
            "pet_count": {"title": "Number of pets", "x-provenance": prov(21),
                          "anyOf": [{"type": "integer", "minimum": 1, "maximum": 20}, NA, DK]},
        },
        "required": ["participant_id", "pets", "pet_count"],
    })
    save(pkg, "household/household.schema.json", {
        "$schema": DRAFT, "$id": BASE + "household/household.schema.json",
        "title": "LARK — Household", "description": "One element is one participant.",
        "type": "array", "minItems": 1,
        "items": {"type": "object", "title": "Household record", "allOf": [
            {"$ref": "categories/home.json"},
            rule("Skip pattern R010: no pets means no pet count.",
                 clause(pets={"const": 0}), {"properties": {"pet_count": {"const": -666}}}),
            rule("Applicability R010: pets mean a count or a missing code.",
                 clause(pets={"const": 1}), {"properties": {"pet_count": {"not": {"const": -666}}}}),
        ], "unevaluatedProperties": False},
    })


def test_multi_table_scoping_and_attribution(v, pkg, tmp_path, monkeypatch, capsys):
    add_household(pkg)
    report = check(v, pkg)
    assert report["ok"] is True and [t["table"] for t in report["tables"]] == [
        "household", "sleep_diary"]
    rules = v.rules_report(v.analyze(pkg), "household")
    assert [(r["table"], r["id"], r["pointer"]) for r in rules["rules"]] == [
        ("household", "R010", "/items/allOf/1"), ("household", "R010", "/items/allOf/2")]
    assert list(rules["variables"]) == ["household"]
    fixtures = v.fixtures_report(v.analyze(pkg))
    assert fixtures["tables"]["household"] == {"skipped": "no toy-data/household/ folder yet"}
    assert fixtures["ok"] is True
    path = tmp_path / "home.json"
    write_json(path, [{"participant_id": "P0001", "pets": 0, "pet_count": 2}])
    code, out = run_main(v, monkeypatch, capsys, "data", pkg, "--file", path)
    assert code == 2 and "--table" in out["hint"]
    code, out = run_main(v, monkeypatch, capsys, "data", pkg, "--file", path, "--table",
                         "household")
    assert code == 1 and out["by_rule"] == {"R010": 1}
    assert out["findings"][0]["allof_index"] == 1
    code, out = run_main(v, monkeypatch, capsys, "rules", pkg, "--table", "nope")
    assert code == 2 and "household" in out["error"]


# --------------------------------------------------------------- hardening


@pytest.mark.parametrize("mutate", [
    lambda pkg: edit(pkg, MOTHER, lambda d: d["items"].update(allOf="categories/sleep.json")),
    lambda pkg: edit(pkg, SLEEP, lambda d: d["properties"]["sleep_minutes"]["anyOf"][0].update(
        minimum="0", maximum="960")),
    lambda pkg: edit(pkg, SLEEP, lambda d: d["properties"].update(caffeine="yes")),
    lambda pkg: edit(pkg, MOTHER, lambda d: d.update(items=[1, 2])),
    lambda pkg: edit(pkg, MOTHER, lambda d: allof(d).extend([
        "text", 5, None, {"$ref": "#"}, {"$ref": "#/$defs/missing"},
        {"$ref": "https://example.com/abs.json"}, {"if": "x", "then": 3}])),
    lambda pkg: (pkg / "schemas" / MOTHER).write_text("{not json", encoding="utf-8"),
    lambda pkg: (pkg / "schemas" / SLEEP).write_bytes(b"\xff\xfe\x00junk"),
    lambda pkg: edit(pkg, SLEEP, lambda d: d.update(properties=[1], required="all")),
    lambda pkg: edit(pkg, DEFS, lambda d: d.update({"$defs": {"x": {"not": "y"}}})),
    lambda pkg: write_json(pkg / "toy-data" / "sleep_diary" / "invalid-ledger.json",
                           {"violations": [5, {"row": True, "column": 3}, None]}),
    lambda pkg: write_json(pkg / "toy-data" / "sleep_diary" / "valid.json", {"rows": []}),
    lambda pkg: (pkg / "provenance.json").write_text("[", encoding="utf-8"),
])
def test_hardening_never_traceback(v, pkg, monkeypatch, capsys, mutate):
    mutate(pkg)
    for command in ("check", "rules", "fixtures", "summary"):
        code, out = run_main(v, monkeypatch, capsys, command, pkg)
        assert code in (0, 1, 2) and isinstance(out, dict) and "ok" in out
        assert code != 2 or "error" in out


def test_odd_data_never_traceback(v, pkg, tmp_path, monkeypatch, capsys):
    weird = tmp_path / "weird.json"
    weird.write_text('[1, "x", null, [], {"age": Infinity}, {"age": 1e400}, '
                     '{"participant_id": {"deep": [NaN]}}]', encoding="utf-8")
    code, out = run_main(v, monkeypatch, capsys, "data", pkg, "--file", weird)
    assert code == 1 and out["rows"] == 7
    cells = {(4, "age"), (5, "age"), (6, "participant_id")}
    assert sorted((f["row"], f["column"], f["keyword"]) for f in out["findings"]
                  if (f["row"], f["column"]) in cells) == [
        (4, "age", "non-finite"), (5, "age", "non-finite"), (6, "participant_id", "non-finite")]
    assert {f["keyword"] for f in out["findings"] if f["row"] < 4} == {"type"}
    ragged = tmp_path / "ragged.csv"
    ragged.write_text("participant_id,age\nP0001,40,extra\n\n,,\nP0002\n", encoding="utf-8")
    code, out = run_main(v, monkeypatch, capsys, "data", pkg, "--file", ragged)
    assert code == 1 and out["rows"] == 2
    assert any(f["keyword"] == "csv" for f in out["findings"])
    binary = tmp_path / "binary.csv"
    binary.write_bytes(b"\x00\xff\xfe")
    code, out = run_main(v, monkeypatch, capsys, "data", pkg, "--file", binary)
    assert code == 2 and "UTF-8" in out["hint"]


# --------------------------------------------------------------------- CLI


def test_exit_codes(v, pkg, tmp_path, monkeypatch, capsys):
    code, out = run_main(v, monkeypatch, capsys, "check", pkg)
    assert code == 0 and out["ok"] is True
    edit(pkg, SLEEP, lambda d: d["properties"]["caffeine"].pop("title"))
    code, out = run_main(v, monkeypatch, capsys, "check", pkg)
    assert code == 1 and out["ok"] is False and out["counts"]["error"] == 1
    code, out = run_main(v, monkeypatch, capsys, "check", tmp_path / "nowhere")
    assert code == 2 and set(out) == {"ok", "error", "hint"}
    code, out = run_main(v, monkeypatch, capsys, "check", tmp_path)
    assert code == 2 and "schemas/" in out["error"]
    code, out = run_main(v, monkeypatch, capsys, "frobnicate", pkg)
    assert code == 2 and out["error"].startswith("Usage")
    code, out = run_main(v, monkeypatch, capsys, "data", pkg)
    assert code == 2 and "--file" in out["error"]
    code, out = run_main(v, monkeypatch, capsys, "check", pkg, "--max-findings", "-1")
    assert code == 2
    code, out = run_main(v, monkeypatch, capsys, "--help")
    assert code == 0 and "check PKG" in out["help"]
    code, out = run_main(v, monkeypatch, capsys, "check", pkg, "--max-findings", "0")
    assert code == 1 and out["findings"] == [] and out["truncated"] is True


def test_refuses_the_skill_folder(v, monkeypatch, capsys):
    code, out = run_main(v, monkeypatch, capsys, "check", SCRIPT.parent.parent)
    assert code == 2 and "skill folder" in out["error"]


def test_missing_dependencies_name_the_fallback(v, pkg, monkeypatch, capsys):
    monkeypatch.setattr(v, "_IMPORT_ERROR", "No module named 'jsonschema'")
    code, out = run_main(v, monkeypatch, capsys, "check", pkg)
    assert code == 2 and 'pip install --user "jsonschema>=4.18" referencing' in out["hint"]


def test_internal_errors_are_reported_not_raised(v, pkg, monkeypatch, capsys):
    def explode(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(v, "check_report", explode)
    code, out = run_main(v, monkeypatch, capsys, "check", pkg)
    assert code == 2 and "boom" in out["error"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
