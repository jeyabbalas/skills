Bringing a schemify 1.x package into a 2.x workspace. Read this when the invocation directory holds a 1.x package — a folder (usually `json_schema/`) with `*/*.schema.json` beside `PROGRESS.md`, `DECISIONS.md`, `VARIABLES.csv`, or `ROUTING.csv` — and no `schemify/` workspace, and whenever `next` says `migrate`.

Table of contents

- [What changes for the user](#what-changes-for-the-user)
- [1. Convert](#1-convert)
- [2. Finish what the script could not](#2-finish-what-the-script-could-not)
- [3. Verify and show](#3-verify-and-show)

## What changes for the user

Before running anything, tell them in chat — the website does not exist yet — in three lines: the work is moving into a new folder, `schemify/`, with a project website for questions and review; nothing in their old folder is changed or deleted; when they are happy with the new one, they may delete the old folder themselves. Then ask one question and wait for the answer: "Were the earlier questions answered by the study's data steward, or by someone else? (If you are not sure, I will treat them as yours and the steward can review them.)" *Steward* → `--person steward`; anyone else, or not sure → `--person author`.

## 1. Convert

`uv run <skill-dir>/scripts/migrate.py --from <the 1.x folder> --person <author|steward>` — add `--study "<name>"` only when the user has given the study a name; otherwise it takes PROGRESS.md's title, or the folder's name. It creates `schemify/` beside the old folder, writes the new workspace's first ledger entries itself (from then on, only `record` writes them), records and closes its own session, and:

- copies the tables and `common/` into `package/schemas/` — same relative paths — and keeps the 1.x `$id` base as `idBase`: never change it;
- copies the dictionary files SOURCES.md lists into `sources/` under their own names and registers them, each with a starter digest holding its 1.x parse notes — `sources` in its output maps each file to its id;
- turns each DECISIONS.md line into a decision (1.x ids map one-to-one when they can; `sources/MIGRATION.md` holds the map), ROUTING.csv rows into rules, VARIABLES.csv into `state/variables.csv`, and PROGRESS.md's categories into topics — categories confirmed in 1.x keep their approval, attributed to `--person`;
- adds `x-provenance` from the inventory's source column, `x-value-kind` to special codes it recognises, and rewrites 1.x decision ids inside `$comment`s;
- copies the toy fixtures into `package/toy-data/<table>/`.

It prints `attention` — every place it could not finish — and writes the same list into `sources/MIGRATION.md` under *Left to do*. Until you record the `migrated` milestone (step 3), `status` → `next` starts with `migrate`.

## 2. Finish what the script could not

In this order:

1. `schemify.py open` (SKILL.md, Open step 2); relay `tell_user`.
2. Run `extract.py` on each registered source (START.md, step 2.4) and record its `extract` event, so you can cite locators. Spot-check three of the citations the script wrote into `x-provenance` against the extract; a wrong one means the inventory's source column was wrong — fix every citation from that source.
3. Ask whether files beside the old folder that SOURCES.md does not list (a dictionary in `docs/`, a questionnaire) should be registered — list their names only (law 2) — and register the ones the user names (START.md, step 2).
4. Work through *Left to do*, one item at a time:
   - **Missing `x-provenance`** on a property or a shared definition: find where a source defines it — search the extract for its name — cite that locator, and fill its `source` column in `state/variables.csv`. A value no source states is a decision: record it as a `guess` and cite it.
   - **A rule without a source**: find where a source states it — the instruction beside its gate question, a note on its target — and cite it on the rule (`set` with `refs`) and on its conditional. A rule nothing states is `inferred`: take its conditional out of the mother (the entries after it move up one place — harmless, since every data-check run keeps the rule map of the schemas it ran on), `set` the rule `suspected`, and ask its consent question (SKIP-LOGIC.md) with this batch.
   - **Inferred rules that were encoded in 1.x** without a recorded consent: ask the consent question; until a person says yes, the rule leaves the mother as above.
   - **Facets**: where the script says a property mentions a decision, cite that decision on the facet it settles (a bound, a pattern, a code).
   - **Sources without a file or URL** (a questionnaire the 1.x steward shared): ask the user for the file and register it.
   - **Toy data not found**, or invalid rows with no ledger of planted mistakes: write the invalid rows and their ledger afresh (DATA-CHECK.md) — never reconstruct which mistake an old row planted from what fails today.
   - **People**: INTERVIEW.md's opening interview minus what 1.x already settled — the study's name when PROGRESS.md had a title, and the other-documentation question when SOURCES.md lists them.
5. Open 1.x questions become ordinary open decisions with generic options; `next` lists them as `post-questions`. Rewrite each as a proper question (QUESTIONS.md) — `open` the new one with a `ref` and, in the same payload, `{"type": "decision", "event": "supersede", "id": "<old>", "replacement": "@<ref>"}`.
6. Post one batch: the interview questions first, then the rewritten and consent questions (QUESTIONS.md).

## 3. Verify and show

1. `build`, then `check`, and fix every error. Most are house-style findings the 1.x style did not require — `x-value-kind` on special codes, a rule's citation of the source that states it — which restate what the sources say and need no decision. Anything a person could dispute — a `uniqueItems` no one confirmed, a bound with no source — becomes a question, with the current encoding as its `provisional`.
2. Once `check` is green and every *Left to do* item is fixed or asked as a question: `{"type": "milestone", "event": "reach", "id": "migrated", "note": "…"}` — answers still pending are ordinary work from then on.
3. Present the result: each topic confirmed in 1.x stays confirmed, but invite the user to look over the website — especially the Skip logic and Sources & decisions tabs, which 1.x did not have.
4. Close (SKILL.md) with a handoff naming anything still open from the migration.
