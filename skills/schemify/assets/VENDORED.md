Provenance for third-party files shipped in this directory. `schema-pages.css` is authored in this repository; everything below is vendored verbatim.

## json-schema-data-dictionary.global.js

- Package: [`json-schema-data-dictionary`](https://www.npmjs.com/package/json-schema-data-dictionary) v0.1.0 — IIFE build (`dist/json-schema-data-dictionary.global.js`), global `JsonSchemaDataDictionary`.
- Source: <https://github.com/jeyabbalas/json-schema-to-data-dictionary> (MIT). Fetched byte-identical from `https://cdn.jsdelivr.net/npm/json-schema-data-dictionary@0.1.0/dist/json-schema-data-dictionary.global.js`.
- sha256: `a41ac00cb8020c5d2e97a34c92c354ff0bc700fca8329c63216b72f108bc1a57`
- Never hand-edit this file — verify it against the npm dist when in doubt.

**Updating**: download the new version's `dist/json-schema-data-dictionary.global.js`, replace the file, update the version and sha256 above, and check that the print selectors in `schema-pages.css` (`.dd-category[data-collapsed]`, `.dd-table-wrap`, `.dd-toolbar`, `.dd-actions`) still exist in the build. Existing packages pick the update up via `render.py refresh-assets`, which re-stamps `assets/VERSION`.
