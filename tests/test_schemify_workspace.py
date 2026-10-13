#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pytest>=8"]
# ///
"""Tests for schemify's workspace scripts: skills/schemify/scripts/schemify.py (the
ledger, replay, question queue, inbox, build, check, sessions), serve.py (the
workspace website's localhost server) and migrate.py (1.x packages into 2.x workspaces).

Run:  uv run tests/test_schemify_workspace.py
      (fallback: python3 -m pip install pytest && python3 -m pytest tests/test_schemify_workspace.py)

Every test works in its own temporary directory. Workspaces are built from a small
sleep-diary package written inline here; the 1.x fixture (tests/fixtures/schemify-1x)
is copied before migrate.py sees it. The package validator, validate.py, has its own
suite: here a stub report stands in for it (`build(validate=False)`, `check(ws,
validate=False)`), except in one end-to-end `build` that needs `uv`.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import http.client
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import types
import zipfile
from pathlib import Path

import pytest

sys.dont_write_bytecode = True          # never write __pycache__ into the skill directory

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "schemify" / "scripts"
SCHEMIFY = SCRIPTS / "schemify.py"
SERVE = SCRIPTS / "serve.py"
MIGRATE = SCRIPTS / "migrate.py"
FIXTURE_1X = ROOT / "tests" / "fixtures" / "schemify-1x"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sf = _load("schemify", SCHEMIFY)            # migrate.py's own `import schemify` finds this module
mg = _load("schemify_migrate", MIGRATE)


# ====================================================================== the inline package

SCHEMA = "https://json-schema.org/draft/2020-12/schema"
BASE = "https://schemas.example.org/lark/"
DEFS = "common/defs.json"
MOTHER = "sleep_diary/sleep_diary.schema.json"
PARTICIPANT = "sleep_diary/categories/participant.json"
SLEEP = "sleep_diary/categories/sleep.json"
DONT_KNOW = {"$ref": "../../common/defs.json#/$defs/dont_know"}
NOT_APPLICABLE = {"$ref": "../../common/defs.json#/$defs/not_applicable"}
STUB_HEADLINE = "stub report: validate.py is tested elsewhere"


def package_docs() -> dict:
    """A small valid sleep-diary package: two topics, one skip pair (R001), shared sentinels."""
    defs = {
        "$schema": SCHEMA, "$id": BASE + DEFS, "title": "LARK — shared definitions",
        "$defs": {
            "not_applicable": {"const": -666, "title": "Not applicable (skipped by design)",
                               "x-value-kind": "sentinel", "x-provenance": {"default": "S01:row 9"}},
            "dont_know": {"const": -888, "title": "Don't know",
                          "x-value-kind": "sentinel", "x-provenance": {"default": "S01:row 2"}},
        },
    }
    participant = {
        "$schema": SCHEMA, "$id": BASE + PARTICIPANT, "title": "Sleep diary — Participant", "type": "object",
        "properties": {
            "participant_id": {"title": "Participant identifier", "x-provenance": {"default": "S01:row 1"},
                               "type": "string", "pattern": "^P[0-9]{4}$"},
            "site_id": {"title": "Recruitment site", "x-provenance": {"default": "S01:row 2"},
                        "oneOf": [{"const": "01", "title": "Northside clinic"},
                                  {"const": "02", "title": "Riverside clinic"}]},
            "age": {"title": "Age at enrollment (years)", "x-provenance": {"default": "S01:row 3"},
                    "anyOf": [{"type": "integer", "minimum": 18, "maximum": 90}, DONT_KNOW]},
        },
        "required": ["participant_id", "site_id", "age"],
    }
    sleep = {
        "$schema": SCHEMA, "$id": BASE + SLEEP, "title": "Sleep diary — Sleep", "type": "object",
        "properties": {
            "sleep_minutes": {"title": "Total sleep last night (minutes)", "x-provenance": {"default": "S01:row 6"},
                              "anyOf": [{"type": "integer", "minimum": 0, "maximum": 960}, DONT_KNOW]},
            "nap_yesterday": {"title": "Napped yesterday", "x-provenance": {"default": "S01:row 8"},
                              "oneOf": [{"const": 0, "title": "No"}, {"const": 1, "title": "Yes"}, DONT_KNOW]},
            "nap_minutes": {"title": "Nap duration yesterday (minutes)", "x-provenance": {"default": "S01:row 9"},
                            "anyOf": [{"type": "integer", "minimum": 0, "maximum": 600}, NOT_APPLICABLE, DONT_KNOW]},
        },
        "required": ["sleep_minutes", "nap_yesterday", "nap_minutes"],
    }
    mother = {
        "$schema": SCHEMA, "$id": BASE + MOTHER, "title": "Sleep diary",
        "description": "Array of diary records. One element is one participant-night.", "type": "array",
        "items": {
            "type": "object",
            "allOf": [
                {"$ref": "categories/participant.json"},
                {"$ref": "categories/sleep.json"},
                {"$comment": "Skip pattern R001: no nap yesterday means nap duration is not applicable. "
                             "Dictionary row 9: 'Asked only if nap_yesterday=1'.",
                 "x-provenance": {"default": "S01:row 9"},
                 "if": {"required": ["nap_yesterday"], "properties": {"nap_yesterday": {"const": 0}}},
                 "then": {"properties": {"nap_minutes": {"const": -666}}}},
                {"$comment": "Applicability R001: a reported nap has a duration or an item-missing code, "
                             "never the not-applicable code.",
                 "x-provenance": {"default": "S01:row 9"},
                 "if": {"required": ["nap_yesterday"], "properties": {"nap_yesterday": {"const": 1}}},
                 "then": {"properties": {"nap_minutes": {"not": {"const": -666}}}}},
            ],
            "unevaluatedProperties": False,
        },
    }
    return copy.deepcopy({DEFS: defs, PARTICIPANT: participant, SLEEP: sleep, MOTHER: mother})


PROJECT = {
    "description": "LARK is a synthetic sleep-diary study: adults keep a morning diary of the night before.",
    "idBase": BASE,
    "tables": [{"name": "sleep_diary", "title": "Sleep diary", "grain": "One element is one participant-night.",
                "mother": MOTHER}],
    "topics": [{"id": "participant", "title": "Participant", "table": "sleep_diary", "file": PARTICIPANT},
               {"id": "sleep", "title": "Sleep", "table": "sleep_diary", "file": SLEEP}],
    "conventions": {"missing": "in-band codes",
                    "sentinels": [{"code": -666, "meaning": "Not applicable (skipped by design)", "structural": True},
                                  {"code": -888, "meaning": "Don't know", "structural": False}]},
    "people": [{"role": "author", "name": "", "profile": "informed", "knows": ["the diary instrument"]}],
}

INVENTORY = [
    {"variable": v, "table": "sleep_diary", "topic": t, "status": "include", "source": s, "note": ""}
    for v, t, s in (("participant_id", "participant", "S01:row 1"), ("site_id", "participant", "S01:row 2"),
                    ("age", "participant", "S01:row 3"), ("sleep_minutes", "sleep", "S01:row 6"),
                    ("nap_yesterday", "sleep", "S01:row 8"), ("nap_minutes", "sleep", "S01:row 9"))
]

OPTS = [{"id": "a", "label": "Keep 0–600"}, {"id": "b", "label": "No upper bound"}]
BULK_OPTIONS = [{"id": "accept", "label": "Yes, accept them all"}, {"id": "review", "label": "Show me each one"},
                {"id": "steward", "label": "Leave them for the data steward"}]
SRC_DOC = {"type": "source", "event": "add", "kind": "document", "title": "Diary form", "what": "The paper diary, 2019",
           "path": "sources/S02-diary-form.pdf", "original": "/Users/someone/Downloads/form.pdf"}
SRC_WEB = {"type": "source", "event": "add", "kind": "web", "title": "Protocol paper", "what": "Methods of the study",
           "url": "https://example.org/lark-protocol", "origin": "agent"}
BASE_RULE = {"type": "rule", "event": "add", "table": "sleep_diary", "gates": ["nap_yesterday"],
             "targets": ["sleep_minutes"], "reading": "nap_yesterday = 0 → sleep_minutes = -666",
             "refs": ["S01:row 6"]}


# ====================================================================== helpers

def write_json(path: Path, data) -> None:
    sf.write_json(path, data)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_inventory(ws: Path, rows=None) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=sf.INVENTORY_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(INVENTORY if rows is None else rows)
    (ws / "state" / "variables.csv").write_text(buf.getvalue(), encoding="utf-8")


def edit(ws: Path, rel: str, fn) -> None:
    """Change one schema file of the package in place."""
    p = ws / "package" / "schemas" / rel
    doc = read_json(p)
    fn(doc)
    write_json(p, doc)


def edit_project(ws: Path, fn) -> None:
    proj = sf.load_project(ws)
    fn(proj)
    sf.save_project(ws, proj)


def rec(ws: Path, *events) -> list:
    """Record events through `record_events`; return the ids it reports."""
    return [r["id"] for r in sf.record_events(ws, list(events))["recorded"]]


def refused(ws: Path, *events) -> str:
    """Record events that must be refused; return every problem, one per line."""
    with pytest.raises(sf.Fail) as ei:
        sf.record_events(ws, list(events))
    assert ei.value.error.startswith("Nothing recorded"), ei.value.error
    return "\n".join(ei.value.extra["problems"])


def question(**kw) -> dict:
    """A decision.open event; a keyword set to None removes that field."""
    ev = {"type": "decision", "event": "open", "kind": "gap", "topic": "sleep", "targets": ["nap_minutes"],
          "question": "Is there an upper limit for nap duration?",
          "evidence": [{"ref": "S01:row 9", "quote": "minutes; -666=N/A (no nap); -888=Don't know"}],
          "options": OPTS, "recommended": "a", "why": "Ten hours of napping is already implausible."}
    ev.update(kw)
    if "provisional" not in kw and "a" in [o.get("id") for o in ev.get("options") or [] if isinstance(o, dict)]:
        ev["provisional"] = "a"                           # what the schemas encode until the answer arrives
    return {k: v for k, v in ev.items() if v is not None}


def guess(**kw) -> dict:
    """A decision.decide event that creates a guess; a keyword set to None removes that field."""
    ev = {"type": "decision", "event": "decide", "kind": "guess", "topic": "sleep", "targets": ["sleep_minutes"],
          "question": "Plausible upper bound for total sleep (minutes)?", "choice": "960",
          "why": "Sixteen hours rejects the impossible, not the rare."}
    ev.update(kw)
    return {k: v for k, v in ev.items() if v is not None}


def answer(did: str, choice="a", by="author", **kw) -> dict:
    return {"type": "decision", "event": "answer", "id": did, "by": by, "choice": choice, **kw}


def apply_(did: str, **kw) -> dict:
    return {"type": "decision", "event": "apply", "id": did, "files": ["package/schemas/" + SLEEP], **kw}


def confirm(did: str, by="author", **kw) -> dict:
    return {"type": "decision", "event": "confirm", "id": did, "by": by, **kw}


def post(*items, to="author", title="Sleep — questions") -> dict:
    return {"type": "batch", "event": "post", "to": to, "title": title, "items": list(items)}


def dec(ws: Path, did: str) -> dict:
    return sf.load_world(ws).decisions[did]


def statuses(ws: Path) -> dict:
    return {k: v["status"] for k, v in sf.load_world(ws).decisions.items()}


def next_actions(ws: Path) -> list:
    return [a["action"] for a in sf.status_payload(ws)["next"]]


def ledger_bytes(ws: Path) -> bytes:
    return (ws / "state" / "ledger.jsonl").read_bytes()


def ledger_events(ws: Path) -> list:
    return [json.loads(line) for line in (ws / "state" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]


def snapshot(root: Path, skip=()) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if any(rel == s or rel.startswith(s + "/") for s in skip):
            continue
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def submit(ws: Path, items, sub="20260102T030405Z-a1b2c3", frm="author") -> str:
    """Drop a submission into inbox/pending exactly as serve.py saves the website's POST."""
    doc = {"schemifyInbox": 1, "workspace": sf.load_project(ws).get("id"), "study": "LARK sleep study", "from": frm,
           "submittedAt": "2026-01-02T03:04:05.678Z", "items": items, "id": sub, "receivedAt": "2026-01-02T03:04:05Z"}
    write_json(ws / "inbox" / "pending" / f"{sub}.json", doc)
    return sub


def stub_checks(ws: Path, tested=(), errors=0) -> None:
    """Stand in for validate.py's last report (state/checks.json)."""
    doc = {"ok": True, "ran": True, "headline": STUB_HEADLINE, "at": sf.now()}
    if tested:
        doc["topics"] = {f"sleep_diary/{t}": {"errors": errors, "warnings": 0, "coverage": {"total": 3, "covered": 3}}
                         for t in tested}
        doc["fixtures"] = {"tables": {"sleep_diary": {"valid": {"status": "pass"},
                                                      "invalid": {"verdicts": [{"status": "caught"}]}}}}
    write_json(ws / "state" / "checks.json", doc)


def checked(ws: Path) -> dict:
    """`check` without the validator: a stub report stands in for it, and the site is rebuilt first."""
    if not (ws / "state" / "checks.json").exists():
        stub_checks(ws)
    sf.build(ws, validate=False)
    return sf.check(ws, validate=False)


def find(result: dict, code: str) -> list:
    return [f for f in result["findings"] if f["code"] == code]


def findings_doc(set_id: str, records=120, failing=7) -> dict:
    """A QuaC 'findings without data' document: two failing checks and one note."""
    return {
        "containsData": False, "findingsSchemaVersion": 1, "generator": "QuaC 1.2.0",
        "dataset": {"name": "wave1-export.csv"},
        "inputs": {"schema": {"setId": set_id, "root": MOTHER}},
        "overview": {"records": records, "recordsWithErrors": failing},
        "schemaChecks": [
            {"severity": "error", "level": "value", "variable": "nap_minutes", "ruleId": "schema:cond:2:then",
             "keyword": "const", "requirement": "must be -666 when nap_yesterday is 0", "records": 7,
             "location": {"file": MOTHER, "pointer": "/items/allOf/2/then/properties/nap_minutes"}},
            {"severity": "warning", "level": "value", "variable": "age", "ruleId": "schema:range",
             "keyword": "maximum", "records": 2,
             "location": {"file": PARTICIPANT, "pointer": "/properties/age/anyOf/0"}},
            {"severity": "info", "level": "dataset", "ruleId": "schema:dataset:undescribed", "keyword": "x",
             "records": 0, "location": {}},
        ],
    }


def json_blocks(page: str) -> list:
    return [json.loads(m) for m in re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', page, re.S)]


def run(script: Path, *args, stdin=None, cwd=None, timeout=120) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *map(str, args)], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", cwd=cwd, env=ENV, timeout=timeout)


def cli(*args, stdin=None, cwd=None, script=SCHEMIFY, timeout=120):
    """Run a script; stdout must be exactly one JSON object. Returns (exit code, object)."""
    proc = run(script, *args, stdin=stdin, cwd=cwd, timeout=timeout)
    assert proc.stdout.startswith("{") and proc.stdout.rstrip().endswith("}"), proc.stdout + proc.stderr
    obj = json.loads(proc.stdout)                 # raises "Extra data" if anything follows the object
    assert isinstance(obj, dict)
    assert "Traceback" not in proc.stderr, proc.stderr
    return proc.returncode, obj


@pytest.fixture(autouse=True)
def _in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def bare(tmp_path) -> Path:
    """A freshly initialised workspace: no sources, no plan."""
    return Path(sf.init(str(tmp_path / "schemify"), "LARK sleep study", None, None, None)["workspace"])


@pytest.fixture
def ws(bare) -> Path:
    """A planned, drafted workspace: S01 registered and digested, two topics drafted, R001 encoded."""
    for rel, doc in package_docs().items():
        write_json(bare / "package" / "schemas" / rel, doc)
    edit_project(bare, lambda p: p.update(copy.deepcopy(PROJECT)))
    write_inventory(bare)
    (bare / "sources" / "S01-dictionary.csv").write_text("#,Variable,Label\n1,participant_id,Participant\n",
                                                         encoding="utf-8")
    (bare / "sources" / "S01").mkdir()
    (bare / "sources" / "S01" / "DIGEST.md").write_text("# S01 — LARK data dictionary\n", encoding="utf-8")
    rec(bare,
        {"type": "source", "event": "add", "kind": "document", "title": "LARK data dictionary",
         "what": "Variables with labels, types and codes", "path": "sources/S01-dictionary.csv",
         "original": "/Users/someone/dictionary.csv", "origin": "user"},
        {"type": "source", "event": "digest", "id": "S01", "path": "sources/S01/DIGEST.md", "variables": 6,
         "verified": ["row 6", "row 9"]},
        {"type": "rule", "event": "add", "table": "sleep_diary", "gates": ["nap_yesterday"], "targets": ["nap_minutes"],
         "reading": "nap_yesterday = 0 → nap_minutes = -666 (= 1 → not -666)", "evidence": "documented",
         "refs": ["S01:row 9"], "status": "encoded"})
    return bare


@pytest.fixture
def stub_validator(monkeypatch) -> list:
    """`close` always validates; this stands in for validate.py and counts the calls."""
    calls = []

    def fake(ws, timeout=900):
        calls.append(ws)
        doc = {"ok": True, "ran": True, "headline": STUB_HEADLINE, "at": sf.now()}
        write_json(ws / "state" / "checks.json", doc)
        return doc

    monkeypatch.setattr(sf, "run_validator", fake)
    return calls


# ====================================================================== init

def test_init_creates_the_tree_and_the_shipped_files(tmp_path):
    code, out = cli("init", "--study", "LARK sleep study", "--harness", "codex", "--invoke", "$schemify", cwd=tmp_path)
    ws = tmp_path / "schemify"
    assert code == 0 and out["ok"] is True and out["existing"] is False and out["next"]
    assert Path(out["workspace"]) == ws.resolve()
    for d in ("state", "sources", "inbox/pending", "inbox/done", "alignment", "site/data", "tools",
              "package/schemas", "package/toy-data", "package/tools", "package/assets"):
        assert (ws / d).is_dir(), d
    for src, dst in sf.SHIPPED:
        assert (ws / dst).read_bytes() == (sf.SKILL_DIR / src).read_bytes(), dst
    assert (ws / "package/tools/requirements.txt").read_text(encoding="utf-8") == sf.REQUIREMENTS
    proj = read_json(ws / "state/project.json")
    assert proj["schemify"] == 2 and proj["study"] == "LARK sleep study" and proj["slug"] == "lark-sleep-study"
    assert re.fullmatch(r"lark-sleep-study-[0-9a-f]{4}", proj["id"]) and out["id"] == proj["id"]
    assert (proj["mode"], proj["invoke"], proj["harness"]) == ("build", "$schemify", "codex")
    assert proj["idBase"] == "https://schemas.example.org/lark-sleep-study/"
    assert proj["preferences"] == {"batchSize": 8, "inferRules": "ask"}
    assert proj["tables"] == [] and proj["topics"] == []
    assert (ws / "state/ledger.jsonl").read_text(encoding="utf-8") == ""
    assert (ws / "state/variables.csv").read_text(encoding="utf-8") == "variable,table,topic,status,source,note\n"
    for f in ("index.html", "START-HERE.md", "site/data/state.js", "site/data/activity.js"):
        assert (ws / f).is_file(), f


def test_init_is_idempotent_and_restores_shipped_files(bare):
    project_before = (bare / "state/project.json").read_bytes()
    (bare / "site/app.js").unlink()
    (bare / "tools/serve.py").write_text("# edited by hand\n", encoding="utf-8")
    res = sf.init(str(bare), "Another name", None, None, None)
    assert res["ok"] is True and res["existing"] is True
    assert sorted(res["restored"]) == ["site/app.js", "tools/serve.py"]
    assert (bare / "site/app.js").read_bytes() == (sf.SKILL_DIR / "assets/site/app.js").read_bytes()
    assert (bare / "tools/serve.py").read_bytes() == (sf.SKILL_DIR / "scripts/serve.py").read_bytes()
    assert (bare / "state/project.json").read_bytes() == project_before       # the study keeps its name and id
    code, out = cli("init", "--study", "x", "--dir", bare)
    assert code == 0 and out["existing"] is True and out["restored"] == []


def test_init_refuses_a_folder_that_is_not_a_workspace(tmp_path):
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes/todo.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(sf.Fail, match="not a schemify workspace"):
        sf.init(str(tmp_path / "notes"), "LARK", None, None, None)
    code, out = cli("init", "--study", "LARK", "--dir", "notes", cwd=tmp_path)
    assert code == 1 and out["ok"] is False and "not a schemify workspace" in out["error"] and out["hint"]
    assert [p.name for p in (tmp_path / "notes").iterdir()] == ["todo.txt"]
    with pytest.raises(sf.Fail, match="needs --study"):
        sf.init(str(tmp_path / "fresh"), "  ", None, None, None)
    (tmp_path / "empty").mkdir()                       # an empty folder is fine
    assert sf.init(str(tmp_path / "empty"), "LARK", None, None, None)["existing"] is False


def test_init_refuses_a_path_inside_the_skill_directory(tmp_path):
    inside = sf.SKILL_DIR / "scripts" / "pytest-must-not-exist"
    with pytest.raises(sf.Fail, match="read-only"):
        sf.init(str(inside), "LARK", None, None, None)
    code, out = cli("init", "--study", "LARK", "--dir", sf.SKILL_DIR / "pytest-ws", cwd=tmp_path)
    assert code == 1 and "read-only" in out["error"]
    assert not inside.exists() and not (sf.SKILL_DIR / "pytest-ws").exists()


# ====================================================================== record

