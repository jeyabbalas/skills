How to ask people things: what deserves a question, how to write one so it can be answered in seconds, how contradictions are put, how questions are batched and posted, and what to do without the website. Read this before posting any batch — a topic ready to present, the opening interview, the plan, a follow-up.

Table of contents

- [Ask, or decide and flag](#ask-or-decide-and-flag)
- [Anatomy of a question](#anatomy-of-a-question)
- [Contradictions between sources](#contradictions-between-sources)
- [Reviewing your guesses in bulk](#reviewing-your-guesses-in-bulk)
- [Batches](#batches)
- [Posting](#posting)
- [Without the website](#without-the-website)

## Ask, or decide and flag

Ask a person when the answer changes the schema and you cannot settle it from the sources:

- **Always ask**: sources that contradict each other, or a person who contradicts a source; whether to include undocumented skip logic you suspect (the `consent` question, SKIP-LOGIC.md); anything that would reject real data a person might consider valid; the plan (grain, tables, missing-value codes, how nested values are delivered, topics).
- **Decide and flag** (a `guess`, `review: needed`): plausibility bounds the sources do not state, a normalized label, an identifier pattern inferred from examples, a type. Encode it, cite the decision, and let people review guesses in bulk.
- **Neither**: anything the sources state plainly. Transcribing is not a decision.
- **Steward-only**: with a `limited` author, a question needing specialist knowledge — the plan's grain, tables, missing-value codes, and how nested values are delivered among them — gets your provisional decision (`decide` with `"to": "steward"`), applied at once like any decision and flagged for the steward. It is not posted to the author; REVIEW-MODE.md picks it up. The topic list and the session plan are still asked. Plan questions posted before the profile arrived (START.md, step 7) stay up: tell the author that *not sure* is a good answer to any of them — it applies your recommendation, flagged for the steward.

## Anatomy of a question

Each question is a decision `open` event (LEDGER-FORMAT.md). Write it for a domain expert who has never seen a schema:

- `question` — one plain sentence in the study's words. "Does 777 in *cigarettes per day* mean 'not asked', or can it be a real count?" — not "Should the numeric branch exclude 777?"
- `context` — one or two lines of background only when the question needs it.
- `evidence` — what each source says, quoted: `[{"ref": "S01:Codes row 41", "quote": "777 = N/A (never smoker)"}, {"ref": "S02:p.6 Q14", "quote": "How many per day? [ _ _ _ ]"}]`.
- `options` — two to four answers, `id` and `label`, plus an `effect` when the consequence is not obvious ("777 stays a special code; 0–99 are counts"). Do not add "something else" or "not sure": the website offers both on every question. An answer that needs the person's own words or numbers — a new upper limit, another site code — is their *Something else*; when you expect one, say so in `context`.
- `recommended` and `why` — always, for every question about the data: the option you would choose and one line of reasoning a person can check. A person accepts a good recommendation in one click, and "not sure" applies it — so recommend only an option you could apply without more words from them.
- `provisional` — the option the schemas encode until the answer arrives. For a question about something already encoded (a real-data finding, a comment on a drafted topic): what is encoded now. Otherwise the loosest reading the sources support, or the safest option when none does — for a rule, no rule.
- `topic`, `targets`, `importance` (`high` for anything that blocks a topic or affects many variables), `to` (`author`, `steward`, or `any`).

Questions about the person themselves (`kind: interview`) carry quick-pick options, and a recommendation only where one is sensible. A code's label comes from the sources; an option's label is your wording of an answer — never let one stand in for the other.

## Contradictions between sources

Put both sides, neutrally, with each source's quote; never hide one. Say what each kind of source is usually good for — the questionnaire shows what was asked; the dictionary usually describes the data as delivered, after cleaning and recoding; the steward knows what happened in between; a web source may describe another release. Then recommend, with the reason grounded in this case, not in a general rule. If the person is not sure, your recommendation is applied and flagged for the steward (INBOX.md) — the conflict stays visible in the review queue until a person settles it.

## Reviewing your guesses in bulk

When a topic carries more than two guesses, add one `bulk` question instead of asking each:

```json
{"kind": "bulk", "topic": "sleep", "covers": ["D021", "D022", "D023"],
 "question": "I made 3 guesses where the dictionary is silent (bounds and one label) — see the list. Do they look right?",
 "options": [{"id": "accept", "label": "Yes, accept them all"},
             {"id": "review", "label": "Show me each one"},
             {"id": "steward", "label": "Leave them for the data steward"}],
 "recommended": "accept", "why": "Each guess only rejects impossible values; the steward can still revisit them."}
```

The option ids `accept`, `review`, and `steward` are fixed: `inbox take` confirms every covered guess on `accept`. On `review`, post the covered guesses as individual questions in the next batch; on `steward`, leave them flagged. "Not sure" counts as `steward`.

## Batches

- Size: `project.json` → `preferences.batchSize` (default 8) — except in a steward review, where their time budget sets it (REVIEW-MODE.md). A batch never mixes tables and rarely mixes topics; follow-up questions may ride with any topic's batch, and the questions from one data-check run share a batch whatever their topics. More questions than the size: post the first batch now and the rest as the next ones.
- Order inside a batch: blocking and high-importance questions first, then conflicts, consent, gaps and ambiguities, confirmations, bulk review last.
- Title: plain and countable — "Smoking — 6 questions".
- One open batch per person: `queue --for <person>` → `openBatches` says whether theirs is still unanswered. If it is, record new questions (`open`) and post them with their next batch. Exceptions that go out at once: the opening interview and the plan batch (they block your work), the questions from a data-check run (the person who sent it is waiting), and a topic's batch while at most one other waits (BUILD.md, step 6). A person with no open batch gets a follow-up at once, in a batch of its own.
- A question that no longer matters: `cancel` it with a note. A batch whose questions all became moot: `withdraw` it.

## Posting

One `record` call posts a batch with its questions inline (they become decisions first):

```bash
uv run <skill-dir>/scripts/schemify.py record <<'EOF'
{"type": "batch", "event": "post", "to": "author", "title": "Smoking — 2 questions",
 "items": [
  {"kind": "conflict", "topic": "smoking", "targets": ["cigs_day"], "importance": "high",
   "question": "Does 777 in cigarettes per day mean 'not asked', or can it be a real count?",
   "evidence": [{"ref": "S01:Codes row 41", "quote": "777 = N/A (never smoker)"}, {"ref": "S02:p.6 Q14", "quote": "How many per day? [ _ _ _ ]"}],
   "options": [{"id": "a", "label": "777 always means not asked (never smoker)", "effect": "777 stays a special code; 0–99 are counts."},
               {"id": "b", "label": "777 can be a real count"}],
   "recommended": "a", "why": "No one smokes 777 a day, and the dictionary labels 777 N/A.", "provisional": "a"},
  "D014"
 ]}
EOF
```

Existing decisions join by id (`"D014"`, as an earlier `record` printed it); inline questions take the batch's `to`, and may carry a `ref` so a later event in the same payload can cite them (`"@q1"`). Then `schemify.py build`, then `check`, and tell the user: how many questions, about how long (a minute each for questions about the data, half a minute for questions about them), and what to reply when done — "done", or in Codex "$schemify done". On a website opened from disk, they reload the page first, and when done press *Review & save*, then *Download as a file*, and tell you where the file is (INBOX.md).

## Without the website

When the person cannot open the website at all — not even `schemify/index.html` from disk — ask in chat with the same content, numbered, recommendation marked, and a one-line answer format:

```
Three questions about smoking — answer like "1a 2b 3: <your words>"; "?" means "not sure — use your recommendation".
1. Does 777 in cigarettes per day mean "not asked"? (dictionary: "777 = N/A (never smoker)"; questionnaire p.6: a 3-digit box)
   a) yes, always — recommended: no one smokes 777 a day   b) it can be a real count
2. …
```

Record the questions and the batch as usual, then record each reply as an `answer` with `"via": "chat"` — the ledger must look the same either way.
