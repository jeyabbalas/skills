# Ashgrove Community Health Survey (ACH) — JSON Schema package

Baseline interview data from the Ashgrove Community Health Survey (ACH): the Ashgrove Regional Health Unit ran the baseline interviews in 2022 and 2023, and the study's documents label the data synthetic. This package describes the 2024 data release (release 2 of the baseline data dictionary): one record per participant, recruited at three sites (Northgate, Riverside and Hillcrest), with age and sex, smoking history, women's reproductive health, body mass index measured at a clinic visit, and diabetes history. It follows the data dictionary and the baseline interview questionnaire, corrected by the data steward where the 2024 cleaning changed the data; for example, participant IDs carry a hyphen after the prefix and cigarettes per day is capped at 60. A smaller extract is sent to collaborators who only need demographics and smoking; it omits the other variables, so checking an extract against these schemas reports them as missing. Exports may also carry a "canary" quality-control column, which is not study data.

| Table | Mother schema | One row is | Topics | Variables |
|---|---|---|---|---|
| Baseline (`baseline`) | `schemas/baseline/baseline.schema.json` | One element is one participant. | 4 | 15 |

Status: 4 of 4 topics confirmed by a person. 6 schema files valid · 10 rules · toy data: 15 valid rows pass, 46/46 seeded errors caught · provenance: 15/15 properties traced. 

## Validate data against these schemas

```bash
pip install -r tools/requirements.txt          # or prefix the commands below with: uv run
python3 tools/validate.py summary .            # the package checks itself: schemas, toy data, provenance
python3 tools/validate.py data . --file your_data.csv   # validate a data file (JSON array, CSV or TSV)
python3 tools/validate.py rules .              # every skip pattern and conditional rule, parsed
```

