The house rulebook for every schema file in `schemify/package/schemas/`. Read it whenever you are about to write or edit schema JSON. One deliberate style — every package validates the same way in `validate.py` and QuaC, renders the same way in the data dictionary, and parses the same way in downstream code. Skip logic and other conditionals have their own file, SKIP-LOGIC.md; `validate.py check` enforces both.

Table of contents

- [Codes get oneOf, measures get anyOf](#codes-get-oneof-measures-get-anyof)
- [Every file](#every-file)
- [The mother file](#the-mother-file)
- [Category files](#category-files)
- [Every property](#every-property)
- [x-provenance](#x-provenance)
- [Categorical variables](#categorical-variables)
- [Continuous variables](#continuous-variables)
- [Sentinels](#sentinels)
- [Strings, identifiers, dates](#strings-identifiers-dates)
- [Annotations](#annotations)
- [common/defs.json](#commondefsjson)
- [Keywords never used](#keywords-never-used)

## Codes get oneOf, measures get anyOf

The one distinction everything hangs off. A **coded** variable — categories with labels — is a `oneOf` of single-value `const` branches, each branch carrying its own `title`. A **measured** variable — a number with a plausible range — is an `anyOf` of one typed branch plus one branch per special code. Downstream tools read `oneOf` as "these are the levels" and `anyOf` as "a measurement, with special codes". Never blur them.

## Every file

- `"$schema": "https://json-schema.org/draft/2020-12/schema"` in every file.
- An absolute `$id` under the package's one base (`project.json` → `idBase`) whose path mirrors the file's path under `schemify/package/schemas/`:

  ```json
  "$id": "https://schemas.example.org/lark/sleep_diary/categories/sleep.json"
  ```
- Every `$ref` is relative: `"categories/sleep.json"` from a mother, `"../../common/defs.json#/$defs/dont_know"` from a category, `"#/$defs/…"` within a file. Never `$ref` an absolute URI.
- Formatting: 2-space indent, one key per line, trailing newline.

## The mother file

`<table>/<table>.schema.json` declares the table: an array whose every element is one row.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.example.org/lark/sleep_diary/sleep_diary.schema.json",
  "title": "LARK — Sleep diary",
  "description": "Array of diary records. One element is one participant-night.",
  "$comment": "Not enforceable here: participant_id + diary_date unique across rows (D011).",
  "type": "array",
  "minItems": 1,
  "items": {
    "type": "object",
    "title": "Sleep diary record",
    "allOf": [
      { "$ref": "categories/participant.json" },
      { "$ref": "categories/sleep.json" },
      { "$comment": "Skip pattern R001: …", "x-provenance": { "default": "S01:row 9" }, "if": { "…": "…" }, "then": { "…": "…" } }
    ],
    "unevaluatedProperties": false
  }
}
```

- The root carries `title`, a `description` that states the grain in the words the table's `grain` holds in `project.json` ("One element is one …"), an optional `$comment` naming what JSON Schema cannot enforce, `type: "array"`, and `minItems: 1`.
- `items` carries only `type`, `title`, `allOf`, and `unevaluatedProperties: false` — never `properties`, `required`, or `additionalProperties`. The row is the union of its categories.
- `allOf` order is a contract: category `$ref`s first, in `project.json` topic order, then every rule (SKIP-LOGIC.md). QuaC's findings name a rule only by its position (`/items/allOf/7/then/…`), and the website maps positions back to rule ids from the current schemas — so after reordering, findings from an earlier QuaC run no longer line up. Append new rules at the end.
- `uniqueItems` only when the steward confirms whole-row duplicates are errors (it compares entire rows; key uniqueness is not enforceable — say so in the root `$comment`).

## Category files

One file per topic, holding that topic's properties and nothing else:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.example.org/lark/sleep_diary/categories/sleep.json",
  "title": "Sleep",
  "description": "Nightly sleep quantity and disruptions from the morning diary.",
  "type": "object",
  "x-variable-group": "sleep",
  "properties": { "…": "…" },
  "required": ["sleep_minutes", "awakenings", "nap_yesterday", "nap_minutes"]
}
```

- `required` lists every property, in `properties` order: every column is present in every row; missingness is a code in the cell, never an absent key.
- Never `additionalProperties` (it would reject the other categories' columns), and never `if`/`then`, `allOf`, `anyOf`, or `dependentSchemas` at the category's top level: rules live in the mother. A rule inside a category makes QuaC report every column of that category as unexpected whenever any one of them fails.
- Every table repeats an identification category with its link keys, even when another table has the same.
- Repeated shapes (roster slots, `_2` variants) get one local `$defs` entry, `$ref`'d with a sibling `title` and `x-provenance` per use.
- Arithmetic that should hold but cannot be enforced goes in a top-level `"$comment": "Not enforceable: adult_count + child_count = household_size (D021)."` plus a `not-expressible` rule record.

## Every property

```json
"sleep_minutes": {
  "title": "Total sleep last night (minutes)",
  "$comment": "Source coding: minutes; -666 N/A (no diary entry); -888 DK.",
  "x-provenance": { "default": "S01:Variables row 6", "maximum": "D002" },
  "x-unit": "minutes",
  "anyOf": [
    { "type": "integer", "minimum": 0, "maximum": 960 },
    { "$ref": "../../common/defs.json#/$defs/not_applicable" },
    { "$ref": "../../common/defs.json#/$defs/dont_know" }
  ]
}
```

Key order: `title`, `description` (only when it says more than the title), `$comment`, `x-provenance`, other `x-*`, then the value schema. Every property has a `title` and an `x-provenance`; `check` rejects a property missing either.

## x-provenance

The core tenet, made checkable: every fact in a property or a rule traces to a source or a decision. `x-provenance` is an object from **facet** to a **reference** (or a list of them) in LEDGER-FORMAT.md's grammar — `S01:<locator>` or `D014`.

- `default` covers every facet not listed. Usually the variable's line in the dictionary: `{"default": "S01:Variables row 6"}`.
- List a facet only when its origin differs from `default`. Facets: `title`, `description`, `type`, `values` (the code list as a whole), `value:<code>` (one code, written as JSON: `value:777`, `value:"01"`), `sentinels` (which special codes the variable accepts, as a set — one code's meaning is its `value:<code>`; without this facet, `check` warns `sentinel-dropped` when the property rejects a special code its `default` row lists), `minimum`, `maximum`, `pattern`, `unit`, `universe`, `derivation`.
- Two sources agreeing: a list, `"value:777": ["S01:Codes row 41", "S02:p.6"]`. A person's answer that settled a facet is cited alone, even when a source agrees with it — the decision's evidence keeps the source.
- Every reference must resolve: a source that is not `suggested` or `rejected` (a `retired` one still counts), or a decision that is not cancelled (a superseded one draws a warning: cite its replacement). A guess cites the decision that records it (`"maximum": "D002"`, where D002 was recorded with `event: decide`) — that is how the website and the steward's review queue find it.
- Rules carry `x-provenance` too, beside their `$comment` (SKIP-LOGIC.md).
- `$comment`'s verbatim "Source coding: …" text is a reading aid; `x-provenance` is the authority.

## Categorical variables

A `oneOf` of single-value `const` branches, each with its own `title` — the code's label as the source states it (normalized wording is a `guess` decision; keep the source's words in `$comment`):

```json
"chronotype": {
  "title": "Self-described chronotype",
  "x-provenance": { "default": "S01:Variables row 4" },
  "oneOf": [
    { "const": 1, "title": "Morning lark" },
    { "const": 2, "title": "Night owl" },
    { "const": 3, "title": "Neither" },
    { "$ref": "../../common/defs.json#/$defs/dont_know" }
  ]
}
```

- Never a bare `enum` for labeled codes — an `enum` has nowhere to put the labels.
- Codes are integers unless leading zeros matter (`"01"`–`"05"`), then strings, `const` and all.
- Yes/no is categorical like any other: `0 No`, `1 Yes`, plus the source's missing codes.
- A code that means "no substantive answer" carries `"x-value-kind": "sentinel"` on its branch (or on the shared `$defs` entry it `$ref`s). The data dictionary files special codes by this keyword and otherwise guesses from wording and number — and guesses wrong for "Legitimate skip", "DK", any negative code, and "999 Other". So: every special code says `sentinel`, and a real answer says `"x-value-kind": "value"` whenever its label sounds like missingness ("None of the above", "Less than one", "Not stated") or its number is 666, 777, 888, 999, 6666, 7777, 8888, or 9999.
- Keep code titles at 60 characters or fewer — rule readings quote them.

## Continuous variables

An `anyOf`: one typed branch, then one branch per special code the source defines for this field.

- Bounds are plausibility bounds: reject the impossible, not the rare. The source's stated range wins; a bound you choose is a `guess` decision cited on the `minimum`/`maximum` facet.
- When a sentinel falls inside `[minimum, maximum]` (888 inside 0–2000), the typed branch adds `"not": { "enum": [888] }` — otherwise the sentinel silently counts as a measurement. Negative sentinels below `minimum: 0` need no guard.
- `type` is `integer` for counts and whole units, `number` only when the source has decimals. Only the typed branch carries `type`.
- A special code inside a measure is a `const` branch with a `title` and `x-value-kind` — inline or `$ref`'d.

## Sentinels

A sentinel is a reserved code meaning "no substantive value here": not applicable, refused, don't know, not collected.

- **Adopt the source's codes; never invent one.** A field the sources give no missing code gets no sentinel branch. A package-wide sentinel policy the sources lack is a `convention` decision a person answers before any schema uses it.
- **Structural vs item missingness.** A *structural* code means "skipped by design" (the target of skip rules); *item* codes (refused, don't know) stay legal everywhere. `project.json` → `conventions.sentinels` marks which codes are structural.
- **Invariant sentinels** (same code, same meaning everywhere) live once in `common/defs.json` and are `$ref`'d. **Context-dependent ones** (777 = "Nondrinker" here, "Nonparous" there) are inlined with the field's own label.
- String fields get string sentinels (`"NA"`, `"REFUSED"`).
- Collisions are documented, not fixed: when a real value could equal a sentinel, keep the sentinel, add `"$comment": "… Dictionary defect: 777 is also a possible value (D031)."`, and record the decision.
- Year-valued fields take the source's wide variants (`-6666`) so a sentinel never looks like a year.
- **Delivered blanks.** When a person confirms the data delivers empty cells for missing values and will not be recoded, the `convention` decision may adopt `null` as the missing code: a branch `{ "const": null, "title": "Missing (blank cell)", "x-value-kind": "sentinel" }`, used like any other sentinel. Never use `null` without that decision.

## Strings, identifiers, dates

- Identifiers: a fully anchored `pattern` (`^P[0-9]{4}$`), defined once in `common/defs.json` and `$ref`'d wherever the id appears.
- Dates and times: strings with an anchored `pattern` for the source's exact format — `^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$` for ISO dates — never `format` (most validators ignore it).
- Free text: bare `"type": "string"`; its sentinels, if the source defines any, are string branches.

## Annotations

Where each kind of text lives — each in exactly one place:

- `title` — the display label, on every property and every `const` branch.
- `description` — real content beyond the title: a definition, a caveat, a cross-table pointer, a derivation summary.
- `$comment` — provenance prose and caveats: the verbatim source coding, source typos in brackets (`[source: 'United Kingdon']`), dictionary defects, coding inversions.
- The `x-*` vocabulary — exactly these seven:
  - `x-provenance` (every property, every rule) — above.
  - `x-value-kind` (`"sentinel"` · `"value"`) — on code branches and shared code definitions.
  - `x-variable-group` (category root) — the topic id.
  - `x-unit` (property) — `"years"`, `"minutes"`, `"cm"`.
  - `x-universe` (property) — who the field applies to, in words: the human twin of the rule that enforces it.
  - `x-derivation` (property) — how a derived variable is computed, in words.
  - `x-role` (property) — `"primary key"`, `"entity key"`, `"time key"`, `"analysis weight"`, `"survey design"`, or `"derived measure"`.

## common/defs.json

Only invariant tokens: canonical sentinels (`const`, `title`, `description`, `x-value-kind`), anchored id and date patterns, a truly invariant yes/no — and nothing study-variable-specific. Every entry carries `x-provenance` like a property, and so does every entry of a file's own `$defs`: the definition holds its provenance, not each place that uses it.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.example.org/lark/common/defs.json",
  "title": "LARK — shared definitions",
  "$defs": {
    "not_applicable": {
      "const": -666,
      "title": "Not applicable (skipped by design)",
      "x-value-kind": "sentinel",
      "x-provenance": { "default": "S01:Notes row 2" }
    },
    "dont_know": {
      "const": -888,
      "title": "Don't know",
      "x-value-kind": "sentinel",
      "x-provenance": { "default": "S01:Notes row 2" }
    },
    "participant_id": {
      "type": "string",
      "pattern": "^P[0-9]{4}$",
      "title": "Participant identifier",
      "x-provenance": { "default": "S01:Variables row 1", "pattern": "D007" }
    }
  }
}
```

When in doubt, inline in the category; promotion to `common/` is cheap later.

## Keywords never used

| Keyword | Why not |
|---|---|
| `additionalProperties` | the mother's single `unevaluatedProperties: false` does this; on a category it rejects the other categories |
| `else`, `dependentRequired`, `dependentSchemas` | every rule is a one-directional `if`/`then` in the mother; the reverse direction is its own rule |
| `format` | not asserted by default validators — a silent no-op; use anchored `pattern` |
| `default`, `examples`, `deprecated`, `readOnly` | a data contract, not documentation of a writer; examples live in the toy data |
| `multipleOf`, `minLength`, `maxLength` | invite precision the source never stated |
| `$anchor`, `$dynamicRef` | relative paths plus `#/$defs/…` are the whole addressing scheme |
| `"type": "null"` | missingness is a declared code; `null` appears only as a `const` under a recorded convention |
