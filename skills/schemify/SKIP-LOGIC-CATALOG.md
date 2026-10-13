Domain memory for skip logic the sources never state outright: what hints that a rule exists, where studies write rules down, which rules epidemiological data usually carries, which sentinel conventions to expect, and what JSON Schema can and cannot express. Read this when a topic has gate-shaped variables or N/A labels the sources do not explain, during discovery's skip-logic scan, and for the skip-logic audit. Nothing in this file is provenance: every family below is a hypothesis to look for in the sources or to put to a person. A rule reaches a schema only on SKIP-LOGIC.md's terms.

Table of contents

- [Detection signals](#detection-signals)
- [Where routing is documented](#where-routing-is-documented)
- [Routing families](#routing-families)
- [Sentinel families](#sentinel-families)
- [Expressibility](#expressibility)
- [Asking about rules](#asking-about-rules)
- [When inferRules is no](#when-inferrules-is-no)
- [Cross-category and cross-table cases](#cross-category-and-cross-table-cases)

## Detection signals

| grade | signal | reading | next |
|---|---|---|---|
| strong | NA-type label on a code: "not applicable", "legitimate/valid skip", "inapplicable", "not asked", "INAP", "blank — skipped", "N/A (nonsmoker)" | a rule exists; a parenthetical names the universe | find the gate; the label is `implied` evidence to cite |
| strong | routing text in label/notes: "If yes", "skip to", "go to", "→", "universe:", "asked of", "only if", "among", "for those who", "if Q12=1" | documented routing | encode; map question numbers to variables |
| strong | a routing column: REDCap `Branching Logic (Show field only if...)`, XLSForm `relevant`, DDI `<universe>`/`<forward>`, NHANES "Skip to Item", a "Universe" column | machine-readable or near | parse it; each expression is a documented rule or a `not-expressible` record |
| strong | the questionnaire/CRF is among the inputs | arrows and boxes are documented routing | read the instrument beside the slice |
| strong | software special missings (SAS `.A`–`.Z`, Stata `.a`–`.z`, SPSS user-missing) with distinct labels | a skip code distinct from item-missing | ask the delivered literal |
| medium | gate/detail name pairs: `ever_`, `has_`, `any_`, `cur_`, `_yn`, `_flag` beside `age_`, `agefirst`, `num_`, `_per_day`, `_years`, `_dur`, `_dt`, `_specify`, `_oth`, `_txt` | a family below | `implied` if an N/A label names this gate's universe or the questionnaire's layout routes it; otherwise `inferred` — ask first |
| medium | sex-specific blocks (menarche, pregnancies, PSA); age-limited items (screening, retirement) | a demographic gate | ask *which* variable gates |
| medium | roster/loop slots `child1_…childN_`, `med1_…`; a count beside them | count-gated slots | one pair per slot |
| medium | "other, specify" pairs; checkbox groups with a "none of the above" member | structural pairs | see families |
| medium | wave/visit suffixes `_w2`/`_v3` with a participation flag; proxy/mode variables | block gates | compound consequences |
| medium | a codebook frequency column where the NA count equals the gate's "No" count | the gate, exposed | quote both counts as evidence |
| weak | a yes/no immediately followed by quantities on the same topic | ordering suggests a gate | `inferred` — ask first |
| weak | a derived variable (pack-years, BMI class, MET-min) | inputs exist; routing may sit on them | `x-derivation`; not routing itself |
| negative | one-analyte-per-row lab extracts, assay panels, genotype matrices, crosswalks, weights/design tables | little questionnaire routing; what exists is result/flag pairing | ask only about result-vs-flag |
| negative | a harmonized analytic file where NA was recoded to missing | routing existed upstream and is invisible | ask whether structural NA is recoverable; else document, not enforce |

## Where routing is documented

Ask for the artifact, not the rule. `mr` = machine-readable; `conf` = confidence in this row's description (verified 2026-09 where high).

| source type | ask for | holds | mr | conf |
|---|---|---|---|---|
| any survey | the instrument (PDF/Word) with arrows/"GO TO"/boxed instructions | what was asked, of whom; not the delivered coding | no | high |
| any survey | interviewer manual / question-by-question specs | universes in prose, probes | no | high |
| CAPI/CATI | Blaise source (RULES, IF…THEN routing); CSPro dictionary + logic skip statements | executable routing | bespoke | med |
| ODK/SurveyCTO | XLSForm `survey` sheet: `relevant` (routing), `calculation` (derived), `constraint` | XPath expressions | yes | high |
| Qualtrics | QSF export (survey flow, display/skip logic) | routing, painful to parse | yes | high |
| REDCap | data dictionary CSV: `Branching Logic (Show field only if...)`; `Field Type = calc` (derived → not-expressible); checkboxes export as `var___k` 0/1 | routing per field | yes | high |
| public codebooks | NHANES variable pages ("Skip to Item"; `.` for skipped in XPT); NHIS (7 refused/8 not ascertained/9 DK; universe lines); BRFSS (BLANK = not asked); HRS core (blank INAP; 8 DK/NA, 9 RF); DHS Recode manual (BLANK = not applicable) | universes, skip targets, sentinel policy | HTML/PDF | high |
| public cohorts | UK Biobank Showcase field pages + data-codings (e.g. -10/-3/-1); touchscreen flow documents | codings certain; branching docs verify per field | HTML | med |
| PhenX | protocol text + REDCap-format dictionaries | skip logic in protocol prose | partly | med |
| DDI-Codebook 2.5 | `<var><universe>`, `<qstn><forward>/<backward>` | universe prose; skip targets | XML | high |
| DDI-Lifecycle 3.x | control constructs (IfThenElse) | structured routing | XML | med |
| cleaning code | SAS/Stata/R: `if ever_smk ne 1 then cigs_day = .A;` | the delivered representation — the most reliable record of what landed in the cell | bespoke | high |
| derived docs | derived-variable specifications | derivations (→ `x-derivation`, not-expressible) | no | high |
| SEER | Program Coding and Staging Manual; laterality-by-site table; SSDI manual; Summary Stage manual | site-specific applicability, paired-site list | PDF | high |
| NAACCR | Volume II dictionary (required-status by agency); Volume IV Standard Data Edits; EDITS metafile `.smf` | conditionality lives in the edits, not a dictionary column | metafile | med |
| CoC STORE | Standards for Oncology Registry Entry | conditional items | PDF | low |
| OMOP | CDM spec + THEMIS conventions | few hard rules; `value_as_number` and `value_as_concept_id` may both be populated — never encode exclusivity; NULLs not sentinels → sentinel policy is an interview question | HTML | high |
| PCORnet | CDM spec, per-field "populated for" notes | `DISCHARGE_DISPOSITION` for IP and IS encounters (EI unconfirmed); `LAB_RESULT_CM` `RESULT_NUM`/`RESULT_QUAL`/`RESULT_MODIFIER` | PDF | med |
| i2b2 | `observation_fact` `valtype_cd` vs `nval_num`/`tval_char` | type-gated value columns | tables | low |
| FHIR | profile invariants (FHIRPath), e.g. obs-6 `dataAbsentReason` only when `value[x]` absent | in-row conditionals | JSON/XML | high |
| HL7 v2 | conformance-profile usage codes R/RE/C/X; C carries a predicate | conditional fields | partly | med |
| CMS/ResDAC | per-file documentation (MedPAR, Inpatient, Outpatient, Carrier, MBSF) | inpatient-only fields (DRG, admission/discharge, discharge status) | HTML/PDF | med |
| labs | assay SOP; per-analyte LOD/LOQ; comment-code variable (NHANES `*LC` 0/1, value = LOD/√2) | flag/value pairing, specimen-type gating | tables | high |
| biospecimens | inventory/LIMS export spec | collected → volume/aliquots/processing time | tables | med |
| consortium | harmonization documents; Maelstrom-style catalogue; data-use agreements | which studies asked what; suppressed variables | HTML/PDF | med |

## Routing families

Forms: `pair` (skip half pins NA, applicability half forbids NA) · `pin` (substantive pin, one direction, no twin) · `narrow` (then-side enum or range keeping item-missing codes) · `at-least-one` · `implication` (categorical → categorical const) · `compound` (many dependents, one `then.properties`). Evidence = what such a rule usually carries when a source speaks to it; a rule no source hints at is `inferred`, whatever its family.

**Behaviours**

| family | gate | dependents | form | evidence | pitfalls |
|---|---|---|---|---|---|
| tobacco | `ever=No` (or the 100-cigarettes item) | status, cigs/day, age started, age quit, years smoked, brand | pair | documented/implied | each product (cigarette, cigar, e-cig, smokeless) has its own gate; pack-years derived → not-expressible + `x-derivation` |
| tobacco status | `status=Current` → age quit, years since quit NA | | pair | implied | `Former` → age quit applicable, DK still legal |
| derived zero | `ever=No` → cigs/day `=0` | | pin | inferred | only if the source delivers 0, not NA; **no reverse**: a former smoker reports 0 today, so 0 implication nothing; no twin |
| implication | `status=Current` → `ever=Yes` | | implication | implied | only when both are asked, not one derived from the other |
| alcohol | `ever=No` | status, drinks/week, frequency, binge, age started, age quit | pair | documented/implied | nondrinker may live *inside* the dependent as a context sentinel (777 Nondrinker) — the gate is then a code, not a column; lifetime abstainer ≠ former drinker for `age_quit` |
| physical activity | `any=No`; per-intensity `days=0` | type, minutes, frequency per intensity | pair | documented | each intensity gates its own minutes; MET-min → not-expressible |

**Sex-gated and reproductive**

| family | gate | dependents | form | evidence | pitfalls |
|---|---|---|---|---|---|
| female block | *which?* `sex`, `gender`, `sex_at_birth`, or a "women's questionnaire administered" flag | menarche, pregnancy, parity, menopause, OC, HRT, hysterectomy | compound pair | documented | the instrument routed on one variable — usually interviewer-recorded sex or a screener; a later gender-identity variable is never the gate; intersex/other/refused codes need their own reading |
| pregnancy → births | `ever_pregnant=No` | n_pregnancies, age first pregnancy | pair | documented/implied | pregnancies ≠ births |
| parity | `parity=0` | age at first birth, breastfeeding, n live births | pair | documented/implied | miscarriage-only histories: pregnant yes, parity 0 — gate births on parity |
| menopause | `status=Pre` → age at menopause NA; `Post` → applicable | | pair | implied | hysterectomy/oophorectomy → surgical menopause or "unknown — hysterectomy": `hysterectomy=Yes` → status narrowed; ask whether status is derived |
| oral contraceptives | `oc_ever=No` | years, age started, current use | pair | implied | |
| currently pregnant | `pregnant=Yes` → weight/waist NA or flagged | | pair/narrow | documented | some studies drop the row instead — then no rule |
| male block | same gate question | PSA ever, prostate items | pair | documented | |

**Age-gated**: `age < t` → item NA (screening at ≥45/50, retirement ≥50, child items <18). Range trigger; exclude positive sentinels in the trigger. Threshold may have moved across years; the age must be the row's own age at that wave. Evidence documented.

**Clinical**

| family | gate | dependents | form | evidence | pitfalls |
|---|---|---|---|---|---|
| diagnosis → details | `dx_X=No` | age/year at dx, treatment, stage, site, condition-specific meds | pair | documented/implied | one gate per condition; "any cancer=Yes" → ≥1 site flag = at-least-one |
| laterality | `site ∈ paired list` → laterality ∈ {1,2,3,4,5,9}; else `=0` | | narrow/pin | documented (SEER) | paired-site list is an external source — approve before use |
| behavior → stage | `behavior=3 malignant` → stage applicable; `2 in situ`/benign → nodal stage NA or pinned | | narrow | documented | in situ handling differs between Summary Stage and AJCC — confirm codes |
| vital status | `Dead` → date, cause applicable; `Alive` → NA | | pair | documented | lost-to-follow-up is a third level; "cause pending" is item-missing not NA; dates pin to the string/wide sentinel |
| family history | `fh_any=No` → relative flags NA; `fh_rel=No` → their age at dx NA; `n_affected<k` → slot k NA | | pair per slot | documented/implied | "adopted/unknown family" is a level, not NA |
| medication | `use=No` → name, dose, duration, start age; `n_meds<k` → slot k | | pair | documented/implied | names free text → string sentinel |
| screening | `ever=No` → age at last, frequency, result; stacked with sex and age gates | | pair | documented | result may be DK in-universe — never require a substantive result |

**Social**

| family | gate | dependents | form | evidence | pitfalls |
|---|---|---|---|---|---|
| employment | `employed=No` → occupation, industry, hours; `Retired` → longest job applicable | | pair/narrow | documented/implied | universes differ per item — occupation may be asked of ever-worked; occupation codes are strings with leading zeros |
| marital | `Never married` → years married NA | | pair | implied | widowed/divorced: duration of the ended marriage may be asked |
| migration | `born in study country` → age at immigration NA | | pair (complement trigger) | implied | trigger needs a coded country or flag; free text → not-expressible |
| education | `level` below degree-bearing → degree type NA | | pair/narrow | implied | |
| household roster | `n_children<k` → `child_k_*` NA; `≥k` → applicable | | pair per slot | documented/implied | slot shape from `$defs`; one pair per slot; slots capped while the count runs higher |

**Study logistics and instrument structure**

| family | gate | consequence | form | evidence | pitfalls |
|---|---|---|---|---|---|
| consent | `consent_X=No` → whole block NA | | compound pair | documented | many columns, one `then.properties` |
| wave participation | `participated_w2=No` → every `_w2` NA | | compound pair | documented | wide files only; in a long file the row's existence is the gate → nothing to encode |
| proxy/mode | `proxy=Yes` → self-report-only items NA; `No` → proxy-only items NA | | pair | documented | mode may live in paradata → cross-table |
| other, specify | `code≠Other` → text = string sentinel; `=Other` → text ≠ sentinel | | pair (complement trigger) | documented/implied | ask what the empty cell is; "meaningful text" is not assertable |
| checkbox + none | `none=1` → members `=0`; `member=1` → `none=0`; group asked → at-least-one | | compound/implication | implied | REDCap exports unchecked as 0 with no NA — group-level routing is invisible; ask |
| implication | `hysterectomy=Yes` → `menstruating=No`; `any=Yes` → ≥1 member | | implication/at-least-one | implied/inferred | encode only the direction a source or a person supports |

**Registry, claims, EHR, laboratory**

| family | gate | consequence | form | evidence | pitfalls |
|---|---|---|---|---|---|
| claims | `claim_type=Inpatient` → admission/discharge dates, discharge status, DRG applicable; outpatient → NA | | pair | documented | files usually pre-split by type — the gate is the table, nothing to encode |
| EHR encounter | `enc_type ∈ {IP, IS}` → discharge disposition applicable; ambulatory/ED → NA | | pair | documented (PCORnet, med) | EI unconfirmed — ask |
| result type | `type=Numeric` → numeric ≠ NA, text = NA; `Text` → reverse | | pair | implied | OMOP allows both populated — never encode exclusivity there |
| LOD | `below_lod=1` → modifier `<` (pin); value ≤ LOD | | pin / not-expressible | documented | LOD per batch → not-expressible; constant per field → narrow |
| specimen | `collected=No` → volume, processing time, aliquots, storage NA | | pair | documented/implied | |
| assay | `run=No` → result, batch, run date NA; `specimen_type` → analyte panel narrowed | | pair/narrow | implied (protocol) | quality flags narrow result-quality codes — protocol says |

## Sentinel families

The family is a clue; the meaning is a question. Never transcribe a study's codes from this table — read them from the source.

| family | typical codes | seen in (conf) | trap |
|---|---|---|---|
| width-scaled 7/8/9 | 7/77/777, 8/88/888, 9/99/999 | NHANES 7 refused · 9 DK · `.` skipped (high); NHIS 7 refused · 8 not ascertained · 9 DK (high); BRFSS 7 DK · 9 refused · BLANK not asked (high) | 7 and 9 swap meaning between studies; positive codes inside a numeric range need the `not: enum` guard |
| negatives | -1/-6/-7/-8/-9; UK Biobank -1 DK, -3 prefer not, -10 less than one (high); RAND HRS special missings (low) | | -10 is a *substantive* "less than one", not missing |
| DHS-style | 96 other, 97 inconsistent, 98 DK, 99 missing, width-scaled; BLANK = not applicable (high) | | 96 is a real category; BLANK conflates skip with country omission |
| HRS core | 8 DK/NA, 9 RF, blank INAP (high) | | INAP is blank, so the delivered literal is the question |
| registry | 888 not applicable, 999 unknown (med) | | 888 inside 0–2000 ranges needs the guard |
| zero overload | 0 = "not applicable" / "none" / "No" | everywhere | the structural-zero trap: 0 is also a legitimate count; the schema can only `pin`, and the `$comment` must say 0 doubles as NA |
| strings | "NA", "N/A", ".", "", "-", "SKIP" | CSV exports | declare the delivered literal as a string sentinel; a blank cell is a value that must be named |
| software specials | SAS `.`, `.A`–`.Z`; Stata `.a`–`.z`; SPSS user-missing | dictionaries written from analysis files | on CSV export they become blank or a literal — which? |

Three distinctions every rule question makes explicit:

- **Structural NA vs item missing.** A rule exists only for structural NA; refused and don't know are legal everywhere, in and out of universe. One merged "missing" code has lost the distinction — say so, encode no skip rule, and record the decision.
- **What lands in the cell** for a skipped person: a code, a blank, a zero, or last wave's value carried forward — panel studies preload prior answers, and an NA pin would be wrong.
- **Delivered ≠ questionnaire.** The instrument skipped; SAS wrote `.`; the CSV wrote blank; a recode wrote -666. A rule question always establishes the *delivered* representation, because that is what the validator reads; a blank-delivered skip needs a `convention` decision (a code, or `null` — SCHEMA-STYLE.md) before any pair can be written.

## Expressibility

| rule family | in-row if/then? | canonical form |
|---|---|---|
| gate const/enum → dependent NA; gate → NA forbidden | yes | skip pair |
| gate → dependent = 0 (derived zero) | yes, one direction | substantive pin, `<Domain> routing` comment, no twin |
| gate → dependent ∈ subset | yes | narrowing `enum` keeping item-missing codes |
| categorical gate → different numeric range (sex-specific bounds) | yes | narrowing: then-side `anyOf` numeric branch + sentinel branches |
| gate → at least one of several flags | yes | at-least-one: `then.anyOf` |
| categorical → categorical (current → ever=Yes) | yes | implication |
| numeric range trigger (age ≥ 50) | yes | range trigger with sentinel exclusion |
| several conditions that must all hold (women aged 40+) | yes | AND trigger: all in one `if.properties`, all `required` |
| "everyone but code v" (other → specify) | yes | complement trigger `not: {const: v}` |
| count → slot k | yes | one pair per slot |
| sentinel as trigger (X not asked → Y not asked) | yes | skip pair with the structural code as the test |
| checkbox mutual exclusion | yes | one `then.properties` with every target |
| other → specify text non-empty | partly | forbid the string sentinel; cannot assert content |
| arithmetic (pack-years, sums, BMI) | no | `not-expressible` + root `$comment` + `x-derivation` |
| date/age ordering (quit ≥ start; dx ≤ death) | no | `not-expressible` |
| range depending on another numeric field | no | `not-expressible` |
| value ≤ LOD when LOD varies per batch | no | `not-expressible` (constant LOD → narrowing) |
| cross-row (uniqueness, one baseline per id, wave order); aggregates; age consistency across waves | no | `not-expressible` (`uniqueItems` catches whole-row duplicates only) |
| gate in another table; free-text gate | no | `not-expressible` |

## Asking about rules

Rule questions follow QUESTIONS.md: batched, grouped by gate, every question with a recommended answer and the evidence quoted. Two things every rule question settles — who was asked, and what sits in the cell for everyone else. Examples of the cards' wording:

> **`smk_ever` gates four smoking variables.** The questionnaire (p.6, Q14) says "If NO, go to Q20", so never smokers were not asked `smk_status`, `cigs_day`, `smk_age_start`, or `smk_years`. The dictionary lists 777 = "N/A (never smoker)" for all four. *Recommended:* enforce 777 in all four for never smokers, and forbid 777 for everyone else (they may still carry refused or don't-know codes).

> **`cigs_day` has both "0 = never smoked" and "777 = not asked".** *Recommended:* treat 777 as the code for never smokers, and 0 as a real "none today" for former smokers — a 0 says nothing about `smk_ever`. Your QuaC findings (A02) show 1,204 records failing the rule that way round, all with 777, so the data agrees.

> **I believe — but nothing documents — that `age_first_birth` was asked only when `parity` ≥ 1, so women with no live births hold -6 ("not applicable") there.** Two more variables follow the same pattern (list). *Recommended:* include these rules, each marked for review by the data steward. — the `consent` question (SKIP-LOGIC.md), which names the code skipped cells hold.

Counts come only from QuaC findings the user sent (DATA-CHECK.md) — never from reading data.

## When inferRules is no

`preferences.inferRules: no` means the person wants nothing beyond their documents. Use this catalog only to *recognize* what the sources imply — an N/A label naming its universe, a title "among current smokers", a universe column, a layout cue in the questionnaire — and to name which variable such a hint points to; those rules carry evidence `implied` and cite the source. Never put forward a rule no source hints at: suspected rules are recorded `declined`, citing the decision that set the preference, and wait for the steward's review.

## Cross-category and cross-table cases

Rules live in the mother file, so category order only decides *when* a pair is written, never *where*; the rule record (`status: waiting`) carries the wait.

- **Gate drafted first, dependents later** — `sex` confirmed in demographics; the reproductive category arrives three sittings on. The rule record waits on the dependents; the pair is written when they are drafted; demographics is not reopened; fixtures extend for both halves.
- **Dependent drafted first, gate later** — `age_first_birth` sits in demographics with "-666 = N/A"; `parity` is in reproductive history, not yet drafted. Keep the sentinel branch, write no conditional, record the rule `waiting` on `parity`. When `parity` is drafted, a documented or implied rule is encoded; an inferred one goes through consent (SKIP-LOGIC.md) first.
- **Gate in another table** — sex in `participant`, the women's block in `visit`; proxy status in a paradata table. Each table is one flat grain, so a rule never crosses: `not-expressible`, README "Documented but not enforced". If a person chooses to carry the gate into the dependent table as a column, it becomes an `added` variable on their instruction (a decision) and the rule becomes in-row — offer it, never do it unasked.
- **Bidirectional facts are two rules** — `status=Current → ever=Yes` and `ever=No → status=Never` are separate rules, separately evidenced; encode only the directions a source or a person supports; never manufacture a twin for a substantive pin.
- **Stacked gates** (`sex` → `mammogram_ever` → `mammogram_age_last`): one pair per gate on the deepest field; rows with the outer gate off carry NA in the inner gate, so the inner pair never fires on them.
- **Wide vs long** — wave participation gates wave variables in a wide file; in a long file the row's absence is the routing and there is nothing to encode — say so in the README's grain paragraph.
