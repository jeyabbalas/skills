# Ch 1 — Exploratory data analysis
book: downey2014-think-stats · pages: 21–36 (PDF; printed 1–16) · deck: ../decks/ch01.md

## Cues
- [x] C1 The book opens on anecdotes — what exactly makes anecdotal evidence fail? → §1 (four named failure modes) · recite 2026-08-13 ✓
- [x] C2 What kind of study is the NSFG, and whom does it represent? → §1.2 · recite 2026-08-13 ✓
- [x] C3 (backlog Q8) What does pandas replace in my R workflow — data.frame, vectors — and where will it bite? → §1.4 (DataFrame/Series/Index mapped; more coming) · recite 2026-08-13 ✓
- [x] C4 What does "cleaning" concretely involve for this data? → §1.6 · recite 2026-08-13 ✗ on the dot-notation half → ch01-c006, retried ✓
- [x] C5 How do you validate a freshly imported dataset? → §1.7 · recite 2026-08-13 ✓
- [x] C6 What is a recode, and when should I trust one over raw data? → §1.5 · recite 2026-08-13 ✓
- [x] C7 The last heading is "Interpretation" — what does it add beyond the numbers? → §1.8 · recite 2026-08-13 ✓

## Terms
| term | the book's definition (verbatim, p.) | field usage / contrast |
|---|---|---|
| anecdotal evidence | "based on data that is unpublished and usually personal" (p.1) | — |
| cross-sectional study | "captures a snapshot of a group at a point in time" (p.3) | — |
| oversampling | recruiting some groups "at rates higher than their representation in the U.S. population" (p.4) | ◆ in epi I'd say stratified sampling with unequal fractions; same object, design-weights (finalwgt) to undo it |
| recode | "not part of the raw data… calculated using the raw data" (p.8) | ◆ epi datasets call these derived variables |
| data cleaning | "check for errors, deal with special values, convert data into different formats, and perform calculations" (p.8) | — |

## Propositions
- Anecdotal evidence fails on four counts: small n, selection bias, confirmation bias, inaccuracy (p.2).
- The statistical alternative is a pipeline: data collection → descriptive statistics → exploratory analysis → estimation → hypothesis testing (p.2–3).
- The NSFG (Cycle 6, 2002–03) is cross-sectional, targets U.S. residents aged 15–44, and is deliberately *not* representative — three groups oversampled for subgroup power, at the cost of direct generalization (p.3–4).
- Import runs through the Stata dictionary (2002FemPreg.dct) into a pandas DataFrame: 13,593 pregnancies × 244 variables (p.4–6).
- Cleaning is consequential, not cosmetic: sentinel codes 97/98/99 → np.nan, agepreg centiyears → years, totalwgt_lb built from pounds + ounces/16 (p.9).
- Validation = value_counts() against the codebook's published tables; it caught a 51-pound baby (p.11–12).
- Work on two levels at once — statistics and context; records are people (p.12–13).

## Argument
My reconstruction: the chapter is one long argument that *trustworthy conclusions are manufactured, step by step, before any statistics happen*. Anecdotes fail for reasons that are really sampling-theory reasons (n, selection, confirmation, measurement). The remedy is a designed survey plus a disciplined import: know the design (cross-sectional, oversampled — so weights exist for a reason), read the codebook, prefer recodes because they embed the designers' consistency logic, convert sentinel codes to nan so missingness can't masquerade as data, then validate against published margins before believing anything downstream. The 51-pound baby is the whole thesis in one row: an error you'd never see without deliberately looking. This is exactly my R workflow's read_dta → clean → sanity-check loop, with the codebook playing the role of my data dictionary.

## Worked examples
### CleanFemPreg (p.9)
```python
def CleanFemPreg(df):
    df.agepreg /= 100.0
    na_vals = [97, 98, 99]
    df['birthwgt_lb'] = df.birthwgt_lb.replace(na_vals, np.nan)
    df['birthwgt_oz'] = df.birthwgt_oz.replace(na_vals, np.nan)
    df['totalwgt_lb'] = df.birthwgt_lb + df.birthwgt_oz / 16.0
```
Line by line: centiyears→years in place (dot access is fine for *reading/modifying* an existing column); sentinel codes become nan so IEEE nan-propagation keeps them out of every later computation; the new column is created with bracket syntax — creation is the one place dot syntax silently does the wrong thing (attribute, not column; p.10). The later addition `df.loc[df.birthwgt_lb > 20, 'birthwgt_lb'] = np.nan` (p.12) is the validation loop feeding back into cleaning.

## My questions
- Q1 (open) finalwgt is introduced and shelved ("we will come back to this point later", p.4) — where exactly does the book cash in the survey weights, and does it ever compare weighted vs unweighted answers?
- Q2 (closed — answered in §1.8) Whether the book would treat ethics as in scope: it does, explicitly (respect for respondents, p.13).

## Teach-back
### 2026-08-13 · closed-book
The chapter says: don't trust stories, trust designed data — but designed data only pays off if you respect its design. The NSFG oversamples some groups on purpose, so raw proportions don't describe the country until you use the weights. Getting the data in is half the work: variables come with a codebook, some are precomputed from raw answers and you should usually take those, and missing answers hide behind codes like 97–99 that will wreck your means if you don't turn them into real missing values. Then you check yourself against the published tables before doing anything — that's how a 51-pound baby gets caught. And the last point I liked: every row is a person; one respondent's record was six miscarriages then a birth. Statistics with empathy.
#### Critique
Solid — all seven cues touched, mechanism given for the sentinel-code trap. One scope note: "you should usually take those" (recodes) — the book's version carries a condition, "unless there is a compelling reason to process the raw data yourself" (p.8); kept as stated since the qualifier came back on probing. No new cards minted; ch01-c003/c005 already cover the wobbliest ground.

## Summary
Chapter 1 replaces anecdote with a manufactured chain of trust: a designed survey read through its codebook, imported into pandas, cleaned so sentinel codes become honest missingness, and validated against published tables before analysis begins. Its two lasting reflexes are "prefer recodes, they embed the designers' checks" and "compare value_counts to the codebook before believing anything." The chapter's ethic — records are people — is stated as part of the method, not an aside.

## Links
> ◆ **Beyond the book · Source** — [pandas: Comparison with R / R libraries](https://pandas.pydata.org/docs/getting_started/comparison/comparison_with_r.html) — the one-page mapping (data.frame ↔ DataFrame, aggregate ↔ groupby) that makes §1.4 read natively for an R hand.
