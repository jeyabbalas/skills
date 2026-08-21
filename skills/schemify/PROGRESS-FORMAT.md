`PROGRESS.md`, in the package root, is the one file every resuming session reads — the plan, the settled conventions, where each category stands, and the log that ends in a `next:` pointer. It is built to stay small: an index over the package, never a store.

## Template

```md
# {Study name} — conversion progress

package: {path from repo root, e.g. json_schema} · started: {YYYY-MM-DD}
grain: One element is one {…, matching the mother file's description}
dictionary: {source file(s), one gist} — full inventory in SOURCES.md

## How to continue

This conversion runs over several sittings — an agent session can hold only so
much at once, so the work is planned in units that each fit one session. Nothing
is lost between sittings: this file is the memory.

To continue at any time: open a fresh agent session in {invocation directory}
and invoke the skill again. The agent reads this file and proposes the next
unit. You can also ask for anything directly — a specific category, a change,
a question, the final review.

## Conventions

- sentinels: {codes · meanings, e.g. -666 not applicable · -777 refused · -888 don't know} · D{NNN}
- $id base: {https://…/} (replace before publishing) · D{NNN}
- grain: see header · title separator: {char} · formatting: 2-space, one key per line
- real data: {none in repo | at {path} — read only with consent, never quoted} · D{NNN}

## Categories

| # | category | file | vars | source slice | status | touched |
|---|---|---|---|---|---|---|
| 1 | {Participant} | {sleep_diary/categories/participant.json} | {4} | {dictionary.csv rows 2–5} | {confirmed} | {YYYY-MM-DD} |
| 2 | {Sleep} | {sleep_diary/categories/sleep.json} | {8} | {dictionary.csv rows 6–13} | {drafted} | {YYYY-MM-DD} |

## Package milestones

- [ ] intake: sources registered · grain confirmed · categories confirmed
- [ ] common/defs.json + mother scaffold validate green
- [ ] every category confirmed
- [ ] cross-category skip audit
- [ ] coverage audit 1:1
- [ ] pages current for the whole package
- [ ] review walked · cleanup decided

## Session log

- {YYYY-MM-DD} · {unit} · {what happened, telegraphic} · next: {concrete unit}
```

## Rules

- **An index, not a store.** Rows gist and point — variable detail lives in the schemas and VARIABLES.csv, rulings in DECISIONS.md, source detail in SOURCES.md. A cell that wants a second sentence is telling you the content belongs elsewhere.
- **How to continue is written once, at creation, for the steward** — plain words, no token talk beyond "a session holds only so much". Edit it only if the package moves.
- **Statuses move only on their events**: `pending → drafted` when the category file exists and meta-validates; `→ validated` when its fixtures pass and fail as designed; `→ rendered` when both pages carry it; `→ confirmed` only when the steward says so — never on your own. `blocked(D{NNN})` may stand in for any status while an open decision gates the work; restore the earned status when it resolves. A review overturn sets `drafted` — the loop re-runs from there.
- **The log only appends** — one line per session, `·`-separated, ending in `next:`. The pointer vocabulary: `intake` · `convert {category}` · `skips {scope}` · `fixtures {scope}` · `pages` · `elicit ({N} open)` · `revise {category}` · `review` · `— (complete)`.
- **Conventions cite their decision** (`D{NNN}`) so the review can walk them — a convention with no ledger line is an invention.
- **Multi-table packages** add a `table` column to Categories; milestones repeat per table only when the tables truly stagger.
