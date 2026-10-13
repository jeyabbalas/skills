Interviewing people: the opening interview, the plan questions, how the user's profile changes your strategy, and steward knowledge sessions — how institutional memory gets into the schemas. Read this at a fresh start, whenever `next` says `interview`, before planning, and before any knowledge session. How to word and post questions in general is QUESTIONS.md's.

Table of contents

- [The opening interview](#the-opening-interview)
- [Profiles and strategy](#profiles-and-strategy)
- [The plan questions](#the-plan-questions)
- [Knowledge sessions with a steward](#knowledge-sessions-with-a-steward)
- [Recording what people say](#recording-what-people-say)

## The opening interview

Post it as the first batch, right after registering the sources (START.md, step 3). Adapt it to what you already know, and put these first when they apply:

- a file you could not place as documentation or data: `{"kind": "interview", "importance": "high", "question": "Is exports/baseline_2024.csv your real data, or a document about it?", "context": "I have not opened it: I never open real data.", "options": [{"id": "data", "label": "Real data — one row per person or visit"}, {"id": "documentation", "label": "Documentation — one row per variable or code"}], "recommended": "data", "why": "Its folder and dated name look like a data export."}` — on "documentation", extract it with `--documentation`;
- a working study name: `{"kind": "interview", "input": "text", "question": "What is the study called? (Add its acronym if it has one.)", "context": "Until you answer I call it \"Ashgrove\", from your file names."}`;
- files you saw but were not given: `{"kind": "interview", "input": "multi", "question": "I also see these files beside the ones you gave me. Should I read any of them?", "options": [{"id": "readme", "label": "docs/README.txt"}, {"id": "none", "label": "None of them"}]}`.

Questions about the person carry quick-pick options, and a recommendation only where one is sensible (`kind: interview`). The rest of the batch:

```bash
uv run <skill-dir>/scripts/schemify.py record <<'EOF'
{"type": "batch", "event": "post", "to": "author", "title": "Getting started — 6 questions",
 "note": "About 3 minutes. I am reading your documents meanwhile.",
 "items": [
  {"kind": "interview", "question": "Which describes you best?",
   "options": [{"id": "steward", "label": "I manage this study's data — I know how it was collected, cleaned, and released"},
               {"id": "informed", "label": "I work with this data and know it well, but not every processing detail"},
               {"id": "limited", "label": "I am fairly new to this study"}]},
  {"kind": "interview", "input": "multi", "question": "Which of these do you know first-hand?",
   "options": [{"id": "collection", "label": "How the questionnaires or forms were administered"},
               {"id": "cleaning", "label": "How the data was cleaned and recoded"},
               {"id": "derived", "label": "How derived variables were computed"},
               {"id": "releases", "label": "Differences between data releases or waves"},
               {"id": "none", "label": "None of these yet"}]},
  {"kind": "interview", "input": "multi", "question": "What other documentation exists that I have not seen?",
   "context": "Skip logic and recodes often live outside the data dictionary. If you have any of these, give me the files afterwards.",
   "options": [{"id": "forms", "label": "Questionnaires or case report forms"},
               {"id": "protocol", "label": "A protocol or data-collection manual"},
               {"id": "code", "label": "Cleaning or processing code (SAS, Stata, R, SPSS…)"},
               {"id": "older", "label": "Earlier versions of the data dictionary"},
               {"id": "papers", "label": "Published papers describing the study"},
               {"id": "none", "label": "Nothing else"}]},
  {"kind": "interview", "input": "text", "question": "Who else knows this data well — a data steward or data manager who could review this work later? Name or role (optional)"},
  {"kind": "interview", "question": "Do you have the real dataset this data description is for?",
   "context": "I will never open it. Later, the website lets you check it on your own computer and send me only a summary of what did not fit — no values.",
   "options": [{"id": "yes", "label": "Yes, I can run checks on my computer"},
               {"id": "elsewhere", "label": "Someone else holds it"},
               {"id": "notyet", "label": "Not yet"}]},
  {"kind": "interview", "question": "How many questions do you want at a time?",
   "options": [{"id": "5", "label": "About 5 — short sittings"}, {"id": "8", "label": "About 8"}, {"id": "15", "label": "As many as you have"}],
   "recommended": "8", "why": "Enough to make progress without a long sitting."}
 ]}
EOF
```

Interview questions take about half a minute each: say "about N minutes" with N half the count, rounded up (6 questions → about 3 minutes). Then `build`, and tell the user the questions are waiting (START.md, step 3).

## Profiles and strategy

Set each person's `profile` in `project.json` → `people` from their answer to *Which describes you best?*, and adapt:

| profile | who | strategy |
|---|---|---|
| `steward` | knows collection, cleaning, and releases first-hand | Ask more and deeper: run a knowledge session per topic (below). Their answers are authoritative; record them as `knowledge` or answered decisions. Escalate nothing — they are the escalation. |
| `informed` | knows the study, not every processing detail | The normal flow. Ask about meaning, labels, and what looks wrong; expect some "not sure" answers — those are applied as your recommendation and flagged for the steward. |
| `limited` | new to the study | Ask only what a newcomer can answer: names, labels, which variables matter, obvious mismatches. Everything needing specialist knowledge becomes your provisional decision (`decide`, review needed) with `to: steward`, never posted to them. Tell them early that a steward review will settle the rest. |

The other answers:

- *Who else knows this data well?* — a steward they name is recorded as a person (`role: steward`, `name` as they typed it, no profile yet), so FINISH.md can offer the review.
- *What other documentation exists?* — ask the user once for the files they named: paths in chat, or copies into a folder you name; register them (START.md, "Later sources"). Documents they do not have: put who has them in their `note` in `people`, and move on.
- *Do you have the real dataset?* — `preferences.realData` (`yes` · `elsewhere` · `notyet`); DATA-CHECK.md says when to offer the check. A note or later message saying the data is public, or that their agent runs on a model they control → DATA-CHECK.md, "When the person allows it".
- *How many questions at a time?* — `preferences.batchSize`.
- The study's name — `study`, and `description` once you can write it. `slug` and `idBase` follow it at the plan (START.md, step 7), before the first schema file.

## The plan questions

After the digests, one batch (QUESTIONS.md rules; recommendations from the digests) — posted even while the interview is unanswered, since it blocks your work:

- **Grain**, per table — "What is one row?" Recommended: what the identifiers imply ("one row per participant: `participant_id` is unique and nothing repeats per visit").
- **Tables** — one dataset or several related ones (a participant table, a visit table)? Each distinct grain is its own table.
- **Missing-value codes** — "Your dictionary uses -666 (not applicable), -777 (refused), -888 (don't know). Is -666 always 'skipped by design'?" and, separately, "In the delivered data, can a cell be empty? What does an empty cell mean?" Recommended: the source's codes, no empty cells. An answer that empty cells occur and mean something needs a `convention` decision (SCHEMA-STYLE.md, "Delivered blanks").
- **Topics** — the proposed list as a table in `context` (topic · variables · examples · why), options "Use these topics" (recommended) / "Change them" (the person says how in "Something else").
- **Session plan** — "About N sessions of two to four topics; this session: topics A and B." Options: the plan (recommended), "Do as much as possible now", "Smaller steps".
- Web sources waiting for approval are not questions: the person approves each on the Sources & decisions tab (*Use* / *Do not use*). Say so in the batch's `note` and link it: "Also: two web pages I found need your OK — `<website>#evidence/sources`."

## Knowledge sessions with a steward

Institutional memory is the rarest source and the easiest to lose. With a steward (`profile: steward`), open each topic with a short knowledge batch before drafting — the questions only they can answer, each still with your reading of the documents as the recommendation:

- **Processing history**: "The questionnaire offers 1–5; the dictionary lists 1–4. Was a category merged after collection? *Recommended:* yes — the dictionary describes the delivered data."
- **Codes**: what each special code means in practice; whether a code changed meaning between waves or releases.
- **Skip logic**: who was asked what, and what landed in the cell for everyone else.
- **Derived variables**: how each was computed, from which inputs (goes into `x-derivation`).
- **Known quirks**: impossible values that are real, values that were capped, sites that differ.

Also invite free notes: "Anything I should know about this topic? Use *Note to your agent* on the website any time." A steward's note can be long and wide-ranging: split it into one `knowledge` decision per fact, each with its targets, and say so when you report back.

Pace it: one knowledge batch per topic, folded into the topic's question batch when the topic is small. Never ask a steward what the documents already answer — quote the document and ask whether it still holds.

## Recording what people say

- An interview answer is a decision (`kind: interview`) the website answer created; apply it to `project.json` as listed under "Profiles and strategy" and record `apply` with `"files": ["state/project.json"]` — or `[]` when nothing in a file changed.
- A fact a person states — in an answer, a comment, a note, or chat — is a decision a person answered (`kind: knowledge`), with `targets` naming the variables. Apply it to the schemas with that decision in `x-provenance`; a statement that changes a code, a bound, or a rule cites the decision on that facet.
- Something said in chat: record it the same way with `"via": "chat"` — chat is a valid channel; the ledger is where it must end up.
- The user's preference for batch size is `project.json` → `preferences.batchSize`; honour it in every later batch.