def test_record_accepts_every_event_type(ws):
    write_json(ws / "alignment/A01.json", {"containsData": False, "schemaChecks": []})
    recorded = sf.record_events(ws, [
        SRC_DOC,
        {"type": "source", "event": "extract", "id": "S02", "dir": "sources/S02/extract", "files": 4},
        {"type": "source", "event": "digest", "id": "S02", "path": "sources/S02/DIGEST.md", "variables": 0,
         "verified": ["p.2 Q4"]},
        {"type": "source", "event": "update", "id": "S02", "notes": "p.3 is a scan"},
        {"type": "source", "event": "retire", "id": "S02", "note": "replaced by the 2020 form"},
        SRC_WEB,
        {"type": "source", "event": "approve", "id": "S03", "by": "author", "note": "that is our paper"},
        {**SRC_WEB, "title": "Another cohort", "url": "https://example.org/other"},
        {"type": "source", "event": "reject", "id": "S04", "by": "steward"},
        question(),
        answer("D001", "b", via="chat"),
        guess(),
        confirm("D002", by="steward"),
        apply_("D002"),
        question(question="Is caffeine recorded?"),
        {"type": "decision", "event": "cancel", "id": "D003", "note": "the variable was dropped"},
        guess(question="Lower bound for total sleep?", choice="0"),
        guess(question="Lower bound for total sleep, revised?", choice="1"),
        {"type": "decision", "event": "supersede", "id": "D004", "replacement": "D005"},
        {**BASE_RULE, "gates": ["melatonin_use"], "targets": ["melatonin_dose"], "evidence": "documented",
         "status": "waiting", "waits_for": ["melatonin_use", "melatonin_dose"], "refs": ["S01:row 11"]},
        {"type": "rule", "event": "set", "id": "R002", "status": "deferred", "note": "the coding sheet is missing"},
        post(question(question="Is 0 a real nap length?")),
        {"type": "batch", "event": "withdraw", "id": "B01", "note": "moot"},
        {"type": "topic", "event": "present", "id": "participant", "note": "check the site codes"},
        {"type": "topic", "event": "changes", "id": "participant", "by": "author", "text": "Site 02 is Riverside"},
        {"type": "topic", "event": "approve", "id": "sleep", "by": "steward", "via": "chat"},
        {"type": "session", "event": "start", "mode": "build", "harness": "claude-code", "model": "test-model"},
        {"type": "session", "event": "end", "summary": "Drafted both topics.", "handoff": "Nothing odd.", "next": "done"},
        {"type": "alignment", "event": "add", "file": "alignment/A01.json", "label": "wave 1", "records": 10,
         "failing": 0, "checks": 0, "current": True},
        {"type": "alignment", "event": "triage", "id": "A01", "check": "k|const|f|/p|", "verdict": "data-issue",
         "decision": "D001", "note": "an export bug"},
        {"type": "milestone", "event": "reach", "id": "ready-for-review"},
    ])["recorded"]
    got = [(r["type"], r["event"], r["id"]) for r in recorded]
    session = got[27][2]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}#1", session)
    assert got == [
        ("source", "add", "S02"), ("source", "extract", "S02"), ("source", "digest", "S02"),
        ("source", "update", "S02"), ("source", "retire", "S02"), ("source", "add", "S03"),
        ("source", "approve", "S03"), ("source", "add", "S04"), ("source", "reject", "S04"),
        ("decision", "open", "D001"), ("decision", "answer", "D001"), ("decision", "decide", "D002"),
        ("decision", "confirm", "D002"), ("decision", "apply", "D002"), ("decision", "open", "D003"),
        ("decision", "cancel", "D003"), ("decision", "decide", "D004"), ("decision", "decide", "D005"),
        ("decision", "supersede", "D004"), ("rule", "add", "R002"), ("rule", "set", "R002"),
        ("decision", "open", "D006"), ("batch", "post", "B01"), ("batch", "withdraw", "B01"),
        ("topic", "present", "participant"), ("topic", "changes", "participant"), ("topic", "approve", "sleep"),
        ("session", "start", session), ("session", "end", session),
        ("alignment", "add", "A01"), ("alignment", "triage", "A01"), ("milestone", "reach", "ready-for-review"),
    ]
    w = sf.load_world(ws)
    s2, s3, s4 = w.sources["S02"], w.sources["S03"], w.sources["S04"]
    assert s2["status"] == "retired" and s2["extract"]["files"] == 4 and s2["digest"]["verified"] == ["p.2 Q4"]
    assert s2["notes"] == ["p.3 is a scan"] and s2["path"] == "sources/S02-diary-form.pdf"
    assert s3["status"] == "approved" and s3["verdict"]["by"] == "author" and s4["status"] == "rejected"
    assert {k: v["status"] for k, v in w.decisions.items()} == {
        "D001": "answered", "D002": "confirmed", "D003": "cancelled", "D004": "superseded",
        "D005": "provisional", "D006": "open"}
    assert w.decisions["D002"]["unapplied"] is False and w.decisions["D001"]["answer"]["via"] == "chat"
    assert w.rules["R002"]["status"] == "deferred" and w.rules["R002"]["note"] == "the coding sheet is missing"
    assert w.batches["B01"]["withdrawn"] is True and w.batches["B01"]["items"] == ["D006"]
    assert w.topics["participant"]["review"] == "changes-requested" and w.topics["sleep"]["review"] == "confirmed"
    assert w.open_session() is None and w.sessions[-1]["end"]["next"] == "done"
    assert w.alignment["A01"]["triage"]["k|const|f|/p|"]["verdict"] == "data-issue"
    assert "ready-for-review" in w.milestones
    for ev in ledger_events(ws):                  # `record` stamps every line; nothing private is stored
        assert ev["at"] and ev["by"] in ("agent", "author", "steward"), ev
        assert not any(k.startswith("_") or k == "ref" for k in ev), ev


def test_record_is_all_or_nothing(ws):
    before = ledger_bytes(ws)
    problems = refused(ws, question(), question(question=None),
                       {"type": "source", "event": "add", "kind": "web", "title": "t", "what": "w"})
    assert "event 2 (decision.open): missing 'question'" in problems
    assert "event 3 (source.add): a web source needs 'url'" in problems
    assert ledger_bytes(ws) == before
    code, out = cli("--ws", ws, "record", stdin=json.dumps([question(), question(question=None)]))
    assert code == 1 and out["ok"] is False and out["error"].startswith("Nothing recorded") and out["hint"]
    assert any("missing 'question'" in p for p in out["problems"])
    assert ledger_bytes(ws) == before
    assert sf.load_world(ws).decisions == {}


def test_record_assigns_ids(ws):
    assert rec(ws, question(), question(question="Second?"), question(question="Third?", id="new")) == \
        ["D001", "D002", "D003"]
    assert rec(ws, question(question="Fourth?")) == ["D004"]
    assert rec(ws, {**SRC_WEB, "id": "new"}) == ["S02"]                      # S01 exists already
    assert rec(ws, {**BASE_RULE, "evidence": "documented", "status": "encoded"}) == ["R002"]
    assert rec(ws, post("D001")) == ["B01"] and rec(ws, post("D002")) == ["B02"]
    assert rec(ws, {"type": "alignment", "event": "add", "file": "alignment/A01.json"}) == ["A01"]


def test_record_checks_explicit_ids(ws):
    assert "id S01 already exists" in refused(ws, {**SRC_WEB, "id": "S01"})
    assert "'Q7' is not a decision id" in refused(ws, question(id="Q7"))
    rule = {**BASE_RULE, "evidence": "documented", "status": "encoded"}
    assert rec(ws, {**rule, "id": "R007"}) == ["R007"]                         # a 1.x id carried over
    assert rec(ws, rule) == ["R008"]                                           # numbering continues after it
    assert "id R007 already exists" in refused(ws, {**rule, "id": "R007"})
    assert "'D001' does not exist" in refused(ws, apply_("D001"))


def test_record_resolves_local_labels(ws):
    rec(ws,
        {**SRC_DOC, "ref": "form"},                                                        # S02
        {**guess(), "ref": "g1", "evidence": [{"ref": "@form:p.3 Q7", "quote": "If no, skip to Q9"}]},  # D001
        {**guess(question="Upper bound for naps?", targets=["nap_minutes"], choice="600"), "ref": "g2"},  # D002
        guess(kind="rule", question="Do nights without a diary skip naps?", choice="yes", ref="why"),  # D003
        {"type": "decision", "event": "answer", "kind": "consent", "by": "author", "question": "May I infer it?",
         "choice": "other", "text": "Yes", "ref": "yes"},                                # D004
        {**BASE_RULE, "evidence": "inferred", "status": "deferred", "refs": ["@form:p.4"],
         "decision": "@why", "consent": "@yes"},                                         # R002
        {"type": "decision", "event": "open", "kind": "bulk", "topic": "sleep", "covers": ["@g1", "@g2"],
         "question": "I made 2 guesses — do they look right?", "options": BULK_OPTIONS, "recommended": "accept",
         "why": "They only reject impossible values.", "ref": "bulk"},                   # D005
        post("@bulk"),                                                                    # B01
        {**guess(question="Upper bound for naps, revised?", targets=["nap_minutes"], choice="540"), "ref": "new"},  # D006
        {"type": "decision", "event": "supersede", "id": "@g2", "replacement": "@new"},
        confirm("@g1"))
    w = sf.load_world(ws)
    assert w.sources["S02"]["title"] == "Diary form"
    assert w.decisions["D001"]["evidence"] == [{"ref": "S02:p.3 Q7", "quote": "If no, skip to Q9"}]
    assert w.rules["R002"]["refs"] == ["S02:p.4"]
    assert (w.rules["R002"]["decision"], w.rules["R002"]["consent"]) == ("D003", "D004")
    assert w.decisions["D005"]["covers"] == ["D001", "D002"] and w.batches["B01"]["items"] == ["D005"]
    assert w.decisions["D002"]["replacement"] == "D006"
    assert w.decisions["D001"]["status"] == "confirmed"
    assert not any("ref" in ev or "@" in json.dumps(ev) for ev in ledger_events(ws))


def test_record_refuses_unknown_labels(ws):
    assert "names no earlier event" in refused(ws, apply_("@nope"))
    assert "names no earlier event" in refused(ws, apply_("@later"), {**question(), "ref": "later"})
    assert "names no earlier event" in refused(
        ws, {**BASE_RULE, "evidence": "documented", "status": "encoded", "refs": ["@ghost:row 2"]})
    assert "is used twice" in refused(ws, {**question(), "ref": "q"}, {**question(question="Again?"), "ref": "q"})


def test_batch_post_turns_inline_items_into_decisions(ws):
    rec(ws, question())                                                                   # D001
    out = sf.record_events(ws, [
        post(question(question="Is 0 minutes a real nap?", ref="zero"), "D001", title="Sleep — 2 questions"),
        {**BASE_RULE, "evidence": "implied", "status": "waiting", "waits_for": ["sleep_minutes"], "decision": "@zero"},
    ])
    assert [(r["type"], r["event"], r["id"]) for r in out["recorded"]] == [
        ("decision", "open", "D002"), ("batch", "post", "B01"), ("rule", "add", "R002")]
    w = sf.load_world(ws)
    assert w.batches["B01"]["items"] == ["D002", "D001"] and w.batches["B01"]["title"] == "Sleep — 2 questions"
    assert w.decisions["D002"]["question"] == "Is 0 minutes a real nap?"
    for did in ("D001", "D002"):
        assert w.decisions[did]["status"] == "asked" and w.decisions[did]["askedTo"] == "author"
    assert w.rules["R002"]["decision"] == "D002"


def test_batch_post_refuses_settled_decisions(ws):
    rec(ws, question(), question(question="Moot?"), guess(), guess(question="Better bound?", choice="900"))
    rec(ws, answer("D001"), {"type": "decision", "event": "cancel", "id": "D002", "note": "moot"},
        {"type": "decision", "event": "supersede", "id": "D003", "replacement": "D004"})
    for did, status in (("D001", "answered"), ("D002", "cancelled"), ("D003", "superseded")):
        assert f"{did} is already {status}" in refused(ws, post(did))
    assert "'D099' is not a decision" in refused(ws, post("D099"))
    assert "to is 'author' or 'steward'" in refused(ws, post("D004", to="any"))
    assert rec(ws, post("D004", to="steward")) == ["B01"]              # a provisional decision goes up for review


@pytest.mark.parametrize("change, problem", [
    ({"options": [{"id": "a", "label": "Yes"}]}, "at least two options"),
    ({"recommended": "z"}, "recommended 'z' is not one of the option ids"),
    ({"recommended": None}, "carries 'recommended'"),
    ({"why": None}, "missing 'why'"),
    ({"options": OPTS + [{"id": "other", "label": "Something else"}]}, "built in"),
    ({"options": OPTS + [{"id": "unsure", "label": "Not sure"}]}, "built in"),
    ({"options": [{"id": "a", "label": "A"}, {"id": "a", "label": "B"}]}, "option ids must be unique"),
    ({"options": [{"id": "a"}, {"id": "b", "label": "B"}]}, "needs 'id' and 'label'"),
    ({"provisional": "z"}, "provisional 'z' is not one of the option ids"),
    ({"kind": "whim"}, "kind must be one of"),
    ({"topic": "smoking"}, "topic 'smoking' is not in project.json"),
    ({"table": "visits"}, "table 'visits' is not in project.json"),
    ({"input": "slider"}, "input must be choice, multi, or text"),
    ({"importance": "urgent"}, "importance is high, normal, or low"),
    ({"to": "everyone"}, "to is author, steward, or any"),
    ({"question": None}, "missing 'question'"),
    ({"targets": "nap_minutes"}, "targets is a list"),
    ({"evidence": [{"quote": "no ref"}]}, "evidence[0] must be"),
    ({"evidence": [{"ref": "row 9", "quote": "x"}]}, "is not a reference"),
    ({"evidence": [{"ref": "S09:row 9", "quote": "x"}]}, "source S09 is not registered"),
    ({"kind": "bulk"}, "lists the decisions it covers"),
    ({"kind": "bulk", "covers": ["D404"]}, "covers D404 does not exist"),
    ({"by": "robot"}, "'by' must be one of agent, author, steward"),
    ({"kind": "interview", "options": None, "recommended": None, "why": None}, "at least two options"),
    ({"topic": None, "targets": None}, "names its 'topic' or its 'targets'"),
    ({"provisional": None, "options": [{"id": "x", "label": "X"}, {"id": "y", "label": "Y"}], "recommended": "x"},
     "says which option the schemas encode meanwhile"),
    ({"kind": "conflict", "evidence": None}, "quotes its 'evidence'"),
    ({"kind": "consent", "covers": ["R404"]}, "covers R404 is not a rule"),
], ids=lambda v: str(v)[:40])
def test_questions_are_validated(ws, change, problem):
    assert problem in refused(ws, question(**change))


@pytest.mark.parametrize("change", [
    {"kind": "interview", "recommended": None, "why": None},
    {"kind": "knowledge", "recommended": None, "why": None},
    {"kind": "feedback", "recommended": None, "why": None},
    {"input": "text", "options": None, "recommended": None, "why": None},
    {"input": "multi", "options": OPTS + [{"id": "c", "label": "Weekends"}]},
    {"provisional": "a", "importance": "high", "to": "steward", "context": "The protocol is silent."},
], ids=lambda v: str(v)[:40])
def test_questions_that_need_no_recommendation(ws, change):
    assert rec(ws, question(**change)) == ["D001"]


@pytest.mark.parametrize("event", [
    {"type": "decision", "event": "answer", "id": "D001", "choice": "a"},
    {"type": "decision", "event": "answer", "id": "D001", "choice": "a", "by": "agent"},
    {"type": "decision", "event": "answer", "kind": "knowledge", "question": "Volunteered?", "choice": "other",
     "text": "Naps were self-reported."},
    {"type": "decision", "event": "confirm", "id": "D002"},
    {"type": "source", "event": "approve", "id": "S02", "by": "agent"},
    {"type": "source", "event": "reject", "id": "S02"},
    {"type": "topic", "event": "approve", "id": "sleep", "by": "agent"},
    {"type": "topic", "event": "changes", "id": "sleep", "text": "Split naps out."},
], ids=["answer", "answer-by-agent", "knowledge", "confirm", "source-approve", "source-reject", "topic-approve",
        "topic-changes"])
def test_person_only_events_refuse_the_agent(ws, event):
    rec(ws, question(), guess(), SRC_WEB)                                       # D001, D002, S02
    assert "only a person can do this" in refused(ws, event)
    assert rec(ws, {**event, "by": "steward"})                                  # the same from a person is fine


def test_decide_belongs_to_the_agent(ws):
    rec(ws, question())
    assert "'decide' is the agent's" in refused(ws, {"type": "decision", "event": "decide", "id": "D001",
                                                     "choice": "a", "why": "w", "by": "author"})
    assert "review is 'needed' or 'none'" in refused(ws, {"type": "decision", "event": "decide", "id": "D001",
                                                          "choice": "a", "why": "w", "review": "later"})
    assert "missing 'why'" in refused(ws, {"type": "decision", "event": "decide", "id": "D001", "choice": "a"})
    assert "an answer carries 'choice'" in refused(ws, answer("D001", None))


@pytest.mark.parametrize("fields, problem", [
    ({"evidence": "inferred", "status": "encoded", "decision": "D001"}, "encoded only with 'consent'"),
    ({"evidence": "told", "status": "encoded"}, "rule cites its 'decision'"),
    ({"evidence": "inferred", "status": "deferred"}, "rule cites its 'decision'"),
    ({"evidence": "documented", "status": "waiting"}, "names what it waits for in 'waits_for'"),
    ({"evidence": "documented", "status": "encoded", "gates": []}, "only a not-expressible rule may have none"),
    ({"evidence": "quoted", "status": "encoded"}, "evidence is one of"),
    ({"evidence": "documented", "status": "proposed"}, "status is one of"),
    ({"evidence": "documented", "status": "encoded", "table": "visits"}, "table 'visits' is not in project.json"),
    ({"evidence": "documented", "status": "encoded", "gates": "nap_yesterday"}, "gates is a list"),
    ({"evidence": "documented", "status": "encoded", "refs": ["S09:row 1"]}, "source S09 is not registered"),
    ({"evidence": "told", "status": "encoded", "decision": "D099"}, "decision D099 does not exist"),
    ({"evidence": "documented", "status": "encoded", "reading": None}, "missing 'reading'"),
], ids=lambda v: str(v)[:40])
def test_rules_are_validated(ws, fields, problem):
    rec(ws, guess(kind="rule", question="Is there a rule?", choice="yes"))           # D001
    assert problem in refused(ws, {k: v for k, v in {**BASE_RULE, **fields}.items() if v is not None})


@pytest.mark.parametrize("fields", [
    {"evidence": "implied", "status": "not-expressible", "gates": []},
    {"evidence": "inferred", "status": "suspected"},
    {"evidence": "inferred", "status": "encoded", "decision": "D001", "consent": "D002"},
    {"evidence": "told", "status": "encoded", "decision": "D002"},
    {"evidence": "documented", "status": "waiting", "waits_for": ["sleep_minutes"]},
], ids=lambda v: str(v)[:40])
def test_rules_that_are_licensed(ws, fields):
    rec(ws, guess(kind="rule", question="Is there a rule?", choice="yes"),
        {"type": "decision", "event": "answer", "kind": "consent", "by": "author", "question": "May I infer rules?",
         "choice": "other", "text": "Yes"})
    assert rec(ws, {**BASE_RULE, **fields}) == ["R002"]


def test_rule_set_rechecks_the_whole_rule(ws):
    rec(ws, {**BASE_RULE, "evidence": "inferred", "status": "suspected"})            # R002
    assert "missing 'note'" in refused(ws, {"type": "rule", "event": "set", "id": "R002", "status": "declined",
                                            "decision": "D001"})
    assert "rule cites its 'decision'" in refused(ws, {"type": "rule", "event": "set", "id": "R002",
                                                       "status": "declined", "note": "no"})
    rec(ws, guess(kind="rule", question="Is there a rule?", choice="yes"))           # D001
    assert "encoded only with 'consent'" in refused(ws, {"type": "rule", "event": "set", "id": "R002",
                                                         "status": "encoded", "decision": "D001", "note": "go"})
    rec(ws, {"type": "decision", "event": "answer", "kind": "consent", "by": "author", "question": "May I?",
             "choice": "other", "text": "Yes"})                                       # D002
    rec(ws, {"type": "rule", "event": "set", "id": "R002", "status": "encoded", "decision": "D001",
             "consent": "D002", "note": "the author said yes"})
    r = sf.load_world(ws).rules["R002"]
    assert (r["status"], r["consent"], r["note"], r["reading"]) == ("encoded", "D002", "the author said yes",
                                                                    BASE_RULE["reading"])
    assert "rule 'R099' does not exist" in refused(ws, {"type": "rule", "event": "set", "id": "R099",
                                                        "status": "declined", "note": "x"})


def test_only_question_evidence_may_cite_a_data_check_run(ws):
    write_json(ws / "alignment/A01.json", findings_doc("x"))
    rec(ws, {"type": "alignment", "event": "add", "file": "alignment/A01.json", "label": "wave 1"})
    align = {"options": [{"id": "clean", "label": "The data needs cleaning"}, {"id": "change", "label": "Change the schema"},
                         {"id": "accept", "label": "Known and accepted"}], "recommended": "clean", "provisional": "clean"}
    assert rec(ws, question(kind="alignment", evidence=[{"ref": "A01", "quote": "7 records carry -666 after a nap"}], **align))
    assert "option ids are clean, change, accept" in refused(ws, question(kind="alignment", provisional="a",
                                                                         evidence=[{"ref": "A01", "quote": "x"}]))
    assert "data-check run A09 does not exist" in refused(ws, question(evidence=[{"ref": "A09", "quote": "x"}]))
    assert "is not a reference" in refused(ws, {**BASE_RULE, "evidence": "documented", "status": "encoded",
                                                "refs": ["A01"]})
    assert "is not a reference" in refused(ws, {**BASE_RULE, "evidence": "told", "status": "encoded",
                                                "decision": "A01"})
    assert "is not a reference" in refused(ws, {"type": "alignment", "event": "triage", "id": "A01", "check": "k",
                                                "verdict": "question", "decision": "A01"})


