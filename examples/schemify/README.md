# schemify example — the Ashgrove Community Health Survey (synthetic)

A complete schemify workspace, committed as it stood at the end of a run. The study is fictional and so are its documents: `workspace/metadata/` holds what the author handed over — a data dictionary (`ashgrove_dictionary_r2.xlsx`, two sheets: variables and special codes) and the baseline questionnaire (`ashgrove_baseline_questionnaire.docx`). They were written to disagree and to stay silent in the ways real documentation does:

- the dictionary says cigarettes per day run 0–99; the questionnaire's answer box says 1–60. The agent put the contradiction to the person, recommending the dictionary's range, and they chose 1–60;
- the skip patterns come from the questionnaire's routing instructions ("IF NO, GO TO…", women-only sections), each rule cited to the paragraph that states it; the diabetes follow-up is stated in both documents;
- nothing says women with no live births skip "age at first birth" and "ever breastfed". The agent asked before inferring the rule; the person knew it was done that way, so it is encoded on their word;
- neither document says what refused or don't-know answers to a gate question do to the questions behind it. Each case became a question with a recommended answer.

## What happened in the run

Seven sessions, each closed with a written handoff (`state/ledger.jsonl` → `session` events). The simulated person was the study's data manager, who is also its data steward. They answered 35 questions in 8 batches on the website and approved the four topics one by one. Along the way they volunteered what the 2024 cleaning changed — ages above 85 top-coded, implausible smoking-start ages recoded to don't-know, BMI rounded to one decimal — and each fact is a decision cited where it applies.

They then checked a 40-row extract of their "real" data in QuaC, in the browser. That extract was synthetic, built to test the agent, and is not included here. The agent saw only QuaC's findings — counts and column names, no values (`alignment/A01.json`). It never opened the file, asking about it only by name. The 13 failed checks became four questions:

- every ID failed the pattern the person had confirmed: they explained the 2024 release adds a hyphen, so the pattern changed and the earlier decision is superseded;
- five ages were data-entry errors, a data issue, so the schema stayed;
- the 10 missing variables (a partial extract) and an extra quality-control column were recorded as expected.

## Look around

- `workspace/schemify/index.html` — the project website. Double-click it: everything shows from disk. To see it as during a run, with live updates and one-click sending, serve it: `python3 workspace/schemify/tools/serve.py`, then open the address it prints. The Data check tab's tables load the data-table library from jsDelivr, so they need a network connection.
- `workspace/schemify/package/` — the deliverable: `README.md` (start there), `PROVENANCE.md`, `schemas/`, `toy-data/`, `dictionary.html`, and `tools/validate.py`.
- `workspace/schemify/state/ledger.jsonl` — every source, decision, rule, question batch, data check, and session, in order.

Check it yourself: `uv run workspace/schemify/package/tools/validate.py summary workspace/schemify/package`. Expect 6 schema files valid, 10 rules, 15 valid toy rows passing, 46/46 seeded errors caught, and 15/15 properties traced.

## Restoring what git leaves out

The synthetic data extract, which the agent never saw, is not included. The text and tables the agent extracted from the two documents are left out too, because they regenerate: the digests cite them, in `workspace/schemify/sources/S01/extract/` and `S02/extract/`. To restore them, run these from `examples/schemify/workspace`:

```
uv run ../../../skills/schemify/scripts/extract.py schemify/sources/ashgrove_dictionary_r2.xlsx --out schemify/sources/S01/extract --id S01
uv run ../../../skills/schemify/scripts/extract.py schemify/sources/ashgrove_baseline_questionnaire.docx --out schemify/sources/S02/extract --id S02
```

The run's machine-specific paths in `START-HERE.md` and the website's data were replaced with repository-relative ones. Rebuilding (`uv run skills/schemify/scripts/schemify.py --ws examples/schemify/workspace/schemify build`) writes your own.

## How to prompt the agent

```
/schemify metadata/ashgrove_dictionary_r2.xlsx metadata/ashgrove_baseline_questionnaire.docx
/schemify                                   (resume: it says where things stand and continues)
/schemify the steward says -7 never occurs for sex; drop it
/schemify review                            (the data steward's review)
```

One honest note: the person's side of this run was simulated. A second AI agent, working for the skill's author, played the data manager and answered on the website as a person would. Every file here is real output of the skill's scripts and of the agent that ran them.
