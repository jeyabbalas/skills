The first session: set up the workspace, register and read every source, research the study on the web, interview the user, and plan the tables and topics. Read this for a fresh start — its steps are the order to follow — and whenever `status` → `next` says `add-sources`, `discover`, or `plan`. The interview's content is INTERVIEW.md's; delegation briefs are SUBAGENTS.md's.

Table of contents

- [Overview](#overview)
- [1. Set up](#1-set-up)
- [2. Register the sources](#2-register-the-sources)
- [3. Post the opening interview](#3-post-the-opening-interview)
- [4. Digest every source](#4-digest-every-source)
- [5. Research the study on the web](#5-research-the-study-on-the-web)
- [6. Inventory](#6-inventory)
- [7. Plan](#7-plan)
- [8. Scaffold](#8-scaffold)
- [Later sources](#later-sources)

## Overview

| step | done when |
|---|---|
| 1. Set up | `init` and `open` ran; the user has the website link |
| 2. Register | every documentation file the user named is copied, registered, and extracted; possible data files are left closed and asked about |
| 3. Interview | the opening batch is posted and the user knows it waits |
| 4. Digest | every document has a verified DIGEST.md and a `digest` event |
| 5. Research | web findings are registered as suggested sources |
| 6. Inventory | `state/variables.csv` lists every variable; you know the size |
| 7. Plan | a person approved tables, grain, missing-value codes, and topics; rules found so far are recorded |
| 8. Scaffold | defs, mothers, and one empty file per topic exist; `check` is green; the session plan is written |

Steps 4 and 5 run while the user answers step 3. With a small dictionary the plan batch follows within minutes, and the whole package can fit one session. Before each step, `activity` (SKILL.md, Work).

## 1. Set up

1. Sort what the user named into documentation and possible data — by name, folder, and their words only (SKILL.md, law 2); open nothing yet. If nothing they named is documentation, ask for their metadata files in chat and stop: never set up a workspace around nothing.
2. If the invocation directory is a home folder, the desktop, or a code repository with no metadata in sight, ask in one line where the workspace should go.
3. `schemify.py init --study "<name>" --invoke "<the command alone: /schemify or $schemify>" --harness <claude-code|codex|cursor|other>`. The name is the study's as the user or a file name gives it; with nothing better, the folder's name — a working name the opening interview confirms.
4. `schemify.py open --harness <…> --model <…>`; relay `tell_user`, adding that they should keep the website open — it is where they will answer your questions and watch progress. If you run on another machine than their browser (an SSH session, a cluster), give WEBSITE.md's port-forwarding command with the link.
5. Introduce the method in four plain sentences, adapted to the user: you will read their documents and look for more online; you will ask questions in batches on the website, each with a recommended answer; you will build the data description — JSON Schema files — one topic at a time, testing each on made-up data, and they review each topic; everything is saved, so the work can span sessions.

## 2. Register the sources

For each file the user named, and each file in a folder they named (hidden and temporary files such as `~$…` and `.DS_Store` aside). Files they did not name — a README beside the dictionary — you only list by name, from the named files' folders and the invocation directory's top level, and ask about them in the interview.

1. **Documentation or data?** Data dictionaries, codebooks, questionnaires, protocols, papers, cleaning code, and data-portal pages are documentation. A file law 2 says is data — or one you cannot place from its name, folder, and the user's words (`baseline_2024.csv` in `exports/`) — stays closed: not copied, extracted, or measured. Ask about it as the first item of the opening batch (INTERVIEW.md). A data file with embedded labels (SPSS, Stata, SAS): ask the user for a metadata-only export — variable names, labels, value labels; never values or frequencies.
2. Copy each documentation file to `schemify/sources/<its original file name>` — the workspace must travel complete. A web page the user gave you is registered by URL, not copied.
3. Record it: `{"type": "source", "event": "add", "kind": "document", "title": "…", "what": "one line: what it holds", "path": "sources/<file name>", "original": "<the user's path>", "origin": "user"}` — `title` and `what` come from the user's words or the file name until you have read it (refine them later with `update`). For a page the user gave you: `"kind": "web", "url": "…", "origin": "user"` (no approval needed: they chose it). `record` prints the source's id.
4. Extract it: `extract.py schemify/sources/<file name> --out schemify/sources/<id>/extract --id <id>`; add `--documentation` for a `.csv`, `.tsv`, tabular `.txt`, `.json`, `.jsonl`, or `.ndjson` only when the user called it documentation (a JSON file is often the data itself — an array of records). Record `{"type": "source", "event": "extract", "id": "<id>", "dir": "sources/<id>/extract", "files": <the manifest's files_total>}`. Note the manifest's `locators` line — it is how you will cite this source. For a workbook, read `stats.sheets` before any sheet: `stats.skipped_sheets` names sheets left out because they look like records — never read them; ask the user, and only if they say a sheet describes variables, extract again with `--include-sheet "<name>"`. A sheet of records that slipped through (one row per person) is data too: never read it; tell the user. Cleaning code extracts as text with its embedded data lines blanked; a warning names them.

## 3. Post the opening interview

Right after registering, look at the first lines of each extract for the study's name, acronyms, and ids — they shape the name question and brief the subagents — and post INTERVIEW.md's opening interview, adapted to what you know: a question about each file you could not place (first), the study's name when it is a working name, and the files you saw but were not given. Then `build`, then `check`, and tell the user, in one message: "While I read your documents and look for more about the study, please answer the N questions waiting on the website (about N minutes): <link>#questions. Reply *done* when you have sent them." In Codex, add: start the reply with `$schemify`. On a website opened from disk, QUESTIONS.md ("Posting") says what they do instead of sending.

## 4. Digest every source

A digest (`schemify/sources/<id>/DIGEST.md`) is what a later session reads instead of the source: what the source holds, how to read it, and every variable and rule it states — with locators, and codes and labels copied exactly. Delegate in one message: one digest subagent per source and the research subagent (step 5), all in parallel, with SUBAGENTS.md's briefs. Without subagents, digest sources yourself, one at a time, largest last; split a large source into chunks (sheet by sheet, 20 pages at a time) and write each chunk's part before reading the next.

When each digest returns:

1. **Spot-check it**: open the extract at three or more of its locators — per chunk for a chunked source — the first variable, one variable with codes, and one skip instruction if it found any, and compare; for a scan, compare with the page image, not its text layer. A wrong locator or a changed label means the digest is unreliable: fix it, or redo that chunk yourself.
2. Record `{"type": "source", "event": "digest", "id": "<id>", "path": "sources/<id>/DIGEST.md", "variables": <n>, "verified": ["<locator>", …]}` — every locator you checked, across chunks; leave out `variables` for a source that defines none by name (a questionnaire whose questions the digest mapped to variables where it could).
3. Refine the source's `what`, and note parse quirks (a merged header, a code list on another sheet, a Word file whose layout was lost) as an `update` event's `notes` — the next session reads them instead of rediscovering them. A questionnaire whose routing depends on layout and arrived as Word: ask the user for a PDF of it.

## 5. Research the study on the web

The research subagent (SUBAGENTS.md) looks for the study's site, published codebooks and questionnaires, data-portal variable pages (dbGaP, consortium catalogues), cohort-profile papers, and harmonisation documents. With only a generic name, give it the dictionary's title words too. Without web access (or when it reports it could not search), say so once and ask the user for links instead; when it finds nothing, say that — and if the interview later gives the study a different name, search again with it.

Register each finding worth asking about as `{"type": "source", "event": "add", "kind": "web", "title": "…", "what": "what it would settle", "url": "…", "origin": "agent"}` — it starts `suggested`. You may read a suggested page to decide whether to propose it, but nothing from it reaches a schema, a question's recommendation, or a decision until a person approves the source on the Sources & decisions tab (the plan batch's note points there). A finding that contradicts the user's documents becomes a `conflict` question once approved — never a silent correction.

## 6. Inventory

1. Write `state/variables.csv` — one row per variable any source defines, and one per field inside a variable that holds several values, named by its path (`household[].age`; NESTED.md, "Names") (LEDGER-FORMAT.md): `status` `include`, `source` the reference of its primary definition, `table` and `topic` blank until the plan, `note` naming other sources that also define it. A variable two sources describe differently stays one row; the difference becomes a question when its topic is drafted.
2. For a structured dictionary of hundreds of variables, generate the rows from the digests' `variables-found.csv` files or the extract with a short script of your own rather than by hand — then spot-check five rows.
3. Count the variables, the documents, the skip-logic signals the digests reported, and the variables whose shape is not a single value — check every digest's shape column; read NESTED.md if any is a group, a list, a lookup, mixed, or unclear. Those numbers size the plan.

## 7. Plan

Take the interview's answers first if they have arrived (INBOX.md). If not, post the plan batch anyway — it blocks your work — and tell the user both batches wait, the interview first. The plan batch is INTERVIEW.md's "The plan questions": grain and tables, missing-value codes, how nested values are delivered (when any variable holds several values), the topic list, the suggested web sources, and the session plan, each with your recommendation drawn from the digests:

- **Topics** come from the source's own structure — its sections, sheets, form pages, variable-name prefixes. Only a flat source is grouped by meaning. A variable that holds several values stays in one topic with all its fields. Under about 20 variables with no natural sections: one topic. Present them in the question's `context`, one line per topic: topic · variables · three examples · why — plain text, since the page keeps line breaks but shows no Markdown; with more than about 15 topics, one line per section with its topics and counts.
- **Missing-value codes** are the source's own; the question confirms which mean "skipped by design" (structural) and what an empty cell means in the delivered data.
- **The session plan**: about two to four topics per session; a topic whose skip logic lives mainly in a questionnaire counts double. With hundreds of variables, this first session is setup and plan only.

When the answers come back, apply them:

- `project.json`: `study` (as confirmed), `slug` and `idBase` to match it (or, for `idBase`, the `$id` namespace a source already gives the study's schemas), `description` (one paragraph for the README), `tables` (name, title, grain, mother), `topics` (id, title, table, file — in reading order), `conventions.sentinels` (code, meaning, structural, decision), `people`, `preferences`, `plan` (sessions, note).
- `state/variables.csv`: fill the `table` and `topic` columns.
- Record `apply` for each plan decision.
- Record every rule the digests found (SKIP-LOGIC.md, "Recording rules"), now that each has a table: `waiting` for documented and implied rules, `suspected` for ones you only believe in. Their consent questions go out with their topics.

## 8. Scaffold

1. `package/schemas/common/defs.json` — the invariant special codes (`const`, `title`, `x-value-kind`, `x-provenance`) and the id and date patterns already known (SCHEMA-STYLE.md).
2. Each table's mother — every topic's `$ref` in topic order, no rules yet (SCHEMA-STYLE.md) — and one file per topic holding only its header: `$schema`, `$id`, `title`, `type: object`, `x-variable-group`, and `"properties": {}`. BUILD.md fills them; a topic stays *planned* while its file has no properties.
3. `schemify.py build`, then `schemify.py check` — green before anything else.
4. Continue into the first topic (BUILD.md) if the session has room; otherwise close with `next: build topic <first topic>`.

## Later sources

A user may bring a new document in any session. Register, extract, and digest it as above; add its variables to the inventory; compare it with what is already drafted — every disagreement is a `conflict` question; every new variable joins a topic (or a new one, with the user's yes). A new topic's `$ref` goes into the mother after the other topics' and before the first rule.
