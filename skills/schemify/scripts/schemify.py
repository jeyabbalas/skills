#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The schemify workspace tool: the ledger, the question queue, the website's data,
and the session bookkeeping that lets any later agent pick the work up cold.

Usage:     uv run <skill-dir>/scripts/schemify.py <command> [--ws schemify] [...]
Fallback:  python3 <skill-dir>/scripts/schemify.py <command> ...   (standard library only)

Commands -- each prints one JSON object on stdout:
  init      --study NAME [--dir schemify] [--invoke /schemify] [--harness H]
            Create the workspace (idempotent).
  open      [--mode build|review] [--harness H] [--model M] [--no-serve]
            Start a session: record it, start the website, print status.
  status    Where the work stands, what waits on people, and what to do next.
  record    [--file F]  One JSON event or an array of them on stdin; validated,
            assigned ids, appended to state/ledger.jsonl. Nothing is written
            unless every event is valid.
  show      ID ...  S01, D014, R003, B02, A01, X01, topic:<id>, variable:<name>
  queue     [--for author|steward] [--topic T] [--limit N]
            What needs a person, ranked; low-stakes guesses grouped for one-click review.
  inbox     list | take ID | import FILE
            Feedback from the website. `take` records every answer, approval and
            comment in the ledger and prints what is left for you to do.
  build     [--no-validate]  Regenerate the website's data and the package's
            generated files (README, PROVENANCE, provenance.json, dictionary, CSVs).
  check     Verify everything: state, inventory coverage, provenance, rules, the
            validator. Run it before closing a session.
  activity  TEXT  Tell the website what you are doing right now.
  close     JSON {"summary", "handoff", "next"[, "force"]} on stdin. Ends the
            session; refuses while feedback is unprocessed or answers unapplied.
  data-check  X01 [--timeout SECONDS]  Run QuaC on a dataset a person allowed you
            to check (DATA-CHECK.md) and import its findings without data. QuaC's
            own messages are never shown: they can quote the data.
  serve     start|stop|status   The website server (serve.py).
  share     [--out PATH]  Zip the workspace for a reviewer.
  refresh-assets  Re-copy the website's files and tools from this skill.

Exit codes: 0 ok; 1 refused or failed -- the JSON carries "error" and "hint"; 2 bad
arguments. Output is bounded: long lists are cut and say so.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
WS_FORMAT = 2
STATE_JS_FORMAT = 1
QUAC_APP = "https://jeyabbalas.github.io/quac/"
QUAC_CLI = "npx --yes @jeyabbalas/quac@1.2.0"
LIST_CAP = 40            # items per list in stdout before "truncated" -- agents' harnesses cut at ~10-30K chars
REOPEN_HOURS = 12        # an unclosed session younger than this is resumed, not duplicated

# Files this skill ships into every workspace (skill path -> workspace path).
SHIPPED = [
    ("assets/site/app.js", "site/app.js"),
    ("assets/site/schemify.css", "site/schemify.css"),
    ("assets/json-schema-data-dictionary.global.js", "site/json-schema-data-dictionary.global.js"),
    ("assets/embed-worker.js", "site/embed-worker.js"),
    ("scripts/serve.py", "tools/serve.py"),
    ("scripts/validate.py", "package/tools/validate.py"),
    ("assets/json-schema-data-dictionary.global.js", "package/assets/json-schema-data-dictionary.global.js"),
    ("assets/embed-worker.js", "package/assets/embed-worker.js"),
    ("assets/site/schemify.css", "package/assets/schemify.css"),
    ("assets/LICENSE-json-schema-mark.txt", "site/LICENSE-json-schema-mark.txt"),
    ("assets/LICENSE-json-schema-mark.txt", "package/assets/LICENSE-json-schema-mark.txt"),
]
TEMPLATES = ["templates/index.html", "templates/dictionary.html", "assets/json-schema-mark.svg"]
REQUIREMENTS = "jsonschema>=4.18\nreferencing>=0.35\n"

DECISION_KINDS = {"conflict", "gap", "ambiguity", "guess", "rule", "consent", "structure", "convention",
                  "interview", "knowledge", "alignment", "bulk", "feedback"}
DATA_KINDS = {"conflict", "gap", "ambiguity", "guess", "rule", "consent", "alignment", "bulk"}   # questions about variables
PROVISIONAL_KINDS = {"conflict", "gap", "ambiguity", "guess", "rule", "consent", "alignment"}
EVIDENCE_KINDS = {"conflict", "ambiguity", "alignment"}
CONSENT_YES = {"yes", "always", "known"}
RULE_STATUSES = {"suspected", "waiting", "encoded", "deferred", "declined", "not-expressible"}
RULE_EVIDENCE = {"documented", "implied", "told", "inferred"}
PEOPLE = {"author", "steward"}
ACTORS = PEOPLE | {"agent"}
MILESTONES = {"migrated", "ready-for-review", "review-complete", "finished"}
REF_RE = re.compile(r"^(S\d{2,})(?::([^\n|]+))?$|^(D\d{3,})$")
ID_RE = {"source": re.compile(r"^S\d{2,}$"), "decision": re.compile(r"^D\d{3,}$"),
         "rule": re.compile(r"^R\d{3,}$"), "batch": re.compile(r"^B\d{2,}$"),
         "alignment": re.compile(r"^A\d{2,}$"), "dataset": re.compile(r"^X\d{2,}$")}
ID_PREFIX = {"source": ("S", 2), "decision": ("D", 3), "rule": ("R", 3), "batch": ("B", 2), "alignment": ("A", 2),
             "dataset": ("X", 2)}
DATASET_BASES = {"public", "local-model", "browser"}   # how a dataset gets checked without its data reaching you:
# public or local-model — a person let you run QuaC on it (`data-check`); browser — their own browser keeps it
# in QuaC, and the website asks QuaC to re-run (`data-check` asks the page, and waits for the findings).
PRESENCE_FRESH = 45                              # seconds: a connected website reports every few seconds
QUAC_EXIT = {1: "QuaC refused its arguments", 2: "QuaC could not read the dataset (unreadable, an unsupported format, "
             "too large, or a workbook with several sheets and no sheet named)", 3: "QuaC could not load the schema files",
             4: "QuaC's run failed before the findings were complete", 5: "QuaC could not write the findings file",
             130: "QuaC was interrupted"}
RULE_COMMENT_RE = re.compile(r"^(Skip pattern|Applicability|[A-Z][A-Za-z]*(?: [A-Za-z]+)* routing) (R\d{3,}):\s*(.*)$", re.S)
INVENTORY_COLUMNS = ["variable", "table", "topic", "status", "source", "note"]
INVENTORY_STATUSES = {"include", "deferred", "dropped", "added"}


class Fail(Exception):
    def __init__(self, error: str, hint: str, **extra):
        super().__init__(error)
        self.error, self.hint, self.extra = error, hint, extra


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def emit(payload: dict, code: int = 0) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    sys.exit(code)


def capped(items: list, cap: int = LIST_CAP) -> dict:
    return {"items": items[:cap], "total": len(items), "truncated": len(items) > cap}


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"{path} is not readable JSON: {exc}", "Fix or restore the file; `check` names what is wrong.")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def slugify(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:maxlen].rstrip("-")) or "study"


def sha12(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


# ===================================================================== workspace

def is_workspace(p: Path) -> bool:
    return (p / "state" / "project.json").is_file()


def guard(p: Path) -> None:
    rp = p.resolve()
    if rp == SKILL_DIR or SKILL_DIR in rp.parents:
        raise Fail(f"{p} is inside the skill directory, which is read-only.",
                   "Workspaces live in the user's own folder: run from the directory the user invoked you in.")


def find_ws(arg: str | None) -> Path:
    if arg:
        p = Path(arg).expanduser()
        if is_workspace(p):
            guard(p)
            return p.resolve()
        if is_workspace(p / "schemify"):
            return (p / "schemify").resolve()
        raise Fail(f"No schemify workspace at {arg}.",
                   "Pass the folder that holds state/project.json (usually ./schemify), or create one with `init`.")
    cwd = Path.cwd()
    for base in [cwd, *list(cwd.parents)[:4]]:
        if is_workspace(base):
            return base.resolve()
        found = sorted(d.parent.parent for d in base.glob("schemify*/state/project.json"))
        if len(found) == 1:
            return found[0].resolve()
        if len(found) > 1:
            raise Fail("Several schemify workspaces here: " + ", ".join(str(f) for f in found),
                       "Pass --ws with the one this session is about.")
    raise Fail("No schemify workspace found from here.",
               "A fresh start: `init --study \"<name>\"` (START.md). Otherwise pass --ws <path>.")


def load_project(ws: Path) -> dict:
    proj = read_json(ws / "state" / "project.json", {})
    if not isinstance(proj, dict):
        raise Fail("state/project.json is not a JSON object.", "Restore it from version control or re-create it (LEDGER-FORMAT.md).")
    return proj


def save_project(ws: Path, proj: dict) -> None:
    write_json(ws / "state" / "project.json", proj)


# ===================================================================== ledger

def ledger_path(ws: Path) -> Path:
    return ws / "state" / "ledger.jsonl"


def read_ledger(ws: Path) -> list[dict]:
    p = ledger_path(ws)
    if not p.exists():
        return []
    events = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Fail(f"state/ledger.jsonl line {n} is not JSON ({exc}).",
                       "The ledger is append-only and written only by `record`; restore the line from version control.")
        if not isinstance(ev, dict):
            raise Fail(f"state/ledger.jsonl line {n} is not a JSON object.", "Restore the line from version control.")
        ev["_line"] = n
        events.append(ev)
    return events


def append_ledger(ws: Path, events: list[dict]) -> None:
    p = ledger_path(ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = "".join(json.dumps({k: v for k, v in e.items() if not k.startswith("_")}, ensure_ascii=False) + "\n"
                    for e in events)
    with open(p, "a", encoding="utf-8") as fh:
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        fh.write(lines)
        fh.flush()
        os.fsync(fh.fileno())


class World:
    """The ledger replayed: current state of every record, plus its history."""

    def __init__(self, project: dict, events: list[dict]):
        self.project = project
        self.events = events
        self.sources: dict[str, dict] = {}
        self.decisions: dict[str, dict] = {}
        self.rules: dict[str, dict] = {}
        self.batches: dict[str, dict] = {}
        self.topics: dict[str, dict] = {}
        self.sessions: list[dict] = []
        self.alignment: dict[str, dict] = {}
        self.datasets: dict[str, dict] = {}
        self.milestones: dict[str, str] = {}
        self.finished_set: str | None = None
        self.migrated_hashes: dict[str, str] = {}
        self.seq = 0                 # ledger position: what came after what (`at` ties within a second)
        for ev in events:
            self.apply(ev)
        for d in self.decisions.values():
            finish_decision(d)
        # A decision that only explains a rule not (yet) in the schemas has nothing to apply.
        for r in self.rules.values():
            if r.get("status") in ("suspected", "deferred", "declined", "waiting", "not-expressible"):
                d = self.decisions.get(r.get("decision") or "")
                if d and d["status"] in ("provisional", "decided", "confirmed"):
                    d["unapplied"] = False

    # -- generic helpers
    @staticmethod
    def _hist(rec: dict, ev: dict) -> None:
        rec.setdefault("history", []).append({k: v for k, v in ev.items() if not k.startswith("_") and k != "type"})

    def apply(self, ev: dict) -> None:
        self.seq += 1
        t, e = ev.get("type"), ev.get("event")
        handler = getattr(self, f"_{t}", None)
        if handler:
            handler(e, ev)

    # -- sources
    def _source(self, e: str, ev: dict) -> None:
        sid = ev.get("id")
        if e == "add":
            web_found = ev.get("kind") == "web" and ev.get("origin", "user") == "agent"
            self.sources[sid] = {"id": sid, "kind": ev.get("kind"), "title": ev.get("title"), "what": ev.get("what"),
                                 "path": ev.get("path"), "original": ev.get("original"), "url": ev.get("url"),
                                 "origin": ev.get("origin", "user"), "status": "suggested" if web_found else "active",
                                 "notes": [ev["notes"]] if ev.get("notes") else [], "added": ev.get("at")}
        rec = self.sources.get(sid)
        if rec is None:
            return
        if e == "approve":
            rec["status"], rec["verdict"] = "approved", {"by": ev.get("by"), "at": ev.get("at"), "note": ev.get("note")}
        elif e == "reject":
            rec["status"], rec["verdict"] = "rejected", {"by": ev.get("by"), "at": ev.get("at"), "note": ev.get("note")}
        elif e == "extract":
            rec["extract"] = {"dir": ev.get("dir"), "files": ev.get("files"), "at": ev.get("at")}
        elif e == "digest":
            rec["digest"] = {"path": ev.get("path"), "variables": ev.get("variables"),
                             "verified": ev.get("verified") or [], "at": ev.get("at")}
        elif e == "update":
            for k in ("title", "what", "path", "url"):
                if ev.get(k):
                    rec[k] = ev[k]
            if ev.get("notes"):
                rec["notes"].append(ev["notes"])
        elif e == "retire":
            rec["status"] = "retired"
        self._hist(rec, ev)

    # -- decisions
    def _decision(self, e: str, ev: dict) -> None:
        did = ev.get("id")
        rec = self.decisions.get(did)
        if rec is None:
            rec = self.decisions[did] = new_decision(did, ev)
        else:
            for k in DECISION_FIELDS:
                if e == "open" and ev.get(k) is not None:
                    rec[k] = ev[k]
        order = rec.setdefault("_order", {})     # ledger positions; finish_decision compares and drops them
        if e == "answer":
            rec["answer"] = {**{k: ev.get(k) for k in ("by", "choice", "choices", "text", "note", "via", "at")}, "seq": self.seq}
            if ev.get("choice") != "unsure":
                rec["changedAt"] = ev.get("at")
                order["answer"] = order["changed"] = self.seq
            else:
                rec["unsure"] = True
        elif e == "decide":
            rec["agentDecision"] = {"choice": ev.get("choice"), "why": ev.get("why"), "at": ev.get("at"),
                                    "review": ev.get("review", "needed")}
            rec["changedAt"] = ev.get("at")
            order["agent"] = order["changed"] = self.seq
            for k in DECISION_FIELDS:            # a decide may create the record
                if ev.get(k) is not None and not rec.get(k):
                    rec[k] = ev[k]
        elif e == "confirm":
            rec["confirmations"].append({"by": ev.get("by"), "at": ev.get("at"), "note": ev.get("note"), "via": ev.get("via")})
            order["confirm"] = self.seq
        elif e == "apply":
            rec["appliedAt"] = ev.get("at")
            rec["appliedFiles"] = ev.get("files") or []
            order["applied"] = self.seq
            for tid, h in (ev.get("approvedHashes") or {}).items():
                approvals = (self.topics.get(tid) or {}).get("approvals") or []
                if approvals:
                    approvals[-1]["hash"] = h        # their answer was part of what they approved
        elif e == "supersede":
            rec["replacement"] = ev.get("replacement")
        elif e == "cancel":
            rec["cancelled"] = True
        if ev.get("applied") is True and e in ("answer", "decide", "open"):
            rec["appliedAt"] = ev.get("at")
            order["applied"] = self.seq
        self._hist(rec, ev)

    # -- rules
    def _rule(self, e: str, ev: dict) -> None:
        rid = ev.get("id")
        if e == "add":
            self.rules[rid] = {"id": rid, "added": ev.get("at")}
        rec = self.rules.get(rid)
        if rec is None:
            return
        for k in RULE_FIELDS:
            if k in ev:
                rec[k] = ev[k]
        self._hist(rec, ev)

    # -- batches
    def _batch(self, e: str, ev: dict) -> None:
        bid = ev.get("id")
        if e == "post":
            self.batches[bid] = {"id": bid, "to": ev.get("to"), "title": ev.get("title"), "items": list(ev.get("items") or []),
                                 "note": ev.get("note"), "postedAt": ev.get("at"), "withdrawn": False}
            for did in ev.get("items") or []:
                if did in self.decisions:
                    self.decisions[did]["batch"] = bid
                    self.decisions[did]["askedAt"] = ev.get("at")
                    self.decisions[did]["askedSeq"] = self.seq
                    self.decisions[did]["askedTo"] = ev.get("to")
        elif e == "withdraw" and bid in self.batches:
            self.batches[bid]["withdrawn"] = True
            for did in self.batches[bid]["items"]:
                d = self.decisions.get(did)
                if d and d.get("batch") == bid:
                    d["batch"] = None

    # -- topics
    def _topic(self, e: str, ev: dict) -> None:
        tid = ev.get("id")
        rec = self.topics.setdefault(tid, {"id": tid, "review": None, "approvals": [], "changes": [], "presentedAt": None})
        if e == "present":
            rec["review"], rec["presentedAt"], rec["presentNote"] = "in-review", ev.get("at"), ev.get("note")
        elif e == "approve":
            rec["review"] = "confirmed"
            rec["approvals"].append({"by": ev.get("by"), "at": ev.get("at"), "via": ev.get("via"), "note": ev.get("note"),
                                     "hash": ev.get("hash"), "seq": self.seq})
        elif e == "changes":
            rec["review"] = "changes-requested"
            rec["changes"].append({"by": ev.get("by"), "at": ev.get("at"), "via": ev.get("via"), "text": ev.get("text")})
        self._hist(rec, ev)

    # -- sessions, alignment, milestones
    def _session(self, e: str, ev: dict) -> None:
        if e == "start":
            self.sessions.append({"id": ev.get("id"), "mode": ev.get("mode", "build"), "harness": ev.get("harness"),
                                  "model": ev.get("model"), "startedAt": ev.get("at"), "end": None})
        elif e == "end":
            for s in reversed(self.sessions):
                if s["id"] == ev.get("id"):
                    s["end"] = {k: ev.get(k) for k in ("summary", "handoff", "next", "at", "forced")}
                    break

    def _alignment(self, e: str, ev: dict) -> None:
        aid = ev.get("id")
        if e == "add":
            self.alignment[aid] = {"id": aid, "triage": {}, **{k: ev.get(k) for k in
                                   ("file", "label", "records", "failing", "checks", "fingerprint", "current", "via", "at", "note",
                                    "ruleMap", "planned", "by", "dataset", "accepts")}}
        rec = self.alignment.get(aid)
        if rec is not None and e == "triage":
            rec["triage"][ev.get("check")] = {"verdict": ev.get("verdict"), "decision": ev.get("decision"),
                                              "note": ev.get("note"), "at": ev.get("at")}

    def _dataset(self, e: str, ev: dict) -> None:
        xid = ev.get("id")
        if e == "allow":
            self.datasets[xid] = {"id": xid, "withdrawn": None, **{k: ev.get(k) for k in
                                  ("path", "label", "table", "sheet", "basis", "model", "by", "via", "text", "at")}}
        elif e == "withdraw" and xid in self.datasets:
            self.datasets[xid]["withdrawn"] = {k: ev.get(k) for k in ("by", "via", "note", "at")}

    def _milestone(self, e: str, ev: dict) -> None:
        if e == "reach":
            self.milestones[ev.get("id")] = ev.get("at")
            if ev.get("id") == "finished":
                self.finished_set = ev.get("setId")      # the schema files the person was told were finished
            elif ev.get("id") == "migrated":
                self.migrated_hashes = ev.get("topicHashes") or {}   # what approvals carried over from 1.x now cover

    # -- queries
    def open_session(self) -> dict | None:
        if self.sessions and self.sessions[-1]["end"] is None:
            return self.sessions[-1]
        return None

    def last_closed(self) -> dict | None:
        for s in reversed(self.sessions):
            if s["end"]:
                return s
        return None


DECISION_FIELDS = ("kind", "question", "topic", "table", "targets", "context", "evidence", "input", "options",
                   "recommended", "why", "provisional", "importance", "to", "covers")
RULE_FIELDS = ("table", "gates", "targets", "reading", "evidence", "refs", "status", "waits_for", "decision",
               "consent", "note")


def new_decision(did: str, ev: dict) -> dict:
    d = {"id": did, "created": ev.get("at"), "targets": [], "evidence": [], "options": [], "covers": [],
         "input": "choice", "importance": "normal", "to": "any", "answer": None, "agentDecision": None,
         "confirmations": [], "appliedAt": None, "changedAt": None, "batch": None, "replacement": None,
         "cancelled": False, "unsure": False}
    for k in DECISION_FIELDS:
        if ev.get(k) is not None:
            d[k] = ev[k]
    return d


def finish_decision(d: dict) -> None:
    order = d.pop("_order", {})
    ans = d.get("answer")
    agent = d.get("agentDecision")
    if d.get("cancelled"):
        status = "cancelled"
    elif d.get("replacement"):
        status = "superseded"
    elif ans and ans.get("choice") != "unsure" and (not agent or order.get("answer", 0) > order.get("agent", 0)):
        status = "answered"
    elif agent:
        if order.get("confirm", 0) > order.get("agent", 0):
            status = "confirmed"
        elif agent.get("review", "needed") == "none":
            status = "decided"                      # mechanical: nothing a person needs to review
        else:
            status = "provisional"
    elif ans and ans.get("choice") == "unsure":
        status = "unsure"
    elif d.get("batch"):
        status = "asked"
    else:
        status = "open"
    d["status"] = status
    d["needsReview"] = status == "provisional"
    d["reviewer"] = "steward" if d.get("unsure") else "any"
    applied = order.get("applied")
    d["unapplied"] = status in ("answered", "provisional", "decided", "confirmed", "unsure") and (
        status == "unsure" or applied is None or order.get("changed", 0) > applied)


def load_world(ws: Path) -> World:
    world = World(load_project(ws), read_ledger(ws))
    world.ws = ws
    return world


# ===================================================================== record: validation

def next_id(kind: str, used: set[str]) -> str:
    prefix, width = ID_PREFIX[kind]
    nums = [int(i[len(prefix):]) for i in used if ID_RE[kind].match(i or "")]
    return f"{prefix}{(max(nums) if nums else 0) + 1:0{width}d}"


RUN_RE = re.compile(r"^A\d{2,}$")


def check_ref(ref, world: World, pending: dict, where: str, errors: list[str], runs: bool = False) -> None:
    if runs and isinstance(ref, str) and RUN_RE.match(ref):
        if ref not in world.alignment and ref not in pending["alignment"]:
            errors.append(f"{where}: data-check run {ref} does not exist")
        return
    if not isinstance(ref, str) or not REF_RE.match(ref):
        errors.append(f"{where}: {ref!r} is not a reference (write S01, S01:<locator>, or D014" + (", or A01" if runs else "") + ")")
        return
    rid = ref.split(":", 1)[0]
    if rid.startswith("S") and rid not in world.sources and rid not in pending["source"]:
        errors.append(f"{where}: source {rid} is not registered")
    if rid.startswith("D") and rid not in world.decisions and rid not in pending["decision"]:
        errors.append(f"{where}: decision {rid} does not exist")


def str_list(v) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) and x for x in v)


