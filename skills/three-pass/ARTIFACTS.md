How to author every generated artifact: the markdown sources, the HTML renders, and the conventions that keep pages consistent across sessions that share no memory. Consistency here is mechanical — templates, published CSS classes, and these rules — never taste recalled from a previous session.

Table of contents

- [The rendering pipeline](#the-rendering-pipeline)
- [Templates and tokens](#templates-and-tokens)
- [Marking Beyond the paper](#marking-beyond-the-paper)
- [Math](#math)
- [Paper profile](#paper-profile)
- [Detailed summary](#detailed-summary)
- [Glossary page](#glossary-page)
- [Notes page](#notes-page)
- [Figure pages](#figure-pages)
- [Table pages](#table-pages)
- [Equation pages](#equation-pages)
- [References page and reference map](#references-page-and-reference-map)
- [Relationship map](#relationship-map)
- [Paper hub](#paper-hub)
- [Library dashboard](#library-dashboard)
- [Sister markdown quality](#sister-markdown-quality)

## The rendering pipeline

1. Write or update the **markdown source** (the artifact's `.md`).
2. Copy the right **template** from `./templates/`, replace every `{{TOKEN}}`, and fill the slot comments from the markdown source, using only the markup shown in the template comments and here.
3. Save as the same-basename `.html` beside the source.

Regenerate the render of every markdown file you touched this session — and only those. Never edit an `.html` directly: a page you hand-edited is a page the next session will silently clobber. Run `workspace.py check` (LAYOUT.md) before closing a session that touched HTML.

## Templates and tokens

| Template | Used for |
|---|---|
| `./templates/page.html` | profile, summary, figure, table, references, derivation, walkthrough — any article |
| `./templates/list.html` | glossary, notes — filterable entry lists |
| `./templates/hub.html` | the paper hub `index.html` |
| `./templates/library.html` | the workspace `index.html` |
| `./templates/map.html` | relationship map, and the reference map when it outgrows the references page |
| `./templates/equation.html` | equation pages |

Tokens: `{{TITLE}}` (page title), `{{ASSET_PREFIX}}` (depth table in LAYOUT.md), `{{BREADCRUMB}}` (trail `Library › <paper> › <item>`; a segment is an `<a>` only when a page exists to link — Library links `index.html` at the workspace root, the paper links its hub; skip collection segments like "Figures", which have no index page), `{{PASS_BADGE}}` (`Pass 1` / `Pass 2` / `Pass 3` — the pass that owns the artifact; pages spanning passes, like notes, badge the paper's current status), `{{GENERATED_DATE}}` (today, `YYYY-MM-DD` — update on regeneration), `{{SISTER_MD}}` (the source markdown's filename). Component markup lives in the template comments; classes used beyond them: `wide` (breakout for figures/maps/tables), `scroll` (horizontal-scroll wrapper), `print-urls` (on glossary/notes/references containers so external URLs print), `chrome` (anything hidden in print).

## Marking Beyond the paper

SKILL.md defines when content must be demarcated and the five kinds. The forms:

- **Markdown** (artifact sources, state files, anywhere): a blockquote whose first line starts with ◆ —

  ```md
  > ◆ **Beyond the paper · Critique** — The ablation in §5.2 does not control for parameter count…
  ```

  A blockquote that does *not* start with ◆ is a verbatim quote from the paper, nothing else.

- **HTML**: the amber aside (amber appears nowhere else in the design):

  ```html
  <aside class="beyond" data-kind="critique">
    <p class="beyond-kicker">◆ Beyond the paper · Critique</p>
    <p>…</p>
  </aside>
  ```

- A `Diagram`-kind aside may contain inline SVG; keep it self-contained and theme-safe by using the CSS variables (`var(--ink)`, `var(--accent)`, …) for all strokes and fills.

## Math

- Delimiters: inline `\( … \)`, display `\[ … \]`. Never a bare `$…$` — prose about "$5" would render as math.
- Math-bearing pages carry `data-math` on `<body>` and the pinned KaTeX tags — already present in `page.html` and `equation.html`; copy them from `page.html` when another template needs math (a map whose profile panels contain formulas, say). Pages without math carry neither. Offline, raw LaTeX stays visible and a banner says so — that is the intended degradation; sisters always carry clean (unannotated) LaTeX.
- Term coloring (equation pages): wrap each term of the display equation as `\htmlClass{term tN term-<id>}{…}` where `tN` picks one of six color slots (`t1`–`t6`) and `<id>` is a short stable slug (`q`, `scale`, `posterior`). The matching legend row carries `data-term="<id>"` and the same `tN` class. Reuse a slot only after all six are taken on that page.

## Paper profile

`profile.md` → `profile.html` via `page.html`. The content template (field order, terseness caps, citation slots) is in PASS-1.md — the page mirrors it exactly, one `h2` per field group, no chrome beyond the standard. Once `summary.html` exists, each outline row links to its `summary.html#sec-<slug>` anchor. The profile is deliberately terse: if the render exceeds roughly two printed pages, the source is over budget — cut there, not here.

## Detailed summary

`summary.md` → `summary.html` via `page.html`. One file for the whole paper:

- On first touch, seed the source with the full section skeleton from SKELETON.md — every top-level section as a header with *(not yet read together)* under the unvisited ones. The reader always sees the whole shape and what remains.
- Render each top-level section as `<details class="sec" open id="sec-<slug>">` with `<summary>N · Section title</summary>`; subsections are `h3`/`h4` inside. Put the expand/collapse `sec-tools` block (template comment) once, before the first section.
- Section slugs come from SKELETON.md numbering (`sec-3-2` for §3.2) so anchors never move.
- Interleave ◆ asides where the conversation added value; margin notes that target a section get a one-line link — `<p class="entry-meta"><a href="notes.html#note-N0007">N0007 — gist</a></p>` — at the end of that section.

## Glossary page

`GLOSSARY.md` (schema: GLOSSARY-FORMAT.md) → `glossary.html` via `list.html`. One `article.entry` per term, alphabetical, `id="term-<slug>"`, `data-tags` from the entry's tags; definition paragraph; `entry-meta` line with `first needed: §N` and the authoritative external link. Container keeps `print-urls`. The filter input and count are already in the template.

## Notes page

`notes.md` (schema: NOTES-FORMAT.md) → `notes.html` via `list.html`. One `article.entry` per note, newest first, `id="note-N0007"`, `data-tags` from type + tags; `entry-meta` = id · date · anchor · type, plus the status when it has ended (`superseded-by N0012`, `closed — deriv-01`); then the gist as `h3`, a blockquote only when the source entry has one, the distilled thought. Notes whose status has ended (superseded or closed) add class `superseded` and stay on the page — visibly retired, never deleted.

## Figure pages

`figures/fig-NN.md` → `fig-NN.html` via `page.html`, image `fig-NN.png` cropped at 2× via `pdf_figures.py crop` (contract in LAYOUT.md). Structure:

1. `figure.figure.wide` with the image, the **verbatim** caption as `figcaption`, and `<p class="src">Figure N · p.P of paper.pdf</p>`.
2. `## What it shows` — a faithful description of what is actually drawn; cite panels/axes as the paper labels them.
3. `## How to read it` — walk the reader through it in their register.
4. Optional ◆ asides (a redrawn or annotated version of the figure is `Diagram` kind).
5. `nav.pager.chrome` with prev/next figure links.

If the image could not be extracted, keep the `<img>` tag and add under it: `<p class="placeholder">No image yet — see paper.pdf, page P. Save a screenshot to figures/fig-NN.png and it will appear here.</p>` A manual screenshot then slots in with no page edit.

## Table pages

`figures/table-NN.md` → `table-NN.html` via `page.html`. Transcribe the table **verbatim** — every cell, exactly as printed, in a semantic `<table>` inside `div.scroll.wide` (markdown table in the source). Caption verbatim, then `## What it says` and `## How to read it` as for figures. No sorting controls: reordering a transcribed table misrepresents the paper. Bold or footnote markers in the original are reproduced, not interpreted.

## Equation pages

`equations/eq-NN-<name>.md` → `.html` via `equation.html`. The source carries a fenced data block the render is rebuilt from:

````md
```yaml equation-data
latex_clean: "\\mathrm{Attention}(Q, K, V) = \\mathrm{softmax}\\left(\\frac{QK^{\\top}}{\\sqrt{d_k}}\\right)V"
latex_annotated: "\\mathrm{Attention}(\\htmlClass{term t1 term-q}{Q}, …"
terms:
  - {id: q, slot: t1, math: "Q", meaning: "…, per the paper (§, p.)", intuition: "…"}
```
````

The page: statement (`latex_annotated` in the `eq-statement`), `## What it says`, `## Intuition`, `## Term by term` (one `legend-row` per term, in reading order of the equation), `## Where it's used`, optional ◆ asides, pager. The sister markdown displays `latex_clean` in `\[ … \]` plus the same sections — printable and readable in any markdown viewer.

## References page and reference map

`references.md` → `references.html` via `page.html` (use `map.html` instead only if the map is the page's main event). Part 1 — the references in SKELETON.md's key-references list, each: full citation, what it contains, why it matters *to this paper* (tie to the section that cites it), and a link (DOI/arXiv; a link the paper itself doesn't print is web-located — label it so). Part 2 — a `div.map.wide` whose nodes are this paper (center) plus the key references; clicking a reference node reveals a `section.map-profile` info card: citation, one-paragraph content summary, relevance, link. Container class `print-urls`.

## Relationship map

`map.md` → `map.html` via `map.html` (template). The source's fenced block is the single thing to iterate on:

````md
```yaml map-data
nodes:
  - {id: vaswani2017-attention, label: "Attention Is All You Need", sub: "Vaswani · 2017",
     title: "Attention Is All You Need", col: 1, row: 0, href: "papers/vaswani2017-attention/index.html"}
edges:
  - {from: vaswani2017-attention, to: bahdanau2014-nmt-attention, label: "replaces recurrence", kind: builds-on}
```
````

Rules: node `id` = paper slug; `label` ≤ 26 characters; `sub` = `Surname · year`; grid `col`/`row` are small integers — place related papers adjacent, time flowing top→bottom or left→right, and say which when presenting. Edge `kind` ∈ `builds-on | contrasts | shares-method | same-problem`; `label` ≤ 4 words. When the reader asks for a different arrangement, the data block is what you iterate: edit it, mirror it into the HTML's JSON `script.map-data`, and update any prose that restates it (the layout-logic line, edge-grounding bullets) — data drives, prose follows. Each node gets a hidden `section.map-profile` panel with `id="panel-<slug>"` holding that paper's full profile content copied from its `profile.md` at regeneration — rewriting paper-relative links for the workspace root (`summary.html` → `papers/<slug>/summary.html`); node detail never lives in the map data itself. A map session logs to every paper whose node or edges it added or changed.

## Paper hub

`papers/<slug>/index.html` + printable `index.md`, via `hub.html`, rendered from `PAPER.md` and what exists on disk. The masthead chip shows the paper's current `status` (e.g. `pass-2`), and the colophon reads "paper hub", not "Pass N artifact". Subtitle = authors · venue · year; the `passes` line shows `● done ◐ in progress ○ not started` (annotate a committed-but-unstarted pass `○ up next`); then the reader's goal (verbatim from PAPER.md); then `section.dir` rows for every artifact that exists — profile, summary, glossary, references, notes, each figure/table/equation/derivation page, reproduction docs, `paper.pdf`, and the state files (`PAPER.md`, `SKELETON.md`, `notes.md` link to the rendered pages where one exists). State column: `Pass N · done / in progress`. Regenerate whenever a session adds an artifact or changes status.

## Library dashboard

Workspace `index.html` + printable `index.md`, via `library.html`, rendered from `LIBRARY.md`: one `article.card` per paper (most recently touched first) — linked title, `who` line, the one-line gist, `passes` chips; plus a map card when ≥ 2 papers. Include the filter input only at 6+ papers. Regenerate whenever LIBRARY.md changes.

## Sister markdown quality

The sister is not an export artifact — it is the version the reader prints and reads on paper. Complete sentences, the same section order as the page, ◆ blockquotes where the page has asides, clean LaTeX for math, and a first line naming the paper and artifact (`# Attention Is All You Need — Figure 1`). If the page and its sister would tell a different story, the sister is what the next session trusts — keep it whole.