@pytest.mark.parametrize("event, problem", [
    ({"type": "widget", "event": "add"}, "unknown type 'widget'"),
    ({"type": "source", "event": "frob", "id": "S01"}, "unknown source event"),
    ({"type": "source", "event": "add", "kind": "book", "title": "t", "what": "w"}, "kind must be 'document' or 'web'"),
    ({"type": "source", "event": "add", "kind": "document", "title": "t", "what": "w"}, "a document needs 'path'"),
    ({"type": "source", "event": "retire", "id": "S01"}, "missing 'note'"),
    ({"type": "decision", "event": "reopen", "id": "D001"}, "unknown decision event"),
    ({"type": "decision", "event": "apply", "id": "D001", "files": "x.json"}, "files is a list of paths"),
    ({"type": "rule", "event": "drop", "id": "R001"}, "unknown rule event"),
    ({"type": "batch", "event": "edit", "id": "B01"}, "unknown batch event"),
    ({"type": "topic", "event": "archive", "id": "sleep"}, "unknown topic event"),
    ({"type": "topic", "event": "present", "id": "smoking"}, "topic 'smoking' is not in project.json"),
    ({"type": "topic", "event": "changes", "id": "sleep", "by": "author"}, "missing 'text'"),
    ({"type": "session", "event": "pause"}, "unknown session event"),
    ({"type": "session", "event": "start", "mode": "audit"}, "mode is build or review"),
    ({"type": "session", "event": "end", "summary": "s", "next": "n"}, "no open session to end"),
    ({"type": "alignment", "event": "remove", "id": "A01"}, "unknown alignment event"),
    ({"type": "alignment", "event": "triage", "id": "A01", "check": "k", "verdict": "fine"}, "verdict is"),
    ({"type": "milestone", "event": "reach", "id": "done"}, "milestone"),
    ("not an object", "not a JSON object"),
], ids=lambda v: str(v)[:40])
def test_record_refuses_unknown_and_malformed_events(ws, event, problem):
    rec(ws, question())
    assert problem in refused(ws, event)


def test_record_cli_contract(ws, tmp_path):
    code, out = cli("--ws", ws, "record", stdin=json.dumps(question()))
    assert code == 0 and out == {"ok": True, "recorded": [{"type": "decision", "event": "open", "id": "D001"}]}
    payload = tmp_path / "events.json"
    payload.write_text(json.dumps([answer("D001", "b")]), encoding="utf-8")
    code, out = cli("--ws", ws, "record", "--file", payload)
    assert code == 0 and out["recorded"] == [{"type": "decision", "event": "answer", "id": "D001"}]
    for bad, error in (("{not json", "Not valid JSON"), ("", "No JSON received"), ("[]", "non-empty array"),
                       ('"text"', "non-empty array")):
        code, out = cli("--ws", ws, "record", stdin=bad)
        assert code == 1 and out["ok"] is False and error in out["error"] and out["hint"], bad


# ====================================================================== replay: decision status

def test_a_question_goes_open_asked_answered(ws):
    rec(ws, question())
    d = dec(ws, "D001")
    assert (d["status"], d["unapplied"], d["needsReview"]) == ("open", False, False)
    rec(ws, post("D001"))
    d = dec(ws, "D001")
    assert (d["status"], d["batch"], d["askedTo"]) == ("asked", "B01", "author")
    rec(ws, answer("D001", "b", note="The protocol has no cap."))
    d = dec(ws, "D001")
    assert d["status"] == "answered" and d["answer"]["choice"] == "b" and d["answer"]["by"] == "author"
    assert d["answer"]["note"] == "The protocol has no cap."
    assert d["unapplied"] is True and d["needsReview"] is False
    assert sf.status_payload(ws)["counts"]["decisions"] == {"open": 0, "asked": 0, "needsReview": 0, "unapplied": 1}


def test_a_guess_is_provisional_until_a_person_confirms_it(ws):
    rec(ws, guess(), guess(kind="convention", topic=None, targets=None, question="Which $id namespace?",
                           choice=BASE, why="A placeholder nothing fetches.", review="none"))
    d1, d2 = dec(ws, "D001"), dec(ws, "D002")
    assert (d1["status"], d1["needsReview"], d1["unapplied"], d1["reviewer"]) == ("provisional", True, True, "any")
    assert d2["needsReview"] is False                                        # mechanical: nothing to review
    rec(ws, confirm("D001", note="Fine by me."))
    d1 = dec(ws, "D001")
    assert d1["status"] == "confirmed" and d1["needsReview"] is False
    assert d1["confirmations"][0]["by"] == "author" and d1["confirmations"][0]["note"] == "Fine by me."


def test_a_new_decision_after_a_confirmation_needs_review_again(ws):
    rec(ws, guess())
    rec(ws, confirm("D001"))
    assert dec(ws, "D001")["status"] == "confirmed"
    rec(ws, {"type": "decision", "event": "decide", "id": "D001", "choice": "900",
             "why": "The steward's records stop at 15 hours."})
    d = dec(ws, "D001")
    assert d["agentDecision"]["choice"] == "900"
    assert (d["status"], d["needsReview"], d["unapplied"]) == ("provisional", True, True)


def test_not_sure_is_decided_on_the_persons_behalf(ws):
    rec(ws, question())
    rec(ws, post("D001"))
    rec(ws, answer("D001", "unsure"))
    d = dec(ws, "D001")
    assert (d["status"], d["unapplied"], d["reviewer"]) == ("unsure", True, "steward")
    nxt = {a["action"]: a for a in sf.status_payload(ws)["next"]}
    assert nxt["decide-on-behalf"]["ids"] == ["D001"] and "apply-decisions" not in nxt
    rec(ws, {"type": "decision", "event": "decide", "id": "D001", "choice": "a",
             "why": "The person was not sure; recommendation applied for now."})
    d = dec(ws, "D001")
    assert (d["status"], d["needsReview"], d["reviewer"], d["unapplied"]) == ("provisional", True, "steward", True)
    nxt = {a["action"]: a for a in sf.status_payload(ws)["next"]}
    assert "decide-on-behalf" not in nxt and nxt["apply-decisions"]["ids"] == ["D001"]
    rec(ws, apply_("D001"))
    assert dec(ws, "D001")["unapplied"] is False


def test_supersede_and_cancel_end_a_decision(ws):
    rec(ws, guess(), guess(question="Revised upper bound?", choice="900"), question())
    rec(ws, {"type": "decision", "event": "supersede", "id": "D001", "replacement": "D002"},
        {"type": "decision", "event": "cancel", "id": "D003", "note": "melatonin_use was dropped"})
    assert statuses(ws) == {"D001": "superseded", "D002": "provisional", "D003": "cancelled"}
    d1 = dec(ws, "D001")
    assert d1["replacement"] == "D002" and d1["unapplied"] is False and d1["needsReview"] is False
    assert "replacement D099 does not exist" in refused(
        ws, {"type": "decision", "event": "supersede", "id": "D002", "replacement": "D099"})
    assert "missing 'replacement'" in refused(ws, {"type": "decision", "event": "supersede", "id": "D002"})
    assert "missing 'note'" in refused(ws, {"type": "decision", "event": "cancel", "id": "D002"})


def test_applied_true_is_shorthand_for_an_apply(ws):
    rec(ws, {**guess(), "applied": True},
        {"type": "decision", "event": "answer", "kind": "knowledge", "by": "steward", "question": "Which sites?",
         "choice": "other", "text": "Sites 01–05", "targets": ["site_id"], "applied": True})
    for did, status in (("D001", "provisional"), ("D002", "answered")):
        d = dec(ws, did)
        assert d["status"] == status and d["unapplied"] is False and d["appliedAt"], did


def test_unapplied_is_cleared_by_apply_and_set_again_by_a_later_answer(ws):
    rec(ws, question())
    rec(ws, answer("D001", "a"))
    assert dec(ws, "D001")["unapplied"] is True
    rec(ws, apply_("D001", note="bound kept at 600"))
    d = dec(ws, "D001")
    assert d["unapplied"] is False and d["appliedFiles"] == ["package/schemas/" + SLEEP]
    rec(ws, answer("D001", "b", by="steward", note="The protocol has no cap."))
    d = dec(ws, "D001")
    assert (d["status"], d["answer"]["by"], d["unapplied"]) == ("answered", "steward", True)
    rec(ws, apply_("D001", note="cap removed"))
    assert dec(ws, "D001")["unapplied"] is False


def test_a_decision_that_only_explains_an_unencoded_rule_has_nothing_to_apply(ws):
    rec(ws, guess(kind="rule", targets=["nap_minutes"], question="Do nights without a diary skip the nap items?",
                  choice="yes", why="The morning diary was not filled in.", ref="why"),
        {**BASE_RULE, "evidence": "inferred", "status": "suspected", "decision": "@why"})
    d = dec(ws, "D001")
    assert (d["status"], d["needsReview"], d["unapplied"]) == ("provisional", True, False)
    rec(ws, {"type": "rule", "event": "set", "id": "R002", "status": "deferred", "note": "the author said not now"})
    assert dec(ws, "D001")["unapplied"] is False
    rec(ws, {"type": "decision", "event": "answer", "kind": "consent", "by": "author", "question": "Include it?",
             "choice": "other", "text": "Yes", "applied": True})                       # D002
    rec(ws, {"type": "rule", "event": "set", "id": "R002", "status": "encoded", "consent": "D002",
             "note": "the author said yes"})
    assert dec(ws, "D001")["unapplied"] is True                # once encoded, its decision must be applied


def test_withdrawing_a_batch_returns_its_questions(ws):
    rec(ws, post(question(), question(question="Second?")))
    assert statuses(ws) == {"D001": "asked", "D002": "asked"}
    rec(ws, {"type": "batch", "event": "withdraw", "id": "B01", "note": "superseded by the new plan"})
    assert statuses(ws) == {"D001": "open", "D002": "open"}
    assert rec(ws, post("D001", "D002")) == ["B02"] and statuses(ws) == {"D001": "asked", "D002": "asked"}
    assert "batch 'B09' does not exist" in refused(ws, {"type": "batch", "event": "withdraw", "id": "B09"})


# ====================================================================== status: what to do next

def test_next_on_a_fresh_workspace(bare):
    assert next_actions(bare) == ["add-sources"]
    submit(bare, [{"kind": "note", "text": "hello"}])
    assert next_actions(bare) == ["process-inbox", "add-sources"]


def test_next_actions_are_ranked(ws):
    submit(ws, [{"kind": "note", "text": "hello"}])                                           # process-inbox
    rec(ws, question(question="Unsure one?"), question(question="Answered one?"))
    rec(ws, answer("D001", "unsure"), answer("D002", "a"))                                    # decide-on-behalf, apply
    rec(ws, SRC_DOC)                                                                          # discover
    edit_project(ws, lambda p: p.update(people=[{"role": "author", "name": "", "profile": "", "knows": []}]))
    stub_checks(ws, tested=["participant"])                                   # present participant, build sleep
    rec(ws, {**BASE_RULE, "gates": ["sleep_minutes"], "targets": ["nap_yesterday"], "evidence": "documented",
             "status": "waiting", "waits_for": ["nap_yesterday"]})                            # R002 encode-rules
    rec(ws, {**BASE_RULE, "evidence": "inferred", "status": "suspected"})                     # R003 ask-consent
    rec(ws, question(question="Open one?"))                                                   # D003 post-questions
    write_json(ws / "alignment/A01.json", findings_doc("0" * 16))
    rec(ws, {"type": "alignment", "event": "add", "file": "alignment/A01.json", "label": "wave 1"})  # triage
    nxt = sf.status_payload(ws)["next"]
    assert [a["action"] for a in nxt] == [
        "process-inbox", "decide-on-behalf", "apply-decisions", "discover", "interview", "build-topic",
        "triage-alignment", "present-topic", "encode-rules", "ask-consent", "post-questions"]
    by = {a["action"]: a for a in nxt}
    assert by["decide-on-behalf"]["ids"] == ["D001"] and by["apply-decisions"]["ids"] == ["D002"]
    assert by["discover"]["ids"] == ["S02"]
    assert by["build-topic"]["topic"] == "sleep" and by["present-topic"]["topic"] == "participant"
    assert by["encode-rules"]["ids"] == ["R002"] and by["ask-consent"]["ids"] == ["R003"]
    assert by["post-questions"]["ids"] == ["D003"] and by["triage-alignment"]["ids"] == ["A01"]
    assert all(a["why"] and a["read"].endswith(".md") for a in nxt)


def test_next_plan_comes_before_any_topic_work(ws):
    edit_project(ws, lambda p: p.update(tables=[], topics=[]))
    rec(ws, question(topic=None))
    assert next_actions(ws) == ["plan"]


def test_next_revise_topic_on_requested_changes(ws):
    rec(ws, {"type": "topic", "event": "changes", "id": "participant", "by": "author", "text": "Rename site 02."})
    nxt = sf.status_payload(ws)["next"]
    assert [(a["action"], a["topic"]) for a in nxt] == [("revise-topic", "participant"), ("build-topic", "sleep")]


def test_next_skip_audit_then_finish(ws):
    rec(ws, *[{"type": "topic", "event": "approve", "id": t, "by": "author"} for t in ("participant", "sleep")])
    assert next_actions(ws) == ["finish"]
    rec(ws, {**BASE_RULE, "gates": ["melatonin_use"], "evidence": "documented", "status": "waiting",
             "waits_for": ["melatonin_use"]})
    assert next_actions(ws) == ["skip-audit"]
    rec(ws, {"type": "rule", "event": "set", "id": "R002", "status": "not-expressible",
             "note": "melatonin_use is never delivered"})
    assert next_actions(ws) == ["finish"]
    rec(ws, {"type": "milestone", "event": "reach", "id": "finished"})
    assert next_actions(ws) == [] and sf.status_payload(ws)["phase"] == "Finished"
    edit(ws, DEFS, lambda d: d["$defs"]["dont_know"].update(description="Said they did not know"))
    nxt = sf.status_payload(ws)["next"]                                  # nothing is ever final: finish again
    assert [(a["action"], a["why"]) for a in nxt] == [("finish", "the schemas changed since you finished — finish again")]
    assert sf.status_payload(ws)["phase"] == "Finish"
    edit(ws, PARTICIPANT, lambda d: d["properties"]["age"].update(description="Age in whole years"))
    assert "finish" not in next_actions(ws)                              # a changed topic goes back to the person first


def test_next_wait_when_only_people_are_needed(ws):
    rec(ws, *[{"type": "topic", "event": "present", "id": t} for t in ("participant", "sleep")])
    rec(ws, post(question()))
    nxt = sf.status_payload(ws)["next"]
    assert len(nxt) == 1 and nxt[0]["action"] == "wait"
    assert nxt[0]["batches"] == ["B01"] and nxt[0]["topics"] == ["participant", "sleep"]


def test_next_finish_waits_for_the_persons_own_questions(ws):
    rec(ws, *[{"type": "topic", "event": "approve", "id": t, "by": "author"} for t in ("participant", "sleep")])
    rec(ws, post(question()))                                            # B01 waits on the author
    rec(ws, question(question="Who collected the data, and when?"))      # D002 goes out with their next batch
    nxt = sf.status_payload(ws)["next"]
    assert [a["action"] for a in nxt] == ["post-questions", "wait"] and nxt[1]["batches"] == ["B01"]
    assert sf.status_payload(ws)["phase"] == "Finish"                   # the current step, not "the work is done"
    # questions for a steward who is someone else may stay open through the finish (Ending A)
    edit_project(ws, lambda p: p.update(people=[
        {"role": "author", "name": "", "profile": "limited", "knows": []},
        {"role": "steward", "name": "Dr. R. Osei", "knows": ["every release"]}]))
    rec(ws, {"type": "batch", "event": "withdraw", "id": "B01"}, post("D001", "D002", to="steward"))
    assert next_actions(ws) == ["finish"]
    # ...but not when the author is the steward
    edit_project(ws, lambda p: p["people"][0].update(name="Dr. R. Osei", profile="steward"))
    assert next_actions(ws) == ["wait"]


def test_next_in_review_mode(ws):
    edit_project(ws, lambda p: p.update(mode="review"))
    submit(ws, [{"kind": "note", "text": "hello"}])
    rec(ws, question())
    assert next_actions(ws) == ["process-inbox", "review"]
    rec(ws, {"type": "milestone", "event": "reach", "id": "review-complete"})
    assert "review" not in next_actions(ws)


def test_status_cli_reads_everything_and_writes_nothing(ws):
    rec(ws, {"type": "session", "event": "start"},
        {"type": "session", "event": "end", "summary": "Drafted.", "handoff": "Watch the CSV quoting.",
         "next": "draft sleep"})
    before = snapshot(ws)
    code, out = cli("--ws", ws, "status")
    assert code == 0 and out["ok"] is True
    for key in ("workspace", "study", "mode", "website", "phase", "counts", "topics", "checks", "lastSession", "next"):
        assert key in out, key
    assert out["lastSession"]["handoff"] == "Watch the CSV quoting." and out["lastSession"]["next"] == "draft sleep"
    assert out["phase"] == "Build topic by topic" and out["websiteServed"] is False
    assert out["counts"]["rules"] == {"encoded": 1} and out["counts"]["sources"]["documents"] == 1
    assert out["topics"]["total"] == 2 and out["checks"] is None
    assert snapshot(ws) == before


# ====================================================================== topics

def test_topic_status_is_derived_from_files_checks_and_reviews(ws):
    edit_project(ws, lambda p: p["topics"].append(
        {"id": "naps", "title": "Naps", "table": "sleep_diary", "file": "sleep_diary/categories/naps.json"}))

    def topic_status():
        return {t["id"]: t["status"] for t in sf.status_payload(ws)["topics"]["items"]}

    assert topic_status() == {"participant": "drafted", "sleep": "drafted", "naps": "planned"}
    stub_checks(ws, tested=["sleep"])
    assert topic_status()["sleep"] == "tested"
    stub_checks(ws, tested=["sleep"], errors=1)
    assert topic_status()["sleep"] == "drafted"
    stub_checks(ws, tested=["sleep"])
    rec(ws, {"type": "topic", "event": "present", "id": "sleep", "note": "the bounds"})
    assert topic_status()["sleep"] == "in-review"
    rec(ws, {"type": "topic", "event": "changes", "id": "sleep", "by": "author", "text": "960 is too low."})
    assert topic_status()["sleep"] == "changes-requested"
    rec(ws, {"type": "topic", "event": "present", "id": "sleep"})
    assert topic_status()["sleep"] == "in-review"
    rec(ws, {"type": "topic", "event": "approve", "id": "sleep", "by": "author"})
    assert topic_status()["sleep"] == "confirmed"
    rec(ws, {"type": "topic", "event": "present", "id": "naps"})
    assert topic_status()["naps"] == "planned"                 # a review event cannot skip the drafting


# ====================================================================== queue

def test_queue_shows_each_person_their_own_items(ws):
    rec(ws, question(question="Only the author knows?", to="author"),
        question(question="Anyone?"),
        question(question="Escalated?", kind="conflict"))
    rec(ws, answer("D003", "unsure"))
    rec(ws, {"type": "decision", "event": "decide", "id": "D003", "choice": "a", "why": "The author was not sure."})
    assert [i["id"] for i in sf.queue_items(ws, "author", None, 20)["items"]] == ["D001", "D002"]
    assert [i["id"] for i in sf.queue_items(ws, "steward", None, 20)["items"]] == ["D003", "D002"]


def test_queue_ranks_conflicts_and_not_sure_first_and_groups_guesses(ws):
    rec(ws,
        question(kind="gap", question="Gap?"),                                                   # D001: 5+3
        question(kind="conflict", question="Conflict?"),                                         # D002: 5+5
        question(kind="gap", question="Escalated?"),                                             # D003: 2+6+3
        guess(question="Bound A?"),                                                              # D004 bulk
        guess(question="Bound B?", importance="low"),                                            # D005 bulk
        guess(question="Bound C?", importance="high", topic="participant", targets=["age"]),     # D006: 2+3
        guess(question="Bound D?", topic="participant", targets=["age"]),                        # D007 bulk
        question(question="Posted?"),                                                            # D008 asked
        question(question="Answered?"))                                                          # D009 answered
    rec(ws, answer("D003", "unsure"), answer("D009", "a"), post("D008"))
    rec(ws, {"type": "decision", "event": "decide", "id": "D003", "choice": "a", "why": "The author was not sure."})
    q = sf.queue_items(ws, "steward", None, 20)
    assert [(i["id"], i["score"]) for i in q["items"]] == [("D003", 11), ("D002", 10), ("D001", 8), ("D006", 5)]
    assert "the author was not sure" in q["items"][0]["why"]
    assert q["bulkGuesses"] == [{"topic": "participant", "decisions": ["D007"], "count": 1},
                                {"topic": "sleep", "decisions": ["D004", "D005"], "count": 2}]
    assert (q["total"], q["truncated"], q["for"]) == (4, False, "steward")
    q = sf.queue_items(ws, "steward", None, 2)
    assert len(q["items"]) == 2 and q["truncated"] is True and q["total"] == 4
    q = sf.queue_items(ws, "steward", "participant", 20)
    assert [i["id"] for i in q["items"]] == ["D006"] and [b["topic"] for b in q["bulkGuesses"]] == ["participant"]
    code, out = cli("--ws", ws, "queue", "--for", "steward", "--limit", "3")
    assert code == 0 and [i["id"] for i in out["items"]] == ["D003", "D002", "D001"]


