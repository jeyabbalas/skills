Pass 2 is the analytical read — the reader converses with the paper through you, the way a margin fills with notes. It skips what pass 3 owns (proofs, implementation detail) and builds the paper's reference apparatus: summary, glossary, figure/table/equation pages, references. Two kinds of work share every session: **planned units** (the next chunk per PAPER.md's `next:` pointer) and **reactive work** (whatever passage the reader brings up). Reactive work always wins the floor.

Table of contents

- [The exchange loop](#the-exchange-loop)
- [Planned units](#planned-units)
- [Building the summary](#building-the-summary)
- [Figure, table, and equation pages](#figure-table-and-equation-pages)
- [The references unit](#the-references-unit)
- [Ending pass 2](#ending-pass-2)

## The exchange loop

Every reactive exchange runs this loop:

1. **Locate.** Resolve what the reader is pointing at against SKELETON.md and read only that page range of the PDF.
2. **Converse.** Answer in READER.md's register. Quote the paper verbatim where exactness matters; mark anything beyond the paper ◆, in chat too (SKILL.md).
3. **Capture — gated.** If the exchange met a write-trigger in NOTES-FORMAT.md, write the note now (write immediately, not at session end). A question answered in one turn writes nothing.
4. **Glossary reflex.** If a term was load-bearing, offer one line — "add it to the glossary?" — and on yes, write the entry per GLOSSARY-FORMAT.md.
5. **Weave, don't build.** If the clarification is durable and its summary section already exists, fold it in (◆-marked if beyond the paper). If the section doesn't exist yet, leave it to its planned unit — a question is not a commission.
6. Return to the planned unit, or follow the reader.

## Planned units

One per session, by default (SKILL.md's session budget):

- **A summary section**: one top-level section of the paper, plus the figure, table, and equation pages belonging to it.
- **The references unit**: the references page and its map.
- **A Feynman sitting**: read FEYNMAN.md — the reader can also invoke it mid-session at any time.

The unit is done when its artifacts are written, rendered, and reflected in the closing checklist — not when "the section feels covered."

## Building the summary

`summary.md` — structure and page mechanics in ARTIFACTS.md. The work of this pass:

- On the first summary session, seed the file with the full section skeleton from SKELETON.md, then fill this session's section.
- Under each section header: the section's actual content as tight bullets — claims, methods, findings, each anchored (`§`/`p.`). Restate the paper faithfully; this is the paper's voice.
- Your voice goes in ◆ asides between the bullets: critique, outside context, a tie to the reader's goal or background, a clarifying diagram. Never blend the two voices.
- Read the section's pages from the PDF (range from SKELETON.md) while writing — summarize what the section says, not what you remember papers like it saying.

## Figure, table, and equation pages

Build a page when its planned unit arrives or the reader dwells on it — presence in the paper alone is not a trigger. Authoring specs are in ARTIFACTS.md; the pass-2 judgment calls:

- **Figures**: crop via `pdf_figures.py` (LAYOUT.md), tightening the skeleton's bbox if it was a `band-fallback` guess — look at the PNG, re-crop until clean, then write the final bbox back to SKELETON.md with the marker `(verified YYYY-MM-DD)`. Describe what is actually drawn before interpreting it; interpretation beyond the caption's own words is ◆.
- **Tables**: transcribe verbatim — every cell, checked against the PDF, no rounding, no reordering.
- **Equations**: an *important* equation earns a page — one the paper contributes, names, or leans on. Choose term ids and color slots once, in reading order; per-term meanings cite the paper's own definitions (`§`/`p.`), intuitions are yours and read as such (the `intuition` field is understood to be interpretive — ◆ callouts are for anything further).

## The references unit

From SKELETON.md's key-references list, build `references.md` / `references.html` (spec in ARTIFACTS.md): for each reference that matters, what it contains and why *this* paper leans on it — grounded in where it's cited. The reference map's edges follow the same grounding rule as the relationship map (PASS-1.md). Fetching a reference's own PDF is out of scope for this pass — if the reader wants to actually read one, that's a new paper for the library (New paper mode).

## Ending pass 2

Pass 2 has no natural last unit — it ends when the reader says the apparatus serves them. When the planned units run out (all sections summarized, references done), say so, and ask the gate question: **worth a pass 3 — re-derive the math and/or reproduce the results?** Record the decision (PAPER.md status + log line). A Feynman sitting is a good gate-check when the reader is unsure whether they've absorbed enough.
