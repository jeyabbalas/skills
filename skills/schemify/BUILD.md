The topic loop: one topic carried from its sources to a person's confirmation. Read this when `next` says `build-topic`, `present-topic`, or `revise-topic`. It sends you to SCHEMA-STYLE.md (the JSON), SKIP-LOGIC.md (rules), DATA-CHECK.md (toy data), and QUESTIONS.md (asking).

Table of contents

- [The loop](#the-loop)
- [1. Orient](#1-orient)
- [2. Draft](#2-draft)
- [3. Skip logic](#3-skip-logic)
- [4. Toy data](#4-toy-data)
- [5. Verify](#5-verify)
- [6. Present](#6-present)
- [7. Keep going](#7-keep-going)
- [Revising a topic](#revising-a-topic)

## The loop

| step | done when | topic status |
|---|---|---|
| 1. Orient | you know the topic's variables, their locators, its open decisions, and the rules waiting on it | planned |
| 2. Draft | the category file exists; every variable's shape is settled; every judgment is a decision; every property and nested field has `x-provenance` | drafted |
| 3. Skip logic | every rule touching the topic is recorded; licensed ones are encoded | drafted |
| 4. Toy data | valid and invalid rows cover the topic's codes, bounds, and rules | drafted |
| 5. Verify | `build` shows no errors for the topic and full toy-data coverage | tested |
| 6. Present | its questions are posted and `topic present` is recorded | in review |
| — | a person approves it on the website | confirmed |

Statuses are computed — never set them by hand. A topic is finished for you at step 6; confirmation is the person's.

## 1. Orient

1. `schemify.py show topic:<id>` — its file, its table, its inventory rows with locators, the decisions and rules that touch it.
2. Read the topic's part of each digest; open the extract at the locators for every code list and label you will transcribe. For questionnaire pages where layout carries skip logic, view the page itself.
3. When the person answering this topic's questions is a steward (`profile: steward` in `project.json` → `people`), post the topic's knowledge batch first unless the topic is trivial (INTERVIEW.md) — and draft meanwhile.

## 2. Draft

Fill `package/schemas/<table>/categories/<topic>.json` — the scaffold made it with empty `properties` — following SCHEMA-STYLE.md exactly. For every variable in the topic:

1. Shape first: does it hold one value, or several — a group of fields, a list of values, a list of entries, a lookup? Look for the signals in NESTED.md ("Spotting a nested variable") even when the digest says `value`, and follow how the plan settled its delivery. A nested variable whose delivery nobody settled is a `structure` question (NESTED.md) — draft it once it is answered, never as flat columns meanwhile. Each field inside is then drafted by the steps below, with its own title, codes, and `x-provenance`.
2. Transcribe: title (the source's label, lightly cleaned — a rewording is a `guess`), codes and their labels verbatim, special codes, ranges, formats. Copy the source's coding text into `$comment`. A code the source lists without a label is a `gap` question — never write a label for it.
3. Add `x-provenance`: `default` cites the variable's own line in the source; list a facet only where its origin differs.
4. Every place you go beyond the source is a decision, recorded as you go:
   - a choice no person needs to make now (a plausibility bound, a normalized label, an id pattern) → `{"type": "decision", "event": "decide", "kind": "guess", "topic": …, "targets": […], "question": "…", "choice": "…", "why": "…", "applied": true}` — cite it on the facet;
   - sources that disagree → a `conflict` question; a source that is silent where it matters → `gap`; unclear wording → `ambiguity`. Each is `open`, with `provisional` naming the option you encode meanwhile — the loosest reading the sources support — and cited on the facet. Post them in step 6.
5. A variable that cannot be drafted yet (its code sheet is missing, its meaning is unknown) → `variables.csv` status `deferred`, the note naming the decision; it stays out of the schema.
6. A variable no source defines but a person asked for → `variables.csv` status `added`, `source` the decision.

The mother already references the file (START.md, step 8).

## 3. Skip logic

Follow SKIP-LOGIC.md: scan the topic's sources for every signal; record each rule as you notice it (`waiting` when a variable lives in a topic not drafted yet); encode documented, implied, and told rules whose variables now exist — including rules that were `waiting` on this topic (`status` lists them as `encode-rules`); suspected ones go into this topic's consent question (step 6) and nowhere into the schemas. Append encoded rules to the end of the mother's `allOf`.

## 4. Toy data

Extend `package/toy-data/<table>/valid.json`, `invalid.json`, and `invalid-ledger.json` to cover the topic: every code and special code, each bound, both halves of each encoded rule, one planted mistake per invalid row (DATA-CHECK.md, "Toy data") — inside nested values too, entry by entry. Every row holds the columns of every built topic and no other (the mother rejects the rest), so a new topic's columns go into every existing row too, each consistent with that row's scenario. Rows touching a suspected rule stay consistent with it, and none tests it yet.

## 5. Verify

1. `schemify.py build` — it runs the validator. Read `checks.headline`, then `schemify.py check`; fix every error before going on. Common findings and their fixes are in each finding's `hint`.
2. `schemify.py status` shows the topic as `tested` once its file is clean and the toy data covers it. Still `drafted`? `state/checks.json` → `topics` → `<table>/<topic>` → `coverage` says what the toy data misses.

## 6. Present

1. Post the topic's batch (QUESTIONS.md): its conflicts, gaps, and ambiguities; one consent question for its suspected rules; confirmations of rules encoded from implied evidence; and one `bulk` review of your guesses if there are more than two. A topic's batch goes out even while the person's previous topic batch waits — the website lists them in order — but never a third: with two of their batches open, keep drafting and present this topic when one comes back.
2. Record `{"type": "topic", "event": "present", "id": "<topic>", "note": "what to look at: e.g. 12 variables; the alcohol codes come from the 2019 dictionary"}` — in the same payload as the batch.
3. `schemify.py build`, then `check`, then tell the user in one or two lines: the topic is ready on the website, how many questions wait (with minutes), what to look at first — and what to reply when done.

## 7. Keep going

Do not wait idle for answers: start the next topic's loop while the user reviews. Take their answers when they arrive (INBOX.md) — in this session or the next. Stop at the session's plan; close with `next` naming the next topic.

## Revising a topic

When a person asks for changes (`next` says `revise-topic`), or anything changes a topic a person already approved — a later answer or a comment (INBOX.md), a slip you fix (DATA-CHECK.md): once its file is not what they approved, `next` says `present-topic` again:

1. `schemify.py show topic:<id>` → the `changes` entry holds their words; their comments are `feedback` decisions with the variables as targets.
2. Make the change. When it overturns a decision a facet cited, record the new decision, then `{"type": "decision", "event": "supersede", "id": "<old>", "replacement": "<new>"}`, and re-cite the facet.
3. Re-check every rule naming a changed variable — a recoded gate silently breaks its rule, and a new code on a gate is a question (SKIP-LOGIC.md, "Skip pairs") — and redo steps 4–5 (toy data, verify).
4. Present again (step 6) with a note saying exactly what changed — the website shows it above the topic.
