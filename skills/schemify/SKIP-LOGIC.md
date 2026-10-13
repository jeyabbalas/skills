Skip patterns and other conditional logic: how to find them, what licenses each one, when to ask before inferring, how to record them, and the one canonical JSON form every rule takes. Read this before drafting any topic, whenever you notice a rule or a hint of one, when answers about rules come back, and for the skip-logic audit. Rule records are LEDGER-FORMAT.md's; the domain catalog of where rules hide and which ones epidemiological data carries is SKIP-LOGIC-CATALOG.md's.

Table of contents

- [Why this gets its own file](#why-this-gets-its-own-file)
- [Finding rules](#finding-rules)
- [Reading questionnaires](#reading-questionnaires)
- [Evidence and what it licenses](#evidence-and-what-it-licenses)
- [Asking before inferring](#asking-before-inferring)
- [Recording rules](#recording-rules)
- [The canonical form](#the-canonical-form)
- [Skip pairs](#skip-pairs)
- [Other rule shapes](#other-rule-shapes)
- [Rules inside nested values](#rules-inside-nested-values)
- [Fields left out](#fields-left-out)
- [What cannot be a rule](#what-cannot-be-a-rule)
- [Fixtures for every rule](#fixtures-for-every-rule)
- [The skip-logic audit](#the-skip-logic-audit)

## Why this gets its own file

Questionnaire data lives on skip logic, dictionaries seldom state it, and downstream tools parse it from the schemas. So: hunt for it in every source and every topic, never invent it, ask before inferring it, and write every rule in exactly one shape.

## Finding rules

Every source is scanned at discovery — the digests do it (SUBAGENTS.md, the digest brief's section 4) — and every topic's slice again before drafting. Signals, strongest first (the full graded table is SKIP-LOGIC-CATALOG.md's):

- **Stated routing**: "asked only if", "if yes", "skip to", "go to Q12", "→", "universe:", "for those who", a REDCap `Branching Logic` or XLSForm `relevant` column, DDI `<universe>`.
- **Not-applicable labels**: "not applicable", "legitimate skip", "inapplicable", "not asked", "N/A (never smoker)" — a parenthetical names the universe.
- **Questionnaire structure** (next section): arrows, boxed instructions, indented follow-ups, sex- or age-specific sections.
- **Variable shape**: gate-and-detail pairs (`ever_` beside `age_`, `num_`, `_per_day`, `_specify`), roster slots with a count, "other, specify" pairs, checkbox groups with a "none" member, wave suffixes beside a participation flag — and the same pairs among the fields of a list's entries (each visit, each household member).

Register what you find the moment it has a table (Recording rules, below) — before the plan, the digest holds it. A rule is cheap to record and expensive to forget.

## Reading questionnaires

A questionnaire may hold skip logic the dictionary never mentions, explicitly or only in its layout. It is not automatically more reliable than the dictionary: after collection, cleaning and recoding may have changed what the data holds, and the dictionary usually describes the data as delivered. Read it for **who was asked**, and read the dictionary (or ask) for **what sits in the cell** for someone who was not.

- Read layout-bearing pages as pages, not as extracted text: arrows, boxes, and indentation vanish in text extraction. View the PDF page or image directly when your harness can; a Word questionnaire's extract has lost its layout — ask the user for a PDF when routing may hang on it.
- Explicit routing: "If NO, go to Q20", "Skip to Section D", "Women only", "Interviewer: ask if…". This is `documented` evidence — quote it and cite the page and question number.
- Implicit routing on the page: an indented or boxed follow-up under a yes/no item, an arrow, numbering that jumps, a section header naming a subgroup. This is `implied` evidence — cite the page and say what in the layout implies it.
- Wording alone is not layout. A question that only makes sense for one answer ("Age at your first live birth" after "How many live births?") with nothing on the page routing it is a belief: `inferred` — ask first.
- Map question numbers to variable names before encoding; a rule whose variables you cannot map is a `gap` question, not a guess.
- When the questionnaire and the dictionary disagree — different universe, different codes for skipped respondents, a recode note — record a `conflict` decision with both quotes and ask (QUESTIONS.md). Never pick a side silently.

## Evidence and what it licenses

| evidence | what it is | licenses |
|---|---|---|
| `documented` | a source states the rule (dictionary, questionnaire, protocol, cleaning code, approved web source) | encode; `x-provenance` cites the statement |
| `implied` | a source implies it without stating it: an N/A label naming who, a title "among current smokers", questionnaire layout. A generic label ("legitimate skip") says some routing exists, not which gate: the gate is implied only when layout or another source shows it | encode; cite the implying text; ask for confirmation in the topic's batch ("encoded from the label — say no to remove it") |
| `told` | a person said so (a `rule` or `knowledge` decision) | encode; cite the decision |
| `inferred` | nothing documents it; you believe it from the study design, variable names, or domain knowledge | **ask first** (next section); encode only after a yes, cited to your own `guess` decision so it stays flagged for review |

Every rule also needs its delivered representation: the code a skipped respondent carries. For a source-traced rule, if nothing says which code — or whether skipped cells are blank — that is a `gap` question, and the rule waits. For an inferred rule, the consent question names the code you believe skipped cells hold (usually the dictionary's not-applicable code), so one yes settles both; a person who knows otherwise says so under *Something else*. Codes the study treats as structural are listed in `project.json` → `conventions.sentinels`; a code not listed there needs a `convention` question in the same batch before any pair can use it.

## Asking before inferring

When you believe rules exist that no source documents:

1. Record each as a rule — `evidence: inferred`, `status: suspected`, `refs` to what made you think so, and a `reading` saying exactly what you would enforce: both halves of the pair, and the code skipped cells hold. Nothing goes into the schemas yet — no conditional, no `x-universe`, no `$comment` hinting at it. Valid toy rows stay consistent with the belief; no invalid row tests it until it is encoded.
2. Check `project.json` → `preferences.inferRules`:
   - `ask` (the default): the topic's batch (BUILD.md, step 6) carries one `consent` question for the topic's suspected rules: `covers` their R ids, `targets` their variables, the rules listed in plain words in `context`, `provisional: "later"`, and these options with these ids —
     - `known`: "Yes — I know this is how it was done"
     - `yes`: "Yes — include them, each marked for review by the data steward"
     - `later`: "Not now — keep them listed for later"
     - `no`: "No — only rules my documents state"
     - `always`: "Yes, and from now on infer such rules without asking"

     Recommend `yes` when the study's design or a strong pattern in SKIP-LOGIC-CATALOG.md supports the rules; otherwise recommend `later`.
   - `yes`: encode them now, citing the decision that set the preference as `consent`.
   - `no`: record them `declined`, citing that decision in `consent`; they stay listed for the steward's review.
3. On the answer, for each rule it covers:
   - `yes` or `always`: record your `guess` decision (`event: decide`, `kind: rule`, review needed) saying why you believe it; encode both halves, cited to that decision; add fixtures; `set` the rule `encoded` with `consent` (the consent decision) and `decision` (the guess); `apply` both decisions. `always` also sets `inferRules: yes` in `project.json`.
   - `known`: the person vouches for it — encode it cited to the consent decision; `set` the rule `encoded` with `evidence: told` and `decision` (the consent decision); no guess, no flag.
   - `later`, or "not sure": `deferred`. `no`: `declined`. Either `set` cites the consent decision in `consent`. A person may accept some and not others (*Something else*); split accordingly.

A deferred rule is not put to the same person again; it waits in the steward's review (REVIEW-MODE.md) and stays listed in the package README. Inferred rules remain flagged for review — the website and the README list them as "inferred by the agent, not yet confirmed" — until a person confirms each rule's `guess` decision.

## Recording rules

- Record a rule as soon as you notice it and it has a table, gate seen or detail seen, even when its variables are not drafted yet: `status: waiting` for a documented, implied, or told rule, `suspected` for an inferred one, with `waits_for` naming the variables not yet in a schema. A rule already recorded is updated with `set`, never added twice.
- Both ends must be properties of the **same table, in the same row** — or fields of the same group or the same list entry ([Rules inside nested values](#rules-inside-nested-values)). A gate in another table, another row (a previous wave in a long file), another entry of a list, or a variable never delivered makes the rule `not-expressible` — README material, not schema. Gates and targets inside nested values are named by their paths (`household[].relation`, NESTED.md).
- When both ends exist: `documented`, `implied`, and `told` rules are encoded in the same session (or become the `next:` step); `inferred` ones follow the consent step.
- Every encoded rule's id appears in its conditional's `$comment`; `check` reconciles ledger and schemas both ways.

## The canonical form

Every rule is one entry of its mother's `items.allOf`, after the category `$ref`s, with exactly these four keys:

```json
{
  "$comment": "Skip pattern R004: never smokers (smk_ever = 2) were not asked how many cigarettes they smoke. Questionnaire p.6 Q14: 'If NO, go to Q20'.",
  "x-provenance": { "default": "S02:p.6 Q14", "value:777": "S01:Codes row 41" },
  "if": {
    "required": ["smk_ever"],
    "properties": { "smk_ever": { "const": 2 } }
  },
  "then": {
    "properties": { "cigs_per_day": { "const": 777 } }
  }
}
```

**`$comment`** — `<Kind> R<NNN>: <plain reading>. <Provenance sentence>.` Kind is `Skip pattern` (pins the structural code, or leaves the field out), `Applicability` (forbids it, or requires the field), or `<Domain> routing` (anything else: `Smoking routing`, `Reproductive routing`). The provenance sentence quotes the source, cites the person's decision, or — for an inferred rule — says "Inferred by the agent (D041); not stated in any source; confirm with the data steward." A rule you cannot state plainly is a rule you do not understand yet.

**`if`** — one clause, or `{"anyOf": [clause, clause, …]}` for "any of these". A clause is `{"required": [gates…], "properties": {gate: test, …}}` with every tested gate in both — `required` keeps a missing gate from satisfying the condition vacuously. Several gates in one clause all must hold. A gate in `required` with no test is a presence test, for a field the data may leave out ([Fields left out](#fields-left-out)); `{"required": [gates…]}` alone is a clause of them. A test is one of:

| test | means |
|---|---|
| `{"const": v}` | gate equals v |
| `{"enum": [v1, v2]}` | gate is any of these |
| `{"not": {"const": v}}` / `{"not": {"enum": […]}}` | gate is anything but these ("other, specify") |
| `{"contains": {"const": v}}` / `{"not": {"contains": {"const": v}}}` | a list-of-values gate includes v / does not include v ("if Fever is among the symptoms") |
| `{"type": "integer", "minimum": a, "maximum": b, "not": {"enum": [sentinels]}}` | gate in a numeric range — exclude every sentinel that could fall inside it; `exclusiveMinimum`/`exclusiveMaximum` allowed |

**`then`** — `{"properties": {target: effect, …}}`, one or more targets, and `"required": [targets…]` beside it or alone for targets that must be present ([Fields left out](#fields-left-out)); or, for "at least one of these must hold", `{"anyOf": [{"required": [t], "properties": {t: effect}}, …]}`, where `{"required": [t]}` alone means t is present. An effect is one of:

| effect | means | comment kind |
|---|---|---|
| `{"const": c}` with c the structural code | target was skipped | `Skip pattern` |
| `{"not": {"const": c}}` | target was asked: no structural code | `Applicability` |
| `{"const": v}` with v substantive (0, a date), or a merged missing code a source routes there | target pinned to that value — no twin | `<Domain> routing` |
| `{"not": {"const": v}}` with v an item-missing code or `null` | target never holds v here ("the participant's own line always gives an age") | `<Domain> routing` |
| `{"enum": [levels…, item-missing codes…]}` | target narrowed to some levels | `<Domain> routing` |
| `{"anyOf": [{"type": …, "minimum": …, "maximum": …}, sentinel branches…]}` | measure narrowed to a sub-range; the typed branch carries `"not": {"enum": [codes]}` when a special code falls inside it | `<Domain> routing` |
| `{"maxItems": n}` / `{"minItems": n}`, or both | a list target holds at most / at least n entries — `{"maxItems": 0}`: empty; `{"minItems": 1}`: not empty | `<Domain> routing` |
| `false` | target is left out (a field the data may leave out) | `Skip pattern`, or `<Domain> routing` |

A gate or a target may also be a field of a group, reached from the record: the test or effect on the group is itself a clause — `{"required": ["consent"], "properties": {"consent": {"required": ["data_sharing"], "properties": {"data_sharing": {"const": false}}}}}` tests `consent.data_sharing`, and `"then": {"properties": {"consent": {"properties": {"recontact": {"const": -666}}}}}` pins `consent.recontact` (`{"consent": {"required": ["recontact"]}}` there requires it). Groups only: never into a list.

Nothing else: no `else`, no nested `if`, no `allOf` inside `if` or `then`, no `false` except as an effect, no conditionals in category files except among one nested value's own fields ([Rules inside nested values](#rules-inside-nested-values)), no `$ref` inside a rule except to sentinel definitions in a narrowed effect. `validate.py check` rejects other shapes, so every consumer can parse every package with one small grammar; `validate.py rules` prints the parsed form.

## Skip pairs

One routing fact, two enforced directions, one id:

```json
{
  "$comment": "Skip pattern R001: no nap yesterday means nap duration is not applicable. Dictionary row 9: 'Asked only if nap_yesterday=1'.",
  "x-provenance": { "default": "S01:Variables row 9" },
  "if": { "required": ["nap_yesterday"], "properties": { "nap_yesterday": { "const": 0 } } },
  "then": { "properties": { "nap_minutes": { "const": -666 } } }
},
{
  "$comment": "Applicability R001: a reported nap has a duration or an item-missing code, never the not-applicable code.",
  "x-provenance": { "default": "S01:Variables row 9" },
  "if": { "required": ["nap_yesterday"], "properties": { "nap_yesterday": { "const": 1 } } },
  "then": { "properties": { "nap_minutes": { "not": { "const": -666 } } } }
}
```

- The applicability half forbids the structural code — never demands a substantive value. In-universe respondents may still refuse or not know; a `then` that demands a real number outlaws honest missingness.
- Build the applicability half whenever the source states or implies the universe; when the source states only one direction, the twin is still sound (it is the same fact read the other way) and rides the same `x-provenance` — unless skipped cells hold a merged missing code (one code for skipped, refused, and unknown): the source's direction is then a one-way `<Domain> routing` pin, with no twin (SKIP-LOGIC-CATALOG.md, "Sentinel families").
- A gate whose own answer can be missing (DK, refused) appears in neither half's `if` for those codes — what a skipped-gate respondent's targets hold is a question for the source or a person.
- A code added to a gate later (an answer, a new release) is in neither half until a person says where its people go: one question (kind `rule`) per rule on that gate, recommending what the routing text says read literally ("women only (A2 = 2)": everyone else skips), with the rule as it stands as `provisional`. Their answer is evidence for the new code, cited in the rule's `refs` and `x-provenance` — no consent question.
- Stacked gates (`sex` → `mammogram_ever` → `mammogram_age`): one pair per gate on its direct targets. Rows with the outer gate off carry the structural code in the inner gate, so the inner pair never fires on them.

## Other rule shapes

- **Substantive pin** — "never smokers carry 0 cigarettes per day": `then` pins a real value, prefix `<Domain> routing`, no applicability twin (a former smoker may honestly report 0). Licensed only when a source or a person states the value.
- **Narrowing** — "school-age children use enrollment codes 3–6": a `then` enum that keeps every item-missing code. A `then` enum is the one place a bare `enum` is allowed — the labels live on the field's own `oneOf`.
- **At least one** — "any cancer = yes means at least one site flag is yes": the `then.anyOf` form.
- **Implication** — "current smoker means ever smoker = yes": a pin on another categorical. Encode only the directions a source or a person supports.
- **Sentinel as trigger** — "if X was not asked, Y was not asked": the `if` test is the structural code.

## Rules inside nested values

Questionnaires route inside repeated sections too: "If the visit was not fasting, skip the glucose draw" holds for each visit; "Ask age only if the person is not the participant" holds for each household member. Where a rule lives depends on where its gate and its targets are (NESTED.md names them):

- **Among one entry's fields, or one group's** — both ends in the same entry of a list, or in the same group: the rule lives inside that object, in its own `allOf` — a list's `items.allOf`, a group's `allOf` — and nowhere else, so it holds for every entry separately. It takes exactly the canonical form above, with the object's own field names (`relation`, not `household[].relation`); its id is an ordinary R id, unique in the table, recorded with paths as gates and targets (`household[].relation` → `household[].age`):

  ```json
  "items": {
    "type": "object",
    "properties": { "fasting": { "…": "…" }, "glucose": { "…": "…" } },
    "required": ["fasting", "glucose"],
    "additionalProperties": false,
    "allOf": [
      {
        "$comment": "Skip pattern R012: a visit without fasting has no glucose draw (fasting = 0). Visit form Q7: 'If not fasting, skip to Q9'.",
        "x-provenance": { "default": "S02:p.3 Q7" },
        "if": { "required": ["fasting"], "properties": { "fasting": { "const": 0 } } },
        "then": { "properties": { "glucose": { "const": -666 } } }
      }
    ]
  }
  ```
- **A record-level gate and a whole nested value** — "no medications taken (`meds_any = 2`) means no medication list": an ordinary rule in the mother, targeting the list as one variable. Its effect is what the data delivers for someone not asked (NESTED.md): a special code (`{"const": -666}`, with its applicability twin `{"not": {"const": -666}}`), `null` under the blank-cell convention, the variable left out ([Fields left out](#fields-left-out)), or an empty list — `{"maxItems": 0}`, a `<Domain> routing` rule. An empty list that also means "asked, none" gets no twin; one that only ever means "not asked" may take `{"minItems": 1}` the other way, when a source or a person says every asked record has an entry.
- **A choose-many gate** — "if Fever is among the symptoms, the fever's duration applies": the test is `{"contains": {"const": 1}}` (and `{"not": {"contains": {"const": 1}}}` for the skip half). A code that stands alone ("none of these", "not collected") is a rule on the list itself: if it includes the code, `{"maxItems": 1}`.
- **A record-level rule and a field of a group** — reach into the group with a nested clause (The canonical form). A record-level rule never reaches into a list's entries: a rule about each entry lives in the entry.

A rule inside a nested value is appended to the end of that object's `allOf` and never reordered — its position is a contract, like the mother's. `validate.py rules` prints its `scope` (`household[]`, `address`); the data dictionary reads it as "… in the same item". A shape shared by several variables through `$ref` holds no rules: write it inline in each.

## Fields left out

A JSON delivery may leave a field out of its record, group, or entry instead of writing a code — only under a person's `convention` decision, cited on the field's `required` facet (SCHEMA-STYLE.md, "Nested values"). Rules about such a field say whether it is there:

```json
{
  "$comment": "Skip pattern R014: the participant's own line leaves the age out (relation = 1). Roster instructions p.2: 'Age: other members only'.",
  "x-provenance": { "default": "S02:p.2" },
  "if": { "required": ["relation"], "properties": { "relation": { "const": 1 } } },
  "then": { "properties": { "age": false } }
},
{
  "$comment": "Applicability R014: every other member's line gives an age.",
  "x-provenance": { "default": "S02:p.2" },
  "if": { "required": ["relation"], "properties": { "relation": { "enum": [2, 3] } } },
  "then": { "required": ["age"] }
}
```

- **Skip pattern**: a skipped field is left out, `false`. **Applicability**: an asked field is there, named in `then`'s `required` — only when the data leaves the field out *only* when it was not asked. When a missing answer is left out too, requiring the field outlaws honest missingness: write no applicability half (NESTED.md asks which, "What a missing value looks like inside").
- **A presence gate** — "when a medication note is given …": the gate in the clause's `required`, with no test. Absence cannot be tested; state such a rule the other way round ("a note only for those on medication": if the note is present, `on_meds` is 1).
- A value effect on such a field (`{"not": {"const": -888}}`) holds only when the field is there; name it in `required` too when the rule also demands it. So a variable with a coded pair whose field may also be left out keeps one pair: its applicability half says both, `"then": {"required": ["death_year"], "properties": {"death_year": {"not": {"const": 777}}}}`. A presence rule with no skip half to pair with is `<Domain> routing`.

Presence tests and effects name only fields the data may leave out — `validate.py check` rejects one on a field its object always holds, which takes the coded pair instead. The data dictionary reads them as "value is absent", "value must be present", and "When meds_note is present". Fixtures as for any rule: valid rows on each side of the gate, and invalid rows that give a skipped field (`skip-break`) or leave out an asked one (`applicability-break`), ledgered on the field.

## What cannot be a rule

Arithmetic (pack-years, sums), date or age ordering across fields, a range that depends on another numeric field, uniqueness across rows, anything across tables or rows, a free-text gate: record the rule `not-expressible`, add a line to the mother's root `$comment`, and the package README lists it under "documented but not enforced" (FINISH.md). Inside nested values the same holds for a gate in one entry and a target in another ("if a child is listed, the participant's own entry …"), a gate inside a list's entries with a target outside them ("any visit while fasting → …"), and counts of entries that depend on another field ("as many entries as `n_children`" — a fixed count for one gate value is a rule: `{"minItems": 2, "maxItems": 2}`). What a list must hold whatever else is true ("the roster lists the participant exactly once") is no rule but the list's own `contains` (SCHEMA-STYLE.md, "Nested values"); nor is anything the shape states by itself — a field a group or a branch of a mixed value requires ("email is required when contact is a record" is that branch's `required`), a field every entry holds. Cite its source on the shape's own facets and record no rule.

## Fixtures for every rule

Every encoded rule id ships with toy rows (DATA-CHECK.md): in `valid.json`, at least one row where the rule fires and is satisfied — for a pair, one row on each side of the gate, plus one in-universe row carrying an item-missing code; in `invalid.json`, one row per half that breaks it, ledgered with kind `skip-break`, `applicability-break`, or `routing-break` and a reason naming the id. A rule inside a nested value fires entry by entry: a valid row's list holds an entry on each side of the gate, and an invalid row breaks it in one entry, ledgered on the target's path (`visits[].glucose`). `validate.py fixtures` reports any rule that never fired.

## The skip-logic audit

Run once every topic is confirmed (`status` proposes it), and again after any late rule change:

1. `uv run <skill-dir>/scripts/validate.py rules schemify/package` — every rule parses; read the list once, top to bottom, as a reader would.
2. `schemify.py check` shows no `waiting` rule whose variables now exist, every `encoded` rule fixtured, and no conditional without a ledger rule.
3. Every property and nested field whose value set includes a structural code is a target of some rule — or of a rule record (any status), or of a `rule` decision saying why not. `check` warns `structural-unruled` for each straggler.
4. Every `suspected` rule has been put to a person (asked, deferred, or declined) — none sit unasked.
5. Rebuild, and tell the user the Skip logic page is complete for their review.
