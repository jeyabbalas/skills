`books/<slug>/BOOK.md` is the book's dossier — the small file a resuming session reads to know what this book is, why the student is reading it, and exactly where things stand. Fields update in place; the session log only appends.

## Template

````md
# {Full book title}

```bibtex
@book{downey2014-think-stats,
  author    = {Allen B. Downey},
  title     = {Think Stats: Exploratory Data Analysis},
  edition   = {2},
  year      = {2014},
  publisher = {O'Reilly Media},
  url       = {https://greenteapress.com/thinkstats2/}
}
```

status: pass-2
format: pdf
added: {YYYY-MM-DD}
source: {where the file came from — "provided by student", or the URL plus the open
license that allowed the fetch, with the date the license page was checked}
bibsource: {where the BibTeX facts came from — publisher page, library record}

## Goal
> "{the student's answer to “What do you want from this book?”, verbatim}"

## Companions
- code repo: {url · checked YYYY-MM-DD, or —}
- errata: {url · checked YYYY-MM-DD, or "none found ({date}, searched: {where})"}
- companion site: {url, or —}
- solutions: {what exists and where — "in-book appendix", a URL, or "not published"}

## Session log
- {YYYY-MM-DD} · pass 1 · registered; ingested; CONTENTS.md drafted · next: confirm ranges, survey skim
```
````

## Rules

- **The bibliographic block at intake, from day one.** Fill it from the book in hand plus the publisher page; record where in `bibsource`; the book slug is the citation key.
- **The goal is verbatim.** Ask once at intake — "What do you want from this book?" — record the answer in the student's own words, and let it steer every pass: the reading plan, the question backlog, which items get written. If it shifts mid-study, update it and say so in the log line.
- **`status`** — the enum, its meaning, and who moves it are defined in SHELF-FORMAT.md; this file is the authority for the value, the shelf row is its mirror. **`format`** is `pdf` or `epub`.
- **`source` records provenance and permission.** A student-provided file writes "provided by student". A fetched file writes the URL *and* the open license that permitted the fetch — if you cannot name the license, the fetch should not have happened (SKILL.md's acquisition gotcha).
- **Companions are looked up once, at intake** (PASS-1.md), each link dated. Errata findings themselves live in CONTENTS.md's `## Errata`, not here — this section only points at the page they came from.
- **One log line per session that touched this book** — a session that appends no log line did not happen. The line format and its `next:` requirement are defined in SKILL.md's Closing a session; the pass slot may read `revise` for a pure revision session. Keep each line one line: the log is an index of sessions, not a journal.
