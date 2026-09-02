Provenance for the files in this directory. `schema-pages.css`, `embed-worker.js`, and `schemify-mark.svg` are authored in this repository (the first two are copied into packages by `render.py`; the mark is inlined into every page at build time, never copied). The library below is vendored verbatim.

## json-schema-data-dictionary.global.js

- Package: [`json-schema-data-dictionary`](https://www.npmjs.com/package/json-schema-data-dictionary) v0.2.0 — IIFE build (`dist/json-schema-data-dictionary.global.js`), global `JsonSchemaDataDictionary`.
- Source: <https://github.com/jeyabbalas/json-schema-to-data-dictionary> (MIT). Fetched byte-identical from `https://cdn.jsdelivr.net/npm/json-schema-data-dictionary@0.2.0/dist/json-schema-data-dictionary.global.js`.
- sha256: `1bf66c4c259703bc603570caa08c44168c00dbc7f9a6f4d2ddf12af50c069c74`
- Never hand-edit this file — verify it against the npm dist when in doubt.
- What the pages use from the global: `schemaDocumentsToTable`, `renderDataDictionary` (light DOM, options re-set per mount), and for semantic search `createWorkerEmbedder`, `createTransformersEmbedder`, `serveEmbedder`, `createIndexedDbVectorCache`. The embedding runtime is deliberately not vendored: `dictionary.html` loads Transformers.js 4.2.0 from cdn.jsdelivr.net and the model `Xenova/bge-small-en-v1.5` from huggingface.co only when the steward switches semantic search on.

**Updating**: download the new version's `dist/json-schema-data-dictionary.global.js`, replace the file, update the version and sha256 above, confirm the exports named above are still on the global, and check that the selectors `schema-pages.css` relies on still exist in the build — print: `.dd-category[data-collapsed]`, `.dd-table-wrap`, `.dd-toolbar`, `.dd-actions`, `.dd-row`, `.dd-category-desc`, `.dd-badge`, `.dd-cond-badge`; layout: `.dd-title`, `.dd-header`, `.dd-table`, `.dd-col-name`. Existing packages pick the update up via `render.py refresh-assets`, which re-stamps `assets/VERSION`; rebuild their pages afterwards.
