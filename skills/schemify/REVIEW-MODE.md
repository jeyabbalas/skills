Steward review: the data steward settles what the first pass could not — and only that. Read this when the invocation carries `review`, when `project.json` → `mode` is `review`, or when the person says they are the steward reviewing someone's work.

Table of contents

- [What review mode is](#what-review-mode-is)
- [1. Open and orient](#1-open-and-orient)
- [2. The three questions](#2-the-three-questions)
- [3. Build the review queue](#3-build-the-review-queue)
- [4. Post, take, apply](#4-post-take-apply)
- [5. Hand back](#5-hand-back)
- [A steward without an agent](#a-steward-without-an-agent)

## What review mode is

The author's first pass settled what a person with domain knowledge can settle. What remains needs the steward's first-hand knowledge of collection, cleaning, and releases: answers the author was not sure of, your guesses, rules you inferred, unresolved conflicts, and findings from a data check. The steward's time is the scarce resource: show them only those, ranked, a sitting's worth at a time. Everything else stays browsable on the website, never pushed.

## 1. Open and orient

1. `schemify.py open --mode review --harness <…> --model <…>`. In review mode, `next` lists only inbox work and the review itself.
2. If the person turns out to be the author continuing their own work (their words say so — ask once when unsure), run `open --mode build` instead and follow `status`. A workspace in a shared or synced folder is edited by one person at a time: the author pauses while the steward reviews.
3. `schemify.py queue --for steward --limit 40` — read-only; it sizes the review: N = its `items` plus one per topic in `bulkGuesses`.
4. Orient them in a few plain lines: what the data dictionary covers; what the author did (from `status`: topics confirmed, decisions made); what you need from them — "about N items that need your knowledge, about N minutes"; and, last, what to do now: open the website link, check that the header says *Answering as: data steward* (it starts that way in review mode), answer the three questions waiting under *Questions*, and reply *done* (in Codex: `$schemify done`).

## 2. The three questions

Post as the first batch, `"to": "steward"`, all three `kind: interview` — even when batches for the steward were posted earlier for a review without an agent (tell them to answer these three first):

1. "Which of these topics do you know first-hand?" — `input: multi`, one option per topic (`id` the topic id, `label` its title).
2. "How much time do you have now?" — options `15` (about 15 minutes), `30` (about 30 minutes), `60` (an hour or more).
3. "Is anything you already know to be wrong or missing? (optional)" — `input: text`.

Leave out a question their message already answered ("I have about 15 minutes", "I only know the smoking data"): record that answer as theirs — `{"type": "decision", "event": "answer", "kind": "interview", "question": "How much time do you have now?", "choice": "other", "text": "about 15 minutes", "by": "steward", "via": "chat"}` — and act on it now. With the time known, the first batch of review items (step 3) goes out with these questions instead of after them.

When the answers arrive, update the steward's entry in `project.json` → `people` (`profile: steward`, `knows`: the topic titles they chose) and record `apply` with `"files": ["state/project.json"]`. Their time answer sets this sitting's budget, whatever `preferences.batchSize` says: 15 minutes → one batch of up to 10; 30 minutes → a second batch once the first comes back; an hour → a third, a knowledge batch on the topics they know best (INTERVIEW.md). An answer to the third question is acted on first: each fact a `knowledge` decision, applied wherever it reaches — a bound or a code it settles changes now, and the decision it overrules is superseded (INBOX.md, "A new fact about the study") — and each disputed point a question. When the website cannot run, ask all of this in chat with QUESTIONS.md's chat form.

## 3. Build the review queue

Cross off first what the steward's own words already settle (their third answer, a comment): it is applied, not asked again. `schemify.py queue --for steward --limit 40` returns the candidates ranked — escalated "not sure" answers and conflicts first, then inferred rules and real-data questions, then gaps — plus `bulkGuesses` (your low-stakes guesses, grouped by topic), `suspectedRulesUnasked` (rules nobody was asked about), and `deferredRules` (rules a person put off). Compose the sitting's batches from the top:

- Re-post a decision you made on someone's behalf as it is: the website shows it as "Your agent chose X — looks right?", with the options to choose differently.
- An inferred rule: post its `guess` decision; a yes confirms it, a different answer changes or removes the rule.
- One `bulk` question per topic for the grouped guesses (QUESTIONS.md), after the individual items.
- Suspected and deferred rules: one `consent` question per topic (SKIP-LOGIC.md), offering `known` first — a steward often simply knows.
- Within the budget, prefer the topics they said they know first-hand.

Never post what the author answered with confidence; the steward can still disagree with anything through the website's comments, and those arrive as feedback.

## 4. Post, take, apply

Post the batch (`"to": "steward"`), `build`, `check`, and tell them what waits; then close (SKILL.md, Close) — if they answer within this conversation, run `open` again (the project stays in review mode) and follow INBOX.md. In review mode:

- A steward's answer is final unless they say otherwise; when it differs from the author's earlier answer, supersede the old decision rather than editing it — both stay in the history.
- A steward's "not sure" leaves the item open for good: record your decision on their behalf as usual, and add `"note": "steward not sure"` — FINISH.md lists it in the README's open items.
- A steward's statement about how the data was produced is `knowledge`: apply it everywhere it reaches, including topics that were already confirmed (re-present those to the author, BUILD.md "Revising a topic").

When the budget is spent, stop asking — even with items left. Tell the steward how many remain and that they can continue any time with the same command.

## 5. Hand back

1. `build` and `check`.
2. Record `{"type": "milestone", "event": "reach", "id": "review-complete"}` when the queue is empty or the steward says they are done; set `project.json` → `mode` to `build`.
3. Close with a handoff written for the author's next session: what the steward changed (decision ids), what they confirmed, what they left open.
4. Tell the steward how the work goes back to the author: the same shared folder, or `schemify.py share` for a zip they send back. One person edits the workspace at a time.

## A steward without an agent

A steward who has no coding agent can still review: they open `schemify/index.html` from the shared folder, choose *Answering as: data steward*, answer on the Questions tab, and send the author the feedback file the page downloads. The author's agent imports it (`inbox import`, INBOX.md) — the steward's answers carry their role as provenance. Prepare for this case by posting the steward's batches (step 3) before sharing (FINISH.md).