def test_queue_lists_suspected_rules_nobody_was_asked_about(ws):
    rec(ws, {**BASE_RULE, "evidence": "inferred", "status": "suspected"},
        {**BASE_RULE, "gates": ["sleep_minutes"], "targets": ["nap_yesterday"], "evidence": "inferred",
         "status": "suspected"})
    assert sf.queue_items(ws, "steward", None, 20)["suspectedRulesUnasked"] == ["R002", "R003"]
    rec(ws, question(kind="consent", question="I think one skip pattern exists that no document states (R002). "
                                              "Should I include it?",
                     options=[{"id": "yes", "label": "Yes"}, {"id": "later", "label": "Not now"},
                              {"id": "no", "label": "No"}], recommended="yes", provisional="later"))
    assert sf.queue_items(ws, "steward", None, 20)["suspectedRulesUnasked"] == ["R002", "R003"]   # not yet asked
    rec(ws, post("D001"))
    assert sf.queue_items(ws, "steward", None, 20)["suspectedRulesUnasked"] == ["R003"]
    assert [a["ids"] for a in sf.status_payload(ws)["next"] if a["action"] == "ask-consent"] == [["R003"]]
    rec(ws, post(question(kind="consent", covers=["R003"], targets=["sleep_minutes", "nap_yesterday"],
                          question="Your documents don't say so, but I think one more skip pattern exists. "
                                   "Should I include it?",
                          context="When there is no diary entry, the nap questions were not asked either.",
                          options=[{"id": "yes", "label": "Yes"}, {"id": "later", "label": "Not now"},
                                   {"id": "no", "label": "No"}], recommended="later", provisional="later")))
    assert sf.queue_items(ws, "steward", None, 20)["suspectedRulesUnasked"] == []       # `covers` names R003
    assert "ask-consent" not in next_actions(ws)


def test_inline_batch_items_take_the_batch_addressee(ws):
    rec(ws, post(question(), question(question="For anyone?", to="any"), to="steward"))
    world = sf.load_world(ws)
    assert world.decisions["D001"]["to"] == "steward" and world.decisions["D002"]["to"] == "any"


def test_labels_are_resolved_inside_notes(ws):
    rec(ws, question())
    rec(ws, {**question(question="Follow-up?"), "ref": "q"},
        {"type": "decision", "event": "apply", "id": "D001", "files": [], "note": "asked as @q; mail me at a@b.org"})
    hist = sf.load_world(ws).decisions["D001"]
    notes = [h.get("note") for h in hist.get("history", []) if h.get("event") == "apply"]
    assert notes == ["asked as D002; mail me at a@b.org"]


def test_answers_and_decisions_must_name_an_option(ws):
    rec(ws, question())
    assert "choice 'c' is not one of" in refused(ws, {"type": "decision", "event": "answer", "id": "D001", "by": "author",
                                                       "choice": "c"})
    assert "is not one of the question's options" in refused(ws, {"type": "decision", "event": "decide", "id": "D001",
                                                                   "choice": "c", "why": "typo"})
    assert rec(ws, {"type": "decision", "event": "answer", "id": "D001", "by": "author", "choice": "other",
                    "text": "Nine hours"}) == ["D001"]


# ====================================================================== inbox

def test_inbox_list(ws):
    assert sf.inbox_list(ws) == {"ok": True, "pending": [], "total": 0, "next": "Nothing waiting."}
    a = submit(ws, [{"kind": "note", "text": "a"}, {"kind": "note", "text": "b"},
                    {"kind": "confirm", "decision": "D001"}], sub="20260102T030405Z-aaaaaa")
    b = submit(ws, [{"kind": "topic", "topic": "sleep", "verdict": "approve"}], sub="20260103T000000Z-bbbbbb",
               frm="steward")
    out = sf.inbox_list(ws)
    assert [p["id"] for p in out["pending"]] == [a, b] and out["total"] == 2 and "inbox take" in out["next"]
    assert out["pending"][0]["items"] == {"note": 2, "confirm": 1}
    assert out["pending"][0]["receivedAt"] == "2026-01-02T03:04:05Z" and out["pending"][1]["from"] == "steward"


def test_take_records_answers_of_every_input_kind(ws):
    rec(ws, question(),
        question(question="Which nights were diaries kept?", input="multi",
                 options=OPTS + [{"id": "c", "label": "Weekends"}]),
        question(question="What did the 2019 wave use?", input="text", options=None, recommended=None, why=None))
    rec(ws, post("D001", "D002", "D003"))
    sub = submit(ws, [{"kind": "answer", "decision": "D001", "choice": "b", "note": "from the protocol"},
                      {"kind": "answer", "decision": "D002", "choices": ["a", "c"]},
                      {"kind": "answer", "decision": "D003", "text": "Paper diaries"}])
    out = sf.take_submission(ws, sub)
    assert out["ok"] is True and out["submission"] == sub and out["from"] == "author" and out["unhandled"] == []
    assert out["recorded"] == [{"type": "decision", "event": "answer", "id": d} for d in ("D001", "D002", "D003")]
    w = sf.load_world(ws)
    a1, a2, a3 = (w.decisions[d]["answer"] for d in ("D001", "D002", "D003"))
    assert (a1["choice"], a1["note"], a1["by"], a1["via"]) == ("b", "from the protocol", "author", f"inbox:{sub}")
    assert a2["choices"] == ["a", "c"]
    assert (a3["choice"], a3["text"]) == ("other", "Paper diaries")
    assert all(w.decisions[d]["status"] == "answered" for d in ("D001", "D002", "D003"))
    todo = {t["decision"]: t for t in out["todo"]}
    assert sorted(todo) == ["D001", "D002", "D003"] and out["todoTotal"] == 3
    assert todo["D001"]["answer"] == "No upper bound" and todo["D001"]["note"] == "from the protocol"
    assert todo["D002"]["answer"] == "Keep 0–600; Weekends"
    assert todo["D003"]["answer"] == "Paper diaries"
    assert all("record `apply`" in t["do"] for t in out["todo"])


def test_take_turns_not_sure_into_a_decision_to_make(ws):
    rec(ws, question())
    rec(ws, post("D001"))
    out = sf.take_submission(ws, submit(ws, [{"kind": "answer", "decision": "D001", "choice": "unsure"}],
                                        frm="steward"))
    assert out["from"] == "steward"
    assert [t["decision"] for t in out["todo"]] == ["D001"] and "record a `decide`" in out["todo"][0]["do"]
    d = dec(ws, "D001")
    assert (d["status"], d["reviewer"], d["answer"]["by"]) == ("unsure", "steward", "steward")


def test_take_records_a_confirmation(ws):
    rec(ws, guess())
    rec(ws, post("D001", to="steward"))
    sub = submit(ws, [{"kind": "confirm", "decision": "D001", "note": "matches the cleaning code"}], frm="steward")
    out = sf.take_submission(ws, sub)
    assert out["recorded"] == [{"type": "decision", "event": "confirm", "id": "D001"}]
    d = dec(ws, "D001")
    assert d["status"] == "confirmed" and d["needsReview"] is False
    assert {k: d["confirmations"][0][k] for k in ("by", "via", "note")} == \
        {"by": "steward", "via": f"inbox:{sub}", "note": "matches the cleaning code"}


def test_take_turns_comments_and_notes_into_feedback(ws):
    sub = submit(ws, [
        {"kind": "comment", "target": {"type": "variable", "table": "sleep_diary", "name": "nap_minutes"},
         "tags": ["Wrong code"], "text": "-666 was never used for naps."},
        {"kind": "comment", "target": {"type": "rule", "id": "R001"}, "tags": ["Looks right"], "text": ""},
        {"kind": "comment", "target": {"type": "topic", "id": "participant"}, "tags": [],
         "text": "Add the enrolment date."},
        {"kind": "note", "text": "  The 2019 wave used paper diaries.  "},
    ])
    out = sf.take_submission(ws, sub)
    assert [(r["event"], r["id"]) for r in out["recorded"]] == [("answer", f"D00{n}") for n in range(1, 5)]
    w = sf.load_world(ws)
    d1 = w.decisions["D001"]
    assert (d1["kind"], d1["status"], d1["targets"], d1["topic"], d1["table"]) == \
        ("feedback", "answered", ["nap_minutes"], "sleep", "sleep_diary")
    assert d1["question"] == "Comment on variable nap_minutes (table sleep_diary)"
    assert d1["answer"]["text"] == "[Wrong code] -666 was never used for naps."
    assert (d1["answer"]["by"], d1["answer"]["via"], d1["answer"]["choice"]) == ("author", f"inbox:{sub}", "other")
    assert w.decisions["D002"]["context"] == "About rule R001."
    assert w.decisions["D002"]["answer"]["text"].startswith("[Looks right]")
    assert w.decisions["D003"]["topic"] == "participant"
    d4 = w.decisions["D004"]
    assert d4["question"] == "Note from the author" and d4["answer"]["text"] == "The 2019 wave used paper diaries."
    assert [t["decision"] for t in out["todo"]] == ["D001", "D002", "D003", "D004"]
    assert all(t["kind"] == "feedback" and "follow-up question" in t["do"] for t in out["todo"])


def test_take_records_topic_and_source_verdicts(ws):
    rec(ws, SRC_WEB, {**SRC_WEB, "title": "Another cohort", "url": "https://example.org/other"})   # S02, S03
    sub = submit(ws, [
        {"kind": "topic", "topic": "participant", "verdict": "approve", "text": "All good."},
        {"kind": "topic", "topic": "sleep", "verdict": "changes", "text": "Split naps into their own topic."},
        {"kind": "source", "source": "S02", "verdict": "approve"},
        {"kind": "source", "source": "S03", "verdict": "reject", "note": "A different cohort."},
    ], frm="steward")
    out = sf.take_submission(ws, sub)
    assert [(r["type"], r["event"], r["id"]) for r in out["recorded"]] == [
        ("topic", "approve", "participant"), ("topic", "changes", "sleep"),
        ("source", "approve", "S02"), ("source", "reject", "S03")]
    w = sf.load_world(ws)
    assert {k: w.topics["participant"]["approvals"][0][k] for k in ("by", "via", "note")} == \
        {"by": "steward", "via": f"inbox:{sub}", "note": "All good."}
    assert w.topics["sleep"]["changes"][0]["text"] == "Split naps into their own topic."
    assert w.sources["S02"]["status"] == "approved" and w.sources["S03"]["status"] == "rejected"
    assert w.sources["S03"]["verdict"]["note"] == "A different cohort."
    assert {t["id"]: t["status"] for t in sf.status_payload(ws)["topics"]["items"]} == \
        {"participant": "confirmed", "sleep": "changes-requested"}
    assert len(out["todo"]) == 1 and out["todo"][0]["topic"] == "sleep" and "revise" in out["todo"][0]["do"]
    sub2 = submit(ws, [{"kind": "topic", "topic": "participant", "verdict": "changes"}],
                  sub="20260102T030406Z-b2c3d4")
    sf.take_submission(ws, sub2)
    assert sf.load_world(ws).topics["participant"]["changes"][0]["text"] == "(no details given)"


FAKE_QUAC = """
import json, os, shutil, sys
args = sys.argv[1:]
print("SECRET-CELL-VALUE on stdout"); print("SECRET-CELL-VALUE on stderr", file=sys.stderr)
code = int(os.environ.get("FAKE_QUAC_EXIT", "0"))
if code == 0:
    shutil.copy(os.environ["FAKE_QUAC_FINDINGS"], args[args.index("--findings") + 1])
    with open(os.environ["FAKE_QUAC_ARGS"], "w") as f:
        json.dump(args, f)
sys.exit(code)
"""


def allow(**kw) -> dict:
    ev = {"type": "dataset", "event": "allow", "path": "data/export.csv", "label": "Public export", "basis": "public",
          "by": "author", "via": "chat", "text": "It is the public-use file; check it yourself."}
    ev.update(kw)
    return {k: v for k, v in ev.items() if v is not None}


@pytest.fixture
def quac(ws, tmp_path, monkeypatch):
    """A stand-in for QuaC's command line that prints a secret, writes findings, and records its arguments."""
    script = tmp_path / "fake_quac.py"
    script.write_text(FAKE_QUAC, encoding="utf-8")
    findings = tmp_path / "findings.json"
    doc = findings_doc(sf.quac_set_id(ws / "package" / "schemas"))
    doc["dataset"] = {"name": "export.csv", "format": "csv", "records": 120}
    doc["schemaChecks"].append({"severity": "error", "level": "variable", "variable": "shoe_size",
                                "ruleId": "schema:column:shoe_size:unexpected", "keyword": "unevaluatedProperties",
                                "records": None, "location": {"file": MOTHER, "pointer": "/items/unevaluatedProperties"}})
    write_json(findings, doc)
    monkeypatch.setenv("SCHEMIFY_QUAC", f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}")
    monkeypatch.setenv("FAKE_QUAC_FINDINGS", str(findings))
    monkeypatch.setenv("FAKE_QUAC_ARGS", str(tmp_path / "quac-args.json"))
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "export.csv").write_text("participant_id,age\nP0001,SECRET-CELL-VALUE\n", encoding="utf-8")
    rec(ws, {"type": "session", "event": "start", "harness": "opencode", "model": "qwen3-coder"})
    return tmp_path


def test_dataset_allow_needs_a_person_a_basis_and_their_words(ws):
    problems = refused(ws, allow(by="agent"), allow(basis="internal"), allow(text=None), allow(path="schemify/state/x.csv"))
    assert "only a person can do this" in problems and "basis is 'public'" in problems
    assert "missing 'text'" in problems and "inside the workspace" in problems
    assert "covers one model" in refused(ws, allow(basis="local-model"))          # no session names a model yet
    rec(ws, {"type": "session", "event": "start", "harness": "opencode", "model": "qwen3-coder"})
    rec(ws, allow(basis="local-model"), allow())
    w = sf.load_world(ws)
    assert (w.datasets["X01"]["model"], w.datasets["X02"].get("model")) == ("qwen3-coder", None)
    assert sf.status_payload(ws)["counts"]["datasets"] == 2
    rec(ws, {"type": "dataset", "event": "withdraw", "id": "X01", "by": "author", "via": "chat"})
    assert sf.status_payload(ws)["counts"]["datasets"] == 1
    assert "dataset 'X09' does not exist" in refused(ws, {"type": "dataset", "event": "withdraw", "id": "X09", "by": "author"})


def test_data_check_imports_findings_without_ever_showing_quac_output(ws, quac, capfd):
    rec(ws, allow())
    out = sf.run_data_check(ws, "X01")
    assert (out["run"], out["dataset"], out["label"], out["records"], out["current"]) == ("A01", "X01", "Public export", 120, True)
    assert out["checksFailing"] == 3 and out["notBuiltYet"] == 0
    assert "SECRET" not in capfd.readouterr().out + capfd.readouterr().err
    stored = read_json(ws / "alignment/A01.json")
    assert stored["dataset"]["name"] == "Public export"                      # the person's label, never the file name
    args = read_json(quac / "quac-args.json")
    assert args[0] == str((quac / "data" / "export.csv").resolve()) and "--no-report" in args and "--index" not in args
    a = sf.load_world(ws).alignment["A01"]
    assert (a["by"], a["via"], a["dataset"]) == ("agent", "data-check:X01", "X01")
    shown = sf.show_items(ws, ["A01", "X01"])["items"]
    assert shown["A01"]["askTo"] == "author" and shown["X01"]["runs"] == ["A01"]


def test_data_check_failure_hides_quac_messages_and_hands_over_the_command(ws, quac, monkeypatch):
    rec(ws, allow())
    monkeypatch.setenv("FAKE_QUAC_EXIT", "2")
    with pytest.raises(sf.Fail) as ei:
        sf.run_data_check(ws, "X01")
    text = json.dumps({"error": ei.value.error, "hint": ei.value.hint, **ei.value.extra})
    assert "could not read the dataset" in ei.value.error and "SECRET" not in text
    assert ei.value.extra["command"].startswith("npx --yes @jeyabbalas/quac@") and "export.csv" in ei.value.extra["command"]
    assert not list((ws / "alignment").glob("*.json"))                       # nothing imported


def test_data_check_refuses_what_no_person_allowed(ws, quac):
    with pytest.raises(sf.Fail, match="not a dataset a person allowed"):
        sf.run_data_check(ws, "X01")
    rec(ws, allow(basis="local-model"), allow(path="data/missing.csv"))
    rec(ws, {"type": "session", "event": "end", "summary": "s", "next": "n"},
        {"type": "session", "event": "start", "harness": "claude-code", "model": "claude-opus-5-5"})
    with pytest.raises(sf.Fail, match="allowed for an agent on qwen3-coder; this session runs on claude-opus-5-5"):
        sf.run_data_check(ws, "X01")
    with pytest.raises(sf.Fail, match="is not at data/missing.csv"):
        sf.run_data_check(ws, "X02")
    rec(ws, {"type": "dataset", "event": "withdraw", "id": "X02", "by": "steward", "via": "chat"})
    with pytest.raises(sf.Fail, match="withdrawn by the steward"):
        sf.run_data_check(ws, "X02")


def validated(ws: Path, ok=True) -> None:
    """What `build` leaves when the validator ran on the current schema files."""
    write_json(ws / "state" / "checks.json", {"ok": ok, "ran": True, "headline": "stub",
                                              "setId": sf.quac_set_id(ws / "package" / "schemas")})


def test_next_runs_an_allowed_check_whenever_the_schemas_change(ws, quac):
    rec(ws, *[{"type": "topic", "event": "present", "id": t} for t in ("participant", "sleep")])
    validated(ws)
    rec(ws, allow())                                                          # the ledger moved; the schemas did not
    assert next_actions(ws)[:1] == ["run-data-check"]
    sf.run_data_check(ws, "X01")
    assert "run-data-check" not in next_actions(ws) and "triage-alignment" in next_actions(ws)
    keys = [c["key"] for c in sf.show_items(ws, ["A01"])["items"]["A01"]["checks"]]
    rec(ws, question(kind="alignment", ref="q", question="Ages above 90?", options=[
            {"id": "clean", "label": "Fix the data"}, {"id": "change", "label": "Change the schema"},
            {"id": "accept", "label": "Known"}], recommended="clean", provisional="clean",
            evidence=[{"ref": "A01", "quote": "age: at most 90 — 2 records"}]),
        *[{"type": "alignment", "event": "triage", "id": "A01", "check": k, "verdict": "question", "decision": "@q"}
          for k in keys])
    edit(ws, SLEEP, lambda d: d["properties"]["sleep_minutes"]["anyOf"][0].update(maximum=900))   # your own slip, fixed
    assert "run-data-check" not in next_actions(ws)                           # not before these files pass the validator
    validated(ws)
    assert next_actions(ws)[:2] == ["run-data-check", "post-questions"]      # re-run before asking: fresh counts
    sf.run_data_check(ws, "X01")
    rec(ws, *[{"type": "alignment", "event": "triage", "id": "A02", "check": k, "verdict": "question", "decision": "D001"}
              for k in keys], post("D001"))
    edit(ws, PARTICIPANT, lambda d: d["properties"]["age"]["anyOf"][0].update(maximum=95))
    validated(ws)
    assert "run-data-check" not in next_actions(ws)                           # its question is with a person now
    rec(ws, answer("D001", choice="change"),
        {"type": "decision", "event": "apply", "id": "D001", "files": [f"package/schemas/{PARTICIPANT}"]})
    assert next_actions(ws)[:1] == ["run-data-check"]
    validated(ws, ok=False)
    assert "run-data-check" not in next_actions(ws)


def fresh_findings(ws: Path, quac: Path) -> None:
    """Make the stand-in QuaC report the schema files as they are now, as the real one does."""
    doc = read_json(quac / "findings.json")
    doc["inputs"]["schema"]["setId"] = sf.quac_set_id(ws / "package" / "schemas")
    write_json(quac / "findings.json", doc)


def test_a_rerun_replaces_the_checks_left_open_on_the_run_before(ws, quac):
    rec(ws, *[{"type": "topic", "event": "present", "id": t} for t in ("participant", "sleep")])
    validated(ws)
    rec(ws, allow())
    sf.run_data_check(ws, "X01")
    keys = [c["key"] for c in sf.show_items(ws, ["A01"])["items"]["A01"]["checks"]]
    rec(ws, {"type": "alignment", "event": "triage", "id": "A01", "check": keys[0], "verdict": "schema-fix",
             "note": "the rule was encoded the wrong way round"})
    assert "triage-alignment" in next_actions(ws)                             # nothing changed yet: finish triage
    edit(ws, SLEEP, lambda d: d["properties"]["nap_minutes"].update(description="Minutes napped"))
    validated(ws)
    assert "run-data-check" not in next_actions(ws)                           # words only: the data would fail the same
    edit(ws, SLEEP, lambda d: d["properties"]["nap_minutes"]["anyOf"][0].update(maximum=480))   # the slip, fixed
    validated(ws)
    acts = next_actions(ws)
    assert acts[:1] == ["run-data-check"] and "triage-alignment" not in acts  # the rest wait for the fresh counts
    fresh_findings(ws, quac)
    sf.run_data_check(ws, "X01")
    shown = sf.show_items(ws, ["A01", "A02"])["items"]
    assert shown["A01"]["supersededBy"] == "A02" and "supersededBy" not in shown["A02"]
    assert [a["ids"] for a in sf.status_payload(ws)["next"] if a["action"] == "triage-alignment"] == [["A02"]]
    assert "run-data-check" not in next_actions(ws)
    redo = next(c for c in shown["A02"]["checks"] if c["variable"] == "nap_minutes")
    assert redo["earlier"] == [{"run": "A01", "label": "Public export", "dataset": "X01", "verdict": "schema-fix",
                                "decision": None, "note": "the rule was encoded the wrong way round"}]
    assert "earlier" not in next(c for c in shown["A02"]["checks"] if c["variable"] == "age")
    site = sf.state_payload(ws, sf.load_world(ws), sf.Pkg(ws, sf.load_project(ws)), None, [], {})
    assert [a.get("supersededBy") for a in site["alignment"]] == ["A02", None]


