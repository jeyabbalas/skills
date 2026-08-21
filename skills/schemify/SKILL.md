---
name: schemify
description: Turn a bespoke data dictionary — Excel, CSV, PDF, whatever the study ships — into a validated package of interlinked JSON Schema files, working with you as the data steward: it interviews you for what the files don't say, tests every rule against toy data, renders browsable web pages for feedback, and remembers progress across sessions. Give it the path to your data dictionary.
disable-model-invocation: true
argument-hint: "data dictionary path(s), or a request — a category, a change, review"
---

The steward has asked you to turn their data dictionary — however it arrives: Excel, CSV, PDF, RTF, XML, a legacy website — into a package of interlinked JSON Schema files that machines can validate against and people can browse. This is stateful work: real dictionaries outlast any one session, so the plan, every judgment call, and every source live as markdown beside the schemas, and any future session picks up exactly where the last one stopped. You are a translator with a ledger, not an oracle: the steward owns the truth about their study, the source dictionary owns what it says, you own the encoding — and the ledger remembers which of the three every fact came from. The deliverable is a package that stands alone: schemas, toy test data, a validator, and two web pages, usable by people who have never heard of this skill.

## The package

The package is one directory (default `json_schema/`) holding the schemas and everything that ships with them. Until cleanup it also holds three working state files:

- `PROGRESS.md` — the plan: package conventions, the category table with statuses, the session log, and the steward-facing How to continue. Read [PROGRESS-FORMAT.md](./PROGRESS-FORMAT.md) when creating it, adding or re-planning categories or tables, or unsure what a status value means.
- `DECISIONS.md` — the append-only ledger of every judgment call, each tagged `user-confirmed`, `agent-decided`, or `open`. Read [DECISIONS-FORMAT.md](./DECISIONS-FORMAT.md) before your first append of the session, and again at review.
- `SOURCES.md` — what feeds the package: dictionary files with parse notes, external sources with URLs and approval status, and what the steward can answer first-hand. Read [SOURCES-FORMAT.md](./SOURCES-FORMAT.md) when registering a source or recording who knows what.
- The schemas, fixtures, tools, and pages — the deliverable tree, its naming, multi-package roots, and the contracts for the two bundled scripts: read [LAYOUT.md](./LAYOUT.md) when creating anything new in the package, running a script, or unsure where something lives.

Four laws hold everywhere: **the schemas are the source of truth** — every `.html` page is a disposable render of them, and a fact that lives only in chat does not exist: it lands in a schema keyword, a state file, or the package README, or it is lost; **never invent metadata** — every title, code, sentinel, bound, and rule traces to the source dictionary, a named external source, or the steward, and DECISIONS.md remembers which; **missingness lives in-band** — a missing or inapplicable value is a documented sentinel code with its own schema branch, never an absent key, never `null`, never a loosened type, and every column is required in every row; **case is ownership** — `UPPERCASE.md` files are working state with a `*-FORMAT.md` schema in this skill, scaffolding the steward may clean away at the end, while everything lowercase plus the `.json` schemas is the deliverable, built to stand alone.

## Invocation

First find the package, then dispatch on its state.

**Find the package.** The state anchor is `PROGRESS.md` in the package root. Look in order; first hit wins:

1. A path in the invocation that is, or sits inside, a package → that package.
2. `PROGRESS.md` in the current directory — you were invoked inside the package.
3. `json_schema/PROGRESS.md` — the default location.
4. A shallow scan, three levels deep, skipping hidden and dependency directories. One hit: use it, confirming in one line since it wasn't where expected. Several: name them and ask which.

No hit anywhere: if the scan instead finds a package-shaped directory — table directories with `*.schema.json`, a `common/defs.json`, a README describing a dataset — that is a **finished package** (state cleaned away at completion, by design). Otherwise this is a **fresh start**.

Then dispatch:

**Bootstrap** — fresh start. The invocation should bring a data dictionary (a path, a directory of files); if it brings nothing, ask for one — never scaffold a package around no source. Read [INTAKE.md](./INTAKE.md) and follow it end to end.

**Resume** — `PROGRESS.md` exists and the invocation brings nothing new. The mandatory read is one file; resist reading more to "get oriented":

1. Read `PROGRESS.md` — the whole file; it is built to stay small.
2. Propose the session in one line from the last log line's `next:` pointer — "Pick up the reproductive-history category?" The steward may redirect anywhere.
3. Read the one playbook for the agreed unit — and nothing else. Open only what the unit names: the category's own source slice (its plan row says where), `common/defs.json` when `$ref`-ing it, the mother file when appending to it. Never re-read the whole dictionary; never read DECISIONS.md end to end (grep it for a ruling — the standing ones are already in PROGRESS.md's Conventions); never open finished categories' files.

**Resume, with a request** — the invocation names a category, a variable, a change, or a question: same one-file read, then route. A category or variable to work on becomes the session's unit; a change to something `confirmed` reopens it (Revising, in CONVERT.md); a question is answered from the schemas and the ledger — a question is not a commission; "review" goes to Review even with categories unfinished (say what is unfinished first).

**New dictionary, existing package** — the invocation brings a dictionary file while `PROGRESS.md` exists: check SOURCES.md. Listed there → it is an input to the current work; Resume. Not listed → a second study wants its own package: confirm, then Bootstrap a sibling package (multi-package roots in LAYOUT.md) — never mix two studies' variables in one package.

