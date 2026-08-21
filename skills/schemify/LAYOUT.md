The package is the directory holding the schemas and everything that ships with them. This file is the tree of record: what lives where, what everything is named, and the contracts for the two bundled scripts. All package paths are relative to the package root.

Table of contents

- [The package tree](#the-package-tree)
- [Multi-package roots](#multi-package-roots)
- [Naming rules](#naming-rules)
- [Standing rules](#standing-rules)
- [Script contracts](#script-contracts)

## The package tree

A mid-flight package with one table (the same shape holds at four tables — more table directories, one playground page per table):

```
json_schema/                          ← package root (name agreed at intake)
├── README.md                         ← the deliverable's front door; finished at review (REVIEW.md)
├── manifest.json                     ← optional package card: counts, entrypoints, sentinel glossary
│                                       (never any JSON Schema keyword, so tools don't mistake it for a schema)
├── PROGRESS.md                       ← plan · statuses · session log (PROGRESS-FORMAT.md)
├── DECISIONS.md                      ← the judgment ledger (DECISIONS-FORMAT.md)
├── SOURCES.md                        ← provenance map (SOURCES-FORMAT.md)
├── VARIABLES.csv                     ← the variables inventory (format in VALIDATE.md); coverage ground truth
├── common/
│   └── defs.json                     ← shared $defs: invariant sentinels, id and date patterns
├── sleep_diary/                      ← one directory per table
│   ├── sleep_diary.schema.json       ← the mother file: array of row objects (SCHEMA-PATTERNS.md)
│   └── categories/
│       ├── participant.json          ← one file per category
│       └── sleep.json
├── examples/
│   ├── toy_valid.json                ← toy rows that must all pass (VALIDATE.md)
│   ├── toy_invalid.json              ← one seeded violation per row
│   └── toy_invalid_ledger.json       ← ground truth: which row breaks which column, and why
├── tools/
│   ├── validate.py                   ← copy of the skill's validator — the package validates itself forever
│   └── requirements.txt
├── dictionary.html                   ← searchable data dictionary; opens straight from disk (PAGES.md)
├── playground.html                   ← toy-data viewer + live validator; needs a local server (PAGES.md)
└── assets/
    ├── json-schema-data-dictionary.global.js   ← vendored rendering library (render.py init)
    ├── schema-pages.css                        ← the pages' stylesheet
    └── VERSION                                 ← hash stamp; render.py check flags drift
```

State files sit in the package root so the whole story travels together in version control. The state trio is scaffolding — the steward may clean it away at review; `VARIABLES.csv` is not scaffolding: it stays, so the coverage check runs for as long as the package lives.

## Multi-package roots

- One study → one package: `json_schema/` alone in the invocation directory.
- Several studies → sibling packages, each under its own study directory: `hesp/json_schema/`, `bcrpp/json_schema/`. Each package carries its own state trio, its own `common/defs.json`, its own pages — nothing is shared across packages, ever.
- Several *tables* of one study stay in one package as sibling table directories; they share `common/defs.json` and the state trio. A table is one flat grain; a second grain ("one row per person" vs "one row per visit") is a second table, not a second package.

## Naming rules

- **Package root**: `json_schema` unless the steward names it otherwise at intake.
- **Table directory and mother file**: the table's name, `snake_case` — `sleep_diary/sleep_diary.schema.json`. The `.schema.json` suffix marks mothers and only mothers; anything matching `*/*.schema.json` is a table root.
- **Category files**: `<table>/categories/<snake_case_category>.json` — no `.schema.json` suffix, ever. Category names come from the steward-approved category table, snake_cased. Every table gets its own `identification.json` (or equivalent) holding the link keys, even when that repeats another table's.
- **Fixtures**: `examples/toy_valid.json`, `examples/toy_invalid.json`, `examples/toy_invalid_ledger.json`; with several tables, `examples/<table>/` holds each table's trio.
- **Pages**: `dictionary.html` (always one, all tables stacked); `playground.html`, or `playground-<table>.html` per table when there are several.
- **$id base**: one absolute, non-dereferenceable URI base per package, mirroring on-disk paths — rules in SCHEMA-PATTERNS.md; the chosen base is a Conventions row in PROGRESS.md.

## Standing rules

- **Create lazily.** `render.py init` makes only `assets/` and `tools/`; every other directory appears the first time something is written into it. Never scaffold empty structure ahead of need.
- **The package must stand alone.** A consumer with the package and Python can validate (`tools/validate.py`), browse (`dictionary.html`), and read the rules (README.md) without this skill installed. Nothing in the package may reference the skill's install directory — `render.py check` enforces this.
- **Pages are renders.** Regenerate them with `render.py`; never hand-edit an `.html` — the edit dies at the next render.
- **Scripts refuse to write into the skill directory**, and everything they write lands inside the package you name.

## Script contracts

`<skill-dir>` below means this skill's own directory — the directory this file was loaded from. Always EXECUTE these scripts (never read them); they print JSON to stdout, exit 0 only on success, and every failure carries a `hint` naming the next move.

**Fallback ladder** (applies to both; `render.py` is stdlib-only — plain `python3` always works for it):

1. `uv run <skill-dir>/scripts/<script>.py …` — preferred; uv resolves dependencies.
2. No uv → `python3 -m pip install --user "jsonschema>=4.18" referencing`, then `python3 <skill-dir>/scripts/<script>.py …`. The package copy runs the same way: `python3 tools/validate.py …` after `pip install -r tools/requirements.txt`.
3. Neither → drafting may continue, but no category may reach `validated` and the debt goes in the session log — skipping validation is not a fallback.

| Script | Use |
|---|---|
| `validate.py check PKG` | Every schema file parses and meta-validates against draft 2020-12; the `$id` policy is linted (one base, path-mirroring — warnings name the fix); every `$ref` in every file resolves. Run after any schema edit. |
| `validate.py data PKG --file F [--table T] [--format json\|csv] [--max-errors N]` | Validate a data file (JSON array of objects, or CSV with in-band sentinel literals) against a table's mother schema. Findings carry row, column, message, a hint — and, when a routing rule fired, that conditional's own `$comment` text. `--table` required when the package has several. |
| `validate.py fixtures PKG [--table T]` | The unit test: `toy_valid` must yield zero findings; every `toy_invalid` row must fail with an error on exactly the column its ledger names. Per-row verdicts (`caught`, `missed-passed`, `missed-wrong-column`) with hints; ledger and data must match one-to-one. |
| `validate.py coverage PKG [--inventory PATH]` | Reconcile `VARIABLES.csv` against the schemas: every `converted` row has its property, every property has its row (`converted` or `added`), `deferred`/`dropped`/`pending` rows appear in no schema. |
| `validate.py summary PKG` | check + fixtures + coverage in one rollup, with a one-line `headline` fit to relay to the steward. Missing fixtures or inventory are reported as skipped, not failed. |
| `render.py init PKG` | Create `assets/` and `tools/` — the vendored dictionary library, the stylesheet, the validator copy, `requirements.txt` — and stamp `assets/VERSION`. Idempotent; reports when the package's copies are older than the skill's. |
| `render.py refresh-assets PKG` | Overwrite the shipped copies from the skill and re-stamp VERSION — upgrades the package's whole executable surface at once. Re-render pages afterwards if it says templates changed. |
| `render.py dictionary PKG [--title T]` | Build `dictionary.html` from every schema file in the package. The page opens straight from disk. |
| `render.py playground PKG [--table T]` | Build the playground page(s), schemas and toy fixtures inlined. Without `--table`, builds every table that has a mother file. |
| `render.py check PKG` | Lint the built surface: asset freshness against the skill, page staleness (each page fingerprints its inputs), inline data parses, no absolute-path or skill-directory references. Run before closing any session that touched schemas or pages. |
