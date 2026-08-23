How to author every generated artifact: the markdown sources, the HTML renders, and the conventions that keep pages consistent across sessions that share no memory. Consistency here is mechanical — templates, published CSS classes, and these rules — never taste recalled from a previous session.

Table of contents

- [The rendering pipeline](#the-rendering-pipeline)
- [Templates and tokens](#templates-and-tokens)
- [Marking Beyond the book](#marking-beyond-the-book)
- [Math](#math)
- [Survey page](#survey-page)
- [Chapter pages](#chapter-pages)
- [Deck pages](#deck-pages)
- [Exam pages](#exam-pages)
- [Concept pages and index](#concept-pages-and-index)
- [Prerequisite map](#prerequisite-map)
- [Critique page](#critique-page)
- [Book hub](#book-hub)
- [Shelf dashboard](#shelf-dashboard)
- [Sister markdown quality](#sister-markdown-quality)

## The rendering pipeline

1. Write or update the **markdown source** (the artifact's `.md`).
2. Copy the right **template** from `./templates/`, replace every `{{TOKEN}}`, and fill the slot comments from the markdown source, using only the markup shown in the template comments and here.
3. Save as the same-basename `.html` beside the source.

Regenerate the render of every markdown file you touched this session — and only those. Never edit an `.html` directly: a page you hand-edited is a page the next session will silently clobber. Run `workspace.py check` (LAYOUT.md) before closing a session that touched HTML.

## Templates and tokens

| Template | Used for |
|---|---|
| `./templates/page.html` | survey, chapter notes, concept notes, critique — any article |
| `./templates/list.html` | the concepts index — filterable entry lists |
| `./templates/deck.html` | deck quiz pages and exam pages — question/answer lists with reveal and print modes |
| `./templates/hub.html` | the book hub `index.html` |
| `./templates/shelf.html` | the workspace `index.html` |
| `./templates/map.html` | the chapter prerequisite map |
| `./templates/equation.html` | an equation page, when a single equation earns one (rare in pass 2; same mechanics as three-pass) |

Tokens: `{{TITLE}}` (page title), `{{ASSET_PREFIX}}` (depth table in LAYOUT.md), `{{BREADCRUMB}}` (trail `Shelf › <book> › <item>`, concepts under `Shelf › Concepts ›`; a segment is an `<a>` only when a page exists to link — Shelf links the workspace `index.html`, the book links its hub; skip collection segments like "Notes", which have no index page), `{{PASS_BADGE}}` (`Pass 1` / `Pass 2` / `Pass 3` / `Revise` — the pass that owns the artifact; pages that span passes — chapter notes, decks, the hub — badge the book's current status string, e.g. `pass-2`), `{{GENERATED_DATE}}` (today, `YYYY-MM-DD` — update on regeneration), `{{SISTER_MD}}` (the source markdown's filename). Component markup lives in the template comments; classes used beyond them: `wide` (breakout for figures/maps/tables), `scroll` (horizontal-scroll wrapper), `print-urls` (on containers whose external URLs should print), `chrome` (anything hidden in print), `print-key` (on `<body>`, toggled by the deck page's button — printing *with* the answer key).

## Marking Beyond the book

SKILL.md defines when content must be demarcated and the five kinds. The forms:

- **Markdown** (artifact sources, state files, anywhere): a blockquote whose first line starts with ◆ —

  ```md
  > ◆ **Beyond the book · Source** — [StatQuest: Maximum Likelihood](https://…) — a gentler
  > derivation than §7.4's, worth the 10 minutes if the log-likelihood setup didn't land.
  ```

  A blockquote that does *not* start with ◆ is a verbatim quote from the book, nothing else.

- **HTML**: the amber aside (amber appears nowhere else in the design):

  ```html
  <aside class="beyond" data-kind="source">
    <p class="beyond-kicker">◆ Beyond the book · Source</p>
    <p>…</p>
  </aside>
  ```

- A `Diagram`-kind aside may contain inline SVG; keep it self-contained and theme-safe by using the CSS variables (`var(--ink)`, `var(--accent)`, …) for all strokes and fills.

## Math

- Delimiters: inline `\( … \)`, display `\[ … \]`. Never a bare `$…$`.
- Math-bearing pages carry `data-math` on `<body>` and the pinned KaTeX tags — already present in `page.html` and `equation.html`; copy them from `page.html` into a rendered `deck.html` or `map.html` when that page carries formulas. Pages without math carry neither. Offline, raw LaTeX stays visible and a banner says so — intended degradation; sisters always carry clean LaTeX.
- Equation-page term coloring works exactly as the template's comments show (six `tN` slots, `data-term` legend rows).

## Survey page

`survey.md` → `survey.html` via `page.html`. The content template (field order, caps) is in PASS-1.md — the page mirrors it, one `h2` per section. Once chapter pages exist, each chapter-map row links its `notes/chNN-<slug>.html`. Keep it terse: the survey is a map, and if the render exceeds roughly two printed pages the source is over budget.

## Chapter pages

`notes/chNN-<slug>.md` → `.html` via `page.html`. The note's `##` sections (NOTES-FORMAT.md) render in order as `<details class="sec" open id="cues">…` — slug ids `cues`, `terms`, `propositions`, `argument`, `worked-examples`, `my-questions`, `teach-back`, `summary`, `links` — with the `sec-tools` expand/collapse block once, before the first. Inside:

- **Cues** as a plain list; resolved cues carry their pointer, missed ones their `✗ → card id` as text (the deck page is where cards live — link it once in the section's lead line).
- **Terms** as a semantic `<table>` in `div.scroll.wide`.
- **Worked examples** verbatim in `pre` (code) or display math; figures referenced from the book render as `figure.figure.wide` with the image at `../figures/chNN-fig-MM.png`, the **verbatim** caption as `figcaption`, and `<p class="src">Figure N.M · p.P of book.pdf</p>`. If the crop doesn't exist yet: keep the `<img>` and add `<p class="placeholder">No image yet — see book.pdf, page P. Save a screenshot to figures/chNN-fig-MM.png and it will appear here.</p>`.
- **Teach-back** — the student's text as a plain paragraph (it is their voice, not a book quote: no blockquote), the critique under an `h4`.
- **Links** — each resource as a ◆ `Source` aside; concept links as plain links. Container class `print-urls` on this section.

## Deck pages

`decks/chNN.md` → `decks/chNN.html` via `deck.html`. One `<article class="entry qa">` per card, deck order, `id="card-chNN-cNNN"`, `data-tags` from type + bloom + stage (+ `retired`):

```html
<article class="entry qa" data-tags="apply, completion" id="card-ch07-c012">
  <p class="entry-meta"><span>ch07-c012</span><span class="tag">apply</span>
    <span class="tag">completion</span></p>
  <div class="q"><p>Derive the MLE of \(\lambda\) for an i.i.d. Poisson sample…</p></div>
  <details class="answer">
    <summary>Answer</summary>
    <div class="a"><p>\(\ell(\lambda)=\dots\); \(\hat\lambda=\bar{x}\)…</p></div>
    <p class="rubric"><strong>Good requires:</strong> correct derivative, correct solve,
      saying why the critical point is a maximum.</p>
    <p class="entry-meta"><span>ch.7 · §7.4 · p.214 · “the maximum likelihood estimate is obtained”</span></p>
  </details>
</article>
```

Retired cards keep rendering with class `superseded` and a `<span class="tag">retired</span>` chip — visibly retired, never deleted. The template's `sec-tools` block carries the page controls (reveal all · hide all · the print toggle). **Print modes**: printing is questions-only by default (answers stay hidden — a self-testable paper deck); the `Print: with answer key` button toggles `print-key` on `<body>` and the printout includes answers and rubrics. The filter input filters by text and `data-tags` as everywhere.

## Exam pages

`exams/exam-NN.md` → `.html` via `deck.html`, same markup — one `entry.qa` per item in the exam's order, **no chapter labels anywhere on the page** (the anchor line inside `details.answer` is the one exception, since it only shows once revealed). The source's front matter lines record what the spec said: chapters covered, n, seed, date sat. Questions-only print is what makes a re-sittable paper exam free.

## Concept pages and index

`concepts/<slug>.md` → `.html` via `page.html`, sections in the note's order (NOTES-FORMAT.md); every passage blockquote carries its `{book · ch · p.}` anchor. `concepts/index.md` → `index.html` via `list.html`: one `article.entry` per concept, alphabetical, `id="concept-<slug>"`, `data-tags` from the source books' slugs; entry body = the first line of My resolution (or "unresolved"); `entry-meta` = the sources list. Regenerate the index whenever a concept note is added or gains a source. Container keeps `print-urls`.

## Prerequisite map

`map.md` → `map.html` via `map.html` (template). CONTENTS.md's `prereqs` column is the authority; the map derives from it — edit order: CONTENTS.md, then the sister's `yaml map-data` block, then its mirror in the HTML's JSON `script.map-data`. Data drives, prose follows.

```md
```yaml map-data
nodes:
  - {id: ch03, label: "3 · Probability mass functions", sub: "recited · box 2", title: "Chapter 3 — Probability mass functions", col: 2, row: 0, href: "notes/ch03-pmfs.html"}
edges:
  - {from: ch05, to: ch02, label: "builds on", kind: prereq}
```
```

Node `id` = `chNN`; `label` = `N · Short title` (≤26 chars); `sub` = the status plus box (`recited · box 2`, or `unread`); `col`/`row` are small integers — put prerequisites left of (or above) their dependents, let long linear runs flow along a row and wrap or fan onto rows below, and state the layout logic in one line when presenting. Edge `kind` ∈ `prereq` (solid — a stated dependency) | `soft` (dashed — an inferred, ◆-grade edge; say so when presenting). Linear adjacency is implied and not drawn — only the load-bearing edges from the `prereqs` column appear. Each node's hidden `section.map-profile` panel (`id="panel-chNN"`) holds a chapter mini-card: status line, the chapter-map one-liner from the survey, cue count, links to note and deck. Chapters without pages keep `href` empty and rely on the panel.

## Critique page

`critique.md` → `critique.html` via `page.html`. Content template in PASS-3.md; each finding renders as an `h3` with its `F1 · count · anchor` heading line, the four labeled paragraphs inside. Dissolved findings add class `superseded` on their wrapper `<section>` — visibly retired, like everything else.

## Book hub

`books/<slug>/index.html` + printable `index.md`, via `hub.html`, rendered from BOOK.md + CONTENTS.md + what exists on disk. Masthead chip = the book's current `status`; colophon reads "book hub". Subtitle = author · edition · year. Then, in order:

1. The student's goal, verbatim (from BOOK.md).
2. **The progress table** — one `.dir-row` per chapter inside `section.dir.progress`, CONTENTS.md order:

   ```html
   <div class="dir-row">
     <span class="what"><a href="notes/ch01-exploratory.html">1 · Exploratory data analysis</a></span>
     <span class="state">recited · box 2 · due 2026-08-29</span>
     <span class="stat">Brier .11</span>
     <span class="bar" role="img" aria-label="accuracy 82%"><span style="width:82%"></span></span>
   </div>
   ```

   `stat` and `bar` come from `revise.py stats` at regeneration (accuracy = the bar; omit both spans for chapters with no attempts). A blind-spot-flagged chapter adds class `flagged` to its row and appends ` · blind spot` to the stat. Unread chapters: bare text, `state` = `unread`.
3. `section.dir` rows for the book-level artifacts that exist — survey, map, critique, each exam, the deck index (one row per deck), `book.pdf`, and the state files (BOOK.md, CONTENTS.md — linked as files).

Regenerate whenever a session adds an artifact, moves a status, or changes the numbers.

## Shelf dashboard

Workspace `index.html` + printable `index.md`, via `shelf.html`, rendered from SHELF.md: one `article.card` per book (most recently touched first) — linked title, `who` line (author · edition), the gist, and a `passes` line built from the row: `<span class="done">● recited 2/13</span> <span class="now">◐ ch 3 · pass-2</span> <span class="todo">○ 12 due</span>` (the due count from `revise.py due` at regeneration; drop the span when zero). Add a concepts card when `concepts/` is non-empty. Include the filter input only at 6+ books. Regenerate whenever SHELF.md changes.

## Sister markdown quality

The sister is not an export artifact — it is the version the student prints and reads on paper. Complete sentences, the same section order as the page, ◆ blockquotes where the page has asides, clean LaTeX for math, and a first line naming the book and artifact (`# Think Stats — Chapter 3 deck`). Deck sisters list every card in full — prompt, answer, rubric — because the printed sister *is* the answer key; the questions-only artifact is the page's default printout, not the sister's job. If the page and its sister would tell a different story, the sister is what the next session trusts — keep it whole.