def validate_event(ev: dict, world: World, pending: dict, n: int, creating_hint: bool = False) -> list[str]:
    t, e = ev.get("type"), ev.get("event")
    where = f"event {n} ({t}.{e})"
    errs: list[str] = []
    topics = {tp.get("id") for tp in world.project.get("topics", [])}
    tables = {tb.get("name") for tb in world.project.get("tables", [])}

    def need(*keys):
        for k in keys:
            if ev.get(k) in (None, "", []):
                errs.append(f"{where}: missing '{k}'")

    def person():
        if ev.get("by") not in PEOPLE:
            errs.append(f"{where}: 'by' must be 'author' or 'steward' — only a person can do this")

    def existing(kind, pool):
        rid = ev.get("id")
        if not rid or rid not in pool and rid not in pending[kind]:
            errs.append(f"{where}: {kind} {rid!r} does not exist")

    if ev.get("by") is not None and ev.get("by") not in ACTORS:
        errs.append(f"{where}: 'by' must be one of agent, author, steward")
    if t == "source":
        if e == "add":
            need("kind", "title", "what")
            if ev.get("kind") not in ("document", "web"):
                errs.append(f"{where}: kind must be 'document' or 'web'")
            if ev.get("kind") == "document" and not ev.get("path"):
                errs.append(f"{where}: a document needs 'path' (its copy under schemify/sources/)")
            if ev.get("kind") == "web" and not ev.get("url"):
                errs.append(f"{where}: a web source needs 'url'")
            if ev.get("origin", "user") not in ("user", "agent"):
                errs.append(f"{where}: origin must be 'user' or 'agent'")
        elif e in ("approve", "reject"):
            existing("source", world.sources)
            person()
        elif e == "extract":
            existing("source", world.sources)
            need("dir")
        elif e == "digest":
            existing("source", world.sources)
            need("path")
            if ev.get("verified") is not None and not str_list(ev.get("verified")):
                errs.append(f"{where}: 'verified' is a list of locators you spot-checked")
        elif e in ("update", "retire"):
            existing("source", world.sources)
            if e == "retire":
                need("note")
        else:
            errs.append(f"{where}: unknown source event (add, approve, reject, extract, digest, update, retire)")
    elif t == "decision":
        # record_events assigns a creating event its id before validating it, so it says which events create
        creating = e == "open" or (e in ("answer", "decide") and (creating_hint or ev.get("id") in (None, "new")))
        if creating:
            need("kind", "question")
            if ev.get("kind") and ev["kind"] not in DECISION_KINDS:
                errs.append(f"{where}: kind must be one of {', '.join(sorted(DECISION_KINDS))}")
            for i, item in enumerate(ev.get("evidence") or []):
                if not isinstance(item, dict) or "ref" not in item:
                    errs.append(f"{where}: evidence[{i}] must be {{\"ref\": ..., \"quote\": ...}}")
                else:
                    check_ref(item["ref"], world, pending, f"{where} evidence[{i}]", errs, runs=True)
            opts = ev.get("options") or []
            ids = []
            for i, o in enumerate(opts):
                if not isinstance(o, dict) or not o.get("id") or not o.get("label"):
                    errs.append(f"{where}: options[{i}] needs 'id' and 'label'")
                else:
                    ids.append(o["id"])
            if len(ids) != len(set(ids)):
                errs.append(f"{where}: option ids must be unique")
            if {"other", "unsure"} & set(ids):
                errs.append(f"{where}: 'other' and 'unsure' are built in — do not use them as option ids")
            fixed = {"alignment": ("clean", "change", "accept"), "bulk": ("accept", "review", "steward")}.get(ev.get("kind"))
            if e == "open" and fixed and ids and not set(ids) <= set(fixed):
                errs.append(f"{where}: a {ev.get('kind')} question's option ids are {', '.join(fixed)} — each maps to what "
                            f"happens next ({'DATA-CHECK.md, Triage' if ev.get('kind') == 'alignment' else 'QUESTIONS.md'})")
            if ev.get("input", "choice") not in ("choice", "multi", "text"):
                errs.append(f"{where}: input must be choice, multi, or text")
            if e == "open" and ev.get("input", "choice") != "text" and ev.get("kind") not in ("knowledge", "feedback") and len(ids) < 2:
                errs.append(f"{where}: a question needs at least two options (QUESTIONS.md)")
            kind = ev.get("kind")
            if e == "open" and kind in DATA_KINDS:
                if not ev.get("topic") and not ev.get("targets"):
                    errs.append(f"{where}: a {kind} question names its 'topic' or its 'targets' (variables)")
                if kind in PROVISIONAL_KINDS and ev.get("input", "choice") != "text" and not ev.get("provisional"):
                    errs.append(f"{where}: a {kind} question says which option the schemas encode meanwhile in 'provisional' "
                                f"(the safest one when no source settles it; for a rule, no rule)")
                if kind in EVIDENCE_KINDS and not ev.get("evidence"):
                    errs.append(f"{where}: a {kind} question quotes its 'evidence' ([{{\"ref\": \"S01:…\", \"quote\": \"…\"}}])")
            if e != "open" and kind in ("knowledge", "feedback") and not (ev.get("text") or "").strip():
                errs.append(f"{where}: a {kind} decision holds the person's words in 'text'")
            if e == "open" and ev.get("kind") not in ("interview", "knowledge", "feedback") and ev.get("input", "choice") != "text":
                if not ev.get("recommended"):
                    errs.append(f"{where}: every question about the data carries 'recommended' (an option id) and 'why'")
                elif ev["recommended"] not in ids:
                    errs.append(f"{where}: recommended {ev['recommended']!r} is not one of the option ids {ids}")
                if not ev.get("why"):
                    errs.append(f"{where}: missing 'why' (one line on why you recommend it)")
            if ev.get("provisional") and ids and ev["provisional"] not in ids:
                errs.append(f"{where}: provisional {ev['provisional']!r} is not one of the option ids")
            if ev.get("topic") and topics and ev["topic"] not in topics:
                errs.append(f"{where}: topic {ev['topic']!r} is not in project.json")
            if ev.get("table") and tables and ev["table"] not in tables:
                errs.append(f"{where}: table {ev['table']!r} is not in project.json")
            if ev.get("targets") is not None and not (isinstance(ev["targets"], list) and all(isinstance(x, str) for x in ev["targets"])):
                errs.append(f"{where}: targets is a list of variable names")
            if ev.get("kind") == "bulk":
                if not str_list(ev.get("covers")):
                    errs.append(f"{where}: a bulk decision lists the decisions it covers in 'covers'")
                for c in ev.get("covers") or []:
                    if c not in world.decisions and c not in pending["decision"]:
                        errs.append(f"{where}: covers {c} does not exist")
            if ev.get("kind") == "consent" and ev.get("covers") is not None:
                if not str_list(ev.get("covers")):
                    errs.append(f"{where}: a consent question lists the rules it asks about in 'covers' (R ids)")
                for c in ev.get("covers") or []:
                    if c not in world.rules and c not in pending["rule"]:
                        errs.append(f"{where}: covers {c} is not a rule")
            if ev.get("importance", "normal") not in ("high", "normal", "low"):
                errs.append(f"{where}: importance is high, normal, or low")
            if ev.get("to", "any") not in ("author", "steward", "any"):
                errs.append(f"{where}: to is author, steward, or any")
        else:
            existing("decision", world.decisions)
        target = world.decisions.get(ev.get("id")) if not creating else None
        opt_ids = [o.get("id") for o in ((target or ev).get("options") or []) if isinstance(o, dict)]
        if e == "answer":
            person()
            if ev.get("choice") in (None, "") and not ev.get("choices") and not ev.get("text"):
                errs.append(f"{where}: an answer carries 'choice' (an option id, 'other', or 'unsure'), 'choices', or 'text'")
            if opt_ids and ev.get("choice") not in (None, "", "other", "unsure") and ev["choice"] not in opt_ids:
                errs.append(f"{where}: choice {ev['choice']!r} is not one of {opt_ids} (or 'other', 'unsure')")
            for c in ev.get("choices") or []:
                if opt_ids and c not in opt_ids:
                    errs.append(f"{where}: choices holds {c!r}, which is not one of {opt_ids}")
        elif e == "decide":
            need("choice", "why")
            if opt_ids and ev.get("choice") not in opt_ids + ["other"]:
                errs.append(f"{where}: choice {ev.get('choice')!r} is not one of the question's options {opt_ids}")
            if ev.get("by", "agent") != "agent":
                errs.append(f"{where}: 'decide' is the agent's; a person's choice is an 'answer'")
            if ev.get("review", "needed") not in ("needed", "none"):
                errs.append(f"{where}: review is 'needed' or 'none'")
        elif e == "confirm":
            person()
        elif e == "apply":
            if ev.get("files") is not None and not isinstance(ev.get("files"), list):
                errs.append(f"{where}: files is a list of paths")
        elif e == "supersede":
            need("replacement")
            r = ev.get("replacement")
            if r and r not in world.decisions and r not in pending["decision"]:
                errs.append(f"{where}: replacement {r} does not exist")
        elif e == "cancel":
            need("note")
        elif e not in ("open",):
            errs.append(f"{where}: unknown decision event (open, answer, decide, confirm, apply, supersede, cancel)")
    elif t == "rule":
        if e == "add":
            need("table", "targets", "reading", "evidence", "status")
            if not ev.get("gates") and ev.get("status") != "not-expressible":
                errs.append(f"{where}: missing 'gates' (only a not-expressible rule may have none)")
            if ev.get("table") and tables and ev["table"] not in tables:
                errs.append(f"{where}: table {ev['table']!r} is not in project.json")
            for k in ("gates", "targets"):
                if ev.get(k) is not None and not str_list(ev[k]):
                    errs.append(f"{where}: {k} is a list of variable names")
        elif e == "set":
            existing("rule", world.rules)
            need("note")
        else:
            errs.append(f"{where}: unknown rule event (add, set)")
        if ev.get("evidence") is not None and ev["evidence"] not in RULE_EVIDENCE:
            errs.append(f"{where}: evidence is one of {', '.join(sorted(RULE_EVIDENCE))}")
        if ev.get("status") is not None and ev["status"] not in RULE_STATUSES:
            errs.append(f"{where}: status is one of {', '.join(sorted(RULE_STATUSES))}")
        for i, ref in enumerate(ev.get("refs") or []):
            check_ref(ref, world, pending, f"{where} refs[{i}]", errs)
        for k in ("decision", "consent"):
            if ev.get(k):
                check_ref(ev[k], world, pending, f"{where} {k}", errs)
        cur = dict(world.rules.get(ev.get("id")) or {})
        cur.update({k: ev[k] for k in RULE_FIELDS if k in ev})
        if cur.get("evidence") == "inferred" and cur.get("status") == "encoded" and not cur.get("consent"):
            errs.append(f"{where}: an inferred rule is encoded only with 'consent' — the D id of a person's yes (SKIP-LOGIC.md)")
        if cur.get("evidence") in ("told", "inferred") and cur.get("status") not in ("suspected", None) and not cur.get("decision"):
            errs.append(f"{where}: a {cur.get('evidence')} rule cites its 'decision'")
        if cur.get("status") == "waiting" and not cur.get("waits_for"):
            errs.append(f"{where}: a waiting rule names what it waits for in 'waits_for'")
    elif t == "batch":
        if e == "post":
            need("to", "title", "items")
            if ev.get("to") not in PEOPLE:
                errs.append(f"{where}: to is 'author' or 'steward'")
            for did in ev.get("items") or []:
                if not isinstance(did, str) or (did not in world.decisions and did not in pending["decision"]):
                    errs.append(f"{where}: item {did!r} is not a decision")
                else:
                    d = world.decisions.get(did)
                    if d and d.get("status") in ("answered", "cancelled", "superseded"):
                        errs.append(f"{where}: {did} is already {d['status']}; post only open or provisional decisions")
        elif e == "withdraw":
            existing("batch", world.batches)
        else:
            errs.append(f"{where}: unknown batch event (post, withdraw)")
    elif t == "topic":
        if ev.get("id") not in topics:
            errs.append(f"{where}: topic {ev.get('id')!r} is not in project.json → topics")
        if e in ("approve", "changes"):
            person()
            if e == "changes":
                need("text")
        elif e != "present":
            errs.append(f"{where}: unknown topic event (present, approve, changes)")
    elif t == "session":
        if e == "start":
            if ev.get("mode", "build") not in ("build", "review"):
                errs.append(f"{where}: mode is build or review")
        elif e == "end":
            need("summary", "next")
        else:
            errs.append(f"{where}: unknown session event (start, end)")
    elif t == "alignment":
        if e == "add":
            need("file")
            if ev.get("dataset") and ev["dataset"] not in world.datasets and ev["dataset"] not in pending["dataset"]:
                errs.append(f"{where}: dataset {ev['dataset']!r} does not exist")
        elif e == "triage":
            existing("alignment", world.alignment)
            need("check", "verdict")
            verdict = ev.get("verdict")
            if verdict not in (None, "schema-fix", "data-issue", "expected", "question"):
                errs.append(f"{where}: verdict is schema-fix, data-issue, expected, or question")
            run_rec = world.alignment.get(ev.get("id"))
            ws_ = getattr(world, "ws", None)
            if run_rec and ws_ and run_rec.get("file") and ev.get("check"):
                doc = read_json(ws_ / run_rec["file"], None)
                keys = {check_key(c) for c in (doc or {}).get("schemaChecks", []) if c.get("severity") in ("error", "warning")}
                if keys and ev["check"] not in keys:
                    errs.append(f"{where}: check {ev['check']!r} is not one of {ev.get('id')}'s failing checks — "
                                f"copy each `key` exactly as `show {ev.get('id')}` prints it")
            if ev.get("decision"):
                check_ref(ev["decision"], world, pending, f"{where} decision", errs)
            if verdict in ("data-issue", "expected"):
                dec = world.decisions.get(ev.get("decision") or "")
                if not ev.get("decision"):
                    errs.append(f"{where}: a {verdict} verdict cites, in 'decision', the question a person answered "
                                f"(DATA-CHECK.md, Triage)")
                elif dec and dec.get("status") and dec["status"] not in ("answered", "confirmed"):
                    errs.append(f"{where}: a {verdict} verdict needs a person's answer; {ev['decision']} is {dec.get('status')}")
        else:
            errs.append(f"{where}: unknown alignment event (add, triage)")
    elif t == "dataset":
        if e == "allow":
            person()
            need("label", "basis", *(() if ev.get("basis") == "browser" else ("path", "text")))
            if ev.get("basis") and ev["basis"] not in DATASET_BASES:
                errs.append(f"{where}: basis is 'public' (the data is public), 'local-model' (you run on a model the "
                            f"person controls, which their data agreement allows to process it), or 'browser' (the "
                            f"website keeps it checked in QuaC, in their browser)")
            if len(tables) > 1 and ev.get("table") not in tables:
                errs.append(f"{where}: the package has several tables — 'table' names this dataset's: {', '.join(sorted(tables))}")
            elif ev.get("table") and ev["table"] not in tables:
                errs.append(f"{where}: table {ev['table']!r} is not in project.json → tables")
            if ev.get("basis") == "local-model" and not ev.get("model"):
                errs.append(f"{where}: a 'local-model' permission covers one model — open the session with --model "
                            f"(SKILL.md, Open), so the permission records which")
            ws_ = getattr(world, "ws", None)
            if ws_ and isinstance(ev.get("path"), str) and ev["path"].strip():
                if is_inside(resolve_data_path(ws_, ev["path"]), ws_):
                    errs.append(f"{where}: {ev['path']} is inside the workspace, where data never goes — ask the person "
                                f"to move it out (DATA-CHECK.md)")
        elif e == "withdraw":
            existing("dataset", world.datasets)
            person()
        else:
            errs.append(f"{where}: unknown dataset event (allow, withdraw)")
    elif t == "milestone":
        if e != "reach" or ev.get("id") not in MILESTONES:
            errs.append(f"{where}: write {{\"type\": \"milestone\", \"event\": \"reach\", \"id\": one of {sorted(MILESTONES)}}}")
    else:
        errs.append(f"{where}: unknown type {t!r} (source, decision, rule, batch, topic, session, alignment, dataset, milestone)")
    return errs


def expand_inline(events: list) -> list:
    """A batch post may carry new decisions inline; they become decision.open events first."""
    out = []
    for ev in events:
        if isinstance(ev, dict) and ev.get("type") == "batch" and ev.get("event") == "post":
            items = []
            for it in ev.get("items") or []:
                if isinstance(it, dict):
                    opened = {"type": "decision", "event": "open", **it}
                    if ev.get("to") in PEOPLE and "to" not in it:
                        opened["to"] = ev["to"]             # inline questions take the batch's addressee
                    opened.pop("id", None)          # "ref" survives, so later events can say "@label"
                    marker = f"__inline{len(out)}"
                    opened["_marker"] = marker
                    out.append(opened)
                    items.append(marker)
                else:
                    items.append(it)
            ev = {**ev, "items": items}
        out.append(ev)
    return out


LOCAL_FIELDS = ("id", "decision", "consent", "replacement")
LOCAL_LISTS = ("refs", "covers", "items")


def resolve_locals(ev: dict, labels: dict[str, str], errors: list[str], n: int) -> dict:
    """Swap '@label' (or '@label:<locator>') for the id an earlier event in this payload was given."""
    def sub(v):
        if isinstance(v, str) and v.startswith("@"):
            name, _, loc = v[1:].partition(":")
            if name not in labels:
                errors.append(f"event {n}: {v!r} names no earlier event of this payload (give that event \"ref\": \"{name}\")")
                return v
            return labels[name] + (":" + loc if loc else "")
        return v
    for k in LOCAL_FIELDS:
        if k in ev:
            ev[k] = sub(ev[k])
    for k in LOCAL_LISTS:
        if isinstance(ev.get(k), list):
            ev[k] = [sub(x) for x in ev[k]]
    if isinstance(ev.get("evidence"), list):
        ev["evidence"] = [dict(x, ref=sub(x["ref"])) if isinstance(x, dict) and "ref" in x else x for x in ev["evidence"]]
    if isinstance(ev.get("note"), str) and "@" in ev["note"]:
        # "asked as @q" → "asked as D032": only labels this payload defined; anything else (an email) stays as written
        ev["note"] = re.sub(r"@([A-Za-z0-9_-]+)", lambda m: labels.get(m.group(1), m.group(0)), ev["note"])
    return ev


