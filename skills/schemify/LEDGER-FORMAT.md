The workspace's memory, field by field: `schemify/state/project.json` (the plan and settings), `schemify/state/ledger.jsonl` (every source, decision, rule, batch, topic event, session, alignment run, and dataset permission), and `schemify/state/variables.csv` (the inventory). Read this before your first `record` of a session, and whenever a `record` call is refused.

Table of contents

- [How state is written](#how-state-is-written)
- [References](#references)
- [Sources](#sources)
- [Decisions](#decisions)
- [Rules](#rules)
- [Batches](#batches)
- [Topics](#topics)
- [Sessions](#sessions)
- [Alignment runs](#alignment-runs)
- [Datasets](#datasets)
- [Milestones](#milestones)
- [project.json](#projectjson)
- [variables.csv](#variablescsv)

## How state is written

- `ledger.jsonl` is append-only, one JSON event per line. Never edit it by hand; write it only through `schemify.py record` (LAYOUT.md), which validates every event, assigns ids, stamps `at`, and refuses anything malformed with a hint. You are its only writer: subagents report to you, and you record.
- An event is `{"type": …, "event": …, …fields}`. Common fields: `id` (omit it on a creating event: `record` assigns the next one), `by` (`agent`, `author`, or `steward`; default `agent`), `via` (`chat`, or `inbox:<submission id>` when it came from the website), `note`, and `ref` — a label for this event, so a later event in the same payload can use its id as `"@label"`: in any id field (`id`, `decision`, `consent`, `replacement`, `covers`, a batch's `items`, a rule's `refs`, an evidence `ref`) and inside `note` text.
- Paths in events are relative to the workspace folder — `package/schemas/…`, `sources/…`, `alignment/A01.json` — never starting with `schemify/`.
- `record` takes one event or a JSON array of events on stdin, and prints the ids it assigned. Write the payload with a quoted heredoc so apostrophes need no escaping:

  ```bash
  uv run <skill-dir>/scripts/schemify.py record <<'EOF'
  {"type": "decision", "event": "decide", "topic": "sleep", "targets": ["sleep_minutes"], "kind": "guess",
   "question": "Plausible upper bound for total sleep?", "choice": "960",
   "why": "The dictionary states no bound; 16 hours rejects the impossible, not the rare."}
  EOF
  ```
- Current state is a replay of the ledger. `schemify.py show <id>` prints any record's current state and its history; `status` and the website read the same replay. A changed fact is a new event, never a rewritten line — the history is the provenance.

## References

One grammar everywhere — evidence, `x-provenance`, rule records, alignment triage:

- `S03` or `S03:<locator>` — a source. The locator says where inside it, in the source's own terms: `Variables row 41`, `Codes row 12`, `p.6 Q14`, `¶12`, `§Smoking history`. No newlines, no `|`.
- `D014` — a decision: anything a person told you, or anything you decided.

A web source is citable only once a person has approved it; a retired source stays citable. A decision is citable at any status but `cancelled` (citing a superseded one draws a warning: cite its replacement); what it says about confidence lives on the decision. A question's `evidence` may also cite a data-check run (`A01`) — the counts in a person's findings — but `x-provenance` never does: a run is evidence for a question, not a source of metadata.

## Sources

A source is a document: a file the user gave you, or a web page you found. People are not sources — what they say becomes decisions.

| event | fields | meaning |
|---|---|---|
| `add` | `kind` (`document` · `web`), `title`, `what` (one line: what it holds — from the user's words or the file name until you have read it; refine it with `update`), `path` (the workspace copy, `sources/<original file name>`, for documents), `original` (the user's path to the file, as they gave it), `url` (web), `origin` (`user` · `agent`) | registered. A web source the agent found starts `suggested`; everything else starts `active` |
| `approve` / `reject` | `by` (a person), `note` | a person's verdict on a suggested web source |
| `extract` | `dir` (the extract folder, `sources/<id>/extract`), `files` (how many files the manifest lists) | `extract.py` ran on it |
| `digest` | `path` (its DIGEST.md), `variables` (count, when it defines variables), `verified` (spot-checked locators, e.g. `["Variables row 41", "p.6"]`) | a digest exists and you spot-checked it |
| `update` | any of `title`, `what`, `notes` | parse notes and corrections |
| `retire` | `note` | no longer used; existing citations stay valid |

Status: `active` (user documents) · `suggested` → `approved` or `rejected` (web) · `retired`.

## Decisions

A decision is every fact the schemas hold that is not transcribed verbatim from a source: an answer, a steward's statement, a conflict ruling, a convention, a guess. Its lifecycle is the question queue.

| event | fields | meaning |
|---|---|---|
| `open` | `kind`, `question`, `topic`, `table`, `targets` (variable names), `context`, `evidence` (`[{"ref", "quote"}]`), `input` (`choice` default · `multi` · `text`), `options` (`[{"id", "label", "effect"}]`), `recommended` (an option id), `why` (one line), `provisional` (the option the schemas encode meanwhile), `importance` (`high` · `normal` default · `low`), `to` (`author` · `steward` · `any` default), `covers` (`bulk`: D ids; `consent`: R ids) | a question exists |
| `answer` | `by` (`author` · `steward`), `choice` (an option id, `other`, or `unsure`), `choices` (for `multi`), `text`, `note`, `via` | a person answered. `unsure` means "use the recommendation for now and flag it for the steward" |
| `decide` | `choice`, `why`, plus any `open` field when it creates the decision; `review` (`needed` default · `none` for mechanical choices no person could dispute) | you decided — a guess, or on a person's behalf after `unsure` |
| `confirm` | `by` (a person), `note`, `via` | a person accepts a decision you made |
| `apply` | `files` (the paths you changed — schemas, toy data, `project.json`, `state/variables.csv`; `[]` when nothing needed changing), `note` | the files now reflect the current answer |
| `supersede` | `replacement` (the new D id) | replaced; the new decision says why |
| `cancel` | `note` | the question no longer matters (say why) |

`kind` is one of: `conflict` (two origins disagree — source and source, a person and a source, or two people) · `gap` (sources are silent) · `ambiguity` (a source is unclear) · `guess` (a bound, a normalized label, a type you chose) · `rule` (skip logic) · `consent` (whether to infer undocumented rules; carries `covers`: `[R ids]`) · `structure` (tables, grain, topics) · `convention` (package-wide encoding choices, and instructions that change how you work) · `interview` (about the person) · `knowledge` (a person volunteered a fact) · `feedback` (a comment or note from the website; `inbox take` creates these) · `alignment` (a real-data finding) · `bulk` (covers several decisions; carries `covers`: `[D ids]`).

What a creating event needs (`record` refuses the rest with a hint):

- every kind: `kind`, `question`.
- an `open` question: at least two `options` unless `input` is `text`, and `recommended` and `why` — for an `interview` question a recommendation is optional.
- about particular variables (`conflict`, `gap`, `ambiguity`, `guess`, `rule`, `consent`, `alignment`, `bulk`): `topic` or `targets` (`table` too when the package has several); a column no document names may be a target. `structure` and `convention` are package-wide: `targets` only when they concern particular variables.
- `provisional` on an `open` of those kinds, `bulk` excepted: the option the schemas encode until the answer arrives (QUESTIONS.md, "Anatomy of a question").
- `evidence` on `conflict`, `ambiguity`, and `alignment` questions — the quotes that disagree or are unclear; give it on any other question a source bears on.
- a `decide` that creates its decision (your guess): `kind`, `question`, `choice`, `why` — no options; give it `topic` or `targets` too, so the website shows it beside its variables.
- `interview`: mark an optional text question "(optional)" at the end of its wording.
- `knowledge` and `feedback`: the person's words in `text`.
- Option ids `other` and `unsure` are reserved for the website's *Something else* and *Not sure*. An `alignment` question's options are `clean`, `change`, and `accept` (DATA-CHECK.md); a `bulk` question's, `accept`, `review`, and `steward` (QUESTIONS.md).

`"applied": true` on an `answer`, `decide`, or `open` records its `apply` in the same event — for a decision whose files you already changed.

Status is computed: `open` → `asked` (in a posted batch) → `answered` (a person chose) — or `provisional` (you decided; needs review) → `confirmed` (a person accepted it). A decision you made with `review: none` is `decided`: mechanical, nothing to review. `superseded` and `cancelled` end it. Two flags ride along: **needs review** — provisional and not confirmed, or answered `unsure`; **unapplied** — answered or decided after its last `apply`. `check` reports every unapplied decision; the steward's review queue is built from the needs-review ones.

Recording a person's volunteered knowledge: `{"type": "decision", "event": "answer", "kind": "knowledge", "by": "steward", "question": "<what it answers, in your words>", "choice": "other", "text": "<what they said>", "targets": [...], "via": "chat"}` — an answer may create its decision when it carries `question`.

## Rules

A rule is one skip pattern or other conditional fact: a gate (the variables whose answers decide) and its consequences for target variables. A skip/applicability pair is one rule. Encoding lives in the mother schema (SKIP-LOGIC.md); the ledger holds the lifecycle.

| event | fields |
|---|---|
| `add` | `table`, `gates` (variable names), `targets`, `reading` (one plain sentence in the source's codes, e.g. "smk_ever = 2 → cigs_per_day, smk_age = 777"), `evidence` (`documented` · `implied` · `told` · `inferred`), `refs` (references to the evidence), `status`, `waits_for` (variables not yet in a schema), `decision` (why: the person's `rule`/`knowledge` decision for `told`; your `guess` decision for `inferred`, recorded when you encode it), `consent` (for `inferred` only: the `consent` decision a person answered yes, or the decision that set `inferRules` to `yes`) |
| `set` | `id`, `status` and any `add` field that changed, plus `note` saying why |

```json
{"type": "rule", "event": "add", "table": "baseline", "gates": ["smk_ever"], "targets": ["cigs_day"],
 "reading": "smk_ever = 2 → cigs_day = -6; smk_ever = 1 → cigs_day ≠ -6", "evidence": "documented",
 "refs": ["S02:¶41"], "status": "waiting", "waits_for": ["cigs_day"]}
{"type": "rule", "event": "set", "id": "R004", "status": "encoded", "note": "pair appended as allOf 6–7; fixtures added"}
```

Status: `suspected` (you believe it exists; nothing documents it; awaiting consent — `waits_for` may ride along) · `waiting` (licensed, but a gate or target is not in a schema yet) · `encoded` (in the mother; its toy-data rows follow in BUILD.md step 4, and `check`'s coverage names any still missing) · `deferred` (a person said "not now", or was not sure) · `declined` (a person said no, or "only documented rules") · `not-expressible` (cross-table, cross-row, arithmetic — documented in the package README instead).

`check` holds the line: every `encoded` rule's id is on a conditional in its mother and every conditional's id has an `encoded` rule; an `inferred` rule may be `encoded` only with a `consent` decision a person answered yes.

## Batches

| event | fields |
|---|---|
| `post` | `to` (`author` · `steward`), `title` (plain words: "Smoking — 6 questions"), `items` (decision ids, or inline `open` objects that `record` turns into decisions first — they take the batch's `to` unless they name their own), `note` |
| `withdraw` | `note` |

Posting marks every item `asked`. The website's Questions tab shows the open batches addressed to whoever it is *Answering as* (and to `any`), in posting order; batches for the other person are listed below them, folded.

## Topics

A topic is one category file — the user-facing name for a group of variables. `planned`, `drafted`, and `tested` are computed from the files and from `validate.py`; these events record the rest:

| event | fields | status it sets |
|---|---|---|
| `present` | `note` (what to look at) | `in review` |
| `approve` | `by` (a person), `via`, `note` | `confirmed` — while the file is what they approved |
| `changes` | `by`, `via`, `text` | `changes requested` — until the next `present` |

Only a person's `approve` confirms a topic. Never record one for them. `record` stamps it with the topic file's `hash` (the website sends the hash of the page the person read): once the file's content differs, the topic is back to `tested` or `drafted`, and `next` says to present it again — except where an `apply` of an answer to a question they had already been asked carries the approval over (`record` stamps that `apply` with `approvedHashes`; INBOX.md).

## Sessions

| event | fields |
|---|---|
| `start` | `mode` (`build` · `review`), `harness` (`claude-code` · `codex` · `cursor` · `other`), `model` — written by `open`, never by you |
| `end` | `summary` (what happened, two lines at most), `handoff` (what the next agent must know that the files do not show — parse quirks, the user's preferences, a half-done step), `next` (one concrete step, or `done`) |

`end` is written by `close`, never by you. `status` prints the last `end`, so the next agent starts from your `handoff` and `next`.

## Alignment runs

A run is one QuaC *findings without data* document: sent by a person through the website, or made by `schemify.py data-check` on a file a person allowed you to check (DATA-CHECK.md).

| event | fields |
|---|---|
| `add` | `file` (`alignment/A01.json`), `label` (the user's name for the dataset — never a path), `records`, `failing` (records failing at error level), `checks` (failed check count), `fingerprint` (QuaC's schema-set fingerprint), `current` (whether it was run against the current schemas), `ruleMap` and `planned` (written for you: rule ids by position, and the checks on columns of topics not built yet), `by` (`agent` for a `data-check` run), `dataset` (its X id), `via` |
| `triage` | `check` (the failing check's `key`, exactly as `show <A id>` prints it), `verdict` (`schema-fix` · `data-issue` · `expected` · `question`), `decision` (the question you asked; for `data-issue` and `expected`, the question a person answered; none for your own slip), `note` |

`inbox take` records the `add` for findings sent from the website, and `data-check` for its own runs; you record each `triage`. A later `triage` of the same check replaces the earlier verdict: a `question` becomes the verdict its answer gives (DATA-CHECK.md).

## Datasets

A dataset checked against the schemas without its data reaching you: a file a person allowed you to check with QuaC yourself (DATA-CHECK.md, "When the person allows it"), or one their own browser keeps checked in QuaC (basis `browser`: DATA-CHECK.md, "Kept checked in QuaC"). Ids `X01`, `X02`, …

| event | fields |
|---|---|
| `allow` | `by` (`author` · `steward` — never `agent`), `path` (the file as they gave it: absolute, or relative to the folder holding `schemify/`; never inside it), `label` (their name for it), `basis` (`public` · `local-model` · `browser` — the website records this one when they connect QuaC, with no `path`), `text` (their words), `via`, `table` (needed when the package has several), `sheet` (a workbook with several sheets), `model` (`local-model` only: filled in from the open session — the permission covers that model alone) |
| `withdraw` | `id`, `by` (a person), `via`, `note` |

`inbox take` records both when they come from the website. A file that moved needs a new `allow`, after a `withdraw` of the old one.

## Milestones

`{"type": "milestone", "event": "reach", "id": "<milestone>", "note": "…"}` — `migrated` (a 1.x migration's *Left to do* is worked through and `check` is green: MIGRATE.md; `record` stamps the topic files' hashes, so the approvals carried over from 1.x cover the files as they stand then), `ready-for-review` (the author handed the package to the steward: FINISH.md), `review-complete` (the steward's review is done: REVIEW-MODE.md), `finished` (the package is final: FINISH.md; `record` stamps it with the schema files' `setId`, and a later change to them makes `next` offer `finish` again). The website's progress line reads them.

## project.json

Edited directly (it is small), then `check` validates it. Fields:

```json
{
  "schemify": 2,
  "id": "lark-7f3a",
  "study": "LARK sleep study",
  "slug": "lark",
  "description": "One paragraph for the package README: what the data is and who collected it.",
  "mode": "build",
  "invoke": "/schemify",
  "harness": "claude-code",
  "idBase": "https://schemas.example.org/lark/",
  "tables": [
    {"name": "sleep_diary", "title": "Sleep diary", "grain": "One element is one participant-night.", "mother": "sleep_diary/sleep_diary.schema.json"}
  ],
  "topics": [
    {"id": "participant", "title": "Participant", "table": "sleep_diary", "file": "sleep_diary/categories/participant.json"},
    {"id": "sleep", "title": "Sleep", "table": "sleep_diary", "file": "sleep_diary/categories/sleep.json"}
  ],
  "conventions": {
    "missing": "in-band codes",
    "sentinels": [{"code": -666, "meaning": "Not applicable (skipped by design)", "structural": true, "decision": "D004"}],
    "titles": "sentence case; units in parentheses",
    "decision": "D005"
  },
  "people": [
    {"role": "author", "name": "", "profile": "informed", "knows": ["questionnaire design", "the 2019 wave"]},
    {"role": "steward", "name": "Dr. R. Osei", "profile": "steward", "knows": ["cleaning code", "every release"],
     "note": "has the 2019 protocol"}
  ],
  "preferences": {"batchSize": 8, "inferRules": "ask", "realData": "yes"},
  "plan": {"sessions": 3, "note": "Topics 1–3 this session; questionnaire-heavy topics 4–6 next."}
}
```

- Paths in `tables` and `topics` are relative to `schemify/package/schemas/`. `topics` order is the reading order: it fixes each mother's `allOf` order and every page's section order.
- `mode` is `build` or `review`; `inferRules` is `ask`, `yes`, or `no` (set only from a person's answer); `realData` is `yes`, `elsewhere`, or `notyet`; `profile` is `steward`, `informed`, or `limited` (INTERVIEW.md).
- `idBase` is a placeholder namespace that nothing fetches; the package README tells publishers to replace it.

## variables.csv

The inventory: every variable any source defines, written at discovery, so no variable is forgotten silently. Columns, fixed: `variable,table,topic,status,source,note`.

- `status`: `include` (belongs in a schema) · `deferred` (waits on a decision — `note` names it) · `dropped` (deliberately excluded — `note` says why) · `added` (not in any source; a person asked for it — `source` is its D id).
- `source`: a reference — where the variable is defined (`S01:Variables row 41`).
- `check` reconciles it with the schemas: an `include` or `added` variable must be a property once its topic is drafted; a `deferred` or `dropped` one must not be. Whether a variable is drafted is never stored — the schemas say it.
