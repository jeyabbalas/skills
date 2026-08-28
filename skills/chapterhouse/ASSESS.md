Every graded moment in the skill runs through this file: what items look like, how a recite or exam is conducted, how hand-worked and programming problems are checked, how a teach-back is critiqued, and how derivation cards fade. Two rules bind everywhere. **The grade is the student's** — you propose, they may override, both get recorded (DECK-FORMAT.md). **Gaps are findings, not failures** — a miss is the system working: it just found what to practice.

Table of contents

- [Item types and the chapter mix](#item-types-and-the-chapter-mix)
- [Writing good items](#writing-good-items)
- [The recite protocol](#the-recite-protocol)
- [Hand-worked problems](#hand-worked-problems)
- [Programming problems](#programming-problems)
- [The teach-back critique](#the-teach-back-critique)
- [The worked-example fade](#the-worked-example-fade)

## Item types and the chapter mix

Six types, doubling as Bloom levels (storage grammar in DECK-FORMAT.md), written at these rough per-chapter rates:

| type | asks the student to… | per chapter |
|---|---|---|
| `term` | produce a definition, notation, name | 5–10 |
| `concept` | explain in their own words; say what something is *not* | 3–5 |
| `apply` | work a problem: plug-in numeric, small program, procedure | 3–5 |
| `analyze` | trace a causal chain; find which assumption breaks; compare methods | 2–4 |
| `evaluate` | judge fitness: "is this test appropriate here, and why?" | 1–3 |
| `create` | derive or design something the book didn't hand over | 0–2 |

**Genre gates the upper types** (genre from CONTENTS.md): `theoretical` books lean on `analyze`/`create` derivation items; `practical` books lean on `apply` (including programming); `expository` books lean on `analyze` mechanism chains — and a derivation item against a book that proves nothing, or a mechanism chain against a book that teaches procedures, is a wrong item, not a hard one. Every chapter still gets its `term`/`concept` floor.

## Writing good items

- **One retrieval per card.** A prompt hiding three questions grades none of them well.
- **The rubric is written with the card**, not at grading time — it is the contract that makes two sessions grade alike.
- **Anchor every card** (DECK-FORMAT.md) so a miss leads straight back to the page.
- **Prefer the book's own exercises** for `apply` — the author wrote better problems than either of you will improvise; a card can simply point at one ("Work exercise 3.2"; answer = the book's, or pinned by a test).
- **Elaboration prompts ride along**: on `concept`/`analyze` cards, a second-beat follow-up — "why would that be true?", "how does it connect to {earlier chapter's idea}?" — deepens the retrieval without becoming its own card.
- **Cards are minted at friction**: a recite miss, a hard-won exchange, a teach-back flag, a re-creation divergence. Read the draft back; add on yes.

## The recite protocol

For pass-2 recites — chapter or section (PASS-2.md) — revision blocks (REVISE.md), and exams (PASS-3.md) alike:

1. **Declare closed-book.** *"Book closed, notes closed? Say ready."* Don't start before it. If they want open-book, run it — every line records `note: "open-book"` and ratings cap at Good.
2. **One item at a time**, prompt only — never the card id, never the chapter ("this one's from chapter 5" un-interleaves the session; the plan withholds chapters on purpose).
3. **Confidence first**, every free-response item: *"Before you answer — how sure are you: 25, 50, 75, 90, or 99?"*
4. **They answer free-form.** No interrupting, no leading. A hint on request is fine — it is ◆, sets `hint_used`, and caps the rating at Hard.
5. **Grade against the rubric, then reveal.** Verdict first in one line, naming the rubric clause hit or missed; then the full answer; then the anchor.
6. **Offer the override.** *"I'd score that {rating}. The grade is yours — override it and I'll record both."*
7. **Append the ledger line now** (DECK-FORMAT.md), shown in chat, before the next item.
8. **Misses re-queue** at session end for one ungraded-then-regraded second attempt — its own ledger line.
9. **A miss that exposes a *new* gap mints a card** — the missed card already covers the asked one.

Ratings: `again` — couldn't produce it; `hard` — produced with a hint or major gaps; `good` — correct, effortful; `easy` — immediate and complete. `correct` is the rubric-level boolean and can disagree with the rating's difficulty shading; both are final post-override.

**Rehearsal is not grading.** A guide's self-test and foundations checks (SCAFFOLD.md) run open-voice and ungraded — no confidence ritual, no ledger line. Only the four ledger modes (`recite | revise | exam | practice`) are graded events.

## Hand-worked problems

For math and statistics `apply`/`create` items worked on paper:

1. Confidence first (step 3 above), then: *"Work it on paper — no book. When you're done, either type the final answer plus your key steps, or photograph the page and give me the file path; I'll read your handwriting."*
2. From a photo, **transcribe their result back before grading** — *"I read your final answer as \(\hat\lambda=\bar x\) — right?"* — so a misread never becomes a misgrade.
3. Check step by step and **name the first broken step**, at that altitude: *"Sound through line 3; the sign flips when you differentiate the exponent."* Never dump the full solution unbidden — a dumped solution is ◆ and caps at Hard.
4. Grade: right result, sound steps → Good (Easy when clean and, by their own report, quick). Right result, broken reasoning → Hard, say which step. Wrong result → Again, point at the first break; it re-queues.

## Programming problems

`practice/chNN/` holds one pair per exercise — **you write both files; the student writes the solution**:

- `exercise_NN.py` — a stub: docstring spec (contract, an example, the edge cases), the signature, `raise NotImplementedError`.
- `test_exercise_NN.py` — plain asserts in `test_*` functions plus a `__main__` runner that reports PASS/FAIL per test and exits non-zero on failure — runnable by both bare `python3` and pytest, no framework dependency.

Run contract: from the exercise's directory, `python3 test_exercise_NN.py`; you run it, or the student pastes the output. Rating map: all tests pass on the first run → Good (Easy only if the student calls it trivial); passing within the sitting after ≤2 fix rounds → Good; more rounds → Hard; any ◆ unblock used → Hard at best, `hint_used: true`; abandoned, or you had to show working code → Again. **The unblock rule**: after two failed attempts you may offer one targeted unblock — the smallest failing sub-case, or a single conceptual pointer — never the code, always ◆. Ledger lines carry `mode: "practice"`, `confidence: null`.

## The teach-back critique

The student's teach-back (NOTES-FORMAT.md) is theirs; you quote it and ask. Four flags, each minting a card aimed at the exact gap:

- **Smuggled term** — used but never grounded in their own words: *"You said 'haploinsufficiency' — one sentence, what is it?"* → `term` card.
- **Assertion without mechanism** — "X causes Y" with no how: *"By what steps?"* → `analyze` chain card.
- **Wrong causal order** — quote their order verbatim, ask what happens first → `analyze` card.
- **Scope creep** — a claim the book doesn't make: say so plainly ("the book does not say this"); a note, not necessarily a card.

Close like a sitting: what landed, where it wobbled, the student's gaps kept distinct from the book's. The teach-back itself writes no ledger line — the minted cards get graded later, and that is its score.

## The worked-example fade

Derivation-style cards (`apply`/`create` on math and statistics) carry a `stage` and climb a ladder — novices learn more from studying solutions than solving, and experts the reverse, so the card moves with the student:

- **`worked`** — you present the complete worked solution; the student self-explains each step (*"why is this step allowed?"*). The self-explanations are what gets graded.
- **`completion`** — the solution with its 2–3 *load-bearing* steps blanked (the "why" steps, never the arithmetic); the student fills them.
- **`full`** — the prompt alone; the hand-worked protocol applies.

**Promotion**: Good or Easy at the current stage on two consecutive encounters → edit `stage` up one (DECK-FORMAT.md keeps the transition visible). **Demotion**: Again at `full` → `completion`; Again twice running → `worked`. **The expertise-reversal guard**: when minting a new derivation card, check `revise.py stats` for the card's prerequisite chapters — accuracy ≥ 0.85 and mean rating ≥ 3.0 there means start at `completion`, not `worked`; a competent student handed full solutions is studying redundancy, not the skill.
