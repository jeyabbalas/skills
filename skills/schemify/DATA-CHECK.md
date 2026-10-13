Checking the schemas against data: toy data you author (the unit tests, and the user's practice set), and the user's real data, which only they touch — in QuaC, privately, by hand or kept checked from the website — sending you back findings without data, unless they allow you to run QuaC on a public file or from a model they control. Read this when writing or editing toy data, when a person asks about their real data, and when `next` says `triage-alignment` or `run-data-check`.

Table of contents

- [Toy data](#toy-data)
- [The ledger of planted mistakes](#the-ledger-of-planted-mistakes)
- [Real data: the person's job, not yours](#real-data-the-persons-job-not-yours)
- [Kept checked in QuaC](#kept-checked-in-quac)
- [When the person allows it](#when-the-person-allows-it)
- [When to suggest a data check](#when-to-suggest-a-data-check)
- [Triage](#triage)

## Toy data

Toy data is made up from the documents — never sampled, copied, or paraphrased from real data — so it is safe to commit, share, and show. Per table, in `package/toy-data/<table>/`:

- `valid.json` — rows that must all pass. Start from one complete, plausible row; make every later row a copy that changes only what its scenario needs, so every row stays consistent with every rule. Together the rows must contain: every code of each code list (lists over 12 codes: the first, the last, and every special code); the exact lowest and highest plausible value of each measure; each special code of each variable; for each rule, a row where it fires and holds on each side of its gate, and an in-universe row carrying an item-missing code (refused, don't know) — the case an applicability rule must allow; one value matching each pattern. Keys in schema order; special codes written as values (`-666`, never `null`).
- `invalid.json` — one planted mistake per row; every other value legal. Make each row by copying a valid row and breaking one thing.
- `invalid-ledger.json` — which column each invalid row breaks, and why (next section).

`build` writes a CSV twin of each file — the format most people's real data arrives in. `validate.py fixtures` (run by `build`) proves the valid rows pass and each invalid row fails on exactly its column, and reports what the valid rows do not yet cover; a topic is *tested* only at full coverage.

`build` also validates each toy file for the website: its Data check tab shows the rows in an interactive table, every validation error pinned to its cell and explained in the validator's words, with each planted mistake's reason beside it. Point people there to see what a mismatch looks like before they check their real data.

## The ledger of planted mistakes

```json
{
  "violations": [
    {"row": 0, "column": "sleep_minutes", "kind": "range-break", "value": 1500, "reason": "above the plausible 960 (D002)"},
    {"row": 1, "column": "chronotype", "kind": "unknown-level", "value": 9, "reason": "9 is not a code the dictionary defines"},
    {"row": 2, "column": "nap_minutes", "kind": "skip-break", "value": 45, "reason": "R001: no nap yesterday, yet a duration"},
    {"row": 3, "column": "nap_minutes", "kind": "applicability-break", "value": -666, "reason": "R001: a nap, yet 'not applicable'"},
    {"row": 4, "column": "sleep_minutes", "kind": "invented-sentinel", "value": -999, "reason": "-999 is no code of this study"},
    {"row": 5, "column": "participant_id", "kind": "pattern-break", "value": "P12", "reason": "ids are P + 4 digits"},
    {"row": 6, "column": "site_id", "kind": "wrong-type", "value": 1, "reason": "site codes are strings with a leading zero"},
    {"row": 7, "column": "age", "kind": "missing-key", "reason": "every column is required"},
    {"row": 8, "column": "shoe_size", "kind": "undeclared-column", "reason": "not a variable of this study"}
  ]
}
```

Rows count from 0. Kinds: `wrong-type`, `unknown-level`, `range-break`, `invented-sentinel`, `pattern-break`, `skip-break`, `applicability-break`, `routing-break` (a pin or narrowing rule), `missing-key`, `undeclared-column`, `duplicate-row`. Plant at least one of each kind the package's constructs use, and per rule: a `skip-break` and an `applicability-break` for each pair, a `routing-break` for each other rule — with the rule id in `reason`. A `wrong-type` value must stay wrong in the CSV twin, which reads digits back as a number: put a word in a numeric column ("two"), never a quoted number ("1").

## Real data: the person's job, not yours

You never open, read, sample, count, or run anything on real data (SKILL.md, law 2) — the data use agreement binds the person, not you, and you cannot tell what it allows. Asked to look anyway, give law 2's one-line reason. Instead the website's Data check tab gives them QuaC, which runs entirely in their browser — kept checked automatically (next section), or by hand, one run at a time:

1. Open QuaC (https://jeyabbalas.github.io/quac/).
2. Drop their data file into *Dataset* and the folder `schemify/package/schemas` into *JSON Schema* (with several tables, QuaC asks which schema is the table's — the `<table>.schema.json`).
3. *Run QC*, then *Findings without data* → *JSON*.
4. *Reset* QuaC — it keeps loaded files in the browser until they do.
5. Drop the findings file on the Data check tab and send it.

The findings hold the schema's own wording, the dataset's column names, and counts — no values (QuaC builds them that way). The website replaces the dataset's file name with a label the person chooses and shows them exactly what will be sent. People comfortable with a terminal can run QuaC's command line themselves — the tab shows the command; you never run it on their data.

You may run QuaC on the **toy** data yourself to show what findings look like: `npx --yes @jeyabbalas/quac@1.2.0 schemify/package/toy-data/<table>/invalid.json --schema schemify/package/schemas --no-report --findings <a temporary file outside the workspace>` (Node 24+).

Never ask for example values, row counts by value, or "a few rows". A person who volunteers something about their data ("999 shows up in age") has given you metadata — record it as `knowledge` — but never ask for more than that.

Data never enters the workspace. If a data file appears in `schemify/`, do not open it: ask the person to move it out. If someone pastes rows, values, or a findings file with values into the chat, stop: do not quote it or record it; tell them you have not used it, ask them to delete it where they can, and point them to findings without data.

## Kept checked in QuaC

On the Data check tab, *Connect QuaC* opens QuaC in its own tab; the person loads their file there once (QuaC keeps it between visits) and presses *Allow*. The website records a dataset with basis `browser` (`inbox take`: `X01`, no path) and sends the findings of a first check. None of this is an exception to law 2: the data stays in their browser, and you receive what any findings file holds.

- **Re-runs.** `next` lists `run-data-check` for it as for a file you run yourself, and the loop is the same (below). `schemify.py data-check X01` asks the open website to have QuaC re-check against the current schemas and waits for the findings — seconds, for most files.
- **When it fails,** it says what the person must do — open the website and *Connect QuaC* (one click: QuaC still has the file), or load the file in QuaC — and imports nothing. Tell them in one line, and do not retry until they say it is done. Findings that arrive later wait in the inbox (`process-inbox`).
- **It never holds up the end:** `finish` does not wait for the person's browser.
- **Stopping:** *Stop for good* on the website withdraws it; `inbox take` records the `withdraw`.

## When the person allows it

A person may let you run the check yourself, for one named file, when the data is public, or when you run on a model they control (self-hosted) and their data use agreement allows that model to process it. Only they can decide that.

- **Never suggest it to someone whose data is not public.** Bring it up only when they say the data is public, or that their agent runs on their own model, or when they ask whether you can run the check. Otherwise the steps above are the way.
- **Recording it.** They allow a file on the website (Data check tab, *Let your agent run the check itself*; `inbox take` records it), or in chat. In chat, ask one question when their words leave the basis open — "Is the data public, or does your agent run on a model you control?" — and for their own model, say which model you run on (the one you pass to `open --model`) and record only once they confirm it is theirs: `{"type": "dataset", "event": "allow", "path": "<the path as they gave it>", "label": "<their name for it, or a few of their words>", "basis": "public", "by": "author", "via": "chat", "text": "<their words>"}` — `basis` is `local-model` for their own model, and the permission then covers only the model of this session; add `table` when the package has several tables, and `sheet` for a workbook with several sheets. The file stays outside `schemify/`.
- **Running it.** `schemify.py data-check X01` runs QuaC on the file against the current schemas and imports the findings without data as a new run, the file's name replaced by the label. `next` lists `run-data-check` whenever what the schemas accept changed since that file's last run (titles, descriptions, and comments alone do not count), at a resting point: after a clean `build`, with a topic tested and none being edited, and no posted data-check question waiting on a person. QuaC's own messages never reach you — they can quote the data. If the command fails, tell the person in one line, give them the `command` it prints to run in their own terminal, and do not retry until something has changed.
- **The loop.** Triage each run (below) — at first only your own slips: fix them all and `build`, leaving the other checks without a verdict. `next` then brings the re-run, ahead of any questions, and the new run replaces the old one: `show` marks the old one `supersededBy`, and it needs no more verdicts. Triage the new run in full, and only then post its questions, so they carry the counts that remain. A check you fixed as your slip that still fails is a question, never a second fix (`show` lists each check's `earlier` verdicts). A person who says "fix what you can" still means your slips only: a value the documents do not define is theirs to explain, never yours to guess.
- **Still never.** The permission covers QuaC through `data-check`, nothing else: you never open, read, sample, count, or copy the file, and never run anything else on it.
- **Stopping.** When they say stop — in chat, or *Stop* on the website — record `{"type": "dataset", "event": "withdraw", "id": "X01", "by": "author", "via": "chat"}`; `data-check` refuses the file from then on. A file that moved needs a new `allow`, after withdrawing the old one.

## When to suggest a data check

- Once the first topic is *tested* and `preferences.realData` is `yes`: offer it once, in one line, pointing at the Data check tab — *Connect QuaC* keeps it checked from then on. Optional; never nag. For a file they allowed you to check, there is nothing to offer: `next` runs it. `elsewhere`: when you finish (FINISH.md), say the data's holder can run it from the website the user shares. `notyet`: only when they bring it up.
- After a round of fixes that came from findings: suggest re-running with the current schemas — the tab's history shows the mismatches shrinking.
- Before finishing (FINISH.md): offer a last check.

## Triage

`next` says `triage-alignment` after a findings file arrives, or after a `data-check` run. `schemify.py show A01` lists each failing check: its `key`, the variable, its topic, the rule id when a conditional failed, the schema's wording of the requirement, and how many records failed. If `current` is false, the findings came from an older version of the schemas — triage what still lines up and ask for a re-run when it matters. A check marked `notBuiltYet` is a column of a topic you have not built yet: it needs no verdict, and the first run after that topic is built checks it again.

Take each check `show` lists through these steps; the first that applies gives its verdict:

1. **Your slip** — the schema does not say what its cited source says (a code mistyped, a special code left out, a rule encoded the wrong way round). Read the source line its `x-provenance` cites (`sources/<id>/extract/`) beside the schema; `check` warns `sentinel-dropped` when a property rejects a special code its dictionary row lists. Make it match the source, and record `schema-fix` with a `note` saying what changed. This is the only verdict you give on your own.
2. **Already answered** — a person already settled this mismatch (an earlier data-check question, a comment on the topic; `show variable:<name>` lists the decisions about it, and `show A01` each check's `earlier` verdicts): record the verdict their answer gives, citing that decision. Match by variable and what failed, not by key — a key changes with the schema's shape. An answer about another file carries over when it was about the schema — `clean` (the schema is right; tell them this file's records need the same cleaning) or `change` — but `accept` covered the records they had checked: ask again. Still unanswered: verdict `question`, citing the same decision — never a second question. A check failing against a change an answer just made is new: the answer said what the schema should say, not what the data holds.
3. **Everything else is a question** — a code the documents never mention, a bound the data exceeds (the documents' or your guess), a rule that fails, an unexpected column, a missing variable, however few or many records fail: ask, and record `question` with that decision.

An alignment question (`kind: alignment`, QUESTIONS.md) goes `to` the person `show` names in `askTo`: whoever sent the findings or allowed the file you checked — the steward instead of a `limited` author. Its evidence quotes the requirement with the counts — `{"ref": "A01", "quote": "nap_minutes: when nap_yesterday = 0, must be -666 — 112 records (4%)"}` — and the source line the requirement comes from; an unexpected column has none — say no document mentions it — and is named in `targets`, with the run's `table` (`show` prints it). Checks that one explanation would cover — several variables missing from the dataset (a partial extract?), the same code wrong across a block of variables — share one question, and each of their triage events cites it. Its options carry these ids, so each answer maps to a verdict: `clean` — the data needs cleaning (`data-issue`); `change` — the documents or the schema are wrong, change it (`schema-fix`); `accept` — known and accepted: test records, a documented exception (`expected`). Its `provisional` is `clean`: the schema stays as it is.

Asking how something is coded — what a code means, which codes a variable uses — is metadata. Asking which values occur, or how often, is asking for data: never do it, and never ask for "a few rows".

When the answer arrives, apply it (INBOX.md) and record the check again with the verdict it gives — `schema-fix`, `data-issue`, or `expected` — citing the answered decision; `data-issue` and `expected` always cite one. "Not sure" leaves the schema as it is and the check a `question`, flagged for the steward. A rule a person says is wrong: take its conditional out of the mother — the entries after it move up one place, which is safe, since every run keeps the rule map of the schemas it ran on — and `set` it `declined`, citing that decision.

Never loosen a schema just to make data pass: a value the documents do not define is a question, not a fix. Record each verdict: `{"type": "alignment", "event": "triage", "id": "A01", "check": "<its key, exactly as show prints it>", "verdict": "question", "decision": "D041", "note": "…"}`.

Once every answer is applied and the package rebuilt (`build`): tell the person plainly which checks point at their data (`data-issue`), so they can pass them on, and invite a re-run with the current schemas — not before. For a file they allowed you to check, run it yourself when `next` says so, and tell them what the re-run shows.
