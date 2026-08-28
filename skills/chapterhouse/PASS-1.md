Pass 1 is the inspectional survey: acquire the book, map it, classify it, and plan the read — enough for the student to decide whether this book deserves months of their time, without having read it yet. Adler's discipline governs: systematic skimming is a real reading technique, not a lesser one, and its product is a map, never a verdict on material you haven't read.

Table of contents

- [Acquiring the book](#acquiring-the-book)
- [Registering](#registering)
- [Ingesting](#ingesting)
- [Intake enrichment](#intake-enrichment)
- [The systematic skim](#the-systematic-skim)
- [Classifying the genre](#classifying-the-genre)
- [Finishing CONTENTS.md](#finishing-contentsmd)
- [The question backlog](#the-question-backlog)
- [The reading plan](#the-reading-plan)
- [Survey template](#survey-template)
- [Presenting pass 1](#presenting-pass-1)
- [Splitting the pass](#splitting-the-pass)

## Acquiring the book

- **Given a file path**: verify it opens and is a PDF or EPUB; then register. This is the normal case — most academic books are bought, and the student's own copy is always first-class.
- **Given a URL**: fetch only when the page it came from names a verifiably open license (CC, an author-posted open edition) — record the license and check date in BOOK.md's `source`. If you cannot name the license, don't fetch: ask the student to download through their own access and give you the path.
- **Given only a title**: search the web for a *legitimate* copy — the publisher's page, the author's page, an open-textbook library. Confirm with the student you found the right book (title + author + edition) before anything downloads; when only paid copies exist, say so and ask for their file.
- **DRM-protected or converted formats**: a DRM'd EPUB is refused honestly (SKILL.md's gotcha; the ingest script detects it); a DjVu file gets the conversion hint the script prints, then re-enters as a PDF.

## Registering

1. Choose the slug (rules in LAYOUT.md) and EXECUTE `workspace.py add-book --slug <slug> --file <path>`.
2. Write BOOK.md per BOOK-FORMAT.md — the bibliographic block from the book in hand plus the publisher page, and the one goal question: **"What do you want from this book?"** Record the answer verbatim.
3. Add the SHELF.md row (SHELF-FORMAT.md), status `pass-1` (or `inbox` if the student wants register-only).

## Ingesting

1. EXECUTE `ingest_pdf.py toc` or `ingest_epub.py toc` (contracts and fallbacks in LAYOUT.md). The output is a **seed**: proposed chapters with page or spine ranges, plus warnings — no text layer, printed-page numbering that needs the `--offset` calibration, a too-thin TOC.
2. Show the student the proposed chapter table and **have them confirm or correct the ranges before CONTENTS.md is written** — spot-check chapter 1's true start against the PDF yourself first. A hand-edited CONTENTS.md always wins over any script output, now and forever.
3. Write CONTENTS.md's header and chapter table per CONTENTS-FORMAT.md (plan columns still empty — the skim fills them). Do not pre-extract text for the whole book; `extract/` fills lazily, chapter by chapter, as pass 2 arrives (EPUBs: extract chapter text on first need; PDFs: prefer native page-ranged reads).

## Intake enrichment

Three web lookups, once per book, results into BOOK.md's `## Companions` with check dates — ◆ `Source` discipline throughout, authoritative links only, and the student may decline any of it:

- **Errata** — the publisher's or author's errata page. Transcribe the entries that touch plannable chapters into CONTENTS.md's `## Errata`; this is the single highest-value lookup for a math or statistics book.
- **Companion code / site** — the book's own repository or site; record the URL (and default branch or tag) for pass-2 exercises and pass-3 re-creation.
- **Solutions** — whether worked solutions exist and where (in-book appendix, official manual, instructor-only). Never link an unauthorized solutions dump.

## The systematic skim

Adler's inspectional read, operationalized — an hour, not a day, in page-ranged reads:

1. **Title page, preface, introduction** — read fully: what the author says the book is, who it's for, how they say to read it.
2. **The table of contents, studied** — not glanced: the argument's architecture is usually right here.
3. **The index, scanned** — the dozen most load-bearing terms by column inches; dip into one or two crucial passages they point at.
4. **Pivotal chapters, dipped** — openings and closings of the chapters that look load-bearing; first/last paragraphs, summary boxes, exercise sets (count them for `exx`).
5. **The last pages** — read the final chapter's close fully; authors summarize their whole case there.

While skimming, fill the chapter table's `diff` and `exx` columns and note candidate prerequisite edges.

## Classifying the genre

One line in CONTENTS.md's header, with an anchored rationale. The test:

- **`theoretical`** — the book argues what is *true*; chapters build proofs or evidence toward claims (a mathematics text, a theory monograph). Mastery will mean re-deriving.
- **`practical`** — the book teaches what to *do*; chapters teach procedures the student should perform (most programming, statistics, and methods books). Mastery will mean doing it unaided.
- **`expository`** — the book surveys what is *known*; chapters organize a territory (most biology textbooks, reviews-as-books). Mastery will mean reconstructing mechanisms and maps from memory.

Say the consequence in one sentence — the genre gates which item types are legal (ASSESS.md) and which pass-3 re-creation track applies (PASS-3.md) — and let the student veto a borderline call. Mixed books take the dominant genre; note the exception chapters in their `diff` row's company.

## Finishing CONTENTS.md

Fill `prereqs` from the book's own signals first — "this chapter assumes chapter 4", cross-references, the preface's reading-order diagram; an edge you inferred without textual support is a ◆ claim and its rationale goes on the survey page. Then render the prerequisite map (`map.md`/`map.html` — data derived from the `prereqs` column; spec in ARTIFACTS.md) when the DAG is non-linear; a strictly linear book skips the map.

## The question backlog

Before any real reading, **offer** the backlog, once: 5–15 questions the student wants this book to answer — concrete, in their words, against their goal ("Why do my cohort's p-values cluster near 0.05?", not "understand statistics"). Push once past generic answers — then take the answer, whichever it is. **"Reading cover to cover", "I don't know the book yet", and "no questions" are first-class answers, not failed elicitations**: record the decline verbatim and dated in the survey's questions section, add the `questions:` line to BOOK.md (BOOK-FORMAT.md), and never offer again — a question the student brings later, any session, simply joins the survey section and retires the line. With a backlog: it lives on the survey page; pass 2 seeds each chapter's prequestions from the backlog items that touch it, and pass 3's synthesis answers it explicitly. Without one: prequestions, when the student wants them at all, derive from each chapter's own survey (PASS-2.md), and pass 3 answers to the book's own claims instead (PASS-3.md). A question the book turns out not to answer is a finding, not a failure.

## The reading plan

Adler licenses not reading everything; make the license explicit and the student's:

- **Order** — the default is the book's own; reorder only along the DAG.
- **Skip / skim licenses** — chapters outside the goal get `skipped`; background the student owns gets `skimmed`. Both leave the recite denominator; either can be revoked later.
- **Pacing** — chapter-at-a-time is the default; any chapter may be planned by sections instead (propose it for the ones marked `diff 3`; mechanics in PASS-2.md). A default, not a contract — the student re-decides at any chapter's start, and the log's `next:` pointer always names the live unit.
- **Target sessions** — planned units — chapters, or their sections where the plan paces by sections — ÷ STUDENT.md's cadence, said honestly: "13 chapters at 2 sessions a week is about 7 weeks of pass 2."

The plan's prose lives on the survey page; its outcomes are CONTENTS.md statuses.

## Survey template

`survey.md` → `survey.html` via `page.html` (ARTIFACTS.md):

```md
# {Title} — inspectional survey

**Book type**: {genre} — {rationale} (anchor)
**In one sentence**: {the book's unity — what the whole thing is about} (anchor)

## The shape of the book
- {part/chapter architecture in a few indented bullets — structure, not summary}

## Chapter map
- ch {N} — {one line on what it teaches} · diff {1–3} · {exercise count} exx
{one per chapter; skip/skim decisions annotated}

## What depends on what
{the non-linear prerequisite edges, one line each, with the book's evidence — or "strictly linear"}

## Your questions for this book
1. {backlog, numbered, verbatim — or the decline, quoted and dated: "{their words}"
   ({date} — offered and declined; one line on what replaces it in passes 2 and 3)}

## The reading plan
{order · licenses · pacing · target sessions — and what would change the plan}
```

## Presenting pass 1

1. Render `survey.html`, the map (when it exists), the book hub, and the shelf dashboard (ARTIFACTS.md); open the survey (serving notes in LAYOUT.md).
2. Give a three-sentence spoken version in chat — what kind of book, what it covers, what the plan is.
3. Ask the gate question: **right book for your goal — worth the analytical read?** Record the decision (BOOK.md status + log line). On a yes, propose the entry unit for the `next:` pointer: the plan's first chapter. On a no, `done` at the survey is a respectable outcome — the survey was the point.

## Splitting the pass

When acquisition plus ingestion fill the sitting (a 1,000-page PDF with a broken outline can), close after CONTENTS.md is confirmed — log `next: skim + plan` — and run the skim, backlog, and plan next session. The gate always ends the pass, whichever session reaches it.
