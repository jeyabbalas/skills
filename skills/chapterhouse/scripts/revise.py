#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["fsrs>=6"]
# ///
"""Spaced-revision scheduler for a chapterhouse study workspace — a pure reader.

Run with `uv run scripts/revise.py …` (uv resolves the FSRS scheduler
automatically). No uv? Plain `python3 scripts/revise.py …` still works — the
script falls back to an inlined SM-2 scheduler (stdlib only) and the output's
`scheduler` field names which engine ran; `python3 -m pip install --user fsrs`
upgrades it to FSRS in place. No Python at all? Item scheduling is paused, not
skipped: revise chapter-tier from CONTENTS.md's Leitner boxes and log the
item-tier debt (ladder in LAYOUT.md) — never skip revision silently.

This script never writes a file. All item state is derived by replaying
books/<slug>/reviews.jsonl (the agent appends ledger lines; DECK-FORMAT.md
defines them). Identical ledger + --today gives identical output; omit --today
and today's local date is used and echoed (`today_source: "clock"`).

Subcommands (all print JSON to stdout):

  due [DIR] [--book S] [--today YYYY-MM-DD] [--limit N] [--scheduler auto|fsrs|sm2]
      Due and new cards plus an interleaved session plan (shuffled across
      chapters and item types, prerequisite chapters early, capped at --limit,
      default 20). Plan items carry no chapter field — do not name an item's
      chapter aloud before it is graded. With several books and no --book,
      prints per-book due counts instead of a plan.

  stats [DIR] [--book S] [--today YYYY-MM-DD] [--scheduler auto|fsrs|sm2]
      Per-chapter attempts, accuracy, mean rating, Brier score, reliability by
      claimed confidence, blind-spot flags — the dashboard's numbers, and the
      ledger validator (`ledger_warnings` must be empty at session close).

  exam --book S [DIR] [--chapters 1-8] [--n 20] [--today YYYY-MM-DD]
      Coverage-weighted cumulative exam spec: recent misses, low Leitner boxes,
      and high-Brier chapters oversampled; Bloom mix enforced; interleaved
      order. The agent copies the items into exams/exam-NN.md (ASSESS.md).
"""

import argparse
import datetime as dt
import hashlib
import json
import random
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

CARD_HEADER = re.compile(
    r"^### (ch\d{2,3}-c\d{3}) · (term|concept|apply|analyze|evaluate|create)"
    r"(?: · stage: (worked|completion|full)\b.*)?$"
)
META = re.compile(r"^(born|bloom|anchor|links|status): (.+)$")
RATINGS = {"again": 1, "hard": 2, "good": 3, "easy": 4}
MODES = {"recite", "revise", "exam", "practice"}
CONFS = {25, 50, 75, 90, 99}
BLOOM_DEFAULT = {"term": "remember", "concept": "understand", "apply": "apply",
                 "analyze": "analyze", "evaluate": "evaluate", "create": "create"}
CARD_ID = re.compile(r"^ch(\d{2,3})-c\d{3}$")


def card_chapter(cid):
    m = CARD_ID.match(str(cid))
    return int(m.group(1)) if m else None


def fail(error, hint):
    print(json.dumps({"ok": False, "error": error, "hint": hint}, indent=2))
    sys.exit(1)


# ---------- scheduler engines (everything funnels through schedule()) ----------

_ENGINE, _ENGINE_NAME = "sm2", "sm2-fallback"


def _probe_fsrs():
    global _ENGINE, _ENGINE_NAME
    try:
        from fsrs import Scheduler, Card, Rating  # noqa: F401
        s = Scheduler(desired_retention=0.9, enable_fuzzing=False)
        c = Card()
        s.review_card(c, Rating.Good,
                      review_datetime=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc))
        from importlib.metadata import version
        _ENGINE, _ENGINE_NAME = "fsrs", "fsrs-" + version("fsrs")
    except Exception:
        pass  # anything wrong with fsrs → the inlined SM-2 runs instead


