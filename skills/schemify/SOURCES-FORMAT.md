`SOURCES.md`, beside PROGRESS.md, is the provenance map — every file, page, and person the schemas draw on. "Never invent metadata" means every fact traces to a row here or to the steward; the review distills this file into the package README before it is cleaned away, because provenance outlives the scaffolding.

## Template

```md
# Sources — {study name}

## Dictionary files

- `{original/study_dictionary_v3.xlsx}` · {Excel, 4 sheets} · {variables on "Dictionary", header row 2, merged cells in col A; value labels on "Codes"} · registered {YYYY-MM-DD}

## External sources

- {Study site — data documentation} · {URL} · {what it offers: questionnaire PDFs, release notes} · {suggested | steward-approved | consulted YYYY-MM-DD | rejected ({why})}

## The steward

- {role, as offered — else "the steward"} · first-hand: {domains, e.g. ran the follow-up questionnaire; knows the lab codings} · defers to: {who or what, e.g. the coordinating center for genotyping}
- ask here: {kinds of questions the steward can settle} · not here: {what must go elsewhere or stay open}
```

## Rules

- **Register before you read.** A dictionary file gets its row — with parse notes — the first time it is opened; the notes (header row, sheet roles, merged cells, delimiter) are what save the next session from re-discovering them.
- **An external source enters as `suggested`**, with what it would resolve, and becomes citable provenance only once `steward-approved` and `consulted` (date it; the web moves). A search result the steward hasn't seen is not authority.
- **The steward section is a map, not a queue.** What they *can* answer lives here; what they *haven't yet* answered lives as `open` lines in DECISIONS.md.
- **Conflicts don't resolve here.** When an external source contradicts the dictionary, both citations land in one `open` decision; this file only records that each exists.
- **Distill before deletion.** At cleanup, the essentials — dictionary files, consulted sources with URLs — are copied into the README's provenance section (REVIEW.md). The file may then go; the trail must not.