**Review** — every category `confirmed` and the review milestone open, or the steward asks for it: read [REVIEW.md](./REVIEW.md).

**Finished package** — package shape, no `PROGRESS.md`: the README is now the front door. Read REVIEW.md's section on working on a finished package and treat the invocation as a targeted revision or a question.

## The work

Three phases; each ends at a gate the steward holds.

**Intake** — inventory the sources, learn the study, agree on the grain and the categories, scaffold the package and its state. Read [INTAKE.md](./INTAKE.md) when the package has no PROGRESS.md, or when a confirmed re-plan adds a table. Gate: the steward approves the category table.

**Convert** — the loop that carries one category at a time from source slice to confirmed schema. Read [CONVERT.md](./CONVERT.md) when the session will draft or revise a category. It sends you onward: read [SCHEMA-PATTERNS.md](./SCHEMA-PATTERNS.md) whenever you are about to write or edit schema JSON — it is the house rulebook; read [SKIP-PATTERNS.md](./SKIP-PATTERNS.md) when the slice carries routing — "asked only if", universe statements, skip logic; read [VALIDATE.md](./VALIDATE.md) when authoring or extending toy fixtures or interpreting a validation run; read [PAGES.md](./PAGES.md) when building, refreshing, serving, or presenting the web pages. Read [ELICIT.md](./ELICIT.md) before asking the steward any batch of questions and before hunting external sources — during intake included. Gate, per category: the steward confirms the rendered result.

**Review** — walk the ledger by confidence, revise what the steward dislikes, finish the package README, offer cleanup. Read [REVIEW.md](./REVIEW.md) when every category is confirmed, when the steward asks, or when working on a finished package. Gate: the steward accepts the package; cleanup is their call.

## Provenance

Everything you put in a schema is one of three things: transcribed from the source dictionary, taken from a named external source, or told to you by the steward. There is no fourth kind.

- Transcribe from the open source file, never from memory of similar studies. Codes, labels, ranges, units: read, then write.
- Verbatim source text goes in `$comment`, typos preserved in brackets (`[source: 'United Kingdon']`).
- "The dictionary does not say" is a finding — record it as an `open` decision rather than filling the silence.
- External facts carry their source's row in SOURCES.md; steward facts carry a dated ledger line.
- Whatever you add beyond all three — a plausibility bound, a normalized name, an inferred skip — is a judgment call, and the ledger remembers it (`agent-decided`) until the steward ratifies it.

## Session budget

Defaults; exceed only when the steward explicitly asks and the dictionary is small:

- **Intake**: one session — inventory, interview, category proposal, scaffold. A very large dictionary may need a full session for the inventory alone; propose the split rather than rushing the proposal.
- **Convert**: one category, carried through its whole loop — drafted, validated, rendered — per session. Several categories of under ~10 variables each may share one. A category carried to `validated` beats three left `drafted`.
- **Skip audit, fixture extension, pages refresh, review**: each is its own unit.

The budget is what makes every session end in a resumable state — depth over coverage, and a clean `next:` pointer beats a half-drafted sprawl. The steward likely doesn't know a session has limits: when one must end, say why in one line — "long dictionaries convert best in sittings; everything so far is saved" — and point them at PROGRESS.md's How to continue. Never end silently mid-unit, and close early rather than letting the limit arrive before the log line does.

## Closing a session

Before ending any session that touched the package, run this checklist — copy it and check it off:

```
- [ ] Session-log line appended to PROGRESS.md:
      - YYYY-MM-DD · {unit} · {what happened, telegraphic} · next: {concrete unit}
- [ ] Category rows current for everything touched (status moved only on its event, date updated)
- [ ] Every judgment call this session made is a DECISIONS.md line — a silent decision is an invention
- [ ] validate.py ran green after the last schema edit (or the failure itself is the next: unit)
- [ ] The next: pointer names something a stranger could pick up cold
      (a finished package writes: next: — (complete))
```

Only end when all five are checked. A session that appends no log line did not happen.

## Gotchas

- **`./` means this skill's own directory** — playbooks, formats, templates, scripts — and it is read-only. Every package path in these documents is written bare (`PROGRESS.md`, `core/categories/…`) and resolves from the package root. If a path you are about to write contains the skill's install location, stop: that is a bug.
- **A question is not a commission.** The steward asking what a schema says means answer them — changing it is planned work unless they ask.
- **Real data is radioactive.** Never copy real rows into schemas, fixtures, state files, pages, or chat. Toy rows are authored from the dictionary's value space, never sampled. Read real data only with the steward's explicit go-ahead, and only to check — observed levels, ranges — reporting counts and rules, never quoted rows.
- **The dictionary is not gospel.** When it contradicts itself — a code listed twice, an inverted label — encode what the steward confirms and record the defect (a "Dictionary defect" `$comment` plus a ledger line). Never silently pick a side.
- **A code project is not a study.** If the invocation directory looks like someone's software and no dictionary is in sight, confirm before scaffolding — the steward may have meant to invoke elsewhere, or may want a subdirectory.
- **Skipping validation is not a fallback.** If neither `uv` nor `pip` can run the scripts (ladder in LAYOUT.md), drafting may continue but no status may reach `validated` — say so, and log the debt.