def record_events(ws: Path, raw, by_default: str = "agent") -> dict:
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise Fail("record expects a JSON object or a non-empty array of them.", "See LEDGER-FORMAT.md for the event shapes.")
    world = load_world(ws)
    events = expand_inline(raw)
    pending = {k: set() for k in ID_PREFIX}
    used = {k: set() for k in ID_PREFIX}
    used["source"] |= set(world.sources)
    used["decision"] |= set(world.decisions)
    used["rule"] |= set(world.rules)
    used["batch"] |= set(world.batches)
    used["alignment"] |= set(world.alignment)
    used["dataset"] |= set(world.datasets)
    markers: dict[str, str] = {}
    labels: dict[str, str] = {}
    errors: list[str] = []
    stamped = []
    ts = now()
    session_ids = [s["id"] for s in world.sessions]
    for n, ev in enumerate(events, 1):
        if not isinstance(ev, dict):
            errors.append(f"event {n}: not a JSON object")
            continue
        ev = dict(ev)
        label = ev.pop("ref", None)
        ev = resolve_locals(ev, labels, errors, n)
        ev.setdefault("at", ts)
        ev.setdefault("by", by_default)
        t, e = ev.get("type"), ev.get("event")
        creating = (t in ("source", "rule", "alignment") and e == "add") or (t == "batch" and e == "post") or \
                   (t == "dataset" and e == "allow") or \
                   (t == "decision" and (e == "open" or (e in ("answer", "decide") and ev.get("id") in (None, "new"))))
        if t == "dataset" and e == "allow" and ev.get("basis") == "local-model" and not ev.get("model"):
            ev["model"] = (world.open_session() or {}).get("model")    # the model this permission covers
        if t == "milestone" and e == "reach" and ev.get("id") == "finished" and not ev.get("setId"):
            ev["setId"] = quac_set_id(schemas_dir(ws))          # a later change to these files means finishing again
        if t == "milestone" and e == "reach" and ev.get("id") == "migrated" and not ev.get("topicHashes"):
            pkg = Pkg(ws, world.project)                # the house-style fixes are done: approvals carried over cover this
            ev["topicHashes"] = {tp["id"]: doc_hash(pkg.docs.get(tp.get("file"))) for tp in world.project.get("topics", [])
                                 if tp.get("id") and pkg.docs.get(tp.get("file")) is not None}
        if t == "decision" and e == "apply" and "approvedHashes" not in ev:
            covered = approval_covers(ws, world, ev)
            if covered:
                ev["approvedHashes"] = covered
        if t == "topic" and e == "approve" and not ev.get("hash") and ev.get("via") != "migration":
            rel = next((tp.get("file") for tp in world.project.get("topics", []) if tp.get("id") == ev.get("id")), None)
            ev["hash"] = doc_hash(Pkg(ws, world.project).docs.get(rel))   # what they approved: a later change reopens it
        if creating:
            if ev.get("id") not in (None, "new"):
                if ev["id"] in used[t]:
                    errors.append(f"event {n} ({t}.{e}): id {ev['id']} already exists — omit 'id' to get a new one")
                elif not ID_RE[t].match(str(ev["id"])):
                    errors.append(f"event {n} ({t}.{e}): {ev['id']!r} is not a {t} id")
            else:
                ev["id"] = next_id(t, used[t])
            used[t].add(ev["id"])
            pending[t].add(ev["id"])
            if "_marker" in ev:
                markers[ev.pop("_marker")] = ev["id"]
            if label:
                if label in labels:
                    errors.append(f"event {n}: ref {label!r} is used twice in this payload")
                labels[str(label)] = ev["id"]
        if t == "batch" and e == "post":
            ev["items"] = [markers.get(i, i) for i in ev.get("items") or []]
        if t == "session" and e == "start":
            day = ts[:10]
            k = sum(1 for s in session_ids if str(s).startswith(day)) + 1
            ev["id"] = f"{day}#{k}"
            session_ids.append(ev["id"])
        if t == "session" and e == "end" and not ev.get("id"):
            cur = world.open_session()
            if not cur:
                errors.append(f"event {n} (session.end): no open session to end")
            else:
                ev["id"] = cur["id"]
        errors += validate_event(ev, world, pending, n, creating)
        stamped.append(ev)
        if not errors:
            world.apply(ev)          # later events may refer to earlier ones
    if errors:
        raise Fail(f"Nothing recorded: {len(errors)} problem(s).", "Fix the events and send them again (LEDGER-FORMAT.md).",
                   problems=errors[:LIST_CAP])
    append_ledger(ws, stamped)
    return {"recorded": [{"type": e["type"], "event": e["event"], "id": e.get("id")} for e in stamped]}


# ===================================================================== the package's schemas (plain JSON walk)

def pkg_dir(ws: Path) -> Path:
    return ws / "package"


def schemas_dir(ws: Path) -> Path:
    return ws / "package" / "schemas"


def resolve_data_path(ws: Path, raw: str) -> Path:
    """A dataset's path as the person gave it: absolute, or relative to the folder they opened their agent in."""
    p = Path(str(raw).strip()).expanduser()
    return (p if p.is_absolute() else ws.parent / p).resolve()


def is_inside(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


class Pkg:
    """What the schema files say, read without a validator: enough for coverage,
    provenance bookkeeping and rule reconciliation even when validate.py cannot run."""

    def __init__(self, ws: Path, project: dict):
        self.root = schemas_dir(ws)
        self.docs: dict[str, dict] = {}         # relative path -> parsed JSON
        self.broken: dict[str, str] = {}
        self.properties: dict[str, dict] = {}   # "<table>.<name>" -> {table, topic, file, schema}
        self.by_name: dict[str, list[str]] = {}
        self.rules: list[dict] = []             # rule entries found in mothers
        self.mothers: dict[str, str] = {}
        if self.root.is_dir():
            for p in sorted(self.root.rglob("*")):
                if not p.is_file() or p.suffix.lower() != ".json":
                    continue
                rel = p.relative_to(self.root).as_posix()
                try:
                    doc = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    self.broken[rel] = str(exc)
                    continue
                self.docs[rel] = doc
        topic_of = {tp.get("file"): tp for tp in project.get("topics", [])}
        for tb in project.get("tables", []):
            mother = tb.get("mother")
            if mother in self.docs:
                self.mothers[tb.get("name")] = mother
        for rel, doc in self.docs.items():
            tp = topic_of.get(rel)
            if tp is None or not isinstance(doc, dict):
                continue
            for name, sch in (doc.get("properties") or {}).items():
                key = f"{tp.get('table')}.{name}"
                self.properties[key] = {"table": tp.get("table"), "topic": tp.get("id"), "file": rel,
                                        "name": name, "schema": sch if isinstance(sch, dict) else {}}
                self.by_name.setdefault(name, []).append(key)
        for table, rel in self.mothers.items():
            entries = ((self.docs[rel].get("items") or {}).get("allOf") or []) if isinstance(self.docs[rel], dict) else []
            for i, ent in enumerate(entries if isinstance(entries, list) else []):
                if not isinstance(ent, dict) or "if" not in ent:
                    continue
                m = RULE_COMMENT_RE.match(str(ent.get("$comment") or ""))
                self.rules.append({"table": table, "index": i, "file": rel, "pointer": f"/items/allOf/{i}",
                                   "id": m.group(2) if m else None, "prefix": m.group(1) if m else None,
                                   "comment": ent.get("$comment"), "provenance": ent.get("x-provenance"),
                                   "names": sorted(names_in(ent.get("if")) | names_in(ent.get("then")))})

    def provenance_refs(self) -> list[tuple[str, str, str]]:
        """(where, facet, ref) for every x-provenance reference in the package."""
        out = []

        def walk(node, where):
            if isinstance(node, dict):
                prov = node.get("x-provenance")
                if isinstance(prov, dict):
                    for facet, refs in prov.items():
                        for r in (refs if isinstance(refs, list) else [refs]):
                            out.append((where, facet, r))
                for k, v in node.items():
                    if k not in ("const", "enum", "x-provenance", "examples", "default"):
                        walk(v, where)
            elif isinstance(node, list):
                for v in node:
                    walk(v, where)
        for rel, doc in self.docs.items():
            walk(doc, rel)
        return out

    def property_provenance(self, key: str) -> dict:
        p = self.properties.get(key)
        return (p or {}).get("schema", {}).get("x-provenance") or {}


def names_in(node) -> set[str]:
    out: set[str] = set()
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            out |= set(props)
        req = node.get("required")
        if isinstance(req, list):
            out |= {r for r in req if isinstance(r, str)}
        for k in ("anyOf", "allOf", "oneOf"):
            for sub in node.get(k) or []:
                out |= names_in(sub)
    return out


def read_inventory(ws: Path) -> tuple[list[dict], list[str]]:
    p = ws / "state" / "variables.csv"
    if not p.exists():
        return [], []
    problems = []
    try:
        text = p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return [], ["state/variables.csv is not UTF-8 — re-save it as UTF-8."]
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip() for h in (reader.fieldnames or [])]
    if header != INVENTORY_COLUMNS:
        problems.append(f"state/variables.csv header must be exactly: {','.join(INVENTORY_COLUMNS)}")
        return [], problems
    seen = set()
    for n, row in enumerate(reader, 2):
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        if not any(row.values()):
            continue
        row["_line"] = n
        if row.get("status") not in INVENTORY_STATUSES:
            problems.append(f"variables.csv line {n}: status {row.get('status')!r} is not one of {sorted(INVENTORY_STATUSES)}")
        key = (row.get("table"), row.get("variable"))
        if key in seen:
            problems.append(f"variables.csv line {n}: {row.get('variable')} appears twice")
        seen.add(key)
        rows.append(row)
    return rows, problems


# ===================================================================== checks.json (the validator's full report)

def checks_report(ws: Path) -> dict | None:
    try:
        return read_json(ws / "state" / "checks.json")
    except Fail:
        return None


def run_validator(ws: Path, timeout: int = 900) -> dict | None:
    """Run validate.py summary on the package; returns the full report or None (with why)."""
    script = SKILL_DIR / "scripts" / "validate.py"
    out_file = ws / "state" / "checks.json"
    if not script.exists():
        return {"ok": False, "ran": False, "headline": "validator missing from the skill", "error": str(script)}
    pkg = pkg_dir(ws)
    attempts = []
    if shutil.which("uv"):
        attempts.append(["uv", "run", "--quiet", str(script), "summary", str(pkg), "--out", str(out_file)])
    attempts.append([sys.executable, str(script), "summary", str(pkg), "--out", str(out_file)])
    last_err = ""
    for cmd in attempts:
        try:
            if out_file.exists():
                out_file.unlink()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            last_err = str(exc)
            continue
        try:
            compact = json.loads(proc.stdout)
        except json.JSONDecodeError:
            last_err = (proc.stderr or proc.stdout)[-400:]
            continue
        if compact.get("ok") is False and "error" in compact and "hint" in compact and not out_file.exists():
            last_err = compact["error"]
            if "jsonschema" in (compact.get("hint") or "") or "referencing" in (compact.get("hint") or ""):
                continue                        # dependency missing under this interpreter; try the next
            return {"ok": False, "ran": True, "headline": compact["error"], "hint": compact.get("hint"), "at": now()}
        full = read_json(out_file, None) or compact
        full["ran"] = True
        full["at"] = now()
        full["setId"] = quac_set_id(schemas_dir(ws))     # which schema files these results are for (QuaC's fingerprint)
        write_json(out_file, full)
        return full
    return {"ok": False, "ran": False, "at": now(), "headline": "The validator could not run.",
            "error": last_err[-400:],
            "hint": "Install uv (https://docs.astral.sh/uv/) or: python3 -m pip install --user \"jsonschema>=4.18\" referencing"}


# ===================================================================== derived status

def topic_statuses(world: World, pkg: Pkg, checks: dict | None) -> list[dict]:
    out = []
    ctopics = ((checks or {}).get("topics") or {}) if checks and checks.get("ran") else {}
    fixtures = ((checks or {}).get("fixtures") or {}).get("tables") or {}
    for tp in world.project.get("topics", []):
        tid, table, rel = tp.get("id"), tp.get("table"), tp.get("file")
        props = [k for k, v in pkg.properties.items() if v["topic"] == tid]
        info = ctopics.get(f"{table}/{tid}") or ctopics.get(f"{table}/{Path(rel or '').stem}") or {}
        if rel not in pkg.docs or not props:
            status = "planned"
        else:
            status = "drafted"
            cov = info.get("coverage") or {}
            fx = fixtures.get(table) or {}
            fixtures_ok = (fx.get("valid") or {}).get("status") == "pass" and not (fx.get("invalid") or {}).get("unledgered") \
                and all(v.get("status") == "caught" for v in ((fx.get("invalid") or {}).get("verdicts") or []))
            if info and not info.get("errors") and fixtures_ok and cov.get("total") and cov.get("covered") == cov.get("total"):
                status = "tested"
        rec = world.topics.get(tid) or {}
        rev, cur = rec.get("review"), doc_hash(pkg.docs.get(rel))
        last = (rec.get("approvals") or [{}])[-1] if rev == "confirmed" else {}
        approved = last.get("hash") or (world.migrated_hashes.get(tid) if last.get("via") == "migration" else None)
        changed = bool(approved and approved != cur)
        if changed:
            rev = None                  # the file is no longer what the person approved: present it again (BUILD.md)
        if rev and status != "planned":
            status = rev
        decisions = [d for d in world.decisions.values() if d.get("topic") == tid]
        out.append({
            "id": tid, "title": tp.get("title"), "table": table, "file": rel, "status": status, "hash": cur,
            **({"changedSinceApproval": True} if changed else {}),
            "presentedAt": rec.get("presentedAt"), "presentNote": rec.get("presentNote") if rev == "in-review" else None,
            "variables": len(props),
            "open": sum(1 for d in decisions if d["status"] in ("open", "asked")),
            "guesses": sum(1 for d in decisions if d.get("needsReview")),
            "errors": info.get("errors", 0), "warnings": info.get("warnings", 0),
            "coverage": info.get("coverage"),
            "rules": sum(1 for r in world.rules.values() if set((r.get("gates") or []) + (r.get("targets") or []))
                         & {pkg.properties[k]["name"] for k in props}),
        })
    return out


def inventory_summary(rows: list[dict], pkg: Pkg) -> dict:
    total = len(rows)
    by = {s: sum(1 for r in rows if r.get("status") == s) for s in INVENTORY_STATUSES}
    in_schema = sum(1 for r in rows if r.get("status") in ("include", "added")
                    and f"{r.get('table')}.{r.get('variable')}" in pkg.properties)
    return {"total": total, "inSchemas": in_schema, **by}


def rule_view(world: World, pkg: Pkg) -> dict:
    encoded_ids = {r["id"] for r in pkg.rules if r.get("id")}
    by_status: dict[str, int] = {}
    for r in world.rules.values():
        by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
    ready = []
    for r in world.rules.values():
        if r.get("status") == "waiting":
            names = set((r.get("gates") or []) + (r.get("targets") or []))
            if names and all(f"{r.get('table')}.{n}" in pkg.properties for n in names):
                ready.append(r["id"])
    return {"byStatus": by_status, "encodedInSchemas": len(encoded_ids), "ready": ready}


def suspected_unasked(world: World) -> list[str]:
    asked = set()
    for d in world.decisions.values():
        if d.get("kind") == "consent" and d["status"] not in ("open", "cancelled"):
            asked |= set(d.get("covers") or [])            # a consent question names its rules in `covers`
            asked |= set(d.get("targets") or [])
            for ev in d.get("evidence") or []:
                asked.add(str(ev.get("ref", "")).split(":")[0])
            asked |= set(re.findall(r"R\d{3,}", " ".join(str(o.get("label", "")) for o in d.get("options") or []) + " " + str(d.get("question") or "") + " " + str(d.get("context") or "")))
    return [r["id"] for r in world.rules.values() if r.get("status") == "suspected" and r["id"] not in asked]


def finished_now(ws: Path, world: World) -> bool:
    """Finished, and the schema files are still the ones it finished with (FINISH.md, After the end)."""
    return "finished" in world.milestones and (not world.finished_set or world.finished_set == quac_set_id(schemas_dir(ws)))


def phase_steps(world: World, topics: list[dict], inv: dict, rules: dict, finished: bool | None = None) -> list[dict]:
    proj = world.project
    docs = [s for s in world.sources.values() if s.get("kind") == "document" and s.get("status") == "active"]
    steps = [
        ("setup", "Set up", True),
        ("sources", "Read the sources", bool(docs) and all(s.get("digest") for s in docs)),
        ("interview", "Interview", any(p.get("profile") for p in proj.get("people", []))),
        ("plan", "Plan the topics", bool(proj.get("tables")) and bool(proj.get("topics"))),
        ("build", "Build topic by topic", bool(topics) and all(t["status"] == "confirmed" for t in topics)),
        ("skiplogic", "Skip-logic audit", bool(topics) and all(t["status"] == "confirmed" for t in topics)
         and not rules["ready"] and not suspected_unasked(world)
         and not any(r.get("status") in ("suspected", "waiting") for r in world.rules.values())),
        ("datacheck", "Check real data", bool(world.alignment) and all(
            a.get("current") for a in list(world.alignment.values())[-1:])),
        ("review", "Steward review", "review-complete" in world.milestones),
        ("done", "Finish", "finished" in world.milestones if finished is None else finished),
    ]
    out, current_set = [], False
    for sid, label, done in steps:
        optional = sid in ("datacheck", "review")
        state = "done" if done else ("optional" if optional else ("current" if not current_set else "todo"))
        if state == "current":
            current_set = True
        out.append({"id": sid, "label": label, "state": state})
    return out


def next_actions(ws: Path, world: World, pkg: Pkg, topics: list[dict], rules: dict, inbox_n: int) -> list[dict]:
    acts: list[dict] = []

    def add(action, why, read, **kw):
        acts.append({"action": action, "why": why, "read": read, **kw})

    proj = world.project
    drift = asset_drift(ws)
    if drift:
        add("refresh-assets", f"this skill was updated: {len(drift)} file(s) the workspace copied from it differ — "
            "run refresh-assets, then build", "LAYOUT.md")
    if inbox_n:
        add("process-inbox", f"{inbox_n} feedback submission(s) from the website are waiting", "INBOX.md")
    unsure = [d["id"] for d in world.decisions.values() if d["status"] == "unsure"]
    if unsure:
        add("decide-on-behalf", f"{len(unsure)} answer(s) were 'not sure' — record your decision for each, flagged for the steward",
            "INBOX.md", ids=unsure[:LIST_CAP])
    unapplied = [d["id"] for d in world.decisions.values() if d.get("unapplied") and d["status"] != "unsure"]
    if unapplied:
        add("apply-decisions", f"{len(unapplied)} answered or decided question(s) are not yet reflected in the files",
            "INBOX.md", ids=unapplied[:LIST_CAP])
    migrating = (ws / "sources" / "MIGRATION.md").is_file() and "migrated" not in world.milestones
    if migrating:
        add("migrate", "the schemify 1.x conversion is unfinished: sources/MIGRATION.md → Left to do", "MIGRATE.md")
    if proj.get("mode") == "review" and "review-complete" not in world.milestones:
        add("review", "the workspace is in steward-review mode", "REVIEW-MODE.md")
        return acts
    docs = [s for s in world.sources.values() if s.get("kind") == "document" and s.get("status") == "active"]
    if not docs:
        add("add-sources", "no source document is registered yet", "START.md")
        return acts
    undigested = [s["id"] for s in docs if not s.get("digest")]
    if undigested:
        add("discover", f"source(s) not yet digested: {', '.join(undigested)}", "START.md", ids=undigested)
    if not any(p.get("profile") for p in proj.get("people", [])):
        add("interview", "the opening interview has not been recorded (project.json → people)", "INTERVIEW.md")
    if not proj.get("tables") or not proj.get("topics"):
        add("plan", "no tables/topics planned yet", "START.md")
        return acts
    for t in topics:
        if t["status"] == "changes-requested":
            add("revise-topic", f"changes requested on '{t['title']}'", "BUILD.md", topic=t["id"])
    for t in topics:
        if t["status"] in ("planned", "drafted"):
            add("build-topic", f"'{t['title']}' is {t['status']}", "BUILD.md", topic=t["id"])
            break
    due = datasets_due(ws, world, topics)        # real data before presenting: a slip it finds changes the topic
    for a in world.alignment.values():
        if a.get("dataset") and (a["id"] != superseding_run(world, a) or a["dataset"] in due):
            continue        # a file you check yourself: its later run, or the re-run now due, replaces this one
        left = untriaged(ws, a)
        if left:
            add("triage-alignment", f"{a['id']}: {len(left)} failing check(s) not yet triaged", "DATA-CHECK.md", ids=[a["id"]])
    held = inbox_n or unsure or unapplied or any(x["action"] == "triage-alignment" for x in acts) or any(
        d.get("kind") == "alignment" and d["status"] == "asked" for d in world.decisions.values())   # posted: a person is on it
    due = [] if held else due
    if due:
        add("run-data-check", "what the schemas accept changed since the last check of a dataset a person allowed you to "
            "check — re-run it before presenting or posting its questions", "DATA-CHECK.md", ids=due)
    for t in topics:
        if t["status"] == "tested":
            add("present-topic", f"'{t['title']}' changed after a person approved it — present it again, saying what changed"
                if t.get("changedSinceApproval") else f"'{t['title']}' is tested and ready for the user's review",
                "BUILD.md", topic=t["id"])
    if rules["ready"]:
        add("encode-rules", f"rules whose variables now exist: {', '.join(rules['ready'][:10])}", "SKIP-LOGIC.md", ids=rules["ready"])
    sus = suspected_unasked(world)
    if sus:
        add("ask-consent", f"{len(sus)} suspected undocumented rule(s) not yet put to a person", "SKIP-LOGIC.md", ids=sus[:LIST_CAP])
    unasked = [d["id"] for d in world.decisions.values() if d["status"] == "open"]
    if unasked:
        add("post-questions", f"{len(unasked)} open question(s) not yet posted", "QUESTIONS.md", ids=unasked[:LIST_CAP])
    waiting = [b for b in world.batches.values() if not b["withdrawn"] and any(
        world.decisions.get(i, {}).get("status") == "asked" for i in b["items"])]
    in_review = [t for t in topics if t["status"] == "in-review"]
    # Questions waiting on a steward who is someone else may stay open through the finish (FINISH.md,
    # Ending A); questions waiting on the person you work with come first.
    people = {p.get("role"): p for p in proj.get("people", [])}
    stw, auth = people.get("steward") or {}, people.get("author") or {}
    steward_elsewhere = bool(stw) and not (auth.get("profile") == "steward" or (
        stw.get("name") and stw.get("name") == auth.get("name")))
    blocking = [b for b in waiting if not (steward_elsewhere and b.get("to") == "steward")]
    if topics and all(t["status"] == "confirmed" for t in topics):
        audit_open = any(r.get("status") in ("suspected", "waiting") for r in world.rules.values()) or rules["ready"]
        if audit_open:
            add("skip-audit", "every topic is confirmed; the skip-logic audit is next", "SKIP-LOGIC.md")
        elif not finished_now(ws, world) and not migrating and not blocking and not [
                x for x in due if (world.datasets.get(x) or {}).get("basis") != "browser"]:
            add("finish", "the schemas changed since you finished — finish again" if "finished" in world.milestones
                else "every topic is confirmed and the skip-logic audit is clean", "FINISH.md")
    if (waiting or in_review) and all(a["action"] == "post-questions" for a in acts):
        add("wait", "the user has questions or topics to review on the website: close the session (Close) "
            "and tell them what waits", "SKILL.md",
            batches=[b["id"] for b in waiting], topics=[t["id"] for t in in_review])
    return acts


