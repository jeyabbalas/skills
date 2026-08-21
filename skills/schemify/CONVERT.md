The per-category loop: one category carried from source slice to confirmed schema. This file is the loop's spine; the content it moves lives elsewhere — encoding rules in SCHEMA-PATTERNS.md, routing in SKIP-PATTERNS.md, fixtures and runs in VALIDATE.md, pages in PAGES.md, question craft in ELICIT.md.

Table of contents

- [The loop](#the-loop)
- [Reading the slice](#reading-the-slice)
- [Rules the schema cannot hold](#rules-the-schema-cannot-hold)
- [Presenting a category](#presenting-a-category)
- [Revising a category](#revising-a-category)

## The loop

1. **Read the plan row.** Its source slice says exactly where this category's variables live; SOURCES.md's parse notes say how to read that file. Open only the slice.
2. **Draft the category file** — SCHEMA-PATTERNS.md open beside you. Every variable in the slice becomes a property; every property gets its title, its constraint, its provenance. Flip each variable's VARIABLES.csv row to `converted` as it lands (`deferred` with a note if it must wait).
3. **Routing in the slice** — "asked only if", a universe statement, a skip — is mother-file work: read SKIP-PATTERNS.md and write the conditional pair there, not here.
4. **Log judgment calls as they happen**, not at the end — what earns a line is in DECISIONS-FORMAT.md. An unknown gets the loosest encoding the source supports plus an `open` line, and the loop keeps moving.
5. **Wire the mother file**: the category's `$ref` joins `items.allOf` in reading order, before the conditionals.
6. **Validate** — extend the toy fixtures to cover the new category and run per VALIDATE.md. Green moves the plan row to `validated`.
7. **Render** — refresh both pages per PAGES.md. The plan row moves to `rendered`.
8. **Present** (below), batching any opens per ELICIT.md. The row moves to `confirmed` only on the steward's yes.
9. **Close** per SKILL.md's checklist.

Steps 6–8 are the category's finish line, not garnish: a category that validates against fixtures it never got, or renders on a page nobody refreshed, is still `drafted` no matter how complete its JSON looks.

## Reading the slice

Trust the parse notes; a stale slice pointer is fixed in the plan row, not worked around. A variable that appears in the source but sits outside every slice goes to the steward — the category table may need a scoped re-plan (INTAKE.md's proposal step, for the affected rows only, re-confirmed). A variable in VARIABLES.csv that the slice no longer contains is a finding, not a shrug: mark it `dropped` with the reason or chase where it moved.

## Rules the schema cannot hold

The dictionary will state rules JSON Schema cannot express — a sum that must reconcile, a date that must precede another, an ID unique across rows. Capture them anyway: a ledger line with scope `not-enforceable`, and — for arithmetic identities within one category — a trailing `$comment` on the category file, `"Soft checks: …"`, per SCHEMA-PATTERNS.md. The review migrates these into the README's "Documented but not enforced" section. Never quietly drop a rule because the standard can't say it; a consumer who knows the rule exists can enforce it elsewhere.

## Presenting a category

Give the steward two things: a chat gist in their language — N variables converted, the notable judgment calls by D-number, anything odd found in the source — and the rendered page: `dictionary.html`, opened at this category's section (serving in PAGES.md). Ask for the confirmation explicitly: "If the names, labels, and value meanings in this section match how you'd document the study, I'll mark it confirmed."

The page is how a steward who has never read JSON gives real feedback — offer it every time. If they confirm from the gist without opening it, accept that; the offer, once, is the obligation. "Looks fine" in response to nothing at all is not confirmation — there must be something in front of them, gist or page.

## Revising a category

A steward request or a review overturn reopens a category: its plan row goes back to `drafted`, and the loop re-runs from step 2 scoped to the change. Supersede the overturned ledger lines per DECISIONS-FORMAT.md — never rewrite them. Fixtures and pages must catch up before the row earns `validated` and `rendered` again; re-present only what changed.
