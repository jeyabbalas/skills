The study workspace is the directory where the skill was invoked. This file is the tree of record: what lives where, what everything is named, and the contracts for the four bundled scripts. All workspace paths are relative to the workspace root.

Table of contents

- [The workspace tree](#the-workspace-tree)
- [Standing rules](#standing-rules)
- [Naming rules](#naming-rules)
- [Asset paths inside pages](#asset-paths-inside-pages)
- [Script contracts](#script-contracts)
- [Serving pages](#serving-pages)

## The workspace tree

A workspace with one book mid-study (the same shape holds at three books — `concepts/` simply grows richer as books accumulate):

```
<workspace root>
├── SHELF.md                        ← index of every book (SHELF-FORMAT.md)
├── STUDENT.md                      ← who the student is (BOOTSTRAP.md)
├── index.html / index.md           ← shelf dashboard, rendered FROM SHELF.md
├── concepts/                       ← cross-book concept notes (NOTES-FORMAT.md)
│   ├── index.html / index.md       ← concepts index, rendered from what exists here
│   └── p-value.md / p-value.html   ← one atomic concept per file
├── assets/                         ← book-study.css/js + VERSION-book-study (workspace.py)
└── books/
    └── downey2014-think-stats/
        ├── BOOK.md                 ← dossier: bibtex, goal, status, companions,
        │                             session log (BOOK-FORMAT.md)
        ├── CONTENTS.md             ← chapter manifest: ranges, prerequisites, statuses,
        │                             boxes, due dates (CONTENTS-FORMAT.md)
        ├── book.pdf                ← the book itself — always book.pdf or book.epub
        ├── reviews.jsonl           ← append-only review ledger (DECK-FORMAT.md)
        ├── index.html / index.md   ← book hub: chapter progress + artifact directory
        ├── survey.html / survey.md ← pass 1 inspectional survey
        ├── map.html / map.md       ← chapter prerequisite map (data from CONTENTS.md)
        ├── critique.html / critique.md ← pass 3 critique
        ├── notes/                  ← ch02-distributions.md/.html — Cornell chapter notes
        ├── decks/                  ← ch02.md/.html — card banks and their quiz pages
        ├── exams/                  ← exam-01.md/.html — cumulative exams
        ├── practice/               ← ch02/exercise_01.py + its test; p3-<slug>/
        │                             re-creations (code and worked files, no pages)
        ├── figures/                ← ch02-fig-01.png crops referenced by chapter pages
        └── extract/                ← cached chapter text from ingestion (regenerable)
```

## Standing rules

- **Create lazily.** `workspace.py init` makes only `assets/` and `books/`; every deeper directory appears the first time something is written into it. Never scaffold empty structure ahead of need.
- **Case is ownership.** `UPPERCASE.md` files are living state documents with a `*-FORMAT.md` schema in this skill; lowercase files are content sources and their renders. `reviews.jsonl` is the one non-markdown state file: an append-only machine ledger (schema in DECK-FORMAT.md) with no render and no mirror — nothing restates it, so nothing can diverge from it.
- **Markdown is the source of truth; every `.html` is a disposable render.** Regenerate a page from its same-basename markdown; never hand-merge into HTML. Three pairs render *state* rather than a same-named source: the shelf `index.*` render SHELF.md, the book hub `index.*` render BOOK.md + CONTENTS.md + what exists on disk, and the concepts `index.*` render the notes that exist beside them. Everything else pairs one `.md` source with one `.html` render. `extract/`, `practice/`, and `reviews.jsonl` have no renders.
- **The workspace never references the skill's install directory** — no links, no copies of skill files beyond `assets/`, no writes. `workspace.py check` enforces this.
- **A shelf can share a directory with a paper-reading library.** Every filename here is disjoint from the three-pass skill's (`STUDENT.md` not `READER.md`, `books/` not `papers/`, `book-study.*` + `VERSION-book-study` in `assets/`); never touch `paper-reader.*` or a bare `VERSION` — they belong to the other skill.

## Naming rules

- **Book slug**: `surname` + `year` + `-short-title`, lowercase kebab, short title 1–4 words, whole slug ≤ 40 characters: `downey2014-think-stats`, `weinberg2013-biology-of-cancer`. On collision, extend the short title with more title words — never numeric suffixes. The slug doubles as the citation key. Multi-volume works: one slug per volume by default; a work studied as one arc keeps one slug, continuous chapter numbers, and a note in CONTENTS.md naming which file holds which chapters.
- **Chapters**: `chNN` — the book's own chapter numbers, zero-padded to two digits (`ch101` past 99). CONTENTS.md is the numbering authority; front and back matter the book doesn't number stay out of the chapter table (the survey covers them).
- **Chapter notes**: `notes/chNN-<short-slug>.md` — `ch02-distributions.md`.
- **Decks and cards**: `decks/chNN.md`; cards inside are `chNN-cNNN`, zero-padded to three. Scan the deck for the highest number and increment; never reuse an id — the ledger references it forever.
- **Exams**: `exams/exam-NN.md`, numbered in the order they are sat.
- **Figures**: `figures/chNN-fig-MM.png` — `MM` is the book's within-chapter figure number (`Figure 2.3` → `ch02-fig-03.png`); books that number straight through keep the running number (`Figure 47` in chapter 5 → `ch05-fig-47.png`).
- **Concepts**: `concepts/<kebab-slug>.md`, named for the concept, never for a book.
- **Practice**: `practice/chNN/exercise_NN.py` with `test_exercise_NN.py` beside it; pass-3 re-creation targets in `practice/p3-<short-slug>/`.
- **Extract cache**: `extract/chNN.md` (chapter text); `extract/chNN.pdf` (the split escape hatch).

## Asset paths inside pages

Pages link the shared assets relatively; the depth is fixed by location:

| Page location | `{{ASSET_PREFIX}}` |
|---|---|
| workspace root (`index.html`) | `` (empty) |
| `concepts/` | `../` |
| book root (`books/<slug>/*.html`) | `../../` |
| book subdirectory (`notes/`, `decks/`, `exams/`) | `../../../` |

## Script contracts

`<skill-dir>` below means this skill's own directory — the directory this file was loaded from. Always EXECUTE these scripts (never read them); they print JSON to stdout and refuse to write into `<skill-dir>`.

**Fallback ladder** (applies to all four):

1. `uv run <skill-dir>/scripts/<script>.py …` — preferred; uv resolves dependencies.
2. No uv → plain `python3` fully runs `workspace.py` (stdlib), `ingest_epub.py toc`/`images` (stdlib), and `revise.py` — which then schedules on its inlined SM-2 engine; the output's `scheduler` field says which engine ran, and `python3 -m pip install --user fsrs` upgrades it to FSRS. For `ingest_pdf.py` and `ingest_epub.py text`: `python3 -m pip install --user pypdf pdfplumber pypdfium2 pillow beautifulsoup4 markdownify`, then plain `python3`.
3. Neither → degrade loudly, never silently. Ingestion: read the book natively page-ranged, hand-write CONTENTS.md's chapter table from the printed table of contents (a hand-edited CONTENTS.md is first-class, not a failure), and tell the student which `figures/` paths manual screenshots should be saved to — pages pick them up with no edits. Revision: run the session chapter-tier only from CONTENTS.md's boxes (quiz due chapters from their notes' `## Cues`), still append every graded line to `reviews.jsonl`, and log in the session log: `item scheduler unavailable — item-tier debt accruing`.

| Script | Use |
|---|---|
| `workspace.py init [DIR]` | Create `assets/` + `books/`; idempotent; warns when assets are outdated. |
| `workspace.py add-book --slug S [--file PATH] [DIR]` | Validate the slug, create `books/S/`, copy the book to `book.pdf`/`book.epub` (magic-byte checked; DjVu detected and refused with a conversion hint). |
| `workspace.py refresh-assets [DIR]` | Overwrite `assets/book-study.*` from the skill copy — upgrades every page at once. |
| `workspace.py check [DIR]` | Lint the generated pages: sister-markdown pairing, resolvable relative links, no absolute-path or skill-directory references. Run before closing any session that touched HTML. |
| `ingest_pdf.py toc PDF [--offset K]` | Outline → chapters with PDF-page ranges (seed for CONTENTS.md — the student confirms, and a hand-edited CONTENTS.md always wins). No outline → printed-TOC parse; the output then says how to calibrate `--offset`. Also reports whether the PDF has a text layer. |
| `ingest_pdf.py text PDF --pages A-B --out books/<slug>/extract/chNN.md [--layout] [--force]` | Cache a chapter's text. An existing cache short-circuits (`--force` re-extracts). Prefer your native page-ranged PDF reading — it sees layout and figures; this sees only text, and it mangles displayed math: when an equation must be verbatim, crop the region with `figures` and read the image. |
| `ingest_pdf.py figures PDF --page N [--bbox x0,y0,x1,y1] --out books/<slug>/figures/chNN-fig-MM.png [--scale 2]` | Without `--bbox`: caption candidates with guessed content bboxes (`matched-content` is trustworthy; `band-fallback` is a generous over-crop — verify, then tighten). With `--bbox`: render the region to PNG at 2×. Points, origin top-left. |
| `ingest_pdf.py split PDF --chapters 7=201-236,… --out books/<slug>/extract/` | Per-chapter PDFs — an escape hatch for viewers that cannot page-range a huge file. Prefer page-ranged native reading. |
| `ingest_epub.py toc EPUB` | Spine + TOC → chapters (spine runs; DRM-protected EPUBs are refused honestly — never unlocked). |
| `ingest_epub.py text EPUB --chapter N --out books/<slug>/extract/chNN.md [--force]` | Chapter XHTML → markdown cache; same cache contract as the PDF `text`. |
| `ingest_epub.py images EPUB --chapter N --out books/<slug>/figures/` | Extract the chapter's images as `chNN-img-KK.*`; rename the keepers per the figure naming rule. |
| `revise.py due [DIR] [--book S] [--today YYYY-MM-DD] [--limit N]` | Replay the ledger → due and new cards plus an interleaved session plan. Run at every session open (SKILL.md). A pure reader — it never writes; the agent appends ledger lines (DECK-FORMAT.md). |
| `revise.py stats [DIR] [--book S] [--today YYYY-MM-DD]` | Per-chapter accuracy, Brier score, reliability, blind-spot flags — the dashboard's numbers, and the ledger validator (`ledger_warnings` must be empty at close). |
| `revise.py exam --book S [DIR] [--chapters 1-8] [--n 20] [--today YYYY-MM-DD]` | Coverage-weighted, Bloom-mixed, interleaved exam spec; the agent turns it into `exams/exam-NN.md` (ASSESS.md). |

## Serving pages

Open pages straight from disk — `open index.html` (macOS), `xdg-open index.html` (Linux), `start index.html` (Windows). Pages are built to work under `file://`: no modules, no fetch, data inlined. If the student's browser is locked down about local files, fall back to `python3 -m http.server` from the workspace root and open `http://localhost:8000/`.
