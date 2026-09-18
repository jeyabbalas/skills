The first session in a package: learn the study, inventory the sources, agree on the shape, scaffold. This runs once per package — PROGRESS.md's existence is the never-again flag — and again only when a confirmed re-plan adds a table. Interview craft lives in ELICIT.md; schema content in SCHEMA-PATTERNS.md; the tree and script contracts in LAYOUT.md.

Table of contents

- [Steps](#steps)
- [Surveying the sources](#surveying-the-sources)
- [Introducing the method](#introducing-the-method)
- [The interview](#the-interview)
- [Proposing categories](#proposing-categories)
- [Scaffolding](#scaffolding)
- [Handing off](#handing-off)

## Steps

1. **Survey the sources.** Register every dictionary file, extract the variables inventory, estimate the size. Done when: SOURCES.md rows exist for every input, VARIABLES.csv lists every variable, and you can say "N variables, roughly M sittings" out loud — and the routing scan (ROUTING.md) has run, its hits in the parse notes.
2. **Introduce the method.** The short version of how this will work, in the steward's terms. Done when: they know the work runs in sittings, where state lives, and how to continue.
3. **Interview the steward.** Eight questions, one message, read-back confirmation. Done when: grain, tables, sentinel policy, real-data ruling, external leads, the steward's own domains, and the routing policy are recorded.
4. **Propose categories.** Derived from the source's own structure, iterated until approved whole. Done when: the steward has said yes to the category table as a whole.
5. **Scaffold.** The package skeleton, the state trio, a green validation run. Done when: `validate.py check` passes on the scaffold and the state trio, VARIABLES.csv, and ROUTING.csv exist.
6. **Continue into the first category** if the session's budget allows — otherwise close per SKILL.md with `next: convert <first category>`. A very large dictionary may spend this whole session on steps 1–2 and interview next time; propose the split rather than rushing the proposal.

## Surveying the sources

Register each dictionary file in SOURCES.md *before* deep reading — the parse notes you leave are the next session's map. Then read enough to inventory, not yet to convert:

- **Excel**: find the real header row (rarely row 1); note each sheet's role — variables, value labels, notes; watch for merged cells that carry a value only in their first row.
- **CSV/TSV**: note delimiter and encoding; a `;`-separated export or a UTF-8 BOM is worth one parse note now, not a surprise later.
- **PDF**: read page-ranged, never the whole file at once; note where the variable tables start and how a variable's block is laid out.
- **RTF/XML/HTML**: extract to text first (`textutil` on macOS, an XML pretty-print, saving the page as text) and note the extraction command; work from the extraction.
- **A website**: it is an external source — record the URL in SOURCES.md and treat pages you consult like PDF pages.

While surveying, write `VARIABLES.csv` in the package root — one row per variable the source defines, category left `unassigned` until the proposal, status `pending` (format in VALIDATE.md). This inventory is the coverage check's ground truth: a variable missing from it is a variable the package will silently forget. Count it honestly and state the estimate to the steward — variable count is what decides between "one sitting" and "a phased plan".

While surveying, run ROUTING.md's scan on each file — an NA-type label, a gate-and-detail name pair, a branching-logic column, a questionnaire among the inputs — and note the hits in that file's parse notes. Register what the source *states* as `waiting` rows in `ROUTING.csv` now, without encoding; the hits decide how the routing question is asked and where to send the hunt.

Everything registered here is input, not yet truth: parse notes describe the files; the interview establishes what they mean.

## Introducing the method

Before the interview, tell the steward how this will work — adapt to their register, don't recite:

> We'll turn your data dictionary into a package of JSON Schema files — a machine-checkable version of what your documentation says, organized by topic, that validators and web tools can use directly.
>
> The work runs in sittings: an agent session can hold only so much text at once, so we go category by category — draft, test against toy data, render pages you can browse, then the next. Between sittings everything lives in three markdown files beside the schemas — progress, decisions, sources — so any future session picks up exactly where we stopped. To continue at any time, invoke this skill here again.
>
> You stay the authority throughout: I ask rather than guess, I batch questions so you aren't interrupted constantly, and at the end we review every judgment call together before I clean up my working files.

Small dictionary, likely one sitting? Say that instead — the sittings paragraph shrinks to a sentence. The introduction is spoken once; its durable twin is PROGRESS.md's How to continue section, written at scaffolding.

## The interview

One message, numbered, conducted per ELICIT.md's craft (speak the study, offer readings, read back what you heard). The eight:

1. **Grain** — "What is one row in this data: one participant? one visit? one household at one wave?" The answer becomes the mother file's description and never changes silently.
2. **Tables** — "Is this one dataset, or several related ones (a main table, a diagnosis table, a measurements table)?" Each distinct grain is its own table directory.
3. **Missing-value codes** — "When a value is missing, refused, or doesn't apply, what goes in the cell?" Adopt the source's own codes as the package's sentinel policy — never invent one the source doesn't define. If the source truly has none, propose a set and record it as an explicit `agent-decided` line for the review. Either way the policy lands in DECISIONS.md and PROGRESS.md's Conventions.
4. **Real data** — "Is actual study data in this repository? May I look at it?" Whatever they answer, the radioactivity rule from SKILL.md governs; the ruling is a Conventions row.
5. **Public documentation** — "Does the study have a website, a published codebook, questionnaire forms?" Any lead triggers ELICIT.md's hunt; suggest likely sources yourself from what the study's name and field imply.
6. **Their own knowledge** — "Which parts of this data do you know first-hand, and where do you defer to someone else?" This fills SOURCES.md's steward map and tells you where `open` questions can actually be settled.
7. **Downstream consumer** — "Who will validate against these schemas, with what tooling?" A constraining answer (a specific validator, a required draft) becomes a Conventions row.
8. **Routing** — "Were some questions asked only of some people — smoking details of ever-smokers, pregnancy items of women, follow-ups only of those who said yes? Where is that written down: the questionnaire's skip instructions, a REDCap or survey-tool export, the interviewer manual, your cleaning code? And what sits in the cell for someone who wasn't asked — a code such as 777, a blank, a zero? I'll encode every rule your documents state or imply. Beyond that I can propose rules I'd expect from the study design for you to accept or reject, or stay strictly faithful to your documentation and propose nothing — which do you prefer?" Lead with the scan's hits when there are any ("your codes list '777 = N/A (never smoker)' on eleven variables — that reads as a rule; is it one?") and suggest sources from ROUTING-CATALOG.md's table for this data type. Silence or "sure" is `full`; "stay faithful" is `faithful`; "later" is `undecided`; only an explicit no is `declined` (ROUTING.md). The answer is the `routing` Conventions row and its ledger line; named sources enter SOURCES.md as `suggested`; "a blank" is not a code, so that answer reopens question 3.

Push back once on a vague answer — "roughly how many rows per participant?" — then record what you got and move on; a residual unknown is an `open` decision, not a stalled intake. The routing question in particular may get "later" — that is the policy `undecided`, and ROUTING.md says what proceeds meanwhile.

## Proposing categories

Categories are how the steward thinks about their data, not how you would file it. Propose, don't assign:

1. Derive the proposal from the dictionary's own structure first — its sections, sheet tabs, heading rows, variable-name prefixes. Only when the source is flat do you group by topic yourself.
2. Present one table in chat: proposed category · working file name · variable count · three example variables · a one-line rationale. Under it, one honest line about anything that didn't fit and where you put it.
3. Ask for exactly this: "Merge, split, rename, or move anything — these names become the package's files and every page's sections, so they should match how you and your colleagues talk about the data." Iterate the table until the steward approves it whole.
4. Record the outcome: one `user-confirmed` ledger line, the Categories table in PROGRESS.md — one row per category with its source slice — and the `category` column of VARIABLES.csv filled in.

A dictionary under ~20 variables with no natural grouping is one category — say so and don't manufacture taxonomy; the package keeps the same shape (one mother file, one category file). Never split what the source keeps together without the steward's yes.

## Scaffolding

1. EXECUTE `render.py init <package>` (contract and fallbacks in LAYOUT.md) — assets, tools, VERSION.
2. Write `common/defs.json` — the sentinel policy's invariant codes and any id or date patterns already known — and each table's mother file with its category `$ref`s pointing at files that will exist, per SCHEMA-PATTERNS.md. Category files themselves are convert-phase work; scaffold none of them.
3. Write the state trio per PROGRESS-FORMAT.md, DECISIONS-FORMAT.md, SOURCES-FORMAT.md — Conventions filled from the interview, each row citing its D-number, the `routing` row among them; the interview's decisions are the ledger's first lines. Write `ROUTING.csv` with its header only (ROUTING-FORMAT.md), even when no routing is expected — a header-only register means "audited, none".
4. EXECUTE `validate.py check <package>` — green before anything else happens. A scaffold that doesn't validate is not a scaffold.

## Handing off

Append the first session-log line and close per SKILL.md's checklist. The `next:` pointer names the first category; the log line notes the method was introduced, so no future session repeats it. If budget remains and the steward is game, roll straight into CONVERT.md for that category — intake ending early is a feature, not a quota to fill.
