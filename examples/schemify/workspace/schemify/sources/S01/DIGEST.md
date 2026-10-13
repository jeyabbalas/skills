# S01 digest — Ashgrove data dictionary (release 2)

Source: `schemify/sources/ashgrove_dictionary_r2.xlsx` (hash in `extract/manifest.json`), read from the extracted `sheet-01-variables.csv` and `sheet-02-codes.csv`; the workbook itself was not opened. Locators: `<sheet> row N` is the Excel row number (the extract's `_row`); `¶N` cites S02, the baseline questionnaire, which was read only for the comparison in section 6.

Contents: [1. What it is](#1-what-it-is) · [2. How to read it](#2-how-to-read-it) · [3. Variables](#3-variables) · [4. Skip logic and conditions](#4-skip-logic-and-conditions) · [5. Other facts](#5-other-facts) · [6. Problems](#6-problems)

## 1. What it is

- A data dictionary in an Excel workbook (sheets "Variables" and "Codes", both visible) for the "Ashgrove Community Health Survey (synthetic)", per its title in Variables row 1.
- Release 2 of the baseline dictionary (Variables row 1; file `ashgrove_dictionary_r2.xlsx`), describing one table of baseline data, "One record per participant" (Variables row 2): 15 variables (Variables rows 5-19) and 4 special codes (Codes rows 2-5). No table or file name, release date, or wave other than "baseline" is stated.

## 2. How to read it

- Both sheets are visible. The manifest reports no merged cells, no hidden rows or columns, no cell comments and no warnings. Both hold dictionary text (18 and 5 rows), not records, so both were read.
- **Variables sheet** (A1:F19): row 1 is the title (A1); row 2 is a note (A2), "One record per participant. Special codes are listed on the Codes sheet."; row 3 is blank (absent from the extract); row 4 is the header; rows 5-19 hold one variable per row (15 variables). Nothing follows row 19.
- Variables columns, from the row 4 header: A `Variable` (name) · B `Label` · C `Type` (text, integer or number) · D `Values / range` (a `lo-hi` range, a list, or a pattern in words; blank for coded variables) · E `Codes` (value labels and special codes together) · F `Notes`.
- **Codes sheet** (A1:C5): row 1 is the header `Code` | `Meaning` | `Notes`; rows 2-5 are the four special codes, in the order -6, -7, -9, -1. It is the only place the bare numbers in Variables column E get a meaning. Value labels such as `1=Yes` are written inline in column E and are not repeated on the Codes sheet.
- Easy to misread:
  - Column E mixes two kinds of entry separated by `; `: `value=label` pairs (`1=Yes`) and bare negative numbers (`-9`). A bare number is a special code defined on the Codes sheet, not a value label. In every cell the pairs come first.
  - A blank column D is not "any value": the five variables with a blank D (`sex`, `smk_ever`, `smk_status`, `breastfed_ever`, `diabetes_dx`) are all coded and take the `value=label` pairs in E.
  - `site` is text: D "01, 02, 03" is a list, not a range, and F says "Leading zero kept".
  - `participant_id` column D is a pattern in words ("ACH followed by 4 digits"), not a regex.
  - Ranges use an ASCII hyphen (`18-85`) and special codes use the same hyphen as a minus sign. Every stated range is non-negative, so the two cannot be confused.
  - Notes (F) mixes provenance, format and routing hints; there is no separate routing column (see section 4).
  - "kg/m2" in the BMI label is plain text for kg/m².

## 3. Variables

Label, type, range, codes and notes are copied verbatim from the Variables sheet; `—` marks a blank cell. The Codes cell is split: `value=label` pairs go in "codes and labels", the bare special codes in "missing-value codes". Their meanings are in section 4 (Codes rows 2-5): -6 Not applicable, -7 Refused, -9 Don't know, -1 Not measured.

| variable | label | type | range / pattern | codes and labels | missing-value codes | notes | locator |
|---|---|---|---|---|---|---|---|
| `participant_id` | Participant ID | text | ACH followed by 4 digits | — | — | Assigned at enrollment | Variables row 5 |
| `site` | Recruitment site | text | 01, 02, 03 | 01=Northgate; 02=Riverside; 03=Hillcrest | — | Leading zero kept | Variables row 6 |
| `age` | Age at interview (years) | integer | 18-85 | — | -9 | — | Variables row 7 |
| `sex` | Sex | integer | — | 1=Male; 2=Female | -7 | Recorded by interviewer | Variables row 8 |
| `smk_ever` | Smoked at least 100 cigarettes in lifetime | integer | — | 1=Yes; 2=No | -7; -9 | — | Variables row 9 |
| `smk_status` | Current smoking status | integer | — | 1=Current; 2=Former | -6; -9 | — | Variables row 10 |
| `cigs_day` | Cigarettes per day (current smokers) | integer | 0-99 | — | -6; -9 | Current smokers only | Variables row 11 |
| `smk_age_start` | Age started smoking (years) | integer | 5-80 | — | -6; -9 | — | Variables row 12 |
| `menarche_age` | Age at first menstrual period (years) | integer | 8-20 | — | -6; -9 | Women only | Variables row 13 |
| `parity` | Number of live births | integer | 0-15 | — | -6; -9 | Women only | Variables row 14 |
| `age_first_birth` | Age at first live birth (years) | integer | 14-50 | — | -6; -9 | — | Variables row 15 |
| `breastfed_ever` | Ever breastfed | integer | — | 1=Yes; 2=No | -6; -9 | — | Variables row 16 |
| `bmi` | Body mass index (kg/m2) | number | 12.0-70.0 | — | -1 | Measured at clinic visit | Variables row 17 |
| `diabetes_dx` | Ever told you have diabetes | integer | — | 1=Yes; 2=No | -9 | — | Variables row 18 |
| `diabetes_age` | Age at diabetes diagnosis (years) | integer | 10-85 | — | -6; -9 | Asked only if diabetes_dx = 1 | Variables row 19 |

## 4. Skip logic and conditions

The workbook has no "go to" instruction, no branching column, no section rows and no indentation. Routing appears only as Notes text (repeated once in a label), as a "-6" in a variable's Codes cell, and on the Codes sheet. Only R1 names its gate variable and value.

**What the Codes sheet says each special code means** (columns `Meaning` and `Notes`):

| code | meaning | note | variables whose Codes cell lists it (Variables sheet) | locator |
|---|---|---|---|---|
| -6 | Not applicable | Question not asked of this participant (skip pattern) | `smk_status`, `cigs_day`, `smk_age_start`, `menarche_age`, `parity`, `age_first_birth`, `breastfed_ever`, `diabetes_age` (8) | Codes row 2 |
| -7 | Refused | — | `sex`, `smk_ever` (2) | Codes row 3 |
| -9 | Don't know | — | `age`, `smk_ever`, `smk_status`, `cigs_day`, `smk_age_start`, `menarche_age`, `parity`, `age_first_birth`, `breastfed_ever`, `diabetes_dx`, `diabetes_age` (11) | Codes row 4 |
| -1 | Not measured | Clinic measurement not taken | `bmi` (1) | Codes row 5 |

The Codes sheet does not say which skip patterns -6 stands for, or who is not asked.

**Routing statements** (source text in quotes):

| id | kind | text | variables involved | locator |
|---|---|---|---|---|
| R1 | explicit: "asked only if" | "Asked only if diabetes_dx = 1" | gate `diabetes_dx` (1=Yes); skipped follow-up `diabetes_age` (lists -6; -9) | Variables row 19 (Notes) |
| R2 | implicit: Notes names a subgroup | "Current smokers only"; the label repeats it: "Cigarettes per day (current smokers)" | `cigs_day` (lists -6; -9). Gate variable and value not stated; `smk_status` 1=Current (Variables row 10) is the evident candidate (inference) | Variables row 11 (Notes, Label) |
| R3 | implicit: Notes names a subgroup | "Women only" | `menarche_age` (lists -6; -9). Gate not stated; `sex` 2=Female (Variables row 8) is the evident candidate (inference) | Variables row 13 |
| R4 | implicit: Notes names a subgroup | "Women only" | `parity` (lists -6; -9). Gate not stated, as R3 | Variables row 14 |
| R5 | implicit: "Not applicable" code with no stated condition | no Notes; the Codes cell reads "-6; -9" | `smk_status`, `smk_age_start`, `age_first_birth`, `breastfed_ever`. Who is not asked is not stated | Variables rows 10, 12, 15, 16 |
| R6 | implicit: measurement condition | "Measured at clinic visit"; code -1 means "Not measured" ("Clinic measurement not taken") | `bmi` (lists -1 only, no -6 or -9) | Variables row 17; Codes row 5 |

Row order is the only grouping, and the source does not label it: smoking `smk_ever` to `smk_age_start` (rows 9-12), reproductive `menarche_age` to `breastfed_ever` (rows 13-16), clinic `bmi` (row 17), diabetes `diabetes_dx`, `diabetes_age` (rows 18-19). I note it only because the R5 variables sit inside the first two blocks; it is an inference from names and order, not a stated rule.

## 5. Other facts

- **ID pattern:** `participant_id` is text, "ACH followed by 4 digits" (Variables row 5), assigned at enrollment. My reading of the words is `^ACH[0-9]{4}$`; the source gives no regex or example and says nothing about case. "One record per participant" (Variables row 2) implies one ID per record, but uniqueness is not stated as a rule.
- **Sites:** `site` is text with allowed values "01, 02, 03" (Variables row 6, column D) and labels 01=Northgate; 02=Riverside; 03=Hillcrest (column E). "Leading zero kept" means the values are the strings "01", "02", "03", not the integers 1-3.
- **Special codes sit outside every range:** the four codes are negative integers (-1, -6, -7, -9); every stated range is non-negative (lowest lower bound is 0, for `cigs_day` and `parity`). A numeric variable therefore takes either an in-range value or one of the special codes in its own Codes cell.
- **Special codes are per variable, not blanket:** `age` accepts -9 but not -7, `sex` accepts -7 but not -9, `bmi` accepts only -1, `participant_id` and `site` accept none (Variables rows 5-8, 17).
- **Types:** 2 text (`participant_id`, `site`), 12 integer, 1 number (`bmi`, whose range 12.0-70.0 is the only one with a decimal; Variables row 17). Yes/No variables are integers coded `1=Yes; 2=No`, not booleans (Variables rows 9, 16, 18).
- **Units:** ages are in years (labels, Variables rows 7, 12, 13, 15, 19); `bmi` is kg/m2 (row 17); `cigs_day` is per day (row 11).
- **Provenance notes:** `sex` "Recorded by interviewer" (Variables row 8); `bmi` "Measured at clinic visit" (row 17); `participant_id` "Assigned at enrollment" (row 5).
- **Version and wave:** "baseline" and "release 2" (Variables row 1), and the file name suffix `_r2`. The project calls this source "revision 2"; the workbook never uses that word. There is no release date, change log, or description of other waves or releases.
- **"(synthetic)":** the survey is labelled synthetic in the title (Variables row 1).
- **Not stated anywhere:** derivations or recodes (BMI's formula is not given and no derived variable is flagged), required/optional flags, whether blanks are allowed, cross-variable rules (for example an age at an event against `age`), and the number of participants.

## 6. Problems

1. **Gate variables whose own special codes leave the routing undefined.**
   - `sex` lists -7 (Variables row 8), yet `menarche_age` and `parity` are "Women only" (Variables rows 13-14). What they hold when `sex` is -7 (Refused) is not stated.
   - `smk_ever` lists -7 and -9 (Variables row 9). No Notes entry names it as a gate, so what `smk_status`, `cigs_day` and `smk_age_start` (rows 10-12, each listing -6) hold when `smk_ever` is 2, -7 or -9 is not stated.
   - `smk_status` lists -6 and -9 (Variables row 10). `cigs_day` is "Current smokers only" (row 11), but what it holds when `smk_status` is -6 or -9 is not stated.
   - `diabetes_dx` lists -9 (Variables row 18). "Asked only if diabetes_dx = 1" (row 19) implies `diabetes_age` is not asked when `diabetes_dx` is 2 or -9, but the value it then holds is not stated; both -6 and -9 are listed for it.
2. **"-6" listed with no stated condition.** `smk_status` (Variables row 10), `smk_age_start` (row 12), `age_first_birth` (row 15) and `breastfed_ever` (row 16) list -6 and have blank Notes; Codes row 2 says only "Question not asked of this participant (skip pattern)". Whom they are not asked of is not stated. Specific gaps: `smk_status` offers only "1=Current; 2=Former", so what a never-smoker holds is not stated; `age_first_birth` and `breastfed_ever` lack the "Women only" note of rows 13-14; `parity` allows 0 (range 0-15, row 14) but nothing says whether women with 0 live births are -6 on these two.
3. **Gates are named once.** "Current smokers only" (Variables row 11) and "Women only" (rows 13-14) name a subgroup but not the variable and value that define it. The links to `smk_status` = 1 and `sex` = 2 are inference (section 4).
4. **`cigs_day` range admits 0.** "0-99" (Variables row 11) includes 0 for a variable that is "Current smokers only"; whether 0 is a valid answer for a current smoker is not stated.
5. **Disagreements with S02** (read only to compare; not digested):
   - `cigs_day` range: this dictionary says "0-99" (Variables row 11); S02 says "B3. IF SMOKES NOW: On average, how many cigarettes do you smoke a day? (1–60) ____" (¶10).
   - `smk_age_start` label: this dictionary says "Age started smoking (years)" (Variables row 12); S02 asks "B4. How old were you when you started smoking regularly? ____ years" (¶11). The questionnaire says "regularly"; the label does not. A wording difference unless the data show otherwise.
   - Nothing else visibly disagreed in the items compared: the `1`/`2` code values for sex, smoking, breastfeeding and diabetes, the smoking and women-only routing, the diabetes follow-up, and the clinic-measured BMI.
6. **Checks that found nothing.** Every special code on the Variables sheet (-1, -6, -7, -9) is defined on the Codes sheet, and every Codes row is used by at least one variable. Every variable with a skip note ("Current smokers only", "Women only", "Asked only if diabetes_dx = 1") lists -6. No typos found in the two sheets; the only non-ASCII character is the em dash in Variables row 1.
7. **Not checked.** Cell number formats, data-validation lists and defined names do not appear in the extract, and the workbook was not opened, so they are unchecked.
