Processing what people send back: answers, "not sure", comments and notes, topic verdicts, source approvals, data-check findings, and permissions to check a file yourself. Read this when `next` says `process-inbox`, `decide-on-behalf`, or `apply-decisions`, and whenever the user says they have sent something.

Table of contents

- [Take every submission](#take-every-submission)
- [Applying an answer](#applying-an-answer)
- [Not sure](#not-sure)
- [Comments and notes](#comments-and-notes)
- [Topic verdicts, sources, findings](#topic-verdicts-sources-findings)
- [Feedback that did not come through the server](#feedback-that-did-not-come-through-the-server)
- [Tell the user](#tell-the-user)

## Take every submission

1. `schemify.py inbox list`.
2. For each, oldest first: `schemify.py inbox take <id>`. It records every answer, confirmation, comment, topic verdict, source verdict, and findings file in the ledger — with the person and `via: inbox:<id>` as provenance — moves the submission to `inbox/done/`, and prints `from` and `todo`: your work list, each item with its decision, question, answer, topic, table, targets, and the `files` it may change — your `apply` lists only the ones you did change. `show <id>` prints a decision's options, their effects, and its evidence when you need them.
3. In review mode, a submission `from` the author is unexpected: ask the person once whether the steward answered, and let them fix *Answering as* on the website if not.
4. Work through `todo` in order (below). `status` keeps listing anything still unapplied, so nothing is lost if the session ends midway.

## Applying an answer

For each answered decision:

1. Change the files to match the answer: the schema (a code, a label, a bound, a rule), `project.json` (a convention, a preference, a person), `state/variables.csv` (deferred, dropped, added) — and the toy data whenever a code, a bound, or a rule changed: the edge rows move to the new values and the planted mistake stays just outside them (DATA-CHECK.md).
2. Re-cite the facet: the property's or rule's `x-provenance` now names this decision where the answer settled it — a person's answer replaces your provisional guess as the origin. When it agrees with a source, cite the decision (the person settled it; the source stays in its evidence); the value the answer rejected may live on as a `$comment` caveat ("the questionnaire's box allowed 1–60").
3. When the answer overturns a different, earlier decision that a facet cited (your guess D009), that one is replaced: record `{"type": "decision", "event": "supersede", "id": "D009", "replacement": "D014"}`. A question's own provisional answer is not a separate decision — re-citing is enough.
4. Record `{"type": "decision", "event": "apply", "id": "D014", "files": ["package/schemas/…", "package/toy-data/…"], "note": "one line on what changed"}` — in the same payload as any `supersede`.
5. An answer that matched what was already encoded still gets its `apply` (`"files"` naming any file whose provenance now cites it, else `[]`: "already encoded").
6. A topic a person approved stays approved through the answers to questions they had been asked, or had answered, before approving it: list its file in the `apply`'s `files`, and record a person's chat answers before their approval. Any other change to an approved topic — the answer to a question posted after the approval, a comment, a slip you fix — sends it back: `next` says `present-topic` (BUILD.md, "Revising a topic").

By kind:

- `consent` → SKIP-LOGIC.md, "Asking before inferring", step 3, for every rule it `covers`: `yes` and `always` encode them as inferred rules flagged for review (`always` also sets `preferences.inferRules: yes`); `known` encodes them as rules the person vouches for (evidence `told`, no flag); `later` → each `deferred`; `no` → each `declined`.
- `structure` or `convention` → `project.json` first; a change that moves variables or codes across files is a re-plan of the affected topics (BUILD.md, "Revising a topic").
- `interview` → `project.json` → `people`, `preferences`.
- An answer naming documents the person will provide → ask them for the files and register them (START.md, "Later sources").
- `alignment` → DATA-CHECK.md, "Triage": `clean` changes no file — record the check's new verdict `data-issue`; `change` → make the change their answer gives (a bound, a code, a rule taken out), cite their decision on it, verdict `schema-fix`; `accept` → verdict `expected`. Each verdict cites the answered decision. On an inferred rule, `clean` or `accept` says the rule is right: also record `confirm` on the rule's `decision`.
- `bulk` → `accept` was handled by `take`; record `apply`. `review` → post the covered guesses individually in the next batch, then `apply` the bulk decision. `steward` → `apply` with the note "left for the steward".

## Not sure

A person who answers "not sure" is asking you to decide for now and have the steward settle it. For each (`next` says `decide-on-behalf`):

1. Record `{"type": "decision", "event": "decide", "id": "D014", "choice": "<the recommended option id>", "why": "<the recommendation's reason>; the person was not sure"}` — it stays flagged for the steward's review.
2. Change the files and record `apply` as above, in the same payload as the `decide`.

Three exceptions: a `consent` question answered "not sure" is decided `later` — an unsure person has not licensed a rule; a `bulk` question, `steward`; an `alignment` question, its `provisional` — nothing changes, and the check stays a `question` for the steward. Use another option than the one you recommended only if the person's note changes your view; say so in `why`.

## Comments and notes

`take` turns each comment and note into a decision of kind `feedback`, answered by the person, holding their words (`targets` name the variable when they commented on one).

A comment that changes something — a label, a code, a bound, a rule — is sorted by what the thing cites now (`show variable:<name>` prints each facet's citation). So is a note on an answer that says more than its option; against the same person's earlier answer, their newer words win when they are plain (`supersede` the old decision), and are asked about when they could be read either way:

- **Your own guess, or nothing** → the person outranks your guess: make the change, cite the feedback decision on the facet it settles, record `apply` (and `supersede` the guess it replaced). A hedged statement ("I think the lowest age is 3") is still their statement; only when their words leave the value itself open ("3 or 4?") do you ask a follow-up instead.
- **A source, or another person's answer, and the comment comes from a steward** (`profile: steward`) → they are the escalation, and their word settles it: apply it as a new fact (below), and keep the source's wording in the facet's `$comment`, so the disagreement stays visible.
- **A source, or another person's answer, from anyone else** → two origins disagree, and that is always a question: record a follow-up `conflict` question (QUESTIONS.md) quoting both — their comment as `{"ref": "D031", "quote": "…"}` — with your recommendation; the current value stays until it is answered. In the same payload, `apply` the feedback decision with `"files": []` and the note "asked as @q" (the follow-up carries `"ref": "q"`). It goes out with the person's next batch, or at once if none of theirs is open (QUESTIONS.md, "Batches").
- **A new fact about the study** → the same as your own guess: their words are the provenance. A long note with several facts: split it into `knowledge` decisions answered by the same person (one per fact, each with targets and `"via": "inbox:<id>"`), apply each, then `apply` the feedback decision with a note listing them.
- **"Looks right"** on a variable or a rule → `apply` with no change. On an inferred rule, it confirms that rule's guess: record `confirm` on the rule's `decision` with the person and via.

## Topic verdicts, sources, findings

- Topic approved → nothing to do; it is confirmed. Changes requested → BUILD.md, "Revising a topic".
- Web source approved → it is now citable: read what it settles, compare it with the drafted topics, and turn every disagreement into a `conflict` question. Rejected → never cite it.
- Findings file (`alignment add`) → DATA-CHECK.md, "Triage".
- A file they allow you to check (`dataset allow`) → nothing to apply; `next` lists `run-data-check` at the next resting point (DATA-CHECK.md, "When the person allows it"). Withdrawn → never check it again.

## Feedback that did not come through the server

The website saves answers as a file when it is opened from disk or the server is down. When the user says they saved feedback — usually in their Downloads folder as `schemify-feedback-<study>-<time>.json`:

1. Find the file the user names (ask for the path if needed). If you cannot read it where it is (a sandbox), ask them to move it into `schemify/inbox/`.
2. `schemify.py inbox import <path>` — it checks the file belongs to this workspace, and answers it has seen before come back as `duplicate` (nothing to do) — then `inbox take` as usual.

A user who pasted the JSON into chat (the website's *Copy*): save it as `schemify/inbox/pasted-<time>.json`, then import that file.

## Tell the user

After processing — `build`, then `check` — send one message for the whole pass: what changed ("Applied your 6 answers: melatonin stays out until the coding sheet is found; awakenings keep the 0–20 range; the no-diary-entry rule is in, marked for the steward."), and what waits for them next — or that nothing does, and what you are doing meanwhile.
