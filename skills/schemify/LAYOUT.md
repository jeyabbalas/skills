Where everything lives in a workspace, how things are named, and the exact contract of every script command. Read it once per session, right after `open` (START.md and MIGRATE.md give in full the commands that come before it), when creating anything new in the workspace, and when a script fails.

Table of contents

- [The workspace](#the-workspace)
- [Naming](#naming)
- [Running scripts](#running-scripts)
- [schemify.py](#schemifypy)
- [validate.py](#validatepy)
- [extract.py](#extractpy)
- [serve.py](#servepy)
- [migrate.py](#migratepy)

## The workspace

One study, one workspace: the folder `schemify/` in the directory the user invoked you in. It is self-contained — share or move it as a unit.

```
schemify/
├── index.html                ← the project website (built; open it, never edit it)
├── START-HERE.md             ← for people: what this is, how to continue (built)
├── site/                     ← the website's script, styles, library, and data/ (built)
├── state/
│   ├── project.json          ← study, tables, topics, conventions, people, preferences (you edit)
│   ├── ledger.jsonl          ← every source, decision, rule, batch, topic event, session (only `record` writes)
│   ├── variables.csv         ← the inventory of every variable the sources define (you edit)
│   ├── checks.json, toy-checks.json   ← the validator's last reports on the package and the toy data (built)
│   └── activity.json, server.json, server.log   ← runtime
├── sources/                  ← copies of the user's documents, their extracts, and your digests
│   ├── ashgrove_dictionary_r2.xlsx          (each copy keeps its original file name)
│   ├── S01/extract/…, S01/DIGEST.md, S01/variables-found.csv
│   └── MIGRATION.md          ← only after a 1.x migration: the id map and what is left to do
├── inbox/pending/, inbox/done/   ← feedback the website sent (take it with `inbox take`)
├── alignment/A01.json …      ← QuaC findings without data (no values)
├── tools/serve.py            ← lets people restart the website without an agent
└── package/                  ← THE DELIVERABLE — stands alone
    ├── README.md, PROVENANCE.md, provenance.json, dictionary.html   (built)
    ├── schemas/              ← only schema files: people drop this folder into QuaC
    │   ├── common/defs.json
    │   └── <table>/<table>.schema.json, <table>/categories/<topic>.json
    ├── toy-data/<table>/valid.json, invalid.json, invalid-ledger.json (+ valid.csv and invalid.csv, built)
    ├── assets/               ← the dictionary page's library and styles (shipped)
    └── tools/validate.py, requirements.txt   (shipped)
```

Create lazily: `init` makes the skeleton — `state/`, `sources/`, `inbox/`, `alignment/`, `site/`, `tools/`, and `package/` with its `schemas/`, `toy-data/`, `tools/`, and `assets/` folders; everything else appears the first time something is written into it. Never put anything but schema files under `package/schemas/` — QuaC and the dictionary treat every `.json` there as part of the schema set.

## Naming

- Workspace folder: `schemify`. A second study in the same directory: `schemify-<slug>` (`init --dir`), and pass `--ws` to every command.
- Sources: copy each document as `sources/<its original file name>` (on a clash, add `-2`). Once `record` has given it an id, its extract goes in `sources/<id>/extract/`, its digest in `sources/<id>/DIGEST.md`, the digest's variable list in `sources/<id>/variables-found.csv`.
- Tables: `snake_case`. Mother: `package/schemas/<table>/<table>.schema.json`. Topics: `package/schemas/<table>/categories/<topic>.json`, where `<topic>` is the topic id in `project.json`.
- `$id`: `project.json` → `idBase` + the path under `package/schemas/`. `init` derives `slug` and `idBase` from the study name it is given; settle both at the plan (START.md, step 7), before the first schema file — never change `idBase` after.
- Ids: `S01`, `D001`, `R001`, `B01`, `A01` — assigned by `record`, never chosen by you.

## Running scripts

Every script is run, never read: `uv run <skill-dir>/scripts/<name>.py <command> …`. `uv` installs what a script needs on first run. Each prints one JSON object on stdout — `"ok": true`, or `"ok": false` with `"error"` and `"hint"` (do what the hint says). Lists are cut at about 40 items and say `"truncated": true`.

Without `uv`: `schemify.py` and `serve.py` need only Python 3.9+, so `python3 <skill-dir>/scripts/<name>.py …` works as is. `validate.py` needs `python3 -m pip install --user "jsonschema>=4.18" referencing`; `extract.py` needs `python3 -m pip install --user openpyxl pypdf python-docx xlrd striprtf`. If neither route works, drafting may continue, but no topic can reach *tested* — say so to the user and in the handoff.

Run commands from the directory the user invoked you in. `schemify.py` finds `schemify/` there, below, or above; otherwise pass `--ws <absolute path to the workspace>` (before or after the command name).

## schemify.py

| command | does | prints |
|---|---|---|
| `init --study NAME [--dir schemify] [--invoke /schemify] [--harness H]` | creates the workspace (idempotent; on an existing one it restores shipped files). `NAME` may be a working name (the folder's or the dictionary file's); `--invoke` is the command alone (`/schemify`, `$schemify`), never its arguments | `workspace`, `id`, `next` |
| `open [--mode build\|review] [--harness claude-code\|codex\|cursor\|other] [--model M] [--no-serve]` | records the session start (resumes an unclosed one under 12 hours old, closes an older one as unfinished), starts the website, rebuilds its data; without `--mode` the project's mode stays | the `status` payload + `mode`, `website`, `tell_user` |
| `status` | reads everything, writes nothing | `phase`, `counts`, `topics`, `checks`, `lastSession` (with `handoff`, `next`), `next` (ranked actions: `action`, `why`, `read`, ids) |
| `record [--file F]` | validates and appends ledger events from stdin; all or nothing | `recorded`: `[{type, event, id}]` |
| `show ID…` | `S01`, `D014`, `R003`, `B02`, `A01` (with its failing checks and their keys, each check's `earlier` verdicts on the same variable, `askTo`, and `supersededBy` once a later run of the same file replaced it), `X01` (a dataset a person allowed, with its runs), `topic:<id>`, `variable:<name>` | current state + history |
| `queue [--for author\|steward] [--topic T] [--limit N]` | what needs a person, ranked; low-stakes guesses grouped per topic; which of their batches are still unanswered | `items`, `bulkGuesses`, `suspectedRulesUnasked`, `openBatches` |
| `inbox list` · `inbox take ID` · `inbox import FILE` | lists submissions · records everything mechanical in one and moves it to `done/` · brings in a feedback file the user downloaded | `take` prints `recorded` and `todo` — your work list, each item with its decision, kind, question, answer, topic, table, targets, `files` to change, and `do` |
| `build [--no-validate]` | runs `validate.py summary`, regenerates the website's data and the package's generated files | `written`, `checks` (`ok`, `headline`), `website` |
| `check [--strict]` | verifies state, inventory coverage, provenance, rules against schemas, unapplied answers, the inbox, staleness, and runs the validator; before any schema exists it has little to check and is green | `ok`, `blocking`, `counts`, `findings` (each with a `hint`); exit 1 when not ok (`--strict`: also when the website or shipped files are stale) |
| `activity TEXT` | tells the website what you are doing | — |
| `close` | stdin `{"summary": "what happened, two sentences at most", "handoff": "a paragraph: what the next agent must know that the files do not say — a half-done step, the person's preferences, parse quirks", "next": "one concrete step, or done"}`; builds, checks, and refuses while `check` has an error, a submission waits in the inbox, or an answer is unapplied (`blockers` lists them). Fix them, or — when the session must end now — resend with `"force": true` and a handoff naming each blocker | `tell_user` |
| `data-check X01 [--timeout SECONDS]` | (default 1800 seconds) runs QuaC (Node 24+, through `npx`; or the command in the environment variable `SCHEMIFY_QUAC`, for an installed `quac` on a machine without npm access) on a file a person allowed you to check, against the current schemas, and imports the findings without data as a new run; QuaC's own messages are discarded unread. Refuses a withdrawn file, a file inside the workspace, and a `local-model` permission under another model. For a `browser` dataset it runs nothing itself: it asks the open website to have QuaC re-check, waits for the findings (they arrive as a submission, which it takes), and fails at once, saying what the person must do, when no page is connected or QuaC lacks the dataset | `run`, `records`, `recordsFailing`, `checksFailing`, `notBuiltYet`, `current`, `next`; on failure, `command` for the person to run (agent runs) |
| `serve start\|stop\|status` | the website server | `url` |
| `share [--out PATH]` | zips the workspace for a reviewer | `file`, `tell_user` |
| `refresh-assets` | re-copies the website's files, the validator, and `serve.py` from this skill | `changed` |

## validate.py

`uv run <skill-dir>/scripts/validate.py <command> schemify/package …` — the same file ships as `package/tools/validate.py`, so the package checks itself anywhere.

| command | checks |
|---|---|
| `check PKG` | every schema file parses and meta-validates (draft 2020-12); `$id`s and `$ref`s; the house style (SCHEMA-STYLE.md); `x-provenance` on every property and rule, and every reference resolvable against `provenance.json`; every rule in the canonical form (SKIP-LOGIC.md) |
| `rules PKG [--table T]` | prints every rule parsed: id, kind, gates and tests, targets and effects, provenance — read it during the skip-logic audit |
| `fixtures PKG [--table T]` | `valid.json` passes; each `invalid.json` row fails on exactly the column its ledger names; coverage of codes, bounds, and rules |
| `data PKG --file F [--table T]` | validates a data file — **toy data only**: you never run it on real data (law 2) |
| `summary PKG [--out FILE]` | all of the above with a plain-English `headline`; `build` runs it and keeps the full report in `state/checks.json` |

Exit codes: 0 ok, 1 the package fails (read `findings`), 2 bad arguments or missing files.

## extract.py

`uv run <skill-dir>/scripts/extract.py SOURCE --out schemify/sources/S01/extract --id S01` turns a document into text and CSV with locators you can cite: Excel → one CSV per sheet whose `_row` column is the spreadsheet's row number (cite `<sheet> row N`); CSV → a normalized copy (cite `row N`); PDF → one text file per page and `text.md` with page markers (cite `p.N`); Word → `text.md` with `¶N` paragraph numbers and tables as CSVs; HTML, RTF, text → `text.md` (cite `§heading` or `L<line>`).

- It prints the manifest: `files` (each file written, cut at 50 with `files_total` beside it), `locators` (how to cite), `stats` (for a workbook, `stats.sheets` lists each sheet's name and size, and `stats.skipped_sheets` the sheets it left out), and `warnings`. Record `files` as `files_total`.
- It refuses data files (`.sav`, `.dta`, `.sas7bdat`, `.parquet`, …): ask the user for a metadata-only export instead.
- A delimited file (`.csv`, `.tsv`, a `.txt` laid out as a table) can be a dataset or a dictionary, and the script cannot tell; it refuses one unless you pass `--documentation` — only after the user said the file describes variables (law 2).
- A workbook can hide a sheet of records beside its dictionary. A sheet that looks like records — variable names over rows of mostly numbers, or headings that another sheet lists as variables — is not extracted at all: it appears in `stats.skipped_sheets`, unmeasured, with a warning. Never read it; ask the user, and only if they say it describes variables, extract again with `--include-sheet "<name>"` (repeatable). Before reading any extracted sheet, check `stats.sheets` too: a sheet of records the check missed is never read — tell the user.
- Cleaning or processing code (`.sas`, `.do`, `.r`, `.sps`, `.py`, `.sql`) is extracted as text, cited as `L<N>`; rows of data embedded in it (SAS `datalines`, Stata `input` … `end`) are replaced line for line by `[embedded data line, not extracted]`, and a warning names their lines.
- A PDF page with no text layer is reported — view that page directly. A Word file loses indentation and boxes: when routing depends on layout, ask the user for a PDF of the questionnaire.

## serve.py

`schemify.py open` and `serve start` run it for you; it listens on 127.0.0.1 only, on a port fixed per workspace (so the browser keeps the user's unsent answers), serves the workspace, and accepts writes only from the website's own page: feedback (into `inbox/pending/`), and whether the page is connected to QuaC (`state/presence.json`, a few words, never data). Builds point the page at the QuaC app in `SCHEMIFY_QUAC_APP` when set (testing, or a self-hosted QuaC), else at the public one. It stops a day after the last page closed. People can run the workspace's copy themselves — `python3 schemify/tools/serve.py` (Ctrl-C stops it) — and the website also works opened straight from disk, minus one-click sending and live updates. When the agent runs on another machine than the user's browser (a server, a cluster), the user forwards the port (`ssh -L <port>:127.0.0.1:<port> <host>`, then opens the same address), or opens `index.html` from a synced copy and sends answers as a downloaded file.

## migrate.py

`uv run <skill-dir>/scripts/migrate.py --from <the 1.x folder> [--to schemify] [--study NAME] [--person author|steward]` builds a workspace from a schemify 1.x package and never touches the old folder. `--person` (default `author`) is who answered the 1.x questions; `--study` defaults to PROGRESS.md's title, else the folder's name. It writes the first ledger entries itself — its own session included, opened and closed — and prints `sources` (each registered file → its id), `idMap` (1.x decision ids → new ones), and `attention` — what is left to finish by hand, also in `sources/MIGRATION.md` (MIGRATE.md). Standard library only.
