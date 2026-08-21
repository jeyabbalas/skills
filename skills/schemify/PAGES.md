The two web pages are how a steward who has never read JSON sees the schemas and talks back. Read this when building, refreshing, serving, or presenting either page. The build commands and their contracts live in LAYOUT.md; the pages are renders — the schemas are the source of truth.

Table of contents

- [The two pages](#the-two-pages)
- [Building and refreshing](#building-and-refreshing)
- [Serving](#serving)
- [Presenting to the steward](#presenting-to-the-steward)
- [Styling](#styling)

## The two pages

- **`dictionary.html`** — the searchable data dictionary: every variable's label, type, valid values with their meanings, constraints, and the routing rules, grouped by category, one section per table. Fully self-contained — schemas inlined, rendering library vendored in `assets/` — so it opens by double-click, offline, forever. This is the page stewards review and print.
- **`playground.html`** (one per table) — the toy data made visible and the validator made live: the PASS and FAIL fixtures loadable at a click, every seeded violation highlighted on its cell with the rule's own explanation, column headers carrying the schema's labels and codes, and a file picker so the steward can drop in their own JSON or CSV and watch it validate — entirely in their browser; nothing they upload leaves their machine, which matters when their real data is sensitive. It loads its table engine from a CDN and needs a local server (below).

## Building and refreshing

EXECUTE `render.py dictionary` and `render.py playground` (contracts and fallbacks in LAYOUT.md) — never hand-write or hand-edit the pages. Rebuild whatever this session's schema or fixture edits touched; `render.py check` names any page whose inputs have drifted since its last build, so staleness is a lint, not a memory burden.

A mid-flight package renders honestly: the dictionary shows the categories that exist and PROGRESS.md still says which are missing — presenting a partial page is fine, presenting it as finished is not.

## Serving

- **dictionary.html**: open straight from disk — `open dictionary.html` (macOS), `xdg-open` (Linux), `start` (Windows). No server, no network.
- **playground.html**: needs a local server, because browsers block the page's database engine on `file://`. From the package root: `python3 -m http.server 8000`, then `http://localhost:8000/playground.html`. Opened from disk anyway, the page itself shows exactly these instructions instead of a broken screen — designed degradation, not a bug. Offline, it explains that too and points at the dictionary page, which always works.
- Hosting the playground somewhere with a strict content-security policy needs `'unsafe-eval'` (its validator compiles schemas); when that is refused, ship the dictionary page alone and let `tools/validate.py` do the checking.

## Presenting to the steward

Open the page at the part you want judged — the dictionary's new category section, the playground with the FAIL fixture loaded — and ask for feedback in their terms: do the names, labels, and value meanings match how they'd document the study? Does the highlighted violation look like something that should be flagged in real data? Never ask a steward to approve "the schema"; ask them to approve what the page says, and translate their answer into schema edits yourself.

The playground earns its keep at two moments: showing that the rules *catch* (load the FAIL fixture, walk one highlighted cell and its explanation), and letting the steward test their own file. If the toy rows strike the steward as unrepresentative, that is fixture feedback — take it into `toy_valid.json` and re-run the fixtures check.

## Styling

`schema-pages.css` and the vendored rendering library arrive via `render.py init` and upgrade via `refresh-assets` — the pages' whole look lives in that stylesheet's published classes and theme variables, matching in light, dark, and print. Never inline ad-hoc styles into a page or edit the shipped assets in place: a package with custom styling needs is a package whose stylesheet should be regenerated from the skill, not forked by hand.
