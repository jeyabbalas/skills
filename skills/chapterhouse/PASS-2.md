Pass 2 is the analytical read — the long middle where the book actually gets learned, one chapter per session through a fixed loop: survey the chapter, write prequestions, read it together into a Cornell note, recite it closed-book, and hand it to the revision ladder. The loop's last two steps are the ones learning science actually vouches for; the loop exists so they cannot be skipped. Two kinds of work share every session: **planned units** (the next chapter per BOOK.md's `next:` pointer) and **reactive work** (whatever passage the student brings up). Reactive work always wins the floor.

Table of contents

- [The unit, and what precedes it](#the-unit-and-what-precedes-it)
- [The loop](#the-loop)
- [Survey](#survey)
- [Question](#question)
- [Read together](#read-together)
- [Enrichment](#enrichment)
- [Recite, closed book](#recite-closed-book)
- [Review](#review)
- [The chapter page](#the-chapter-page)
- [Ending pass 2](#ending-pass-2)

## The unit, and what precedes it

The unit is one chapter through the whole loop — or one section of a chapter CONTENTS.md marks `diff 3`, in which case the recite covers the sections read so far and the chapter stays `reading` until its last section's recite passes. Before new material, two things ride on top of the unit (both from REVISE.md, both short): the **warm-up** over whatever the due check returned, and the **delayed judgment of learning** — one question about the *previous* chapter's confidence, asked now because a day-later estimate is honest where a same-day one flatters.

## The loop

Survey → Question → Read → Recite → Review, in order, one chapter. The chapter is not done without step 4: **no recite, no `recited`** (SKILL.md's gotcha). A session that runs out of time before the recite logs `next: recite ch N` and leaves status `reading`.

## Survey

Two minutes, from the chapter's page range (CONTENTS.md): headings, figures, summary boxes, and the exercise set — the shape of what's coming, and which exercises look worth working. Check CONTENTS.md's `## Errata` for this chapter *now*, before reading around a known error.

## Question

Write 4–8 prequestions into the chapter note's `## Cues` (NOTES-FORMAT.md) **before reading**: backlog questions that touch this chapter first (survey page), then questions generated from the headings ("§3.2 'The limits of histograms' — what limits?"). The student may add, veto, or sharpen any of them. Prequestions are cheap and they change how the read attends — write them even when the student is impatient to start.

## Read together

The conversational read, in page-ranged chunks, building the note as you go:

1. **Locate.** Take the next section's page range from CONTENTS.md; read it (natively page-ranged; `extract/` when the harness can't — LAYOUT.md).
2. **Converse.** Walk it in STUDENT.md's register. Quote verbatim where exactness matters; ◆ anything beyond the book, in chat too.
3. **Capture into the note** (NOTES-FORMAT.md): Terms as the author defines them; the section's Propositions, anchored; the Argument rebuilt in the student's own notation — ask them to say it back and write *their* version; at least one worked example transcribed verbatim and annotated line by line.
4. **The concept-reflex.** When an idea will clearly outlive this book, offer one line — "start a concept note for *p-value*?" — and write it on yes (NOTES-FORMAT.md).
5. **Item-writing reflex.** When something was hard-won in conversation, draft its card now (ASSESS.md owns item shapes and the per-chapter mix; DECK-FORMAT.md owns storage) — read the card back, add on yes.
6. Return to the planned section, or follow the student. A question is not a commission.

Exercises the book poses are pass-2 work too: work the ones the plan or the student picked — hand-worked or programming, protocols in ASSESS.md — as they arrive in the reading, not as a batch at the end.

## Enrichment

Up to ~3 external resources per chapter, offered not imposed, into the note's `## Links` as ◆ `Source` cards: a lecture that teaches this chapter better than the book does, an interactive visualization, canonical documentation, an alternative explanation for a section that didn't land. Authoritative links only — a resource you wouldn't cite doesn't earn a card. Never a substitute for the book's own text, and never book content itself from elsewhere.

## Recite, closed book

The chapter's exit exam, mandatory, run to ASSESS.md's recite protocol: book and notes closed; you ask from the Cues plus the chapter's new cards; confidence before every answer; grade against rubrics; every graded exchange appends its ledger line (DECK-FORMAT.md); misses become cards and mark their cue `✗`.

**Pass/fail is the student's call, guided**: propose pass when the cues' misses are minor and the core held (a number like "most cues Good or better" helps; the rubric record is what makes the call honest). On a pass → Review. On a fail, no ceremony: the retry is the `next:` pointer, targeted at what missed.

## Review

The chapter's close, in order:

1. **Ladder entry** — the chapter takes box 1 and its due date per REVISE.md; write the CONTENTS.md columns.
2. **Teach-back** — the student writes it, closed-book, ≤200 words, into the note; you critique per ASSESS.md and mint cards from the flags. Never write it for them.
3. **Summary** — 3–5 sentences into the note's `## Summary`, drafted by either of you, approved by them.
4. **Bookkeeping** — status `recited`, SHELF.md progress, the chapter page rendered, the closing checklist.

## The chapter page

`notes/chNN-<slug>.md` → `.html` via `page.html` (spec in ARTIFACTS.md) — regenerated whenever the note changes, which is every session that touches the chapter. The deck's quiz page (`decks/chNN.html`) regenerates whenever cards were added or retired.

## Ending pass 2

When every planned chapter is `recited` (or licensed `skimmed`/`skipped`), say so, and ask the gate question: **worth a pass 3 — critique, re-creation, the cumulative exam?** Record the decision (BOOK.md status + log line). The question backlog is the gate-check: read it aloud — which questions can the student now answer cold, and which does the book leave open? Unanswered ones either point at pass 3 work or at the book's limits; both are worth saying.
