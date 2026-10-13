#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Convert a schemify 1.x package into a schemify 2 workspace, as far as it can be done mechanically.

A 1.x package is a folder (default `json_schema/`) holding the schemas beside PROGRESS.md,
DECISIONS.md, SOURCES.md, VARIABLES.csv, and ROUTING.csv -- or, after its cleanup, the
schemas with VARIABLES.csv, ROUTING.csv and a README. This script builds the 2.x workspace
next to it and never modifies or deletes the old folder:

  - copies the table folders and common/ into package/schemas/ (same relative paths, so $ids hold)
  - copies the dictionary files SOURCES.md lists into sources/ and registers them
  - turns DECISIONS.md lines into decisions, ROUTING.csv rows into rules, VARIABLES.csv into
    state/variables.csv, PROGRESS.md categories into topics (confirmed ones keep their approval)
  - adds x-provenance (from the inventory's source column) and x-value-kind (to special codes)
    where it can, rewrites 1.x decision ids inside $comments to the new ids
  - copies the toy fixtures to package/toy-data/<table>/

Usage:    uv run <skill-dir>/scripts/migrate.py --from json_schema [--to schemify] [--study NAME] [--person author|steward]
Fallback: python3 <skill-dir>/scripts/migrate.py ...   (standard library only)

Prints one JSON object: what was converted, the id map, and `attention` -- every place a
person or the agent must finish by hand (MIGRATE.md says how). Exit 0 on success, 1 on error.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True          # never write __pycache__ into the (read-only) skill directory
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schemify as sf  # noqa: E402  (the workspace tool, standard library only)

DEC_LINE = re.compile(r"^\s*-\s*(D\d{3,})\s*·\s*(\d{4}-\d{2}-\d{2})\s*·\s*(.+)$")
OLD_DEC = re.compile(r"\bD(\d{3,})\b")
MISSING_WORDS = re.compile(r"(missing|unknown|not applicable|n/a|inapplicable|skip|refus|don'?t know|do not know|not asked|not collected|structural)", re.I)
STATUS_MAP = {"converted": "include", "pending": "include", "deferred": "deferred", "dropped": "dropped", "added": "added"}
EVIDENCE_MAP = {"quoted": "documented", "implied": "implied", "steward": "told", "inferred": "inferred"}
RULE_STATUS_MAP = {"waiting": "waiting", "proposed": "suspected", "confirmed": "waiting", "encoded": "encoded",
                   "declined": "declined", "not-enforceable": "not-expressible"}


def fail(msg: str, hint: str) -> None:
    print(json.dumps({"ok": False, "error": msg, "hint": hint}, indent=2))
    sys.exit(1)


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return ""


def parse_decisions(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        m = DEC_LINE.match(line)
        if not m:
            continue
        parts = [p.strip() for p in m.group(3).split("·")]
        rec = {"old": m.group(1), "date": m.group(2), "scope": parts[0] if parts else "",
               "decision": parts[1] if len(parts) > 1 else "", "why": parts[2] if len(parts) > 2 else "",
               "confidence": " · ".join(parts[3:-1]) if len(parts) > 4 else (parts[3] if len(parts) > 3 else ""),
               "status": parts[-1] if len(parts) > 4 else "active"}
        out.append(rec)
    return out


def guess_kind(rec: dict) -> str:
    text = (rec["scope"] + " " + rec["decision"]).lower()
    if rec["scope"] == "package":
        return "convention"
    if "rout" in text or "skip" in text or "applicability" in text:
        return "rule"
    if "bound" in text or "range" in text:
        return "guess"
    if rec["confidence"].startswith("open"):
        return "gap"
    return "knowledge" if rec["confidence"].startswith("user-confirmed") and "agent-decided" not in rec["confidence"] else "guess"


def scope_targets(scope: str) -> list[str]:
    m = re.search(r"\.([A-Za-z_][A-Za-z0-9_]*)$", scope)
    return [m.group(1)] if m else []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", required=True, help="the 1.x package folder")
    ap.add_argument("--to", default="schemify", help="the new workspace folder (default schemify)")
    ap.add_argument("--study", help="study name (default: PROGRESS.md's title)")
    ap.add_argument("--person", choices=["author", "steward"], default="author",
                    help="who answered the 1.x questions (default author)")
    a = ap.parse_args()
    old = Path(a.src).expanduser().resolve()
    if not old.is_dir():
        fail(f"{a.src} is not a folder.", "Pass the 1.x package folder, e.g. --from json_schema.")
    mothers = sorted(old.glob("*/*.schema.json"))
    if not mothers:
        fail(f"No */*.schema.json under {old}.", "This does not look like a schemify 1.x package.")
    attention: list[str] = []
    progress = read(old / "PROGRESS.md")
    title = re.search(r"^#\s+(.+?)(?:\s+—\s+conversion progress)?\s*$", progress, re.M)
    study = a.study or (title.group(1).strip() if title else old.parent.name)

    try:
        res = sf.init(a.to, study, None, "/schemify", "")
    except sf.Fail as exc:
        fail(exc.error, exc.hint)
    ws = Path(res["workspace"])
    if res.get("existing"):
        fail(f"{ws} already exists.", "Migrate into a fresh folder: pass --to schemify-migrated, or move the existing one.")
    session_id = sf.record_events(ws, [{"type": "session", "event": "start", "mode": "build", "harness": "migration"}])["recorded"][0]["id"]

    # ---- schemas
    schemas = ws / "package" / "schemas"
    tables = []
    for m in mothers:
        tdir = m.parent
        shutil.copytree(tdir, schemas / tdir.name, dirs_exist_ok=True)
        tables.append(tdir.name)
    if (old / "common").is_dir():
        shutil.copytree(old / "common", schemas / "common", dirs_exist_ok=True)

    # ---- sources
    src_text = read(old / "SOURCES.md")
    source_ids: dict[str, str] = {}
    events = []
    block = re.search(r"## Dictionary files\s*\n(.*?)(?:\n## |\Z)", src_text, re.S)
    n = 0
    for line in (block.group(1) if block else "").splitlines():
        m = re.match(r"\s*-\s*`([^`]+)`\s*·\s*(.*)$", line)
        if not m:
            continue
        rel = m.group(1)
        cand = [old / rel, old.parent / rel, Path(rel)]
        f = next((c for c in cand if c.is_file()), None)
        if not f:
            attention.append(f"SOURCES.md lists {rel}, which was not found: register it by hand (START.md, step 2).")
            continue
        n += 1
        sid = f"S{n:02d}"
        dest = ws / "sources" / f.name                      # copies keep their original file names (LAYOUT.md)
        k = 2
        while dest.exists():
            dest = ws / "sources" / f"{f.stem}-{k}{f.suffix}"
            k += 1
        shutil.copyfile(f, dest)
        source_ids[f.name] = sid
        source_ids[rel] = sid
        events.append({"type": "source", "event": "add", "kind": "document", "title": f.stem, "what": m.group(2)[:200],
                       "path": str(dest.relative_to(ws)), "original": str(f), "origin": "user", "notes": "migrated from 1.x SOURCES.md"})
        dg = ws / "sources" / sid / "DIGEST.md"
        dg.parent.mkdir(parents=True, exist_ok=True)
        dg.write_text(f"# {sid} — {f.name}\n\nMigrated from schemify 1.x. Its parse notes:\n\n> {m.group(2)}\n\n"
                      "The variables are already in the schemas and in state/variables.csv. Run extract.py on this source "
                      "and extend this digest the next time a topic needs it (START.md, step 4).\n", encoding="utf-8")
        events.append({"type": "source", "event": "digest", "id": sid, "path": str(dg.relative_to(ws)), "verified": []})
    if not source_ids:
        attention.append("No dictionary file could be registered: register the sources by hand, then fix x-provenance.")
    ext = re.search(r"## External sources\s*\n(.*?)(?:\n## |\Z)", src_text, re.S)
    for line in (ext.group(1) if ext else "").splitlines():
        if not line.strip().startswith("-"):
            continue
        url = re.search(r"https?://\S+", line)
        if url:
            events.append({"type": "source", "event": "add", "kind": "web", "title": line.strip("- ").split("·")[0].strip()[:120],
                           "what": "migrated from 1.x SOURCES.md", "url": url.group(0).rstrip(").,"), "origin": "agent"})
        else:
            attention.append(f"External source without a URL: {line.strip('- ')[:120]} — ask the user for the file and register it.")
    if events:
        sf.record_events(ws, events)

    def ref_from(text: str) -> str | None:
        m = re.search(r"([\w./-]+\.(?:csv|xlsx|xls|pdf|docx|txt|json|html?))\s+(row|rows|p\.?|page|sheet)\s*([\w–-]+)", text or "")
        if not m:
            return None
        sid = source_ids.get(m.group(1)) or source_ids.get(Path(m.group(1)).name)
        if not sid:
            return None
        loc = {"rows": "row", "page": "p.", "p": "p.", "p.": "p."}.get(m.group(2), m.group(2))
        return f"{sid}:{loc} {m.group(3)}" if not loc.endswith(".") else f"{sid}:{loc}{m.group(3)}"

    # ---- decisions
    decs = parse_decisions(read(old / "DECISIONS.md"))
    idmap: dict[str, str] = {}
    for rec in decs:
        kind = guess_kind(rec)
        base = {"type": "decision", "kind": kind, "question": rec["decision"] or rec["scope"], "targets": scope_targets(rec["scope"]),
                "note": f"migrated from 1.x {rec['old']} ({rec['date']}): {rec['why']}"[:600], "ref": rec["old"]}
        conf = rec["confidence"]
        if conf.startswith("open"):
            ev = dict(base, event="open", options=[{"id": "keep", "label": "Keep the current encoding"},
                                                   {"id": "change", "label": "Change it (say how)"}],
                      recommended="keep", why="Migrated from schemify 1.x, where this question was still open.", provisional="keep")
            batch = []
        elif "agent-decided" in conf and "user-confirmed" in conf:
            ev = dict(base, event="decide", choice=rec["decision"] or "as encoded", why=rec["why"] or "1.x decision", applied=True)
            batch = [{"type": "decision", "event": "confirm", "id": f"@{rec['old']}", "by": a.person, "via": "migration"}]
        elif conf.startswith("user-confirmed"):
            ev = dict(base, event="answer", by=a.person, via="migration", choice="other", text=rec["decision"], applied=True)
            batch = []
        else:
            ev = dict(base, event="decide", choice=rec["decision"] or "as encoded", why=rec["why"] or "1.x agent decision", applied=True)
            batch = []
        try:
            out = sf.record_events(ws, [ev] + batch)
        except sf.Fail as exc:
            attention.append(f"{rec['old']} could not be migrated ({'; '.join(exc.extra.get('problems', [exc.error]))[:300]}) — record it by hand.")
            continue
        idmap[rec["old"]] = out["recorded"][0]["id"]
    superseded = set()
    for rec in decs:
        m = re.match(r"superseded-by\s+(D\d{3,})", rec["status"])
        if m and rec["old"] in idmap and m.group(1) in idmap:
            sf.record_events(ws, [{"type": "decision", "event": "supersede", "id": idmap[rec["old"]], "replacement": idmap[m.group(1)]}])
            superseded.add(idmap[rec["old"]])

    # ---- project.json: tables, topics, conventions
    proj = sf.load_project(ws)
    cats = re.findall(r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?\.json)\s*\|[^|]*\|[^|]*\|\s*([^|]+?)\s*\|", progress, re.M)
    topics, confirmed = [], []
    for name, rel, status in cats:
        rel = rel.strip()
        topics.append({"id": Path(rel).stem, "title": name.strip(), "table": rel.split("/")[0], "file": rel})
        if status.strip().startswith("confirmed"):
            confirmed.append(Path(rel).stem)
    if not topics:
        for t in tables:
            for f in sorted((schemas / t / "categories").glob("*.json")):
                doc = json.loads(read(f) or "{}")
                topics.append({"id": f.stem, "title": str(doc.get("title") or f.stem).split("—")[-1].strip(), "table": t,
                               "file": f"{t}/categories/{f.name}"})
        attention.append("No categories table in PROGRESS.md: topics were taken from the category files — check their order.")
    proj["tables"] = []
    for t in tables:
        mdoc = json.loads(read(schemas / t / f"{t}.schema.json") or "{}")
        g = re.search(r"(One element is one [^.]+\.)", str(mdoc.get("description") or ""))
        proj["tables"].append({"name": t, "title": t.replace("_", " ").capitalize(),
                               "grain": g.group(1) if g else "One element is one row.", "mother": f"{t}/{t}.schema.json"})
        if not g:
            attention.append(f"Table {t}: no grain sentence found — set project.json → tables → grain with the user.")
        idm = re.match(r"(https?://.+/)" + re.escape(t) + "/", str(mdoc.get("$id") or ""))
        if idm:
            proj["idBase"] = idm.group(1)
    proj["topics"] = topics
    sent = re.search(r"^- sentinels:\s*(.+?)\s*·\s*(D\d{3,})\s*$", progress, re.M)
    if sent:
        codes = re.findall(r"(-?\d+)\s+([^·]+)", sent.group(1))
        proj["conventions"] = {"missing": "in-band codes", "sentinels": [
            {"code": int(c), "meaning": mng.strip(), "structural": bool(re.search(r"not applicable|structural|skip", mng, re.I)),
             "decision": idmap.get(sent.group(2), "")} for c, mng in codes]}
    routing = re.search(r"^- routing:\s*(\w+)", progress, re.M)
    if routing:
        proj["preferences"]["inferRules"] = {"full": "ask", "undecided": "ask", "faithful": "no", "declined": "no"}.get(routing.group(1), "ask")
    proj["people"] = [{"role": a.person, "name": "", "profile": "", "knows": []}]
    attention.append("project.json → people → profile and description: set them from a short conversation (INTERVIEW.md).")
    sf.save_project(ws, proj)

    # ---- inventory
    inv_rows = list(csv.DictReader(io.StringIO(read(old / "VARIABLES.csv"))))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(sf.INVENTORY_COLUMNS)
    src_of: dict[str, str] = {}
    for r in inv_rows:
        r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
        table = r.get("table") or (tables[0] if len(tables) == 1 else "")
        ref = ref_from(r.get("source", ""))
        dmention = OLD_DEC.findall(r.get("source", "") + " " + r.get("notes", ""))
        if not ref and r.get("status") == "added" and dmention:
            ref = idmap.get("D" + dmention[0], "")
        if ref:
            src_of[f"{table}.{r.get('variable')}"] = ref
        w.writerow([r.get("variable"), table, r.get("category", ""), STATUS_MAP.get(r.get("status", ""), "include"), ref or "",
                    OLD_DEC.sub(lambda m: idmap.get(m.group(0), m.group(0)), r.get("notes", ""))])
        if not ref:
            attention.append(f"variables.csv: {r.get('variable')} has no source reference — set its `source` column.")
    sf.write_text(ws / "state" / "variables.csv", buf.getvalue())

    # ---- schemas: provenance, value kinds, decision ids
    renamed = lambda s: OLD_DEC.sub(lambda m: idmap.get(m.group(0), m.group(0)), s)  # noqa: E731
    for f in sorted(schemas.rglob("*.json")):
        doc = json.loads(read(f) or "null")
        if not isinstance(doc, dict):
            continue
        table = f.relative_to(schemas).parts[0]

        def fix(node, name=None):
            if isinstance(node, dict):
                if "$comment" in node and isinstance(node["$comment"], str):
                    node["$comment"] = renamed(node["$comment"])
                if "const" in node and "title" in node and "x-value-kind" not in node and MISSING_WORDS.search(str(node["title"])):
                    node["x-value-kind"] = "sentinel"
                for k, v in list(node.items()):
                    fix(v, k)
            elif isinstance(node, list):
                for v in node:
                    fix(v)
        fix(doc)
        props = doc.get("properties") if isinstance(doc.get("properties"), dict) else {}
        for name, sch in props.items():
            if not isinstance(sch, dict) or "x-provenance" in sch:
                continue
            ref = src_of.get(f"{table}.{name}")
            if ref:
                prov = {"default": ref}
                mentioned = [idmap.get("D" + d) for d in OLD_DEC.findall(json.dumps(sch))]
                live = [x for x in mentioned if x and x not in superseded]
                pick = live[-1] if live else None
                low = str(sch.get("$comment", "")).lower()
                if pick and ("bound" in low or "range" in low):
                    prov["minimum"] = prov["maximum"] = pick
                elif pick and "pattern" in low:
                    prov["pattern"] = pick
                elif pick and pick != ref:
                    attention.append(f"{f.relative_to(ws)}: {name} mentions {pick} — cite it on the facet it settles.")
                ordered = {k: sch[k] for k in ("title", "description", "$comment") if k in sch}
                ordered["x-provenance"] = prov
                ordered.update({k: v for k, v in sch.items() if k not in ordered})
                props[name] = ordered
            else:
                attention.append(f"{f.relative_to(ws)}: {name} has no x-provenance — add it (SCHEMA-STYLE.md).")
        if isinstance(doc.get("$defs"), dict):
            for k, v in doc["$defs"].items():
                if isinstance(v, dict) and "x-provenance" not in v:
                    attention.append(f"{f.relative_to(ws)}: $defs/{k} has no x-provenance — cite the source line that defines it.")
        items = doc.get("items") if isinstance(doc.get("items"), dict) else {}
        for ent in items.get("allOf") or []:
            if isinstance(ent, dict) and "if" in ent and "x-provenance" not in ent:
                rid = re.search(r"\bR\d{3,}\b", str(ent.get("$comment", "")))
                ent_prov = None
                for row in csv.DictReader(io.StringIO(read(old / "ROUTING.csv"))):
                    if rid and row.get("id") == rid.group(0):
                        ent_prov = ref_from(row.get("source", "")) or idmap.get((row.get("decision") or "").strip())
                if ent_prov:
                    c, i, t = ent.pop("$comment", None), ent.pop("if"), ent.pop("then", None)
                    rest = dict(ent)
                    ent.clear()
                    if c is not None:
                        ent["$comment"] = c
                    ent["x-provenance"] = {"default": ent_prov}
                    ent["if"] = i
                    if t is not None:
                        ent["then"] = t
                    ent.update(rest)
                else:
                    attention.append(f"{f.relative_to(ws)}: rule {rid.group(0) if rid else '(no id)'} has no x-provenance — add it.")
        sf.write_json(f, doc)

    # ---- rules
    revents = []
    for row in csv.DictReader(io.StringIO(read(old / "ROUTING.csv"))):
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        if not row.get("id"):
            continue
        status = RULE_STATUS_MAP.get(row.get("status", ""), "waiting")
        ev = {"type": "rule", "event": "add", "id": row["id"], "table": row.get("table") or (tables[0] if len(tables) == 1 else ""),
              "gates": [x for x in row.get("trigger", "").split(";") if x], "targets": [x for x in row.get("targets", "").split(";") if x],
              "reading": row.get("rule") or "(no reading)", "evidence": EVIDENCE_MAP.get(row.get("evidence", ""), "documented"),
              "status": status, "note": (row.get("notes") or "migrated from 1.x")[:300]}
        ref = ref_from(row.get("source", ""))
        if ref:
            ev["refs"] = [ref]
        if row.get("decision") in idmap:
            ev["decision"] = idmap[row["decision"]]
        if status == "waiting":
            ev["waits_for"] = ev["targets"] or ["(see note)"]
        if ev["evidence"] == "inferred" and status == "encoded":
            attention.append(f"{row['id']} is inferred and encoded: record the person's consent (SKIP-LOGIC.md) and set `consent`.")
        revents.append(ev)
    for ev in revents:
        try:
            sf.record_events(ws, [ev])
        except sf.Fail as exc:
            attention.append(f"{ev['id']} could not be migrated ({'; '.join(exc.extra.get('problems', [exc.error]))[:300]}) — record it by hand.")

    # ---- toy data
    for t in tables:
        srcdir = old / "examples" / t if len(tables) > 1 else old / "examples"
        for a_, b_ in (("toy_valid.json", "valid.json"), ("toy_invalid.json", "invalid.json"), ("toy_invalid_ledger.json", "invalid-ledger.json")):
            if (srcdir / a_).is_file():
                dst = ws / "package" / "toy-data" / t / b_
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(renamed(read(srcdir / a_)), encoding="utf-8")
            else:
                attention.append(f"toy data {t}/{b_} not found — write it (DATA-CHECK.md).")

    # ---- confirmed topics keep their approval
    tev = [{"type": "topic", "event": "approve", "id": tid, "by": a.person, "via": "migration", "note": "confirmed in schemify 1.x"}
           for tid in confirmed if tid in {t["id"] for t in topics}]
    if tev:
        sf.record_events(ws, tev)
    sf.write_text(ws / "sources" / "MIGRATION.md", "# Migration from schemify 1.x\n\nFrom `" + str(old) + "`.\n\n| 1.x | 2 |\n|---|---|\n"
                  + "".join(f"| {k} | {v} |\n" for k, v in idmap.items()) + "\n## Left to do\n\n" + "".join(f"- {x}\n" for x in attention))
    sf.record_events(ws, [{"type": "session", "event": "end", "id": session_id,
                           "summary": f"Converted the schemify 1.x package in {old.name}/ by script: {len(idmap)} decisions, "
                                      f"{len(revents)} rules, {len(topics)} topics.",
                           "handoff": f"{len(attention)} item(s) could not be converted mechanically; sources/MIGRATION.md "
                                      "lists them under Left to do (MIGRATE.md says how to finish each).",
                           "next": "Finish the migration (MIGRATE.md, step 2)."}])
    sf.build(ws, validate=False)
    print(json.dumps({"ok": True, "workspace": str(ws), "tables": tables, "topics": [t["id"] for t in topics],
                      "sources": source_ids, "decisions": len(idmap), "rules": len(revents), "idMap": idmap,
                      "attention": attention[:60], "attentionTotal": len(attention),
                      "next": "Work through `attention` (MIGRATE.md), then `schemify.py build` and `check` until green."}, indent=2))


if __name__ == "__main__":
    main()
