How to get knowledge out of the steward and the world and into the package. Read this before asking the steward any batch of questions and before hunting external sources — intake, convert, and review all funnel through here. Recording mechanics live in DECISIONS-FORMAT.md and SOURCES-FORMAT.md.

Table of contents

- [Speak the study, not the schema](#speak-the-study-not-the-schema)
- [Batch, don't ping-pong](#batch-dont-ping-pong)
- [The ledger is the queue](#the-ledger-is-the-queue)
- [Hunting external sources](#hunting-external-sources)
- [When sources disagree](#when-sources-disagree)
- [What gets recorded where](#what-gets-recorded-where)

## Speak the study, not the schema

Every question must be answerable by someone who knows the study and has never seen a JSON Schema. Translate before asking:

- Not "should the numeric branch exclude 777 with a `not` clause?" but "could 777 ever be a real number of cigarettes per day in this data, or is it always the code for 'not asked'?"
- Use their variable names and their dictionary's own words; quote the dictionary line you are unsure about.
- Offer a reading, don't request an essay: "I read X as meaning Y — right?" A steward corrects faster than they compose.
- One concrete record beats an abstract rule: "a woman with parity 0 — what does `age_first_birth` contain for her?"

Match their register as it reveals itself: an epidemiologist hears "skip pattern" and "universe"; a lab manager hears "this field is only filled in when…". When they correct your vocabulary, keep the correction for the rest of the package.

## Batch, don't ping-pong

Questions accumulate; sessions ask them in batches. Mid-conversion, an unknown never stops the line: give it a safe provisional encoding — the loosest reading the source supports — log an `open` decision, and keep going. Ask at natural pauses — a category finished, a session closing, five opens pending — as one numbered message grouped by topic, each question answerable in a line, each ending with its D-number so answers file mechanically.

One exception asks alone and immediately: a blocker that gates the whole unit — the grain is ambiguous, two sheets disagree on the primary key. Everything else waits for the batch. Never make the steward hunt through prose for the question marks.

## The ledger is the queue

`grep "· open ·" DECISIONS.md` *is* the question list — there is no second one. Presenting a batch:

> Three things only you can settle, quickest first:
> 1. `cigs_day` — could 777 ever be a real daily count, or is it always "not asked"? (D014)
> 2. The label sheet lists `site` codes 1–5 but the data note mentions six sites — which is right? (D017)
> 3. …

On each answer: flip the line's confidence to `user-confirmed ({date})` in place, then apply it to the schemas in the same session — or, if the change is bigger than the session has room for, make it the `next:` unit. An answer applied nowhere is a question wasted.

## Hunting external sources

Before asking the steward what the public record already answers, search for it: the study's name plus "data dictionary", "codebook", "questionnaire"; the study's own website; national data archives; the funder's or publisher's repository. Well-known studies usually have official documentation online — find it rather than making the steward retype it.

Present findings as a suggested list — name · URL · what it would resolve — and let the steward approve before anything from it becomes provenance. In SOURCES.md a source moves `suggested → steward-approved → consulted {date}`; only a consulted source may be cited in a schema's `$comment` or a decision's why. Date the consultation — the web moves.

If your session cannot search the web, say so once and ask the steward for links instead; their browser works even when yours doesn't.

## When sources disagree

The dictionary says one thing, the questionnaire another, the steward remembers a third. Never silently prefer one: put both citations in one `open` decision and let the steward arbitrate. When presenting, say what each source is good for — the dictionary usually reflects the data as delivered; the questionnaire reflects what was asked; the steward knows what happened in between. The winning reading goes in the schema; the losing one survives in `$comment` provenance.

## What gets recorded where

- An answer about the data → DECISIONS.md (confidence flipped, or a new line).
- Who knows what, a new file, an approved link → SOURCES.md.
- A repeated correction of your register → just speak differently; no file needed.
- Anything that changed a schema → the schema itself, same session, plus its ledger line.
