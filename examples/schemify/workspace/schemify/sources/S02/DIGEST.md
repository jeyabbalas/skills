# S02 — Ashgrove baseline questionnaire: digest

Table of contents

- [1. What it is](#1-what-it-is)
- [2. How to read it](#2-how-to-read-it)
- [3. Variables](#3-variables)
- [4. Skip logic and conditions](#4-skip-logic-and-conditions)
- [5. Other facts](#5-other-facts)
- [6. Problems](#6-problems)

Locators: `¶N` is the paragraph's position among the 21 body paragraphs of the Word file, the prefix of each line in `extract/text.md` (no paragraph is empty). `S01:Variables row N` and `S01:Codes row N` are Excel row numbers (the `_row` column) in the sibling dictionary S01, which was read only to map questions to variables and to compare; it is not digested here.

## 1. What it is

- Interviewer-administered questionnaire (an interview script with routing instructions) of the Ashgrove Community Health Survey (synthetic), as a Word file of 21 paragraphs: a title (¶1), one instruction line (¶2), four lettered sections A–D and 13 numbered questions (¶3–¶21).
- Version or wave: only "Baseline interview" (¶1) — no release number, date or form id is printed, and no table or dataset is named. By content, 13 of its questions line up with 13 of the 15 variables of the baseline dictionary S01 ("release 2", "One record per participant": S01:Variables rows 1–2), so it presumably feeds that participant-level table; S02 never says so.

## 2. How to read it

- **Order.** ¶1 is the title (Heading 1). ¶2 is the only general instruction: `Interviewer: read each question aloud. Follow the routing instructions in capitals.` Four sections follow, each opened by a Heading 2 line `Section X. <title>`: A About you (¶3), B Smoking (¶6), C Women's health (¶12), D Health (¶18). Questions are numbered `<section letter><n>.` and restart in each section (A1–A2, B1–B4, C1–C4, D1–D3); one question per paragraph; no tables, bullets or indentation.
- **Response options** follow the question on the same line: a label, then its code in square brackets, options separated by three spaces — `Yes [1]   No [2]`. The bracketed number is the code to record and it comes after its label. All five coded questions (A2, B1, B2, C4, D2) have exactly two options, codes 1 and 2. No refused, don't-know, not-applicable or not-measured option is printed anywhere.
- **Write-in answers** are a blank of four underscores, `____`, usually followed by a unit word (`____ years`). B3 prints a range before its blank (`(1–60) ____`); C2 has a bare `____`.
- **Capitals are the interviewer's instructions**; ¶2 calls the routing ones "routing instructions in capitals". Capitalised text in S02: `INTERVIEWER: RECORD SEX.` (¶5, a recording instruction), `IF NO, GO TO SECTION C.` (¶8), `IF SMOKES NOW:` (¶10), `ASK SECTION C OF WOMEN ONLY (A2 = 2). MEN: GO TO SECTION D.` (¶13), `IF YES:` (¶21). ¶2 does not say in so many words that capitals are not read aloud.
- **`(Clinic)`** at the start of D1 (¶19) is not in capitals. It marks D1 as a measured value rather than a question: D1 has no question mark and no answer format.
- **Easy to misread**
  - `IF NO, GO TO SECTION C.` (¶8) is its own paragraph after B1 and names no question. "NO" is B1's `No [2]` by position, not B2's `No, I have quit [2]` (¶9), which only people who answered Yes at B1 reach.
  - Going to Section C is not the end of the route for men: ¶13 then sends them on to Section D.
  - `(A2 = 2)` in ¶13 cites A2's recorded code: 2 = Female (¶5).
  - `IF SMOKES NOW:` and `IF YES:` sit inside the B3 and D3 paragraphs and govern those questions only; B4 (¶11) has no prefix.
  - Yes is [1] and No is [2] on B1, C4 and D2 — not 1/0.
  - "read each question aloud" (¶2) does not fit A2 (recorded by the interviewer) or D1 (a measurement).
- **Layout** adds nothing beyond paragraph order and the headings (Problems 6).

## 3. Variables

13 questions; none names a variable. Variable names are the dictionary's (S01), matched by label. In `variables-found.csv`, `type` says how the answer is printed (`write-in blank` = a `____` field; `choice` = options with bracketed codes) because S02 prints no data type; an empty `codes` cell means no codes are printed; `missing` is `not stated` in every row.

| Q | Question text (verbatim) | Response options (verbatim) | Variable | Locator |
|---|---|---|---|---|
| A1 | How old are you? | `____ years` | likely `age` (by label, S01:Variables row 7) | ¶4 |
| A2 | INTERVIEWER: RECORD SEX. | `Male [1]   Female [2]` | likely `sex` (by label, S01:Variables row 8) | ¶5 |
| B1 | Have you smoked at least 100 cigarettes in your entire life? | `Yes [1]   No [2]` | likely `smk_ever` (by label, S01:Variables row 9) | ¶7 |
| B2 | Do you smoke cigarettes now? | `Yes, I smoke now [1]   No, I have quit [2]` | likely `smk_status` (by label, S01:Variables row 10) | ¶9 |
| B3 | IF SMOKES NOW: On average, how many cigarettes do you smoke a day? | `(1–60) ____` | likely `cigs_day` (by label, S01:Variables row 11) | ¶10 |
| B4 | How old were you when you started smoking regularly? | `____ years` | likely `smk_age_start` (by label, S01:Variables row 12) | ¶11 |
| C1 | How old were you when you had your first menstrual period? | `____ years` | likely `menarche_age` (by label, S01:Variables row 13) | ¶14 |
| C2 | How many live births have you had? | `____` | likely `parity` (by label, S01:Variables row 14) | ¶15 |
| C3 | How old were you at your first live birth? | `____ years` | likely `age_first_birth` (by label, S01:Variables row 15) | ¶16 |
| C4 | Did you ever breastfeed any of your children? | `Yes [1]   No [2]` | likely `breastfed_ever` (by label, S01:Variables row 16) | ¶17 |
| D1 | (Clinic) Body mass index recorded from measured height and weight. | none printed | likely `bmi` (by label, S01:Variables row 17) | ¶19 |
| D2 | Has a doctor ever told you that you have diabetes? | `Yes [1]   No [2]` | likely `diabetes_dx` (by label, S01:Variables row 18) | ¶20 |
| D3 | IF YES: How old were you when you were told? | `____ years` | likely `diabetes_age` (by label, S01:Variables row 19) | ¶21 |

No question for `participant_id` (S01:Variables row 5, note "Assigned at enrollment") or `site` (row 6): S02 has no field for either and does not say how they are captured.

## 4. Skip logic and conditions

All routing is in capitals (¶2). Four rules are stated (R1–R4); R5 is a dependency the wording suggests but S02 does not state; R6 is an implicit condition. Every rule shares two gaps, spelled out per rule below and summarised in Problems 2: S02 prints no refused or don't-know option, so a gate answered that way is undefined; and S02 never says what a skipped question is recorded as.

**G — ¶2 — explicit, general.** `Interviewer: read each question aloud. Follow the routing instructions in capitals.` Covers the whole document and is the only statement that capitals carry routing; it states no rule itself. The one other capitalised line that is not a rule below, `INTERVIEWER: RECORD SEX.` (¶5), is a recording instruction for A2, not routing.

**R1 — ¶8 — explicit (a stated "go to").** Text: `IF NO, GO TO SECTION C.`
- Gate: B1 (¶7), likely `smk_ever`, answer `No [2]`. The instruction names no question; B1 is read from position (it is the paragraph right after B1).
- Skips: B2, B3, B4 (¶9–¶11), likely `smk_status`, `cigs_day`, `smk_age_start`. Next asked: Section C, where R3 applies.
- Not said: what happens if B1 is refused or don't know (no such option is printed; the dictionary allows `-7; -9`, S01:Variables row 9); what B2–B4 are recorded as when skipped (the dictionary lists `-6` on rows 10–12; S02 mentions no code); that Yes continues to B2 (follows from order only); what happens to a person who answers No at B1 but smokes now (fewer than 100 cigarettes) — B2 is never asked of them.

**R2 — ¶10 — explicit (inline condition, worded as a description, not a code).** Text: B3 begins `IF SMOKES NOW:`
- Gate: B2 (¶9), likely `smk_status`, option `Yes, I smoke now [1]`.
- Skips: B3 (likely `cigs_day`) when B2 is `No, I have quit [2]` (B3 is already skipped through R1 when B1 = No). B4 (¶11) has no condition, so by the document it follows for current smokers and quitters alike once B1 was Yes.
- Not said: B2 refused or don't know (the dictionary allows `-9` but not `-7` for `smk_status`, S01:Variables row 10); what B3 is recorded as for quitters (dictionary: `-6`, and the note "Current smokers only", row 11); whether B4 is meant for quitters (nothing is stated either way).

**R3 — ¶13 — explicit; also implicit in the heading (¶12).** Text: `ASK SECTION C OF WOMEN ONLY (A2 = 2). MEN: GO TO SECTION D.`
- Gate: A2 (¶5), likely `sex`, code 2 = Female. The heading "Section C. Women's health" (¶12) also names the subgroup (implicit).
- Skips: C1–C4 (¶14–¶17), likely `menarche_age`, `parity`, `age_first_birth`, `breastfed_ever`, for A2 = 1 (Male). Next asked: Section D (D1, ¶19).
- Scope: the whole section — the line is the first thing under the Section C heading and names "SECTION C".
- Interaction with R1: B1 = No sends everyone to Section C, where this line re-routes men to D; S02 does not spell out that sequence.
- Not said: what happens if A2 is missing or refused (the dictionary allows `-7` for `sex`, S01:Variables row 8; S02 prints no such option), since the person is then neither "women" nor "men"; what C1–C4 are recorded as for men (the dictionary lists `-6` on rows 13–16); any exception inside Section C (see R5).

**R4 — ¶21 — explicit (inline condition).** Text: D3 begins `IF YES:`
- Gate: D2 (¶20), likely `diabetes_dx`, option `Yes [1]`.
- Skips: D3 (¶21), likely `diabetes_age`, when D2 is `No [2]`.
- Not said: D2 refused or don't know (the dictionary allows `-9`, S01:Variables row 18; no such option is printed); what D3 is recorded as when skipped (the dictionary has the note "Asked only if diabetes_dx = 1" and codes `-6; -9`, row 19 — both outside S02).

**R5 — ¶15–¶17 — not stated (wording only).** C3 ("age at your first live birth") and C4 ("any of your children") only make sense if C2 (live births) is at least 1, but nothing in S02 routes on C2: there is no instruction or prefix at C2–C4, and the dictionary allows `parity` = 0 (`0-15`, S01:Variables row 14). Skips: nothing, per S02. This is a belief from wording, not a rule the document states.

**R6 — ¶19 — implicit.** D1 begins `(Clinic)`: its value is "recorded from measured height and weight", not asked of the participant, so it exists only where a clinic measurement was taken (likely `bmi`; dictionary note "Measured at clinic visit", S01:Variables row 17).
- Not said: who records it, when, or what is entered if no measurement was taken (the dictionary has `-1` "Not measured", S01:Variables row 17 and S01:Codes row 5).

**As routed, who is asked:** everyone — A1, A2, B1, D2; B1 = Yes [1] — B2 and B4 (the Yes path is implied by order; R1 states only the No path, and B4 has no condition of its own); B1 = Yes and B2 = `Yes, I smoke now [1]` — B3 (R2); A2 = 2 — C1–C4, whatever the B1 answer (R3); D2 = Yes [1] — D3 (R4); D1 — where a clinic measurement exists (R6). A gate answered refused or don't know: not defined (Problems 2).

## 5. Other facts

- Printed range: only B3 prints one, `(1–60)` (¶10). No other question prints a range or limit; the dictionary has ranges for A1, B4, C1–C3, D1 and D3 (S01:Variables rows 7, 12–15, 17, 19) that S02 cannot confirm.
- Units: `years` follows the blank in A1 (¶4), B4 (¶11), C1 (¶14), C3 (¶16) and D3 (¶21). B3's unit is in its wording, "cigarettes … a day" (¶10). C2's blank (¶15) and D1 (¶19) print none (the dictionary says kg/m2 for `bmi`, S01:Variables row 17).
- Interviewer-recorded: A2 (¶5), `INTERVIEWER: RECORD SEX.` — recorded, not put to the participant (dictionary note "Recorded by interviewer", S01:Variables row 8).
- Clinic-measured: D1 (¶19) — BMI "recorded from measured height and weight"; the two measurements are not items in S02 (dictionary note "Measured at clinic visit", S01:Variables row 17).
- Codes printed: Male [1] / Female [2] (¶5); Yes [1] / No [2] on B1 (¶7), C4 (¶17), D2 (¶20); `Yes, I smoke now [1]` / `No, I have quit [2]` on B2 (¶9). No special code (refused, don't know, not applicable, not measured) is printed; `-1`, `-6`, `-7`, `-9` exist only in S01 (S01:Codes rows 2–5).
- Definitions in the wording: B1 threshold "at least 100 cigarettes in your entire life" (¶7); B2 "now" (¶9); B3 "On average … a day" (¶10); B4 "regularly" (¶11, not defined in S02); C2 "live births" (¶15); D2 "Has a doctor ever told you" — self-report of a doctor's diagnosis, lifetime (¶20); D3 age "when you were told" (¶21). B1, C4 and D2 use "ever"/"entire life"; B2 is current.
- Structure: every question is answered once per participant — no roster, repeating block or select-all item. S02 has no field for participant id, site, interview date or interviewer.
- Counts: sections A–D hold 2, 4, 4 and 3 questions (13 in all).

## 6. Problems

1. **Printed range differs from the dictionary.** B3 prints `(1–60)` (S02:¶10); `cigs_day` is `0-99` in S01:Variables row 11. Both bounds differ: S02 excludes 0 and stops at 60. S02 does not say whether its range is a hard limit or a prompt, so which one holds is not stated.
2. **No refused, don't-know, not-applicable or not-measured option in S02, so routing on such answers is undefined.** S02 prints only [1]/[2] options. The dictionary lists special codes for the same items: `age` `-9` (S01:Variables row 7 vs S02:¶4), `sex` `-7` (row 8 vs ¶5), `smk_ever` `-7; -9` (row 9 vs ¶7), `smk_status` `-6; -9` (row 10 vs ¶9), `bmi` `-1` (row 17 vs ¶19), `diabetes_dx` `-9` (row 18 vs ¶20), and `-6; -9` on every other question (rows 11–16 and 19). For each gate (R1–R4) the case "refused or don't know" is therefore undefined in S02, and S02 never says that skipped questions are recorded as `-6` (S01:Codes row 2: "Question not asked of this participant (skip pattern)").
3. **C3 and C4 are not routed on C2.** ¶15–¶17 (R5): no instruction handles zero live births, yet `parity` may be 0 (S01:Variables row 14). The follow-ups `age_first_birth` (row 15) and `breastfed_ever` (row 16) list `-6` but carry no note on when they are skipped, so no source states the rule.
4. **D1 mentions a measurement S02 does not include.** ¶19 says the BMI is "recorded from measured height and weight", but no height or weight item, clinic form, BMI formula or unit is in S02, and D1 prints no answer format or range. The dictionary's type `number`, range `12.0-70.0` and unit `kg/m2` (S01:Variables row 17) cannot be confirmed from S02.
5. **Dictionary notes vs S02 routing.** S02:¶13 puts C1–C4 behind "WOMEN ONLY" (¶14–¶17); S01:Variables rows 13–14 (`menarche_age`, `parity`) say "Women only" but rows 15–16 (`age_first_birth`, `breastfed_ever`) carry no note. Rows 10 (`smk_status`) and 12 (`smk_age_start`) carry no note on the B1 gate (S02:¶8), and the label "Current smoking status" does not say the variable exists only for people who answered Yes at B1. In agreement: row 11 "Current smokers only" with ¶10, and row 19 "Asked only if diabetes_dx = 1" with ¶21.
6. **Layout (Word file).** The extract loses indentation and boxes, so the original .docx's XML was read (in memory; nothing was written). Every body paragraph is a plain one-run paragraph in the Normal style except the five Heading 1/2 lines (¶1, ¶3, ¶6, ¶12, ¶18). There is no indentation, list numbering, border, shading, table, text box, form field, comment, tracked change, hidden text, header or footer, and the capitals are typed capitals with no font effect. Routing therefore depends on nothing the extract cannot show, and no PDF is needed. But scope rests on adjacency and wording alone: nothing marks ¶8 as belonging to B1 (it names no question) or B4 (¶11) as a follow-up of B3 or not; ¶13 reaches all of Section C through its wording ("SECTION C") and its position under the heading.
7. **No version, release or dataset named.** ¶1 says only "Baseline interview". The file's properties give no title or version (creator `python-docx`; created and modified 2013-12-23). The link to S01 ("release 2", S01:Variables row 1) is by content only.
8. **Dictionary variables without a question:** `participant_id` (S01:Variables row 5) and `site` (row 6) — S02 has no field for either.
9. **Wording differs from the dictionary label** (plain matches, but definitions may differ). B4 asks when "you started smoking regularly" (¶11) against "Age started smoking (years)" (S01:Variables row 12), and "regularly" is not defined in S02. B2's options `Yes, I smoke now [1]` / `No, I have quit [2]` (¶9) against `1=Current; 2=Former` (row 10): same codes, different words. D3 "How old were you when you were told?" (¶21) against "Age at diabetes diagnosis (years)" (row 19).
10. **¶2 against A2 and D1.** "read each question aloud" (¶2) makes no exception for A2 (¶5, recorded by the interviewer) or D1 (¶19, a measurement).
11. **Typos:** none found in the 21 paragraphs. The only non-ASCII characters are the em dash in the title (¶1, U+2014) and the en dash in `(1–60)` (¶10, U+2013); the apostrophe in "Women's health" (¶12) is ASCII.
