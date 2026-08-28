`books/<slug>/CONTENTS.md` is the book's chapter manifest — the numbering authority everywhere (anchors, note filenames, deck names, page links all use its chapter numbers) and the hand-legible face of the study's state: what each chapter's status is, where it sits on the revision ladder, and how well the student actually knows it. `revise.py` parses the chapter table by its header names; keep them exactly as below.

Table of contents

- [Template](#template)
- [Header fields](#header-fields)
- [Chapter table columns](#chapter-table-columns)
- [Errata](#errata)
- [Rules](#rules)

## Template

```md
# Contents — {book title}
genre: practical — teaches procedures the student is meant to perform (preface, p. xi)
pages: 226 · source: book.pdf · ingested: {YYYY-MM-DD}

## Chapters
| ch | title | pages | prereqs | diff | exx | status | box | due | conf | brier |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Exploratory data analysis](notes/ch01-exploratory.md) | 1–14 | — | 1 | 4 | recited | 2 | 2026-08-29 | 75 | 0.11 |
| 2 | [Distributions](notes/ch02-distributions.md) | 15–26 | 1 | 1 | 6 | reading | — | — | — | — |
| 3 | Probability mass functions | 27–36 | 2 | 2 | 5 | unread | — | — | — | — |

## Errata
source: {errata page URL · checked YYYY-MM-DD} — or "none found ({date}, searched: {where})"
- ch 3 · p. 34 · {one-line description of the correction} ({link})
```

## Header fields

- **`genre`** — `theoretical` (argues what is true) · `practical` (teaches what to do) · `expository` (surveys a territory), with a one-line anchored rationale. Classification criteria live in PASS-1.md; the genre gates which item types are legal (ASSESS.md) and which pass-3 re-creation track applies (PASS-3.md).
- **`pages` · `source` · `ingested`** — total pages (or spine items for an EPUB), which file, and when ingestion ran. Multi-file works add one clause per file naming its chapters.

## Chapter table columns

- **`ch`** — the book's own chapter number. This table is the numbering authority; correct it here and everything downstream follows.
- **`title`** — linked to the chapter note once one exists; bare text before that.
- **`pages`** — the chapter's PDF page range (always PDF pages, never the printed numbers — the ingest output labels which it gave you). EPUBs put the spine/file run here (`spine 3–5`).
- **`prereqs`** — comma-separated chapter numbers this chapter leans on, or `—`. Linear order is implied; list only real dependencies. This column is the prerequisite-DAG authority: the map page and `revise.py`'s interleaving both read it. Rationale for a surprising edge belongs on the survey page as ◆, not here.
- **`diff`** — anticipated difficulty for *this* student, 1–3, judged at survey time. `diff 3` is also the cue to propose section pacing (PASS-2.md).
- **`exx`** — the book's own exercise count for the chapter.
- **`status`** — `unread` · `reading` (started, recite not passed) · `recited` (closed-book recite passed — the only route to this value is a ledger event) · `skimmed` · `skipped` (reading-plan licenses executed; no recite owed). While a chapter is section-paced or scaffolded, `reading` may carry a short parenthetical gist — `reading (§1.2 of 4)`, `reading (opener + §1.1)` — an index of the note's `## Sections`, never an authority, dropped when the status moves. Only `reading` may be annotated: the other four stay bare, exactly as spelled — `revise.py` matches them as exact strings.
- **`box`** — 1–6, the chapter's rung on the Leitner ladder, or `—` before the first passing recite. Gap table and movement rules live in REVISE.md.
- **`due`** — the chapter's next cumulative-recite date, from the ladder.
- **`conf`** — the student's most recent whole-chapter confidence (25/50/75/90/99) — the pre-recite estimate, superseded by each delayed judgment of learning (REVISE.md).
- **`brier`** — the chapter's running Brier score from `revise.py stats`, two decimals. Lower is better calibrated.

## Errata

Filled from the intake errata lookup (PASS-1.md) and extended whenever a new erratum surfaces. One line per erratum that touches a chapter the plan includes: chapter, page, what changes, link. Check this section before reading a chapter (PASS-2.md) — a corrected passage is cited with its erratum link (SKILL.md's Accuracy).

## Rules

- **The table is a projection, not an authority, for its scheduling columns.** `box`, `due`, `conf`, and `brier` restate what the ledger and `revise.py` derive — write them at the same moment you append the matching ledger line or move the ladder, and reconcile against `revise.py stats` at close. When the two disagree, the ledger wins and the table gets corrected.
- **`status` and the plan columns are this file's own.** Statuses move per the playbooks (`recited` only after a passing closed-book recite; `skimmed`/`skipped` only per the reading plan's licenses, decided by the student).
- **Hand edits are first-class.** Ingestion output is a seed; the student confirms chapter ranges before this file is written, and later corrections are made here directly — every other file follows this one.
- **Rows edit in place.** History lives in BOOK.md's session log and the ledger, never here.
- **Sections never get rows here.** Within-chapter pacing lives in the chapter note's `## Sections` (NOTES-FORMAT.md); this file stays one table, one row per chapter — `revise.py` treats every table row in this file whose first cell is a number as a chapter row, so a second table would corrupt the replay.
