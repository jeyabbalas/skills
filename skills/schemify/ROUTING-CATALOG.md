Domain memory for the routing a dictionary never states: what hints that skip logic exists, where studies write it down, which rules an epidemiologist expects, and how to put each one to the steward. Read this when a slice carries gate-shaped variables or NA-type labels and the source states no routing, at intake's scan, and for the skip audit. Nothing in this file is provenance: every family below is a hypothesis to look for in the source or put to the steward, and a rule reaches a schema only when the source states or implies it, an approved external source states it, or the steward confirms it. Evidence and the workflow: ROUTING.md; encoding: SKIP-PATTERNS.md; sentinels: SCHEMA-PATTERNS.md; question craft: ELICIT.md.

Table of contents

- [Detection signals](#detection-signals)
- [Where routing is documented](#where-routing-is-documented)
- [Routing families](#routing-families)
- [Sentinel families](#sentinel-families)
- [Expressibility](#expressibility)
- [Proposing to the steward](#proposing-to-the-steward)
- [Under a faithful policy](#under-a-faithful-policy)
- [Cross-category and cross-table cases](#cross-category-and-cross-table-cases)

## Detection signals

| grade | signal | reading | next |
|---|---|---|---|
| strong | NA-type label on a code: "not applicable", "legitimate/valid skip", "inapplicable", "not asked", "INAP", "blank — skipped", "N/A (nonsmoker)" | a rule exists; a parenthetical names the universe | find the gate; the label is `implied` evidence to quote |
| strong | routing text in label/notes: "If yes", "skip to", "go to", "→", "universe:", "asked of", "only if", "among", "for those who", "if Q12=1" | quoted routing | encode; map question numbers to variables |
| strong | a routing column: REDCap `Branching Logic (Show field only if...)`, XLSForm `relevant`, DDI `<universe>`/`<forward>`, NHANES "Skip to Item", a "Universe" column | machine-readable or near | parse it; each expression is a quoted rule or a `not-enforceable` line |
| strong | the questionnaire/CRF is among the inputs | arrows and boxes are quoted routing | read the instrument beside the slice |
| strong | software special missings (SAS `.A`–`.Z`, Stata `.a`–`.z`, SPSS user-missing) with distinct labels | a skip code distinct from item-missing | ask the delivered literal |
| medium | gate/detail name pairs: `ever_`, `has_`, `any_`, `cur_`, `_yn`, `_flag` beside `age_`, `agefirst`, `num_`, `_per_day`, `_years`, `_dur`, `_dt`, `_specify`, `_oth`, `_txt` | a family below | propose; `implied` if an NA label agrees, else `inferred` |
| medium | sex-specific blocks (menarche, pregnancies, PSA); age-limited items (screening, retirement) | a demographic gate | ask *which* variable gates |
| medium | roster/loop slots `child1_…childN_`, `med1_…`; a count beside them | count-gated slots | one pair per slot |
| medium | "other, specify" pairs; checkbox groups with a "none of the above" member | structural pairs | see families |
| medium | wave/visit suffixes `_w2`/`_v3` with a participation flag; proxy/mode variables | block gates | compound consequences |
| medium | a codebook frequency column where the NA count equals the gate's "No" count | the gate, exposed | quote both counts as evidence |
| weak | a yes/no immediately followed by quantities on the same topic | ordering suggests a gate | `inferred` only |
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
| REDCap | data dictionary CSV: `Branching Logic (Show field only if...)`; `Field Type = calc` (derived → not-enforceable); checkboxes export as `var___k` 0/1 | routing per field | yes | high |
| public codebooks | NHANES variable pages ("Skip to Item"; `.` for skipped in XPT); NHIS (7 refused/8 not ascertained/9 DK; universe lines); BRFSS (BLANK = not asked); HRS core (blank INAP; 8 DK/NA, 9 RF); DHS Recode manual (BLANK = not applicable) | universes, skip targets, sentinel policy | HTML/PDF | high |
| public cohorts | UK Biobank Showcase field pages + data-codings (e.g. -10/-3/-1); touchscreen flow documents | codings certain; branching docs verify per field | HTML | med |
| PhenX | protocol text + REDCap-format dictionaries | skip logic in protocol prose | partly | med |
| DDI-Codebook 2.5 | `<var><universe>`, `<qstn><forward>/<backward>` | universe prose; skip targets | XML | high |
| DDI-Lifecycle 3.x | control constructs (IfThenElse) | structured routing | XML | med |
| cleaning code | SAS/Stata/R: `if ever_smk ne 1 then cigs_day = .A;` | the delivered representation — the most reliable record of what landed in the cell | bespoke | high |
| derived docs | derived-variable specifications | derivations (→ `x-derivation`, not-enforceable) | no | high |
| SEER | Program Coding and Staging Manual; laterality-by-site table; SSDI manual; Summary Stage manual | site-specific applicability, paired-site list | PDF | high |
| NAACCR | Volume II dictionary (required-status by agency); Volume IV Standard Data Edits; EDITS metafile `.smf` | conditionality lives in the edits, not a dictionary column | metafile | med |
| CoC STORE | Standards for Oncology Registry Entry | conditional items | PDF | low |
| OMOP | CDM spec + THEMIS conventions | few hard rules; `value_as_number` and `value_as_concept_id` may both be populated — never propose exclusivity; NULLs not sentinels → sentinel policy is an interview question | HTML | high |
| PCORnet | CDM spec, per-field "populated for" notes | `DISCHARGE_DISPOSITION` for IP and IS encounters (EI unconfirmed); `LAB_RESULT_CM` `RESULT_NUM`/`RESULT_QUAL`/`RESULT_MODIFIER` | PDF | med |
| i2b2 | `observation_fact` `valtype_cd` vs `nval_num`/`tval_char` | type-gated value columns | tables | low |
| FHIR | profile invariants (FHIRPath), e.g. obs-6 `dataAbsentReason` only when `value[x]` absent | in-row conditionals | JSON/XML | high |
| HL7 v2 | conformance-profile usage codes R/RE/C/X; C carries a predicate | conditional fields | partly | med |
| CMS/ResDAC | per-file documentation (MedPAR, Inpatient, Outpatient, Carrier, MBSF) | inpatient-only fields (DRG, admission/discharge, discharge status) | HTML/PDF | med |
| labs | assay SOP; per-analyte LOD/LOQ; comment-code variable (NHANES `*LC` 0/1, value = LOD/√2) | flag/value pairing, specimen-type gating | tables | high |
| biospecimens | inventory/LIMS export spec | collected → volume/aliquots/processing time | tables | med |
| consortium | harmonization documents; Maelstrom-style catalogue; data-use agreements | which studies asked what; suppressed variables | HTML/PDF | med |

## Routing families

Forms: `pair` (skip half pins NA, applicability half forbids NA) · `pin0` (substantive pin, one direction, no twin) · `narrow` (then-side enum or range keeping item-missing codes) · `any-of` · `implies` (categorical → categorical const) · `compound` (many dependents, one `then.properties`). Evidence = where it usually comes from.

**Behaviours**

| family | gate | dependents | form | evidence | pitfalls |
|---|---|---|---|---|---|
| tobacco | `ever=No` (or the 100-cigarettes item) | status, cigs/day, age started, age quit, years smoked, brand | pair | quoted/implied | each product (cigarette, cigar, e-cig, smokeless) has its own gate; pack-years derived → not-enforceable + `x-derivation` |
| tobacco status | `status=Current` → age quit, years since quit NA | | pair | implied | `Former` → age quit applicable, DK still legal |
| derived zero | `ever=No` → cigs/day `=0` | | pin0 | inferred | only if the source delivers 0, not NA; **no reverse**: a former smoker reports 0 today, so 0 implies nothing; no twin |
| implication | `status=Current` → `ever=Yes` | | implies | implied | only when both are asked, not one derived from the other |
| alcohol | `ever=No` | status, drinks/week, frequency, binge, age started, age quit | pair | quoted/implied | nondrinker may live *inside* the dependent as a context sentinel (777 Nondrinker) — the gate is then a code, not a column; lifetime abstainer ≠ former drinker for `age_quit` |
| physical activity | `any=No`; per-intensity `days=0` | type, minutes, frequency per intensity | pair | quoted | each intensity gates its own minutes; MET-min → not-enforceable |

**Sex-gated and reproductive**

| family | gate | dependents | form | evidence | pitfalls |
|---|---|---|---|---|---|
| female block | *which?* `sex`, `gender`, `sex_at_birth`, or a "women's questionnaire administered" flag | menarche, pregnancy, parity, menopause, OC, HRT, hysterectomy | compound pair | quoted | the instrument routed on one variable — usually interviewer-recorded sex or a screener; a later gender-identity variable is never the gate; intersex/other/refused codes need their own reading |
| pregnancy → births | `ever_pregnant=No` | n_pregnancies, age first pregnancy | pair | quoted/implied | pregnancies ≠ births |
| parity | `parity=0` | age at first birth, breastfeeding, n live births | pair | quoted/implied | miscarriage-only histories: pregnant yes, parity 0 — gate births on parity |
| menopause | `status=Pre` → age at menopause NA; `Post` → applicable | | pair | implied | hysterectomy/oophorectomy → surgical menopause or "unknown — hysterectomy": `hysterectomy=Yes` → status narrowed; ask whether status is derived |
| oral contraceptives | `oc_ever=No` | years, age started, current use | pair | implied | |
| currently pregnant | `pregnant=Yes` → weight/waist NA or flagged | | pair/narrow | quoted | some studies drop the row instead — then no rule |
| male block | same gate question | PSA ever, prostate items | pair | quoted | |

**Age-gated**: `age < t` → item NA (screening at ≥45/50, retirement ≥50, child items <18). Range trigger; exclude positive sentinels in the trigger. Threshold may have moved across years; the age must be the row's own age at that wave. Evidence quoted.

**Clinical**

| family | gate | dependents | form | evidence | pitfalls |
|---|---|---|---|---|---|
| diagnosis → details | `dx_X=No` | age/year at dx, treatment, stage, site, condition-specific meds | pair | quoted/implied | one gate per condition; "any cancer=Yes" → ≥1 site flag = any-of |
| laterality | `site ∈ paired list` → laterality ∈ {1,2,3,4,5,9}; else `=0` | | narrow/pin | quoted (SEER) | paired-site list is an external source — approve before use |
| behavior → stage | `behavior=3 malignant` → stage applicable; `2 in situ`/benign → nodal stage NA or pinned | | narrow | quoted | in situ handling differs between Summary Stage and AJCC — confirm codes |
| vital status | `Dead` → date, cause applicable; `Alive` → NA | | pair | quoted | lost-to-follow-up is a third level; "cause pending" is item-missing not NA; dates pin to the string/wide sentinel |
| family history | `fh_any=No` → relative flags NA; `fh_rel=No` → their age at dx NA; `n_affected<k` → slot k NA | | pair per slot | quoted/implied | "adopted/unknown family" is a level, not NA |
| medication | `use=No` → name, dose, duration, start age; `n_meds<k` → slot k | | pair | quoted/implied | names free text → string sentinel |
| screening | `ever=No` → age at last, frequency, result; stacked with sex and age gates | | pair | quoted | result may be DK in-universe — never require a substantive result |

**Social**

| family | gate | dependents | form | evidence | pitfalls |
|---|---|---|---|---|---|
| employment | `employed=No` → occupation, industry, hours; `Retired` → longest job applicable | | pair/narrow | quoted/implied | universes differ per item — occupation may be asked of ever-worked; occupation codes are strings with leading zeros |
| marital | `Never married` → years married NA | | pair | implied | widowed/divorced: duration of the ended marriage may be asked |
| migration | `born in study country` → age at immigration NA | | pair (complement trigger) | implied | trigger needs a coded country or flag; free text → not-enforceable |
| education | `level` below degree-bearing → degree type NA | | pair/narrow | implied | |
| household roster | `n_children<k` → `child_k_*` NA; `≥k` → applicable | | pair per slot | quoted/implied | slot shape from `$defs`; one pair per slot; slots capped while the count runs higher |

**Study logistics and instrument structure**

| family | gate | consequence | form | evidence | pitfalls |
|---|---|---|---|---|---|
| consent | `consent_X=No` → whole block NA | | compound pair | quoted | many columns, one `then.properties` |
| wave participation | `participated_w2=No` → every `_w2` NA | | compound pair | quoted | wide files only; in a long file the row's existence is the gate → nothing to encode |
| proxy/mode | `proxy=Yes` → self-report-only items NA; `No` → proxy-only items NA | | pair | quoted | mode may live in paradata → cross-table |
| other, specify | `code≠Other` → text = string sentinel; `=Other` → text ≠ sentinel | | pair (complement trigger) | quoted/implied | ask what the empty cell is; "meaningful text" is not assertable |
| checkbox + none | `none=1` → members `=0`; `member=1` → `none=0`; group asked → any-of | | compound/implies | implied | REDCap exports unchecked as 0 with no NA — group-level routing is invisible; ask |
| implication | `hysterectomy=Yes` → `menstruating=No`; `any=Yes` → ≥1 member | | implies/any-of | implied/inferred | encode only the direction the source or steward supports |

**Registry, claims, EHR, laboratory**

| family | gate | consequence | form | evidence | pitfalls |
|---|---|---|---|---|---|
| claims | `claim_type=Inpatient` → admission/discharge dates, discharge status, DRG applicable; outpatient → NA | | pair | quoted | files usually pre-split by type — the gate is the table, nothing to encode |
| EHR encounter | `enc_type ∈ {IP, IS}` → discharge disposition applicable; ambulatory/ED → NA | | pair | quoted (PCORnet, med) | EI unconfirmed — ask |
| result type | `type=Numeric` → numeric ≠ NA, text = NA; `Text` → reverse | | pair | implied | OMOP allows both populated — never propose exclusivity there |
| LOD | `below_lod=1` → modifier `<` (pin); value ≤ LOD | | pin / not-enforceable | quoted | LOD per batch → not-enforceable; constant per field → narrow |
| specimen | `collected=No` → volume, processing time, aliquots, storage NA | | pair | quoted/implied | |
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
| zero overload | 0 = "not applicable" / "none" / "No" | everywhere | the structural-zero trap: 0 is also a legitimate count; the schema can only `pin0`, and the `$comment` must say 0 doubles as NA |
| strings | "NA", "N/A", ".", "", "-", "SKIP" | CSV exports | declare the delivered literal as a string sentinel; a blank cell is a value that must be named |
| software specials | SAS `.`, `.A`–`.Z`; Stata `.a`–`.z`; SPSS user-missing | dictionaries written from analysis files | on CSV export they become blank or a literal — which? |

Three distinctions every proposal makes explicit:

- **Structural NA vs item missing.** A rule exists only for structural NA; refused and don't know are legal everywhere, in and out of universe. One merged "missing" code has lost the distinction — say so, propose nothing enforceable, ledger it.
- **What lands in the cell** for a skipped person: a code, a blank, a zero, or last wave's value carried forward — panel studies preload prior answers, and an NA pin would be wrong.
- **Delivered ≠ questionnaire.** The instrument skipped; SAS wrote `.`; the CSV wrote blank; a recode wrote -666. The routing question always establishes the *delivered* representation, because that is what the validator reads; a blank-delivered skip needs a code chosen at intake before any pair can be written.

## Expressibility

| rule family | in-row if/then? | schemify pattern |
|---|---|---|
| gate const/enum → dependent NA; gate → NA forbidden | yes | skip pair |
| gate → dependent = 0 (derived zero) | yes, one direction | substantive pin, `<Domain> routing:` comment, no twin |
| gate → dependent ∈ subset | yes | narrowing enum keeping item-missing codes |
| categorical gate → different numeric range (sex-specific bounds) | yes | narrowing: then-side `anyOf` numeric branch + sentinel branches |
| gate → at least one of several flags | yes | any-of under `then.allOf` |
| categorical → categorical (current → ever=Yes) | yes | implication |
| numeric range trigger (age ≥ 50) | yes | range trigger with sentinel exclusion |
| several conditions that must all hold (women aged 40+) | yes | AND trigger: all in one `if.properties`, all `required` |
| "everyone but code v" (other → specify) | yes | complement trigger `not: {const: v}` |
| count → slot k | yes | one pair per slot |
| sentinel as trigger (X not asked → Y not asked) | yes | skip pair on the sentinel const |
| checkbox mutual exclusion | yes | compound `then.properties` |
| other → specify text non-empty | partly | forbid the string sentinel; cannot assert content |
| arithmetic (pack-years, sums, BMI) | no | `not-enforceable` + `Soft checks` `$comment` + `x-derivation` |
| date/age ordering (quit ≥ start; dx ≤ death) | no | `not-enforceable` |
| range depending on another numeric field | no | `not-enforceable` |
| value ≤ LOD when LOD varies per batch | no | `not-enforceable` (constant LOD → narrowing) |
| cross-row (uniqueness, one baseline per id, wave order); aggregates; age consistency across waves | no | `not-enforceable` (`uniqueItems` catches whole-row duplicates only) |
| gate in another table; free-text gate | no | `not-enforceable` |

## Proposing to the steward

Always a batch: one message, numbered, grouped by gate variable, each gate listing all its dependents — never one rule at a time unless the steward has asked for one-at-a-time review. Sizing: at most ten numbered items per message; order by evidence (`quoted`, `implied`, `inferred`), then by number of dependents descending; a rule whose answer gates a whole category asks alone. Each item: the gate in study words · the reading · the dependents · "what does the cell contain for such a person" · the evidence · a one-line ask · D-number. On "yes": encode, flip the row and the line. On "no rule": ledger `user-confirmed — no routing on X` so it is never re-asked. On silence: the row stays `proposed`, no conditional.

**Batch 1 — survey cohort, behaviours** (mixed evidence; the derived-zero ambiguity and the cell question):

> Four routing questions, grouped by the variable I think does the gating:
>
> **`smk_ever`** (codebook: 1 Yes, 2 No, 7 refused, 9 DK)
> 1. I read `smk_status`, `cigs_day`, `smk_age_start`, `smk_years` as asked only when `smk_ever` = 1 — the questionnaire's Q14 arrow says "No → go to Q20" (quoted). For someone with `smk_ever` = 2, what is in those four cells in the file you deliver: a code, blank, or 0? (D031)
> 2. `cigs_day` has "0 = never smoked" in its label but also "777 = not asked". With your consent I counted: 1,204 rows carry 777 and 0 rows carry 0 among `smk_ever` = 2. I'd enforce 777 for never-smokers and treat 0 as a real "smokes none currently" for former smokers — not the reverse (a 0 tells me nothing about `smk_ever`). Right? (D032)
> 3. `smk_status` = 1 (current): I'd forbid the not-asked code in `cigs_day` but allow refused/DK — a current smoker can decline. Fine? (D033)
>
> **`alc_ever`**
> 4. `drinks_week` lists "777 = Nondrinker" inside its own codes; `alc_ever` also exists. Is 777 pinned by `alc_ever` = 2, or is `alc_ever` derived from `drinks_week` (in which case I'd encode the implication the other way)? (D034)

**Batch 2 — reproductive block** (which variable gates; hysterectomy interplay; counts as evidence, not provenance):

> The women's block. Three things I cannot settle from the dictionary:
>
> **The gate**
> 1. Menarche, pregnancies, menopause, OC, HRT, hysterectomy carry "-666 = N/A (male)". The file has `sex` (interviewer-recorded) and `gender_identity` (2019 module). Which one did the interview route on? I assume `sex` = 1 (male) pins all eleven fields to -666, and `gender_identity` never gates. (D040) — Also: `sex` = 3 (other): are these fields asked, skipped, or does it vary? (D041)
>
> **`parity`**
> 2. `age_first_birth` and `breastfed_ever` show "-666 = N/A" without saying for whom. I read the universe as `parity` ≥ 1 (implied by the label), not `ever_pregnant` = 1 — a miscarriage-only history should still carry -666 here. A woman with `parity` = 0: what is in `age_first_birth`? (D042)
>
> **`menopause_status`**
> 3. `age_menopause` is "-666 = N/A (premenopausal)". Level 4 of `menopause_status` is "unknown — hysterectomy". For level 4, is `age_menopause` -666, -888 (DK), or an age at surgery? Counts with your consent: 312 rows at level 4, 298 carry -888, 14 carry an age. I'd allow -888 and an age, forbid -666, and treat the 14 as real — but that is your call. (D043)

**Batch 3 — registry extract** (external source suggested; one item deliberately not-enforceable):

> Tumor table, three gates:
>
> **`vital_status`** (1 alive, 4 dead)
> 1. Dead → `date_last_contact` and `cause_death` must hold a value or an unknown code, never "not applicable"; alive → `cause_death` = 8888 (your "N/A" code), and date of last contact stays a real date. Confirm? (D050)
> 2. "Date of death ≥ date of diagnosis" — I can document this but cannot enforce it; it goes to the README's unenforced list. (D051, for your awareness)
>
> **`primary_site`**
> 3. `laterality` "0 = not a paired site". Enforcing "0 only for unpaired sites and 1–5/9 only for paired" needs the paired-site list. SEER's laterality-by-site table (Program Coding and Staging Manual) would supply it — may I use it as a named source, or do you have the registry's own list? (D052, source S07 pending your approval)
>
> **`behavior`**
> 4. In situ (2): I expect regional-nodes fields to carry the "not applicable" code and Summary Stage to be 0. Stated anywhere in your edits? If the registry's EDITS metafile is available, I'd read the inter-field edit rather than guess. (D053)

## Under a faithful policy

When the routing policy is `faithful`, the families above stop being a candidate generator. The catalog is still used to *recognize* what the source implies — an NA label naming a universe, a title "among current smokers", a universe or branching column, a skip-to column, an NA count matching a gate's No count — and to name which variable such a hint most plausibly points to; those rules carry evidence `implied` and quote the source text. It must not be used to put forward any rule the source never hints at: no `inferred` rows, no "an epidemiologist would expect", no crosstab-driven discovery.

## Cross-category and cross-table cases

Rules live in the mother file, so category order only decides *when* a pair is written, never *where*; the register (ROUTING.md) carries the wait.

- **Gate converted first, dependents later** — `sex` confirmed in demographics; the reproductive category arrives three sittings on. The register row waits on the dependents; the pair is written when they convert; demographics is not reopened; fixtures extend for both halves.
- **Dependent converted first, gate later** — `age_first_birth` sits in demographics with "-666 = N/A"; `parity` is in reproductive history, unconverted. Keep the sentinel branch, write no conditional, register the row `waiting` on `parity`. When `parity` converts, the row is encoded (quoted/implied) or becomes `proposed` (inferred) and the pair follows.
- **Gate in another table** — sex in `participant`, the women's block in `visit`; proxy status in a paradata table. Each table is one flat grain, so a rule never crosses: `not-enforceable`, README "Documented but not enforced". If the steward chooses to carry the gate into the dependent table as a column, it becomes an `added` variable on their instruction and the rule becomes in-row — offer it, never do it unasked.
- **Bidirectional facts are two rules** — `status=Current → ever=Yes` and `ever=No → status=Never` are separate rows, separately evidenced; encode only the directions the source or steward supports; never manufacture a twin for a substantive pin.
- **Stacked gates** (`sex` → `mammogram_ever` → `mammogram_age_last`): one pair per gate on the deepest field; rows with the outer gate off carry NA in the inner gate, so the inner pair never fires on them.
- **Wide vs long** — wave participation gates wave variables in a wide file; in a long file the row's absence is the routing and there is nothing to encode — say so in the README's grain paragraph.