def browser_allow(**kw) -> dict:
    ev = {"type": "dataset", "event": "allow", "label": "Clinic export", "basis": "browser", "by": "author",
          "via": "inbox:20260102T030405Z-a1b2c3"}
    ev.update(kw)
    return ev


@pytest.fixture
def page(ws, monkeypatch):
    """A served website, as `data-check` sees it: the server answers, and the page reports what it is connected to."""
    monkeypatch.setattr(sf, "server_info", lambda _ws: {"url": "http://127.0.0.1:8899/", "port": 8899})
    rec(ws, {"type": "session", "event": "start", "harness": "claude-code", "model": "claude-opus-5-5"}, browser_allow())

    def report(connected=True, dataset="X01", **kw):
        write_json(ws / "state" / "presence.json", {"at": sf.now(), "quac": {"connected": connected, "dataset": dataset, **kw}})
    return report


def answer_request(ws: Path, findings: dict, status: str | None = None) -> threading.Thread:
    """Play the website: wait for `data-check`'s request, then send QuaC's findings (or report QuaC's status)."""
    def run():
        for _ in range(200):
            rq = read_json(ws / "state" / "recheck.json") if (ws / "state" / "recheck.json").is_file() else None
            if rq:
                assert "recheck" in (ws / "site" / "data" / "activity.js").read_text(encoding="utf-8")
                if status:
                    write_json(ws / "state" / "presence.json", {"at": sf.now(), "quac": {
                        "connected": True, "dataset": rq["dataset"], "request": rq["id"], "status": status,
                        "detail": "Load a dataset to run QC."}})
                else:
                    submit(ws, [{"kind": "alignment", "label": "Clinic export", "request": rq["id"], "dataset": rq["dataset"],
                                 "findings": findings}], sub="20260102T030406Z-b2c3d4")
                return
            time.sleep(0.05)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def test_dataset_allow_in_the_browser_needs_no_path(ws):
    rec(ws, browser_allow())
    x = sf.load_world(ws).datasets["X01"]
    assert (x["basis"], x.get("path"), x["label"]) == ("browser", None, "Clinic export")
    assert "missing 'label'" in refused(ws, browser_allow(label=None))


def test_data_check_asks_the_open_website_and_imports_what_comes_back(ws, page):
    page()
    doc = findings_doc(sf.quac_set_id(ws / "package" / "schemas"))
    t = answer_request(ws, doc)
    out = sf.run_data_check(ws, "X01", timeout=20)
    t.join(5)
    assert (out["run"], out["dataset"], out["label"], out["current"]) == ("A01", "X01", "Clinic export", True)
    a = sf.load_world(ws).alignment["A01"]
    assert (a["dataset"], a["by"], a["via"]) == ("X01", "author", "inbox:20260102T030406Z-b2c3d4")
    assert not (ws / "state" / "recheck.json").exists()
    assert "recheck" not in (ws / "site" / "data" / "activity.js").read_text(encoding="utf-8")
    assert sf.inbox_list(ws)["total"] == 0                                    # taken, like any submission


def test_data_check_in_the_browser_says_what_the_person_must_do(ws, page, monkeypatch):
    page(connected=False)
    with pytest.raises(sf.Fail, match="No open website is connected to QuaC for Clinic export"):
        sf.run_data_check(ws, "X01", timeout=5)
    page(dataset="X09")                                                       # connected, but for another file
    with pytest.raises(sf.Fail, match="No open website is connected"):
        sf.run_data_check(ws, "X01", timeout=5)
    page()
    answer_request(ws, {}, status="needs-dataset")
    with pytest.raises(sf.Fail, match="QuaC has no dataset loaded"):
        sf.run_data_check(ws, "X01", timeout=20)
    assert not (ws / "state" / "recheck.json").exists()
    monkeypatch.setattr(sf, "server_info", lambda _ws: None)
    with pytest.raises(sf.Fail, match="not being served"):
        sf.run_data_check(ws, "X01", timeout=5)


def test_a_browser_check_waits_for_the_person_s_answer_like_any_other(ws, page):
    page()
    assert "run-data-check" not in next_actions(ws)                           # nothing tested yet
    rec(ws, *[{"type": "topic", "event": "present", "id": t} for t in ("participant", "sleep")])
    validated(ws)
    assert "run-data-check" in next_actions(ws)                               # due like a file you run yourself
    rec(ws, *[{"type": "topic", "event": "approve", "id": t, "by": "author"} for t in ("participant", "sleep")])
    nxt = next_actions(ws)
    assert "run-data-check" in nxt and "finish" in nxt                        # but the person's browser never holds up the end


def test_take_links_findings_only_to_a_browser_dataset(ws):
    rec(ws, {"type": "session", "event": "start", "harness": "opencode", "model": "qwen3-coder"},
        allow(), browser_allow())                                             # X01 the agent runs; X02 the browser checks
    doc = findings_doc(sf.quac_set_id(ws / "package" / "schemas"))
    sf.take_submission(ws, submit(ws, [{"kind": "alignment", "label": "a", "dataset": "X01", "findings": doc},
                                       {"kind": "alignment", "label": "b", "dataset": "X02", "findings": doc}]))
    w = sf.load_world(ws)
    assert (w.alignment["A01"].get("dataset"), w.alignment["A02"].get("dataset")) == (None, "X02")


def test_checks_on_columns_of_unbuilt_topics_wait_for_the_topic(ws, quac):
    rows = INVENTORY + [{"variable": "shoe_size", "table": "sleep_diary", "topic": "sleep", "status": "include",
                         "source": "S01:row 12", "note": ""}]
    write_inventory(ws, rows)
    rec(ws, allow())
    sf.run_data_check(ws, "X01")
    a = sf.load_world(ws).alignment["A01"]
    assert len(a["planned"]) == 1 and "shoe_size" in a["planned"][0]
    checks = sf.show_items(ws, ["A01"])["items"]["A01"]["checks"]
    assert [c["variable"] for c in checks if c.get("notBuiltYet")] == ["shoe_size"]
    nxt = sf.status_payload(ws)["next"]
    assert next(x for x in nxt if x["action"] == "triage-alignment")["why"].startswith("A01: 2 failing")


def test_take_records_a_dataset_the_person_allows_on_the_website(ws):
    rec(ws, {"type": "session", "event": "start", "harness": "opencode", "model": "llama-4-local"})
    sub = submit(ws, [{"kind": "dataset", "path": "data/export.csv", "label": "Public export", "basis": "local-model",
                       "text": "Our agent runs on our own GPU server; the agreement allows it."}], frm="steward")
    out = sf.take_submission(ws, sub)
    assert [(r["type"], r["id"]) for r in out["recorded"]] == [("dataset", "X01")]
    x = sf.load_world(ws).datasets["X01"]
    assert (x["by"], x["basis"], x["model"], x["via"]) == ("steward", "local-model", "llama-4-local", f"inbox:{sub}")
    sub2 = submit(ws, [{"kind": "dataset", "withdraw": "X01", "text": "Not any more."}], sub="20260102T030406Z-b2c3d4")
    sf.take_submission(ws, sub2)
    assert sf.load_world(ws).datasets["X01"]["withdrawn"]["by"] == "author"


def test_questions_from_an_agent_run_go_to_the_steward_for_a_limited_author(ws, quac):
    edit_project(ws, lambda p: p.update(people=[{"role": "author", "name": "", "profile": "limited", "knows": []},
                                                {"role": "steward", "name": "Dr. R. Osei", "knows": []}]))
    rec(ws, allow())
    sf.run_data_check(ws, "X01")
    assert sf.show_items(ws, ["A01"])["items"]["A01"]["askTo"] == "steward"


def topic_status(ws: Path, tid: str) -> dict:
    w = sf.load_world(ws)
    return next(t for t in sf.topic_statuses(w, sf.Pkg(ws, w.project), sf.checks_report(ws)) if t["id"] == tid)


def test_a_change_to_an_approved_topic_sends_it_back_to_the_person(ws):
    rec(ws, {"type": "topic", "event": "present", "id": "sleep"},
        {"type": "topic", "event": "approve", "id": "sleep", "by": "author", "via": "chat"})
    approved = topic_status(ws, "sleep")
    assert approved["status"] == "confirmed" and sf.load_world(ws).topics["sleep"]["approvals"][0]["hash"] == approved["hash"]
    (ws / "package" / "schemas" / SLEEP).write_text(json.dumps(read_json(ws / "package" / "schemas" / SLEEP)),
                                                    encoding="utf-8")         # formatting is not content
    assert topic_status(ws, "sleep")["status"] == "confirmed"
    edit(ws, SLEEP, lambda d: d["properties"]["nap_minutes"]["anyOf"][0].update(maximum=480))
    changed = topic_status(ws, "sleep")
    assert changed["status"] not in ("confirmed", "in-review") and changed["changedSinceApproval"]
    sub = submit(ws, [{"kind": "topic", "topic": "sleep", "verdict": "approve", "hash": approved["hash"]}])
    sf.take_submission(ws, sub)                                               # they approved the page before your edit
    assert topic_status(ws, "sleep")["status"] != "confirmed"
    sub = submit(ws, [{"kind": "topic", "topic": "sleep", "verdict": "approve", "hash": changed["hash"]}],
                 sub="20260102T030406Z-b2c3d4")
    sf.take_submission(ws, sub)
    assert topic_status(ws, "sleep")["status"] == "confirmed"


def test_an_approval_covers_the_answers_the_person_had_seen(ws):
    rec(ws, {"type": "topic", "event": "present", "id": "sleep"}, post(question()))          # D001, with the topic
    sf.take_submission(ws, submit(ws, [{"kind": "answer", "decision": "D001", "choice": "b"},
                                       {"kind": "topic", "topic": "sleep", "verdict": "approve"}]))
    edit(ws, SLEEP, lambda d: d["properties"]["nap_minutes"]["anyOf"][0].pop("maximum"))     # their answer, applied
    rec(ws, apply_("D001"))
    assert topic_status(ws, "sleep")["status"] == "confirmed"
    assert ledger_events(ws)[-1]["approvedHashes"] == {"sleep": topic_status(ws, "sleep")["hash"]}
    rec(ws, post(question(question="Is a doze under five minutes a nap?")), answer("D002", "b"))   # asked afterwards
    edit(ws, SLEEP, lambda d: d["properties"]["nap_minutes"]["anyOf"][0].update(minimum=5))
    rec(ws, apply_("D002"))
    assert topic_status(ws, "sleep")["status"] not in ("confirmed", "in-review")            # they have not seen this


def test_next_says_to_refresh_files_copied_from_an_updated_skill(ws):
    assert "refresh-assets" not in next_actions(ws)
    dst = next(ws / d for _, d in sf.SHIPPED if (ws / d).is_file())
    dst.write_bytes(dst.read_bytes() + b"\n")
    assert next_actions(ws)[:1] == ["refresh-assets"]
    sf.refresh_assets(ws)
    assert "refresh-assets" not in next_actions(ws)


def test_present_topic_says_when_it_changed_after_approval(ws, monkeypatch):
    rec(ws, {"type": "topic", "event": "present", "id": "sleep"},
        {"type": "topic", "event": "approve", "id": "sleep", "by": "author", "via": "chat"},
        {"type": "topic", "event": "present", "id": "participant", "note": "Age now accepts don't know."})
    edit(ws, SLEEP, lambda d: d["properties"]["nap_minutes"]["anyOf"][0].update(maximum=480))
    real = sf.topic_statuses
    monkeypatch.setattr(sf, "topic_statuses", lambda *a: [dict(t, status="tested") if t["id"] == "sleep" else t
                                                          for t in real(*a)])    # as if build had tested it
    acts = sf.status_payload(ws)["next"]
    why = next(a["why"] for a in acts if a["action"] == "present-topic")
    assert why.startswith("'Sleep' changed after a person approved it")
    assert next(t for t in sf.topic_statuses(sf.load_world(ws), sf.Pkg(ws, sf.load_project(ws)), None)
                if t["id"] == "participant")["presentNote"] == "Age now accepts don't know."


def test_check_warns_when_a_property_drops_a_code_its_dictionary_row_lists(ws):
    ext = ws / "sources" / "S01" / "extract"
    ext.mkdir(parents=True)
    (ext / "table.csv").write_text("_row,A,B,C\n4,age,Age at enrollment,18-90; -888 = don't know\n"
                                   "7,sleep_minutes,Total sleep,0-960; -888\n", encoding="utf-8")
    write_json(ext / "manifest.json", {"ok": True, "id": "S01", "kind": "csv"})
    rec(ws, {"type": "source", "event": "extract", "id": "S01", "dir": "sources/S01/extract", "files": 1})
    edit(ws, PARTICIPANT, lambda d: d["properties"]["age"].update({"x-provenance": {"default": "S01:row 4"}}))
    assert not [x for x in sf.check(ws, validate=False)["findings"] if x["code"] == "sentinel-dropped"]
    edit(ws, PARTICIPANT, lambda d: d["properties"]["age"].update(anyOf=[{"type": "integer", "minimum": 18, "maximum": 90}]))
    found = [x for x in sf.check(ws, validate=False)["findings"] if x["code"] == "sentinel-dropped"]
    assert [(x["variable"], x["severity"]) for x in found] == [("age", "warning")]
    assert "S01:row 4 lists -888 (Don't know)" in found[0]["message"]
    edit(ws, PARTICIPANT, lambda d: d["properties"]["age"]["x-provenance"].update(sentinels="D001"))
    assert not [x for x in sf.check(ws, validate=False)["findings"] if x["code"] == "sentinel-dropped"]


@pytest.mark.parametrize("schema, value, ok", [
    ({"anyOf": [{"type": "integer", "minimum": 0}, {"$ref": "../../common/defs.json#/$defs/dont_know"}]}, -888, True),
    ({"type": "integer", "minimum": 0}, -888, False),
    ({"oneOf": [{"const": 1}, {"const": 2}]}, -888, False),
    ({"enum": [1, 2, -888]}, -888, True),
    ({"type": "integer", "maximum": 999, "not": {"enum": [999]}}, 999, False),
    ({"type": "string"}, -888, False),
    ({"$ref": "#/nowhere"}, -888, True),                                       # unsure: no warning
])
def test_accepts_reads_a_schema_without_a_validator(ws, schema, value, ok):
    assert sf.accepts(sf.Pkg(ws, sf.load_project(ws)), PARTICIPANT, schema, value) is ok


def test_take_saves_data_check_findings(ws):
    current = sf.quac_set_id(ws / "package" / "schemas")
    sub = submit(ws, [
        {"kind": "alignment", "label": "Wave 1 export", "note": "from the 2019 release",
         "findings": findings_doc(current)},
        {"kind": "alignment", "label": "", "findings": findings_doc("0123456789abcdef", records=50, failing=1)},
        {"kind": "alignment", "label": "raw", "findings": {"containsData": True, "rows": [[1, 2]]}},
    ], frm="steward")
    out = sf.take_submission(ws, sub)
    assert [(r["type"], r["id"]) for r in out["recorded"]] == [("alignment", "A01"), ("alignment", "A02")]
    assert out["unhandled"] == [{"item": 3, "why": "not a QuaC findings-without-data document"}]
    assert read_json(ws / "alignment/A01.json") == findings_doc(current)
    w = sf.load_world(ws)
    a1, a2 = w.alignment["A01"], w.alignment["A02"]
    assert (a1["file"], a1["label"], a1["note"], a1["via"]) == \
        ("alignment/A01.json", "Wave 1 export", "from the 2019 release", f"inbox:{sub}")
    assert (a1["records"], a1["failing"], a1["checks"], a1["fingerprint"], a1["current"]) == (120, 7, 2, current, True)
    assert (a2["label"], a2["fingerprint"], a2["current"], a2["records"]) == \
        ("wave1-export.csv", "0123456789abcdef", False, 50)
    assert sorted(t["alignment"] for t in out["todo"]) == ["A01", "A02"]
    checks = sf.show_items(ws, ["A01"])["items"]["A01"]["checks"]
    assert [(c["variable"], c["topic"], c["rule"]) for c in checks] == [("nap_minutes", "sleep", "R001"),
                                                                         ("age", "participant", None)]
    assert [a["ids"] for a in sf.status_payload(ws)["next"] if a["action"] == "triage-alignment"] == \
        [["A01"], ["A02"]]
    assert "is not one of A01's failing checks" in refused(ws, {"type": "alignment", "event": "triage", "id": "A01",
                                                                "check": "no|such|key", "verdict": "question"})
    assert "cites, in 'decision'" in refused(ws, {"type": "alignment", "event": "triage", "id": "A01",
                                                  "check": checks[0]["key"], "verdict": "expected"})
    rec(ws, *[{"type": "alignment", "event": "triage", "id": "A01", "check": c["key"], "verdict": "schema-fix",
               "note": "my transcription slip"} for c in checks])
    assert [a["ids"] for a in sf.status_payload(ws)["next"] if a["action"] == "triage-alignment"] == [["A02"]]


def test_take_bulk_accept_confirms_the_covered_guesses(ws):
    rec(ws, guess(), guess(question="Upper bound for naps?", targets=["nap_minutes"], choice="600"),
        guess(question="Lower bound for age?", topic="participant", targets=["age"], choice="18"))
    rec(ws, {"type": "decision", "event": "open", "kind": "bulk", "topic": "sleep", "covers": ["D001", "D002"],
             "question": "I made 2 guesses where the dictionary is silent — do they look right?",
             "options": BULK_OPTIONS, "recommended": "accept", "why": "Each only rejects impossible values."})
    rec(ws, post("D004"))
    sub = submit(ws, [{"kind": "answer", "decision": "D004", "choice": "accept"}])
    out = sf.take_submission(ws, sub)
    assert [(r["event"], r["id"]) for r in out["recorded"]] == [("answer", "D004"), ("confirm", "D001"),
                                                                ("confirm", "D002")]
    assert statuses(ws) == {"D001": "confirmed", "D002": "confirmed", "D003": "provisional", "D004": "answered"}
    c = dec(ws, "D001")["confirmations"][0]
    assert (c["by"], c["note"], c["via"]) == ("author", "accepted with D004", f"inbox:{sub}")
    assert "D004" in {t["decision"] for t in out["todo"]}
    rec(ws, {"type": "decision", "event": "open", "kind": "bulk", "topic": "participant", "covers": ["D003"],
             "question": "One guess for age — does it look right?", "options": BULK_OPTIONS, "recommended": "accept",
             "why": "It only rejects impossible values."})
    out = sf.take_submission(ws, submit(ws, [{"kind": "answer", "decision": "D005", "choice": "review"}],
                                        sub="20260102T030406Z-b2c3d4"))
    assert [(r["event"], r["id"]) for r in out["recorded"]] == [("answer", "D005")]
    assert statuses(ws)["D003"] == "provisional"


def test_take_sets_aside_what_it_cannot_record_and_files_the_submission(ws):
    rec(ws, question())
    items = [
        {"kind": "answer", "decision": "D099", "choice": "a"},
        {"kind": "confirm", "decision": "D098"},
        {"kind": "rating", "stars": 5},
        "just text",
        {"kind": "topic", "topic": "smoking", "verdict": "approve"},
        {"kind": "topic", "topic": "sleep", "verdict": "maybe"},
        {"kind": "source", "source": "S77", "verdict": "approve"},
        {"kind": "comment", "target": None, "tags": [], "text": "   "},
        {"kind": "answer", "decision": "D001", "choice": "b"},
    ]
    sub = submit(ws, items)
    out = sf.take_submission(ws, sub)
    assert [u["item"] for u in out["unhandled"]] == [1, 2, 3, 4, 5, 6, 7, 8]
    whys = [u["why"] for u in out["unhandled"]]
    assert "D099 does not exist" in whys[0] and "D098 does not exist" in whys[1]
    assert "unknown kind 'rating'" in whys[2] and whys[3] == "not an object" and whys[7] == "empty comment"
    assert out["unhandled"][0]["raw"] == items[0]
    assert out["recorded"] == [{"type": "decision", "event": "answer", "id": "D001"}]
    assert not (ws / "inbox/pending" / f"{sub}.json").exists()
    done = read_json(ws / "inbox/done" / f"{sub}.json")
    assert done["takenAt"] and done["recorded"] == out["recorded"] and len(done["unhandled"]) == 8
    assert done["items"] == items and done["receivedAt"] == "2026-01-02T03:04:05Z"
    assert sf.inbox_list(ws)["total"] == 0 and "process-inbox" not in next_actions(ws)
    sf.build(ws, validate=False)
    state = json.loads((ws / "site/data/state.js").read_text(encoding="utf-8")[len("window.SCHEMIFY_STATE = "):-2])
    assert [d["id"] for d in state["inbox"]["done"]] == [sub] and state["inbox"]["pending"] == 0
    with pytest.raises(sf.Fail, match="No single pending submission"):
        sf.take_submission(ws, sub)


def test_take_matches_a_unique_prefix_only(ws):
    submit(ws, [{"kind": "note", "text": "a"}], sub="20260102T030405Z-aaaaaa")
    submit(ws, [{"kind": "note", "text": "b"}], sub="20260102T030405Z-bbbbbb")
    with pytest.raises(sf.Fail) as ei:
        sf.take_submission(ws, "20260102T030405Z")
    assert ei.value.extra["pending"] == ["20260102T030405Z-aaaaaa", "20260102T030405Z-bbbbbb"]
    assert sf.take_submission(ws, "20260102T030405Z-b")["submission"] == "20260102T030405Z-bbbbbb"


