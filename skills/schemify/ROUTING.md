Routing, found and decided: how a package learns which rules its data obeys when the dictionary does not say — the scan, the evidence that licenses a rule, the steward's policy, the register that remembers rules across sittings, the proposals, the audit, and the way back for a package that has none of this. Dictionaries seldom state skip logic and downstream consumers depend on it, so routing is hunted and recorded by default; domain knowledge writes questions, never schemas. Writing the JSON is SKIP-PATTERNS.md's; the register's rows are ROUTING-FORMAT.md's; the routing families epidemiological data carries are ROUTING-CATALOG.md's.

Table of contents

- [The routing scan](#the-routing-scan)
- [Evidence](#evidence)
- [Where routing hides](#where-routing-hides)
- [The routing policy](#the-routing-policy)
- [Noticing and registering](#noticing-and-registering)
- [Proposing](#proposing)
- [The skip audit](#the-skip-audit)
- [Migration](#migration)

## The routing scan

Run it twice: over every source file at intake's survey, and over each slice before drafting. Look for:

- NA-type labels on codes — "not applicable", "legitimate skip", "inapplicable", "not asked", "INAP", "N/A (never smoker)". A parenthetical names the universe.
- Routing text in labels or notes — "asked only if", "if yes", "skip to", "go to", "→", "universe:", "among", "for those who".
- A routing column — REDCap `Branching Logic`, XLSForm `relevant`, DDI `<universe>`, a "Skip to" or "Universe" column.
- A questionnaire, CRF, or interviewer manual among the inputs.
- Gate-and-detail name pairs (`ever_` beside `age_`, `num_`, `_specify`), sex- or age-specific blocks, roster slots, wave suffixes, "other, specify" pairs, checkbox groups with a "none" member.

The verdict is one line — signals seen, named, or none — written into the file's parse notes in SOURCES.md; the graded table of what each signal means is ROUTING-CATALOG.md's. A rule the source *states* becomes a `waiting` register row the moment the scan finds it, without encoding: nothing is encoded before the policy is set and the variables exist.

## Evidence

Every rule records its origin once in the register, and the origin decides what may happen to it. One sentence governs: **source-traced or steward-told → encode; agent-expected → ask.**

- `quoted` — the source states the routing. Encode the pair; the `$comment` quotes the source. The applicability twin is your construction, so the pair earns one `agent-decided` line.
- `implied` — source text implies a universe without stating it: an NA code labelled "N/A (never smoker)", a title "among current smokers", a universe column. Encode the pair provisionally, `agent-decided`, quoting the implying text in the `$comment`, and put it in the next batch — the proposal names both directions, since the applicability half is a further step.
- `steward` — the steward said so: an interview answer, a volunteered rule, a yes to a proposal. Encode; their dated ledger line is the provenance.
- `inferred` — you expect it from the study design and nothing in the source hints at it. Never encoded. It is a proposal: an `open` ledger line, a `proposed` register row, no conditional. A yes makes the steward its provenance; only then is it encoded.

ELICIT.md's "loosest reading the source supports" is, for a routing rule, no conditional at all — which is why `inferred` stays out of the schema. Counts from real data — with the Conventions row's consent, a gate-by-target crosstab on coded variables, counts never rows, and only to test a proposal that already exists, never to go looking — strengthen the question and go in the row's `notes`. They never license a rule.

## Where routing hides

Before asking the steward, ask for the artifact: the instrument with its arrows, a survey-tool export with its logic column, the interviewer manual, the cleaning code that wrote the delivered codes — the table by data type is ROUTING-CATALOG.md's. Suggest them the way ELICIT.md hunts external sources: each enters SOURCES.md as `suggested`, and only a consulted source is quoted in a `$comment`.

## The routing policy

One Conventions row in PROGRESS.md, always present, cited to its ledger line: set by interview question 8, changed by any later steward request — "stay faithful to the metadata", "leave the skips out", "go ahead and enforce them" — each change a new line superseding the old.

- `full` — the default; silence or "sure" means this. Every evidence kind; you propose from ROUTING-CATALOG.md.
- `faithful` — the steward wants nothing beyond their documentation. `quoted`, `implied`, and `steward` rules only; no `inferred` row is ever created, no proposal ever made. Set mid-project: unconfirmed `inferred` rows become `declined` citing the policy line and their open lines are superseded; inferred rules the steward already confirmed stay — they trace to the steward now.
- `declined` — nothing is enforced. Rules you meet while converting are still registered, `declined` citing the policy line, at no research cost: they are the revisit list and the README's "documented but not enforced" material. The skip-audit milestone reads `waived (D{NNN})`. Offer the revisit exactly once, at review — "the register holds N rules your documents state; say the word and they are enforced" — and never again unprompted.
- `undecided` — "later". Quoted and implied rules are still encoded (they are the source's own reading); no proposals; the question rides the next batch.

A PROGRESS.md without a `routing` row is a package that predates the register — Migration, below.

## Noticing and registering

- **Before drafting a category**: grep `ROUTING.csv` for the category's name and every variable in its slice. Rows `waiting` on this category are its work.
- **While drafting**, register the moment you notice — gate seen or detail seen. A gate (`ever_smoker`, `sex`, `vital_status`) names the dependents you expect, in this category or a later one; a detail (an NA code, a `_specify` field, an "age at" beside a status) names the gate you expect, converted already or not. Rows are cheap; a forgotten rule is not.
- **Both ends must be properties of one table and one row.** A named variable not yet converted, or `deferred`, holds the row at `waiting`; `dropped`, never delivered, another table, or another row makes it `not-enforceable` with the reason. Never encode against a property that does not exist — the validator refuses it.
- **The askable moment**: when both ends exist, a `quoted`, `implied`, or `steward` row is encoded (this session, or as `next: skips {category}`); an `inferred` row becomes `proposed` and gets its `open` ledger line — that line is the question, and ELICIT.md's queue picks it up. Under `faithful` no inferred row exists; under `declined` every row is `declined`.

## Proposing

Proposals ride the category's presentation message (CONVERT.md), after the gist, under ELICIT.md's batch rule — never their own round trip, never one at a time unless the steward asked for that. One proposal per gate, listing every dependent it controls, so the steward confirms a list, not a pair; at most ten items per message; quoted first, then implied, then inferred, and within a kind the gate with the most dependents first.

Each proposal: the gate in the study's words · your reading · the dependents · the cell question — "for someone this was skipped for, what is in the cell: a code, blank, zero, last wave's value?" · the evidence · a one-line ask · its D-number. Offer the reading as options: the NA code, a substantive value, anything, or a different rule. A pin — "never smokers carry 0" — is asked, never assumed, and its reverse is asked separately (a former smoker may honestly report 0). An implied rule already encoded reads "encoded from the label — say no to remove it". Chains (`sex` gates `mammogram_ever` gates `mammogram_age_last`) ask one question per gate.

Answers: **yes** → `confirmed`, encoded this session with fixtures and the `$comment` citing the line, or `next: skips {category}`; **no** → `declined`, the line `user-confirmed` with "no routing on X" so it is never re-asked; **a different rule** → the row rewritten, the line superseded; **later** → the row stays `proposed`, rides one more batch, then the review, where a second "later" migrates it to the README's open items; a partial answer splits the row.

## The skip audit

The `skips audit` unit runs once every category is `confirmed` and before the review — it is what the milestone means:

- No `waiting` or `proposed` row remains; every `confirmed` row is `encoded`.
- EXECUTE `validate.py routing` (contract in LAYOUT.md) — green: every id in the mother has its row, every `encoded` row its conditional, no dangling variable.
- Every encoded rule fired on a fixture case (the check reports `rule-unfixtured`); extend fixtures per VALIDATE.md where it did not.
- Every property the check lists as carrying a structural-NA code with no rule has a register row of some status, or a ledger line saying why not.
- README section 5 regenerates from the mother; both pages re-rendered if any `$comment` changed.

Tick the milestone, or mark it `waived (D{NNN})` under a declined policy.

## Migration

A package with conditionals but no `ROUTING.csv` — PROGRESS.md's Conventions have no `routing` row — predates the register. The `skips migrate` unit: create `ROUTING.csv` per ROUTING-FORMAT.md with one `encoded` row per existing routing fact (a pair is one row; evidence from the ledger line that encoded it, `quoted` where none exists); add the id to each conditional's `$comment`; add `routing: full` as an `agent-decided` Conventions row with its ledger line and put question 8 in the next batch; EXECUTE `validate.py routing` until green; re-render both pages (the `$comment` edits change their fingerprints); log the unit. A finished package — no state trio — migrates in revision mode per REVIEW.md, without resurrecting the trio.
