Routing, encoded: what to write once a rule is licensed — stated or implied by a source, or confirmed by the steward. Which is which, the register, and the proposals are ROUTING.md's; this file owns only the JSON. Survey data lives on these rules; a cohort extract may have none — in which case this file never loads. Sentinel encoding itself is SCHEMA-PATTERNS.md's; this file owns how sentinels and conditionals interact.

Table of contents

- [Where conditionals live](#where-conditionals-live)
- [The $comment contract](#the-comment-contract)
- [Trigger forms](#trigger-forms)
- [Write skips in pairs](#write-skips-in-pairs)
- [Substantive pins](#substantive-pins)
- [Narrowing without strangling](#narrowing-without-strangling)
- [Compound consequences](#compound-consequences)
- [What arrives here](#what-arrives-here)
- [Fixture duty](#fixture-duty)

## Where conditionals live

Every conditional is an entry of the mother file's `items.allOf`, after the category `$ref`s, shaped exactly:

```json
{
  "$comment": "Skip pattern R001: no nap yesterday means nap duration is structurally not applicable.",
  "if": {
    "required": ["nap_yesterday"],
    "properties": { "nap_yesterday": { "const": 0 } }
  },
  "then": {
    "properties": { "nap_minutes": { "const": -666 } }
  }
}
```

`{ "$comment", "if", "then" }` — three keys, no more. No `else` (the reverse direction is its own rule, below), no `dependentSchemas`, and never a conditional inside a category file: validators attribute a conditional's errors by its `allOf` position in the mother, and a rule hidden behind a category `$ref` loses its address.

## The $comment contract

Every conditional carries a `$comment` — no exceptions; the bundled validator surfaces it as the human explanation whenever the rule fires, and the playground shows it to the steward beside the failing cell. It begins with a controlled prefix, then the rule's register id (ROUTING-FORMAT.md), then trigger and consequence in plain words — `Skip pattern R012: …`, `Applicability R012: …`, `<Domain> routing R012: …`:

- `Skip pattern:` — out-of-universe fields pinned to their structural-NA code.
- `Applicability:` — in-universe fields forbidden from carrying that code.
- `<Domain> routing:` — anything richer (`Housing routing: renters answer the rent block; owners the mortgage block.`).

Both halves of a pair share one id; the routing check reconciles register and mother by it. Provenance closes the comment: a quoted rule quotes the source ("Asked only if Q3 = 1"); an implied rule quotes the text that implies it ("777 - N/A (never smoker)"); a steward-confirmed rule cites its ledger line (D031).

A conditional whose `$comment` you cannot write plainly is a conditional you do not understand yet — back to the source or the steward.

## Trigger forms

`if` **always** pairs `required` with `properties`:

```json
"if": {
  "required": ["nap_yesterday"],
  "properties": { "nap_yesterday": { "const": 1 } }
}
```

Without `required`, a row missing the trigger column satisfies the `if` vacuously and the `then` fires on garbage. With it, an absent trigger fails `required` at the category level instead, where it belongs.

Trigger forms, plainest first — use the earliest that says what the source says:

- `{ "const": v }` — one triggering code.
- `{ "enum": [v1, v2] }` — any of a few codes.
- `{ "type": "integer", "minimum": a, "maximum": b }` — a range trigger. A range that could capture a sentinel **must** exclude them — `"not": { "enum": [-666, -888] }` inside the trigger — or a sentinel-coded row (sentinels are numbers too) spuriously fires the rule.
- `"if": { "anyOf": [ …guarded branches… ] }` — "any of these happened": each branch its own `{ "required", "properties" }`.
- `{ "not": { "const": v } }` — everyone but code v ("other, specify": anyone who did not answer *Other*; migration: anyone not born in the study country), still under `required`.
- Several conditions that must all hold — "women aged 40 and over": every trigger property in one `if.properties`, all of them in `required`. "Any of" is the `anyOf` form; never mix the two in one rule.

## Write skips in pairs

One routing fact, two enforced directions. The **skip** half pins the out-of-universe value; the **applicability** half forbids it in-universe:

```json
{
  "$comment": "Skip pattern R001: no nap yesterday means nap duration is structurally not applicable.",
  "if": { "required": ["nap_yesterday"], "properties": { "nap_yesterday": { "const": 0 } } },
  "then": { "properties": { "nap_minutes": { "const": -666 } } }
},
{
  "$comment": "Applicability R001: a reported nap must have a duration or an item-missing code — never the structural-NA code.",
  "if": { "required": ["nap_yesterday"], "properties": { "nap_yesterday": { "const": 1 } } },
  "then": { "properties": { "nap_minutes": { "not": { "const": -666 } } } }
}
```

The applicability half asserts `not: { "const": <NA code> }` — **never a substantive value**. An in-universe respondent may still refuse or not know; item-missing codes stay legal everywhere. A `then` that demands a real number outlaws honest missingness — the single most common routing-encoding mistake.

When the trigger itself is a sentinel ("if X was not asked, Y was not asked either"), the same shape holds: the trigger `const` is the sentinel code. String-valued targets pin to their string sentinel (`"NA"`) in the same `const` shape.

## Substantive pins

Sometimes the out-of-universe value is a real number, not a code — never smokers carry `cigs_per_day` = 0. That is a pin: `"then": { "properties": { "cigs_per_day": { "const": 0 } } }`, prefix `<Domain> routing`, licensed only when the source or the steward states the value (ROUTING.md). A pin has **no applicability twin** — `not: { "const": 0 }` for smokers would outlaw an honest zero; the reverse direction exists only if the steward states it, as its own rule. The target's `$comment` says the value doubles as out-of-universe, and the pin's violation kind is `routing-break` (VALIDATE.md).

## Narrowing without strangling

A `then` may narrow an in-universe field's allowed levels — school-age children get school categories — but the narrowed set keeps every item-missing code and excludes only the structural NA:

```json
{
  "$comment": "Diary routing R004: school-age children use enrollment categories 3-6.",
  "if": {
    "required": ["child_age"],
    "properties": { "child_age": { "type": "integer", "minimum": 5, "maximum": 17 } }
  },
  "then": {
    "properties": { "school_status": { "enum": [3, 4, 5, 6, -777, -888] } }
  }
}
```

A `then`-side `enum` is the one licensed exception to "never a bare enum" — the labels already live on the field's own `oneOf`; the `enum` here only narrows. Year-valued fields pinned by a `then` take the wide year sentinel (`-6666`), matching the field's own branches.

A range that depends on a categorical — "at least one pregnancy when `ever_pregnant` = 1" — narrows the numeric branch the same way, keeping the item-missing codes legal:

```json
"then": {
  "properties": {
    "num_pregnancies": {
      "anyOf": [
        { "type": "integer", "minimum": 1, "maximum": 20 },
        { "$ref": "../../common/defs.json#/$defs/dont_know" }
      ]
    }
  }
}
```

## Compound consequences

A trigger with several consequences lists them all in one `then.properties`. A consequence that is an *existence* claim — "at least one account type must be owned" — joins value pins under `then.allOf`:

```json
"then": {
  "allOf": [
    {
      "anyOf": [
        { "properties": { "has_checking": { "const": 1 } }, "required": ["has_checking"] },
        { "properties": { "has_savings": { "const": 1 } }, "required": ["has_savings"] }
      ]
    },
    {
      "properties": { "unbanked_reason": { "const": -666 } }
    }
  ]
}
```

If a rule wants more nesting than this, it is probably two rules — split it and give each its own `$comment`.

## What arrives here

A rule is written only when its evidence licenses it (ROUTING.md), and each kind arrives with its own duty:

- **Quoted routing** — "Asked only if Q3 = 1": encode the pair; the `$comment` quotes the source. One `agent-decided` line covers the pair — the applicability half is your construction.
- **Implied routing** — an NA label naming its universe ("777 - N/A (never smoker)"), a title "among current smokers", a universe column: encode the pair against the variable that defines the universe, quote the implying text in the `$comment`, give the property its `x-universe` prose twin (SCHEMA-PATTERNS.md) so page readers see it without reading conditionals, and log it `agent-decided` with the text as the why. It rides the category's confirmation.
- **A rule you expect** — every nonsmoker plausibly carries -666 in three columns, but no source says so: not encoded, here or anywhere. It is a proposal (ROUTING.md) and reaches this file only after the steward's yes, when their ledger line is its provenance and the `$comment` cites it. Counts from real data strengthen the question; they never license the rule.

The universe's defining variable must be delivered by the source, in the same table and the same row. Not yet converted → the rule waits in the register; never delivered ("asked only in phase 2 sites"), another table, or another row → a `not-enforceable` ledger line, a register row, and README material instead.

## Fixture duty

Every rule id ships with its PASS/FAIL fixtures — a row proving each half holds and a seeded row proving each half catches its violation; both halves of a pair, one `routing-break` for a twinless pin or narrowing. What those rows look like, and the ledger that binds them: VALIDATE.md.
