Routing, encoded: what to write when the dictionary says a variable is "asked only if", states a universe, or describes skip logic. Survey data lives on these rules; a cohort extract may have none — in which case this file never loads. Sentinel encoding itself is SCHEMA-PATTERNS.md's; this file owns how sentinels and conditionals interact.

Table of contents

- [Where conditionals live](#where-conditionals-live)
- [The $comment contract](#the-comment-contract)
- [Trigger forms](#trigger-forms)
- [Write skips in pairs](#write-skips-in-pairs)
- [Narrowing without strangling](#narrowing-without-strangling)
- [Compound consequences](#compound-consequences)
- [From prose to pattern](#from-prose-to-pattern)
- [Fixture duty](#fixture-duty)

## Where conditionals live

Every conditional is an entry of the mother file's `items.allOf`, after the category `$ref`s, shaped exactly:

```json
{
  "$comment": "Skip pattern: no nap yesterday means nap duration is structurally not applicable.",
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

Every conditional carries a `$comment` — no exceptions; the bundled validator surfaces it as the human explanation whenever the rule fires, and the playground shows it to the steward beside the failing cell. It begins with a controlled prefix and names trigger and consequence in plain words:

- `Skip pattern:` — out-of-universe fields pinned to their structural-NA code.
- `Applicability:` — in-universe fields forbidden from carrying that code.
- `<Domain> routing:` — anything richer (`Housing routing: renters answer the rent block; owners the mortgage block.`).

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

## Write skips in pairs

One routing fact, two enforced directions. The **skip** half pins the out-of-universe value; the **applicability** half forbids it in-universe:

```json
{
  "$comment": "Skip pattern: no nap yesterday means nap duration is structurally not applicable.",
  "if": { "required": ["nap_yesterday"], "properties": { "nap_yesterday": { "const": 0 } } },
  "then": { "properties": { "nap_minutes": { "const": -666 } } }
},
{
  "$comment": "Applicability: a reported nap must have a duration or an item-missing code — never the structural-NA code.",
  "if": { "required": ["nap_yesterday"], "properties": { "nap_yesterday": { "const": 1 } } },
  "then": { "properties": { "nap_minutes": { "not": { "const": -666 } } } }
}
```

The applicability half asserts `not: { "const": <NA code> }` — **never a substantive value**. An in-universe respondent may still refuse or not know; item-missing codes stay legal everywhere. A `then` that demands a real number outlaws honest missingness — the single most common routing-encoding mistake.

When the trigger itself is a sentinel ("if X was not asked, Y was not asked either"), the same shape holds: the trigger `const` is the sentinel code.

## Narrowing without strangling

A `then` may narrow an in-universe field's allowed levels — school-age children get school categories — but the narrowed set keeps every item-missing code and excludes only the structural NA:

```json
{
  "$comment": "Diary routing: school-age children use enrollment categories 3-6.",
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

## From prose to pattern

Dictionaries state routing three ways, and each has a required response:

- **Quoted routing** — "Asked only if Q3 = 1": encode the pair directly; the `$comment` may quote the source.
- **A universe statement** — "Universe: current smokers": encode the pair against the variable that defines the universe, and give the property its `x-universe` prose twin (SCHEMA-PATTERNS.md) so page readers see it without reading conditionals.
- **A pattern you noticed** — every nonsmoker carries -666 in three columns, but the dictionary never says so: that is an *inferred* skip. Encode it, log it `agent-decided` with the evidence as the why, and put it in the steward's next batch — inference confirmed is documentation recovered; inference unconfirmed is an invention wearing a schema.

The universe's defining variable must exist in the package. Routing that hangs on something the source never delivered ("asked only in phase 2 sites") becomes a `not-enforceable` ledger line and README material instead.

## Fixture duty

Every conditional ships with its PASS/FAIL fixture pair — a row proving each half holds and a seeded row proving each half catches its violation. What those rows look like, and the ledger that binds them: VALIDATE.md.
