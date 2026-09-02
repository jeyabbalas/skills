Provenance for the files in this directory. `schema-pages.css`, `embed-worker.js`, and `schemify-mark.svg` are authored in this repository (the first two are copied into packages by `render.py`; the mark is inlined into every page at build time, never copied). The libraries below are vendored verbatim; `vendor/MANIFEST.sha256` carries a hash per file and `uv run scripts/vendor_schemify_assets.py --check` verifies them.

## json-schema-data-dictionary.global.js

- Package: [`json-schema-data-dictionary`](https://www.npmjs.com/package/json-schema-data-dictionary) v0.2.0 — IIFE build (`dist/json-schema-data-dictionary.global.js`), global `JsonSchemaDataDictionary`.
- Source: <https://github.com/jeyabbalas/json-schema-to-data-dictionary> (MIT). Fetched byte-identical from `https://cdn.jsdelivr.net/npm/json-schema-data-dictionary@0.2.0/dist/json-schema-data-dictionary.global.js`.
- sha256: `1bf66c4c259703bc603570caa08c44168c00dbc7f9a6f4d2ddf12af50c069c74`
- Never hand-edit this file — verify it against the npm dist when in doubt.
- What the pages use from the global: `schemaDocumentsToTable`, `renderDataDictionary` (light DOM, options re-set per mount), and for semantic search `createWorkerEmbedder`, `createTransformersEmbedder`, `serveEmbedder`, `createIndexedDbVectorCache`. The embedding runtime is deliberately not vendored: `dictionary.html` loads Transformers.js 4.2.0 from cdn.jsdelivr.net and the model `Xenova/bge-small-en-v1.5` from huggingface.co only when the steward switches semantic search on.

**Updating**: download the new version's `dist/json-schema-data-dictionary.global.js`, replace the file, update the version and sha256 above, confirm the exports named above are still on the global, and check that the selectors `schema-pages.css` relies on still exist in the build — print: `.dd-category[data-collapsed]`, `.dd-table-wrap`, `.dd-toolbar`, `.dd-actions`, `.dd-row`, `.dd-category-desc`, `.dd-badge`, `.dd-cond-badge`; layout: `.dd-title`, `.dd-header`, `.dd-table`, `.dd-col-name`. Existing packages pick the update up via `render.py refresh-assets`, which re-stamps `assets/VERSION`; rebuild their pages afterwards.

## vendor/data-table/

- Package: [`@jeyabbalas/data-table`](https://www.npmjs.com/package/@jeyabbalas/data-table) v0.7.0 — the ESM `dist/`, copied whole (~900 KB) minus `*.map` and `*.d.ts`.
- Source: <https://github.com/jeyabbalas/data-table> (MIT, `LICENSE` beside the code). Fetched byte-identical from `https://cdn.jsdelivr.net/npm/@jeyabbalas/data-table@0.7.0/dist/`.
- **Why vendored rather than loaded from a CDN, and why the layout matters**: the library starts its worker with `new Worker(new URL("assets/worker-<hash>.js", import.meta.url), { type: "module" })`. Served from a CDN that URL is cross-origin and, on esm.sh, a 404 — the module worker then fires a bare `error` event with no message and the page dies with "Worker error: undefined", which is exactly the failure this vendoring fixes. Keep `data-table/assets/worker-*.js` where it is: flattening the tree breaks that resolution.
- Chunk filenames carry content hashes and change on every release, so the file list is discovered from jsDelivr's package index rather than kept by hand. `render.py refresh-assets` deletes a package's `assets/vendor/` before recopying, so renamed chunks cannot pile up.
- Sourcemaps are deliberately absent (four times the weight of the code, and the browser never asks for them). Devtools will log a 404 for `//# sourceMappingURL` — expected, not a defect.
- What the pages use: `createDataTable`, `checkBrowserSupport`, and on the returned table `actions.setColumnHeaderTooltip`, `loadData`, `annotations.clear` / `annotations.addMany`. Themed through `--dt-*` custom properties mapped in `schema-pages.css`.
- Still fetched at runtime, and deliberately not vendored: the DuckDB WASM binary (~36 MB) from `cdn.jsdelivr.net`, once per browser, then cached. Where that is blocked the playground falls back to its static table.

## vendor/ajv-2020.mjs, vendor/ajv-formats.mjs

- Packages: [`ajv`](https://www.npmjs.com/package/ajv) v8.17.1 (draft 2020-12 entry) and [`ajv-formats`](https://www.npmjs.com/package/ajv-formats) v3.0.1. Both MIT.
- Neither ships a browser ESM build, so these are esm.sh's single-file bundles, fetched from `https://esm.sh/ajv@8.17.1/es2022/dist/2020.bundle.mjs` and `https://esm.sh/ajv-formats@3.0.1/es2022/dist/formats.bundle.mjs`. Both are self-contained — the vendor script refuses any build that still imports another module, because that would need an import map.
- `ajv-formats.mjs` is the **format table** (`fullFormats`), not the `addFormats` plugin: esm.sh keeps `ajv` external in the plugin build, so no self-contained version of it exists. `playground.html` registers the table with `ajv.addFormat` itself. Every `format` is asserted exactly as before; only the `formatMinimum`/`formatMaximum` keywords are lost, and `tools/validate.py`'s `jsonschema` does not implement those either — so the page and the CLI stay in step. Do not "fix" this back to `addFormats`.

**Updating any of the above**: run `uv run scripts/vendor_schemify_assets.py` in the skills repo (it re-discovers the file list, re-downloads, and rewrites `MANIFEST.sha256`), bump the versions named here, then rebuild the example package and check the playground still boots — both the interactive grid and, with `assets/vendor/data-table/assets/worker-*.js` removed, the static fallback. Existing packages pick the update up via `render.py refresh-assets`, which re-stamps `assets/VERSION`; rebuild their pages afterwards.
