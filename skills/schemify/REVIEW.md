The end of the work: every judgment call put in front of the steward, the package README finished, the scaffolding offered for cleanup — and the playbook for touching a package after all that is done. Read this when every category is confirmed, when the steward asks for a review, or when working on a finished package.

Table of contents

- [When review runs](#when-review-runs)
- [Completion criteria](#completion-criteria)
- [Walking the ledger](#walking-the-ledger)
- [Revisions](#revisions)
- [Finishing the README](#finishing-the-readme)
- [Cleanup](#cleanup)
- [Working on a finished package](#working-on-a-finished-package)
- [Handoff](#handoff)

## When review runs

Normally: every category `confirmed` and only the review milestone open. On request: any time — name what is unfinished first, and walk only what exists. A steward who skipped per-category confirmations may confirm in bulk here: accepting a category's decisions at the walk *is* its confirmation; both paths are legal, and neither is skippable — a package no steward ever said yes to is a draft, however green its checks.

## Completion criteria

Complete is a checklist, not a feeling:

- **Intake complete**: sources registered · grain and categories user-confirmed · Conventions filled, each row citing its D-number · scaffold validates · How to continue written · the log says the method was introduced.
- **Category complete** (`confirmed`): every variable in its slice is a property (coverage green) · fixtures cover its levels, bounds, sentinels, and both halves of its skips · validation green · both pages carry it · the steward said yes to the rendered result.
- **Package complete**: every category confirmed · every conditional has its PASS/FAIL fixture pair · coverage reconciles with deliberate additions listed · `summary` fully green · pages current · README finished (sections below) · the ledger walked — zero `open` lines, or each survivor migrated with the steward's acknowledgment · the real-data offer made and its outcome logged.

Check them by running the checks, not by recalling that they passed.

## Walking the ledger

The review is a conversation about judgment, not a reading of the ledger. Present in three groups, in this order:

1. **Open** — the unresolved questions, walked one by one. An item stays open past the review only by the steward's explicit choice, and then it migrates to the README's open-items list; nothing stays open silently.
2. **Agent-decided** — every call you made that the steward hasn't ratified. Group by theme — sentinel handling, plausibility bounds, naming, category assignments, skip patterns — and present each theme as a short numbered list: scope · the call · the one-line why. Close each theme with: "Say a number to change it, or 'fine' to accept the group." Acceptance flips the group to `user-confirmed (review {date})`; a challenge becomes a revision unit and its category reopens.
3. **User-confirmed** — a one-line-each recap with no question attached. The steward already decided these; reopen one only if they do.

At most ten items per message; a large ledger walks over more than one sitting, and the review milestone stays open until it finishes.

## Revisions

Each overturned call: supersede its ledger line, set the category back to `drafted`, and re-run the convert loop scoped to the change (CONVERT.md's Revising section). Re-present only what changed. Revisions are the review working, not the review failing — a steward who changes five decisions read all fifty.

## Finishing the README

The package README is the deliverable's front door — written for a consumer who has neither this skill nor the steward on hand. Its sections, in order:

1. **What this package describes** — the study in a paragraph, the grain per table ("one row is one …"), and a table of tables: name · mother file · row grain · categories.
2. **Layout and composition** — the tree in brief; that a row is the `allOf` union of its categories; why unknown columns are rejected by the mother's single `unevaluatedProperties: false`.
3. **Value-encoding conventions** — codes get `oneOf`, measures get `anyOf`; bounds reject the impossible, not the merely rare; the chosen unit and title conventions.
4. **Sentinel semantics** — the code table: code · meaning · where it applies; the wide year variants; any per-field meanings worth a caller's attention.
5. **Enforced routing rules** — each conditional's `$comment` line, enumerated. This list is generated knowledge: it must match the mother file, so derive it from the mother file.
6. **Documented but not enforced** — every `not-enforceable` ledger line, stated as rules a consumer should check downstream.
7. **Known source issues handled** — dictionary defects, corrected typos, coding inversions, each with what the schema does about it.
8. **Sources and provenance** — the dictionary files and consulted external sources with URLs and dates, distilled from SOURCES.md.
9. **Validating and browsing** — exactly these commands, current for this package:

   ```
   pip install -r tools/requirements.txt      # or use: uv run tools/validate.py …
   python3 tools/validate.py summary .        # schemas, fixtures, coverage — everything
   python3 tools/validate.py data . --file your_export.csv
   ```

   plus one line each: double-click `dictionary.html`; `python3 -m http.server 8000` then open `playground.html`. Note that the `$id` namespace is a placeholder to replace before publishing the schemas anywhere public.
10. **Open items to confirm with the data provider** — the surviving opens, one line each.

## Cleanup

Offer once, after the milestones are all checked, in the steward's terms — both options are honest and the choice is theirs:

> The schemas, the toy data, the validator, and the web pages are the deliverable — they stand on their own now. My three working files (progress, decisions, sources) were scaffolding. I can fold what still matters into the package README — the sources we used, anything left open — and delete them; or leave them in place if you want the full working record in version control. Which do you prefer?

On "clean": finish the README first — provenance, open items, the not-enforced list; nothing migrates *after* deletion — run `summary` one last time, delete `PROGRESS.md`, `DECISIONS.md`, and `SOURCES.md` (VARIABLES.csv stays — the coverage check needs it), and say in one line what the package now contains. On "keep": append the final log line `next: — (complete)` and stop — never raise cleanup again; a later session finding a complete PROGRESS.md treats the package as finished and works in revision mode. Either way the deliverable is identical: cleanup changes the scaffolding, never the package.

## Working on a finished package

A finished package has no state files, by design — the README is the front door. For a question or a targeted change: read the README and only the schema files the change touches; encode per SCHEMA-PATTERNS.md; land new judgment calls directly in the README (open items, or a dated line under a `Changes` heading); update VARIABLES.csv if variables moved; re-run `summary`; re-render what changed. Do not resurrect the state trio for a one-line change. A steward asking for a second table, a re-planned category structure, or a rework across many categories is different — that is a re-plan: recreate the state files via INTAKE.md's relevant steps, say why, and work the loop again.

## Handoff

Close the engagement by telling the steward what travels: the package validates anywhere Python runs (`tools/validate.py`, commands in the README), the dictionary page opens anywhere forever, the playground needs one command, and none of it requires this skill — colleagues, repositories, and CI can hold the package to the same contract the two of you just finished writing.
