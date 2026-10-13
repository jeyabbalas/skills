Briefs for delegating the token-heavy work — reading sources, researching the study on the web, drafting large topics — to subagents, and how to check what comes back. Read this before delegating anything. You remain the only writer of the ledger: subagents write the files their brief names and report to you; you verify and `record`.

Table of contents

- [When to delegate](#when-to-delegate)
- [Rules every brief carries](#rules-every-brief-carries)
- [Brief: digest a source](#brief-digest-a-source)
- [Brief: research the study](#brief-research-the-study)
- [Brief: draft a topic](#brief-draft-a-topic)
- [Checking the results](#checking-the-results)

## When to delegate

- Digesting sources: always when your harness can run subagents — one per source, all in parallel (about ten at a time; a part that fails is retried once, then done by you). A source over about 150 pages or 1,000 variables gets one subagent per chunk of about 30 pages or 300 variables, cut where a section starts, never inside a variable; each writes `DIGEST-<chunk>.md` and `variables-found-<chunk>.csv`. A code list on a sheet of its own is not a chunk: each chunk looks its variables' codes up there. Then merge, with a short script: you write `DIGEST.md`'s first two sections, append each chunk's other sections under `## Part <chunk>`, join the CSVs (one header, one row per variable), and delete the chunk files.
- Web research: always, in the same message as the digests.
- Use a subagent type that can read and write files (and, for research, use the web) — in Claude Code, `general-purpose`.
- Drafting: only for a topic of more than about 60 variables, or several independent topics at once in a large package. Small topics are faster to draft yourself.
- No subagents in this harness: do the same work yourself, in the same order, writing each output file before starting the next piece — the files are what survive a full context.

Fill in every `<…>` in a brief. Give paths as absolute paths. Ask for the result in the exact shape the brief names.

## Rules every brief carries

Paste these into every brief, unchanged:

> - Write only the files this brief names. Do not edit anything else in the workspace, and never edit `state/ledger.jsonl` or `state/project.json`.
> - Never open a data file — anything holding individual records (a header of variable names, then one row per person, visit, or sample), or named like one: an `exports/` or `raw/` folder, `*_data.*`, `*export*`, a dated release, `.sav`, `.dta`, `.sas7bdat`, `.parquet`, `.rds`, or a `.json`/`.jsonl`/`.ndjson` file this brief does not name as documentation. A workbook sheet of records counts: check `manifest.json` → `stats.sheets` before reading any sheet. If you meet one, stop and report it.
> - Copy codes, labels, and instructions exactly as the source writes them, typos included. Never fill a gap from memory of similar studies — write "not stated" instead.
> - Every fact carries its locator: `<sheet> row N`, `p.N`, `¶N`, `§heading`, or a URL.
> - Your final message is a short report: what you produced, anything you could not read, and anything surprising — or, when this brief asks for JSON only, that JSON.

## Brief: digest a source

> Read the source `<id> — <title>` and write its digest. The extracted text and tables are in `<workspace>/sources/<id>/extract/` (start with `manifest.json`; its `locators` line says how to cite); the original is `<workspace>/<path>`. For questionnaire pages where layout matters — arrows, boxes, indented follow-ups — view the original page itself; a Word file's extract loses indentation and boxes, so say under **Problems** when routing may depend on layout you cannot see. A scanned document's text layer is machine-read and misreads digits, codes, and tick boxes: copy codes, numbers, and routing from the page image, and list every doubt under **Problems**. For cleaning code, the variables are the ones it creates or recodes, each with its line; lines it marks `[embedded data line, not extracted]` stay unread — never look them up in the original.
>
> <for a chunk: Digest only <the rows or pages of this chunk> — look one row or page either side for context, no further. Write `DIGEST-<chunk>.md` and `variables-found-<chunk>.csv` instead of the file names below.>
>
> Write `<workspace>/sources/<id>/DIGEST.md` with these sections:
> 1. **What it is** — two lines: what kind of document, which study, which version or wave, which table or dataset it describes.
> 2. **How to read it** — the layout: where variables start, which column or page holds what, header rows, merged cells, code lists kept elsewhere, anything easy to misread.
> 3. **Variables** — a table: variable · label (verbatim) · type · shape · codes and labels (verbatim) · missing-value codes · notes · locator. For a questionnaire: question number · question text · response options (verbatim) · the variable name it maps to, if the document says — or "unmapped". **Shape** says whether the variable holds one value or several: `value`, `group` (named parts: an address), `list` (several values of one kind: "select all that apply", codes), `entries` (a repeated block: one entry per person, per visit), `lookup` (values under varying names), `mixed`, or `unclear` — with the words or layout that tell you ("for each person", sub-bullets, a dotted name, a JSON example, a repeating section) in notes. Give each part of a group or an entry its own row, named by its path: `address.city`, `household[].age` (`<skill-dir>/NESTED.md` lists the signals and the names). Numbered families (`child1_age`, `child2_age`) are rows of their own; note that they look like a list delivered as columns.
> 4. **Skip logic and conditions** — every routing instruction or hint: the text verbatim, the questions or variables it involves, explicit (a stated "go to", "asked only if", a branching column) or implicit (an indented follow-up, a section for a subgroup, an N/A label naming who), and its locator.
> 5. **Other facts** — derivations, recodes, units, waves and versions, sites, anything a schema could use.
> 6. **Problems** — contradictions inside the source, typos, missing pieces (e.g. "the coding sheet it refers to is not included").
>
> Also write `<workspace>/sources/<id>/variables-found.csv` with columns `variable,label,type,shape,codes,missing,locator` — one row per variable the source names and per part of a group or entry (by path), codes as `1=Yes; 2=No` copied verbatim.
>
> <the rules every brief carries>

## Brief: research the study

> Find public documentation about this study that its data documentation might lack. Study: `<name>`; also known as `<acronyms, consortium, cohort names, grant or registry ids seen in the first lines of the extracts — or "none found">`; the user's documents are `<titles>`. If the name is generic, search with the documents' title words too. If nothing turns up, return `[]` — never a guess. Look for: the study's own website and data documentation; data-portal pages (dbGaP study and variable pages, consortium catalogues, data-sharing platforms); published questionnaires and codebooks; cohort-profile and design papers; harmonisation documents. Prefer official pages over secondary ones; note versions and dates.
>
> Do not download data files, request data access, or sign in anywhere.
>
> Return JSON only: `[{"title": "…", "url": "…", "what": "what it holds", "settles": "which kinds of gaps it could fill (codes, skip logic, derivations, …)", "official": true, "version": "…", "conflicts": "anything that disagrees with the user's documents, or null"}]`, best first, at most 15.
>
> <the rules every brief carries>

## Brief: draft a topic

> Draft the category file for topic `<id>` (`<title>`) of table `<table>` in the schemify workspace `<workspace>`. Read `<skill-dir>/SCHEMA-STYLE.md` and `<skill-dir>/SKIP-LOGIC.md` first and follow them exactly — and `<skill-dir>/NESTED.md` when any of its variables holds more than one value. How nested values are delivered: `<the structure decisions and their answers, or "all flat">`. Its variables are the rows of `<workspace>/state/variables.csv` with topic `<id>`; read their definitions from the digests and extracts at the locators given, transcribing codes and labels exactly. Shared definitions: `<workspace>/package/schemas/common/defs.json` (read only). Decisions already made: `<list of D ids and one-line answers that apply>`.
>
> Write only `<workspace>/package/schemas/<table>/categories/<id>.json`. Every property carries `x-provenance`: source facts cite `S0N:<locator>`; anything you decided cites a placeholder `"@guess-<variable>-<facet>"`.
>
> Return JSON only: `{"guesses": [{"label": "guess-<variable>-<facet>", "targets": ["…"], "question": "…", "choice": "…", "why": "…"}], "questions": [{"targets": […], "kind": "conflict|gap|ambiguity", "question": "…", "evidence": [{"ref": "S0N:…", "quote": "…"}], "options": [{"id": "a", "label": "…"}, …], "recommended": "a", "why": "…"}], "rules": [{"gates": […], "targets": […], "reading": "…", "evidence": "documented|implied|inferred", "refs": ["S0N:…"]}]}` — every judgment call you made, every question the sources could not settle, and every rule you noticed. Encode no rule yourself.
>
> <the rules every brief carries>

## Checking the results

Nothing a subagent wrote is trusted until you check it:

- **Digests**: spot-check three or more locators per source or chunk against the extract (START.md, step 4) before recording the `digest` event.
- **Research**: you decide which findings to register as suggested sources; nothing reaches a schema until a person approves the source.
- **Drafts**: record the returned guesses as decisions (`event: decide`, each with `"ref": "<its label>"`) and replace the file's `@guess-…` placeholders with the assigned ids; post the questions per QUESTIONS.md; register the rules per SKIP-LOGIC.md; then run `validate.py check` and read every finding before continuing with BUILD.md's loop from step 4.
