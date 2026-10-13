The project website: what each part shows, how to point people at it, how it is served, and what to do when it misbehaves. Read this once per session before you first point someone at the website (relaying `open`'s `tell_user` does not count), when a person asks how to use it, and when it misbehaves.

Table of contents

- [What it is](#what-it-is)
- [The six tabs](#the-six-tabs)
- [How feedback travels](#how-feedback-travels)
- [Presenting work](#presenting-work)
- [Serving and offline use](#serving-and-offline-use)
- [Troubleshooting](#troubleshooting)

## What it is

`schemify/index.html`, built by `schemify.py build` from the ledger, `project.json`, and the schemas — never edit it or anything under `site/`. It is how people who do not read JSON follow the work, review it, and talk back. It updates itself while served: the page re-reads its data every few seconds and shows your `activity` line live.

## The six tabs

- **Overview** — where things stand: a progress bar, *Your turn* (what waits on the person: questions, topics to review, web sources to approve, unsent answers), the journey through the phases, the topics with their status, the checks in plain words, recent sessions, and how to continue later.
- **Questions** — your batches for whoever is *Answering as* (batches for the other person are listed below, folded). Each question shows the sources' words, the options, your recommendation with its reason, *Something else*, and *I'm not sure*. *Accept all recommendations* answers a batch in one click; the person can still change any answer before sending.
- **Dictionary** — the schemas drawn as a data dictionary (json-schema-data-dictionary): codes, ranges, special codes, and the skip patterns that set them; keyword search, optional semantic search, Excel export. Every row has a **Details** button: where each part comes from (document, web source, a person, or your guess ⚑), the decisions and rules about it, and a comment box with quick tags. A topic in review shows a banner with *Looks right* and *Something's wrong*. The dot on *Details*: green — traced to sources or people; amber — includes a guess awaiting review; blue — a question about it is open.
- **Skip logic** — every rule in the schema, grouped by the variable that decides, read aloud ("If smk_ever = 2 (No) → cigs_day = 777"), with its evidence and source; rules you inferred are marked ⚑ with your reason and a *Looks right* button. Below: rules not in the schema — suspected, deferred, declined, waiting, or not expressible.
- **Sources & decisions** — every source (suggested web pages get *Use it* / *Don't use it*), every decision with filters (your guesses to review, answers from people, open, all) and search, and the people.
- **Data check** — the toy data in an interactive table, every validation error pinned to its cell with a plain explanation (hover a red cell; F8 jumps to the next), the column's allowed values in its header, and charts that filter on click; then the real-data check, privately in QuaC, sending back findings without data (DATA-CHECK.md) — kept checked automatically (*Connect QuaC*: QuaC keeps the file in its own tab and re-checks whenever the agent asks, the page forwarding only the findings; the website must be served), or by hand, one run at a time; for public data, or an agent on a model the person controls, a form that lets the agent run QuaC on a named file itself, and a *Stop* button per file; a history shows the mismatches shrinking run by run, the agent's runs marked. The interactive table loads its engine from cdn.jsdelivr.net the first time; offline, the same rows show in a plain table.

The header shows whether the page is connected to you, *Answering as* (author or data steward — it labels every answer's provenance; it starts as data steward when the project is in review mode, and each browser remembers its choice), and *Note to your agent* for anything the person wants to tell you.

## How feedback travels

Everything a person does on the page lands in an outbox (kept in their browser, so nothing is lost on reload). *Review & send* shows the list; then:

- **Connected** (served by `serve.py`): *Send to your agent* posts it to `schemify/inbox/pending/`. The page tells them to reply "done" (in Codex: "$schemify done").
- **Not connected** (opened from disk, or the server stopped): *Download as a file* saves `schemify-feedback-<study>-<time>.json`; they tell you where it is and you `inbox import` it. *Copy* puts the same JSON on the clipboard for pasting into chat.

## Presenting work

- Link the exact place: `<website>#dictionary/topic/<topic id>`, `#questions`, `#skip-logic/R004`, `#evidence/sources` (web sources waiting for an OK), `#evidence/decision/D014`, `#dictionary/var/<table>/<variable>`, `#data-check`.
- Say what to look at and what is being asked: "The *Smoking* topic is ready: check that the labels and codes read the way you would describe them. Four questions wait under Questions — about 4 minutes."
- Never ask a person to approve "the schema"; ask whether the dictionary says what they would say about their study.
- Run `build` after every change you want them to see; while served, the page refreshes itself.

## Serving and offline use

- `schemify.py open` starts the server (`127.0.0.1`, one fixed port per workspace) and prints the address. It keeps running between sessions so people can answer at any time, and stops a day after the last page closed.
- Opened straight from disk (`schemify/index.html`), the page shows everything; sending becomes downloading, and it does not update live — reload it after a `build`.
- People can serve it themselves without you: `python3 schemify/tools/serve.py` from the folder that contains `schemify/` (Ctrl-C stops it). START-HERE.md says so too.
- Semantic search is off until a person turns it on; it then downloads a small model (about 50 MB from huggingface.co and cdn.jsdelivr.net) once. Their schemas and searches never leave the browser.

## Troubleshooting

- **The server did not start** (`open` reports `websiteNote`; some harnesses block background processes or listening ports): do not retry it or try other ports. `tell_user` already gives the person the file link, what changes from disk (reload after each `build`; *Download as a file* instead of sending), and the command `python3 schemify/tools/serve.py` to run in their own terminal — relay it. They pick one way before answering: unsent answers stay with the address they were typed at. A later `open` simply tries again.
- **You run on another machine** (a server, a cluster) and their browser cannot reach 127.0.0.1 there: they forward the port — `ssh -L <port>:127.0.0.1:<port> <host>`, then open the same address — or open `index.html` from a synced copy and send answers as a downloaded file.
- **The page says "Not connected"** but you started the server: it stopped, or the port changed. `schemify.py serve status`; `serve start` again and give the new address. Unsent answers are kept in their browser only for the same address — the fixed port keeps it the same.
- **The page shows old data**: run `build`; reload the page.
- **The page is blank or says its data could not load**: run `build`; if it persists, `refresh-assets`, then `build`.
- **The dictionary is empty**: no topic is drafted yet, or a schema file does not parse — `check` names it.
- **A person sent answers but `inbox list` is empty**: they were not connected — ask for the downloaded file (INBOX.md).
