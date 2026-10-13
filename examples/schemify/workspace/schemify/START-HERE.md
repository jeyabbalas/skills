# Ashgrove Community Health Survey (ACH) — schemify workspace

This folder holds the work of turning the study's data documentation into JSON Schema files: the schemas themselves (in `package/`), and everything the agent needs to remember between sessions.

## See progress and answer questions

Open **`index.html`** in this folder (double-click it). That is the project website: progress, the agent's questions, the data dictionary, skip logic, sources and decisions, and the private data check.

When the agent is running it serves the same page at a local address (it tells you which) — use that one: it sends your answers straight to the agent and updates live. Opened from disk, the page still works; your answers are kept in the browser and you can download them as a file for the agent.

To serve the website yourself, without the agent: `python3 tools/serve.py` from this folder (Ctrl-C to stop).

## Continue the work

1. Open your coding agent in `examples/schemify/workspace` — the folder that contains this one.
2. Then type `/schemify`.
3. The agent reads its notes here, tells you where things stand, and continues. You never need to re-explain anything.

Large dictionaries take several sessions; nothing is lost in between.

## Share for review

To have the study's data steward review the work, ask the agent to prepare it for review — it makes a zip of this folder and tells the steward what to do. (`package/` alone is the finished deliverable.)

## What is where

- `package/` — the deliverable: schemas, toy data, README, provenance, a standalone data dictionary, a validator.
- `state/` — the agent's working memory. Do not edit by hand.
- `sources/` — copies of the documents the work is based on, and what the agent extracted from them.
- `inbox/` — feedback sent from the website.  `alignment/` — data-check summaries (they contain no data).

