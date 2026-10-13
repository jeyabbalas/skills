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
- **Variable shape**: gate-and-detail pairs (`ever_` beside `age_`, `num_`, `_per_day`, `_specify`), roster slots with a count, "other, specify" pairs, checkbox groups with a "none" member, wave suffixes beside a participation flag.

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
   - `no`: record them `declined`, citing that decision; they stay listed for the steward's review.
3. On the answer, for each rule it covers:
   - `yes` or `always`: record your `guess` decision (`event: decide`, `kind: rule`, review needed) saying why you believe it; encode both halves, cited to that decision; add fixtures; `set` the rule `encoded` with `consent` (the consent decision) and `decision` (the guess); `apply` both decisions. `always` also sets `inferRules: yes` in `project.json`.
   - `known`: the person vouches for it — encode it cited to the consent decision; `set` the rule `encoded` with `evidence: told` and `decision` (the consent decision); no guess, no flag.
   - `later`, or "not sure": `deferred`. `no`: `declined`. A person may accept some and not others (*Something else*); split accordingly.

A deferred rule is not put to the same person again; it waits in the steward's review (REVIEW-MODE.md) and stays listed in the package README. Inferred rules remain flagged for review — the website and the README list them as "inferred by the agent, not yet confirmed" — until a person confirms each rule's `guess` decision.

## Recording rules

- Record a rule as soon as you notice it and it has a table, gate seen or detail seen, even when its variables are not drafted yet: `status: waiting` for a documented, implied, or told rule, `suspected` for an inferred one, with `waits_for` naming the variables not yet in a schema. A rule already recorded is updated with `set`, never added twice.
- Both ends must be properties of the **same table, in the same row**. A gate in another table, another row (a previous wave in a long file), or a variable never delivered makes the rule `not-expressible` — README material, not schema.
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

**`$comment`** — `<Kind> R<NNN>: <plain reading>. <Provenance sentence>.` Kind is `Skip pattern` (pins the structural code), `Applicability` (forbids it), or `<Domain> routing` (anything else: `Smoking routing`, `Reproductive routing`). The provenance sentence quotes the source, cites the person's decision, or — for an inferred rule — says "Inferred by the agent (D041); not stated in any source; confirm with the data steward." A rule you cannot state plainly is a rule you do not understand yet.

**`if`** — one clause, or `{"anyOf": [clause, clause, …]}` for "any of these". A clause is `{"required": [gates…], "properties": {gate: test, …}}` with the same names in both — `required` keeps a missing gate from satisfying the condition vacuously. Several gates in one clause all must hold. A test is one of:

| test | means |
|---|---|
| `{"const": v}` | gate equals v |
| `{"enum": [v1, v2]}` | gate is any of these |
| `{"not": {"const": v}}` / `{"not": {"enum": […]}}` | gate is anything but these ("other, specify") |
| `{"type": "integer", "minimum": a, "maximum": b, "not": {"enum": [sentinels]}}` | gate in a numeric range — exclude every sentinel that could fall inside it; `exclusiveMinimum`/`exclusiveMaximum` allowed |

**`then`** — `{"properties": {target: effect, …}}`, one or more targets; or, for "at least one of these must hold", `{"anyOf": [{"required": [t], "properties": {t: effect}}, …]}`. An effect is one of:

| effect | means | comment kind |
|---|---|---|
| `{"const": c}` with c the structural code | target was skipped | `Skip pattern` |
| `{"not": {"const": c}}` | target was asked: no structural code | `Applicability` |
| `{"const": v}` with v substantive (0, a date) | target pinned to a real value | `<Domain> routing` |
| `{"enum": [levels…, item-missing codes…]}` | target narrowed to some levels | `<Domain> routing` |
| `{"anyOf": [{"type": …, "minimum": …, "maximum": …}, sentinel branches…]}` | measure narrowed to a sub-range; the typed branch carries `"not": {"enum": [codes]}` when a special code falls inside it | `<Domain> routing` |

Nothing else: no `else`, no nested `if`, no `allOf` inside `if` or `then`, no conditionals in category files, no `$ref` inside a rule except to sentinel definitions in a narrowed effect. `validate.py check` rejects other shapes, so every consumer can parse every package with one small grammar; `validate.py rules` prints the parsed form.

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
- Build the applicability half whenever the source states or implies the universe; when the source states only one direction, the twin is still sound (it is the same fact read the other way) and rides the same `x-provenance`.
- A gate whose own answer can be missing (DK, refused) appears in neither half's `if` for those codes — what a skipped-gate respondent's targets hold is a question for the source or a person.
- A code added to a gate later (an answer, a new release) is in neither half until a person says where its people go: one question (kind `rule`) per rule on that gate, recommending what the routing text says read literally ("women only (A2 = 2)": everyone else skips), with the rule as it stands as `provisional`. Their answer is evidence for the new code, cited in the rule's `refs` and `x-provenance` — no consent question.
- Stacked gates (`sex` → `mammogram_ever` → `mammogram_age`): one pair per gate on its direct targets. Rows with the outer gate off carry the structural code in the inner gate, so the inner pair never fires on them.

## Other rule shapes

- **Substantive pin** — "never smokers carry 0 cigarettes per day": `then` pins a real value, prefix `<Domain> routing`, no applicability twin (a former smoker may honestly report 0). Licensed only when a source or a person states the value.
- **Narrowing** — "school-age children use enrollment codes 3–6": a `then` enum that keeps every item-missing code. A `then` enum is the one place a bare `enum` is allowed — the labels live on the field's own `oneOf`.
- **At least one** — "any cancer = yes means at least one site flag is yes": the `then.anyOf` form.
- **Implication** — "current smoker means ever smoker = yes": a pin on another categorical. Encode only the directions a source or a person supports.
- **Sentinel as trigger** — "if X was not asked, Y was not asked": the `if` test is the structural code.

## What cannot be a rule

Arithmetic (pack-years, sums), date or age ordering across fields, a range that depends on another numeric field, uniqueness across rows, anything across tables or rows, a free-text gate: record the rule `not-expressible`, add a line to the mother's root `$comment`, and the package README lists it under "documented but not enforced" (FINISH.md).

## Fixtures for every rule

Every encoded rule id ships with toy rows (DATA-CHECK.md): in `valid.json`, at least one row where the rule fires and is satisfied — for a pair, one row on each side of the gate, plus one in-universe row carrying an item-missing code; in `invalid.json`, one row per half that breaks it, ledgered with kind `skip-break`, `applicability-break`, or `routing-break` and a reason naming the id. `validate.py fixtures` reports any rule that never fired.

## The skip-logic audit

Run once every topic is confirmed (`status` proposes it), and again after any late rule change:

1. `uv run <skill-dir>/scripts/validate.py rules schemify/package` — every rule parses; read the list once, top to bottom, as a reader would.
2. `schemify.py check` shows no `waiting` rule whose variables now exist, every `encoded` rule fixtured, and no conditional without a ledger rule.
3. Every property whose value set includes a structural code is a target of some rule — or has a rule record (any status) or a decision saying why not. `check` lists the stragglers.
4. Every `suspected` rule has been put to a person (asked, deferred, or declined) — none sit unasked.
5. Rebuild, and tell the user the Skip logic page is complete for their review.
