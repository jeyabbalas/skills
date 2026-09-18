#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pytest>=8", "jsonschema>=4.18", "referencing>=0.35"]
# ///
"""Tests for skills/schemify/scripts/validate.py: the conditional lint that
`check` runs on every package and the `routing` reconciliation of
ROUTING.csv against the mothers' conditionals.

Run:  uv run tests/test_schemify_validate.py
      (fallback: pip install pytest jsonschema referencing && pytest tests/)

Every test starts from a copy of examples/schemify/workspace/json_schema in
its pre-register state (rule ids stripped, no ROUTING.csv) and migrates it
itself, so the tests hold whether or not the committed example carries the
register.
"""

import csv
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "schemify" / "scripts" / "validate.py"
EXAMPLE = ROOT / "examples" / "schemify" / "workspace" / "json_schema"
MOTHER = "sleep_diary/sleep_diary.schema.json"
SLEEP_CATEGORY = "sleep_diary/categories/sleep.json"
LEDGER = "examples/toy_invalid_ledger.json"
COLUMNS = ["id", "table", "trigger", "targets", "rule", "evidence", "source",
           "decision", "status", "notes"]
ROWS = {
    "R001": {
        "id": "R001", "table": "", "trigger": "nap_yesterday", "targets": "nap_minutes",
        "rule": "nap_yesterday=0 → nap_minutes=-666 (=1 → not -666)",
        "evidence": "quoted", "source": 'dictionary.csv row 9 "Asked only if nap_yesterday=1"',
        "decision": "D010", "status": "encoded", "notes": "",
    },
    "R002": {
        "id": "R002", "table": "", "trigger": "", "targets": "sleep_minutes",
        "rule": "-666 - N/A (no diary entry) is a row-level fact with no trigger variable",
        "evidence": "implied", "source": "dictionary.csv row 6",
        "decision": "D015", "status": "not-enforceable", "notes": "no trigger column exists",
    },
}


# ------------------------------------------------------------------ helpers


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, doc):
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def conditionals(doc):
    return [e for e in doc["items"]["allOf"] if isinstance(e, dict) and "if" in e]


def edit_mother(pkg, fn):
    doc = read_json(pkg / MOTHER)
    fn(doc)
    write_json(pkg / MOTHER, doc)


def strip_ids(pkg):
    def fn(doc):
        for entry in conditionals(doc):
            entry["$comment"] = re.sub(r"^(Skip pattern|Applicability) R\d+:", r"\1:",
                                       entry["$comment"])
    edit_mother(pkg, fn)


def write_register(pkg, rows, columns=None):
    with open(pkg / "ROUTING.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns or COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def row(rid, **overrides):
    base = dict(ROWS.get(rid, {"id": rid, "table": "", "trigger": "", "targets": "",
                               "rule": "", "evidence": "quoted", "source": "",
                               "decision": "", "status": "waiting", "notes": ""}))
    base.update(overrides)
    return base


def migrate(pkg, rows=None):
    """Add R001 to both nap $comments and write the two-row register."""
    def fn(doc):
        for entry in conditionals(doc):
            entry["$comment"] = re.sub(r"^(Skip pattern|Applicability)(?: R\d+)?:",
                                       r"\1 R001:", entry["$comment"])
    edit_mother(pkg, fn)
    write_register(pkg, rows if rows is not None else [row("R001"), row("R002")])


def codes(findings):
    return [f["code"] for f in findings]


def by_code(findings, code):
    return [f for f in findings if f["code"] == code]


def add_second_table(pkg):
    src, dst = pkg / "sleep_diary", pkg / "sleep_diary2"
    shutil.copytree(src, dst)
    (dst / "sleep_diary.schema.json").rename(dst / "sleep_diary2.schema.json")
    for path in dst.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("lark/sleep_diary/", "lark/sleep_diary2/"),
                        encoding="utf-8")


# ----------------------------------------------------------------- fixtures


