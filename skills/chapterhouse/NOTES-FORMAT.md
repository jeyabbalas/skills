Two note kinds share this file: the **chapter note** (`books/<slug>/notes/chNN-<slug>.md`, Cornell-shaped, one per studied chapter, rendered to a page) and the **concept note** (`concepts/<slug>.md` at the workspace root, atomic and cross-book, also rendered). Chapter notes hold what *this book* says and how the study went; concept notes hold what is true *independent of any one book*. When a fact would survive the book, it belongs in a concept note, linked from the chapter note — never duplicated into both.

Table of contents

- [Chapter note template](#chapter-note-template)
- [Chapter note rules](#chapter-note-rules)
- [Who writes which section](#who-writes-which-section)
- [Concept note template](#concept-note-template)
- [Concept note rules](#concept-note-rules)
- [Searching](#searching)

## Chapter note template

```md
# Ch 3 — Probability mass functions
book: downey2014-think-stats · pages: 27–36 · deck: ../decks/ch03.md

## Cues
- [x] C1 What does a PMF add that a histogram lacks? → §3.1 · recite 2026-08-27 ✓
- [ ] C2 Why must PMF values sum to 1? → §3.1 · recite 2026-08-27 ✗ → ch03-c004

## Terms
| term | the book's definition (verbatim, p.) | field usage / contrast |
|---|---|---|
| PMF | "…" (p. 28) | ◆ often defined measure-theoretically elsewhere; same object |

## Propositions
- {the chapter's leading claims, tight bullets, each anchored (§/p.) — the book's voice}

## Argument
{the chapter's argument reconstructed in the student's own words and notation; quotation
marks alone carry the book's voice here}

## Worked examples
### {name} (p. NN)
{≥1 example transcribed verbatim — math or code — interleaved with annotation lines}

## My questions
- Q1 (open) {…}
- Q2 (closed — answered in §3.4) {…}

## Teach-back
### {YYYY-MM-DD} · closed-book
{the student's explanation, verbatim, ≤200 words — never written or edited by you}
#### Critique
{your flags: smuggled terms, assertions without mechanism, order errors → card ids minted}

## Summary
{3–5 sentences, written after a passing recite, student-approved — the Cornell bottom strip}

## Links
- ◆ **Resource · video** — [{title}]({url}): {one line on why it earns a place}
- concept: [p-value](../../../concepts/p-value.md)
```

## Chapter note rules

- **Cues are the retrieval surface.** 4–8 prequestions written *before* the read (PASS-2.md), numbered `C1`…; append, never renumber. After the read each gains a one-line pointer to where it resolved; after a recite, `✓` or `✗ → <card id>` with the date. A cue is the human-readable face of what the recite will ask.
- **Terms is Adler's "come to terms":** the author's definition verbatim with its page, and — only where usage genuinely diverges from the field — a ◆ contrast. A term the whole field shares belongs in a concept note; this table is about *this author's* usage.
- **Propositions restate the book; Argument restates the student.** Propositions are the chapter's claims in the book's voice, every bullet anchored. Argument is the same logic rebuilt in the student's own notation — the section that proves the chapter was understood rather than transcribed.
- **Worked examples are transcribed verbatim** (the worked-example fade in ASSESS.md builds on them); annotations interleave as plain lines, no ◆ needed (see Voice, below).
- **My questions** are the student's open threads, `Q1`… per chapter, `open` → `closed — {what closed it}`; pass 3's critique harvests the ones that stayed open.
- **Header facts are static book facts** (pages, deck path). Mutable study state — status, box, due, confidence — lives in CONTENTS.md only; a note header never carries it.
- **Voice.** Like margin notes in three-pass, a chapter note is mostly the conversation's own voice: inside Argument, Worked-example annotations, My questions, Teach-back, and Summary, no ◆ is needed — quotation marks with anchors carry the book's voice. Cues, Terms, Propositions, and Links follow the normal ◆ rule because they mix the book's content with yours.

## Who writes which section

You draft Cues, Terms, Propositions, and the Links resources; the read fills Argument and Worked examples together. **The student alone writes the Teach-back and owns My questions and the final Summary wording** — you may critique a teach-back (ASSESS.md) and propose a summary, but their words stand. A teach-back you drafted, completed, or polished is a rule violation, not a favor (SKILL.md's gotcha).

## Concept note template

```md
# P-value
sources: downey2014-think-stats · ch 7 · p. 214; rosner2015-biostatistics · ch 5 · p. 132

## Passages
> "{verbatim passage}" — downey2014-think-stats · ch 7 · p. 214

## Terms
{how each book names and defines it — the terminological mapping between sources}

## Questions
{the questions the sources jointly address about this concept}

## Issues
{where the sources genuinely disagree — each side anchored to its book}

## My resolution
{the student's synthesis, their voice — "unresolved" is a legitimate entry}
```

## Concept note rules

- **Atomic and concept-titled.** One idea per file, named for the idea. If a note wants two ideas, it is two notes.
- **Born on the concept-reflex or in pass 3.** During a read, when an idea will clearly recur across books, offer one line — "start a concept note for *p-value*?" — and write it on yes (the sections beyond Passages may start empty). Pass 3's consolidation unit (PASS-3.md) fills and extends them deliberately.
- **Sources only grow.** Each book that touches the concept appends to `sources:` and to Passages; nothing is removed when a book closes. With one book the Issues section is usually empty — that is the syntopical slot waiting for book two.
- **My resolution is the student's.** Same ownership rule as the teach-back.
- **Cards never live here** and ledgers never cross book directories — a concept note is a reading aid, not a scheduling object; cards that drill a concept live in some book's deck and `links:` the note.

## Searching

The uniform fields make grep the search interface:

```sh
grep -n "^- \[ \] C" books/<slug>/notes/ch03-*.md      # unresolved cues in a chapter
grep -rn "(open)" books/<slug>/notes/                  # open student questions
grep -rn -i "poisson" books/*/notes/ concepts/         # a topic, across everything
grep -rn "sources:.*downey2014" concepts/              # concepts a book contributed to
```

On the pages, the same fields feed the live filter.