For sensitive data, [QuaC](https://jeyabbalas.github.io/quac/) runs entirely in your browser: drop the data file into **Dataset** and this package's `schemas/` folder into **JSON Schema**, press **Run QC**, and under **Findings without data** download a summary that holds no data values — safe to share with whoever maintains these schemas. Press **Reset** in QuaC afterwards: it keeps loaded files in the browser until you do.

## Browse

Open `dictionary.html` — a searchable data dictionary that works offline. Its **Semantic search** switch downloads a small text model once (about 50 MB, from huggingface.co and cdn.jsdelivr.net) and then also finds variables by meaning; your schemas never leave the browser.

## Files

```text
PROVENANCE.md
README.md
assets/
  LICENSE-json-schema-mark.txt
  embed-worker.js
  json-schema-data-dictionary.global.js
  schemify.css
dictionary.html
provenance.json
schemas/
  baseline/
    baseline.schema.json
    categories/
      about_you.json
      health.json
      smoking.json
      womens_health.json
  common/
    defs.json
tools/
  requirements.txt
  validate.py
toy-data/
  baseline/
    invalid-ledger.json
    invalid.csv
    invalid.json
    valid.csv
    valid.json
```

## How the schemas are written

- Each table's mother schema is an array of records; a record is the `allOf` of its topic files, and `unevaluatedProperties: false` rejects any column the topics do not declare.
- A coded variable is a `oneOf` of `const` branches, each with a `title`; a measured variable is an `anyOf` of one typed branch (with plausibility bounds) plus its special codes.
- Every column is required in every record: a missing or not-applicable value is a declared code in the cell, never an absent key. Special codes carry `"x-value-kind": "sentinel"`.
- `x-provenance` on every property and rule names where each fact came from — a source (`S01:<location>`) or a decision (`D014`); see PROVENANCE.md.
- The `$id`s use the placeholder namespace `https://schemas.example.org/ashgrove/`, which nothing fetches. Replace it before publishing these schemas anywhere public.

### Missing-value codes

| Code | Meaning | Skipped by design? | Decided in |
|---|---|---|---|
| `-6` | Not applicable (skipped by design) | yes | D010 |
| `-7` | Refused | no | D010 |
| `-9` | Don't know | no | D010 |
| `-1` | Not measured | no | D010 |

## Skip patterns and other conditional logic

Every rule is one entry of its mother schema's `items.allOf`, after the topic references, in one canonical shape: `{"$comment", "x-provenance", "if", "then"}`. The `if` is one clause — or an `anyOf` of clauses — of `required` plus `properties` tests (`const`, `enum`, `not`, or a numeric range); the `then` sets `properties` effects (`const`, `not const`, `enum`, or a narrowed range) or requires at least one of them (`anyOf`). The `$comment` starts with its kind and id — `Skip pattern R001:`, `Applicability R001:` (the same rule read the other way), or `<Domain> routing R007:`. `tools/validate.py rules .` prints every rule in parsed form.

| Rule | Table | Reading | Evidence | Provenance |
|---|---|---|---|---|
| R001 | baseline | Skip pattern R001: people who have not smoked 100 cigarettes (smk_ever = 2), or who refused or did not know (-7, -9), skip the smoking questions that follow, so smk_status, cigs_day and smk_age_start are -6. Questionnaire ¶8: 'IF NO, GO TO SECTION C.'; the data steward says refusals and don't-know answers at B1 were routed like No (D017) and confirms the -6 coding (D018); dictionary Codes row 2: -6 is 'Question not asked of this participant (skip pattern)'. | documented | default: ['S02:¶8', 'D017'], value:-6: D018 |
| R001 | baseline | Applicability R001: people who have smoked 100 cigarettes (smk_ever = 1) were asked whether they smoke now and when they started, so smk_status and smk_age_start are never -6. Questionnaire ¶8 to ¶11: only 'No' at B1 skips B2 to B4 (refusals and don't-know answers count as No: D017); the data steward confirms the rule matches the delivered data (D018). | documented | default: ['S02:¶8', 'D018'] |
| R002 | baseline | Skip pattern R002: former smokers (smk_status = 2), and people who did not know (-9) whether they smoke now, were not asked how many cigarettes they smoke, so cigs_day is -6. Questionnaire ¶10: 'IF SMOKES NOW:'; dictionary Variables row 11: 'Current smokers only'; a don't-know answer is treated like No (D017 for the first question, confirmed for this one in D029); the data steward confirms the -6 coding (D018). | documented | default: ['S02:¶10', 'D017', 'D029'], value:-6: D018 |
| R002 | baseline | Applicability R002: current smokers (smk_status = 1) were asked how many cigarettes they smoke, so cigs_day is never -6. The data steward confirms the rule matches the delivered data (D018). | documented | default: ['S02:¶10', 'D018'] |
| R003 | baseline | Skip pattern R003: men (sex = 1), and people whose sex was refused (-7), skip the women's-health section, so menarche_age, parity, age_first_birth and breastfed_ever are -6. Questionnaire ¶13: 'ASK SECTION C OF WOMEN ONLY (A2 = 2). MEN: GO TO SECTION D.'; dictionary Variables rows 13 and 14: 'Women only'; the data steward says a refused sex is skipped like men (D021) and confirms the -6 coding (D022). | documented | default: ['S02:¶13', 'D021'], value:-6: D022 |
| R003 | baseline | Applicability R003: women (sex = 2) were asked the age at first period and the number of live births, so menarche_age and parity are never -6. The data steward confirms the rule matches the delivered data (D022). | documented | default: ['S02:¶13', 'D022'] |
| R004 | baseline | Skip pattern R004: people who were not told they have diabetes (diabetes_dx = 2), or who did not know (-9), were not asked the age at diagnosis, so diabetes_age is -6. Questionnaire ¶21: 'IF YES:'; dictionary Variables row 19: 'Asked only if diabetes_dx = 1'; the data steward says a don't-know answer means the age was not asked (D024) and confirms the -6 coding (D025). | documented | default: ['S02:¶21', 'D024'], value:-6: D025 |
| R004 | baseline | Applicability R004: people who were told they have diabetes (diabetes_dx = 1) were asked the age at diagnosis, so diabetes_age is never -6. The data steward confirms the rule matches the delivered data (D025). | documented | default: ['S02:¶21', 'D025'] |
| R005 | baseline | Skip pattern R005: women with no live births (parity = 0) have no first birth and no children to breastfeed, so age_first_birth and breastfed_ever are -6. The documents do not state this routing; the data steward vouches for it (D020). | told | default: D020 |
| R005 | baseline | Applicability R005: women with at least one live birth (parity 1 to 15) were asked the age at first birth and about breastfeeding, so age_first_birth and breastfed_ever are never -6 (they may still be refused or don't know). The documents do not state this routing; the data steward vouches for it (D020). | told | default: D020 |

## Documented but not enforced

Rules JSON Schema cannot express (arithmetic, ordering, cross-row, cross-table). Check them downstream.

- R006 (baseline): participant_id is unique across rows: one record per participant
- baseline: Not enforceable here: participant_id is unique across rows, one record per participant (S01:Variables row 2, D009).

## Provenance

| Source | Title | Kind | Status |
|---|---|---|---|
| S01 | Ashgrove data dictionary (release 2) | document | active |
| S02 | Ashgrove baseline questionnaire | document | active |

22 decisions are listed in PROVENANCE.md and machine-readably in provenance.json.

## Open items

- None.

---

Generated 2026-10-13 by [schemify](https://github.com/jeyabbalas/skills) from its working record. Edit the schemas, not this file — it is regenerated.