def _schedule_fsrs(history):
    from fsrs import Scheduler, Card, Rating
    sched = Scheduler(desired_retention=0.9, enable_fuzzing=False)
    rating = {"again": Rating.Again, "hard": Rating.Hard,
              "good": Rating.Good, "easy": Rating.Easy}
    card, lapses, last = Card(), 0, None
    for r in history:
        if r["rating"] == "again" and last is not None:
            lapses += 1
        card, _ = sched.review_card(card, rating[r["rating"]], review_datetime=r["ts"])
        last = r["ts"]
    due = card.due.date()
    return {
        "due": due,
        "state": getattr(card.state, "name", str(card.state)).lower(),
        "reps": len(history),
        "lapses": lapses,
        "interval": max(1, (due - last.date()).days),
        "last_review": last.date(),
        "last_rating": history[-1]["rating"],
    }


def _schedule_sm2(history):
    """Modified SM-2: EF per the classic rule; due anchored to the ACTUAL review
    date; a successful late review credits the elapsed time (I = max(I, elapsed))."""
    ef, n, interval, last, lapses, due = 2.5, 0, 0, None, 0, None
    for r in history:
        q = {"again": 2, "hard": 3, "good": 4, "easy": 5}[r["rating"]]
        d = r["ts"].date()
        elapsed = (d - last).days if last else 0
        if q < 3:
            if last is not None:
                lapses += 1
            n, interval = 0, 1
        else:
            n += 1
            interval = 1 if n == 1 else 6 if n == 2 else round(interval * ef)
            interval = max(interval, elapsed)
        ef = max(1.3, ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
        last = d
        due = d + dt.timedelta(days=interval)
    return {
        "due": due,
        "state": "learning" if n < 3 else "review",
        "reps": len(history),
        "lapses": lapses,
        "interval": max(1, interval),
        "last_review": last,
        "last_rating": history[-1]["rating"],
    }


def schedule(history):
    """The only entry point the rest of the file uses; swap engines here."""
    return _schedule_fsrs(history) if _ENGINE == "fsrs" else _schedule_sm2(history)


# ---------- workspace parsing (read-only) ----------

def find_book(root, book, required=False):
    books_dir = root / "books"
    if book:
        d = books_dir / book
        if not d.is_dir():
            fail("No such book: books/" + book,
                 "Check SHELF.md for the slug, or run without --book to list books.")
        return [d]
    if not books_dir.is_dir():
        fail("No books/ directory here.",
             "Run from the study workspace root (where SHELF.md lives).")
    cands = sorted(d for d in books_dir.iterdir()
                   if d.is_dir() and ((d / "decks").is_dir() or (d / "reviews.jsonl").exists()
                                      or (d / "CONTENTS.md").exists()))
    if not cands:
        fail("No books with decks, a ledger, or a manifest found under books/.",
             "Nothing to schedule yet — pass 1 creates CONTENTS.md, pass 2 creates decks.")
    if required and len(cands) > 1:
        fail("Several books on the shelf: " + ", ".join(d.name for d in cands),
             "Pass --book <slug>.")
    return cands


def parse_decks(book_dir):
    cards = {}
    for deck in sorted(book_dir.glob("decks/ch*.md")):
        current = None
        for line in deck.read_text().splitlines():
            m = CARD_HEADER.match(line)
            if m:
                cid, ctype, stage = m.group(1), m.group(2), m.group(3)
                current = {
                    "card": cid, "chapter": int(cid[2:cid.index("-")]), "type": ctype,
                    "stage": stage, "bloom": BLOOM_DEFAULT[ctype], "born": None,
                    "active": True, "deck": "decks/" + deck.name,
                }
                cards[cid] = current
                continue
            if current is not None:
                m = META.match(line)
                if m:
                    key, val = m.group(1), m.group(2).strip()
                    if key == "bloom":
                        current["bloom"] = val.split()[0]
                    elif key == "born":
                        current["born"] = val
                    elif key == "status":
                        current["active"] = val.startswith("active")
                elif line.startswith("**"):
                    current = None  # past the meta block
    return cards


def parse_ledger(book_dir, cards, warnings):
    history = {}
    path = book_dir / "reviews.jsonl"
    if not path.exists():
        return history
    last_ts = None
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            warnings.append({"line": i, "issue": "malformed JSON"})
            continue
        try:
            ts = dt.datetime.fromisoformat(str(rec.get("ts", "")).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            warnings.append({"line": i, "issue": "unparseable ts"})
            continue
        if last_ts and ts < last_ts:
            warnings.append({"line": i, "issue": "ts earlier than the previous line"})
        last_ts = ts
        cid = rec.get("card")
        if rec.get("rating") not in RATINGS:
            warnings.append({"line": i, "issue": "rating outside again|hard|good|easy"})
            continue
        if rec.get("mode") not in MODES:
            warnings.append({"line": i, "issue": "mode outside recite|revise|exam|practice"})
        conf = rec.get("confidence")
        if conf is not None and conf not in CONFS:
            warnings.append({"line": i, "issue": "confidence outside 25/50/75/90/99"})
            conf = None
        if card_chapter(cid) is None:
            warnings.append({"line": i, "issue": "unusable card id " + repr(cid)})
            continue
        if cid not in cards:
            warnings.append({"line": i, "issue": "unknown card id " + repr(cid)})
        history.setdefault(cid, []).append({
            "ts": ts, "rating": rec["rating"], "correct": bool(rec.get("correct")),
            "confidence": conf,
        })
    return history


def parse_contents(book_dir, notes):
    """Chapter table columns keyed by header names: ch, prereqs, status, box, due."""
    path = book_dir / "CONTENTS.md"
    chapters = {}
    if not path.exists():
        notes.append("contents: not parsed — CONTENTS.md missing")
        return chapters
    header, cols = None, {}
    for line in path.read_text().splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            if "ch" in cells:
                header = cells
                cols = {name: idx for idx, name in enumerate(cells)}
            continue
        if set(line) <= {"|", "-", " ", ":"}:
            continue
        try:
            ch = int(cells[cols["ch"]])
        except (ValueError, KeyError, IndexError):
            continue

        def cell(name):
            idx = cols.get(name)
            return cells[idx] if idx is not None and idx < len(cells) else "—"

        prereqs = []
        for tok in re.split(r"[,\s]+", cell("prereqs")):
            if tok.isdigit():
                prereqs.append(int(tok))
        box = cell("box")
        due = cell("due")
        chapters[ch] = {
            "prereqs": prereqs,
            "status": cell("status"),
            "box": int(box) if box.isdigit() else None,
            "due": due if re.match(r"^\d{4}-\d{2}-\d{2}$", due) else None,
        }
    if not chapters:
        notes.append("contents: not parsed — no chapter table with a 'ch' column found")
    return chapters


# ---------- ordering ----------

def topo_chapters(chapter_ids, contents):
    chs = sorted(set(chapter_ids))
    indeg = {c: 0 for c in chs}
    edges = {c: [] for c in chs}
    for c in chs:
        for p in contents.get(c, {}).get("prereqs", []):
            if p in indeg and p != c:
                edges[p].append(c)
                indeg[c] += 1
    order, ready = [], sorted(c for c in chs if indeg[c] == 0)
    while ready:
        c = ready.pop(0)
        order.append(c)
        for d in edges[c]:
            indeg[d] -= 1
            if indeg[d] == 0:
                ready.append(d)
        ready.sort()
    order += [c for c in chs if c not in order]  # cycle fallback, numeric order
    return order


def interleave(items, contents, seed, limit):
    """Deterministic round-robin across chapters (topological order, rotated by the
    seeded RNG), most-overdue-first within a chapter, breaking 3-long type streaks."""
    queues = {}
    for it in items:
        queues.setdefault(it["chapter"], []).append(it)
    for q in queues.values():
        q.sort(key=lambda it: (-it.get("_priority", 0.0), it["card"]))
    order = topo_chapters(queues.keys(), contents)
    rng = random.Random(seed)
    if order:
        off = rng.randrange(len(order))
        order = order[off:] + order[:off]
    plan, idx, prev_ch, types = [], 0, None, []
    while len(plan) < limit and any(queues.values()):
        pick = None
        for j in range(len(order)):
            ch = order[(idx + j) % len(order)]
            if not queues[ch]:
                continue
            if pick is None:
                pick = (ch, j)
            if ch != prev_ch:
                pick = (ch, j)
                break
        ch, j = pick
        if len(types) >= 2 and types[-1] == types[-2] == queues[ch][0]["type"]:
            for k in range(len(order)):
                alt = order[(idx + j + 1 + k) % len(order)]
                if queues[alt] and queues[alt][0]["type"] != queues[ch][0]["type"]:
                    ch = alt
                    j = j + 1 + k
                    break
        idx += j + 1
        item = queues[ch].pop(0)
        plan.append(item)
        prev_ch = ch
        types.append(item["type"])
    return plan


def seed_hex(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


# ---------- subcommands ----------

def resolve_today(args):
    if args.today:
        try:
            return dt.date.fromisoformat(args.today), "flag"
        except ValueError:
            fail("Could not parse --today " + repr(args.today), "Format: YYYY-MM-DD.")
    return dt.date.today(), "clock"


def replay_book(book_dir, today):
    warnings, notes = [], []
    cards = parse_decks(book_dir)
    history = parse_ledger(book_dir, cards, warnings)
    contents = parse_contents(book_dir, notes)
    due, new = [], []
    for cid, card in sorted(cards.items()):
        if not card["active"]:
            continue
        h = sorted(history.get(cid, []), key=lambda r: r["ts"])
        if not h:
            new.append({k: card[k] for k in ("card", "chapter", "type", "bloom", "stage",
                                             "born", "deck")})
            continue
        s = schedule(h)
        if s["due"] <= today:
            due.append({
                "card": cid, "chapter": card["chapter"], "type": card["type"],
                "bloom": card["bloom"], "stage": card["stage"], "deck": card["deck"],
                "due": s["due"].isoformat(), "days_overdue": (today - s["due"]).days,
                "state": s["state"], "reps": s["reps"], "lapses": s["lapses"],
                "interval": s["interval"], "last_rating": s["last_rating"],
                "_priority": (today - s["due"]).days / max(1, s["interval"]),
            })
    retired = sum(1 for c in cards.values() if not c["active"])
    replayed = sum(len(v) for v in history.values())
    return cards, history, contents, due, new, retired, replayed, warnings, notes


def chapters_due(contents, today):
    out = []
    for ch, row in sorted(contents.items()):
        if row["due"] and dt.date.fromisoformat(row["due"]) <= today:
            out.append({"chapter": ch, "box": row["box"], "due": row["due"]})
    return out


def cmd_due(args):
    root = Path(args.dir)
    today, source = resolve_today(args)
    books = find_book(root, args.book)
    if len(books) > 1:
        summary = []
        for b in books:
            _, _, contents, due, new, _, _, warnings, _ = replay_book(b, today)
            summary.append({"book": b.name, "due": len(due), "new": len(new),
                            "chapters_due": chapters_due(contents, today),
                            "ledger_warnings": len(warnings)})
        print(json.dumps({"ok": True, "scheduler": _ENGINE_NAME, "today": today.isoformat(),
                          "today_source": source, "books": summary,
                          "note": "Several books — re-run with --book for a session plan."},
                         indent=2))
        return
    b = books[0]
    cards, history, contents, due, new, retired, replayed, warnings, notes = \
        replay_book(b, today)
    dag_flags = []
    for it in due:
        for p in contents.get(it["chapter"], {}).get("prereqs", []):
            if contents.get(p, {}).get("status") == "unread":
                dag_flags.append({"card": it["card"],
                                  "issue": "chapter {} prerequisite ch {} is unread".format(
                                      it["chapter"], p)})
    seed = seed_hex(b.name, today.isoformat(), ",".join(sorted(it["card"] for it in due)))
    plan = interleave(list(due), contents, seed, args.limit)
    print(json.dumps({
        "ok": True, "scheduler": _ENGINE_NAME, "book": b.name,
        "today": today.isoformat(), "today_source": source,
        "counts": {"due": len(due), "new": len(new), "retired": retired,
                   "cards": len(cards), "reviews_replayed": replayed},
        "chapters_due": chapters_due(contents, today),
        "due": [{k: v for k, v in it.items() if not k.startswith("_")} for it in due],
        "new": new,
        "plan": {
            "seed": seed, "limit": args.limit, "planned": len(plan),
            "items": [{"seq": i + 1, "card": it["card"], "deck": it["deck"],
                       "type": it["type"], "stage": it["stage"]}
                      for i, it in enumerate(plan)],
            "note": ("Interleaved across chapters and item types. Present prompts only — "
                     "never name an item's chapter before it is graded."),
        },
        "dag_flags": dag_flags,
        "ledger_warnings": warnings,
        "notes": notes,
    }, indent=2))


def cmd_stats(args):
    root = Path(args.dir)
    today, source = resolve_today(args)
    b = find_book(root, args.book, required=True)[0]
    cards, history, contents, _, _, _, replayed, warnings, notes = replay_book(b, today)
    per = {}
    for cid, revs in history.items():
        ch = card_chapter(cid)
        if ch is None:
            continue
        agg = per.setdefault(ch, {"attempts": 0, "correct": 0, "rating_sum": 0,
                                  "brier_terms": [], "conf": {}})
        for r in revs:
            agg["attempts"] += 1
            agg["correct"] += 1 if r["correct"] else 0
            agg["rating_sum"] += RATINGS[r["rating"]]
            if r["confidence"] is not None:
                agg["brier_terms"].append((r["confidence"] / 100 - (1 if r["correct"] else 0)) ** 2)
                c = agg["conf"].setdefault(r["confidence"], {"n": 0, "correct": 0})
                c["n"] += 1
                c["correct"] += 1 if r["correct"] else 0
    chapters, blind = [], []
    all_ch = sorted(set(per) | set(contents))
    for ch in all_ch:
        agg = per.get(ch, {"attempts": 0, "correct": 0, "rating_sum": 0,
                           "brier_terms": [], "conf": {}})
        n = agg["attempts"]
        acc = round(agg["correct"] / n, 2) if n else None
        brier = round(sum(agg["brier_terms"]) / len(agg["brier_terms"]), 2) \
            if agg["brier_terms"] else None
        mean_conf = (sum(k * v["n"] for k, v in agg["conf"].items())
                     / sum(v["n"] for v in agg["conf"].values()) / 100) \
            if agg["conf"] else None
        row = {
            "chapter": ch,
            "status": contents.get(ch, {}).get("status"),
            "box": contents.get(ch, {}).get("box"),
            "chapter_due": contents.get(ch, {}).get("due"),
            "cards": sum(1 for c in cards.values() if c["chapter"] == ch and c["active"]),
            "retired": sum(1 for c in cards.values() if c["chapter"] == ch and not c["active"]),
            "attempts": n,
            "accuracy": acc,
            "mean_rating": round(agg["rating_sum"] / n, 1) if n else None,
            "brier": brier,
            "reliability": [{"claimed": k, "n": v["n"],
                             "actual": round(v["correct"] / v["n"], 2)}
                            for k, v in sorted(agg["conf"].items())],
            "flags": [],
        }
        why = []
        if n >= 10:
            if acc is not None and acc < 0.65:
                why.append("accuracy {} over {} attempts".format(acc, n))
            if brier is not None and brier > 0.20:
                why.append("Brier {}".format(brier))
            if mean_conf is not None and acc is not None and mean_conf - acc > 0.15:
                why.append("claims {}% but scores {}%".format(
                    round(mean_conf * 100), round(acc * 100)))
        if why:
            row["flags"].append("blind spot")
            blind.append({"chapter": ch, "why": "; ".join(why)})
        d = contents.get(ch, {}).get("due")
        if d and dt.date.fromisoformat(d) < today - dt.timedelta(days=14):
            row["flags"].append("chapter-tier overdue")
        chapters.append(row)
    total_n = sum(r["attempts"] for r in chapters)
    all_brier = [t for ch in per.values() for t in ch["brier_terms"]]
    print(json.dumps({
        "ok": True, "scheduler": _ENGINE_NAME, "book": b.name,
        "today": today.isoformat(), "today_source": source,
        "chapters": chapters,
        "overall": {
            "attempts": total_n,
            "accuracy": round(sum(r["correct"] for r in per.values()) / total_n, 2)
            if total_n else None,
            "brier": round(sum(all_brier) / len(all_brier), 2) if all_brier else None,
            "reviews_replayed": replayed,
        },
        "blind_spots": blind,
        "ledger_warnings": warnings,
        "notes": notes,
    }, indent=2))


def parse_chapter_spec(spec):
    chs = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, z = part.split("-", 1)
            chs.update(range(int(a), int(z) + 1))
        elif part:
            chs.add(int(part))
    return chs


BLOOM_LADDER = ["remember", "understand", "apply", "analyze", "evaluate_create"]
BLOOM_SHARE = {"remember": 0.20, "understand": 0.15, "apply": 0.30,
               "analyze": 0.20, "evaluate_create": 0.15}


def cmd_exam(args):
    root = Path(args.dir)
    today, source = resolve_today(args)
    b = find_book(root, args.book, required=True)[0]
    cards, history, contents, _, _, _, _, warnings, notes = replay_book(b, today)
    wanted = parse_chapter_spec(args.chapters) if args.chapters else None
    satisfied = {"recited", "skimmed", "skipped"}

    def eligible(ch):
        row = contents.get(ch, {})
        if row.get("status") != "recited":
            return False
        if wanted is not None and ch not in wanted:
            return False
        return all(contents.get(p, {}).get("status") in satisfied
                   for p in row.get("prereqs", []))

    fresh_cut = today - dt.timedelta(days=3)
    pool, excluded_fresh = [], 0
    for cid, card in sorted(cards.items()):
        if not card["active"] or not eligible(card["chapter"]):
            continue
        revs = history.get(cid, [])
        if any(r["ts"].date() > fresh_cut for r in revs):
            excluded_fresh += 1
            continue
        pool.append(card)
    if not pool:
        fail("No eligible cards for an exam.",
             "Eligible = active cards of recited chapters (prereqs recited/skimmed/skipped), "
             "not reviewed in the last 3 days. Recite more chapters, or widen --chapters.")

    # chapter weights: recent misses, low box, high Brier oversampled
    recent_cut = today - dt.timedelta(days=30)
    weight, why = {}, {}
    for ch in sorted({c["chapter"] for c in pool}):
        revs = [r for cid, rs in history.items() for r in rs if card_chapter(cid) == ch]
        recent = [r for r in revs if r["ts"].date() >= recent_cut]
        miss = (sum(1 for r in recent if not r["correct"]) / len(recent)) if recent else 0.0
        box = contents.get(ch, {}).get("box") or 6
        briers = [(r["confidence"] / 100 - (1 if r["correct"] else 0)) ** 2
                  for r in revs if r["confidence"] is not None]
        brier = sum(briers) / len(briers) if briers else 0.0
        weight[ch] = 1.0 + 1.5 * miss + 1.0 * max(0, 6 - box) / 6 \
            + 1.0 * min(1.0, 4 * max(0.0, brier - 0.10))
        why[ch] = "box {} · Brier {} · recent miss rate {}".format(
            box, round(brier, 2), round(miss, 2))

    n = min(args.n, len(pool))
    if n < args.n:
        notes.append("pool holds only {} eligible cards; exam shrunk to {}".format(
            len(pool), n))
    # Bloom targets by largest remainder
    raw = {t: BLOOM_SHARE[t] * n for t in BLOOM_LADDER}
    target = {t: int(raw[t]) for t in BLOOM_LADDER}
    for t in sorted(BLOOM_LADDER, key=lambda t: raw[t] - target[t], reverse=True):
        if sum(target.values()) >= n:
            break
        target[t] += 1

    def tier(card):
        blm = card["bloom"]
        return "evaluate_create" if blm in ("evaluate", "create") else blm

    rng = random.Random(seed_hex(b.name, today.isoformat(),
                                 args.chapters or "all", n))
    by_tier = {t: [c for c in pool if tier(c) == t] for t in BLOOM_LADDER}
    chosen = []
    for t in BLOOM_LADDER:
        want = target[t]
        idx_t = BLOOM_LADDER.index(t)
        lower = BLOOM_LADDER[idx_t - 1::-1] if idx_t > 0 else []
        src_order, seen = [], set()
        for src in [t] + lower + BLOOM_LADDER[idx_t + 1:]:
            if src not in seen:
                src_order.append(src)
                seen.add(src)
        borrowed = 0
        for src in src_order:
            while want > 0 and by_tier[src]:
                cands = by_tier[src]
                total = sum(weight[c["chapter"]] for c in cands)
                x = rng.random() * total
                acc = 0.0
                for i, c in enumerate(cands):
                    acc += weight[c["chapter"]]
                    if x <= acc:
                        chosen.append(cands.pop(i))
                        want -= 1
                        if src != t:
                            borrowed += 1
                        break
            if want == 0:
                break
        if borrowed:
            notes.append("bloom tier {}: borrowed {} from neighboring tiers".format(
                t, borrowed))
        if want > 0:
            notes.append("bloom tier {} short by {}".format(t, want))
    for c in chosen:
        c["_priority"] = 0.0
    order = interleave(chosen, contents, seed_hex(b.name, today.isoformat(), "order", n),
                       limit=len(chosen))
    existing = sorted((b / "exams").glob("exam-*.md")) if (b / "exams").is_dir() else []
    coverage = {}
    for it in order:
        coverage[it["chapter"]] = coverage.get(it["chapter"], 0) + 1
    mix = {}
    for it in order:
        mix[tier(it)] = mix.get(tier(it), 0) + 1
    print(json.dumps({
        "ok": True, "scheduler": _ENGINE_NAME, "book": b.name,
        "today": today.isoformat(), "today_source": source,
        "exam": {
            "suggested_name": "exam-{:02d}".format(len(existing) + 1),
            "chapters": sorted({it["chapter"] for it in order}),
            "n": len(order),
            "items": [{"seq": i + 1, "card": it["card"], "chapter": it["chapter"],
                       "type": it["type"], "bloom": it["bloom"], "stage": it["stage"],
                       "deck": it["deck"]}
                      for i, it in enumerate(order)],
            "bloom_mix": mix,
            "coverage": [{"chapter": ch, "items": k, "weight": round(weight[ch], 2),
                          "why": why[ch]} for ch, k in sorted(coverage.items())],
            "excluded_fresh": excluded_fresh,
            "note": ("Copy each item's prompt verbatim from its deck into exams/{}.md, in seq "
                     "order, without chapter labels (ASSESS.md).").format(
                "exam-{:02d}".format(len(existing) + 1)),
        },
        "ledger_warnings": warnings,
        "notes": notes,
    }, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, book_required=False):
        p.add_argument("dir", nargs="?", default=".")
        p.add_argument("--book", required=book_required, default=None)
        p.add_argument("--today", default=None, help="YYYY-MM-DD (for determinism)")
        p.add_argument("--scheduler", choices=["auto", "fsrs", "sm2"], default="auto")

    p = sub.add_parser("due", help="due cards + interleaved session plan")
    common(p)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(fn=cmd_due)

    p = sub.add_parser("stats", help="per-chapter accuracy, Brier, blind spots")
    common(p)
    p.set_defaults(fn=cmd_stats)

    p = sub.add_parser("exam", help="cumulative exam spec")
    common(p, book_required=True)
    p.add_argument("--chapters", default=None, help="e.g. 1-8 or 1,3,5-7")
    p.add_argument("--n", type=int, default=20)
    p.set_defaults(fn=cmd_exam)

    args = ap.parse_args()
    resolved = Path(args.dir).resolve()
    if resolved == SKILL_DIR or SKILL_DIR in resolved.parents:
        fail("Refusing to operate inside the installed skill directory.",
             "Run from the study workspace (the directory the skill was invoked in).")
    global _ENGINE, _ENGINE_NAME
    if args.scheduler in ("auto", "fsrs"):
        _probe_fsrs()
        if args.scheduler == "fsrs" and _ENGINE != "fsrs":
            fail("FSRS was requested but the fsrs package is not usable here.",
                 "Install it (`python3 -m pip install --user fsrs` or run via uv), "
                 "or use --scheduler auto to fall back to SM-2.")
    if args.scheduler == "sm2":
        _ENGINE, _ENGINE_NAME = "sm2", "sm2-forced"
    args.fn(args)


if __name__ == "__main__":
    main()