def test_inbox_import_brings_in_a_downloaded_file(ws, tmp_path):
    rec(ws, question())
    rec(ws, post("D001"))
    (tmp_path / "Downloads").mkdir()
    f = tmp_path / "Downloads" / "schemify-feedback-lark-2026-10-12T10-00-00.json"
    payload = {"schemifyInbox": 1, "workspace": sf.load_project(ws)["id"], "study": "LARK sleep study",
               "from": "steward", "submittedAt": "2026-10-12T10:00:00.000Z",
               "items": [{"kind": "answer", "decision": "D001", "choice": "b"}]}
    f.write_text(json.dumps(payload), encoding="utf-8")
    out = sf.inbox_import(ws, str(f))
    assert out["ok"] is True and out["warning"] is None and out["next"] == f"inbox take {out['submission']}"
    saved = read_json(ws / "inbox/pending" / f"{out['submission']}.json")
    assert (saved["importedFrom"], saved["id"], saved["items"]) == (f.name, out["submission"], payload["items"])
    assert saved["receivedAt"] and f.exists()                         # the user's own file is left alone
    took = sf.take_submission(ws, out["submission"])
    assert took["from"] == "steward" and dec(ws, "D001")["answer"]["by"] == "steward"


def test_inbox_import_warns_about_another_workspace_and_refuses_non_feedback(ws, tmp_path):
    f = tmp_path / "feedback.json"
    f.write_text(json.dumps({"workspace": "someone-else-1a2b", "items": [{"kind": "note", "text": "hi"}]}),
                 encoding="utf-8")
    out = sf.inbox_import(ws, str(f))
    assert "someone-else-1a2b" in out["warning"] and sf.load_project(ws)["id"] in out["warning"]
    for bad in ({"items": []}, {"no": "items"}, [1, 2]):
        f.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(sf.Fail, match="not a schemify feedback file"):
            sf.inbox_import(ws, str(f))
    with pytest.raises(sf.Fail, match="not a schemify feedback file"):
        sf.inbox_import(ws, str(tmp_path / "missing.json"))


def test_inbox_import_keeps_every_file(ws, tmp_path):
    ids = []
    for n in range(3):
        f = tmp_path / f"feedback-{n}.json"
        f.write_text(json.dumps({"schemifyInbox": 1, "items": [{"kind": "note", "text": f"note {n}"}]}),
                     encoding="utf-8")
        ids.append(sf.inbox_import(ws, str(f))["submission"])
    assert len(set(ids)) == 3
    assert sorted(p.stem for p in (ws / "inbox/pending").glob("*.json")) == sorted(ids)
    for sub in ids:
        sf.take_submission(ws, sub)
    assert sorted(d["answer"]["text"] for d in sf.load_world(ws).decisions.values()) == ["note 0", "note 1", "note 2"]


def test_tell_user_says_who_each_waiting_question_is_for(ws):
    rec(ws, dict(question(question="Is there an upper limit for naps?"), provisional="a"),
        dict(question(question="Which sites ran the 2019 wave?", to="steward"), provisional="a"))
    rec(ws, post("D001"), post("D002", to="steward"), {"type": "topic", "event": "present", "id": "sleep", "note": "naps"})
    lines = sf.tell_user_lines(ws, sf.load_world(ws), "http://127.0.0.1:1/")
    assert "1 question(s) are waiting for you there." in lines
    assert any(line.startswith("1 question(s) wait there for the data steward") for line in lines)
    assert any(line.startswith("1 topic(s) wait there for your review") and "Something's wrong" in line for line in lines)


def test_topic_statuses_carry_the_latest_presentation(ws):
    # the website asks for a new verdict on a topic presented again after a person's verdict
    rec(ws, {"type": "topic", "event": "present", "id": "sleep", "note": "first look"})
    def sleep_topic():
        w = sf.load_world(ws)
        return next(t for t in sf.topic_statuses(w, sf.Pkg(ws, w.project), None) if t["id"] == "sleep")
    first = sleep_topic()["presentedAt"]
    rec(ws, {"type": "topic", "event": "changes", "id": "sleep", "by": "author", "text": "Rename naps"},
        {"type": "topic", "event": "present", "id": "sleep", "note": "renamed"})
    again = sleep_topic()
    assert again["status"] == "in-review" and again["presentedAt"] >= first


def test_inbox_import_refuses_the_same_answers_twice(ws, tmp_path):
    doc = {"schemifyInbox": 1, "from": "author", "items": [{"kind": "note", "text": "the same note"}]}
    first, again = tmp_path / "feedback.json", tmp_path / "feedback (1).json"
    for f in (first, again):
        f.write_text(json.dumps(doc), encoding="utf-8")
    sub = sf.inbox_import(ws, str(first))["submission"]
    dup = sf.inbox_import(ws, str(again))
    assert dup["duplicate"] == sub and "arrived before" in dup["next"] and len(sf.inbox_pending(ws)) == 1
    sf.take_submission(ws, sub)
    assert sf.inbox_import(ws, str(again))["duplicate"] == sub          # still recognised once taken


def test_inbox_cli_contract(ws, tmp_path):
    code, out = cli("--ws", ws, "inbox", "list")
    assert code == 0 and out["total"] == 0
    code, out = cli("--ws", ws, "inbox", "take")
    assert code == 1 and "needs an argument" in out["error"]
    f = tmp_path / "fb.json"
    f.write_text(json.dumps({"items": [{"kind": "note", "text": "Bedtimes are local time."}]}), encoding="utf-8")
    code, out = cli("--ws", ws, "inbox", "import", f)
    assert code == 0 and out["submission"]
    sub = out["submission"]
    code, out = cli("--ws", ws, "inbox", "take", sub)
    assert code == 0 and out["recorded"] == [{"type": "decision", "event": "answer", "id": "D001"}] and out["todo"]
    code, out = cli("--ws", ws, "inbox", "take", sub)
    assert code == 1 and out["ok"] is False and out["pending"] == []


# ====================================================================== QuaC's schema-set id

QUAC_FILES = [DEFS, MOTHER, PARTICIPANT, SLEEP]


def quac_reference(root: Path):
    """QuaC 1.2.0's setId, transcribed from computeSetId/stripBom (src/core/schema/schema-set.ts):
    every .json file (any case) under its folder-relative POSIX path, sorted with JavaScript's `<`
    (UTF-16 code units); payload `${path.length}:${path}${raw.length}:${raw}` with JavaScript string
    lengths (UTF-16 code units) and the text BOM-stripped; SHA-256 of the UTF-8 payload, first 16 hex."""
    def units(s: str) -> list:
        out = []
        for ch in s:
            cp = ord(ch)
            if cp > 0xFFFF:
                cp -= 0x10000
                out += [0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF)]
            else:
                out.append(cp)
        return out
    entries = []
    for p in root.rglob("*"):
        if p.is_file() and p.name.lower().endswith(".json"):
            raw = p.read_bytes().decode("utf-8", errors="replace")
            if raw[:1] == "﻿":
                raw = raw[1:]
            entries.append((p.relative_to(root).as_posix(), raw))
    if not entries:
        return None
    entries.sort(key=lambda e: units(e[0]))
    payload = "".join(f"{len(units(p))}:{p}{len(units(r))}:{r}" for p, r in entries)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def test_quac_set_id_matches_quac_on_the_1x_fixture(tmp_path):
    root = tmp_path / "schemas"
    for rel in QUAC_FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURE_1X / "json_schema" / rel, root / rel)
    assert sf.quac_set_id(root) == "bcc8105204dc4a6c"
    assert quac_reference(root) == "bcc8105204dc4a6c"


def test_quac_set_id_strips_a_bom(tmp_path):
    text = '{\n  "type": "object"\n}\n'
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a/x.json").write_bytes(text.encode("utf-8"))
    (tmp_path / "b/x.json").write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    assert sf.quac_set_id(tmp_path / "a") == sf.quac_set_id(tmp_path / "b") == quac_reference(tmp_path / "a")


def test_quac_set_id_counts_line_endings(tmp_path):
    text = '{\n  "type": "object"\n}\n'
    (tmp_path / "lf").mkdir()
    (tmp_path / "crlf").mkdir()
    (tmp_path / "lf/x.json").write_bytes(text.encode("utf-8"))
    (tmp_path / "crlf/x.json").write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert sf.quac_set_id(tmp_path / "lf") != sf.quac_set_id(tmp_path / "crlf")
    assert sf.quac_set_id(tmp_path / "crlf") == quac_reference(tmp_path / "crlf")


def test_quac_set_id_counts_utf16_code_units(tmp_path):
    root = tmp_path / "schemas"
    root.mkdir()
    (root / "\U0001F600.json").write_text('{"title": "\U0001F634 sleepy"}', encoding="utf-8")   # astral: 2 units
    (root / "ａ.json").write_text('{"title": "café"}', encoding="utf-8")             # BMP, above surrogates
    (root / "z.json").write_text('{"title": "plain"}', encoding="utf-8")
    got = sf.quac_set_id(root)
    assert got == quac_reference(root)
    entries = sorted((p.name, p.read_text(encoding="utf-8")) for p in root.iterdir())       # code-point order
    naive = hashlib.sha256("".join(f"{len(p)}:{p}{len(r)}:{r}" for p, r in entries).encode()).hexdigest()[:16]
    assert got != naive                                    # Python's len() and sort order are not QuaC's


def test_quac_set_id_of_an_empty_or_missing_folder(tmp_path):
    assert sf.quac_set_id(tmp_path / "missing") is None
    (tmp_path / "empty").mkdir()
    assert sf.quac_set_id(tmp_path / "empty") is None
    (tmp_path / "empty/README.md").write_text("not a schema", encoding="utf-8")
    assert sf.quac_set_id(tmp_path / "empty") is None
    (tmp_path / "empty/Defs.JSON").write_text("{}", encoding="utf-8")
    assert sf.quac_set_id(tmp_path / "empty") == quac_reference(tmp_path / "empty") is not None


# ====================================================================== check

def test_check_is_clean_on_a_consistent_workspace(ws):
    res = checked(ws)
    assert res["findings"] == [] and res["ok"] is True and res["blocking"] == 0
    assert res["counts"] == {"error": 0, "warning": 0, "info": 0}
    assert res["validator"] == {"ok": True, "headline": STUB_HEADLINE}
    rec(ws, SRC_DOC)
    res = checked(ws)
    assert [(f["severity"], f["code"]) for f in res["findings"]] == [("info", "source-undigested")]
    assert res["ok"] is True and res["blocking"] == 0
    (ws / "state/checks.json").unlink()
    res = sf.check(ws, validate=False)
    assert res["ok"] is False and find(res, "validator-not-run")[0]["severity"] == "error"


def test_check_reconciles_the_inventory_with_the_schemas(ws):
    edit_project(ws, lambda p: p["topics"].append(
        {"id": "naps", "title": "Naps", "table": "sleep_diary", "file": "sleep_diary/categories/naps.json"}))
    rows = [dict(r) for r in INVENTORY if r["variable"] != "site_id"]
    for r in rows:
        if r["variable"] == "age":
            r.update(status="deferred", note="waits on D009")
    rows.append({"variable": "melatonin_use", "table": "sleep_diary", "topic": "sleep", "status": "include",
                 "source": "S01:row 11", "note": ""})
    rows.append({"variable": "nap_quality", "table": "sleep_diary", "topic": "naps", "status": "include",
                 "source": "S01:row 12", "note": "its topic is not drafted yet"})
    write_inventory(ws, rows)
    res = checked(ws)
    assert res["ok"] is False
    assert [f["variable"] for f in find(res, "coverage-missing")] == ["melatonin_use"]
    assert [f["variable"] for f in find(res, "coverage-excluded")] == ["age"]
    assert [f["variable"] for f in find(res, "coverage-uninventoried")] == ["site_id"]
    for code in ("coverage-missing", "coverage-excluded", "coverage-uninventoried"):
        assert find(res, code)[0]["severity"] == "error" and find(res, code)[0]["hint"]


def test_check_treats_a_scaffolded_topic_as_planned(ws):
    # START.md step 8: a topic file with an empty `properties` is planned, so its inventory rows are not
    # missing yet, and no toy data is due before the first topic is drafted.
    edit_project(ws, lambda p: p["topics"].append(
        {"id": "naps", "title": "Naps", "table": "sleep_diary", "file": "sleep_diary/categories/naps.json"}))
    write_json(ws / "package/schemas/sleep_diary/categories/naps.json",
               {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": BASE + "sleep_diary/categories/naps.json",
                "title": "Naps", "type": "object", "x-variable-group": "Naps", "properties": {}})
    write_inventory(ws, [dict(r) for r in INVENTORY] + [{"variable": "nap_quality", "table": "sleep_diary", "topic": "naps",
                                                         "status": "include", "source": "S01:row 12", "note": ""}])
    res = checked(ws)
    assert find(res, "coverage-missing") == []
    assert [t["status"] for t in sf.status_payload(ws)["topics"]["items"] if t["id"] == "naps"] == ["planned"]


HEADER = ",".join(sf.INVENTORY_COLUMNS) + "\n"
AGE_ROW = "age,sleep_diary,participant,include,S01:row 3,\n"


@pytest.mark.parametrize("text, message", [
    ("variable,table,topic,status,source\nage,sleep_diary,participant,include,S01:row 3\n", "header must be exactly"),
    (HEADER + AGE_ROW.replace("include", "maybe"), "status 'maybe' is not one of"),
    (HEADER + AGE_ROW + AGE_ROW, "age appears twice"),
], ids=["header", "status", "duplicate"])
def test_check_reports_an_invalid_inventory(ws, text, message):
    (ws / "state/variables.csv").write_text(text, encoding="utf-8")
    res = checked(ws)
    bad = find(res, "inventory-invalid")
    assert bad and message in bad[0]["message"] and bad[0]["severity"] == "error" and res["ok"] is False


def test_check_validates_project_json(ws):
    def spoil(p):
        p["mode"] = "draft"
        p["preferences"]["inferRules"] = "sometimes"
        p["topics"][1]["file"] = "sleep_diary/sleep.json"
        p["conventions"]["sentinels"].append({"code": -999})
    edit_project(ws, spoil)
    res = checked(ws)
    msgs = [f["message"] for f in find(res, "project-invalid")]
    assert any("mode is 'draft'" in m for m in msgs) and any("inferRules" in m for m in msgs)
    assert any("-999" in m for m in msgs)
    assert [f["message"] for f in find(res, "project-layout")] == ["topic sleep: file is sleep_diary/sleep.json"]


def test_check_traces_every_citation(ws):
    rec(ws, SRC_WEB)                                                                       # S02, suggested
    rec(ws, guess(), question(question="Moot?"), guess(question="Old?"), guess(question="New?"),
        question(question="Still open?"))                                                 # D001-D005
    rec(ws, {"type": "decision", "event": "cancel", "id": "D002", "note": "moot"},
        {"type": "decision", "event": "supersede", "id": "D003", "replacement": "D004"})
    edit(ws, SLEEP, lambda d: d["properties"]["sleep_minutes"].update({"x-provenance": {
        "default": "S01:row 6", "maximum": "D001", "title": "S02", "description": "S09:p.1", "minimum": "D077",
        "type": "D002", "anyOf": "D003", "x-unit": "D005"}}))
    res = checked(ws)
    unknown = find(res, "provenance-unknown")
    assert len(unknown) == 2 and all(f["severity"] == "error" for f in unknown)
    assert any("S09" in f["message"] for f in unknown) and any("D077" in f["message"] for f in unknown)
    uncitable = find(res, "provenance-uncitable")
    assert len(uncitable) == 1 and "S02" in uncitable[0]["message"] and "suggested" in uncitable[0]["message"]
    assert "D002" in find(res, "provenance-cancelled")[0]["message"]
    superseded = find(res, "provenance-superseded")
    assert superseded[0]["severity"] == "warning" and "D003" in superseded[0]["message"]
    assert superseded[0]["hint"] == "Cite D004."
    assert "D005" in find(res, "provenance-unsettled")[0]["message"]
    assert not [f for f in res["findings"]                                       # a provisional guess is citable
                if f["code"].startswith("provenance-") and "D001" in f["message"]]
    assert res["ok"] is False
    rec(ws, {"type": "source", "event": "approve", "id": "S02", "by": "author"})
    assert not find(checked(ws), "provenance-uncitable")


def test_check_reconciles_rules_with_the_mothers(ws):
    rec(ws, guess(kind="rule", question="Do nights without a diary skip naps?", choice="yes"))     # D001
    rec(ws, question(kind="consent", question="May I include the rule R004, which I inferred?",
                     options=[{"id": "yes", "label": "Yes"}, {"id": "no", "label": "No"}], recommended="yes",
                     provisional="no"))  # D002
    rec(ws, {**BASE_RULE, "id": "R002", "evidence": "documented", "status": "encoded"},
        {**BASE_RULE, "id": "R003", "gates": ["sleep_minutes"], "targets": ["nap_yesterday"], "evidence": "documented",
         "status": "waiting", "waits_for": ["nap_yesterday"]},
        {**BASE_RULE, "id": "R004", "evidence": "inferred", "status": "encoded", "decision": "D001", "consent": "D002"},
        {**BASE_RULE, "id": "R005", "evidence": "inferred", "status": "suspected"},
        {"type": "rule", "event": "set", "id": "R001", "status": "deferred", "note": "testing the reconciliation"})
    cond = {"if": {"required": ["sleep_minutes"], "properties": {"sleep_minutes": {"const": -666}}},
            "then": {"properties": {"nap_yesterday": {"const": -666}}}}
    edit(ws, MOTHER, lambda d: d["items"]["allOf"].extend([
        {"$comment": "A conditional nobody numbered.", **cond},
        {"$comment": "Skip pattern R009: registered nowhere.", "x-provenance": {"default": "S01:row 6"}, **cond},
        {"$comment": "Skip pattern R004: inferred by the agent (D001).", "x-provenance": {"default": "D001"}, **cond}]))
    res = checked(ws)
    assert ["/items/allOf/4" in f["message"] for f in find(res, "rule-unidentified")] == [True]
    assert ["R009" in f["message"] for f in find(res, "rule-unregistered")] == [True]
    assert ["R002" in f["message"] for f in find(res, "rule-not-encoded")] == [True]
    assert [("R001" in f["message"] and "deferred" in f["message"]) for f in find(res, "rule-status")] == [True]
    assert ["R004" in f["message"] for f in find(res, "rule-consent")] == [True]
    ready = find(res, "rule-ready")
    assert len(ready) == 1 and "R003" in ready[0]["message"] and ready[0]["severity"] == "warning"
    assert ["R005" in f["message"] for f in find(res, "rule-unasked")] == [True]
    rec(ws, answer("D002", "yes"))
    assert not find(checked(ws), "rule-consent")                    # a person's yes licenses the inferred rule


def test_check_blocks_on_unfinished_feedback_without_failing(ws):
    rec(ws, question(), question(question="Unsure?"))
    rec(ws, answer("D001", "a"), answer("D002", "unsure"))
    submit(ws, [{"kind": "note", "text": "hello"}])
    res = checked(ws)
    assert res["ok"] is True and res["blocking"] == 3 and res["counts"] == {"error": 0, "warning": 3, "info": 0}
    for code, did in (("decision-unapplied", "D001"), ("decision-unsure", "D002"), ("inbox-pending", None)):
        f = find(res, code)
        assert len(f) == 1 and f[0]["severity"] == "warning" and f[0]["hint"], code
        assert did is None or did in f[0]["message"]


def test_check_flags_stale_shipped_files_until_refreshed(ws):
    assert not find(checked(ws), "assets-stale")
    app = ws / "site/app.js"
    app.write_text(app.read_text(encoding="utf-8") + "\n// a local edit\n", encoding="utf-8")
    (ws / "tools/serve.py").unlink()
    res = checked(ws)
    stale = find(res, "assets-stale")
    assert len(stale) == 1 and stale[0]["severity"] == "warning" and "refresh-assets" in stale[0]["hint"]
    assert "site/app.js" in stale[0]["message"] and "tools/serve.py" in stale[0]["message"]
    assert res["ok"] is True and res["blocking"] == 0
    code, out = cli("--ws", ws, "refresh-assets")
    assert code == 0 and sorted(out["changed"]) == ["site/app.js", "tools/serve.py"]
    assert not find(checked(ws), "assets-stale")
    code, out = cli("--ws", ws, "refresh-assets")
    assert code == 0 and out["changed"] == [] and out["next"] == "Already current."


def test_check_flags_a_stale_website(ws):
    assert not find(checked(ws), "site-stale")
    state_js = ws / "site/data/state.js"
    old = time.time() - 3600
    os.utime(state_js, (old, old))                       # mtimes do not matter (a git checkout scrambles them)
    assert not find(sf.check(ws, validate=False), "site-stale")
    proj = json.loads((ws / "state/project.json").read_text(encoding="utf-8"))
    proj["description"] = "Changed after the last build."
    (ws / "state/project.json").write_text(json.dumps(proj), encoding="utf-8")
    stale = find(sf.check(ws, validate=False), "site-stale")
    assert stale and stale[0]["severity"] == "warning" and "build" in stale[0]["hint"]
    strict = sf.check(ws, validate=False, strict=True)
    assert find(strict, "site-stale")[0]["severity"] == "error" and strict["ok"] is False
    sf.build(ws, validate=False)
    assert not find(sf.check(ws, validate=False, strict=True), "site-stale")
    state_js.unlink()
    assert find(sf.check(ws, validate=False), "site-stale")


def test_ws_may_follow_the_command(bare):
    code, out = cli("check", "--ws", bare)
    assert code == 0 and out["ok"] is True
    code, out = cli("queue", "--for", "steward", f"--ws={bare}")
    assert code == 0 and out["openBatches"] == [] and out["deferredRules"] == []


def test_check_cli_exit_codes(bare):
    code, out = cli("--ws", bare, "check")
    assert code == 0 and out["ok"] is True and out["blocking"] == 0
    (bare / "state/variables.csv").write_text("name,status\n", encoding="utf-8")
    code, out = cli("--ws", bare, "check")
    assert code == 1 and out["ok"] is False
    assert [f["code"] for f in out["findings"] if f["severity"] == "error"] == ["inventory-invalid"]