def superseding_run(world: World, a: dict) -> str:
    """The latest run of the dataset a run checked (the run itself for findings a person sent)."""
    return next((b["id"] for b in reversed(list(world.alignment.values())) if a.get("dataset") and
                 b.get("dataset") == a["dataset"]), a["id"])


def untriaged(ws: Path, a: dict) -> set[str]:
    doc = read_json(ws / (a.get("file") or ""), None) if a.get("file") else None
    keys = {check_key(c) for c in (doc or {}).get("schemaChecks", []) if c.get("severity") in ("error", "warning")}
    return keys - set(a.get("triage") or {}) - set(a.get("planned") or [])


def datasets_due(ws: Path, world: World, topics: list[dict]) -> list[str]:
    """Allowed datasets whose last check ran on other schemas — at a resting point: a topic is tested and none is mid-edit."""
    allowed = [x for x in world.datasets.values() if not x.get("withdrawn")]
    if not allowed or not any(t["status"] in ("tested", "in-review", "confirmed") for t in topics) or \
            any(t["status"] in ("drafted", "changes-requested") for t in topics):
        return []
    current = quac_set_id(schemas_dir(ws))
    checks = checks_report(ws) or {}
    if not checks.get("ok") or checks.get("setId") != current:
        return []                                   # only once these very schema files have passed the validator
    model = (world.open_session() or {}).get("model")
    accepts = accepted_set_hash(schemas_dir(ws))
    return [x["id"] for x in allowed if (x.get("basis") != "local-model" or x.get("model") == model) and
            not any(a.get("dataset") == x["id"] and (a.get("fingerprint") == current or (a.get("accepts") and
                    a["accepts"] == accepts)) for a in world.alignment.values())]


def approval_covers(ws: Path, world: World, ev: dict) -> dict[str, str]:
    """Topics an `apply` changes that stay confirmed: the person approved them after the question was posted to them,
    or after they answered it — their answer was part of what they approved. Any other change reopens a topic."""
    d = world.decisions.get(ev.get("id")) or {}
    ans = d.get("answer") or {}
    if ans.get("by") not in PEOPLE or ans.get("choice") in (None, "unsure"):
        return {}
    files = {str(f).split("package/schemas/", 1)[-1] for f in ev.get("files") or [] if "package/schemas/" in str(f)}
    seen = min([x for x in (d.get("askedSeq"), ans.get("seq")) if isinstance(x, int)] or [0])
    out, pkg = {}, None
    for tp in world.project.get("topics", []):
        rec = world.topics.get(tp.get("id")) or {}
        last = (rec.get("approvals") or [None])[-1]
        if rec.get("review") == "confirmed" and last and last.get("hash") and tp.get("file") in files and \
                0 < seen < (last.get("seq") or 0):              # ledger order: `at` ties within a second
            pkg = pkg or Pkg(ws, world.project)
            out[tp["id"]] = doc_hash(pkg.docs.get(tp["file"]))
    return out


def doc_hash(doc) -> str | None:
    """A schema file's content, independent of its formatting."""
    if doc is None:
        return None
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def check_key(c: dict) -> str:
    loc = c.get("location") or {}
    return f"{c.get('ruleId')}|{c.get('keyword')}|{loc.get('file')}|{loc.get('pointer')}|{c.get('path') or ''}"


def inbox_pending(ws: Path) -> list[Path]:
    d = ws / "inbox" / "pending"
    return sorted(d.glob("*.json")) if d.is_dir() else []


def server_info(ws: Path) -> dict | None:
    info = read_json(ws / "state" / "server.json", None)
    if not isinstance(info, dict):
        return None
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{int(info.get('port', 0))}/api/session", timeout=1.0) as r:
            sess = json.loads(r.read().decode("utf-8"))
        if sess.get("root") == str(ws):
            return info
    except Exception:
        return None
    return None


def status_payload(ws: Path, world: World | None = None) -> dict:
    world = world or load_world(ws)
    pkg = Pkg(ws, world.project)
    checks = checks_report(ws)
    topics = topic_statuses(world, pkg, checks)
    inv_rows, _ = read_inventory(ws)
    inv = inventory_summary(inv_rows, pkg)
    rules = rule_view(world, pkg)
    inbox_n = len(inbox_pending(ws))
    dec = list(world.decisions.values())
    last = world.last_closed()
    srv = server_info(ws)
    proj = world.project
    return {
        "ok": True,
        "workspace": str(ws), "study": proj.get("study"), "mode": proj.get("mode", "build"),
        "website": (srv or {}).get("url") or str(ws / "index.html"),
        "websiteServed": bool(srv),
        "session": (world.open_session() or {}).get("id"),
        "phase": next((s["label"] for s in phase_steps(world, topics, inv, rules, finished_now(ws, world))
                       if s["state"] == "current"), "Finished"),
        "counts": {
            "sources": {"documents": sum(1 for s in world.sources.values() if s.get("kind") == "document"),
                        "web": sum(1 for s in world.sources.values() if s.get("kind") == "web"),
                        "suggested": sum(1 for s in world.sources.values() if s.get("status") == "suggested")},
            "variables": inv,
            "decisions": {"open": sum(1 for d in dec if d["status"] == "open"),
                          "asked": sum(1 for d in dec if d["status"] == "asked"),
                          "needsReview": sum(1 for d in dec if d.get("needsReview")),
                          "unapplied": sum(1 for d in dec if d.get("unapplied"))},
            "rules": rules["byStatus"],
            "inbox": inbox_n,
            "alignmentRuns": len(world.alignment),
            "datasets": sum(1 for x in world.datasets.values() if not x.get("withdrawn")),
        },
        "topics": capped([{k: t[k] for k in ("id", "title", "status", "variables", "open", "guesses")} for t in topics]),
        "checks": {k: (checks or {}).get(k) for k in ("ok", "headline", "at")} if checks else None,
        "lastSession": ({"id": last["id"], **(last["end"] or {})} if last else None),
        "next": next_actions(ws, world, pkg, topics, rules, inbox_n),
    }


# ===================================================================== show / queue

def show_items(ws: Path, ids: list[str]) -> dict:
    world = load_world(ws)
    pkg = Pkg(ws, world.project)
    out = {}
    for raw in ids:
        if raw.startswith("topic:"):
            tid = raw.split(":", 1)[1]
            tp = next((t for t in world.project.get("topics", []) if t.get("id") == tid), None)
            if not tp:
                out[raw] = {"error": "no such topic in project.json"}
                continue
            props = sorted(v["name"] for v in pkg.properties.values() if v["topic"] == tid)
            inv_rows, _ = read_inventory(ws)
            out[raw] = {"topic": tp, "review": world.topics.get(tid),
                        "inventory": [{k: r.get(k) for k in INVENTORY_COLUMNS} for r in inv_rows if r.get("topic") == tid][:200],
                        "properties": props,
                        "decisions": [short_decision(d) for d in world.decisions.values() if d.get("topic") == tid][:LIST_CAP],
                        "rules": [r for r in world.rules.values() if set((r.get("gates") or []) + (r.get("targets") or [])) & set(props)][:LIST_CAP]}
        elif raw.startswith("variable:"):
            name = raw.split(":", 1)[1]
            keys = pkg.by_name.get(name, [])
            inv_rows, _ = read_inventory(ws)
            out[raw] = {"inventory": [{k: r.get(k) for k in INVENTORY_COLUMNS} for r in inv_rows if r.get("variable") == name],
                        "inSchemas": [{"table": pkg.properties[k]["table"], "topic": pkg.properties[k]["topic"],
                                       "file": "package/schemas/" + pkg.properties[k]["file"], "pointer": f"/properties/{name}",
                                       "x-provenance": pkg.property_provenance(k)} for k in keys],
                        "decisions": [short_decision(d) for d in world.decisions.values() if name in (d.get("targets") or [])][:LIST_CAP],
                        "rules": [r for r in world.rules.values() if name in (r.get("gates") or []) + (r.get("targets") or [])][:LIST_CAP]}
        elif raw[:1] == "S" and raw in world.sources:
            out[raw] = world.sources[raw]
        elif raw[:1] == "D" and raw in world.decisions:
            out[raw] = world.decisions[raw]
        elif raw[:1] == "R" and raw in world.rules:
            r = dict(world.rules[raw])
            r["inSchemas"] = [{k: e[k] for k in ("table", "index", "file", "pointer", "prefix", "comment")} for e in pkg.rules if e.get("id") == raw]
            out[raw] = r
        elif raw[:1] == "B" and raw in world.batches:
            b = dict(world.batches[raw])
            b["itemStatus"] = {i: world.decisions.get(i, {}).get("status") for i in b["items"]}
            out[raw] = b
        elif raw[:1] == "A" and raw in world.alignment:
            a = dict(world.alignment[raw])
            a["checks"] = alignment_checks(ws, a, pkg, world)
            doc = read_json(ws / (a.get("file") or ""), None) if a.get("file") else None
            a["table"] = findings_table(doc, world) if isinstance(doc, dict) else None
            a["askTo"] = alignment_ask_to(world, a)
            later = superseding_run(world, a)
            if later != raw:
                a["supersededBy"] = later         # a later run of the same file: this one needs no more verdicts
            out[raw] = a
        elif raw[:1] == "X" and raw in world.datasets:
            x = dict(world.datasets[raw])
            x["runs"] = [a["id"] for a in world.alignment.values() if a.get("dataset") == raw]
            out[raw] = x
        else:
            out[raw] = {"error": "not found", "hint": "ids look like S01, D014, R003, B02, A01, X01, topic:<id>, variable:<name>"}
    return {"ok": True, "items": out}


def alignment_ask_to(world: World, a: dict) -> str:
    """Who a run's questions go to: the person who sent the findings, or who allowed the dataset the agent checked —
    the steward instead of a limited author."""
    who = a.get("by") if a.get("by") in PEOPLE else (world.datasets.get(a.get("dataset") or "") or {}).get("by")
    who = who if who in PEOPLE else "author"
    people = {pp.get("role"): pp for pp in world.project.get("people", [])}
    if who == "author" and (people.get("author") or {}).get("profile") == "limited" and people.get("steward"):
        return "steward"
    return who


def findings_table(doc: dict, world: World) -> str | None:
    root = (((doc.get("inputs") or {}).get("schema") or {}).get("root") or "")
    return next((t.get("name") for t in world.project.get("tables", []) if t.get("mother") and
                 (root == t["mother"] or root.endswith("/" + t["mother"]))), None)


def findings_rule_map(doc: dict, pkg: Pkg, world: World) -> dict:
    """QuaC names a failing conditional by its position in the mother's allOf (schema:cond:<i>:…);
    map each such ruleId to the rule id that position holds now, to keep with the findings."""
    table = findings_table(doc, world)
    by_index = {(r["table"], r["index"]): r.get("id") for r in pkg.rules}
    out = {}
    for c in doc.get("schemaChecks") or []:
        m = re.match(r"^schema:cond:(\d+):", str(c.get("ruleId") or ""))
        if m and table and by_index.get((table, int(m.group(1)))):
            out[c["ruleId"]] = by_index[(table, int(m.group(1)))]
    return out


def alignment_checks(ws: Path, a: dict, pkg: Pkg, world: World) -> list[dict]:
    """The failing checks of one QuaC findings file, keyed for `triage`, with topic and rule id."""
    doc = read_json(ws / (a.get("file") or ""), None) if a.get("file") else None
    if not isinstance(doc, dict):
        return []
    table = findings_table(doc, world)
    stored = a.get("ruleMap") or findings_rule_map(doc, pkg, world)    # stored at import: positions may move later
    before = earlier_verdicts(ws, world, a["id"])
    out = []
    for c in doc.get("schemaChecks") or []:
        if c.get("severity") not in ("error", "warning"):
            continue
        rule = stored.get(str(c.get("ruleId") or ""))
        prop = pkg.properties.get(f"{table}.{c.get('variable')}") if table and c.get("variable") else None
        key = check_key(c)
        out.append({"key": key, "variable": c.get("variable"), "topic": (prop or {}).get("topic"), "rule": rule,
                    "requirement": c.get("requirement"), "records": c.get("records"), "percent": c.get("percentOfRecords"),
                    "level": c.get("level"), "location": c.get("location"), "triage": (a.get("triage") or {}).get(key),
                    **({"earlier": before[c["variable"]][-6:]} if before.get(c.get("variable")) else {}),
                    **({"notBuiltYet": True} if key in (a.get("planned") or []) else {})})
    out.sort(key=lambda x: -(x.get("records") or 0))
    return out


def earlier_verdicts(ws: Path, world: World, until: str) -> dict[str, list[dict]]:
    """Variable → the verdicts its checks got in runs before `until`: keys change with a schema's shape, variables do not."""
    out: dict[str, list[dict]] = {}
    for b in world.alignment.values():
        if b["id"] == until:
            break
        doc = read_json(ws / (b.get("file") or ""), None) if b.get("file") and b.get("triage") else None
        var_of = {check_key(c): c.get("variable") for c in (doc or {}).get("schemaChecks") or [] if isinstance(c, dict)}
        for key, t in (b.get("triage") or {}).items():
            if var_of.get(key):
                out.setdefault(var_of[key], []).append({"run": b["id"], "label": b.get("label"), "dataset": b.get("dataset"),
                                                        "verdict": t.get("verdict"), "decision": t.get("decision"),
                                                        "note": (t.get("note") or "")[:200] or None})
    return out


def short_decision(d: dict) -> dict:
    keep = ("id", "kind", "status", "topic", "targets", "question", "recommended", "needsReview", "unapplied", "batch")
    out = {k: d.get(k) for k in keep}
    if d.get("answer"):
        out["answer"] = {k: d["answer"].get(k) for k in ("by", "choice", "text")}
    if d.get("agentDecision"):
        out["agentDecision"] = {k: d["agentDecision"].get(k) for k in ("choice", "why")}
    return out


