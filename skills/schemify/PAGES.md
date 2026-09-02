The two web pages are how a steward who has never read JSON sees the schemas and talks back. Read this when building, refreshing, serving, or presenting either page. The build commands and their contracts live in LAYOUT.md; the pages are renders — the schemas are the source of truth.

Table of contents

- [The two pages](#the-two-pages)
- [Building and refreshing](#building-and-refreshing)
- [Serving](#serving)
- [Searching the dictionary](#searching-the-dictionary)
- [Presenting to the steward](#presenting-to-the-steward)
- [Styling and branding](#styling-and-branding)

## The two pages

- **`dictionary.html`** — the searchable data dictionary: every variable's label, type, valid values with their meanings, constraints, and the routing rules, grouped by category, one section per table. Fully self-contained — schemas inlined, rendering library vendored in `assets/` — so it opens by double-click, offline, forever. Keyword search is built in; a **Semantic search** switch beside the title adds meaning-based lookup on request (below). This is the page stewards review and print.
- **`playground.html`** (one per table) — the toy data made visible and the validator made live: the PASS and FAIL fixtures loadable at a click, every seeded violation highlighted on its cell with the rule's own explanation, column headers carrying the schema's labels and codes, and a file picker so the steward can drop in their own JSON or CSV and watch it validate — entirely in their browser; nothing they upload leaves their machine, which matters when their real data is sensitive. It loads its table engine from a CDN and needs a local server (below).

Both pages share one masthead — the `/schemify` mark, then tabs that switch between the dictionary and each table's playground — one title block, and one colophon, so a steward moving between them never has to re-orient.

## Building and refreshing

EXECUTE `render.py dictionary` and `render.py playground` (contracts and fallbacks in LAYOUT.md) — never hand-write or hand-edit the pages. Rebuild whatever this session's schema or fixture edits touched; `render.py check` names any page whose inputs have drifted since its last build, so staleness is a lint, not a memory burden.

A mid-flight package renders honestly: the dictionary shows the categories that exist and PROGRESS.md still says which are missing — presenting a partial page is fine, presenting it as finished is not.

## Serving

- **dictionary.html**: open straight from disk — `open dictionary.html` (macOS), `xdg-open` (Linux), `start` (Windows). No server, no network. Served over http instead (the playground's server does), its semantic search runs in a background worker rather than on the page's own thread — smoother, never required.
- **playground.html**: needs a local server, because browsers block the page's database engine on `file://`. From the package root: `python3 -m http.server 8000`, then `http://localhost:8000/playground.html`. Opened from disk anyway, the page itself shows exactly these instructions instead of a broken screen — designed degradation, not a bug. Offline, it explains that too and points at the dictionary page, which always works.
- Hosting the pages somewhere with a strict content-security policy: the playground needs `'unsafe-eval'` (its validator compiles schemas), and semantic search needs `'wasm-unsafe-eval'` plus `connect-src` for `cdn.jsdelivr.net` and `huggingface.co`. Where those are refused, the dictionary and its keyword search are untouched — ship the dictionary page alone and let `tools/validate.py` do the checking.

## Searching the dictionary

Two searches share the one box above each table, and the steward chooses which they get:

- **Keyword search** — always on, instant, offline. Typing filters every table to the rows whose name, description, or values contain the text, highlights the hits, and counts them per category; `/` focuses the box, `Esc` clears it. The right tool when the steward knows what a variable is called.
- **Semantic search** — the switch beside the page title, off by default. Switched on, the page fetches a small text-embedding model once (`Xenova/bge-small-en-v1.5`, about 34 MB, from huggingface.co, run by Transformers.js from cdn.jsdelivr.net), embeds every row's name, description, and value labels, and from then on answers a query with one ranked list: the keyword matches first — name, then description, then values — followed by up to ten rows that merely *mean* something similar, each badged *related*, its similarity shown when the name is hovered. “Smoking” finds the tobacco rows; “body size” finds height and weight. Clearing the box restores the category sections. The browser remembers the switch per package, so a steward who turned it on finds it on next time.

What the steward should know before they flip the switch — say it in their terms, or point at the note under it: the model is downloaded once and cached by the browser; the schemas' text is embedded on their machine and cached there too (IndexedDB, one store per table, so a revisit is instant and only edited rows are re-embedded); the query never leaves the browser. Their data is never involved — the page holds schemas only. Offline, or on a network that blocks those two hosts, the status chip beside the search box says semantic search is unavailable and keyword search carries on; the dictionary never depends on it.

Two practical notes. Served pages run the model in `assets/embed-worker.js`, off the page's thread; opened from disk, browsers refuse workers, so the model runs on the page itself — the first indexing of a large dictionary can pause the page for a few seconds. And the model is the library's verified default, named in the skill's template; changing it is a skill change, not a package setting.

When to suggest it: dictionaries past a few hundred variables, reviewers who know the concept but not the study's naming, and any steward who asks “where is the question about …?” more than once.

## Presenting to the steward

Open the page at the part you want judged — the dictionary's new category section, the playground with the FAIL fixture loaded — and ask for feedback in their terms: do the names, labels, and value meanings match how they'd document the study? Does the highlighted violation look like something that should be flagged in real data? Never ask a steward to approve "the schema"; ask them to approve what the page says, and translate their answer into schema edits yourself. Use the search box to land on the variable under discussion rather than scrolling to it; with semantic search on, the steward's own words for a concept usually find it.

The playground earns its keep at two moments: showing that the rules *catch* (load the FAIL fixture, walk one highlighted cell and its explanation), and letting the steward test their own file. If the toy rows strike the steward as unrepresentative, that is fixture feedback — take it into `toy_valid.json` and re-run the fixtures check.

## Styling and branding

`schema-pages.css` and the vendored rendering library arrive via `render.py init` and upgrade via `refresh-assets` — the pages' whole look lives in that stylesheet's published classes and theme tokens, and the two rendering libraries are themed through their `--dd-*` and `--dt-*` custom properties mapped onto the same tokens, so both pages read as one system in light, dark, and print. The `/schemify` mark — the tile-and-slash beside the wordmark in every masthead, the favicon, the “Made with /schemify” line in every colophon — is `assets/schemify-mark.svg` in the skill, inlined by `render.py` at build time so it themes with the page and prints; it is how a steward recognizes a schemify package at a glance. Never inline ad-hoc styles into a page or edit the shipped assets in place: a package with custom styling needs is a package whose stylesheet should be regenerated from the skill, not forked by hand.
