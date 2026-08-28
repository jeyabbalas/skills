# `chapterhouse` — example workspace

A real study workspace produced by the [`chapterhouse`](../../skills/chapterhouse/SKILL.md) skill during its verification dry-run, kept here so you can see what the skill builds before you install it. The simulated student is a genetic-epidemiology postdoc — fluent in R, rusty in Python — studying Allen Downey's *Think Stats* (2nd edition) toward analyzing their own cohort data. The workspace covers seven sessions over twelve days: bootstrap, a complete pass 1 (survey, genre call, question backlog, reading plan, prerequisite map), pass 2 for chapters 1–2 with real decks and a real review ledger, two revision sessions with Leitner-box movement, one passing programming exercise, a first cross-book concept note — and chapter 3 just opened in scaffolded, section-paced mode: the student (rusty in Python) asked for a pre-reading guide before each section, so the agent wrote the chapter's assumed-background file and a §3.1 walkthrough before any reading happened. The book has 14 chapters; the study is deliberately mid-flight — that is the state a resuming session most often meets.

One honest note: the student's side of the conversation — the teach-backs, overrides, and interview answers — was simulated during the dry-run. Every book fact, page anchor, quiz card, and scheduler number is real: the ledger replays, the tests pass, and the pages regenerate from their markdown sisters.

## Browse it

Open `workspace/index.html` in a browser — the pages work straight from disk. Worth clicking through:

- **The shelf dashboard** (`workspace/index.html`) — one card per book with progress chips and the due count the scheduler reported at the last session's close.
- **The book hub** (`workspace/books/downey2014-think-stats/index.html`) — per-chapter progress rows: status, Leitner box, next due date, a Brier calibration chip, and an accuracy bar, all derived from the review ledger by `revise.py stats`.
- **The inspectional survey** (`survey.html`) — the book's unity in one sentence, the genre call that decides which quiz types are legal, the student's eight-question backlog, and a reading plan with one licensed skim (ch 12). Note the ◆ aside flagging which prerequisite edges are inferred rather than stated.
- **The prerequisite map** (`map.html`) — a clickable SVG of what depends on what; dashed edges are the inferred, ◆-grade ones. Click a chapter for its mini-card.
- **A chapter page** (`notes/ch02-distributions.html`) — the Cornell note rendered: prequestions with their recite outcomes (one ✗ that became a card), the author's definitions verbatim beside the field's usage, a transcribed worked example with the student's annotations, a real figure crop with its rounding-artifact story, the student's own closed-book teach-back with the agent's critique — including the flag that "digit preference" is the student's term, not the book's.
- **The scaffold guides** (`guides/ch03-foundations.html`, `guides/ch03-s01-pmfs.html`) — what the skill builds when a book is too hard to read unaided: the background the chapter silently assumes (Python dicts mapped onto R, each item ending in a check), and a step-by-step §3.1 walkthrough in a fixed rhythm — what it says → the book's own words, verbatim and page-anchored → a picture → a check — ending in an ungraded self-test. Note the page-level ◆ banner and the inverted colophon: on a guide page, unmarked content is the *agent's* teaching, the book's words appear only inside quotation marks. The chapter note (`notes/ch03-pmfs.html`) shows the section-pacing side: a `Sections` checklist as the single home of within-chapter progress, cues pointing into the guide (`· guide S1`), and an Argument section that in scaffold mode only ever holds the student's own say-back. (Standalone interactive lab pages — `labs/` — are the one new artifact this demo skips.)
- **A quiz deck** (`decks/ch02.html`) — questions visible, answers and grading rubrics behind disclosures. Print it as-is for a questions-only practice sheet, or press "Print: with answer key" first. Card ch02-c007 shows the worked-example fade at `completion` stage.
- **The review ledger** (`books/downey2014-think-stats/reviews.jsonl`) — 30 append-only graded exchanges, including a student override (`"why": "reader: I rambled"`) and two miss-retry pairs. Every due date in the workspace is a replay of this file: try `uv run ../../skills/chapterhouse/scripts/revise.py due workspace --book downey2014-think-stats --today 2026-08-23`.
- **The practice exercise** (`practice/ch02/`) — the agent-written spec and tests, the student's solution: `python3 test_exercise_01.py` passes.
- **A concept note** (`workspace/concepts/effect-size.html`) — the syntopical slot: one book's passages gathered, the Issues section deliberately waiting for a second book to argue with.

Two doctrines to notice while browsing: markdown is the source of truth (every page names its sister in the colophon), and anything in the agent's voice is marked ◆ on an amber background — the student always knows which voice is speaking.

## Restoring what git leaves out

Two pieces are deliberately untracked:

1. **The book itself** (`workspace/books/downey2014-think-stats/book.pdf`). *Think Stats 2e* is free from the author's site (Green Tea Press, CC BY-NC); the repo doesn't redistribute it. Restore:

   ```sh
   curl -L -o workspace/books/downey2014-think-stats/book.pdf https://greenteapress.com/thinkstats2/thinkstats2.pdf
   ```

2. **The text-extraction cache** (`workspace/books/downey2014-think-stats/extract/`), which regenerates from the PDF:

   ```sh
   cd workspace
   uv run ../../../skills/chapterhouse/scripts/ingest_pdf.py text books/downey2014-think-stats/book.pdf --pages 21-36 --out books/downey2014-think-stats/extract/ch01.md
   uv run ../../../skills/chapterhouse/scripts/ingest_pdf.py text books/downey2014-think-stats/book.pdf --pages 37-50 --out books/downey2014-think-stats/extract/ch02.md
   uv run ../../../skills/chapterhouse/scripts/ingest_pdf.py text books/downey2014-think-stats/book.pdf --pages 51-64 --out books/downey2014-think-stats/extract/ch03.md
   ```

The figure crop (`figures/ch02-fig-02.png`) *is* tracked — a small excerpt kept so the chapter page renders; the page cites its exact source page.

## How to prompt the agent

Install per the [repo README](../../README.md#install), then invoke **in the directory you want as your study workspace**. In harnesses without slash commands, say "Use the chapterhouse skill: …".

Bringing a book:

```
/chapterhouse ~/Downloads/thinkstats2.pdf
/chapterhouse ~/books/biology-of-cancer.epub
/chapterhouse register the book at ~/Downloads/rosner.pdf but don't survey it yet
```

Pass 1:

```
/chapterhouse survey the book we just registered
Is this the right book for my goal, or should I be reading something else?
Here are the questions I want this book to answer: …
Let's fix the chapter ranges — chapter 1 actually starts on PDF page 21
```

Pass 2 (one chapter per session; the due check runs first every time):

```
/chapterhouse                          (resume — proposes the warm-up, then the next: pointer)
Let's read chapter 3
Quiz me on chapter 2, closed book
Here's my teach-back for chapter 2: …
Give me a small coding exercise on PMFs
I worked exercise 4.1 on paper — here's a photo: ~/Desktop/ex41.jpg
```

Revision:

```
/chapterhouse revise                   (a pure revision session from the due queue)
What's due today, and how is my calibration looking?
I disagree — score that one Good, not Hard
```

Pass 3, when the plan's chapters are recited:

```
Let's critique the book
I'll re-derive Cohen's d and the pooled variance from scratch — test me
Build my cumulative exam over chapters 1–8
Consolidate the effect-size and p-value concepts across my books
```

Escalation is always yours: each pass ends with the skill presenting what it built and asking whether to go deeper — it never advances on its own, and no chapter is marked done without its closed-book recitation.
