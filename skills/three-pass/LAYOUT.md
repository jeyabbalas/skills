The reading workspace is the directory where the skill was invoked. This file is the tree of record: what lives where, what everything is named, and the contracts for the three bundled scripts. All workspace paths are relative to the workspace root.

Table of contents

- [The workspace tree](#the-workspace-tree)
- [Standing rules](#standing-rules)
- [Naming rules](#naming-rules)
- [Asset paths inside pages](#asset-paths-inside-pages)
- [Script contracts](#script-contracts)
- [Serving pages](#serving-pages)

## The workspace tree

A workspace with two papers mid-read (the same shape holds at one paper or ten — `map.*` simply doesn't exist until the second paper arrives):

```
<workspace root>
├── LIBRARY.md                      ← index of every paper (LIBRARY-FORMAT.md)
├── READER.md                       ← who the reader is (BOOTSTRAP.md)
├── index.html / index.md           ← library dashboard, rendered FROM LIBRARY.md
├── map.html / map.md               ← relationship map across papers (≥2 papers)
├── assets/                         ← paper-reader.css/js + VERSION (workspace.py)
└── papers/
    ├── vaswani2017-attention/
    │   ├── PAPER.md                ← dossier: bibtex, goal, status, session log (PAPER-FORMAT.md)
    │   ├── SKELETON.md             ← cached anatomy: outline, page anchors, figure/table/
    │   │                             equation inventory with crop bboxes (PASS-1.md)
    │   ├── GLOSSARY.md             ← glossary source of truth (GLOSSARY-FORMAT.md)
    │   ├── notes.md                ← margin-note stream (NOTES-FORMAT.md)
    │   ├── paper.pdf               ← the paper itself, always this name
    │   ├── index.html / index.md   ← paper hub: artifact directory with status
    │   ├── profile.html / profile.md      ← pass 1 paper profile
    │   ├── summary.html / summary.md      ← pass 2 detailed summary (one file, all sections)
    │   ├── references.html / references.md← key references + reference map
    │   ├── glossary.html                  ← render of GLOSSARY.md
    │   ├── notes.html                     ← searchable render of notes.md
    │   ├── figures/                ← fig-01.png + fig-01.html/.md, table-01.html/.md
    │   ├── equations/              ← eq-01-<short-name>.html/.md
    │   ├── feynman/                ← 0001-<role>.md transcripts (no pages)
    │   ├── derivations/            ← deriv-01-<short-name>.html/.md
    │   └── reproduction/
    │       ├── INVENTORY.md        ← algorithms, pseudocode, code links, data, hyperparameters
    │       ├── PLAN.md             ← phase index (PASS-3-REPRODUCE.md)
    │       ├── phases/             ← phase-1.md … self-contained phase specs
    │       ├── prompts/            ← phase-1-prompt.md … paste-able session prompts
    │       ├── walkthrough.html / walkthrough.md ← code ↔ paper-idea walkthrough
    │       └── code/               ← the implementation
    └── bahdanau2014-nmt-attention/ ← pass 1 only: PAPER.md, SKELETON.md, paper.pdf,
                                      index.*, profile.*
```

## Standing rules

- **Create lazily.** `workspace.py init` makes only `assets/` and `papers/`; every deeper directory appears the first time something is written into it. Never scaffold empty structure ahead of need.
- **Case is ownership.** `UPPERCASE.md` files are living state documents with a `*-FORMAT.md` schema in this skill; `lowercase` files are content sources and their renders. The two never collide on a name.
- **Markdown is the source of truth; every `.html` is a disposable render.** If something exists only in HTML, it does not exist. Regenerate a page from its same-basename markdown (match is case-insensitive: `glossary.html` renders `GLOSSARY.md`); never hand-merge into HTML. Two files are renders of *state* rather than of a same-named source: `index.html`/`index.md` (library) render `LIBRARY.md`, and the paper hub `index.html`/`index.md` render `PAPER.md` + what exists on disk. Everything else pairs one `.md` source with one `.html` render.
- **The workspace never references the skill's install directory** — no links, no copies of skill files beyond `assets/`, no writes. `workspace.py check` enforces this.

## Naming rules

- **Paper slug**: `surname` + `year` + `-short-title`, lowercase kebab, short title 1–4 words, whole slug ≤ 40 characters: `vaswani2017-attention`, `bahdanau2014-nmt-attention`. On collision, extend the short title with more title words — never numeric suffixes. The slug doubles as a stable citation key.
- **Figures and tables**: the paper's own numbering, zero-padded to two digits — `fig-01.png`, `fig-01.md`, `table-03.md`. Appendix numbering keeps its letter: `fig-a1.md`.
- **Equations**: `eq-<NN>-<short-name>` using the paper's equation numbers when it has them, else order of first appearance: `eq-01-scaled-dot-product.md`.
- **Derivations**: `deriv-<NN>-<short-name>`, numbered in the order derivations are undertaken.
- **Notes**: entries inside `notes.md` are `N0001`, `N0002`, … zero-padded to four, never reused. The highest number is the paper's engagement odometer.
- **Feynman transcripts**: `0001-<role>.md`, incrementing per sitting.

## Asset paths inside pages

Pages link the shared assets relatively; the depth is fixed by location:

| Page location | `{{ASSET_PREFIX}}` |
|---|---|
| workspace root (`index.html`, `map.html`) | `` (empty) |
| paper root (`papers/<slug>/*.html`) | `../../` |
| paper subdirectory (`figures/`, `equations/`, `derivations/`, `reproduction/`) | `../../../` |

## Script contracts

`<skill-dir>` below means this skill's own directory — the directory this file was loaded from. Always EXECUTE these scripts (never read them); they print JSON to stdout and refuse to write into `<skill-dir>`.

**Fallback ladder** (applies to all three; `pdf_figures.py` is the only one needing a dependency):

1. `uv run <skill-dir>/scripts/<script>.py …` — preferred; uv resolves dependencies.
2. No uv → `python3 -m pip install --user pymupdf`, then `python3 <skill-dir>/scripts/<script>.py …` (`fetch_paper.py` and `workspace.py` are stdlib-only — plain `python3` always works for them).
3. Neither → skip the script's job with a note: build the figure page with its placeholder panel (ARTIFACTS.md) and tell the reader which `.png` path a manual screenshot should be saved to; the page picks it up with no edits.

| Script | Use |
|---|---|
| `fetch_paper.py REF --out papers/<slug>/paper.pdf [--email E]` | Download a paper from an arXiv id/URL, direct PDF URL, or DOI (DOI needs `--email` for the Unpaywall lookup). Verifies the bytes are a real PDF. On failure it prints a hint — typically: find an open-access copy, or ask the reader to download the PDF and give you the path. |
| `pdf_figures.py list PDF [--page N]` | Page count, document outline (seed for SKELETON.md), and figure/table caption candidates with caption bboxes and a guessed content bbox (`guess_kind`: `matched-content` is trustworthy; `band-fallback` is a generous over-crop — verify, then tighten). Coordinates are PDF points, origin top-left. |
| `pdf_figures.py crop PDF --page N --bbox x0,y0,x1,y1 --out papers/<slug>/figures/fig-01.png [--scale 2]` | Render a page region to PNG at 2× (the figure-page image). |
| `pdf_figures.py extract PDF --out DIR [--page N]` | Save embedded raster images with placements. Vector figures have no raster — use `crop`. |
| `pdf_figures.py text PDF --pages 1-2,5` | Plain text of the given pages. Use when your harness cannot read PDF pages directly — otherwise prefer your native PDF reading (it sees layout and figures; this sees only text). Text extraction mangles displayed math — never put a formula you reconstructed from garbled text inside quotation marks; when a quote or equation must be verbatim-exact, render the region with `crop` and read the image. |
| `workspace.py init [DIR]` | Create `assets/` + `papers/`; idempotent; warns when assets are outdated. |
| `workspace.py add-paper --slug S [--pdf PATH] [DIR]` | Validate the slug, create `papers/S/`, copy the PDF to `paper.pdf`. |
| `workspace.py refresh-assets [DIR]` | Overwrite `assets/paper-reader.*` from the skill copy — upgrades every page at once. |
| `workspace.py check [DIR]` | Lint the generated pages: sister-markdown pairing, resolvable relative links, no absolute-path or skill-directory references in `href`/`src` (prose, prompts, and state files are not linted). Run it before closing any session that touched HTML. |

## Serving pages

Open pages straight from disk — `open index.html` (macOS), `xdg-open index.html` (Linux), `start index.html` (Windows). Pages are built to work under `file://`: no modules, no fetch, data inlined. If the reader's browser is locked down about local files, fall back to `python3 -m http.server` from the workspace root and open `http://localhost:8000/`.
