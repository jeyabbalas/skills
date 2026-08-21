The house rulebook: how every schema file in the package is written. Read this whenever you are about to write or edit schema JSON. It encodes one deliberate style — proven on real survey and cohort packages — so that every package this skill produces validates the same way, renders the same way, and reads the same way. Conditionals and routing have their own file: SKIP-PATTERNS.md. Where files live and what they are named: LAYOUT.md.

Table of contents

- [Codes get oneOf, measures get anyOf](#codes-get-oneof-measures-get-anyof)
- [Every file](#every-file)
- [The mother file](#the-mother-file)
- [Category files](#category-files)
- [Categorical variables](#categorical-variables)
- [Continuous variables](#continuous-variables)
- [Sentinels](#sentinels)
- [Strings, identifiers, dates](#strings-identifiers-dates)
- [Annotations](#annotations)
- [common/defs.json](#commondefsjson)
- [Keywords never used](#keywords-never-used)

## Codes get oneOf, measures get anyOf

The one distinction everything below hangs off. A **coded** variable — categories with labels — is a `oneOf` of single-value `const` branches, each branch carrying its own `title`. A **measured** variable — a number with a plausible range — is an `anyOf` of one numeric branch plus one branch per sentinel code. The combinator *is* the declaration: downstream tools read `oneOf` as "these are the levels" and `anyOf` as "a measurement, with special codes". Never blur it.

## Every file

- `"$schema": "https://json-schema.org/draft/2020-12/schema"` in **every** file — mothers, categories, `common/defs.json`.
- Every file gets an absolute `$id` under **one** package base whose path mirrors the on-disk path exactly:

  ```json
  "$id": "https://schemas.example.org/lark/sleep_diary/categories/sleep.json"
  ```

  The base is deliberately non-dereferenceable — nothing fetches it; it exists so `$ref` resolution is unambiguous. Record it as a Conventions row, and note in the package README that a publisher should replace the namespace before publishing. Never mix two bases in one package: tools that resolve strictly by `$id` break the moment `common/defs.json` lives under a different base than the file referencing it.
- All `$ref`s are **relative paths**: `"categories/sleep.json"` from a mother, `"../../common/defs.json#/$defs/dont_know"` from a category file, `"#/$defs/…"` within a file. Never `$ref` an absolute `$id` URI.
- Formatting: 2-space indent, fully expanded — one key per line, even for `const` branches — trailing newline. One title-separator character package-wide (`—` or `-`), chosen once.

## The mother file

The mother file (`<table>/<table>.schema.json`) declares the table: an array whose every element is one row.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.example.org/lark/sleep_diary/sleep_diary.schema.json",
  "title": "LARK — SLEEP_DIARY table",
  "description": "Array of diary records. One element is one participant-night. Structurally skipped values remain as reserved sentinel codes so the dataset stays rectangular; the routing rules are enforced below.",
  "$comment": "Standard JSON Schema cannot enforce uniqueness of participant_id + diary_date across rows or arithmetic identities between columns. See the README's 'Documented but not enforced' section.",
  "type": "array",
  "minItems": 1,
  "uniqueItems": true,
  "items": {
    "type": "object",
    "title": "SLEEP_DIARY record",
    "allOf": [
      { "$ref": "categories/participant.json" },
      { "$ref": "categories/sleep.json" },

      { "$comment": "Skip pattern: …", "if": { "…": "…" }, "then": { "…": "…" } }
    ],
    "unevaluatedProperties": false
  }
}
```

- The root carries `title`, a `description` that states the grain ("One element is one …" — the interview's exact answer), an optional `$comment` naming what JSON Schema cannot enforce, `type: "array"`, `minItems: 1`, `uniqueItems: true`.
- `items` carries **only** `type`, `title` (`"<TABLE> record"`), `allOf`, and `unevaluatedProperties: false`. Never `properties`, `required`, or `additionalProperties` at the row level: the row is the union of its categories, and a category file that closed itself would reject every other category's columns under `allOf`.
- `allOf` order is a contract: category `$ref`s first, in the steward-approved reading order, then every conditional (SKIP-PATTERNS.md). Validators attribute a conditional's errors by its position in this array — reorder it and every attribution shifts.
- `unevaluatedProperties: false` is the package's only unknown-column rejection, stated exactly once, here.

## Category files

One file per steward-approved category, holding that category's properties and nothing else.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.example.org/lark/sleep_diary/categories/sleep.json",
  "title": "SLEEP_DIARY — Sleep",
  "description": "Nightly sleep quantity and disruptions from the morning diary.",
  "type": "object",
  "x-variable-group": "sleep",
  "properties": { "…": "…" },
  "required": ["sleep_minutes", "awakenings", "nap_yesterday", "nap_minutes"]
}
```

- `required` lists **every** property in the file, in `properties` order. Every column is present in every row — missingness lives in-band as sentinel codes, never as an absent key. Never set `additionalProperties`.
- Never put `if`/`then` in a category file — conditionals live in the mother so error attribution works (SKIP-PATTERNS.md).
- Every table repeats an identification category holding its link keys, even when that duplicates a sibling table's — each table must stand alone.
- Repeated shapes — roster slots, `*_2nd` variants — get one local `$defs` entry, `$ref`'d with a sibling `title` (and `$comment` where codes differ) overriding per use:

  ```json
  "age_child2": {
    "$ref": "#/$defs/child_age",
    "title": "Age of second child (years)",
    "$comment": "-666 - N/A (fewer than 2 children)."
  }
  ```
- Arithmetic that should hold within the category but cannot be enforced goes in one trailing top-level `$comment`, a sibling of `required`: `"Soft checks: adult_count + child_count should equal household_size."` The convert loop also logs it `not-enforceable`.

## Categorical variables

A `oneOf` of single-value `const` branches, each with its own `title` — the code's label, exactly as the source states it (normalized per Annotations, source wording kept in `$comment`).

```json
"chronotype": {
  "title": "Self-described chronotype",
  "oneOf": [
    { "const": 1, "title": "Morning lark" },
    { "const": 2, "title": "Night owl" },
    { "const": 3, "title": "Neither" },
    { "$ref": "../../common/defs.json#/$defs/dont_know" }
  ]
}
```

- Never a bare `enum` for labeled categories — an `enum` has nowhere to put the labels, and the rendered dictionary would show naked numbers.
- Codes are integers unless leading zeros are significant — site `"01"`–`"05"`, a study code `"07"` — then they are strings, `const` and all, so no tool can strip the zero.
- Yes/no is a categorical like any other: `{ "const": 0, "title": "No" }`, `{ "const": 1, "title": "Yes" }`, plus whatever missing codes the source defines. A shared shape can live in `common/defs.json` when codes and meanings are truly invariant.

## Continuous variables

An `anyOf`: one numeric branch, then one branch per sentinel the source defines for this field.

```json
"sleep_minutes": {
  "title": "Total sleep last night (minutes)",
  "anyOf": [
    {
      "type": "integer",
      "minimum": 0,
      "maximum": 960,
      "not": { "enum": [-666, -888] }
    },
    { "$ref": "../../common/defs.json#/$defs/not_applicable" },
    { "$ref": "../../common/defs.json#/$defs/dont_know" }
  ]
}
```

- Bounds are **plausibility** bounds: reject the impossible, not the merely rare. The source's stated range wins when it has one; when it doesn't, a bound you choose is an `agent-decided` ledger line ("rejects the impossible, not the rare" is the why). Say so in the README's conventions section too.
- The `not: { "enum": […] }` on the numeric branch exists **only when** a sentinel falls inside `[minimum, maximum]` — negative sentinels below a `minimum: 0` need no guard; positive sentinels like 888 inside a 0–2000 range do. Without the guard, a sentinel would satisfy the numeric branch and its meaning would silently vanish.
- `type` is `integer` for counts and coded amounts, `number` only when the source has decimals. The numeric branch is the only branch that carries `type` — `const` branches never do.

## Sentinels

A sentinel is a reserved code meaning "no substantive value here" — not applicable, refused, don't know, not collected. The rules:

- **Adopt the source's codes; never invent one.** A field the dictionary gives no missing code gets no sentinel branch — inventing one falsifies the data contract. If the source has no codes at all and needs them, that is an interview decision (INTAKE.md), recorded before any schema uses it.
- A sentinel is always a **single-value `const` branch** inside the field's `oneOf`/`anyOf` — never a type union, never `null`, never an absent key.
- **Invariant sentinels** — same code, same meaning everywhere — live once in `common/defs.json` and are `$ref`'d. **Context-dependent sentinels** — same code, meaning shifts per field — are inlined with the field's own label:

  ```json
  { "const": 777, "title": "Nondrinker" }
  ```

  is right in an alcohol-cessation field, while 777 means "Nonparous" two categories away. The per-field `title` is the meaning; the shared def would erase it.
- **String-valued fields get string sentinels** (`"NA"`, `"REFUSED"`, `"DONT_KNOW"`), with a `description` saying why: the substantive value is a string, so the codes are too.
- **Collisions are documented, not fixed.** When a real value could equal a sentinel (a 777 cm² area in a field where 777 means N/A), keep the sentinel, flag it — `"$comment": "… Dictionary defect."` — log it, and list it in the README's known-issues section. The schema tells the truth about the data, defect included.
- Year-valued fields take the source's wide sentinel variants (`-6666` beside `-666`) so a sentinel can never look like a year.

## Strings, identifiers, dates

- Identifiers get a fully anchored `pattern` — `^…$`, always — defined once in `common/defs.json` and `$ref`'d everywhere the id appears:

  ```json
  "participant_id": {
    "type": "string",
    "pattern": "^P[0-9]{4}$",
    "title": "Participant identifier"
  }
  ```

  A pattern can carry the source's own whitelist — `"^(0[1-9]|1[0-2])_"` says "sites 01–12" more enforceably than prose.
- Dates are strings with an anchored pattern for the source's exact format — `^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$` for ISO, `^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/[0-9]{4}$` for DD/MM/YYYY — never `format: "date"`. The pattern states which impossible strings are rejected; calendar-day validity beyond it is an application-level check, and the `description` says so.
- Free text is a bare `type: "string"`. If the source defines sentinels for it, they are string sentinel branches; if it doesn't, say in `$comment` what an empty answer looks like in the delivered data.

## Annotations

Where every kind of prose lives — each in exactly one place:

- **`title`** — the display label. On every property (short noun phrase; units in parentheses if the package's convention puts them there) and on every `const` branch (the code's label). This is what the rendered dictionary shows.
- **`description`** — only when there is real semantic content beyond the title: a cross-table pointer ("See COHORT_METADATA.pa_mets_def for the derivation"), a definitional caveat, "provide when X = 5 (Other)". Never a restatement of the title.
- **`$comment`** — provenance and caveats, machine-irrelevant, steward-invisible on pages: the verbatim source coding text (`"Source coding: 1 - Morning lark; 2 - Night owl; -888 - DK."`), source typos preserved in brackets with the correction in `title`, coding inversions relative to sibling tables, dictionary defects.
- **The `x-*` vocabulary** — exactly these five, no others:
  - `x-variable-group` (category file root): the category's snake_case name.
  - `x-role` (property): `"primary key"`, `"entity key"`, `"time key"`, `"analysis weight"`, `"survey design"`, `"derived measure"`.
  - `x-unit` (property): `"years"`, `"minutes"`, `"cm"` — when the package's convention is machine-readable units rather than title parentheticals; pick one convention at intake and hold it.
  - `x-universe` (property): prose stating who the field applies to — "Participants who reported a nap." — the human twin of the routing conditional that enforces it (SKIP-PATTERNS.md).
  - `x-derivation` (property): how a derived measure is computed, in words.

## common/defs.json

Only invariant tokens live here — things whose code *and* meaning never shift between fields:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.example.org/lark/common/defs.json",
  "title": "LARK — shared definitions",
  "description": "Only invariant tokens are centralised here; context-specific sentinels are inlined per field because their meanings differ by variable.",
  "$defs": {
    "not_applicable": {
      "const": -666,
      "title": "Not applicable / structural skip",
      "description": "The routing determined that the variable was outside the respondent universe."
    },
    "dont_know": {
      "const": -888,
      "title": "Don't know",
      "description": "The respondent did not know the value or it could not be determined."
    },
    "participant_id": {
      "type": "string",
      "pattern": "^P[0-9]{4}$",
      "title": "Participant identifier"
    }
  }
}
```

Canonical sentinels (const + title + description), anchored id patterns, date patterns, a truly invariant yes/no — and nothing study-variable-specific. When in doubt, inline it in the category; promotion to `common/` is cheap later, demotion is a hunt.

## Keywords never used

The style's deliberate absences — each with the reason, so nobody "improves" one back in:

| Keyword | Why not |
|---|---|
| `additionalProperties` | the mother's single `unevaluatedProperties: false` does this job; on a category file it would reject the other categories |
| `else` | every routing rule is a one-directional `if`/`then`; the reverse direction is its own paired rule (SKIP-PATTERNS.md) |
| `dependentRequired` / `dependentSchemas` | all columns are always required; conditionals constrain values, and `if`/`then` keeps them attributable |
| `format` | not asserted by default validators — a silent no-op; dates and ids use anchored `pattern` |
| `default` / `examples` / `deprecated` / `readOnly` | this is a data contract, not documentation of a writer; examples live in `examples/toy_valid.json` |
| `multipleOf`, `minLength` / `maxLength` | plausibility bounds and patterns carry the real rules; these invite false precision the source never stated |
| `$anchor` / `$dynamicRef` | relative file paths + `#/$defs/…` pointers are the whole addressing scheme; nothing dynamic |
| `null` type | missingness lives in-band as sentinel codes; a `null` is an undocumented hole |
