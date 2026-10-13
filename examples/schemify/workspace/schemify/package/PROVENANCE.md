# Provenance — Ashgrove Community Health Survey (ACH)

Every title, code, special code, bound, and rule in these schemas traces to a **source** (a document, or a web page a person approved) or a **decision** (an answer from the study's people, or a choice the agent made). Each property's and rule's `x-provenance` names which: `S01:<location>` or `D014`. ⚑ marks an agent decision no person has confirmed yet.

## Sources

| Id | Title | Kind | What it holds | Status |
|---|---|---|---|---|
| S01 | Ashgrove data dictionary (release 2) | document | Excel data dictionary for the Ashgrove Community Health Survey (synthetic), baseline, release 2: one record per participant, 15 variables on the Variables sheet and 4 special codes on the Codes sheet | active |
| S02 | Ashgrove baseline questionnaire | document | Interviewer-administered baseline questionnaire (Word, 21 paragraphs): sections A About you, B Smoking, C Women's health, D Health; 13 numbered questions; routing instructions in capitals at ¶8, ¶10, ¶13 and ¶21 | active |

## Decisions

| Id | Question | Answer | Decided by | Status |
|---|---|---|---|---|
| D009 | Is the data one table with one row per participant? | Yes — one table named baseline, one row per participant | author | answered |
| D010 | Which of your special codes mean "skipped by design"? | Only -6 (Not applicable) means skipped by design | author | answered |
| D011 | In the delivered data, can a cell be empty? | No — every cell holds an answer or a special code | author | answered |
| D012 | Are these the right topics for the dictionary? | Use these four topics: About you, Smoking, Women's health, Health | author | answered |
| D013 | How should we split the work into sittings? | One session: all four topics, in questionnaire order | author | answered |
| D014 | How exactly should participant IDs be written? | ^ACH[0-9]{4}$ | agent | superseded |
| D016 | What range of cigarettes per day should count as plausible? | 1 to 60, as the questionnaire prints | author | answered |
| D017 | When someone refused (-7) or did not know (-9) whether they have smoked 100 cigarettes, or whether they smoke now, what do the smoking questions after it hold? | Skipped like "No": they hold -6 (Not applicable) | author | answered |
| D018 | Do the two smoking skip rules still match what the delivered data holds? | Yes — both match the delivered data | author | answered |
| D020 | Were women with no live births skipped on the first-birth age and breastfeeding questions? | Yes — I know this is how it was done | author | answered |
| D021 | When sex was refused (-7), what do the four women's-health questions hold? | Skipped like men: they hold -6 (Not applicable) | author | answered |
| D022 | Does the women-only rule still match what the delivered data holds? | Yes — it matches the delivered data | author | answered |
| D024 | When "ever told you have diabetes" was answered don't know (-9), what does the age at diagnosis hold? | Not asked: it holds -6 (Not applicable) | author | answered |
| D025 | Does the diabetes follow-up rule still match what the delivered data holds? | Yes — it matches the delivered data | author | answered |
| D027 | Were ages above 85 changed in the delivered data? | Ages above 85 were top-coded to 85 in the 2024 release; nothing else changed. | author | answered |
| D028 | Were any ages at which people started smoking recoded in the 2024 cleaning? | Ages below 10 were recoded to -9 (don't know) as implausible, so real values run 10 to 80. | author | answered |
| D029 | Does a don't-know answer to "Do you smoke cigarettes now?" work like a refused or don't-know answer to the first smoking question? | Yes — a don't-know answer there also means the cigarette count was not asked: cigs_day is -6 | author | answered |
| D030 | How precisely is body mass index delivered? | BMI was rounded to one decimal place in the 2024 release; nothing else changed. | author | answered |
| D031 | Your 2024 file has only 5 of the 15 variables. Is it the whole release or a partial extract? | A partial extract on purpose: the full release has all 15 variables (known and accepted) | author | answered |
| D032 | Every participant ID in your 2024 file fails the pattern "ACH followed by 4 digits". How are the IDs written in the delivered data? | The IDs are written differently from the dictionary: change the schema (describe the format in the note) | author | answered |
| D033 | 5 of the 40 records in your 2024 file have an age the schema rejects. What are they? | Errors or stray codes in the data: the data needs fixing | author | answered |
| D034 | Your 2024 file has a column named "canary" that is not in the dictionary. What is it? | A helper or test column that is not part of the study data (known and accepted) | author | answered |
