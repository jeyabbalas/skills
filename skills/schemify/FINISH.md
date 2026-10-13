Wrapping up: checking that the package is complete, then either handing it to the data steward for review or finishing. Read this when `next` says `finish`, or the person asks to wrap up or to have their steward review the work.

Table of contents

- [Complete means checked](#complete-means-checked)
- [Read the package as a stranger would](#read-the-package-as-a-stranger-would)
- [Ending A: hand it to the steward](#ending-a-hand-it-to-the-steward)
- [Ending B: finished](#ending-b-finished)
- [After the end](#after-the-end)

## Complete means checked

Run the commands; do not recall that they passed:

```
- [ ] `status`: every topic confirmed; `next` offers `finish`, and nothing else but questions for a steward who is not the person you work with
- [ ] The skip-logic audit is done (SKIP-LOGIC.md) — no suspected rule left unasked, no waiting rule whose variables exist
- [ ] `check` green: no errors, nothing unapplied, the inbox empty
- [ ] Every open question answered, or deliberately left for the steward (`to: steward`, or flagged for review); an optional question may stay blank
- [ ] `project.json` → `description` is a paragraph a stranger understands: what the data is, who collected it, when — as far as the sources and the people you asked say; never guess the rest
- [ ] A data check offered, if the person has the data (DATA-CHECK.md) — optional, never required; a file they allowed you to check has run on the final schemas
- [ ] `build` ran last
```

A person who wants to stop before everything is confirmed may: say what is unfinished in one line, record it in the handoff, and take the ending they choose.

## Read the package as a stranger would

Open `schemify/package/README.md` and read it top to bottom once — it is generated from the ledger, `project.json`, and the schemas, and it is what every future user of the schemas sees first. Fix what reads badly at its source (the description, a title, a rule's `$comment`, a decision's wording), never in the README itself, then `build` again.

## Ending A: hand it to the steward

When the person asks for a review, or a steward is named in `project.json` → `people` and `schemify.py queue --for steward` holds anything for them. A named steward with an empty queue has nothing to review: take Ending B, and say the steward can still review later (`/schemify review`). The person may also choose to finish now: what waits for the steward stays listed in the README's open items.

1. `schemify.py queue --for steward` — say how much will reach the steward: "About 14 items need their knowledge — roughly 20 minutes."
2. Record `{"type": "milestone", "event": "reach", "id": "ready-for-review"}` and set `project.json` → `mode` to `review`.
3. Optional, for a steward without a coding agent: post their first batch now (REVIEW-MODE.md, step 3), so the page already holds their questions.
4. `schemify.py build`, then `schemify.py share` — it writes a zip next to the workspace and prints `tell_user`: what to send, and what the steward does with it.
5. Close the session; the handoff says the work is with the steward. One person edits the workspace at a time: the author waits for it to come back (the same folder, or the zip the steward returns).

When it returns, the author's next session finds `review-complete` and continues normally — usually with a few topics to re-confirm.

## Ending B: finished

1. Record `{"type": "milestone", "event": "reach", "id": "finished"}`.
2. Close with `next: done`.
3. Tell the person, in plain words:
   - The deliverable is `schemify/package/` — schemas, toy data, README, PROVENANCE, the data dictionary page, and a validator. Copy it wherever it is needed; it works without you or this skill.
   - Before publishing the schemas anywhere public, replace the placeholder `$id` namespace (`project.json` → `idBase`); the README says where.
   - `schemify/` is the working record: keep it, so the work can be revised later with a single command.
   - Anything flagged for the steward is listed in the README's open items.

## After the end

Nothing is ever final. A later invocation with a change ("the 2024 release added three variables") reopens the work: register any new source (START.md, "Later sources"), revise the affected topics (BUILD.md), and finish again — `next` offers `finish` once the schema files differ from the ones you finished with. The milestones stay in the ledger as history.
