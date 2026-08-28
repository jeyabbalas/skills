Guides are the scaffold-mode artifacts (SCAFFOLD.md): agent-authored teaching that equips the student to read a too-difficult book alone. Two file kinds live in `books/<slug>/guides/`. Ownership is the inverse of the note's: NOTES-FORMAT.md's rules protect the *student's* sections, and a guide is the one artifact where your voice dominates by design — which is exactly why the note's `## Argument` never copies it.

Table of contents

- [Foundations file](#foundations-file)
- [Section guide](#section-guide)
- [Guide rules](#guide-rules)

## Foundations file

`guides/chNN-foundations.md` — the background chapter N silently assumes, diagnosed per section, filed per chapter. Created with the chapter's first guide, appended as later sections are equipped; F-numbers append, never renumber. Later chapters link earlier F-items rather than re-teach them.

```md
# Ch 1 — Foundations
book: {slug} · for: ch 1 · note: ../notes/ch01-<slug>.md

> ◆ **Beyond the book** — everything in this file is mine, not the author's: the
> background the chapter assumes without teaching. Skip any item you already own —
> each check tells you. The book's own words appear only in quotation marks with pages.

### F1 — {title}
{tight teaching, 10–40 lines — formalism, examples, and notation in STUDENT.md's register}
*Check:* {one question answerable on paper}
*Answer:* {compact}

### If a foundation is missing
- ◆ **Source** — [{title}]({url}) — for F3–F4: {exactly which unit of it, and why it earns the link}
```

## Section guide

`guides/chNN-sMM-<slug>.md`, one per section (`sMM` grammar in LAYOUT.md); a book without usable sections writes one `guides/chNN-<slug>.md` per chapter instead, same shape.

```md
# §1.2 — {section title}: a guide
book: {slug} · for: §1.2 (pp. 11–19) · foundations: ch01-foundations.md · note: ../notes/ch01-<slug>.md

> ◆ **Beyond the book** — this whole guide is mine, not the author's; it prepares your
> own read of §1.2, it does not replace it. The book's own words appear only in
> quotation marks with page anchors.

## How to use this guide
{the contract, ~4 lines: foundations first, skipping what you own; the walkthrough beside
the book, not instead of it; the self-test out loud; then the book's own pages; bring
whatever breaks to the next session}

## Foundations
Before S1, own: F2, F4, F7 → [ch01-foundations.md](ch01-foundations.md). {items this
section forced get written there and pointed at from here — never taught twice}

## The section, step by step
### S1 — {what this step is, in plain words}
{the four-beat rhythm: what it says → the book's own words, verbatim + anchored → a
picture (◆ Diagram when it lives only in the render) → a check you can do in your head}

## Self-test
{5–8 oral questions — the recite's questions in easier clothing — then an *Answers:* key}

## Problem path
| problem | what it drills | step |
{optional — the section's exercise set curated, each row pointing back at a step}
```

## Guide rules

- **The four-beat rhythm is the walkthrough's contract**: *what it says* (your plain words) → *the book's own words* (verbatim, anchored — the accuracy law binds inside guides too) → *a picture* → *a check*. Steps `S1`… append, never renumber — the note's cues point at them (`· guide S4`, NOTES-FORMAT.md).
- **The page-level ◆ banner replaces per-item marks.** A guide is beyond the book by nature; marking every paragraph would bury the mark. Three kinds still mark individually because they carry distinct semantics: `Critique` (a real disagreement with the book), `Source` (an external link), `Diagram` (the bridge to a render-only widget).
- **Early vocabulary is allowed, flagged.** Naming what the book deliberately withholds ("the book is showing you the picture before the word *span*") is the guide doing its job — always saying that the book hasn't said it yet.
- **Budgets**: up to ~6 ◆ `Source` links per guide file — the escape hatches live here; the chapter note keeps its own ~3 (PASS-2.md). Soft size cap ~250–300 lines per section guide; foundations amortize in the chapter file — link, don't re-teach.
- **The self-test and the foundations checks are rehearsal, not grading** — no ledger lines (ASSESS.md); the graded exit stays the recite.
- **Widgets** (~1–2 per section guide, preference-gated): each lives only in the guide's render, announced in this markdown by a ◆ `Diagram` blockquote that describes the demonstration well enough to survive printing and links `chNN-sMM-<slug>.html#wN`. Markup in ARTIFACTS.md; a standalone sandbox is a lab (`labs/`, ARTIFACTS.md), not a widget.
- **Render** via `templates/guide.html` (ARTIFACTS.md): badge `Pass 2`, breadcrumb `Shelf › {book} › Guide — §N.M`, and the inverted colophon — on a guide page, unmarked content is *yours*, not the book's.