# ====================================================================== sessions: open, close

def test_close_refuses_while_blocked(ws, stub_validator):
    rec(ws, question())
    rec(ws, answer("D001", "a"))
    submit(ws, [{"kind": "note", "text": "hello"}])
    before = ledger_bytes(ws)
    with pytest.raises(sf.Fail) as ei:
        sf.close_session(ws, {"summary": "Drafted sleep.", "handoff": "", "next": "apply D001"})
    assert ei.value.error.startswith("Not closed: 2 item(s)") and "force" in ei.value.hint
    blockers = ei.value.extra["blockers"]
    assert sorted(b["code"] for b in blockers) == ["decision-unapplied", "inbox-pending"]
    assert any("D001" in b["message"] for b in blockers)
    assert ledger_bytes(ws) == before and stub_validator


def test_close_force_needs_a_handoff(ws, stub_validator):
    rec(ws, question())
    rec(ws, answer("D001", "a"))
    before = ledger_bytes(ws)
    with pytest.raises(sf.Fail, match="handoff"):
        sf.close_session(ws, {"summary": "Stopping early.", "next": "apply D001", "force": True})
    assert ledger_bytes(ws) == before
    out = sf.close_session(ws, {"summary": "Stopping early.", "handoff": "D001 is answered but not applied.",
                                "next": "apply D001", "force": True})
    assert out["ok"] is True and out["forced"] is True
    assert [b["code"] for b in out["blockers"]] == ["decision-unapplied"]
    end = sf.load_world(ws).sessions[-1]["end"]
    assert end["forced"] is True and end["handoff"] == "D001 is answered but not applied."


def test_close_records_the_session_end(ws, stub_validator):
    rec(ws, {"type": "session", "event": "start", "harness": "claude-code"})
    sid = sf.load_world(ws).open_session()["id"]
    out = sf.close_session(ws, {"summary": "Drafted both topics.", "handoff": "The author prefers short batches.",
                                "next": "present sleep"})
    assert out["ok"] is True and out["closed"] == sid and out["forced"] is False and out["blockers"] == []
    assert out["checks"]["headline"] == STUB_HEADLINE and stub_validator          # close validated first
    assert out["tell_user"][0] == "Everything is saved."
    assert any(line.startswith("Your project website:") for line in out["tell_user"])
    assert any("type /schemify" in line for line in out["tell_user"])
    w = sf.load_world(ws)
    assert w.open_session() is None
    assert {k: w.sessions[-1]["end"][k] for k in ("summary", "handoff", "next")} == {
        "summary": "Drafted both topics.", "handoff": "The author prefers short batches.", "next": "present sleep"}
    last = sf.status_payload(ws)["lastSession"]
    assert (last["id"], last["next"]) == (sid, "present sleep")
    with pytest.raises(sf.Fail, match="close needs"):
        sf.close_session(ws, {"summary": "No next step."})


def test_close_cli(bare):
    code, out = cli("--ws", bare, "close", stdin=json.dumps({"summary": "Set up.", "handoff": "none",
                                                             "next": "register the sources"}))
    assert code == 0 and out["ok"] is True and out["closed"] and out["tell_user"]
    w = sf.load_world(bare)                      # no session was open: close records the start and the end
    assert len(w.sessions) == 1 and w.sessions[0]["end"]["next"] == "register the sources"
    submit(bare, [{"kind": "note", "text": "hello"}])
    code, out = cli("--ws", bare, "close", stdin=json.dumps({"summary": "s", "next": "n"}))
    assert code == 1 and out["error"].startswith("Not closed") and out["blockers"][0]["code"] == "inbox-pending"
    code, out = cli("--ws", bare, "close", stdin="{}")
    assert code == 1 and "close needs" in out["error"]


def test_open_starts_then_resumes_a_session(ws):
    out = sf.open_session(ws, None, "claude-code", "test-model", serve=False)
    assert out["ok"] is True and out["sessionReused"] is False and out["session"]
    assert out["tell_user"][0].startswith("Your project website:")
    assert sf.load_project(ws)["harness"] == "claude-code"
    again = sf.open_session(ws, None, None, None, serve=False)
    assert again["sessionReused"] is True and again["session"] == out["session"]
    assert [e["event"] for e in ledger_events(ws) if e["type"] == "session"] == ["start"]
    review = sf.open_session(ws, "review", None, None, serve=False)          # a new mode is a new session
    assert review["sessionReused"] is False and review["mode"] == "review"
    w = sf.load_world(ws)
    assert w.sessions[0]["end"]["forced"] is True and w.sessions[1]["mode"] == "review"


def test_open_ends_an_old_unclosed_session(ws):
    with open(ws / "state/ledger.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "session", "event": "start", "id": "2026-01-01#1", "mode": "build",
                             "at": "2026-01-01T09:00:00Z", "by": "agent"}) + "\n")
    out = sf.open_session(ws, None, None, None, serve=False)
    assert out["sessionReused"] is False and out["session"] != "2026-01-01#1"
    w = sf.load_world(ws)
    old = w.sessions[0]
    assert old["id"] == "2026-01-01#1" and old["end"]["forced"] is True
    assert "without its closing checklist" in old["end"]["summary"]
    assert w.open_session()["id"] == out["session"]
    assert out["lastSession"]["id"] == "2026-01-01#1" and "status" in out["lastSession"]["handoff"]


def test_open_cli(bare):
    code, out = cli("--ws", bare, "open", "--no-serve", "--harness", "codex", "--model", "m")
    assert code == 0 and out["ok"] is True and out["sessionReused"] is False
    assert out["website"].endswith("index.html") and out["websiteServed"] is False
    assert any("start your message with $schemify" in line for line in out["tell_user"])
    assert any("Download as a file" in line for line in out["tell_user"])      # not served: say what changes
    assert out["tell_user"][0].startswith("Your project website: file://")
    assert out["next"][0]["action"] == "add-sources"


# ====================================================================== build

def test_build_writes_the_package_files(ws):
    rec(ws, guess())
    out = sf.build(ws, validate=False)
    assert out["ok"] is True and out["checks"] is None and out["website"].endswith("index.html")
    for f in ("package/provenance.json", "package/PROVENANCE.md", "package/README.md", "package/dictionary.html",
              "site/data/state.js", "index.html", "START-HERE.md"):
        assert f in out["written"] and (ws / f).is_file(), f
    assert (ws / "package/tools/requirements.txt").read_text(encoding="utf-8") == sf.REQUIREMENTS
    readme = (ws / "package/README.md").read_text(encoding="utf-8")
    assert readme.startswith("# LARK sleep study — JSON Schema package")
    assert PROJECT["description"] in readme and "`sleep_diary`" in readme and "R001" in readme
    assert "| `-666` | Not applicable (skipped by design) | yes |" in readme and BASE in readme
    assert ("- D001: Plausible upper bound for total sleep (minutes)? — applied for now: 960 "
            "(an agent decision awaiting a person's review, ⚑ in PROVENANCE.md)") in readme
    provenance_md = (ws / "package/PROVENANCE.md").read_text(encoding="utf-8")
    assert "| D001 ⚑ |" in provenance_md and "| S01 | LARK data dictionary |" in provenance_md
    index = (ws / "index.html").read_text(encoding="utf-8")
    assert "{{" not in index and "LARK sleep study" in index


def test_build_provenance_lists_sources_and_decisions(ws):
    rec(ws, SRC_WEB, {**SRC_WEB, "title": "Rejected but cited", "url": "https://example.org/cited"})   # S02, S03
    rec(ws, {"type": "source", "event": "reject", "id": "S02", "by": "author"},
        {"type": "source", "event": "reject", "id": "S03", "by": "author"})
    rec(ws,
        {"type": "decision", "event": "answer", "kind": "interview", "by": "author", "question": "Your role?",
         "choice": "other", "text": "Study coordinator"},                                              # D001
        {"type": "decision", "event": "answer", "kind": "feedback", "by": "author",
         "question": "Comment on variable sleep_minutes", "choice": "other", "text": "Say 'Total sleep'."},  # D002
        guess(),                                                                                        # D003
        question(question="Moot?"),                                                                     # D004
        {"type": "decision", "event": "answer", "kind": "knowledge", "by": "steward",
         "question": "Were naps self-reported?", "choice": "other", "text": "Yes, in the morning diary"},  # D005
        {"type": "decision", "event": "answer", "kind": "interview", "by": "author",
         "question": "Preferred batch size?", "choice": "other", "text": "5"})                         # D006
    rec(ws, {"type": "decision", "event": "cancel", "id": "D004", "note": "moot"})
    edit(ws, SLEEP, lambda d: d["properties"]["sleep_minutes"].update({"x-provenance": {
        "default": "S01:row 6", "title": "D002", "maximum": "D003", "minimum": "S03", "description": "D006"}}))
    sf.build(ws, validate=False)
    prov = read_json(ws / "package/provenance.json")
    assert prov["schemifyProvenance"] == 1 and prov["study"] == "LARK sleep study"
    assert sorted(prov["sources"]) == ["S01", "S03"]                       # uncited rejected S02 is left out
    assert prov["sources"]["S01"] == {"kind": "document", "title": "LARK data dictionary",
                                      "what": "Variables with labels, types and codes", "status": "active",
                                      "file": "S01-dictionary.csv"}
    assert prov["sources"]["S03"]["url"] == "https://example.org/cited" and prov["sources"]["S03"]["status"] == "rejected"
    assert sorted(prov["decisions"]) == ["D002", "D003", "D005", "D006"]  # uncited interview and cancelled left out
    d3 = prov["decisions"]["D003"]
    assert {k: d3[k] for k in ("kind", "answer", "by", "status", "needsReview", "topic", "targets")} == {
        "kind": "guess", "answer": "960", "by": "agent", "status": "provisional", "needsReview": True,
        "topic": "sleep", "targets": ["sleep_minutes"]}
    assert (prov["decisions"]["D005"]["by"], prov["decisions"]["D005"]["answer"]) == \
        ("steward", "Yes, in the morning diary")
    md = (ws / "package/PROVENANCE.md").read_text(encoding="utf-8")
    assert "| D003 ⚑ |" in md and "[Rejected but cited](https://example.org/cited)" in md and "| D001" not in md


def test_build_writes_a_standalone_dictionary(ws):
    sf.build(ws, validate=False)
    page = (ws / "package/dictionary.html").read_text(encoding="utf-8")
    assert "{{" not in page
    blocks = json_blocks(page)
    docs = next(b for b in blocks if isinstance(b, list))
    assert sorted(d["name"] for d in docs) == sorted(QUAC_FILES)
    for d in docs:
        assert d["schema"] == read_json(ws / "package/schemas" / d["name"]) and d["uri"] == BASE + d["name"]
    config = next(b for b in blocks if isinstance(b, dict) and "mounts" in b)
    assert config["mounts"] == [{"table": "sleep_diary", "title": "Sleep diary", "rootUri": BASE + MOTHER}]
    assert config["package"] == sf.load_project(ws)["id"]
    prov = next(b for b in blocks if isinstance(b, dict) and b.get("schemifyProvenance") == 1)
    assert "S01" in prov["sources"]


def test_build_writes_csv_twins_of_the_toy_data(ws):
    td = ws / "package/toy-data/sleep_diary"
    write_json(td / "valid.json", [
        {"participant_id": "P0001", "site_id": "01", "age": 34, "sleep_minutes": 420, "nap_yesterday": 0,
         "nap_minutes": -666},
        {"participant_id": "P0002", "site_id": "02", "age": None, "sleep_minutes": 300.5, "nap_yesterday": 1,
         "flags": [1, 2], "late": True, "meta": {"k": "v"}},
    ])
    write_json(td / "invalid.json", [{"participant_id": "P12", "shoe_size": 44}])
    out = sf.build(ws, validate=False)
    assert "package/toy-data/sleep_diary/valid.csv" in out["written"]
    assert "package/toy-data/sleep_diary/invalid.csv" in out["written"]
    text = (td / "valid.csv").read_text(encoding="utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == ["participant_id", "site_id", "age", "sleep_minutes", "nap_yesterday", "nap_minutes",
                       "flags", "late", "meta"]                     # topic order first, then extra keys as met
    assert rows[1] == ["P0001", "01", "34", "420", "0", "-666", "", "", ""]
    assert rows[2] == ["P0002", "02", "null", "300.5", "1", "", "[1, 2]", "true", '{"k": "v"}']
    assert "\nP0001,01," in text                                     # string codes keep their leading zero
    invalid = list(csv.reader(io.StringIO((td / "invalid.csv").read_text(encoding="utf-8"))))
    assert invalid[0][-1] == "shoe_size" and invalid[1][0] == "P12" and invalid[1][1] == "" and invalid[1][-1] == "44"


def test_build_state_js_is_a_safe_script(ws):
    hostile = "Ends </script><script>alert(1)</script> here next"
    edit(ws, SLEEP, lambda d: d["properties"]["nap_minutes"].update(description=hostile))
    sf.build(ws, validate=False)
    text = (ws / "site/data/state.js").read_text(encoding="utf-8")
    prefix = "window.SCHEMIFY_STATE = "
    assert text.startswith(prefix) and text.endswith(";\n")
    assert "</script" not in text.lower() and " " not in text
    state = json.loads(text[len(prefix):-2])
    sleep = next(s for s in state["schemas"] if s["path"] == SLEEP)
    assert sleep["schema"]["properties"]["nap_minutes"]["description"] == hostile and sleep["uri"] == BASE + SLEEP
    assert state["format"] == 1 and state["workspace"]["id"] == sf.load_project(ws)["id"]
    assert state["quacSetId"] == sf.quac_set_id(ws / "package/schemas")
    assert [r["id"] for r in state["encodedRules"]] == ["R001", "R001"]
    page = (ws / "package/dictionary.html").read_text(encoding="utf-8")
    assert "</script><script>alert(1)" not in page
    docs = next(b for b in json_blocks(page) if isinstance(b, list))
    assert next(d for d in docs if d["name"] == SLEEP)["schema"]["properties"]["nap_minutes"]["description"] == hostile


def test_build_start_here_says_how_to_continue(ws):
    sf.build(ws, validate=False)
    text = (ws / "START-HERE.md").read_text(encoding="utf-8")
    assert text.startswith("# LARK sleep study — schemify workspace")
    assert "type `/schemify`." in text and f"`{ws.parent}`" in text
    edit_project(ws, lambda p: p.update(harness="codex", invoke="$schemify"))
    sf.build(ws, validate=False)
    assert "start your message with `$schemify`" in (ws / "START-HERE.md").read_text(encoding="utf-8")


def test_build_fills_templates_in_one_pass(ws):
    edit_project(ws, lambda p: p.update(study="Sleep {{STUDY}} study"))
    edit(ws, PARTICIPANT, lambda d: d.update(title="Participant {{TITLE}} {{SCHEMAS_JSON}}"))
    sf.build(ws, validate=False)
    page = (ws / "package/dictionary.html").read_text(encoding="utf-8")
    assert "<title>Sleep {{STUDY}} study — data dictionary</title>" in page
    docs = next(b for b in json_blocks(page) if isinstance(b, list))
    assert next(d for d in docs if d["name"] == PARTICIPANT)["schema"]["title"] == "Participant {{TITLE}} {{SCHEMAS_JSON}}"
    assert "<title>Sleep {{STUDY}} study — schemify</title>" in (ws / "index.html").read_text(encoding="utf-8")
    assert sf.fill("a {{X}} b", {"X": "{{X}}"}) == "a {{X}} b"
    with pytest.raises(sf.Fail, match="has no value"):
        sf.fill("{{NOPE}}", {})


@pytest.mark.skipif(shutil.which("uv") is None, reason="the end-to-end build runs validate.py through uv")
def test_build_with_the_real_validator(ws):
    td = ws / "package/toy-data/sleep_diary"
    write_json(td / "invalid.json", [{"participant_id": "P12", "site_id": "01", "age": 34, "sleep_minutes": 420,
                                      "nap_yesterday": 0, "nap_minutes": -666}])
    write_json(td / "invalid-ledger.json", {"violations": [{"row": 0, "column": "participant_id", "kind": "pattern-break",
                                                            "value": "P12", "reason": "ids are P + 4 digits"}]})
    code, out = cli("--ws", ws, "build", timeout=900)
    assert "checks" in out
    js = (ws / "site/data/state.js").read_text(encoding="utf-8")
    state = json.loads(js[js.index("=") + 1:js.rindex(";")])
    toy = {e["file"]: e for e in state["toyData"]}
    if out["checks"] and out["checks"].get("ran"):
        bad = toy["invalid"]
        assert bad["rows"][0]["participant_id"] == "P12" and bad["planted"][0]["kind"] == "pattern-break"
        assert [f["column"] for f in bad["errors"]] == ["participant_id"] and bad["errorCount"] == 1
        assert "participant_id" in bad["columns"] and bad["hash"]
        cache = read_json(ws / "state/toy-checks.json")
        assert bad["hash"] in cache
        sf.build(ws, validate=False)                       # a build without validation keeps the results
        js = (ws / "site/data/state.js").read_text(encoding="utf-8")
        again = {e["file"]: e for e in json.loads(js[js.index("=") + 1:js.rindex(";")])["toyData"]}
        assert again["invalid"]["errors"] == bad["errors"]


# ====================================================================== show, activity, share, CLI

def test_show_prints_current_state_and_history(ws):
    rec(ws, question())
    rec(ws, answer("D001", "b"))
    items = sf.show_items(ws, ["S01", "D001", "R001", "topic:sleep", "variable:nap_minutes", "B07",
                               "topic:smoking", "nonsense"])["items"]
    assert items["S01"]["kind"] == "document" and items["S01"]["digest"]["variables"] == 6
    assert items["D001"]["status"] == "answered" and [h["event"] for h in items["D001"]["history"]] == ["open", "answer"]
    assert [(e["pointer"], e["prefix"]) for e in items["R001"]["inSchemas"]] == [
        ("/items/allOf/2", "Skip pattern"), ("/items/allOf/3", "Applicability")]
    topic = items["topic:sleep"]
    assert topic["properties"] == ["nap_minutes", "nap_yesterday", "sleep_minutes"]
    assert [r["variable"] for r in topic["inventory"]] == ["sleep_minutes", "nap_yesterday", "nap_minutes"]
    assert [d["id"] for d in topic["decisions"]] == ["D001"] and [r["id"] for r in topic["rules"]] == ["R001"]
    var = items["variable:nap_minutes"]
    assert var["inSchemas"] == [{"table": "sleep_diary", "topic": "sleep", "file": "package/schemas/" + SLEEP,
                                 "pointer": "/properties/nap_minutes", "x-provenance": {"default": "S01:row 9"}}]
    assert [d["id"] for d in var["decisions"]] == ["D001"] and [r["id"] for r in var["rules"]] == ["R001"]
    assert all("error" in items[k] for k in ("B07", "topic:smoking", "nonsense"))
    code, out = cli("--ws", ws, "show", "D001", "R001")
    assert code == 0 and sorted(out["items"]) == ["D001", "R001"]


def test_activity_tells_the_website(ws):
    rec(ws, {"type": "session", "event": "start"})
    code, out = cli("--ws", ws, "activity", "Drafting", "the", "sleep", "topic")
    assert code == 0 and out["activity"]["text"] == "Drafting the sleep topic" and out["activity"]["session"]
    assert read_json(ws / "state/activity.json")["text"] == "Drafting the sleep topic"
    js = (ws / "site/data/activity.js").read_text(encoding="utf-8")
    assert js.startswith("window.SCHEMIFY_ACTIVITY = ") and "Drafting the sleep topic" in js


def test_share_zips_the_workspace_for_a_reviewer(ws):
    sf.build(ws, validate=False)
    write_json(ws / "state/server.json", {"pid": 0, "port": 9, "url": "http://127.0.0.1:9/"})
    (ws / "state/server.log").write_text("log", encoding="utf-8")
    (ws / "state/server.log.1").write_text("old log", encoding="utf-8")
    (ws / "tools/__pycache__").mkdir()
    (ws / "tools/__pycache__/serve.cpython-312.pyc").write_bytes(b"\0")
    (ws / ".DS_Store").write_bytes(b"\0")
    write_json(ws / "state/presence.json", {"at": sf.now(), "quac": {"connected": True}})
    write_json(ws / "state/recheck.json", {"id": "R1", "dataset": "X01"})
    submit(ws, [{"kind": "note", "text": "not yet taken"}])
    out = sf.share(ws, None)
    dest = Path(out["file"])
    assert dest.parent == ws.parent and re.fullmatch(r"lark-sleep-study-schemify-\d{8}\.zip", dest.name)
    with zipfile.ZipFile(dest) as z:
        names = z.namelist()
        assert z.read("schemify/state/project.json") == (ws / "state/project.json").read_bytes()
    assert names and all(n.startswith("schemify/") for n in names) and out["files"] == len(names)
    for must in ("state/ledger.jsonl", "state/variables.csv", "package/schemas/" + MOTHER, "index.html",
                 "tools/serve.py", "sources/S01-dictionary.csv", "site/data/state.js"):
        assert "schemify/" + must in names, must
    assert not [n for n in names if "server.json" in n or "server.log" in n or "__pycache__" in n
                or n.endswith(".DS_Store") or "presence.json" in n or "recheck.json" in n]
    assert out["warnings"] and "feedback" in out["warnings"][0]
    assert dest.name in out["tell_user"][0]
    code, again = cli("--ws", ws, "share", "--out", ws.parent / "review.zip")
    assert code == 0 and Path(again["file"]) == (ws.parent / "review.zip").resolve()
    with pytest.raises(sf.Fail, match="read-only"):
        sf.share(ws, str(sf.SKILL_DIR / "pytest-share.zip"))
    assert not (sf.SKILL_DIR / "pytest-share.zip").exists()


