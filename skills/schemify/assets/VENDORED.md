Provenance for the files in this directory. `site/app.js`, `site/schemify.css`, and `embed-worker.js` are authored in this repository; `schemify.py` copies them into every workspace (`site/`) and package (`assets/`). The library and the mark below come from elsewhere and are kept byte-identical to their sources; data-table is loaded at run time, pinned.

## json-schema-data-dictionary.global.js

- Package: [`json-schema-data-dictionary`](https://www.npmjs.com/package/json-schema-data-dictionary) v0.8.0 — the IIFE build (`dist/json-schema-data-dictionary.global.js`), global `JsonSchemaDataDictionary`.
- Source: <https://github.com/jeyabbalas/json-schema-to-data-dictionary> (MIT). Fetched from `https://cdn.jsdelivr.net/npm/json-schema-data-dictionary@0.8.0/dist/json-schema-data-dictionary.global.js`.
- sha256: `c9c693dc8a0c38ac2c72a2526a6c0d7ff28337c29c1aa36bd32c34391c8095cb`. Never hand-edit it; `uv run scripts/vendor_schemify_assets.py --check` (repo root) verifies it.
- What the pages use: `schemaDocumentsToTable`, `renderDataDictionary` (shadow DOM), `buildViewModel` (the Skip logic tab's readings), `splitDescription`, and for semantic search `createWorkerEmbedder`, `createTransformersEmbedder`, `serveEmbedder`, `createIndexedDbVectorCache`. The website also drives undocumented markup — `tr[data-dd-row][data-dd-row-index]`, `.dd-col-name`, `[data-dd-goto]`, `[data-dd-category][data-dd-cat]`, `[data-dd-category-toggle]`, `[data-dd-root]` — to add its *Details* buttons and to jump to a variable or topic; re-check them when updating.
- Semantic search loads Transformers.js 4.3.1 from cdn.jsdelivr.net and the library's default model (`MongoDB/mdbr-leaf-ir`) from huggingface.co, only when a person turns it on. Neither is vendored.

**Updating**: run `uv run scripts/vendor_schemify_assets.py --version <x.y.z>` (repo root), update the version and sha256 above, check the exports and markup named above still exist, and rebuild the example workspace (`schemify.py refresh-assets`, then `build`). Workspaces pick the update up with `refresh-assets`.

## data-table (loaded from jsDelivr, not vendored)

- Package: [`@jeyabbalas/data-table`](https://www.npmjs.com/package/@jeyabbalas/data-table) v0.10.0 (MIT) — the Data check tab's interactive table of toy data, with each validation error pinned to its cell (`table.annotations`), the dictionary's wording in the column headers (`setColumnHeaderTooltip`), and the column charts.
- Not copied here: `site/app.js` imports `https://cdn.jsdelivr.net/npm/@jeyabbalas/data-table@0.10.0/dist/data-table.js` and its stylesheet when the tab opens, and starts the library's worker (`dist/assets/worker-BpxbYHX2.js` for this version) through a same-page `blob:` URL; DuckDB-WASM and its extensions come from jsDelivr and extensions.duckdb.org. Only toy rows ever reach it. Offline, the tab falls back to a plain table.
- The pin lives in `site/app.js` (`DT.version`, `DT.worker`); `uv run scripts/vendor_schemify_assets.py --check` verifies it matches this section.

**Updating**: set `DT.version` and `DT.worker` in `site/app.js` — the worker's file name is in that version's `dist/assets/` listing on jsDelivr — then update this section, open the website served, and check the Data check tab: cell tints, the popover on a red cell, F8, the column header tooltip.

## json-schema-mark.svg

- The JSON Schema project's mark — curly braces around a tick and a cross — taken unmodified from the current logo in the project's website repository: `public/img/logos/logo-blue.svg` at commit `234558e41b50e4282a69e1a302011b582ad73e57` of <https://github.com/json-schema-org/website>, keeping only its four mark paths (the wordmark removed) and the official blue `#002CC4`. The pages show it in the official white in dark mode.
- License: the repository offers its contents under BSD-3-Clause or AFL-3.0 — "Copyright (c) 2022 JSON Schema Specification Authors". schemify uses BSD-3-Clause; the notice, conditions, and disclaimer travel beside the mark in `LICENSE-json-schema-mark.txt`. Neither license grants trademark rights.
- The mark is the JSON Schema project's; schemify is not affiliated with or endorsed by the project, and every page says so in its footer.
