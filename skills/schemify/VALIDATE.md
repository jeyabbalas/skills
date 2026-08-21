Validation is the package's unit test: toy data proving every rule both holds and catches. Read this when authoring or extending fixtures, or interpreting a run. The script's invocation, contract, and fallback ladder live in LAYOUT.md; the real-data rules in SKILL.md's gotchas govern everything here.

Table of contents

- [What a green run proves](#what-a-green-run-proves)
- [Toy fixtures](#toy-fixtures)
- [The violation ledger](#the-violation-ledger)
- [Running the validator](#running-the-validator)
- [Coverage and VARIABLES.csv](#coverage-and-variablescsv)
- [When a file you didn't touch fails](#when-a-file-you-didnt-touch-fails)
- [Real data](#real-data)

## What a green run proves

`validate.py summary` green means, and only means: every schema file parses and meta-validates under draft 2020-12; every `$ref` resolves; the `$id` policy holds; `toy_valid.json` yields **zero** findings; every seeded violation in `toy_invalid.json` is caught on exactly the column its ledger names; and `VARIABLES.csv` reconciles one-to-one with the schemas. Each clause is a different way a package rots; the summary checks them all so no session has to remember to.

## Toy fixtures

Toy rows are **authored, never sampled** — built from the dictionary's value space, so they are safe to commit, publish, and show. Three files (per table, under `examples/` — paths in LAYOUT.md): `toy_valid.json`, `toy_invalid.json`, `toy_invalid_ledger.json`.

**`toy_valid.json`** — 8–20 rows that must all pass. Author it base-row-plus-deltas: row 0 is one fully in-universe record with every column carrying a plausible substantive value; each later row copies it and changes the few columns that scenario needs. That is what keeps every row consistent with *all* the conditionals at once. Coverage is across rows, not per row — together the rows must contain:

- every sentinel of every variable, at least once;
- every level of every categorical with ≤ 12 levels; for larger code lists: first, last, one middle, and every sentinel level;
- for every continuous variable: the exact `minimum`, the exact `maximum`, one interior value, and each sentinel;
- **both halves of every skip pair**: one row with the trigger on and the skipped field pinned to its NA code, one row with the trigger off and the field carrying a substantive value — plus, somewhere, an in-universe row answering with an item-missing code (the pattern the applicability rule must *permit*);
- one canonical match for every `pattern`, including a leading-zero case where zeros matter.

Keys in schema property order; sentinels as literal in-band values (`-666`, not `null`).

**`toy_invalid.json`** — exactly one seeded violation per row, every other value legal (start from a valid row and break one thing). One ledger case per row.

## The violation ledger

`toy_invalid_ledger.json` is the ground truth the validator asserts against:

```json
{
  "$comment": "Ground truth for toy_invalid.json. Row indexes are 0-based array positions. One seeded violation per row; tools/validate.py fixtures asserts each row FAILS with an error pointer on the named column.",
  "rowIndexBase": 0,
  "violations": [
    { "row": 0, "column": "sleep_minutes", "kind": "range-break", "value": 1500, "reason": "above plausibility max 960" },
    { "row": 1, "column": "chronotype", "kind": "unknown-level", "value": 9, "reason": "9 is not a declared code" },
    { "row": 2, "column": "nap_minutes", "kind": "skip-break", "value": 45, "reason": "nap_yesterday=0 but a real duration is present (must be -666)" },
    { "row": 3, "column": "nap_minutes", "kind": "applicability-break", "value": -666, "reason": "nap_yesterday=1 but the structural-NA code is recorded" },
    { "row": 4, "column": "sleep_minutes", "kind": "invented-sentinel", "value": -999, "reason": "-999 is not a code this source defines" },
    { "row": 5, "column": "participant_id", "kind": "pattern-break", "value": "P12", "reason": "must match ^P[0-9]{4}$" },
    { "row": 6, "column": "site_id", "kind": "wrong-type", "value": 1, "reason": "site codes are strings with leading zeros" },
    { "row": 7, "column": "age", "kind": "missing-key", "reason": "column omitted — missingness must be in-band" },
    { "row": 8, "column": "shoe_size", "kind": "undeclared-column", "reason": "not in the dictionary; rejected by unevaluatedProperties" }
  ]
}
```

`kind`, `value`, and `reason` are documentation; the assertion matches on `row` + `column`. The kind vocabulary is fixed, one per construct the style emits: `wrong-type · unknown-level · range-break · invented-sentinel · pattern-break · skip-break · applicability-break · missing-key · undeclared-column` (plus `duplicate-row` where the package uses `uniqueItems`). Minimum bar: one case per kind the package's constructs use, and one `skip-break` plus one `applicability-break` **per conditional**. Past ~25 conditionals, cover each trigger-variable family once and say so in the ledger's `$comment`.

## Running the validator

EXECUTE it (contract and fallbacks in LAYOUT.md); read the JSON verdict — never eyeball schemas and declare them fine. After any schema edit, `check`; after fixture work, `fixtures`; before presenting or closing, `summary`. A red run is either fixed in this session or *is* the `next:` unit — the closing checklist accepts nothing in between.

Verdicts worth knowing on sight: `missed-passed` — the seeded row validated clean, so the rule it was meant to trip doesn't exist or doesn't fire (a skip missing its applicability twin, most often); `missed-wrong-column` — the row failed somewhere else, so the seed broke more than one thing or the ledger names the wrong column. Both mean the fixture and the schema disagree about the contract — settle which is right before touching either.

## Coverage and VARIABLES.csv

`VARIABLES.csv`, in the package root, is the inventory the coverage check reconciles against — written at intake, statuses flipped as conversion proceeds, kept after cleanup so the check runs for as long as the package lives.

```csv
variable,table,category,status,source,notes
participant_id,,participant,converted,"dictionary.csv row 2","pattern ^P[0-9]{4}$"
site_id,,participant,added,"steward interview 2026-08-21","link key; not in source dictionary"
melatonin_use,,sleep,deferred,"dictionary.csv row 14","source coding ambiguous — D012"
```

Fixed six-column header. `table` stays blank in single-table packages. `status` is one of `pending · converted · deferred · dropped · added`. The reconciliation: every `converted` row has its property in the named category file; every schema property has a row (`converted`, or `added` with its origin in `source`); `pending`, `deferred`, and `dropped` rows appear in no schema. Coverage green plus fixtures green is what "the schemas say what the dictionary says" means mechanically.

## When a file you didn't touch fails

The closing checklist guarantees every session ends green, so a red file you never opened means the package moved outside the sessions — a hand edit, another tool. Say so plainly, fix forward (never revert the steward's own edits without asking), and log what happened; if the hand edit reveals a preference — a renamed title, a loosened bound — treat it as steward input and ledger it.

## Real data

Toy fixtures are the unit test whether or not real data exists — confirm with the steward, but absence of real data blocks nothing. When real data does exist and its Conventions row permits reading: offer one `validate.py data` run at package-complete, report findings as counts per rule ("14 rows fail the nap routing"), quote nothing, and treat surprises as questions about the schema, not accusations about the data — an unexpected code in real data usually means the dictionary was incomplete, which is a finding for the ledger and possibly a new sentinel branch for the steward to confirm.