@pytest.fixture(scope="session")
def v():
    spec = importlib.util.spec_from_file_location("schemify_validate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def pkg(tmp_path):
    dst = tmp_path / "json_schema"
    shutil.copytree(EXAMPLE, dst, ignore=shutil.ignore_patterns("assets", "tools", "*.html"))
    strip_ids(dst)
    register = dst / "ROUTING.csv"
    if register.exists():
        register.unlink()
    return dst


# ------------------------------------------------------------ green paths


def test_example_green_with_routing_headline(v, pkg):
    migrate(pkg)
    result = v.run_summary(v.Package(pkg), v._Args())
    assert result["ok"] is True
    assert ("2 conditionals clean · routing 1/2 encoded · 0 unregistered · 1/1 fixtured"
            in result["headline"])
    assert not [s for s in result["skipped"] if s.startswith("routing")]
    routing = result["routing"]
    assert routing["ok"] is True and routing["findings"] == []
    assert routing["register"]["by_status"]["encoded"] == 1
    assert routing["rules"]["R001"]["conditionals"] == ["/items/allOf/2", "/items/allOf/3"]
    assert routing["rules"]["R001"]["fixture_cases"] == 2
    assert routing["rules"]["R002"]["conditionals"] == []
    na = routing["na"]["sleep_diary"]
    assert na["consts"] == [-666]
    assert sorted(na["bearing"]) == ["nap_minutes", "sleep_minutes"]
    assert na["unrouted"] == [] and na["truncated"] is False
    assert "common/defs.json#/$defs/not_applicable" in na["defs"]


def test_check_on_legacy_package_is_clean(v, pkg):
    check = v.run_check(v.Package(pkg))
    assert check["ok"] is True
    cond = check["conditionals"]
    assert cond["count"] == 2 and cond["with_id"] == 0
    assert cond["tables"] == {"sleep_diary": {"count": 2, "with_id": 0}}
    assert cond["findings"] == []
    # Existing keys are untouched.
    for key in ("files", "tables", "parse_errors", "meta", "ids", "refs"):
        assert key in check


def test_legacy_no_ids_no_register_is_skipped(v, pkg):
    result = v.run_summary(v.Package(pkg), v._Args())
    assert result["ok"] is True
    assert "routing" not in result
    line = [s for s in result["skipped"] if s.startswith("routing:")]
    assert len(line) == 1
    assert "no ROUTING.csv yet" in line[0] and "2 conditionals, 2 without a rule id" in line[0]
    assert result["headline"].endswith("2 conditionals clean")

    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True and routing["register"] is None
    assert routing["skipped"][0].startswith("register: no ROUTING.csv yet")
    unrouted = by_code(routing["findings"], "unrouted-na")
    assert len(unrouted) == 1
    assert unrouted[0]["count"] == 1 and unrouted[0]["variables"] == ["sleep_minutes"]
    assert routing["conditionals"] == {"sleep_diary": {"count": 2, "with_id": 0,
                                                       "unregistered": 2}}
    # Without a register, id-less conditionals are not even a warning.
    assert "unregistered-rule" not in codes(routing["findings"])


def test_fixtures_report_which_rules_fired(v, pkg):
    migrate(pkg)
    report = v.run_fixtures(v.Package(pkg), v._Args())
    assert report["ok"] is True
    invalid = report["tables"]["sleep_diary"]["invalid"]
    assert invalid["rules_fired"] == {"R001": {"cases": 2, "conditionals": {"2": 1, "3": 1}}}
    verdicts = {vd["row"]: vd for vd in invalid["verdicts"]}
    assert verdicts[2]["rules"] == ["R001"] and verdicts[3]["rules"] == ["R001"]
    assert "rules" not in verdicts[0]


def test_flatten_findings_carries_rule_and_rule_id(v, pkg):
    migrate(pkg)
    pkg_obj = v.Package(pkg)
    mother_rel = pkg_obj.mothers()["sleep_diary"]
    rows = read_json(pkg / "examples" / "toy_invalid.json")
    findings = v.flatten_findings(pkg_obj, "sleep_diary", mother_rel,
                                  v.validate_rows(pkg_obj, mother_rel, rows))
    hit = [f for f in findings if f["row"] == 2 and f["column"] == "nap_minutes"][0]
    assert hit["rule"].startswith("Skip pattern R001:")
    assert hit["rule_id"] == "R001" and hit["allof_index"] == 2
    plain = [f for f in findings if f["row"] == 0][0]
    assert "rule" not in plain and "rule_id" not in plain


def test_coverage_helpers_are_behaviour_preserving(v, pkg):
    pkg_obj = v.Package(pkg)
    coverage = v.run_coverage(pkg_obj, v._Args())
    assert coverage["ok"] is True
    assert coverage["totals"]["rows"] == 12 and coverage["schema_properties"] == 11
    index = v.schema_property_index(pkg_obj)
    assert index["sleep_diary"]["nap_minutes"] == "sleep"
    assert index["sleep_diary"]["site_id"] == "participant"
    path, rows = v.load_inventory(pkg_obj)
    assert path == pkg / "VARIABLES.csv" and len(rows) == 12
    (pkg / "VARIABLES.csv").unlink()
    assert v.load_inventory(pkg_obj, strict=False) == (pkg / "VARIABLES.csv", None)
    with pytest.raises(SystemExit):
        v.load_inventory(pkg_obj)


def test_main_routing_exits_zero_with_json(v, pkg, monkeypatch, capsys):
    migrate(pkg)
    monkeypatch.setattr(sys, "argv", ["validate.py", "routing", str(pkg)])
    with pytest.raises(SystemExit) as exc:
        v.main()
    assert exc.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True and payload["register"]["rows"] == 2


# ------------------------------------------------------ check.conditionals


def test_misspelled_trigger_is_dangling(v, pkg):
    migrate(pkg)

    def fn(doc):
        cond = doc["items"]["allOf"][2]
        cond["if"]["required"] = ["nap_yesteday"]
        cond["if"]["properties"] = {"nap_yesteday": {"const": 0}}
    edit_mother(pkg, fn)

    check = v.run_check(v.Package(pkg))
    assert check["ok"] is False
    errors = [f for f in check["conditionals"]["findings"] if f["severity"] == "error"]
    assert len(errors) == 1
    f = errors[0]
    assert f["code"] == "dangling-variable"
    assert f["pointer"] == "/items/allOf/2/if" and f["allof_index"] == 2
    assert f["variable"] == "nap_yesteday" and f["table"] == "sleep_diary"
    assert f["file"] == MOTHER and f["rule"].startswith("Skip pattern R001:")
    assert f["message"] == ("Conditional 2 names 'nap_yesteday', which no category of "
                            "sleep_diary declares.")
    assert "unevaluatedProperties: false" in f["hint"]


def test_nested_then_target_is_caught(v, pkg):
    migrate(pkg)

    def fn(doc):
        doc["items"]["allOf"][2]["then"] = {"allOf": [{"anyOf": [
            {"properties": {"ghost": {"const": 1}}},
            {"properties": {"nap_minutes": {"const": -666}}},
        ]}]}
    edit_mother(pkg, fn)

    check = v.run_check(v.Package(pkg))
    assert check["ok"] is False
    dangling = by_code(check["conditionals"]["findings"], "dangling-variable")
    assert [(f["variable"], f["pointer"]) for f in dangling] == [("ghost", "/items/allOf/2/then")]


def test_trigger_undeclared_level(v, pkg):
    migrate(pkg)

    def fn(doc):
        doc["items"]["allOf"][2]["if"]["properties"]["nap_yesterday"]["const"] = 5
    edit_mother(pkg, fn)

    check = v.run_check(v.Package(pkg))
    assert check["ok"] is True  # a warning, never an error
    warn = by_code(check["conditionals"]["findings"], "trigger-undeclared-level")
    assert len(warn) == 1
    assert warn[0]["variable"] == "nap_yesterday" and warn[0]["value"] == 5
    assert warn[0]["pointer"] == "/items/allOf/2/if" and warn[0]["severity"] == "warn"


def test_trigger_levels_through_refs_and_ranges(v, pkg):
    migrate(pkg)

    def fn(doc):
        # -888 is declared only through a $ref into common/defs.json.
        doc["items"]["allOf"][2]["if"]["properties"]["nap_yesterday"]["const"] = -888
        # An open integer branch covers 50 for age; 200 is outside 18-90.
        doc["items"]["allOf"][3]["if"] = {
            "required": ["age"], "properties": {"age": {"enum": [50, 200]}}}
    edit_mother(pkg, fn)

    check = v.run_check(v.Package(pkg))
    warn = by_code(check["conditionals"]["findings"], "trigger-undeclared-level")
    assert [(f["variable"], f["value"]) for f in warn] == [("age", 200)]


def test_shape_and_comment_warnings(v, pkg):
    migrate(pkg)

    def fn(doc):
        doc["items"]["allOf"][2]["else"] = {}
        del doc["items"]["allOf"][2]["$comment"]
        doc["items"]["allOf"][3]["$comment"] = "Note: unprefixed"
        del doc["items"]["allOf"][3]["if"]["required"]
    edit_mother(pkg, fn)

    check = v.run_check(v.Package(pkg))
    assert check["ok"] is True
    found = codes(check["conditionals"]["findings"])
    assert found.count("conditional-shape") == 2
    assert "missing-comment" in found and "comment-prefix" in found
    unguarded = [f for f in by_code(check["conditionals"]["findings"], "conditional-shape")
                 if "if.required" in f["message"]]
    assert unguarded[0]["pointer"] == "/items/allOf/3/if"


def test_missing_twin_and_applicability_substantive(v, pkg):
    migrate(pkg)

    def fn(doc):
        cond = doc["items"]["allOf"][3]
        cond["$comment"] = "Applicability R002: pinned by mistake."
        cond["then"]["properties"]["nap_minutes"] = {"const": 30}
    edit_mother(pkg, fn)

    check = v.run_check(v.Package(pkg))
    assert check["ok"] is True
    findings = check["conditionals"]["findings"]
    twins = {f["rule_id"]: f["message"] for f in by_code(findings, "missing-twin")}
    assert "no 'Applicability' half" in twins["R001"]
    assert "no 'Skip pattern' half" in twins["R002"]
    pinned = by_code(findings, "applicability-substantive")
    assert len(pinned) == 1 and pinned[0]["pointer"] == "/items/allOf/3/then"


def test_conditional_outside_mother(v, pkg):
    migrate(pkg)
    cat = read_json(pkg / SLEEP_CATEGORY)
    cat["if"] = {"required": ["nap_yesterday"], "properties": {"nap_yesterday": {"const": 0}}}
    cat["then"] = {"properties": {"nap_minutes": {"const": -666}}}
    write_json(pkg / SLEEP_CATEGORY, cat)

    check = v.run_check(v.Package(pkg))
    assert check["ok"] is True
    outside = by_code(check["conditionals"]["findings"], "conditional-outside-mother")
    assert len(outside) == 1
    assert outside[0]["file"] == SLEEP_CATEGORY and outside[0]["pointer"] == "/if"
    assert outside[0]["table"] == "sleep_diary"


def test_hidden_conditional_and_unexpected_entry(v, pkg):
    migrate(pkg)

    def fn(doc):
        allof = doc["items"]["allOf"]
        doc["$defs"] = {"nap_rule": allof[3]}
        allof[3] = {"$ref": "#/$defs/nap_rule"}
        allof.append({"title": "not a category, not a rule"})
    edit_mother(pkg, fn)

    check = v.run_check(v.Package(pkg))
    assert check["ok"] is True
    findings = check["conditionals"]["findings"]
    hidden = by_code(findings, "hidden-conditional")
    assert len(hidden) == 1 and hidden[0]["allof_index"] == 3
    assert hidden[0]["rule"].startswith("Applicability R001:")
    unexpected = by_code(findings, "unexpected-allof-entry")
    assert len(unexpected) == 1 and unexpected[0]["allof_index"] == 4
    # The $def the hidden rule lives in is not reported a second time.
    assert "conditional-outside-mother" not in codes(findings)
    assert check["conditionals"]["with_id"] == 2


def test_dangling_check_stands_down_on_unresolved_category(v, pkg):
    migrate(pkg)

    def fn(doc):
        doc["items"]["allOf"][1]["$ref"] = "categories/missing.json"
    edit_mother(pkg, fn)

    check = v.run_check(v.Package(pkg))
    assert check["ok"] is False  # the unresolved $ref, not a dangling variable
    assert check["refs"]["unresolved"]
    assert "dangling-variable" not in codes(check["conditionals"]["findings"])
    assert "stood down" in check["conditionals"]["tables"]["sleep_diary"]["skipped"]


# ---------------------------------------------------------------- routing


def test_ids_stripped_register_kept(v, pkg):
    write_register(pkg, [row("R001"), row("R002")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is False
    unregistered = by_code(routing["findings"], "unregistered-rule")
    assert sorted(f["allof_index"] for f in unregistered) == [2, 3]
    assert all(f["severity"] == "warn" for f in unregistered)
    unencoded = by_code(routing["findings"], "unencoded-row")
    assert len(unencoded) == 1 and unencoded[0]["rule_id"] == "R001"
    assert unencoded[0]["line"] == 2 and unencoded[0]["severity"] == "error"
    assert routing["conditionals"]["sleep_diary"]["unregistered"] == 2


def test_unconfirmed_encoded(v, pkg):
    migrate(pkg, [row("R001", evidence="inferred", decision=""), row("R002")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is False
    hit = by_code(routing["findings"], "unconfirmed-encoded")
    assert len(hit) == 1 and hit[0]["rule_id"] == "R001" and hit[0]["severity"] == "error"
    assert "decision-missing" not in codes(routing["findings"])


def test_proposed_undecided(v, pkg):
    migrate(pkg, [row("R001"), row("R002"),
                  row("R003", trigger="caffeine_after_noon", targets="awakenings",
                      evidence="inferred", status="proposed", decision="")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is False
    hit = by_code(routing["findings"], "proposed-undecided")
    assert len(hit) == 1 and hit[0]["rule_id"] == "R003" and hit[0]["line"] == 4


def test_declined_while_mother_carries_id_is_misregistered(v, pkg):
    migrate(pkg, [row("R001", status="declined"), row("R002")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is False
    hit = by_code(routing["findings"], "misregistered-rule")
    assert sorted(f["allof_index"] for f in hit) == [2, 3]
    assert all(f["rule_id"] == "R001" and "declined" in f["message"] for f in hit)
    assert "unencoded-row" not in codes(routing["findings"])


def test_rule_variable_mismatch(v, pkg):
    migrate(pkg, [row("R001", targets="sleep_minutes"), row("R002")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is False
    hit = by_code(routing["findings"], "rule-variable-mismatch")
    assert len(hit) == 1 and hit[0]["variable"] == "sleep_minutes"
    assert hit[0]["rule_id"] == "R001" and hit[0]["severity"] == "error"
    unlisted = by_code(routing["findings"], "unlisted-variable")
    assert len(unlisted) == 1 and unlisted[0]["variables"] == ["nap_minutes"]


def test_waiting_row_with_converted_variables_is_ready(v, pkg):
    migrate(pkg, [row("R001"), row("R002"),
                  row("R003", trigger="caffeine_after_noon", targets="awakenings",
                      evidence="quoted", status="waiting", notes="waits for: sleep")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True
    ready = by_code(routing["findings"], "ready")
    assert len(ready) == 1 and ready[0]["rule_id"] == "R003" and ready[0]["severity"] == "info"
    assert "quoted, implied, or steward" in ready[0]["hint"]
    assert "waits-unknown" not in codes(routing["findings"])  # sleep is a category


def test_waiting_row_readiness_bookkeeping(v, pkg):
    migrate(pkg, [row("R001"), row("R002"),
                  row("R003", trigger="melatonin_use", targets="ghost_var",
                      evidence="implied", status="waiting", notes="waits for: nowhere")])
    inv = (pkg / "VARIABLES.csv").read_text(encoding="utf-8")
    (pkg / "VARIABLES.csv").write_text(
        inv.replace("melatonin_use,,sleep,deferred", "melatonin_use,,sleep,dropped"),
        encoding="utf-8")
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True
    found = {(f["code"], f["variable"]) for f in routing["findings"] if "variable" in f}
    assert ("names-dropped", "melatonin_use") in found
    assert ("variable-uninventoried", "ghost_var") in found
    assert ("waits-unknown", "nowhere") in found
    assert "ready" not in codes(routing["findings"])


def test_readiness_skipped_without_inventory(v, pkg):
    migrate(pkg, [row("R001"), row("R002"),
                  row("R003", trigger="caffeine_after_noon", targets="awakenings",
                      status="waiting")])
    (pkg / "VARIABLES.csv").unlink()
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True
    assert any(s.startswith("readiness:") for s in routing["skipped"])
    assert "ready" not in codes(routing["findings"])


def test_unrouted_na_when_register_row_removed(v, pkg):
    migrate(pkg, [row("R001")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True
    hit = by_code(routing["findings"], "unrouted-na")
    assert len(hit) == 1 and hit[0]["count"] == 1 and hit[0]["severity"] == "info"
    assert hit[0]["variables"] == ["sleep_minutes"]
    assert routing["na"]["sleep_diary"]["unrouted"] == ["sleep_minutes"]


def test_universe_unrouted(v, pkg):
    def fn(doc):
        doc["items"]["allOf"] = [e for e in doc["items"]["allOf"] if "if" not in e]
    edit_mother(pkg, fn)
    write_register(pkg, [row("R002")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True
    universe = by_code(routing["findings"], "universe-unrouted")
    assert [f["variable"] for f in universe] == ["nap_minutes"]
    assert by_code(routing["findings"], "unrouted-na")[0]["variables"] == ["nap_minutes"]


def test_second_mother_with_blank_table(v, pkg):
    migrate(pkg)
    add_second_table(pkg)
    pkg_obj = v.Package(pkg)
    assert sorted(pkg_obj.mothers()) == ["sleep_diary", "sleep_diary2"]
    routing = v.run_routing(pkg_obj, v._Args())
    assert routing["ok"] is False
    missing = by_code(routing["findings"], "missing-table")
    assert sorted(f["line"] for f in missing) == [2, 3]
    assert "wrong-table" not in codes(routing["findings"])
    assert routing["register"]["rows"] == 2

    write_register(pkg, [row("R001", table="sleep_diary2"), row("R002", table="sleep_diary2")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    wrong = by_code(routing["findings"], "wrong-table")
    assert {(f["table"], f["allof_index"]) for f in wrong} == {("sleep_diary", 2), ("sleep_diary", 3)}
    assert routing["rules"]["R001"]["table"] == "sleep_diary2"
    # VARIABLES.csv rows without a table column are reported once, not per name.
    assert "variable-uninventoried" not in codes(routing["findings"])
    assert any(s.startswith("readiness: 12 VARIABLES.csv rows have no table column")
               for s in routing["skipped"])

    write_register(pkg, [row("R001", table="nope"), row("R002", table="sleep_diary")])
    routing = v.run_routing(v.Package(pkg), v._Args(table="sleep_diary"))
    assert by_code(routing["findings"], "unknown-table")[0]["line"] == 2
    assert routing["conditionals"] and list(routing["conditionals"]) == ["sleep_diary"]


def test_bad_status_and_missing_column(v, pkg):
    migrate(pkg, [row("R001", status="encoded!"), row("R002")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is False
    hit = by_code(routing["findings"], "bad-status")
    assert len(hit) == 1 and hit[0]["line"] == 2 and "encoded!" in hit[0]["message"]
    assert routing["register"]["by_status"]["encoded"] == 0

    write_register(pkg, [row("R001"), row("R002")], columns=COLUMNS[:-1])
    with pytest.raises(SystemExit):
        v.run_routing(v.Package(pkg), v._Args())


def test_register_syntax_errors(v, pkg):
    migrate(pkg, [row("R001"), row("R001", evidence="guess", decision="10"),
                  row("X1", trigger="nap_yesterday=0", targets="nap_minutes",
                      status="waiting")])
    write_register(pkg, [row("R001"), row("R001", evidence="guess", decision="10"),
                         row("X1", trigger="nap_yesterday=0", targets="nap_minutes",
                             status="waiting")],
                   columns=COLUMNS + ["owner"])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is False
    found = codes(routing["findings"])
    for code in ("duplicate-id", "bad-evidence", "bad-decision", "bad-id",
                 "bad-variable-name", "extra-column"):
        assert code in found, code
    assert by_code(routing["findings"], "extra-column")[0]["severity"] == "warn"
    assert by_code(routing["findings"], "bad-variable-name")[0]["variable"] == "nap_yesterday=0"


def test_decision_missing_empty_variables_and_confirmed(v, pkg):
    migrate(pkg, [row("R001", evidence="implied", decision=""),
                  row("R002", decision=""),
                  row("R003", status="confirmed", evidence="steward", decision="D020")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is False
    missing = {f["rule_id"] for f in by_code(routing["findings"], "decision-missing")}
    assert missing == {"R001", "R002"}
    empty = by_code(routing["findings"], "empty-variables")
    assert len(empty) == 1 and empty[0]["rule_id"] == "R003"
    assert "trigger and targets" in empty[0]["message"]
    confirmed = by_code(routing["findings"], "unencoded-confirmed")
    assert len(confirmed) == 1 and confirmed[0]["rule_id"] == "R003"


def test_unknown_rule_id_in_mother(v, pkg):
    migrate(pkg, [row("R002")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is False
    hit = by_code(routing["findings"], "unknown-rule-id")
    assert sorted(f["allof_index"] for f in hit) == [2, 3]
    assert all(f["rule_id"] == "R001" for f in hit)


def test_ledger_case_deleted_is_unfixtured(v, pkg):
    migrate(pkg)
    ledger = read_json(pkg / LEDGER)
    ledger["violations"] = [c for c in ledger["violations"] if c["row"] != 2]
    write_json(pkg / LEDGER, ledger)
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True  # a warning: the rule exists, nobody has seen it fire
    hit = by_code(routing["findings"], "rule-unfixtured")
    assert len(hit) == 1
    assert hit[0]["rule_id"] == "R001" and hit[0]["allof_index"] == 2
    assert hit[0]["severity"] == "warn" and "Skip pattern" in hit[0]["message"]
    # One location: the conditional in the mother; the register row rides separately.
    assert hit[0]["file"] == MOTHER and hit[0]["pointer"] == "/items/allOf/2"
    assert hit[0]["register_line"] == 2 and "line" not in hit[0]
    assert routing["rules"]["R001"]["fixture_cases"] == 1


def test_routing_reuses_fixtures_report_from_summary(v, pkg):
    migrate(pkg)
    pkg_obj = v.Package(pkg)
    check = v.run_check(pkg_obj)
    fixtures = v.run_fixtures(pkg_obj, v._Args())
    routing = v.run_routing(pkg_obj, v._Args(), check=check, fixtures=fixtures)
    assert routing["ok"] is True and routing["rules"]["R001"]["fixture_cases"] == 2
    shutil.rmtree(pkg / "examples")
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True
    assert any(s.startswith("fixtures:") for s in routing["skipped"])
    assert "rule-unfixtured" not in codes(routing["findings"])


def test_max_findings_caps_output_not_counts(v, pkg):
    # R001 is in the mother but not the register: the errors (unknown-rule-id) are
    # found in the mother phase, after the register phase's warn (decision-missing).
    migrate(pkg, [row("R002", decision="")])
    routing = v.run_routing(v.Package(pkg), v._Args(max_findings=1))
    assert routing["counts"] == {"error": 2, "warn": 1, "info": 0}
    assert routing["truncated"] is True and len(routing["findings"]) == 1
    assert routing["findings"][0]["code"] == "unknown-rule-id"
    full = v.run_routing(v.Package(pkg), v._Args())
    assert [f["severity"] for f in full["findings"]] == ["error", "error", "warn"]


def test_summary_goes_red_only_on_register_errors(v, pkg):
    migrate(pkg, [row("R001", targets="sleep_minutes"), row("R002")])
    result = v.run_summary(v.Package(pkg), v._Args())
    assert result["ok"] is False and result["check"]["ok"] is True
    assert result["routing"]["ok"] is False
    assert "routing 1/2 encoded" in result["headline"]


# -------------------------------------------------------------- hardening


def test_non_utf8_register_fails_with_encoding_hint(v, pkg, capsys):
    migrate(pkg)
    text = ",".join(COLUMNS) + "\n" + \
        "R001,,nap_yesterday,nap_minutes,nap rule,quoted,café sheet,D010,encoded,\n"
    (pkg / "ROUTING.csv").write_bytes(text.encode("cp1252"))  # 0xE9 is not UTF-8
    with pytest.raises(SystemExit) as exc:
        v.run_routing(v.Package(pkg), v._Args())
    assert exc.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and payload["error"].startswith("ROUTING.csv could not be read")
    assert "UTF-8" in payload["hint"] and "ROUTING-FORMAT.md" in payload["hint"]


def test_non_utf8_inventory(v, pkg, capsys):
    migrate(pkg)
    (pkg / "VARIABLES.csv").write_bytes(
        b"variable,table,category,status,source,notes\nage,,participant,converted,caf\xe9,\n")
    with pytest.raises(SystemExit) as exc:
        v.run_coverage(v.Package(pkg), v._Args())
    assert exc.value.code == 1
    assert "UTF-8" in json.loads(capsys.readouterr().out)["hint"]
    routing = v.run_routing(v.Package(pkg), v._Args())  # readiness stands down, no crash
    assert routing["ok"] is True
    assert any(s.startswith("readiness: VARIABLES.csv could not be read") for s in routing["skipped"])


def test_nul_byte_in_register_never_tracebacks(v, pkg, capsys):
    migrate(pkg)
    data = (pkg / "ROUTING.csv").read_bytes().replace(b"encoded", b"enc\x00oded")
    (pkg / "ROUTING.csv").write_bytes(data)
    try:
        result = v.run_routing(v.Package(pkg), v._Args())
    except SystemExit as exc:   # 3.9/3.10: csv refuses NUL bytes - reported, not raised
        assert exc.code == 1
        assert "could not be read" in json.loads(capsys.readouterr().out)["error"]
    else:                       # 3.11+: the NUL rides along and the status is simply wrong
        assert result["ok"] is False and "bad-status" in codes(result["findings"])


def test_blank_register_lines_are_skipped(v, pkg):
    migrate(pkg)
    with open(pkg / "ROUTING.csv", "a", encoding="utf-8", newline="") as f:
        f.write("   \r\n,,,,,,,,,\r\n\r\n")
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True and routing["register"]["rows"] == 2
    assert routing["counts"]["error"] == 0
    info = by_code(routing["findings"], "blank-rows")
    assert len(info) == 1 and info[0]["severity"] == "info"
    assert "2 blank lines ignored (lines 4, 5)" in info[0]["message"]


def test_blank_inventory_lines_are_skipped(v, pkg):
    with open(pkg / "VARIABLES.csv", "a", encoding="utf-8", newline="") as f:
        f.write("   \n,,,,,\n")
    coverage = v.run_coverage(v.Package(pkg), v._Args())
    assert coverage["ok"] is True and coverage["totals"]["rows"] == 12
    assert coverage["notes"] == ["2 blank lines ignored (lines 14, 15)"]
    # Line numbers in coverage findings still point at the file, not the row index.
    inv = (pkg / "VARIABLES.csv").read_text(encoding="utf-8")
    (pkg / "VARIABLES.csv").write_text(inv.replace("awakenings,,sleep,converted",
                                                   "awakenings,,sleep,convertd"),
                                       encoding="utf-8")
    coverage = v.run_coverage(v.Package(pkg), v._Args())
    assert coverage["problems"]["bad_rows"][0]["line"] == 9


def test_padded_headers_are_accepted(v, pkg):
    migrate(pkg)
    for name, columns in (("ROUTING.csv", COLUMNS),
                          ("VARIABLES.csv", v.INVENTORY_COLUMNS)):
        path = pkg / name
        lines = path.read_text(encoding="utf-8").splitlines(True)
        eol = "\r\n" if lines[0].endswith("\r\n") else "\n"
        lines[0] = " , ".join(" " + c + " " for c in columns) + eol
        path.write_text("".join(lines), encoding="utf-8")
    assert v.run_routing(v.Package(pkg), v._Args())["ok"] is True
    assert v.run_coverage(v.Package(pkg), v._Args())["ok"] is True


def test_meta_invalid_category_stands_down_everywhere(v, pkg):
    migrate(pkg)
    cat = read_json(pkg / SLEEP_CATEGORY)
    cat["properties"] = [cat["properties"]]  # a list: meta-invalid, used to traceback
    write_json(pkg / SLEEP_CATEGORY, cat)
    pkg_obj = v.Package(pkg)
    check = v.run_check(pkg_obj)
    assert check["ok"] is False
    assert [m["file"] for m in check["meta"]["failed"]] == [SLEEP_CATEGORY]
    table = check["conditionals"]["tables"]["sleep_diary"]
    assert "meta-validation failed - fix check.meta first" in table["skipped"]
    assert check["conditionals"]["findings"] == [] and table["count"] == 2
    # routing (standalone and via summary) skips the fixtures instead of crashing.
    routing = v.run_routing(pkg_obj, v._Args())
    assert routing["ok"] is True
    assert any(s.startswith("sleep_diary: meta-validation failed") for s in routing["skipped"])
    assert any(s.startswith("fixtures: meta-validation failed") for s in routing["skipped"])
    summary = v.run_summary(pkg_obj, v._Args())
    assert summary["ok"] is False and "fixtures" not in summary
    assert any(s.startswith("fixtures: meta-validation failed") for s in summary["skipped"])


def test_string_bound_and_numeric_trigger_never_traceback(v, pkg):
    assert v.level_declared(50, [], [{"types": ["integer"], "minimum": "18", "maximum": None}])
    assert v.level_declared(50, [], [{"types": ["integer"], "minimum": True, "maximum": 90}])
    assert not v.level_declared(5, [], [{"types": ["integer"], "minimum": 18, "maximum": 90}])
    migrate(pkg)
    participant = pkg / "sleep_diary/categories/participant.json"
    doc = read_json(participant)
    doc["properties"]["age"]["anyOf"][0]["minimum"] = "18"
    write_json(participant, doc)
    edit_mother(pkg, lambda d: d["items"]["allOf"][3].__setitem__(
        "if", {"required": ["age"], "properties": {"age": {"const": 50}}}))
    check = v.run_check(v.Package(pkg))
    assert check["ok"] is False and check["meta"]["failed"]
    assert "trigger-undeclared-level" not in codes(check["conditionals"]["findings"])
    assert v.run_routing(v.Package(pkg), v._Args())["ok"] is True


def test_odd_refs_never_traceback(v, pkg):
    migrate(pkg)

    def fn(doc):
        doc["$defs"] = {"x": [1, 2]}
        doc["items"]["allOf"].append({"$ref": 5})
        doc["items"]["allOf"].append({"$ref": "#/$defs/x", "title": "sibling"})
    edit_mother(pkg, fn)

    pkg_obj = v.Package(pkg)
    mother_rel = pkg_obj.mothers()["sleep_diary"]
    assert pkg_obj.deref({"$ref": 5}, mother_rel) == {"$ref": 5}
    assert pkg_obj.deref({"$ref": "#/$defs/x"}, mother_rel) == [1, 2]
    with_sibling = {"$ref": "#/$defs/x", "title": "sibling"}
    assert pkg_obj.deref(with_sibling, mother_rel) == with_sibling
    assert v.resolve_ref(pkg_obj, mother_rel, 5) == (None, "")
    check = v.run_check(pkg_obj)
    assert check["ok"] is False
    assert [m["file"] for m in check["meta"]["failed"]] == [MOTHER]
    assert "meta-validation failed" in check["conditionals"]["tables"]["sleep_diary"]["skipped"]
    routing = v.run_routing(pkg_obj, v._Args())   # standalone: runs its own meta check
    assert any("meta-validation failed" in s for s in routing["skipped"])


def test_allof_string_is_one_finding(v, pkg):
    migrate(pkg)
    edit_mother(pkg, lambda doc: doc["items"].__setitem__("allOf", "categories/sleep.json"))
    pkg_obj = v.Package(pkg)
    check = v.run_check(pkg_obj)
    assert check["ok"] is False and len(check["meta"]["failed"]) == 1
    cond = check["conditionals"]
    assert cond["findings"] == [] and cond["count"] == 0
    assert "meta-validation failed" in cond["tables"]["sleep_diary"]["skipped"]
    # The guards themselves, for a path that skips the meta stand-down.
    assert v.allof_entries({"items": {"allOf": "abc"}}) == []
    assert v.mother_conditionals(pkg_obj, MOTHER) == ([], [])
    assert v.row_property_schemas(pkg_obj, MOTHER) == {}
    assert v.lint_conditionals(pkg_obj)["findings"] == []


def test_waits_for_prose_is_not_a_wait(v, pkg):
    assert v.parse_waits("waits for the steward to confirm") == []
    assert v.parse_waits("waits for: sleep; nowhere, parity") == ["sleep", "nowhere", "parity"]
    migrate(pkg, [row("R001"), row("R002"),
                  row("R003", trigger="caffeine_after_noon", targets="awakenings",
                      status="waiting", notes="waits for the steward to confirm")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert routing["ok"] is True
    assert "waits-unknown" not in codes(routing["findings"])


def test_confirmed_without_decision(v, pkg):
    migrate(pkg, [row("R001"), row("R002"),
                  row("R003", trigger="caffeine_after_noon", targets="awakenings",
                      evidence="steward", status="confirmed", decision="")])
    routing = v.run_routing(v.Package(pkg), v._Args())
    hit = by_code(routing["findings"], "decision-missing")
    assert [f["rule_id"] for f in hit] == ["R003"] and "steward's yes" in hit[0]["hint"]
    assert "unencoded-confirmed" in codes(routing["findings"])


def test_unresolved_category_stands_routing_down(v, pkg):
    migrate(pkg, [row("R001"), row("R002"),
                  row("R003", trigger="caffeine_after_noon", targets="awakenings",
                      status="waiting", notes="waits for: nowhere")])
    edit_mother(pkg, lambda doc: doc["items"]["allOf"][1].__setitem__(
        "$ref", "categories/missing.json"))
    routing = v.run_routing(v.Package(pkg), v._Args())
    assert any("did not resolve" in s and s.startswith("sleep_diary:") for s in routing["skipped"])
    assert any(s.startswith("fixtures: category $ref(s)") for s in routing["skipped"])
    for code in ("waits-unknown", "unrouted-na", "universe-unrouted", "rule-unfixtured"):
        assert code not in codes(routing["findings"]), code
    assert routing["na"]["sleep_diary"] == {"skipped": "category $ref(s) did not resolve"}
    summary = v.run_summary(v.Package(pkg), v._Args())   # no jsonschema crash either
    assert summary["ok"] is False and "fixtures" not in summary


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
