Two state surfaces share this file: **decks** (`books/<slug>/decks/chNN.md` — the card banks, one per chapter, rendered to quiz pages) and the **ledger** (`books/<slug>/reviews.jsonl` — the append-only record of every graded exchange). Cards are content; the ledger is history; the schedule is neither — `revise.py` derives it by replaying the ledger, so there is no scheduler state file anywhere.

Table of contents

- [Card template](#card-template)
- [Card rules](#card-rules)
- [Example cards](#example-cards)
- [The ledger](#the-ledger)
- [Ledger rules](#ledger-rules)

## Card template

```md
### {chNN-cNNN} · {type} [· stage: {worked|completion|full}]
born: {YYYY-MM-DD}
anchor: ch.{N} · §{N.M} · p.{P} · "{six verbatim words}"
links: {chNN-cNNN}, {concepts/<slug>.md}
status: active

**Prompt.** {the question, exactly as it will be read aloud}

**Answer.** {the full expected answer}

**Rubric.** Good requires: {2–4 clauses}. Easy: {what upgrades}. Hard: {what downgrades}.
```

`revise.py` parses only the `###` header and the meta lines directly under it; the header grammar is frozen: `### chNN-cNNN · type` with an optional ` · stage: worked|completion|full`, `type` ∈ `term | concept | apply | analyze | evaluate | create`.

## Card rules

- **`type` doubles as the Bloom level**: term→remember, concept→understand, the other four are themselves. Add a `bloom: {level}` meta line only to override (rare). What each type looks like, and which are legal for the book's genre, is ASSESS.md's territory.
- **`stage` appears only on faded items** (worked-example ladder, ASSESS.md) and is edited in place on promotion or demotion — stage is card *content* (what to present), not schedule. Keep the transition visible: `stage: completion (from worked · 2026-09-02)`.
- **The anchor** is the same grep-recoverable discipline as everywhere: chapter, section, page, six verbatim words.
- **The rubric is the grading contract.** It states what Good requires so any future session — and the student — grades the same answer the same way.
- **Retiring**: set `status: retired — {why}` and leave the block in place. Retired cards leave `due`/plans/exams but their ledger lines remain and still count in `stats` — history measures the student, not the deck. Un-retiring is `status: active` again; replay resumes the schedule exactly where the history left it.
- **Cards in id order; ids never reused** (numbering in LAYOUT.md). Prompt edits that change what the card tests deserve a new card and a retirement, not an edit — the old history graded a different question.

## Example cards

```md
### ch03-c004 · term
born: 2026-08-19
anchor: ch.3 · §3.1 · p.28 · "the PMF maps each value to"
links: concepts/probability-mass-function.md
status: active

**Prompt.** What is a probability mass function, and what must its values satisfy?

**Answer.** A function mapping each possible value of a discrete variable to its
probability; values are non-negative and sum to 1 over the support.

**Rubric.** Good requires: the mapping idea + both constraints. Easy: adds the
histogram→PMF normalization connection unprompted. Hard: mapping right, constraints vague.
```

```md
### ch07-c012 · apply · stage: completion
born: 2026-08-21
anchor: ch.7 · §7.4 · p.214 · "the maximum likelihood estimate is obtained"
links: concepts/maximum-likelihood.md
status: active

**Prompt.** Derive the MLE of \(\lambda\) for an i.i.d. Poisson sample. At completion
stage: show the log-likelihood setup; the differentiation and solve steps are blanked
for the student to fill.

**Answer.** \(\ell(\lambda)=\sum x_i \log\lambda - n\lambda - \sum\log x_i!\);
\(\partial\ell/\partial\lambda = \sum x_i/\lambda - n = 0\); \(\hat\lambda = \bar{x}\);
second derivative negative confirms a maximum.

**Rubric.** Good requires: correct derivative, correct solve, and saying why the critical
point is a maximum. Hard: algebra slip with the method sound. Again: cannot set up the score equation.
```

```md
### ch02-c007 · apply
born: 2026-08-20
anchor: ch.2 · §2.5 · p.22 · "write a function that takes a"
links: —
status: active

**Prompt.** Work practice/ch02/exercise_01.py (spec in its docstring).
Run: `python3 practice/ch02/test_exercise_01.py`.

**Answer.** Pinned by the asserts in practice/ch02/test_exercise_01.py; no prose answer.

**Rubric.** Good requires: all tests pass with the student's own code (rating map in
ASSESS.md). Any hint from me is ◆ and caps at Hard.
```

## The ledger

One JSON object per line, appended immediately after each graded exchange — composed in chat first, so the student sees exactly what is recorded:

```json
{"ts": "2026-08-23T14:05:11Z", "book": "downey2014-think-stats", "card": "ch07-c012", "mode": "revise", "confidence": 75, "correct": true, "rating": "good", "override": null, "hint_used": false, "note": ""}
```

Fields: `ts` ISO 8601 UTC, the grading moment, never earlier than the previous line's; `book` the slug (kept so a moved ledger stays self-describing); `card` an id existing in some deck; `mode` ∈ `recite` (chapter-close first exposure) · `revise` (spaced session) · `exam` · `practice`; `confidence` ∈ 25/50/75/90/99 or `null` where the protocol skips it (ASSESS.md); `correct` rubric-level boolean, final; `rating` ∈ `again|hard|good|easy`, final; `override` `null` or `{"from_rating": …, "from_correct": …, "why": "≤ six words"}` preserving your original verdict when the student overrode it; `hint_used` true when any ◆ hint preceded the answer; optional `elapsed_s` (only when honestly known) and one-line `note`.

## Ledger rules

- **Append-only, forever.** No line is ever edited or deleted — a retired card's lines included. A wrong old grade is never repaired retroactively; the next review self-corrects the schedule. Corrections of any kind are new lines.
- **You append; scripts only read.** `revise.py` has no write path — that is what makes append-only structural. One graded exchange, one line, appended before the next item; a re-ask later the same session is a second exchange and a second line.
- **All four modes feed the scheduler** — a graded retrieval is a graded retrieval. The top-level `rating`/`correct` are post-override and final; the `override` object is the record of the disagreement (disagreements are signal — `stats` reads them).
- **The ledger is validated on every replay.** `revise.py` flags malformed lines, unknown card ids, out-of-enum values, and non-monotonic timestamps as `ledger_warnings` with line numbers; the closing checklist requires a clean run.
