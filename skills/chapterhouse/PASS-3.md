Pass 3 is synthesis and mastery: the whole book again, mostly closed. Four unit types, one per session, in any order the student picks — critique customarily first, because Adler's rule binds: you may only judge what you can state, so only `recited` chapters are in scope for any of it. The pass ends when the student calls the units served — and the book then enters `maintenance`, because a studied book outlives its last pass: the cards keep cycling until the student closes it.

Table of contents

- [The four units](#the-four-units)
- [Adlerian critique](#adlerian-critique)
- [Critique template](#critique-template)
- [Re-creation, closed book](#re-creation-closed-book)
- [The cumulative exam](#the-cumulative-exam)
- [Concept consolidation](#concept-consolidation)
- [Ending pass 3](#ending-pass-3)

## The four units

- **A critique sweep** — the book judged on Adler's four counts, into `critique.md`.
- **One re-creation target** — a core result rebuilt from memory, genre-appropriate, under `practice/p3-<slug>/`.
- **The cumulative exam** — interleaved, chapter-blind, over everything recited.
- **A consolidation batch** — 3–5 concept notes written or extended in `concepts/`.

Each is one session (SKILL.md's budget); repeat units as the student likes (a second exam weeks later is excellent practice, not repetition).

## Adlerian critique

"I understand" comes before "I disagree" — open each finding by stating the author's position well enough that the student would sign it. Then judge, on exactly four counts:

- **uninformed** — the author lacks knowledge that bears on the argument (say what, and what it changes);
- **misinformed** — the author asserts something not so (anchor the assertion; bring your evidence, ◆-linked — an erratum entry is the cleanest kind);
- **illogical** — the conclusion doesn't follow (name the step that breaks);
- **incomplete** — the account stops short of what the book's own goal requires (this is the mildest count, and the only one that can stand alone without disagreement).

Harvest the raw material before judging fresh: the notes' open `My questions`, `critique`-flavored ◆ asides in chapter notes, backlog questions the book never answered (when one exists). A finding that dissolves on re-reading is recorded as dissolved, not deleted — how the judgment evolved is signal.

## Critique template

`critique.md` → `critique.html` via `page.html` (ARTIFACTS.md):

```md
# {Title} — critique

## Where the book earns agreement
{2–5 lines: the claims the student now positively endorses, having recited them}

## Findings
### F1 · {count} · ch.{N} · §{…} · p.{…}
**The author's position**: {stated fairly, anchored}
**The finding**: {the case, ≤5 lines; evidence ◆-linked}
**Steelman**: {the strongest version of the author's defense}
**Status**: open | dissolved — {what dissolved it}
```

## Re-creation, closed book

Keshav's pass-3 test carried to books: mastery is re-creating the core results without the book open. Pick targets from CONTENTS.md and the decks — the weakest boxes and blind-spot chapters first (`revise.py stats`), because re-creating what's already solid flatters. One target per session, worked under `practice/p3-<slug>/`, book closed until the diff step. The genre picks the track:

- **`practical` (programming, statistics, ML)** — reimplement a core algorithm or analysis from memory, then reproduce one of the book's own worked results. You write the acceptance tests *before* they start (the book open to you for pinning expected values is fine — for you, not them); the student writes the code; the programming protocol and rating map are ASSESS.md's.
- **`theoretical` (mathematics, theory)** — re-derive a main theorem from its assumptions. Open a derivation file in `practice/p3-<slug>/` with the target stated verbatim and an **assumptions ledger** (`# | assumption | stated? | verdict`) built first; the student derives, you referee — offer the smallest next question, never the step. Every leap the book makes is flagged: closed here, or recorded open.
- **`expository` (biology, surveys)** — draw the pathway, mechanism, or concept map from memory: typed, or photographed from paper (you read the image). Then open the book and **diff** — every missing node, wrong edge, or inverted causal order is anchored to the page that corrects it.

Every re-creation ends the same way: the diff against the book, each divergence minted as a card (ASSESS.md), one summary ledger line for the session's graded work, and the target's outcome in the log line.

## The cumulative exam

EXECUTE `revise.py exam` (contract in LAYOUT.md) — the spec oversamples weak chapters and high-Brier territory and enforces a Bloom mix. Copy each item's prompt verbatim from its deck into `exams/exam-NN.md` in the spec's order, **without chapter labels** — the interleaving is the point: identifying *which tool applies* is the skill the blocked-by-chapter reading never tested. Sit it to ASSESS.md's recite protocol (confidence and all; `mode: "exam"` on every ledger line), grade it, then debrief: per-chapter results against CONTENTS.md's `conf`/`brier` columns, updated. The exam page (`exams/exam-NN.md` → `.html`, deck-page markup per ARTIFACTS.md) prints as questions-only by default — a re-sittable paper exam for free.

## Concept consolidation

The syntopical unit: 3–5 concepts per sitting, into `concepts/` per NOTES-FORMAT.md. Harvest candidates from the chapter notes' Terms tables and the cards' `links:` — the ideas that recurred. For each: gather the book's passages verbatim, state the terminology mapping, and have the student write `My resolution`. With one book on the shelf this mostly *plants* notes; the payoff compounds when the second book touches the same concepts and the Issues sections come alive. Regenerate the concepts index page after the batch.

## Ending pass 3

When the student calls the four units served (all four is typical, not required), present the whole: the critique, the re-creation outcomes, the exam debrief, the backlog read out one final time — answered, open, out of scope (a declined backlog reads out the book's own claims instead: the survey's one-sentence unity, or a capstone list when the book offers one, held against what the student can now state). Then the last gate: **maintenance, or closed?** `maintenance` keeps the cards cycling — sessions in this workspace keep offering the book's due reviews indefinitely. `closed` retires it from revision; its log line ends `next: — (closed)`. Either way, status + SHELF row + log line, and the hub regenerated one last time.