def test_cli_finds_the_workspace_and_explains_failures(bare, tmp_path, tmp_path_factory):
    code, out = cli("status", cwd=tmp_path)
    assert code == 0 and out["workspace"] == str(bare)
    code, out = cli("status", cwd=bare / "state")
    assert code == 0 and out["workspace"] == str(bare)
    code, out = cli("--ws", tmp_path / "nowhere", "status")
    assert code == 1 and out["ok"] is False and "No schemify workspace at" in out["error"] and out["hint"]
    deep = tmp_path_factory.mktemp("empty") / "a" / "b" / "c" / "d" / "e"     # the search climbs four levels
    deep.mkdir(parents=True)
    code, out = cli("status", cwd=deep)
    assert code == 1 and "No schemify workspace found" in out["error"]
    sf.init(str(tmp_path / "schemify-b"), "Second study", None, None, None)
    code, out = cli("status", cwd=tmp_path)
    assert code == 1 and "Several schemify workspaces" in out["error"] and "--ws" in out["hint"]
    proc = run(SCHEMIFY, "frobnicate", cwd=tmp_path)
    assert proc.returncode == 2 and proc.stdout == ""


# ====================================================================== serve.py

def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def stop_server(ws: Path, pid) -> None:
    """Stop the workspace's server, and make sure its process is gone even when `stop` fails."""
    try:
        run(SERVE, "stop", "--ws", ws, timeout=60)
    finally:
        if pid:
            deadline = time.monotonic() + 5
            while pid_alive(pid) and time.monotonic() < deadline:
                time.sleep(0.1)
            if pid_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass


def request(port: int, method: str, path: str, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        return resp.status, resp.headers, resp.read()
    finally:
        conn.close()


def post_inbox(port: int, payload, token, origin="same", ctype="application/json", host=None, extra=None):
    headers = {"Content-Type": ctype}
    if token is not None:
        headers["X-Schemify-Token"] = token
    if origin == "same":
        headers["Origin"] = f"http://127.0.0.1:{port}"
    elif origin:
        headers["Origin"] = origin
    if host:
        headers["Host"] = host
    headers.update(extra or {})
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    return request(port, "POST", "/api/inbox", body, headers)


@pytest.fixture
def server(ws):
    port = free_port()
    proc = run(SERVE, "start", "--ws", ws, "--port", port, timeout=60)
    info = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
    try:
        assert proc.returncode == 0 and info.get("ok"), proc.stdout + proc.stderr
        token = json.loads(request(port, "GET", "/api/session")[2])["token"]
        yield types.SimpleNamespace(**{**info, "ws": ws, "port": port, "token": token})
    finally:
        stop_server(ws, info.get("pid"))


def test_serve_lifecycle(ws):
    port = free_port()
    code, out = cli("start", "--ws", ws, "--port", port, script=SERVE, timeout=60)
    pid = out.get("pid")
    try:
        assert code == 0 and out["ok"] is True and out["already"] is False
        assert (out["url"], out["port"]) == (f"http://127.0.0.1:{port}/", port)
        info = read_json(ws / "state/server.json")
        assert (info["pid"], info["port"], info["root"]) == (pid, port, str(ws.resolve()))
        code, again = cli("start", "--ws", ws, script=SERVE, timeout=60)
        assert code == 0 and again["already"] is True and again["pid"] == pid
        code, st = cli("status", "--ws", ws, script=SERVE)
        assert code == 0 and st["running"] is True and st["url"] == out["url"]
        code, st = cli("--ws", ws, "serve", "status")                      # the same, through schemify.py
        assert code == 0 and st["running"] is True
        assert sf.status_payload(ws)["websiteServed"] is True and sf.status_payload(ws)["website"] == out["url"]
        status, headers, body = request(port, "GET", "/api/session")
        sess = json.loads(body)
        assert status == 200 and headers["Cache-Control"] == "no-store"
        assert sess["ok"] is True and len(sess["token"]) >= 24 and sess["pending"] == 0
        assert (sess["workspace"], sess["root"], sess["study"]) == \
            (sf.load_project(ws)["id"], str(ws.resolve()), "LARK sleep study")
        code, stopped = cli("stop", "--ws", ws, script=SERVE, timeout=60)
        assert code == 0 and stopped["stopped"] is True
        deadline = time.monotonic() + 5
        while (ws / "state/server.json").exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not (ws / "state/server.json").exists()
        code, st = cli("status", "--ws", ws, script=SERVE)
        assert code == 0 and st["running"] is False
        code, st = cli("stop", "--ws", ws, script=SERVE)
        assert code == 0 and st["stopped"] is False
    finally:
        stop_server(ws, pid)


def test_serve_refuses_a_busy_port(ws):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        code, out = cli("start", "--ws", ws, "--port", s.getsockname()[1], script=SERVE, timeout=60)
    assert code == 1 and out["ok"] is False and "in use" in out["error"] and out["hint"]
    assert not (ws / "state/server.json").exists()


def test_serve_accepts_feedback_from_its_own_page(server):
    proj_id = sf.load_project(server.ws)["id"]
    payload = {"schemifyInbox": 1, "workspace": proj_id, "from": "author", "submittedAt": "2026-10-12T10:00:00.000Z",
               "items": [{"kind": "note", "text": "Bedtimes are local time."}]}
    status, headers, body = post_inbox(server.port, payload, server.token)
    res = json.loads(body)
    assert status == 200 and res["ok"] is True and re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{6}", res["id"])
    saved = read_json(server.ws / "inbox/pending" / f"{res['id']}.json")
    assert saved["items"] == payload["items"] and saved["workspace"] == proj_id
    assert (saved["id"], saved["receivedAt"]) == (res["id"], res["receivedAt"])
    status, _, _ = post_inbox(server.port, payload, server.token, origin=f"http://localhost:{server.port}",
                              host=f"localhost:{server.port}")
    assert status == 200
    status, _, _ = post_inbox(server.port, payload, server.token, origin=None)      # no Origin: not a browser
    assert status == 200
    assert sf.inbox_list(server.ws)["total"] == 3
    assert json.loads(request(server.port, "GET", "/api/session")[2])["pending"] == 3


def test_serve_refuses_foreign_and_malformed_posts(server):
    port, good = server.port, {"items": [{"kind": "note", "text": "x"}]}
    cases = [
        ("wrong Host", dict(host="evil.example"), 403),
        ("Host without the port", dict(host="127.0.0.1"), 403),
        ("foreign Origin", dict(origin="http://evil.example"), 403),
        ("null Origin", dict(origin="null"), 403),
        ("another port's Origin", dict(origin=f"http://127.0.0.1:{port + 1}"), 403),
        ("no token", dict(token=None), 403),
        ("wrong token", dict(token="x" * 32), 403),
        ("text/plain", dict(ctype="text/plain"), 415),
        ("form post", dict(ctype="application/x-www-form-urlencoded"), 415),
        ("empty items", dict(payload={"items": []}), 400),
        ("no items", dict(payload={"schemifyInbox": 1}), 400),
        ("a JSON array", dict(payload=[{"kind": "note"}]), 400),
        ("not JSON", dict(payload=b"{not json"), 400),
        ("oversize", dict(extra={"Content-Length": str(25 * 1024 * 1024 + 1)}), 413),
        ("empty body", dict(payload=b"", extra={"Content-Length": "0"}), 413),
    ]
    for name, kw, expected in cases:
        kw = dict(kw)
        status, _, body = post_inbox(port, kw.pop("payload", good), kw.pop("token", server.token), **kw)
        assert status == expected, name
        assert json.loads(body)["ok"] is False, name
    assert request(port, "GET", "/api/session", headers={"Host": "evil.example"})[0] == 403
    assert request(port, "POST", "/api/other", b"{}", {"Content-Type": "application/json"})[0] == 404
    assert list((server.ws / "inbox/pending").glob("*")) == []


def test_serve_records_whether_the_page_is_connected_to_quac(server):
    def post(payload, **kw):
        headers = {"Content-Type": "application/json", "X-Schemify-Token": kw.get("token", server.token),
                   "Origin": kw.get("origin", f"http://127.0.0.1:{server.port}")}
        return request(server.port, "POST", "/api/presence", json.dumps(payload).encode("utf-8"), headers)[0]
    assert post({"quac": {"connected": True, "dataset": "X01", "status": "sent", "request": "R1", "rows": [[1, 2]],
                          "detail": "x" * 1000}}) == 200
    saved = read_json(server.ws / "state" / "presence.json")
    assert saved["quac"] == {"connected": True, "datasetLoaded": False, "dataset": "X01", "status": "sent",
                             "request": "R1", "detail": "x" * 300}                        # short words, nothing else
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", saved["at"])
    assert post({"quac": {}}, token="x" * 32) == 403
    assert post({"quac": {}}, origin="http://evil.example") == 403
    assert post({"no": "quac"}) == 400
    assert post({"quac": {"detail": "y" * 5000}}) == 413                       # presence is a few words


def test_serve_static_files_stay_inside_the_workspace(server):
    port, ws = server.port, server.ws
    (ws.parent / "outside.txt").write_text("secret", encoding="utf-8")
    os.symlink(ws.parent / "outside.txt", ws / "site" / "link.txt")
    status, h, body = request(port, "GET", "/")
    assert status == 200 and h["Cache-Control"] == "no-store" and h["Content-Type"].startswith("text/html")
    assert body == (ws / "index.html").read_bytes()
    status, h, body = request(port, "GET", "/site/app.js")
    assert status == 200 and h["Cache-Control"] == "no-store" and "javascript" in h["Content-Type"]
    assert body == (ws / "site/app.js").read_bytes()
    status, h, _ = request(port, "GET", "/site/data/state.js")
    assert status == 200 and h["Cache-Control"] == "no-store"
    status, h, _ = request(port, "GET", "/site/LICENSE-json-schema-mark.txt")
    assert status == 200 and h.get("Cache-Control") is None
    status, h, body = request(port, "HEAD", "/index.html")
    assert status == 200 and body == b"" and int(h["Content-Length"]) == (ws / "index.html").stat().st_size
    for path in ("/../outside.txt", "/%2e%2e/outside.txt", "/site/../../outside.txt", "/site/link.txt"):
        status, _, body = request(port, "GET", path)
        assert status == 403 and b"secret" not in body, path
    for path in ("/state/server.json", "/state/../state/server.json", "/missing.html", "/site/", "/api/whatever"):
        assert request(port, "GET", path)[0] == 404, path
    assert request(port, "GET", "/index.html", headers={"Host": "evil.example"})[0] == 403


# ====================================================================== migrate.py

def test_migrate_reads_1x_decision_lines():
    recs = mg.parse_decisions((FIXTURE_1X / "json_schema/DECISIONS.md").read_text(encoding="utf-8"))
    assert [r["old"] for r in recs] == [f"D{n:03d}" for n in range(1, 17)]
    d5, d8, d13 = recs[4], recs[7], recs[12]
    assert (d5["scope"], d5["date"]) == ("sleep_diary/sleep.sleep_minutes", "2026-08-21")
    assert (d5["confidence"], d5["status"]) == ("agent-decided · user-confirmed (review 2026-08-21)", "active")
    assert (d8["confidence"], d8["status"]) == ("agent-decided", "superseded-by D009")
    assert d13["confidence"] == "open"
    kinds = [mg.guess_kind(r) for r in recs]
    assert kinds[:5] == ["convention", "convention", "convention", "knowledge", "guess"]
    assert (kinds[9], kinds[12], kinds[14]) == ("rule", "gap", "rule")
    assert mg.scope_targets("sleep_diary/sleep.bedtime") == ["bedtime"] and mg.scope_targets("package") == []


@pytest.fixture(scope="module")
def migrated(tmp_path_factory):
    root = tmp_path_factory.mktemp("migration") / "study"
    shutil.copytree(FIXTURE_1X, root)
    before = snapshot(root)
    proc = run(MIGRATE, "--from", "json_schema", "--person", "steward", cwd=root, timeout=300)
    out = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
    return types.SimpleNamespace(root=root, ws=root / "schemify", proc=proc, out=out, before=before,
                                 m=out.get("idMap") or {})


def test_migrate_creates_the_workspace(migrated):
    assert migrated.proc.returncode == 0, migrated.proc.stdout + migrated.proc.stderr
    out = migrated.out
    assert out["ok"] is True and Path(out["workspace"]) == migrated.ws.resolve() and sf.is_workspace(migrated.ws)
    assert (out["tables"], out["topics"]) == (["sleep_diary"], ["participant", "sleep"])
    assert out["sources"]["source/dictionary.csv"] == "S01" and (out["decisions"], out["rules"]) == (16, 2)
    assert out["idMap"] == {f"D{n:03d}": f"D{n:03d}" for n in range(1, 17)}
    proj = sf.load_project(migrated.ws)
    assert proj["study"] == "LARK sleep-diary study" and proj["idBase"] == BASE
    assert proj["tables"] == [{"name": "sleep_diary", "title": "Sleep diary",
                               "grain": "One element is one participant-night.", "mother": MOTHER}]
    assert [t["file"] for t in proj["topics"]] == [PARTICIPANT, SLEEP]
    assert [(s["code"], s["structural"]) for s in proj["conventions"]["sentinels"]] == [(-666, True), (-888, False)]
    assert proj["people"][0]["role"] == "steward"


def test_migrate_registers_the_dictionary(migrated):
    w = sf.load_world(migrated.ws)
    assert sorted(w.sources) == ["S01"]                  # the questionnaire has no file or URL: left to a person
    s1 = w.sources["S01"]
    assert (s1["kind"], s1["status"]) == ("document", "active")
    assert s1["path"] == "sources/dictionary.csv"        # copies keep their original file names
    assert (migrated.ws / s1["path"]).read_bytes() == (migrated.root / "source/dictionary.csv").read_bytes()
    assert s1["digest"]["path"] == "sources/S01/DIGEST.md" and (migrated.ws / s1["digest"]["path"]).is_file()


def test_migrate_maps_every_decision(migrated):
    w, m = sf.load_world(migrated.ws), migrated.m
    d = {old: w.decisions[new] for old, new in m.items()}
    assert len(w.decisions) == 16
    assert d["D008"]["status"] == "superseded" and d["D008"]["replacement"] == m["D009"]
    assert d["D009"]["status"] == "answered" and d["D009"]["answer"]["by"] == "steward"
    assert d["D005"]["status"] == "confirmed" and d["D005"]["confirmations"][0]["by"] == "steward"
    assert (d["D013"]["status"], d["D013"]["kind"], d["D013"]["targets"]) == ("open", "gap", ["melatonin_use"])
    assert (d["D004"]["kind"], d["D004"]["targets"]) == ("knowledge", ["site_id"])
    assert d["D010"]["kind"] == "rule" and d["D001"]["kind"] == "convention"
    assert not [k for k, v in d.items() if v["unapplied"]]          # what 1.x settled is in the schemas already
    assert all("migrated from 1.x" in (v["history"][0].get("note") or "") for v in d.values())


def test_migrate_cites_the_live_decision(migrated):
    m, schemas = migrated.m, migrated.ws / "package/schemas"
    sleep = read_json(schemas / SLEEP)["properties"]
    assert sleep["bedtime"]["x-provenance"] == {"default": "S01:row 5", "pattern": m["D009"]}
    assert list(sleep["bedtime"])[:3] == ["title", "$comment", "x-provenance"]
    assert sleep["sleep_minutes"]["x-provenance"] == {"default": "S01:row 6", "minimum": m["D005"],
                                                      "maximum": m["D005"]}
    assert read_json(schemas / PARTICIPANT)["properties"]["site_id"]["x-provenance"] == {"default": m["D004"]}
    pkg = sf.Pkg(migrated.ws, sf.load_project(migrated.ws))
    assert m["D008"] not in {str(ref).split(":")[0] for _, _, ref in pkg.provenance_refs()}
    conds = [e for e in read_json(schemas / MOTHER)["items"]["allOf"] if "if" in e]
    assert [list(e)[:2] for e in conds] == [["$comment", "x-provenance"]] * 2
    assert all(e["x-provenance"] == {"default": "S01:row 9"} for e in conds)
    defs = read_json(schemas / DEFS)["$defs"]
    assert defs["not_applicable"]["x-value-kind"] == defs["dont_know"]["x-value-kind"] == "sentinel"
    assert "x-value-kind" not in defs["participant_id"]


def test_migrate_registers_the_rules(migrated):
    w, m = sf.load_world(migrated.ws), migrated.m
    r1, r2 = w.rules["R001"], w.rules["R002"]
    assert (r1["status"], r1["evidence"], r1["gates"], r1["targets"]) == \
        ("encoded", "documented", ["nap_yesterday"], ["nap_minutes"])
    assert (r1["refs"], r1["decision"]) == (["S01:row 9"], m["D010"])
    assert (r2["status"], r2["evidence"], r2["gates"], r2["decision"]) == \
        ("not-expressible", "implied", [], m["D015"])
    assert [r["id"] for r in sf.Pkg(migrated.ws, w.project).rules] == ["R001", "R001"]


def test_migrate_maps_the_inventory(migrated):
    rows, problems = sf.read_inventory(migrated.ws)
    by = {r["variable"]: r for r in rows}
    assert problems == [] and len(rows) == 12 and {r["table"] for r in rows} == {"sleep_diary"}
    assert (by["site_id"]["status"], by["site_id"]["source"]) == ("added", migrated.m["D004"])
    assert (by["melatonin_use"]["status"], by["melatonin_use"]["source"]) == ("deferred", "S01:row 11")
    assert (by["bedtime"]["status"], by["bedtime"]["source"]) == ("include", "S01:row 5")
    assert (by["age"]["topic"], by["nap_minutes"]["topic"]) == ("participant", "sleep")


def test_migrate_keeps_confirmed_topics_confirmed(migrated):
    w = sf.load_world(migrated.ws)
    topics = sf.topic_statuses(w, sf.Pkg(migrated.ws, w.project), None)
    assert {t["id"]: t["status"] for t in topics} == {"participant": "confirmed", "sleep": "confirmed"}
    assert all(w.topics[t]["approvals"][0]["by"] == "steward" for t in ("participant", "sleep"))


def test_migrated_approvals_cover_the_files_as_the_migration_leaves_them(migrated, tmp_path):
    ws = tmp_path / "schemify"
    shutil.copytree(migrated.ws, ws)
    statuses = lambda: {t["id"]: t["status"] for t in sf.topic_statuses(sf.load_world(ws), sf.Pkg(ws, sf.load_project(ws)), None)}
    edit(ws, SLEEP, lambda d: d["properties"]["nap_minutes"].update(description="Minutes napped"))  # a house-style fix
    assert statuses() == {"participant": "confirmed", "sleep": "confirmed"}
    rec(ws, {"type": "milestone", "event": "reach", "id": "migrated", "note": "Left to do is done"})
    edit(ws, SLEEP, lambda d: d["properties"]["nap_minutes"].update(description="Nap length"))     # later work
    assert statuses()["participant"] == "confirmed" and statuses()["sleep"] not in ("confirmed", "in-review")


def test_migrate_copies_the_toy_data(migrated):
    td, ex = migrated.ws / "package/toy-data/sleep_diary", migrated.root / "json_schema/examples"
    for new, old in (("valid.json", "toy_valid.json"), ("invalid.json", "toy_invalid.json"),
                     ("invalid-ledger.json", "toy_invalid_ledger.json")):
        assert read_json(td / new) == read_json(ex / old), new
    assert (td / "valid.csv").is_file()


def test_migrate_lists_what_is_left_to_do(migrated):
    att = migrated.out["attention"]
    for name in ("not_applicable", "dont_know", "participant_id", "date_iso"):
        assert any("common/defs.json" in a and f"$defs/{name}" in a and "x-provenance" in a for a in att), name
    assert any("without a URL" in a for a in att)
    assert migrated.out["attentionTotal"] == len(att)
    text = (migrated.ws / "sources/MIGRATION.md").read_text(encoding="utf-8")
    assert "| D008 | D008 |" in text and all(a in text for a in att)


def test_migrate_closes_its_session_and_steers_status(migrated, tmp_path):
    w = sf.load_world(migrated.ws)
    assert w.open_session() is None and w.sessions[-1]["harness"] == "migration"
    assert "sources/MIGRATION.md" in w.sessions[-1]["end"]["handoff"]
    nxt = [a["action"] for a in sf.status_payload(migrated.ws)["next"]]
    assert nxt[0] == "migrate" and "finish" not in nxt          # every topic is confirmed, but the migration is not done
    work = tmp_path / "after-migration"
    shutil.copytree(migrated.ws, work / "schemify")
    rec(work / "schemify", {"type": "milestone", "event": "reach", "id": "migrated", "note": "Left to do worked through"})
    assert "migrate" not in [a["action"] for a in sf.status_payload(work / "schemify")["next"]]


def test_migrate_leaves_the_old_folder_untouched(migrated):
    assert snapshot(migrated.root, skip=("schemify",)) == migrated.before


def test_migrate_refuses_an_existing_workspace(migrated):
    before = ledger_bytes(migrated.ws)
    code, out = cli("--from", "json_schema", "--person", "steward", script=MIGRATE, cwd=migrated.root, timeout=300)
    assert code == 1 and out["ok"] is False and "already exists" in out["error"] and out["hint"]
    assert ledger_bytes(migrated.ws) == before


def test_migrate_refuses_what_is_not_a_1x_package(tmp_path):
    code, out = cli("--from", "nowhere", script=MIGRATE, cwd=tmp_path)
    assert code == 1 and "is not a folder" in out["error"]
    (tmp_path / "json_schema").mkdir()
    (tmp_path / "json_schema/README.md").write_text("a README, no schemas", encoding="utf-8")
    code, out = cli("--from", "json_schema", script=MIGRATE, cwd=tmp_path)
    assert code == 1 and "No */*.schema.json" in out["error"] and "1.x package" in out["hint"]
    assert not (tmp_path / "schemify").exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
