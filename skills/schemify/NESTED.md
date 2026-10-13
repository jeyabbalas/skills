Variables that hold more than one value: how to spot one in the sources, how to ask how the delivered data holds it, and how its fields are named. Read this when a digest reports a shape other than one value, before planning (START.md, step 7) whenever the sources describe one, and when you draft a variable whose shape is not plain — or that you are unsure of. The JSON for each shape is SCHEMA-STYLE.md's ("Nested values"); rules among a value's fields are SKIP-LOGIC.md's ("Rules inside nested values"); toy data for them is DATA-CHECK.md's.

Table of contents

- [Shapes](#shapes)
- [Spotting a nested variable](#spotting-a-nested-variable)
- [Nested, wide, or long: ask](#nested-wide-or-long-ask)
- [What a missing value looks like inside](#what-a-missing-value-looks-like-inside)
- [Names](#names)
- [In plain words](#in-plain-words)

## Shapes

A record is one row, but a cell need not hold one value. Every variable has one of these shapes:

| shape | what the cell holds | example |
|---|---|---|
| one value | a number, a code, a date, text | `age` = 73 |
| group | named fields, the same for every record | `address` = {street, city, postcode, country} |
| list of values | several values of one kind — codes, numbers, text | `diagnoses` = ["E11.9", "I10"]; a "select all that apply" question |
| list of entries | several entries, each a group of the same fields | `household` = one {name, relation, age} per person |
| lookup | a value under each of a varying set of names | `labs` = {"hba1c": 6.8, "ldl": 131} |
| mixed | different shapes in different records | `notes` = text in some records, a group in others |

The shape is a fact about the delivered data, never a modelling choice: the same household roster can arrive as a list inside each record, as numbered columns (`hh1_age`, `hh2_age`, …), or as a table of its own with one row per person. Only the people who deliver the data know which — the sources often say, and when they do not, you ask.

## Spotting a nested variable

Check every variable's shape — at the digest (SUBAGENTS.md, the digest brief), in the inventory, and again before you draft it (BUILD.md, step 2). These signals say it may hold more than one value:

| signal | example | points to |
|---|---|---|
| a dotted or bracketed name | `address.city`, `visits[].date`, `meds[0].dose`, `labs/ldl` | a group or a list of entries; the part before the dot names the variable |
| a type or format column that says so | object, struct, record, group, array, list, set, repeating, roster, map, dictionary, JSON | the shape it names |
| a variable whose rows or bullets list parts | "address — street, city, postcode"; sub-bullets or indented rows under one name; a parent or group column | a group, or a list of entries when the parts repeat |
| words of repetition | "for each", "one entry per", "every visit", "list all", "up to three", "one or more", "at least one", "each … has" | a list |
| a choose-many question | "select all that apply", "mark every", checkboxes under one question | a list of values — or one 0/1 column per option (REDCap `name___1`, `name___2`): ask |
| a set of names that varies between records | "results stored under each test's name", "only tests that were run appear" | a lookup — or a group of optional fields when the names are a fixed list: ask |
| a part that varies in kind | "free text, or a block giving …" | mixed |
| a repeating section of the form | REDCap repeating instruments, XLSForm `begin repeat`, ODK repeats, a roster grid on the questionnaire | a list of entries — or a table of its own |
| numbered families of names | `child1_age`, `child2_age`; `med_1`, `med_2`, … | a list delivered wide (numbered columns): ask before you treat it as nested |
| the delivery format | JSON, NDJSON, Parquet, an API, FHIR resources | nesting is possible; CSV and spreadsheets hold it only as JSON text in a cell |
| example values with brackets or braces | `["E11.9", "I10"]`, `{"city": …}` | the shape they show |

A signal is a reason to look closer, not a verdict. Write the shape you settle on, with the words that settled it, in the digest; a variable you cannot place is a question in the plan batch.

## Nested, wide, or long: ask

When a source describes a variable with more than one value per record and does not say how the file holds it, ask in the plan batch (INTERVIEW.md, "The plan questions"), one `structure` question per variable — or one for several that will share the answer:

```json
{"kind": "structure", "importance": "high", "targets": ["household"],
 "question": "In the delivered file, how is the household roster held?",
 "context": "The codebook lists a name, relation and age for every person who lives with the participant (§C), up to 12 people.",
 "evidence": [{"ref": "S01:§Section C", "quote": "For each person: first name; relation to the participant; age in years"}],
 "options": [{"id": "nested", "label": "As a list inside each participant's record — one entry per person", "effect": "One variable, household, with fields household[].name, household[].relation, household[].age."},
             {"id": "wide", "label": "As numbered columns — hh1_name, hh2_name, …", "effect": "One set of columns per person slot, up to 12."},
             {"id": "long", "label": "As a separate file with one row per person", "effect": "A second table, one row per household member, linked by participant_id."}],
 "recommended": "nested", "why": "The codebook says the file keeps these items inside the participant's record rather than in numbered columns.",
 "provisional": "nested"}
```

What each answer means:

- **Nested** (a list or group inside the record, in a JSON file — or as JSON text in a CSV cell) → one variable with fields, as SCHEMA-STYLE.md's "Nested values" writes it. CSV twins and QuaC both read a list or group from JSON text in a cell.
- **Wide** (numbered columns) → flat columns, one set per slot: the slot's shape lives once in `$defs` (SCHEMA-STYLE.md, "Category files"), and each slot gets its own skip pair (SKIP-LOGIC-CATALOG.md, household roster). Ask how many slots there are.
- **Long** (a separate file) → a table of its own with its own grain (INTERVIEW.md, "The plan questions"); a rule between the two tables is not expressible.

Recommend what the sources' words imply — a JSON or Parquet delivery, "kept inside the record", sub-bullets under one name point to nested; numbered names point to wide; a "one row per visit" file points to long. When nothing does, recommend nested only for a JSON delivery, and otherwise recommend the source's layout read literally. Record the answer as applied before drafting the topic; never flatten a nested value into columns, or turn a list into numbered slots, unless the delivered data does.

## What a missing value looks like inside

The rules for special codes hold inside nested values too (SCHEMA-STYLE.md, "Sentinels"): the source's codes on the fields where it gives them, never invented ones. Three things a flat file never raises need an answer from the sources or a person — ask them in the plan batch (INTERVIEW.md, "The plan questions") when the sources are silent:

- **A field with no value inside a group or an entry**: the source's code, `null`, or the field left out of that entry? `null` and a field left out are each a `convention` decision a person answers (SCHEMA-STYLE.md, "Delivered blanks" and "Nested values"). For a field left out, ask too whether that happens only when it was not asked, or also when an answer is missing: only the first lets a rule require it where it was asked (SKIP-LOGIC.md, "Fields left out").
- **A list with nothing in it**: is an empty list a real "none" ("no medications") — and is it also what a person who was never asked holds? When both share the empty list, no rule can tell them apart (SKIP-LOGIC.md, "Rules inside nested values").
- **A whole nested value for someone not asked**: an empty list, `null`, a special code in place of the list, or the variable left out of the record? Encode what is delivered; a variable left out needs a `convention` decision like a field left out, and its rules say whether it is there (SKIP-LOGIC.md, "Fields left out").

`null` follows "Delivered blanks" wherever it sits — a field of an entry, an item of a list, a whole nested value: a branch `{"const": null, "title": "Missing (null)", "x-value-kind": "sentinel"}` where the decision puts it, citing the decision on `value:null`. A dictionary type such as "array of integer (nullable)" does not say whether the list or its entries may be null: ask which.

## Names

A field inside a nested value is named by its path from the record, the way the data dictionary page and QuaC name it:

| what | name |
|---|---|
| a field of a group | `address.city`; deeper: `contact.address.postcode` |
| a field of every entry of a list | `household[].age`; deeper: `visits[].labs.ldl` |
| the values of a lookup | `labs.*` |
| a name that is not a plain word (spaces, dots, brackets, quotes, `*`, or a leading `/`) | `odd["my field"]` |

A list of values is one variable (`diagnoses`): its codes are its own, and its items have no names. QuaC and the website count list positions from 1 when they point at one entry — `household[2].age` is the second person's age — and drop the position when they speak of the field (`household[].age`).

Use these names everywhere a variable is named: `state/variables.csv` (one row for the variable and one per field inside it — `household`, then `household[].name`, `household[].relation`, `household[].age`), a decision's `targets`, a rule's `gates` and `targets`, `show 'variable:household[].age'` (quoted: the shell reads brackets), and the website's links. Every field is inventoried, titled, traced, and covered by toy data like any variable; `check` holds all of it to the same standard.

## In plain words

People never see "object", "array", or brackets in your messages. Say "the address has four parts", "a list of household members — one entry per person, with their name, relation and age", "a list of diagnosis codes", "lab results under each test's name". On the website the dictionary shows each field as an indented row under its variable, and a mismatch inside a list names the entry: "household member 2: age 130 is above the highest plausible age".
