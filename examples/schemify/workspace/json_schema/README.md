# LARK sleep-diary study — JSON Schema package

## What this package describes

LARK is a (synthetic) two-week community sleep-diary study: adults at five recruitment sites fill in a morning diary about the night before. This package encodes the study's data dictionary as machine-checkable JSON Schema (draft 2020-12).

| table | mother file | one row is | categories |
|---|---|---|---|
| `sleep_diary` | `sleep_diary/sleep_diary.schema.json` | one participant-night | participant, sleep |

## Layout and composition

```
common/defs.json                      shared definitions: sentinels, id and date patterns
sleep_diary/sleep_diary.schema.json   the table: an array of row objects
sleep_diary/categories/*.json         one file per category; a row is their union
examples/                             toy PASS/FAIL fixtures + ground-truth ledger
tools/validate.py                     standalone validator (see below)
dictionary.html · playground.html     browsable renders of the schemas
VARIABLES.csv                         source-variable inventory for the coverage check
```

A row is the `allOf` union of the category files. Unknown columns are rejected by the single `"unevaluatedProperties": false` on the mother file's row object — category files never close themselves, or they would reject each other's columns.

## Value-encoding conventions

- Coded variables are a `oneOf` of `const` branches, each carrying its label as `title`. Measured variables are an `anyOf` of one bounded numeric branch plus one branch per sentinel.
- Numeric bounds are plausibility bounds — they reject the impossible, not the merely rare. Bounds the source did not state are recorded as decisions (D005, D006).
- Site codes are strings so leading zeros survive ("01"–"05").
- Dates and times use fully anchored `pattern`s, never `format`.
- Every column is required in every row; missingness is in-band via sentinel codes.

## Sentinel semantics

| code | meaning | applies to |
|---|---|---|
| `-666` | Not applicable / structural skip | fields with routing (`sleep_minutes`, `nap_minutes`) |
| `-888` | Don't know | every field the source gives the code to |

No other missing codes exist in this source, and none were invented.

## Enforced routing rules

Derived from the mother file's conditionals (each rule's `$comment` is shown by the validator and the playground when it fires):

1. Skip pattern: no nap yesterday means nap duration is structurally not applicable.
2. Applicability: a reported nap must have a duration or an item-missing code — never the structural-NA code.

## Documented but not enforced

Rules the source states (or good practice demands) that JSON Schema cannot express — check them downstream:

- `participant_id` + `diary_date` must be unique across rows (D011). The schema's `uniqueItems` only rejects fully identical records.
- `sleep_minutes` should not exceed the bedtime-to-wake interval reported in the full diary (D012).

## Known source issues handled

- The dictionary's Coding column mixes substantive codes and missing codes in one cell ("1=Morning lark; …; -888=Don't know"); they are parsed apart into labeled `oneOf` branches and sentinel branches.
- The bedtime format was stated only as "hh:mm 24-hour clock"; the steward confirmed zero-padded times, so the anchored pattern is stricter than the prose (D009).

## Sources and provenance

- `source/dictionary.csv` — the study's data dictionary (11 variables), the primary source.
- Sleep diary questionnaire (steward-provided PDF, consulted 2026-08-21) — confirms the nap routing and the bedtime format.
- Steward interview (2026-08-21) — grain, sentinel policy, category approval, the site list (`site_id` is added, not in the source dictionary).

## Validating and browsing

```
pip install -r tools/requirements.txt      # or use: uv run tools/validate.py …
python3 tools/validate.py summary .        # schemas, fixtures, coverage — everything
python3 tools/validate.py data . --file your_export.csv
```

Browse: double-click `dictionary.html` (works offline, prints well; keyword search built in, and a Semantic search switch that fetches a small model once to find related variables by meaning). For the live validator, run `python3 -m http.server 8000` in this directory and open `http://localhost:8000/playground.html` — files you drop in are validated entirely in your browser.

The `$id` namespace `https://schemas.example.org/lark/` is a deliberate placeholder — replace it before publishing these schemas anywhere public.

## Open items to confirm with the data provider

- `melatonin_use` (dictionary row 11) is deferred: the supplement coding sheet is missing from this version of the dictionary (D013). It has a `VARIABLES.csv` row but no schema property until the codes arrive.