def queue_items(ws: Path, who: str, topic: str | None, limit: int) -> dict:
    world = load_world(ws)
    items, guesses = [], {}
    for d in world.decisions.values():
        if topic and d.get("topic") != topic:
            continue
        if d["status"] in ("cancelled", "superseded", "answered", "confirmed"):
            continue
        if d.get("kind") == "bulk":
            continue
        if who == "author" and (d.get("to") == "steward" or d["status"] == "unsure"):
            continue                               # the steward's, or waiting for your decision on the author's behalf
        score, reason = 0, []
        if d["status"] == "open":
            if who == "steward" and d.get("to") == "author":
                continue
            score += 5
            reason.append("unanswered")
        elif d["status"] == "asked":
            continue                               # already in front of someone
        elif d["status"] == "provisional":
            if who == "author" and d.get("reviewer") == "steward":
                continue                           # the author already said "not sure"
            if d.get("kind") == "guess" and d.get("importance") != "high":
                guesses.setdefault(d.get("topic") or "(no topic)", []).append(d["id"])
                continue
            score += 2
            reason.append("your agent's guess")
        if d.get("reviewer") == "steward":
            score += 6
            reason.append("the author was not sure")
        score += {"conflict": 5, "consent": 4, "rule": 4, "alignment": 4, "gap": 3, "ambiguity": 3}.get(d.get("kind"), 0)
        score += {"high": 3, "low": -2}.get(d.get("importance"), 0)
        score += min(3, len(d.get("targets") or []) // 3)
        items.append({**short_decision(d), "score": score, "why": ", ".join(reason)})
    items.sort(key=lambda x: (-x["score"], x["id"]))
    bulk = [{"topic": t, "decisions": ids, "count": len(ids)} for t, ids in sorted(guesses.items())]
    sus = suspected_unasked(world)
    open_batches = []
    for b in world.batches.values():
        if b.get("withdrawn") or b.get("to") not in (who, "any", None):
            continue
        waiting = [i for i in b.get("items") or [] if world.decisions.get(i, {}).get("status") == "asked"]
        if waiting:
            open_batches.append({"id": b["id"], "title": b.get("title"), "unanswered": len(waiting), "postedAt": b.get("at")})
    deferred = [r["id"] for r in world.rules.values() if r.get("status") == "deferred"] if who == "steward" else []
    return {"ok": True, "for": who, "items": items[:limit], "total": len(items), "truncated": len(items) > limit,
            "bulkGuesses": bulk, "suspectedRulesUnasked": sus[:LIST_CAP], "deferredRules": deferred[:LIST_CAP],
            "openBatches": open_batches}


# ===================================================================== inbox

def find_submission(ws: Path, sub: str) -> Path:
    cands = [p for p in inbox_pending(ws) if p.stem == sub or p.stem.startswith(sub)]
    if len(cands) != 1:
        raise Fail(f"No single pending submission matches {sub!r}.",
                   "Run `inbox list` and pass one of its ids.", pending=[p.stem for p in inbox_pending(ws)][:LIST_CAP])
    return cands[0]


def inbox_list(ws: Path) -> dict:
    subs = []
    for p in inbox_pending(ws):
        doc = read_json(p, {}) or {}
        kinds: dict[str, int] = {}
        for it in doc.get("items") or []:
            k = (it or {}).get("kind", "?")
            kinds[k] = kinds.get(k, 0) + 1
        subs.append({"id": p.stem, "receivedAt": doc.get("receivedAt"), "from": doc.get("from"), "items": kinds})
    return {"ok": True, "pending": subs[:LIST_CAP], "total": len(subs),
            "next": "For each: `inbox take <id>`, then work through its todo list (INBOX.md)." if subs else "Nothing waiting."}


def describe_target(t: dict) -> str:
    if not isinstance(t, dict):
        return "the work in general"
    typ = t.get("type")
    if typ == "variable":
        return f"variable {t.get('name')}" + (f" (table {t['table']})" if t.get("table") else "")
    if typ == "code":
        return f"code {t.get('code')} of {t.get('name')}"
    if typ in ("rule", "decision", "source", "topic"):
        return f"{typ} {t.get('id')}"
    return "the work in general"


def alignment_stats(doc: dict, current_set: str | None) -> dict:
    ov = doc.get("overview") or {}
    sch = ((doc.get("inputs") or {}).get("schema") or {})
    failing = [c for c in doc.get("schemaChecks") or [] if c.get("severity") in ("error", "warning")]
    return {"records": ov.get("records"), "failing": ov.get("recordsWithErrors"), "checks": len(failing),
            "fingerprint": sch.get("setId"), "current": bool(current_set) and sch.get("setId") == current_set}


def planned_checks(ws: Path, doc: dict, pkg: Pkg, world: World) -> list[str]:
    """Failing checks on a column the inventory plans for a topic not built yet: they clear once it is."""
    table = findings_table(doc, world)
    if not table:
        return []
    rows, _ = read_inventory(ws)
    planned = {r.get("variable") for r in rows if r.get("table") == table and r.get("status") in ("include", "added")
               and f"{table}.{r.get('variable')}" not in pkg.properties}
    return [check_key(c) for c in doc.get("schemaChecks") or [] if c.get("severity") in ("error", "warning")
            and c.get("variable") in planned and str(c.get("ruleId") or "").endswith(":unexpected")]


def alignment_add_event(ws: Path, world: World, fd: dict, aid: str, by: str, via: str, label: str,
                        note: str | None = None, dataset: str | None = None) -> dict:
    """The `alignment add` event for a findings document, however it arrived."""
    pkg = Pkg(ws, world.project)
    ev = {"type": "alignment", "event": "add", "id": aid, "file": f"alignment/{aid}.json", "by": by, "via": via,
          "label": label, "ruleMap": findings_rule_map(fd, pkg, world), "planned": planned_checks(ws, fd, pkg, world),
          **alignment_stats(fd, quac_set_id(schemas_dir(ws)))}
    if note:
        ev["note"] = note
    if dataset:
        ev["dataset"] = dataset
    if ev.get("current"):
        ev["accepts"] = accepted_set_hash(schemas_dir(ws))   # what these files accept, for re-runs (datasets_due)
    return ev


def take_submission(ws: Path, sub: str) -> dict:
    path = find_submission(ws, sub)
    doc = read_json(path, {}) or {}
    world = load_world(ws)
    who = doc.get("from") if doc.get("from") in PEOPLE else ("steward" if world.project.get("mode") == "review" else "author")
    via = f"inbox:{path.stem}"
    events, todo, unhandled, align_files = [], [], [], []
    topic_ids = {t.get("id") for t in world.project.get("topics", [])}
    used_align = set(world.alignment)
    for n, it in enumerate(doc.get("items") or [], 1):
        if not isinstance(it, dict):
            unhandled.append({"item": n, "why": "not an object"})
            continue
        k = it.get("kind")
        if k == "answer":
            d = world.decisions.get(it.get("decision"))
            if not d:
                unhandled.append({"item": n, "why": f"decision {it.get('decision')} does not exist", "raw": it})
                continue
            ev = {"type": "decision", "event": "answer", "id": d["id"], "by": who, "via": via,
                  "choice": it.get("choice") or ("other" if it.get("text") else None)}
            for f in ("choices", "text", "note"):
                if it.get(f):
                    ev[f] = it[f]
            events.append(ev)
            if d.get("kind") == "bulk" and it.get("choice") == "accept":
                for c in d.get("covers") or []:
                    if world.decisions.get(c, {}).get("status") == "provisional":
                        events.append({"type": "decision", "event": "confirm", "id": c, "by": who, "via": via,
                                       "note": f"accepted with {d['id']}"})
        elif k == "confirm":
            d = world.decisions.get(it.get("decision"))
            if not d:
                unhandled.append({"item": n, "why": f"decision {it.get('decision')} does not exist", "raw": it})
                continue
            events.append({"type": "decision", "event": "confirm", "id": d["id"], "by": who, "via": via,
                           **({"note": it["note"]} if it.get("note") else {})})
        elif k in ("comment", "note"):
            target = it.get("target") if k == "comment" else None
            tags = it.get("tags") or []
            text = (it.get("text") or "").strip()
            if not text and not tags:
                unhandled.append({"item": n, "why": "empty comment"})
                continue
            ev = {"type": "decision", "event": "answer", "kind": "feedback", "by": who, "via": via, "choice": "other",
                  "question": f"{'Comment on ' + describe_target(target) if target else 'Note from the ' + who}",
                  "text": (("[" + ", ".join(tags) + "] ") if tags else "") + text}
            if isinstance(target, dict):
                if target.get("type") in ("variable", "code") and target.get("name"):
                    ev["targets"] = [target["name"]]
                    pk = f"{target.get('table')}.{target.get('name')}"
                    pkg = Pkg(ws, world.project)
                    keys = [pk] if pk in pkg.properties else pkg.by_name.get(target.get("name"), [])
                    if keys:
                        ev["topic"] = pkg.properties[keys[0]]["topic"]
                        ev["table"] = pkg.properties[keys[0]]["table"]
                elif target.get("type") == "topic" and target.get("id") in topic_ids:
                    ev["topic"] = target["id"]
                elif target.get("type") in ("rule", "decision", "source"):
                    ev["context"] = f"About {target.get('type')} {target.get('id')}."
            events.append(ev)
        elif k == "topic":
            if it.get("topic") not in topic_ids or it.get("verdict") not in ("approve", "changes"):
                unhandled.append({"item": n, "why": "unknown topic or verdict", "raw": it})
                continue
            ev = {"type": "topic", "event": it["verdict"], "id": it["topic"], "by": who, "via": via}
            if it["verdict"] == "approve" and isinstance(it.get("hash"), str) and re.fullmatch(r"[0-9a-f]{16}", it["hash"]):
                ev["hash"] = it["hash"]          # the version they saw, which may predate your latest edit
            if it["verdict"] == "changes":
                ev["text"] = (it.get("text") or "").strip() or "(no details given)"
            elif it.get("text"):
                ev["note"] = it["text"]
            events.append(ev)
        elif k == "source":
            if it.get("source") not in world.sources or it.get("verdict") not in ("approve", "reject"):
                unhandled.append({"item": n, "why": "unknown source or verdict", "raw": it})
                continue
            events.append({"type": "source", "event": it["verdict"], "id": it["source"], "by": who, "via": via,
                           **({"note": it["note"]} if it.get("note") else {})})
        elif k == "alignment":
            fd = it.get("findings")
            if not isinstance(fd, dict) or fd.get("containsData") is not False or "schemaChecks" not in fd:
                unhandled.append({"item": n, "why": "not a QuaC findings-without-data document"})
                continue
            aid = next_id("alignment", used_align)
            used_align.add(aid)
            align_files.append((f"alignment/{aid}.json", fd))     # written once the events are recorded
            x = world.datasets.get(str(it.get("dataset") or ""))
            linked = it["dataset"] if x and x.get("basis") == "browser" and not x.get("withdrawn") else None
            events.append(alignment_add_event(ws, world, fd, aid, who, via,
                                              it.get("label") or (fd.get("dataset") or {}).get("name") or "dataset",
                                              note=it.get("note"), dataset=linked))
        elif k == "dataset":
            if it.get("withdraw"):
                if it["withdraw"] not in world.datasets:
                    unhandled.append({"item": n, "why": f"dataset {it['withdraw']} does not exist", "raw": it})
                    continue
                events.append({"type": "dataset", "event": "withdraw", "id": it["withdraw"], "by": who, "via": via,
                               **({"note": it["text"]} if it.get("text") else {})})
            else:
                events.append({"type": "dataset", "event": "allow", "by": who, "via": via,
                               **{f: it[f] for f in ("path", "label", "table", "sheet", "basis", "text") if it.get(f)}})
        else:
            unhandled.append({"item": n, "why": f"unknown kind {k!r}", "raw": it})
    result = record_events(ws, events, by_default=who) if events else {"recorded": []}
    for rel, fd in align_files:
        write_json(ws / rel, fd)
    world = load_world(ws)
    topic_file = {t.get("id"): t.get("file") for t in world.project.get("topics", [])}
    touched = {r["id"] for r in result["recorded"] if r["type"] == "decision"}

    def where(d: dict) -> dict:
        files = []
        if d.get("topic") and topic_file.get(d["topic"]):
            files.append("package/schemas/" + topic_file[d["topic"]])
        if d.get("kind") in ("interview", "structure", "convention"):
            files.append("state/project.json")
        return {"topic": d.get("topic"), "table": d.get("table") or next(
                    (t.get("table") for t in world.project.get("topics", []) if t.get("id") == d.get("topic")), None),
                "targets": d.get("targets") or [], "files": files}
    for did in sorted(touched):
        d = world.decisions[did]
        if d["status"] == "unsure":
            todo.append({"decision": did, "kind": d.get("kind"), "question": d.get("question"), **where(d),
                         "do": "decide `later` and apply it — an unsure person licenses no rule" if d.get("kind") == "consent"
                         else "record a `decide` (the recommendation unless you know better), review needed; apply it"})
        elif d.get("unapplied"):
            ans = d.get("answer") or {}
            todo.append({"decision": did, "kind": d.get("kind"), "question": d.get("question"),
                         "answer": decision_answer_text(d) or None, "note": ans.get("note"), **where(d),
                         "do": "apply it to the files, then record `apply`" if d.get("kind") != "feedback"
                         else "act on it: change the files (record `apply`), or open a follow-up question"})
    for r in result["recorded"]:
        if r["type"] == "topic" and r["event"] == "changes":
            todo.append({"topic": r["id"], "do": "revise the topic per the request (BUILD.md, Revising)"})
        if r["type"] == "alignment":
            todo.append({"alignment": r["id"], "do": "triage every failing check (DATA-CHECK.md)"})
        if r["type"] == "dataset":
            todo.append({"dataset": r["id"], "do": "allowed: run `data-check` when `next` says so (DATA-CHECK.md, "
                         "'When the person allows it')" if r["event"] == "allow" else "withdrawn: never check it again"})
    done_dir = ws / "inbox" / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    doc["takenAt"] = now()
    doc["recorded"] = result["recorded"]
    if unhandled:
        doc["unhandled"] = unhandled
    write_json(done_dir / path.name, doc)
    path.unlink()
    return {"ok": True, "submission": path.stem, "from": who, "recorded": result["recorded"][:LIST_CAP],
            "todo": todo[:LIST_CAP], "todoTotal": len(todo), "unhandled": unhandled[:10],
            "next": "Work through `todo` now; `status` keeps listing anything unapplied."}


def submission_fingerprint(doc: dict) -> str:
    """Same person, same items: the same submission, however it arrived (sent, downloaded, pasted)."""
    return hashlib.sha256(json.dumps({"from": doc.get("from"), "items": doc.get("items")}, sort_keys=True,
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def inbox_import(ws: Path, file: str) -> dict:
    p = Path(file).expanduser()
    doc = read_json(p, None)
    if not isinstance(doc, dict) or not isinstance(doc.get("items"), list) or not doc["items"]:
        raise Fail(f"{file} is not a schemify feedback file.", "It is the .json the website's 'Download feedback' button saves.")
    proj = load_project(ws)
    fp = submission_fingerprint(doc)
    for folder in ("pending", "done"):
        for prev in sorted((ws / "inbox" / folder).glob("*.json")):
            old_doc = read_json(prev, None)
            if isinstance(old_doc, dict) and submission_fingerprint(old_doc) == fp:
                return {"ok": True, "duplicate": old_doc.get("id") or prev.stem,
                        "next": f"nothing to import: these answers arrived before ({folder}/{prev.name})"}
    warn = None
    if doc.get("workspace") and doc["workspace"] != proj.get("id"):
        warn = f"This feedback was written for workspace {doc['workspace']}, not {proj.get('id')} — check with the user."
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sub_id = f"{stamp}-imported-{os.urandom(3).hex()}"    # unique: two imports in one second must not overwrite
    doc["id"], doc["receivedAt"], doc["importedFrom"] = sub_id, now(), p.name
    write_json(ws / "inbox" / "pending" / f"{sub_id}.json", doc)
    return {"ok": True, "submission": sub_id, "warning": warn, "next": f"inbox take {sub_id}"}


# ===================================================================== data check run by the agent

def quac_command() -> tuple[list[str], bool]:
    """QuaC's command line: SCHEMIFY_QUAC when set (an installed `quac`, e.g. on a machine without npm access), else npx."""
    env = os.environ.get("SCHEMIFY_QUAC", "").strip()
    return (shlex.split(env), True) if env else (shlex.split(QUAC_CLI), False)


def node_major() -> int | None:
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
        return int(out.lstrip("v").split(".")[0])
    except Exception:
        return None


def run_data_check(ws: Path, xid: str, timeout: int = 1800) -> dict:
    """Run QuaC on a dataset a person allowed, and import its findings without data. QuaC's output
    streams are discarded unread: an engine message can quote a cell."""
    guard(ws)
    world = load_world(ws)
    ds = world.datasets.get(xid)
    if not ds:
        raise Fail(f"{xid} is not a dataset a person allowed you to check.",
                   "Only a person can allow one (DATA-CHECK.md, 'When the person allows it'); `status` → datasets counts them.")
    label = ds.get("label") or xid
    if ds.get("withdrawn"):
        raise Fail(f"{xid} ({label}) was withdrawn by the {ds['withdrawn'].get('by')}: you may not check it any more.",
                   "The website's Data check steps still work: the person runs QuaC and sends the findings.")
    cur = world.open_session()
    if not cur:
        raise Fail("No session is open.", "Run `open` first (SKILL.md, Open).")
    if ds.get("basis") == "browser":
        return run_browser_check(ws, world, xid, ds, timeout)
    if ds.get("basis") == "local-model" and cur.get("model") != ds.get("model"):
        raise Fail(f"{xid} ({label}) was allowed for an agent on {ds.get('model')}; this session runs on "
                   f"{cur.get('model') or 'an unnamed model'}.",
                   "Ask the person whether this model may process it too; only their yes, recorded as a new `allow`, "
                   "lets you run it (DATA-CHECK.md).")
    data = resolve_data_path(ws, ds.get("path") or "")
    if is_inside(data, ws):
        raise Fail(f"{label} is inside the workspace, where data never goes.",
                   "Ask the person to move it out; then withdraw this permission and record a new `allow` with the new path.")
    if not data.is_file():
        raise Fail(f"{label} ({xid}) is not at {ds.get('path')}.",
                   "Ask the person where it is now; then withdraw this permission and record a new `allow` with that path.")
    tables = world.project.get("tables") or []
    sdir = schemas_dir(ws)
    if not tables or not sdir.is_dir():
        raise Fail("There are no schemas to check against yet.", "Build and test a topic first (BUILD.md).")
    table = ds.get("table") or (tables[0].get("name") if len(tables) == 1 else None)
    mother = next((t.get("mother") for t in tables if t.get("name") == table), None)
    cmd, custom = quac_command()
    if not custom:
        major = node_major()
        if major is None or major < 24:
            raise Fail("QuaC needs Node 24 or newer" + (f"; this machine has Node {major}." if major else ", and `node` was not found."),
                       "Tell the person in one line; once Node 24+ is installed (or SCHEMIFY_QUAC names an installed `quac`, "
                       "LAYOUT.md), run this again. Meanwhile the website's Data check steps work.")
    args = [str(data), "--schema", str(sdir), "--no-report"]
    if len(tables) > 1 and mother:
        args += ["--index", mother]
    if ds.get("sheet"):
        args += ["--sheet", str(ds["sheet"])]
    person_cmd = " ".join(shlex.quote(x) for x in shlex.split(QUAC_CLI) + args + ["--findings", "quac-findings.json"])
    set_activity(ws, f"Checking {label} against the schemas with QuaC")
    tmp = Path(tempfile.mkdtemp(prefix="schemify-quac-"))
    try:
        out = tmp / "findings.json"
        try:
            code = subprocess.run(cmd + args + ["--findings", str(out), "--quiet"], cwd=tmp, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout).returncode
        except FileNotFoundError:
            raise Fail(f"QuaC could not be started: {cmd[0]} was not found.",
                       "Tell the person: QuaC needs Node 24+ with npx, or SCHEMIFY_QUAC naming an installed `quac` (LAYOUT.md).",
                       command=person_cmd)
        except subprocess.TimeoutExpired:
            raise Fail(f"QuaC did not finish within {timeout} seconds.",
                       "For a large file run again with a longer --timeout, or give the person `command` to run themselves.",
                       command=person_cmd)
        fd = read_json(out, None) if out.is_file() else None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if code != 0 or not isinstance(fd, dict):
        raise Fail(f"QuaC stopped: {QUAC_EXIT.get(code, f'exit code {code}')}. Nothing was imported.",
                   "QuaC's own messages can quote the data, so they are kept from you. Tell the person in one line and give "
                   "them `command` to run in their own terminal, where they can read QuaC's message; the website's Data "
                   "check steps work meanwhile. Do not retry until something has changed.", command=person_cmd)
    if fd.get("containsData") is not False or not isinstance(fd.get("schemaChecks"), list):
        raise Fail("QuaC wrote something other than findings without data; nothing was imported.",
                   "Tell the person. Never open the dataset or QuaC's output to look.")
    if isinstance(fd.get("dataset"), dict):
        fd["dataset"]["name"] = label                    # the person's name for it, never the file's
    aid = next_id("alignment", set(world.alignment))
    ev = alignment_add_event(ws, world, fd, aid, "agent", f"data-check:{xid}", label, dataset=xid)
    record_events(ws, [ev])
    write_json(ws / ev["file"], fd)
    set_activity(ws, f"Checked {label}: {ev.get('checks') or 0} failing check(s)")
    to_triage = (ev.get("checks") or 0) - len(ev.get("planned") or [])
    return {"ok": True, "run": aid, "dataset": xid, "label": label, "records": ev.get("records"),
            "recordsFailing": ev.get("failing"), "checksFailing": ev.get("checks"),
            "notBuiltYet": len(ev.get("planned") or []), "current": ev.get("current"),
            "next": (f"`show {aid}`, then triage each check (DATA-CHECK.md, Triage)" if to_triage > 0 else
                     "No mismatches outside topics not built yet: the data fits the schemas. Tell the person in one line.")}


def browser_presence(ws: Path) -> dict | None:
    """What the website last reported about its QuaC tab (`serve.py` → state/presence.json), with its age in seconds."""
    p = read_json(ws / "state" / "presence.json", None)
    if not isinstance(p, dict) or not isinstance(p.get("at"), str):
        return None
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(p["at"].replace("Z", "+00:00"))).total_seconds()
    except ValueError:
        return None
    return {**p, "age": age}


def recheck_submission(ws: Path, rid: str) -> str | None:
    """The pending submission that answers a re-check request, by the request id the page echoes."""
    for path in inbox_pending(ws):
        doc = read_json(path, None)
        if isinstance(doc, dict) and any(isinstance(it, dict) and it.get("kind") == "alignment" and it.get("request") == rid
                                         for it in doc.get("items") or []):
            return path.stem
    return None


QUAC_STATUS = {"needs-dataset": "QuaC has no dataset loaded", "schemas-unusable": "QuaC could not use the schema files",
               "failed": "the check did not finish"}


def run_browser_check(ws: Path, world: World, xid: str, ds: dict, timeout: int) -> dict:
    """Ask the person's open website to re-check a dataset in QuaC, and wait for its findings without data. The data
    stays in their browser: you send a request and receive findings, as from any submission."""
    label = ds.get("label") or xid
    if not world.project.get("tables") or not schemas_dir(ws).is_dir():
        raise Fail("There are no schemas to check against yet.", "Build and test a topic first (BUILD.md).")
    srv = server_info(ws)
    if not srv:
        raise Fail(f"{label} is checked in the person's browser through the website, which is not being served.",
                   "Start it (`serve start`), then ask the person to open the Data check tab and press Connect QuaC under "
                   "'Keep it checked, automatically'; run this again once they have.")
    page = f"{srv['url']}#data-check"
    pres = browser_presence(ws) or {}
    quac = pres.get("quac") or {}
    if pres.get("age", PRESENCE_FRESH + 1) > PRESENCE_FRESH or quac.get("dataset") != xid or not quac.get("connected"):
        raise Fail(f"No open website is connected to QuaC for {label} right now.",
                   f"Ask the person to open {page} and press Connect QuaC under 'Keep it checked, automatically' — QuaC keeps their "
                   "file, so it is one click — then run this again. Do not retry before they say it is open.")
    rid = "R" + os.urandom(4).hex()
    write_json(ws / "state" / "recheck.json", {"id": rid, "dataset": xid, "at": now(),
                                               "setId": quac_set_id(schemas_dir(ws))})
    set_activity(ws, f"Asking QuaC, in your browser, to check {label} against the current schemas")
    deadline, sub = time.monotonic() + timeout, None
    try:
        while sub is None:
            sub = recheck_submission(ws, rid)
            if sub:
                break
            pres = browser_presence(ws) or {}
            quac = pres.get("quac") or {}
            if quac.get("request") == rid and quac.get("status") in QUAC_STATUS:
                raise Fail(f"QuaC could not check {label}: {QUAC_STATUS[quac['status']]}"
                           + (f" ({str(quac['detail'])[:200]})" if quac.get("detail") else "") + ". Nothing was imported.",
                           "Tell the person in one line what QuaC needs (its tab says so too); run this again once they say "
                           "it is done.")
            if pres.get("age", PRESENCE_FRESH + 1) > PRESENCE_FRESH or not quac.get("connected"):
                raise Fail(f"The website stopped answering while QuaC was checking {label}. Nothing was imported.",
                           f"Ask the person to open {page} and connect QuaC again; run this again once they have.")
            if time.monotonic() > deadline:
                raise Fail(f"QuaC did not answer within {timeout} seconds.",
                           "A large file takes longer: run again with a longer --timeout; its tab shows how far it got.")
            time.sleep(1.0)
    finally:
        (ws / "state" / "recheck.json").unlink(missing_ok=True)
    taken = take_submission(ws, sub)
    aid = next((r["id"] for r in taken["recorded"] if r["type"] == "alignment"), None)
    a = load_world(ws).alignment.get(aid) or {}
    set_activity(ws, f"Checked {label}: {a.get('checks') or 0} failing check(s)")
    to_triage = (a.get("checks") or 0) - len(a.get("planned") or [])
    return {"ok": True, "run": aid, "dataset": xid, "label": label, "submission": sub, "records": a.get("records"),
            "recordsFailing": a.get("failing"), "checksFailing": a.get("checks"),
            "notBuiltYet": len(a.get("planned") or []), "current": a.get("current"),
            "next": (f"`show {aid}`, then triage each check (DATA-CHECK.md, Triage)" if to_triage > 0 else
                     "No mismatches outside topics not built yet: the data fits the schemas. Tell the person in one line.")}


# ===================================================================== QuaC fingerprint

SCHEMA_NAME_MAPS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
SCHEMA_ANNOTATIONS = {"$comment", "title", "description", "examples", "default", "deprecated", "readOnly", "writeOnly"}


def accepted_set_hash(root: Path) -> str | None:
    """The schema files with their annotations removed (titles, descriptions, comments, x-provenance…): two folders
    with the same hash accept and reject exactly the same data, so a data check need not run again."""
    if not root.is_dir():
        return None

    def strip(node):
        if isinstance(node, list):
            return [strip(v) for v in node]
        if not isinstance(node, dict):
            return node
        out = {}
        for k, v in node.items():
            if k in SCHEMA_ANNOTATIONS or (k.startswith("x-") and k != "x-value-kind"):
                continue
            out[k] = v if k in ("const", "enum") else {n: strip(x) for n, x in v.items()} \
                if k in SCHEMA_NAME_MAPS and isinstance(v, dict) else strip(v)
        return out
    entries = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() == ".json":
            try:
                doc = strip(json.loads(p.read_text(encoding="utf-8-sig")))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                doc = p.read_bytes().decode("utf-8", errors="replace")
            entries.append([p.relative_to(root).as_posix(), doc])
    return hashlib.sha256(json.dumps(entries, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def quac_set_id(root: Path) -> str | None:
    """QuaC's schema-set id for a folder dropped into its JSON Schema slot: every .json
    file (any case) by its path relative to the folder, sorted in UTF-16 order, hashed as
    length-prefixed path/text pairs with lengths in UTF-16 code units (verified against
    QuaC 1.2.0). Matching ids mean the findings came from these exact schema files."""
    if not root.is_dir():
        return None
    entries = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() == ".json":
            text = p.read_bytes().decode("utf-8", errors="replace")
            if text.startswith("\ufeff"):
                text = text[1:]
            entries.append((p.relative_to(root).as_posix(), text))
    if not entries:
        return None
    entries.sort(key=lambda e: e[0].encode("utf-16-be"))

    def u16(s: str) -> int:
        return len(s.encode("utf-16-le")) // 2
    payload = "".join(f"{u16(path)}:{path}{u16(text)}:{text}" for path, text in entries)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ===================================================================== build

def fill(template: str, slots: dict[str, str]) -> str:
    """Single-pass {{SLOT}} substitution: text inserted for one slot is never rescanned."""
    def sub(m):
        key = m.group(1)
        if key not in slots:
            raise Fail(f"Template slot {{{{{key}}}}} has no value.", "The skill's templates and schemify.py disagree; reinstall the skill.")
        return slots[key]
    return re.sub(r"\{\{([A-Z_]+)\}\}", sub, template)


def inline_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def logo_svg() -> str:
    return (SKILL_DIR / "assets" / "json-schema-mark.svg").read_text(encoding="utf-8").strip()


def favicon_uri() -> str:
    svg = logo_svg().replace('viewBox="0 0 66.3 56.75"', 'viewBox="-6 -10.5 78.3 77.75"')
    from urllib.parse import quote
    return "data:image/svg+xml," + quote(svg)


def option_label(d: dict, choice) -> str | None:
    for o in d.get("options") or []:
        if o.get("id") == choice:
            return o.get("label")
    return None


def decision_answer_text(d: dict) -> str:
    ans, agent = d.get("answer"), d.get("agentDecision")
    if d["status"] == "answered" and ans:
        if ans.get("choices"):
            return "; ".join(option_label(d, c) or str(c) for c in ans["choices"])
        return option_label(d, ans.get("choice")) or ans.get("text") or str(ans.get("choice"))
    if agent:
        return option_label(d, agent.get("choice")) or str(agent.get("choice"))
    return ""


def decision_by(d: dict) -> str:
    if d["status"] == "answered" and d.get("answer"):
        return d["answer"].get("by") or "?"
    if d.get("agentDecision"):
        conf = d.get("confirmations") or []
        return f"agent, confirmed by {conf[-1].get('by')}" if d["status"] == "confirmed" and conf else "agent"
    return ""


def provenance_doc(world: World, pkg: Pkg) -> dict:
    cited = {r.split(":", 1)[0] for _, _, r in pkg.provenance_refs() if isinstance(r, str)}
    for r in world.rules.values():
        cited |= {x.split(":", 1)[0] for x in (r.get("refs") or [])} | {r.get("decision"), r.get("consent")}
    sources = {}
    for s in world.sources.values():
        if s.get("status") == "rejected" and s["id"] not in cited:
            continue
        sources[s["id"]] = {"kind": s.get("kind"), "title": s.get("title"), "what": s.get("what"),
                            "status": s.get("status"), **({"url": s["url"]} if s.get("url") else {}),
                            **({"file": Path(s["path"]).name} if s.get("path") else {})}
    decisions = {}
    for d in world.decisions.values():
        if d["status"] == "cancelled" and d["id"] not in cited:
            continue
        if d.get("kind") in ("interview", "feedback") and d["id"] not in cited:
            continue
        decisions[d["id"]] = {"kind": d.get("kind"), "question": d.get("question"),
                              "answer": decision_answer_text(d), "by": decision_by(d) or None,
                              "status": d["status"], "needsReview": bool(d.get("needsReview")),
                              "date": (d.get("changedAt") or d.get("created") or "")[:10],
                              **({"topic": d["topic"]} if d.get("topic") else {}),
                              **({"targets": d["targets"]} if d.get("targets") else {}),
                              **({"replacement": d["replacement"]} if d.get("replacement") else {})}
    return {"schemifyProvenance": 1, "study": world.project.get("study"), "generatedAt": now(),
            "sources": sources, "decisions": decisions}


def md_cell(text) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def tree_lines(root: Path, base: Path, depth: int = 0, limit: int = 60) -> list[str]:
    out = []
    try:
        entries = sorted(p for p in root.iterdir() if not p.name.startswith("."))
    except OSError:
        return out
    for p in entries:
        if len(out) >= limit:
            out.append("  " * depth + "…")
            break
        out.append("  " * depth + p.name + ("/" if p.is_dir() else ""))
        if p.is_dir() and depth < 3:
            out += tree_lines(p, base, depth + 1, limit - len(out))
    return out


def render_readme(world: World, pkg: Pkg, checks: dict | None, topics: list[dict], prov: dict) -> str:
    proj = world.project
    study = proj.get("study") or "This study"
    lines = [f"# {study} — JSON Schema package", ""]
    lines += [proj.get("description") or f"JSON Schema files describing the {study} dataset.", ""]
    lines += ["| Table | Mother schema | One row is | Topics | Variables |", "|---|---|---|---|---|"]
    for tb in proj.get("tables", []):
        n_topics = sum(1 for t in proj.get("topics", []) if t.get("table") == tb.get("name"))
        n_vars = sum(1 for v in pkg.properties.values() if v["table"] == tb.get("name"))
        lines.append(f"| {md_cell(tb.get('title') or tb.get('name'))} (`{tb.get('name')}`) | `schemas/{tb.get('mother')}` | "
                     f"{md_cell(tb.get('grain'))} | {n_topics} | {n_vars} |")
    needs = [d for d in prov["decisions"].values() if d.get("needsReview")]
    confirmed = sum(1 for t in topics if t["status"] == "confirmed")
    lines += ["", f"Status: {confirmed} of {len(topics)} topics confirmed by a person. "
              + (f"{checks.get('headline')}. " if checks and checks.get("headline") else "")
              + (f"{len(needs)} agent decisions still await a person's review (marked ⚑ in PROVENANCE.md)." if needs else ""), ""]
    idbase = proj.get("idBase") or ""
    lines += [
        "## Validate data against these schemas", "",
        "```bash",
        "pip install -r tools/requirements.txt          # or prefix the commands below with: uv run",
        "python3 tools/validate.py summary .            # the package checks itself: schemas, toy data, provenance",
        "python3 tools/validate.py data . --file your_data.csv   # validate a data file (JSON array, CSV or TSV)",
        "python3 tools/validate.py rules .              # every skip pattern and conditional rule, parsed",
        "```", "",
        "For sensitive data, [QuaC](https://jeyabbalas.github.io/quac/) runs entirely in your browser: drop the data "
        "file into **Dataset** and this package's `schemas/` folder into **JSON Schema**, press **Run QC**, and under "
        "**Findings without data** download a summary that holds no data values — safe to share with whoever maintains "
        "these schemas. Press **Reset** in QuaC afterwards: it keeps loaded files in the browser until you do.", "",
        "## Browse", "",
        "Open `dictionary.html` — a searchable data dictionary that works offline. Its **Semantic search** switch "
        "downloads a small text model once (about 50 MB, from huggingface.co and cdn.jsdelivr.net) and then also finds "
        "variables by meaning; your schemas never leave the browser.", "",
        "## Files", "", "```text", *tree_lines(pkg_dir_from(pkg), pkg_dir_from(pkg)), "```", "",
        "## How the schemas are written", "",
        "- Each table's mother schema is an array of records; a record is the `allOf` of its topic files, and "
        "`unevaluatedProperties: false` rejects any column the topics do not declare.",
        "- A coded variable is a `oneOf` of `const` branches, each with a `title`; a measured variable is an `anyOf` "
        "of one typed branch (with plausibility bounds) plus its special codes.",
        "- Every column is required in every record: a missing or not-applicable value is a declared code in the cell, "
        "never an absent key. Special codes carry `\"x-value-kind\": \"sentinel\"`.",
        "- `x-provenance` on every property and rule names where each fact came from — a source (`S01:<location>`) "
        "or a decision (`D014`); see PROVENANCE.md.",
        f"- The `$id`s use the placeholder namespace `{idbase}`, which nothing fetches. Replace it before publishing "
        "these schemas anywhere public.", ""]
    sents = (proj.get("conventions") or {}).get("sentinels") or []
    if sents:
        lines += ["### Missing-value codes", "", "| Code | Meaning | Skipped by design? | Decided in |", "|---|---|---|---|"]
        for s in sents:
            lines.append(f"| `{json.dumps(s.get('code'))}` | {md_cell(s.get('meaning'))} | {'yes' if s.get('structural') else 'no'} | {md_cell(s.get('decision'))} |")
        lines.append("")
    lines += ["## Skip patterns and other conditional logic", "",
              "Every rule is one entry of its mother schema's `items.allOf`, after the topic references, in one canonical "
              "shape: `{\"$comment\", \"x-provenance\", \"if\", \"then\"}`. The `if` is one clause — or an `anyOf` of "
              "clauses — of `required` plus `properties` tests (`const`, `enum`, `not`, or a numeric range); the `then` sets "
              "`properties` effects (`const`, `not const`, `enum`, or a narrowed range) or requires at least one of them "
              "(`anyOf`). The `$comment` starts with its kind and id — `Skip pattern R001:`, `Applicability R001:` (the "
              "same rule read the other way), or `<Domain> routing R007:`. `tools/validate.py rules .` prints every rule "
              "in parsed form.", ""]
    encoded = [r for r in pkg.rules if r.get("id")]
    if encoded:
        lines += ["| Rule | Table | Reading | Evidence | Provenance |", "|---|---|---|---|---|"]
        for r in encoded:
            rec = world.rules.get(r["id"]) or {}
            prov_txt = ", ".join(f"{k}: {v}" for k, v in (r.get("provenance") or {}).items())
            flag = " ⚑" if rec.get("evidence") == "inferred" else ""
            lines.append(f"| {r['id']}{flag} | {r['table']} | {md_cell(r.get('comment'))} | {rec.get('evidence', '?')} | {md_cell(prov_txt)} |")
        lines.append("")
        inferred = [r for r in world.rules.values() if r.get("evidence") == "inferred" and r.get("status") == "encoded"]
        if inferred:
            lines += [f"⚑ {len(inferred)} rule(s) were inferred by the agent from the study design, not stated in any source, "
                      "and are kept with the user's consent pending the data steward's confirmation.", ""]
    else:
        lines += ["No conditional rules are encoded.", ""]
    noexpr = [r for r in world.rules.values() if r.get("status") == "not-expressible"]
    roots = [(tb.get("name"), (pkg.docs.get(tb.get("mother")) or {}).get("$comment")) for tb in proj.get("tables", [])]
    lines += ["## Documented but not enforced", "",
              "Rules JSON Schema cannot express (arithmetic, ordering, cross-row, cross-table). Check them downstream.", ""]
    if noexpr or any(c for _, c in roots):
        for r in noexpr:
            lines.append(f"- {r['id']} ({r.get('table')}): {r.get('reading')}" + (f" — {r['note']}" if r.get("note") else ""))
        for name, c in roots:
            if c:
                lines.append(f"- {name}: {c}")
    else:
        lines.append("- None recorded.")
    lines += ["", "## Provenance", "",
              "| Source | Title | Kind | Status |", "|---|---|---|---|"]
    for sid, s in prov["sources"].items():
        lines.append(f"| {sid} | {md_cell(s.get('title'))} | {s.get('kind')} | {s.get('status')} |")
    lines += ["", f"{len(prov['decisions'])} decisions are listed in PROVENANCE.md and machine-readably in provenance.json.", ""]
    open_items = [d for d in world.decisions.values() if d["status"] in ("open", "asked", "unsure")]
    deferred = [r for r in world.rules.values() if r.get("status") in ("deferred", "suspected")]
    lines += ["## Open items", ""]
    if not (open_items or needs or deferred):
        lines.append("- None.")
    for d in open_items[:50]:
        lines.append(f"- {d['id']}: {md_cell(d.get('question'))} (open)")
    flagged = [(i, d) for i, d in prov["decisions"].items() if d.get("needsReview")]
    for i, d in flagged[:20]:
        lines.append(f"- {i}: {md_cell(d.get('question'))} — applied for now: {md_cell(d.get('answer'))} "
                     "(an agent decision awaiting a person's review, ⚑ in PROVENANCE.md)")
    if len(flagged) > 20:
        lines.append(f"- {len(flagged) - 20} more agent decision(s) await a person's review — PROVENANCE.md marks them ⚑.")
    for r in deferred[:50]:
        lines.append(f"- {r['id']} ({r.get('status')}): {md_cell(r.get('reading'))}")
    lines += ["", "---", "", f"Generated {now()[:10]} by [schemify](https://github.com/jeyabbalas/skills) from its "
              "working record. Edit the schemas, not this file — it is regenerated."]
    return "\n".join(lines) + "\n"


def pkg_dir_from(pkg: Pkg) -> Path:
    return pkg.root.parent


def render_provenance_md(world: World, prov: dict) -> str:
    study = world.project.get("study") or "This study"
    lines = [f"# Provenance — {study}", "",
             "Every title, code, special code, bound, and rule in these schemas traces to a **source** (a document, "
             "or a web page a person approved) or a **decision** (an answer from the study's people, or a choice the "
             "agent made). Each property's and rule's `x-provenance` names which: `S01:<location>` or `D014`. "
             "⚑ marks an agent decision no person has confirmed yet.", "", "## Sources", "",
             "| Id | Title | Kind | What it holds | Status |", "|---|---|---|---|---|"]
    for sid, s in prov["sources"].items():
        where = s.get("url") or s.get("file") or ""
        title = f"[{md_cell(s.get('title'))}]({where})" if s.get("url") else md_cell(s.get("title"))
        lines.append(f"| {sid} | {title} | {s.get('kind')} | {md_cell(s.get('what'))} | {s.get('status')} |")
    lines += ["", "## Decisions", "", "| Id | Question | Answer | Decided by | Status |", "|---|---|---|---|---|"]
    for did, d in prov["decisions"].items():
        flag = " ⚑" if d.get("needsReview") else ""
        lines.append(f"| {did}{flag} | {md_cell(d.get('question'))} | {md_cell(d.get('answer'))} | {md_cell(d.get('by'))} | {d.get('status')} |")
    return "\n".join(lines) + "\n"


def toy_csv_twins(ws: Path, pkg: Pkg, world: World) -> list[str]:
    written = []
    for tb in world.project.get("tables", []):
        name = tb.get("name")
        order = []
        for tp in world.project.get("topics", []):
            if tp.get("table") == name and tp.get("file") in pkg.docs:
                order += list((pkg.docs[tp["file"]].get("properties") or {}).keys())
        for stem in ("valid", "invalid"):
            src = pkg_dir(ws) / "toy-data" / name / f"{stem}.json"
            rows = read_json(src, None) if src.exists() else None
            if not isinstance(rows, list):
                continue
            cols = list(order)
            for r in rows:
                for k in (r or {}):
                    if k not in cols:
                        cols.append(k)
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            w.writerow(cols)
            for r in rows:
                r = r or {}
                w.writerow(["" if c not in r else (json.dumps(r[c]) if isinstance(r[c], (list, dict, bool)) or r[c] is None
                                                   else str(r[c])) for c in cols])
            dst = src.with_suffix(".csv")
            write_text(dst, buf.getvalue())
            written.append(str(dst.relative_to(ws)))
    return written


TOY_EMBED_BYTES = 1_500_000          # toy files larger than this are linked from the website, not embedded
TOY_MAX_ERRORS = 2000


def run_toy_check(ws: Path, table: str, path: Path) -> dict:
    """`validate.py data` on one toy file (never on real data): findings, per-column wording."""
    script = SKILL_DIR / "scripts" / "validate.py"
    attempts = []
    base = [str(script), "data", str(pkg_dir(ws)), "--file", str(path), "--table", table, "--max-errors", str(TOY_MAX_ERRORS)]
    if shutil.which("uv"):
        attempts.append(["uv", "run", "--quiet"] + base)
    attempts.append([sys.executable] + base)
    last = "validate.py did not run"
    for cmd in attempts:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            res = json.loads(proc.stdout)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            last = str(exc)[:200]
            continue
        if "findings" in res:
            return {"errors": res.get("findings") or [], "errorCount": res.get("errors", 0), "truncated": bool(res.get("truncated")),
                    "columns": res.get("columns") or {}}
        last = res.get("error") or last
        if "jsonschema" in str(res.get("hint") or "") or "referencing" in str(res.get("hint") or ""):
            continue                            # dependency missing under this interpreter; try the next
        break
    return {"checkError": last}


def toy_data_view(ws: Path, world: World, validate: bool) -> list[dict]:
    """Each toy file for the Data check tab: its rows, every validation error, and the planted mistakes.
    Results are cached per content hash in state/toy-checks.json, so a build without validation keeps them."""
    cache_path = ws / "state" / "toy-checks.json"
    cache = read_json(cache_path, None) or {}
    fresh, out = {}, []
    set_id = quac_set_id(schemas_dir(ws)) or ""
    for tb in world.project.get("tables", []):
        name = tb.get("name")
        folder = pkg_dir(ws) / "toy-data" / str(name)
        ledger_path = folder / "invalid-ledger.json"
        ledger_raw = ledger_path.read_bytes() if ledger_path.exists() else b""
        ledger = read_json(ledger_path, None) if ledger_raw else None
        planted = [{k: v.get(k) for k in ("row", "column", "kind", "reason", "value") if k in v}
                   for v in ((ledger or {}).get("violations") or []) if isinstance(v, dict)]
        for stem in ("valid", "invalid"):
            src = folder / f"{stem}.json"
            if not src.exists():
                continue
            raw = src.read_bytes()
            rows = read_json(src, None)
            key = sha12(raw + b"|" + (ledger_raw if stem == "invalid" else b"") + b"|" + set_id.encode())
            entry = {"table": name, "file": stem, "path": f"package/toy-data/{name}/{stem}.json",
                     "csv": f"package/toy-data/{name}/{stem}.csv" if src.with_suffix(".csv").exists() else None,
                     "rowCount": len(rows) if isinstance(rows, list) else None,
                     "rows": rows if isinstance(rows, list) and len(raw) <= TOY_EMBED_BYTES else None, "hash": key}
            if stem == "invalid":
                entry["planted"] = planted
            result = cache.get(key)
            if validate and not result:
                result = run_toy_check(ws, str(name), src)
            if result and "checkError" not in result:
                fresh[key] = result
            if result:
                entry.update(result)
            else:
                entry["unchecked"] = True
            out.append(entry)
    if fresh != cache and (validate or fresh):
        write_json(cache_path, fresh)
    return out


def state_payload(ws: Path, world: World, pkg: Pkg, checks: dict | None, topics: list[dict], prov: dict) -> dict:
    proj = world.project
    inv_rows, _ = read_inventory(ws)
    inv = inventory_summary(inv_rows, pkg)
    rules = rule_view(world, pkg)
    inbox_n = len(inbox_pending(ws))
    acts = next_actions(ws, world, pkg, topics, rules, inbox_n)
    schemas = []
    base = proj.get("idBase") or "https://schemas.example.org/study/"
    for rel, doc in sorted(pkg.docs.items()):
        uri = doc.get("$id") if isinstance(doc, dict) and isinstance(doc.get("$id"), str) else base + rel
        schemas.append({"path": rel, "uri": uri, "schema": doc})
    decisions = []
    for d in world.decisions.values():
        dd = {k: v for k, v in d.items() if k != "history"}
        dd["history"] = d.get("history", [])[-8:]
        decisions.append(dd)
    done = []
    for p in sorted((ws / "inbox" / "done").glob("*.json"))[-30:]:
        doc = read_json(p, {}) or {}
        done.append({"id": p.stem, "receivedAt": doc.get("receivedAt"), "takenAt": doc.get("takenAt"),
                     "from": doc.get("from"), "items": len(doc.get("items") or []),
                     "recorded": [r.get("id") for r in doc.get("recorded") or []][:60]})
    align = []
    for a in world.alignment.values():
        doc = read_json(ws / a["file"], None) if a.get("file") else None
        later = superseding_run(world, a)
        align.append({**a, "findings": doc, **({"supersededBy": later} if later != a["id"] else {})})
    full_rules = (checks or {}).get("rules") if isinstance((checks or {}).get("rules"), list) else \
        ((checks or {}).get("rules") or {}).get("items") if isinstance((checks or {}).get("rules"), dict) else None
    return {
        "format": STATE_JS_FORMAT, "generatedAt": now(),
        "workspace": {"id": proj.get("id"), "study": proj.get("study"), "slug": proj.get("slug"),
                      "description": proj.get("description"), "mode": proj.get("mode", "build"),
                      "invoke": proj.get("invoke") or "/schemify", "harness": proj.get("harness"),
                      "path": str(ws), "folder": ws.name, "parent": str(ws.parent), "idBase": proj.get("idBase"),
                      "model": next((x.get("model") for x in reversed(world.sessions) if x.get("model")), None)},
        "phase": phase_steps(world, topics, inv, rules, finished_now(ws, world)),
        "next": acts,
        "progress": {"variables": inv, "topics": {s: sum(1 for t in topics if t["status"] == s) for s in
                                                 ("planned", "drafted", "tested", "in-review", "changes-requested", "confirmed")},
                     "sessions": len(world.sessions)},
        "tables": proj.get("tables", []), "topics": topics, "people": proj.get("people", []),
        "conventions": proj.get("conventions", {}), "preferences": proj.get("preferences", {}),
        "plan": proj.get("plan", {}),
        "schemas": schemas, "schemasBroken": pkg.broken,
        "sources": list(world.sources.values()), "decisions": decisions,
        "batches": list(world.batches.values()), "rules": list(world.rules.values()),
        "encodedRules": [{k: r.get(k) for k in ("table", "index", "id", "prefix", "comment", "provenance", "names")} for r in pkg.rules],
        "parsedRules": full_rules or [],
        "alignment": align, "quacSetId": quac_set_id(schemas_dir(ws)),
        "datasets": list(world.datasets.values()),
        "inbox": {"pending": inbox_n, "done": done},
        "log": [{"id": s["id"], "mode": s.get("mode"), "startedAt": s.get("startedAt"), **(s.get("end") or {})}
                for s in world.sessions][-40:],
        "milestones": world.milestones,
        "checks": {k: (checks or {}).get(k) for k in ("ok", "ran", "headline", "at", "counts", "provenance", "fixtures", "hint", "error")}
        if checks else None,
        "quac": {"app": os.environ.get("SCHEMIFY_QUAC_APP") or QUAC_APP, "cli": QUAC_CLI, "schemasFolder": "package/schemas"},
        "provenance": prov,
        "inputsHash": inputs_hash(ws),
    }


def write_site(ws: Path, payload: dict) -> list[str]:
    written = []
    data_js = "window.SCHEMIFY_STATE = " + inline_json(payload) + ";\n"
    write_text(ws / "site" / "data" / "state.js", data_js)
    written.append("site/data/state.js")
    act = read_json(ws / "state" / "activity.json", None) or {}
    act["stateAt"] = payload["generatedAt"]
    write_activity_js(ws, act)
    tpl = (SKILL_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    study = payload["workspace"].get("study") or "Study"
    write_text(ws / "index.html", fill(tpl, {"TITLE": html.escape(f"{study} — schemify"), "STUDY": html.escape(study),
                                             "LOGO": logo_svg(), "FAVICON": favicon_uri(),
                                             "SKILL_VERSION": html.escape(skill_version())}))
    written.append("index.html")
    write_text(ws / "START-HERE.md", start_here(ws, payload))
    written.append("START-HERE.md")
    return written


def write_activity_js(ws: Path, act: dict) -> None:
    rq = read_json(ws / "state" / "recheck.json", None)     # a re-check the open website should run in QuaC
    act = {**act, "recheck": rq} if isinstance(rq, dict) else {k: v for k, v in act.items() if k != "recheck"}
    write_text(ws / "site" / "data" / "activity.js", "window.SCHEMIFY_ACTIVITY = " + inline_json(act) + ";\n")


def skill_version() -> str:
    try:
        m = re.search(r'^\s+version:\s*"([^"]+)"', (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"), re.M)
        return m.group(1) if m else "?"
    except OSError:
        return "?"


def invoke_for(invoke: str | None, harness: str | None) -> str:
    """How the user calls the skill: Codex names skills with `$`, the others with `/`."""
    inv = invoke or "/schemify"
    if harness == "codex" and inv.startswith("/"):
        inv = "$" + inv[1:]
    return inv


def start_here(ws: Path, payload: dict) -> str:
    w = payload["workspace"]
    inv = invoke_for(w.get("invoke"), w.get("harness"))
    harness_line = {
        "codex": f"start your message with `{inv}` (Codex needs the skill named in every message you send it).",
    }.get(w.get("harness") or "", f"type `{inv}`.")
    return "\n".join([
        f"# {w.get('study') or 'Study'} — schemify workspace", "",
        "This folder holds the work of turning the study's data documentation into JSON Schema files: the schemas "
        "themselves (in `package/`), and everything the agent needs to remember between sessions.", "",
        "## See progress and answer questions", "",
        "Open **`index.html`** in this folder (double-click it). That is the project website: progress, the agent's "
        "questions, the data dictionary, skip logic, sources and decisions, and the private data check.", "",
        "When the agent is running it serves the same page at a local address (it tells you which) — use that one: "
        "it sends your answers straight to the agent and updates live. Opened from disk, the page still works; your "
        "answers are kept in the browser and you can download them as a file for the agent.", "",
        "To serve the website yourself, without the agent: `python3 tools/serve.py` from this folder (Ctrl-C to stop).", "",
        "## Continue the work", "",
        f"1. Open your coding agent in `{w.get('parent')}` — the folder that contains this one.",
        f"2. Then {harness_line}",
        "3. The agent reads its notes here, tells you where things stand, and continues. You never need to "
        "re-explain anything.", "",
        "Large dictionaries take several sessions; nothing is lost in between.", "",
        "## Share for review", "",
        "To have the study's data steward review the work, ask the agent to prepare it for review — it makes a zip "
        "of this folder and tells the steward what to do. (`package/` alone is the finished deliverable.)", "",
        "## What is where", "",
        "- `package/` — the deliverable: schemas, toy data, README, provenance, a standalone data dictionary, a validator.",
        "- `state/` — the agent's working memory. Do not edit by hand.",
        "- `sources/` — copies of the documents the work is based on, and what the agent extracted from them.",
        "- `inbox/` — feedback sent from the website.  `alignment/` — data-check summaries (they contain no data).",
        "",
    ]) + "\n"


def build(ws: Path, validate: bool = True) -> dict:
    guard(ws)
    ensure_dirs(ws)
    world = load_world(ws)
    pkg = Pkg(ws, world.project)
    prov = provenance_doc(world, pkg)
    written = []
    if pkg.docs or world.project.get("tables"):
        write_json(pkg_dir(ws) / "provenance.json", prov)       # before the validator, which reads it
        written.append("package/provenance.json")
    checks = None
    if validate and pkg.docs:
        checks = run_validator(ws)
    elif not validate:
        checks = checks_report(ws)
    topics = topic_statuses(world, pkg, checks)
    if pkg.docs or world.project.get("tables"):
        write_text(pkg_dir(ws) / "PROVENANCE.md", render_provenance_md(world, prov))
        write_text(pkg_dir(ws) / "README.md", render_readme(world, pkg, checks, topics, prov))
        written += ["package/PROVENANCE.md", "package/README.md"]
        write_text(pkg_dir(ws) / "tools" / "requirements.txt", REQUIREMENTS)
    if pkg.docs:
        written.append(write_dictionary(ws, world, pkg, prov))
        written += toy_csv_twins(ws, pkg, world)
    payload = state_payload(ws, world, pkg, checks, topics, prov)
    payload["toyData"] = toy_data_view(ws, world, validate and bool(pkg.docs) and bool(checks and checks.get("ran")))
    written += write_site(ws, payload)
    srv = server_info(ws)
    return {"ok": True, "written": written,
            "checks": {k: (checks or {}).get(k) for k in ("ok", "ran", "headline", "hint")} if checks else None,
            "website": (srv or {}).get("url") or str(ws / "index.html")}


def write_dictionary(ws: Path, world: World, pkg: Pkg, prov: dict) -> str:
    proj = world.project
    tpl = (SKILL_DIR / "templates" / "dictionary.html").read_text(encoding="utf-8")
    base = proj.get("idBase") or "https://schemas.example.org/study/"
    docs = [{"uri": d.get("$id") if isinstance(d, dict) and isinstance(d.get("$id"), str) else base + rel,
             "name": rel, "schema": d} for rel, d in sorted(pkg.docs.items())]
    mounts = []
    for tb in proj.get("tables", []):
        mother = pkg.docs.get(tb.get("mother"))
        if isinstance(mother, dict):
            mounts.append({"table": tb.get("name"), "title": tb.get("title") or tb.get("name"),
                           "rootUri": mother.get("$id") or base + tb.get("mother")})
    study = proj.get("study") or "Data dictionary"
    page = fill(tpl, {
        "TITLE": html.escape(f"{study} — data dictionary"), "STUDY": html.escape(study),
        "LOGO": logo_svg(), "FAVICON": favicon_uri(), "GENERATED": now()[:10],
        "SCHEMAS_JSON": inline_json(docs), "CONFIG_JSON": inline_json({"package": proj.get("id") or proj.get("slug"), "mounts": mounts}),
        "PROVENANCE_JSON": inline_json(prov), "SKILL_VERSION": html.escape(skill_version()),
    })
    write_text(pkg_dir(ws) / "dictionary.html", page)
    return "package/dictionary.html"


def ensure_dirs(ws: Path) -> None:
    for d in ("state", "sources", "inbox/pending", "inbox/done", "alignment", "site/data", "tools",
              "package/schemas", "package/toy-data", "package/tools", "package/assets"):
        (ws / d).mkdir(parents=True, exist_ok=True)


# ===================================================================== check

BLOCKING_CODES = {"inbox-pending", "decision-unapplied", "decision-unsure"}
CITABLE = {"active", "approved", "retired"}


def built_hash(ws: Path) -> str | None:
    """The inputs hash the last `build` wrote into the website's data."""
    state_js = ws / "site" / "data" / "state.js"
    shown = re.search(r'"inputsHash":\s*"([0-9a-f]+)"', state_js.read_text(encoding="utf-8")) if state_js.exists() else None
    return shown.group(1) if shown else None


def inputs_hash(ws: Path) -> str:
    """What the website is built from, hashed: unlike mtimes, it survives a git checkout."""
    h = hashlib.sha256()
    files = [ws / "state" / "ledger.jsonl", ws / "state" / "project.json", ws / "state" / "variables.csv"]
    for sub in ("package/schemas", "package/toy-data", "alignment"):
        root = ws / sub
        if root.exists():
            files += sorted(p for p in root.rglob("*.json") if p.is_file())
    for p in files:
        if p.exists():
            rel = p.relative_to(ws).as_posix()
            data = p.read_bytes()
            h.update(f"{len(rel)}:{rel}:{len(data)}:".encode())
            h.update(data)
    return h.hexdigest()[:16]


def asset_drift(ws: Path) -> list[dict]:
    out = []
    for src, dst in SHIPPED:
        s, d = SKILL_DIR / src, ws / dst
        if not s.exists():
            continue
        if not d.exists():
            out.append({"file": dst, "issue": "missing"})
        elif sha12(s.read_bytes()) != sha12(d.read_bytes()):
            out.append({"file": dst, "issue": "differs from the skill"})
    return out


def validator_findings(checks: dict) -> list[dict]:
    out = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "findings" and isinstance(v, list):
                    out.extend(x for x in v if isinstance(x, dict) and x.get("severity") in ("error", "warning"))
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(checks)
    seen, uniq = set(), []
    for x in out:
        key = json.dumps(x, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            uniq.append(x)
    return uniq


ROW_LOCATOR_RE = re.compile(r"^(?:(.+?)\s+)?row\s+(\d+)$", re.I)


def cited_row(ws: Path, world: World, ref: str, cache: dict) -> str | None:
    """The text of a spreadsheet or CSV row a reference cites (`S01:Variables row 7`), from the source's extract."""
    sid, _, loc = ref.partition(":")
    m = ROW_LOCATOR_RE.match(loc.strip())
    ext = ((world.sources.get(sid) or {}).get("extract") or {}).get("dir")
    if not m or not ext:
        return None
    d = ws / ext
    if sid not in cache:
        man = read_json(d / "manifest.json", {}) or {}
        sheets = {str(x.get("name") or "").casefold(): x.get("file") for x in ((man.get("stats") or {}).get("sheets") or [])
                  if isinstance(x, dict) and x.get("file")}
        cache[sid] = (sheets, {})
    sheets, rows = cache[sid]
    name = (m.group(1) or "").strip().casefold()
    fname = sheets.get(name) or (next(iter(sheets.values())) if len(sheets) == 1 and not name else None) or \
        ("table.csv" if not sheets and (d / "table.csv").is_file() else None)
    if not fname:
        return None
    if fname not in rows:
        try:
            with (d / fname).open(encoding="utf-8", newline="") as fh:
                rows[fname] = {r.get("_row"): " | ".join(v for k, v in r.items() if k != "_row" and isinstance(v, str) and v)
                               for r in csv.DictReader(fh)}
        except (OSError, UnicodeDecodeError, csv.Error):
            rows[fname] = {}
    return rows[fname].get(m.group(2))


def resolve_ref(pkg: Pkg, rel: str, ref: str):
    """(node, file) a $ref points at inside the package, or (None, None)."""
    path, _, frag = str(ref).partition("#")
    if not path:
        target = rel
    elif "://" in path:
        target = next((r for r, d in pkg.docs.items() if isinstance(d, dict) and d.get("$id") == path), None)
    else:
        target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), path))
    node = pkg.docs.get(target) if target else None
    for part in [x for x in frag.split("/") if x] if frag.startswith("/") else ([] if not frag else [None]):
        if part is None or not isinstance(node, dict):
            return None, None
        node = node.get(part.replace("~1", "/").replace("~0", "~"))
    return (node, target) if isinstance(node, (dict, bool)) else (None, None)


def accepts(pkg: Pkg, rel: str, node, v, depth: int = 0) -> bool:
    """Whether a number passes a schema node, read without a validator; unsure → True, so a lint warns only on a clear no."""
    if isinstance(node, bool):
        return node
    if depth > 12 or not isinstance(node, dict):
        return True
    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
    if "$ref" in node:
        target, trel = resolve_ref(pkg, rel, node["$ref"])
        if target is not None and not accepts(pkg, trel, target, v, depth + 1):
            return False
    if "const" in node and not (num(node["const"]) and node["const"] == v):
        return False
    if isinstance(node.get("enum"), list) and not any(num(x) and x == v for x in node["enum"]):
        return False
    types = node.get("type") if isinstance(node.get("type"), list) else [node.get("type")] if node.get("type") else None
    if types and not ("number" in types or ("integer" in types and float(v).is_integer())):
        return False
    for kw, bad in (("minimum", lambda b: v < b), ("maximum", lambda b: v > b),
                    ("exclusiveMinimum", lambda b: v <= b), ("exclusiveMaximum", lambda b: v >= b)):
        if num(node.get(kw)) and bad(node[kw]):
            return False
    for kw in ("anyOf", "oneOf"):
        if isinstance(node.get(kw), list) and node[kw] and not any(accepts(pkg, rel, x, v, depth + 1) for x in node[kw]):
            return False
    if isinstance(node.get("allOf"), list) and not all(accepts(pkg, rel, x, v, depth + 1) for x in node["allOf"]):
        return False
    neg = node.get("not")
    if isinstance(neg, dict) and neg and set(neg) <= {"enum", "const"} and accepts(pkg, rel, neg, v, depth + 1):
        return False
    return True


def sentinels_dropped(ws: Path, world: World, pkg: Pkg) -> list[tuple[str, str, int, str]]:
    """Properties whose cited dictionary row lists one of the package's numeric special codes that the property
    rejects — the slip a self-consistent package hides (toy data covers only the codes the schema has)."""
    codes: dict[float, str] = {}

    def walk(node):
        if isinstance(node, dict):
            c = node.get("const")
            if node.get("x-value-kind") == "sentinel" and isinstance(c, (int, float)) and not isinstance(c, bool):
                codes.setdefault(c, str(node.get("title") or "special code"))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    for doc in pkg.docs.values():
        walk(doc)
    if not codes:
        return []
    out, cache = [], {}
    for key, p in sorted(pkg.properties.items()):
        prov = p["schema"].get("x-provenance")
        if not isinstance(prov, dict) or "sentinels" in prov:
            continue                                # a facet says where its set of codes came from
        for ref in prov.get("default") if isinstance(prov.get("default"), list) else [prov.get("default")]:
            text = cited_row(ws, world, ref, cache) if isinstance(ref, str) and ref.startswith("S") else None
            for code, title in (codes.items() if text else []):
                lit = str(int(code)) if float(code).is_integer() else str(code)
                if re.search(r"(?<![\w.\-–—])" + re.escape(lit) + r"(?![\w.])", text) and \
                        not accepts(pkg, p["file"], p["schema"], code):
                    out.append((p["name"], ref, int(code) if float(code).is_integer() else code, title))
    return out


def check(ws: Path, validate: bool = True, strict: bool = False) -> dict:
    findings: list[dict] = []

    def f(sev, code, message, hint, **kw):
        findings.append({"severity": sev, "code": code, "message": message, "hint": hint, **kw})

    proj = load_project(ws)
    for key in ("schemify", "id", "study", "slug", "mode", "tables", "topics"):
        if key not in proj:
            f("error", "project-invalid", f"project.json has no '{key}'", "Add it (LEDGER-FORMAT.md → project.json).")
    if proj.get("mode") not in ("build", "review"):
        f("error", "project-invalid", f"mode is {proj.get('mode')!r}", "Set mode to build or review.")
    tables = proj.get("tables") or []
    tnames = [t.get("name") for t in tables if isinstance(t, dict)]
    if len(tnames) != len(set(tnames)):
        f("error", "project-invalid", "table names repeat", "Each table needs a unique name.")
    for t in tables:
        if not isinstance(t, dict) or not t.get("name") or not t.get("grain") or not t.get("mother"):
            f("error", "project-invalid", f"table entry {t!r} needs name, grain, mother", "See LEDGER-FORMAT.md → project.json.")
        elif t["mother"] != f"{t['name']}/{t['name']}.schema.json":
            f("warning", "project-layout", f"table {t['name']}: mother is {t['mother']}", f"Use {t['name']}/{t['name']}.schema.json (SCHEMA-STYLE.md).")
    tids, tfiles = [], []
    for tp in proj.get("topics") or []:
        if not isinstance(tp, dict) or not tp.get("id") or not tp.get("table") or not tp.get("file") or not tp.get("title"):
            f("error", "project-invalid", f"topic entry {tp!r} needs id, title, table, file", "See LEDGER-FORMAT.md → project.json.")
            continue
        tids.append(tp["id"])
        tfiles.append(tp["file"])
        if tp["table"] not in tnames:
            f("error", "project-invalid", f"topic {tp['id']} names table {tp['table']!r}, which is not in tables", "Fix the topic or add the table.")
        if tp["file"] != f"{tp['table']}/categories/{tp['id']}.json":
            f("warning", "project-layout", f"topic {tp['id']}: file is {tp['file']}", f"Use {tp['table']}/categories/{tp['id']}.json.")
    if len(tids) != len(set(tids)) or len(tfiles) != len(set(tfiles)):
        f("error", "project-invalid", "topic ids or files repeat", "Each topic needs a unique id and file.")
    prefs = proj.get("preferences") or {}
    if prefs.get("inferRules", "ask") not in ("ask", "yes", "no"):
        f("error", "project-invalid", "preferences.inferRules must be ask, yes, or no", "Only a person's answer changes it.")
    for s in (proj.get("conventions") or {}).get("sentinels") or []:
        if not isinstance(s, dict) or "code" not in s or not s.get("meaning"):
            f("error", "project-invalid", f"conventions.sentinels entry {s!r} needs code and meaning", "See LEDGER-FORMAT.md.")
    try:
        world = load_world(ws)
    except Fail as exc:
        f("error", "ledger-unreadable", exc.error, exc.hint)
        return {"ok": False, "blocking": 1, "findings": findings}
    pkg = Pkg(ws, proj)
    for rel, err in pkg.broken.items():
        f("error", "schema-unreadable", f"package/schemas/{rel} does not parse: {err}", "Fix the JSON.")
    rows, problems = read_inventory(ws)
    for pmsg in problems:
        f("error", "inventory-invalid", pmsg, "Fix state/variables.csv (LEDGER-FORMAT.md).")
    with_props = {v["topic"] for v in pkg.properties.values()}
    drafted = {tp["id"] for tp in proj.get("topics") or [] if isinstance(tp, dict) and tp.get("file") in pkg.docs
               and tp.get("id") in with_props}           # a scaffolded topic with no properties yet is still planned
    inv_keys = set()
    for r in rows:
        key = f"{r.get('table')}.{r.get('variable')}"
        inv_keys.add(key)
        if r.get("topic") and r["topic"] not in tids:
            f("error", "inventory-topic", f"variables.csv line {r['_line']}: topic {r['topic']!r} is not in project.json", "Fix the topic column.")
        if r.get("source") and not all(REF_RE.match(x.strip()) for x in r["source"].split(";")):
            f("warning", "inventory-source", f"variables.csv line {r['_line']}: source {r['source']!r} is not a reference", "Write S01:<locator> or D014.")
        if r.get("status") in ("include", "added") and r.get("topic") in drafted and key not in pkg.properties:
            f("error", "coverage-missing", f"{r['variable']} is in the inventory for drafted topic {r['topic']} but in no schema",
              "Add it to the topic's file, or mark it deferred/dropped with a note.", variable=r["variable"])
        if r.get("status") in ("deferred", "dropped") and key in pkg.properties:
            f("error", "coverage-excluded", f"{r['variable']} is {r['status']} in the inventory but present in a schema",
              "Remove it from the schema or change its status.", variable=r["variable"])
    if rows:
        for key, p in pkg.properties.items():
            if key not in inv_keys:
                f("error", "coverage-uninventoried", f"{p['name']} is in {p['file']} but not in variables.csv",
                  "Add its row (status include, or added with the D id of the person's request).", variable=p["name"])
    for where, facet, ref in pkg.provenance_refs():
        if not isinstance(ref, str) or not REF_RE.match(ref):
            continue                                   # validate.py reports the grammar
        rid = ref.split(":", 1)[0]
        if rid.startswith("S"):
            s = world.sources.get(rid)
            if not s:
                f("error", "provenance-unknown", f"{where}: {facet} cites {rid}, which is not registered", "Register the source, or cite the right one.")
            elif s.get("status") not in CITABLE:
                f("error", "provenance-uncitable", f"{where}: {facet} cites {rid}, which is {s.get('status')}",
                  "A web source is citable only after a person approves it; ask, or cite something else.")
        else:
            d = world.decisions.get(rid)
            if not d:
                f("error", "provenance-unknown", f"{where}: {facet} cites {rid}, which does not exist", "Record the decision first.")
            elif d["status"] == "cancelled":
                f("error", "provenance-cancelled", f"{where}: {facet} cites cancelled {rid}", "Cite the decision that replaced it.")
            elif d["status"] == "superseded":
                f("warning", "provenance-superseded", f"{where}: {facet} cites {rid}, superseded by {d.get('replacement')}", f"Cite {d.get('replacement')}.")
            elif d["status"] in ("open", "asked"):
                f("warning", "provenance-unsettled", f"{where}: {facet} cites {rid}, still {d['status']}",
                  "Fine while it is provisional; the encoding must follow the answer once it comes.")
    encoded = {}
    for r in pkg.rules:
        if not r.get("id"):
            f("error", "rule-unidentified", f"{r['file']} {r['pointer']}: a conditional with no rule id in its $comment",
              "Every rule's $comment starts '<Kind> R###:' (SKIP-LOGIC.md).")
            continue
        encoded.setdefault(r["id"], []).append(r)
        if r["id"] not in world.rules:
            f("error", "rule-unregistered", f"{r['id']} is in {r['file']} but has no rule record", "Record it: {\"type\": \"rule\", \"event\": \"add\", ...}.")
    for rid, rec in world.rules.items():
        st = rec.get("status")
        if st == "encoded" and rid not in encoded:
            f("error", "rule-not-encoded", f"{rid} is recorded as encoded but no conditional carries it", "Encode it, or `set` its real status.")
        if st != "encoded" and rid in encoded:
            f("error", "rule-status", f"{rid} is in the schemas but recorded as {st}", "Record `set` with status encoded.")
        if rec.get("evidence") == "inferred" and st == "encoded":
            c = world.decisions.get(rec.get("consent") or "")
            choice = ((c or {}).get("answer") or {}).get("choice")
            ok = bool(c) and c["status"] == "answered" and c.get("kind") in ("consent", "rule", "convention") and (
                c.get("kind") != "consent" or choice in CONSENT_YES or choice == "other")
            if not ok and not (c and c.get("kind") == "convention" and prefs.get("inferRules") == "yes"):
                f("error", "rule-consent", f"{rid} is inferred and encoded without a person's yes", "Ask the consent question first (SKIP-LOGIC.md).")
    for name, ref, code, title in sentinels_dropped(ws, world, pkg):
        f("warning", "sentinel-dropped", f"{name}: {ref} lists {code} ({title}), which the property does not accept",
          "If you left it out, add it (SCHEMA-STYLE.md, Sentinels); if a decision dropped it, cite that decision "
          "on the property's `sentinels` facet.", variable=name)
    for rid in rule_view(world, pkg)["ready"]:
        f("warning", "rule-ready", f"{rid} waits for variables that now exist", "Encode it now (SKIP-LOGIC.md).")
    for rid in suspected_unasked(world):
        f("warning", "rule-unasked", f"{rid} is suspected but not yet put to a person", "Include it in the next consent question.")
    for d in world.decisions.values():
        if d["status"] == "unsure":
            f("warning", "decision-unsure", f"{d['id']}: the person was not sure — record your decision on their behalf",
              "decide with the recommendation (review needed), apply it, record apply (INBOX.md).")
        elif d.get("unapplied"):
            f("warning", "decision-unapplied", f"{d['id']} ({d['status']}) is not yet reflected in the files",
              "Apply it, then record {\"type\": \"decision\", \"event\": \"apply\", \"id\": ...}.")
    n_inbox = len(inbox_pending(ws))
    if n_inbox:
        f("warning", "inbox-pending", f"{n_inbox} website submission(s) not yet processed", "`inbox list`, then `inbox take <id>` (INBOX.md).")
    for s in world.sources.values():
        if s.get("kind") == "document" and s.get("status") == "active" and not s.get("digest"):
            f("info", "source-undigested", f"{s['id']} ({s.get('title')}) has no digest yet", "Digest it (START.md, SUBAGENTS.md).")
        if s.get("status") == "suggested":
            f("info", "source-suggested", f"{s['id']} ({s.get('title')}) awaits a person's approval", "Put it in the next batch.")
    drift = asset_drift(ws)
    if drift:
        f("error" if strict else "warning", "assets-stale",
          f"{len(drift)} shipped file(s) differ from this skill's: " + ", ".join(d["file"] for d in drift[:6]),
          "Run `refresh-assets`, then `build`.")
    checks = run_validator(ws) if (validate and pkg.docs) else checks_report(ws)
    if pkg.docs:
        if not checks or not checks.get("ran"):
            f("error", "validator-not-run", (checks or {}).get("headline") or "validate.py has not run",
              (checks or {}).get("hint") or "Run `build`; see LAYOUT.md's fallback ladder.")
        else:
            for x in validator_findings(checks):
                if x.get("code") == "no-fixtures" and not drafted:
                    continue                             # toy data comes with the first drafted topic (BUILD.md)
                findings.append({"severity": x.get("severity"), "code": "validate:" + str(x.get("code")),
                                 "message": x.get("message"), "hint": x.get("hint"),
                                 **{k: x[k] for k in ("file", "pointer", "variable", "rule", "table") if k in x}})
    if built_hash(ws) != inputs_hash(ws):
        f("error" if strict else "warning", "site-stale", "the website shows an older state than the files", "Run `build`.")
    errors = [x for x in findings if x["severity"] == "error"]
    blocking = errors + [x for x in findings if x["code"] in BLOCKING_CODES]
    order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda x: (order.get(x["severity"], 3), x["code"]))
    return {"ok": not errors, "blocking": len(blocking),
            "counts": {s: sum(1 for x in findings if x["severity"] == s) for s in ("error", "warning", "info")},
            "validator": {k: (checks or {}).get(k) for k in ("ok", "headline")} if checks else None,
            "findings": findings[:LIST_CAP * 2], "truncated": len(findings) > LIST_CAP * 2}


# ===================================================================== sessions

def tell_user_lines(ws: Path, world: World, url: str | None, disk_note: bool = False) -> list[str]:
    proj = world.project
    harness = proj.get("harness") or ""
    inv = invoke_for(proj.get("invoke"), harness)
    where = url or (ws / "index.html").resolve().as_uri()
    asked = [d for d in world.decisions.values() if d["status"] == "asked"]
    for_steward = sum(1 for d in asked if d.get("to") == "steward")
    for_you = len(asked) - for_steward
    lines = [f"Your project website: {where}"]
    if disk_note:
        lines.append("It could not be served here, so open it straight from disk: it does not update by itself "
                     "(reload it when I say so), and instead of sending answers you press *Review & save*, then "
                     "*Download as a file*, and tell me where the file is. For live updates instead, run `python3 schemify/tools/serve.py` "
                     f"in your own terminal from {ws.parent} and open the address it prints — pick one way before "
                     "you start answering: unsent answers stay with the address you typed them at.")
    if for_you:
        lines.append(f"{for_you} question(s) are waiting for you there.")
    if for_steward:
        lines.append(f"{for_steward} question(s) wait there for the data steward (the website's *Answering as: data steward*).")
    in_review = [t for t in world.topics.values() if t.get("review") == "in-review"]
    if in_review:
        lines.append(f"{len(in_review)} topic(s) wait there for your review: on the Dictionary tab, *Looks right* or *Something's wrong*.")
    if harness == "codex":
        lines.append(f"To continue later: open your agent in {ws.parent} and start your message with {inv}.")
    else:
        lines.append(f"To continue later: open your agent in {ws.parent} and type {inv}.")
    return lines


def open_session(ws: Path, mode: str | None, harness: str | None, model: str | None, serve: bool) -> dict:
    proj = load_project(ws)
    changed = False
    for key, val in (("mode", mode), ("harness", harness)):
        if val and proj.get(key) != val:
            proj[key] = val
            changed = True
    if changed:
        save_project(ws, proj)
    world = load_world(ws)
    cur = world.open_session()
    reused = False
    if cur:
        started = parse_ts(cur.get("startedAt"))
        age_h = (datetime.now(timezone.utc) - started).total_seconds() / 3600 if started else 999
        if age_h < REOPEN_HOURS and cur.get("mode") == proj.get("mode", "build"):
            reused = True
        else:
            record_events(ws, [{"type": "session", "event": "end", "id": cur["id"], "forced": True,
                                "summary": "(this session ended without its closing checklist)",
                                "handoff": "Check `status` and the inbox; the previous agent did not close.",
                                "next": "see status"}])
    if not reused:
        record_events(ws, [{"type": "session", "event": "start", "mode": proj.get("mode", "build"),
                            **({"harness": harness or proj.get("harness")} if (harness or proj.get("harness")) else {}),
                            **({"model": model} if model else {})}])
    url, serve_note = None, None
    if serve:
        res = run_serve(ws, "start")
        url = res.get("url")
        if not res.get("ok"):
            serve_note = res.get("error")
    build(ws, validate=False)
    st = status_payload(ws)
    st["sessionReused"] = reused
    if url:
        st["website"] = url
        st["websiteServed"] = True
    if serve_note:
        st["websiteNote"] = serve_note + " — the page still works opened from disk (schemify/index.html)."
    st["tell_user"] = tell_user_lines(ws, load_world(ws), url, disk_note=not url)
    return st


def close_session(ws: Path, payload: dict) -> dict:
    if not isinstance(payload, dict) or not payload.get("summary") or not payload.get("next"):
        raise Fail("close needs {\"summary\": ..., \"handoff\": ..., \"next\": ...} on stdin.",
                   "summary: what happened; handoff: what the next agent must know; next: one concrete step (or done).")
    b = build(ws, validate=True)
    c = check(ws, validate=False)
    blockers = [x for x in c["findings"] if x["severity"] == "error" or x["code"] in BLOCKING_CODES]
    if blockers and not payload.get("force"):
        raise Fail(f"Not closed: {len(blockers)} item(s) must be dealt with first.",
                   "Fix them; or, if the session must end anyway, send \"force\": true with a handoff that names each one.",
                   blockers=blockers[:20])
    if payload.get("force") and not payload.get("handoff"):
        raise Fail("A forced close needs a 'handoff' naming what is unfinished.", "Add it and send again.")
    world = load_world(ws)
    if not world.open_session():
        record_events(ws, [{"type": "session", "event": "start", "mode": world.project.get("mode", "build")}])
    record_events(ws, [{"type": "session", "event": "end", "summary": payload["summary"], "next": payload["next"],
                        **({"handoff": payload["handoff"]} if payload.get("handoff") else {}),
                        **({"forced": True} if payload.get("force") else {})}])
    build(ws, validate=False)
    world = load_world(ws)
    srv = server_info(ws)
    return {"ok": True, "closed": world.sessions[-1]["id"], "forced": bool(payload.get("force")),
            "checks": b.get("checks"), "blockers": blockers[:20] if payload.get("force") else [],
            "tell_user": ["Everything is saved."] + tell_user_lines(ws, world, (srv or {}).get("url"))}


def run_serve(ws: Path, cmd: str) -> dict:
    script = SKILL_DIR / "scripts" / "serve.py"
    try:
        proc = subprocess.run([sys.executable, str(script), cmd, "--ws", str(ws)], capture_output=True, text=True, timeout=30)
        return json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"serve.py {cmd} failed: {exc}",
                "hint": "Open schemify/index.html directly, or ask the user to run: python3 schemify/tools/serve.py"}


def set_activity(ws: Path, text: str) -> dict:
    world = load_world(ws)
    act = {"at": now(), "text": text[:300], "session": (world.open_session() or {}).get("id")}
    prev = read_json(ws / "state" / "activity.json", None) or {}
    act["stateAt"] = prev.get("stateAt")
    write_json(ws / "state" / "activity.json", act)
    write_activity_js(ws, act)
    return {"ok": True, "activity": act}


# ===================================================================== share, assets, init

SHARE_SKIP = re.compile(r"(^|/)(__pycache__|\.DS_Store|\.git)(/|$)|(^|/)state/server\.(json|log)(\.\d+)?$|"
                        r"(^|/)state/(presence|recheck)\.json$|\.tmp$")


def share(ws: Path, out: str | None) -> dict:
    proj = load_project(ws)
    dest = Path(out).expanduser() if out else ws.parent / f"{proj.get('slug') or 'study'}-schemify-{now()[:10].replace('-', '')}.zip"
    guard(dest.parent)
    warnings = []
    if inbox_pending(ws):
        warnings.append("Unprocessed website feedback is included; process it first if you can (`inbox take`).")
    n, size = 0, 0
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ws.rglob("*")):
            rel = p.relative_to(ws).as_posix()
            if p.is_dir() or SHARE_SKIP.search(rel):
                continue
            z.write(p, f"{ws.name}/{rel}")
            n += 1
            size += p.stat().st_size
    return {"ok": True, "file": str(dest), "files": n, "bytes": dest.stat().st_size, "warnings": warnings,
            "tell_user": [f"Send {dest.name} to the data steward (it contains copies of the source documents, no data).",
                          "They unzip it, open their coding agent in the folder that holds it, install the schemify skill "
                          "if they have not (README of github.com/jeyabbalas/skills), and type /schemify review.",
                          "No agent? They can open index.html, answer the review questions, and send you the feedback file it downloads."]}


def copy_shipped(ws: Path) -> list[str]:
    changed = []
    for src, dst in SHIPPED:
        s, d = SKILL_DIR / src, ws / dst
        if not s.exists():
            raise Fail(f"The skill is missing {src}.", "Reinstall the skill.")
        if d.exists() and d.read_bytes() == s.read_bytes():
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s, d)
        changed.append(dst)
    req = ws / "package" / "tools" / "requirements.txt"
    if not req.exists() or req.read_text(encoding="utf-8") != REQUIREMENTS:
        write_text(req, REQUIREMENTS)
        changed.append("package/tools/requirements.txt")
    return changed


def refresh_assets(ws: Path) -> dict:
    guard(ws)
    ensure_dirs(ws)
    changed = copy_shipped(ws)
    b = build(ws, validate=False)
    return {"ok": True, "changed": changed, "rebuilt": b["written"],
            "next": "Run `build` (with validation) before presenting anything." if changed else "Already current."}


def init(dirname: str, study: str, slug: str | None, invoke: str | None, harness: str | None) -> dict:
    target = Path(dirname).expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    guard(target)
    if is_workspace(target):
        ensure_dirs(target)
        changed = copy_shipped(target)
        return {"ok": True, "workspace": str(target.resolve()), "existing": True, "restored": changed,
                "next": "This workspace exists already: run `open` and follow `status` (resume)."}
    if target.exists() and any(target.iterdir()):
        raise Fail(f"{target} exists and is not a schemify workspace.",
                   "Pick another --dir (e.g. schemify-<study>), or ask the user what this folder is.")
    if not study or not study.strip():
        raise Fail("init needs --study.", "Use the study's name as the user writes it; you can change it later in project.json.")
    target.mkdir(parents=True, exist_ok=True)
    ensure_dirs(target)
    copy_shipped(target)
    slug = slugify(slug or study)
    proj = {"schemify": WS_FORMAT, "id": f"{slug}-{hashlib.sha256((str(target.resolve()) + now()).encode()).hexdigest()[:4]}",
            "study": study.strip(), "slug": slug, "description": "", "mode": "build",
            "invoke": invoke or "/schemify", "harness": harness or "", "idBase": f"https://schemas.example.org/{slug}/",
            "tables": [], "topics": [], "conventions": {}, "people": [],
            "preferences": {"batchSize": 8, "inferRules": "ask"}, "plan": {}, "created": now()[:10]}
    save_project(target, proj)
    (target / "state" / "ledger.jsonl").touch()
    write_text(target / "state" / "variables.csv", ",".join(INVENTORY_COLUMNS) + "\n")
    build(target, validate=False)
    return {"ok": True, "workspace": str(target.resolve()), "existing": False, "id": proj["id"],
            "next": "Run `open` (it records the session and starts the website), then continue with START.md."}


# ===================================================================== CLI

def stdin_json(file: str | None):
    try:
        text = Path(file).read_text(encoding="utf-8") if file else sys.stdin.read()
    except OSError as exc:
        raise Fail(f"Cannot read {file}: {exc}", "Pass a readable file, or send the JSON on stdin.")
    if not text.strip():
        raise Fail("No JSON received.", "Send the event(s) on stdin with a quoted heredoc: <<'EOF' … EOF")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise Fail(f"Not valid JSON: {exc}", "Check quotes and commas; send it with a quoted heredoc (<<'EOF') so the shell leaves it alone.")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ws", help="workspace folder (default: found from the current directory)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("--study", required=True)
    s.add_argument("--dir", default="schemify")
    s.add_argument("--slug")
    s.add_argument("--invoke")
    s.add_argument("--harness")
    s = sub.add_parser("open")
    s.add_argument("--mode", choices=["build", "review"])
    s.add_argument("--harness")
    s.add_argument("--model")
    s.add_argument("--no-serve", action="store_true")
    sub.add_parser("status")
    s = sub.add_parser("record")
    s.add_argument("--file")
    s = sub.add_parser("show")
    s.add_argument("ids", nargs="+")
    s = sub.add_parser("queue")
    s.add_argument("--for", dest="who", choices=["author", "steward"], default="author")
    s.add_argument("--topic")
    s.add_argument("--limit", type=int, default=20)
    s = sub.add_parser("inbox")
    s.add_argument("action", choices=["list", "take", "import"])
    s.add_argument("arg", nargs="?")
    s = sub.add_parser("build")
    s.add_argument("--no-validate", action="store_true")
    s = sub.add_parser("check")
    s.add_argument("--strict", action="store_true", help="fail (exit 1) also when the website or shipped files are stale")
    s = sub.add_parser("activity")
    s.add_argument("text", nargs="+")
    s = sub.add_parser("close")
    s.add_argument("--file")
    s = sub.add_parser("data-check")
    s.add_argument("dataset")
    s.add_argument("--timeout", type=int, default=1800)
    s = sub.add_parser("serve")
    s.add_argument("action", choices=["start", "stop", "status"])
    s = sub.add_parser("share")
    s.add_argument("--out")
    sub.add_parser("refresh-assets")
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) > 1:                                  # accept --ws after the command name too
        moved, rest, i = [], [argv[0]], 1
        while i < len(argv):
            tok = argv[i]
            if tok == "--ws" and i + 1 < len(argv):
                moved += [tok, argv[i + 1]]
                i += 2
                continue
            if tok.startswith("--ws="):
                moved.append(tok)
            else:
                rest.append(tok)
            i += 1
        argv = moved + rest if argv[0] != "--ws" and not argv[0].startswith("--ws=") else argv
    a = p.parse_args(argv)
    try:
        if a.cmd == "init":
            emit(init(a.dir, a.study, a.slug, a.invoke, a.harness))
        ws = find_ws(a.ws)
        if a.cmd == "open":
            emit(open_session(ws, a.mode, a.harness, a.model, not a.no_serve))
        if a.cmd == "status":
            emit(status_payload(ws))
        if a.cmd == "record":
            emit({"ok": True, **record_events(ws, stdin_json(a.file))})
        if a.cmd == "show":
            emit(show_items(ws, a.ids))
        if a.cmd == "queue":
            emit(queue_items(ws, a.who, a.topic, a.limit))
        if a.cmd == "inbox":
            if a.action == "list":
                emit(inbox_list(ws))
            if not a.arg:
                raise Fail(f"inbox {a.action} needs an argument.", "inbox take <submission id> | inbox import <file>")
            emit(take_submission(ws, a.arg) if a.action == "take" else inbox_import(ws, a.arg))
        if a.cmd == "build":
            emit(build(ws, validate=not a.no_validate))
        if a.cmd == "check":
            res = check(ws, strict=a.strict)
            emit(res, 0 if res["ok"] else 1)
        if a.cmd == "activity":
            emit(set_activity(ws, " ".join(a.text)))
        if a.cmd == "close":
            emit(close_session(ws, stdin_json(a.file)))
        if a.cmd == "data-check":
            emit(run_data_check(ws, a.dataset, a.timeout))
        if a.cmd == "serve":
            res = run_serve(ws, a.action)
            emit(res, 0 if res.get("ok") else 1)
        if a.cmd == "share":
            emit(share(ws, a.out))
        if a.cmd == "refresh-assets":
            emit(refresh_assets(ws))
    except Fail as exc:
        emit({"ok": False, "error": exc.error, "hint": exc.hint, **exc.extra}, 1)
    except SystemExit:
        raise
    except Exception as exc:  # never a bare traceback for the agent
        import traceback
        emit({"ok": False, "error": f"internal error: {exc!r}",
              "hint": "A bug in schemify.py — report it. Files are unchanged unless this command's earlier steps said otherwise.",
              "trace": traceback.format_exc().splitlines()[-6:]}, 1)


if __name__ == "__main__":
    main()
