# Think Stats, 2nd edition — inspectional survey

**Book type**: practical — the preface organizes the whole book around a process the reader performs: "the process I use when I start working with a dataset" (p.v), with per-chapter exercises meant to be coded.
**In one sentence**: Statistics taught as a computational practice — simulation and Python code in place of formula-first derivation — with one real question (do first babies arrive late?) carried through a national survey dataset from import to analytic methods.

## The shape of the book
- The chapter order *is* the author's analysis pipeline (p.v): import/clean → single-variable distributions (ch 1–6) → pairwise relationships (ch 7) → estimation and testing (ch 8–9) → regression and multivariate (ch 10–11) → specialized methods (ch 12–13) → the analytic shortcuts last, as an epilogue to simulation (ch 14).
- Two survey datasets run throughout: the NSFG (pregnancy) and BRFSS (health behaviors), both CDC (p.vi–vii).
- The computational stance is explicit: p-values by simulation, the CLT by experiment; "some ideas that are hard to grasp mathematically are easy to understand by simulation" (p.vi).
- Everything rides on the companion repo (thinkstats2.py, thinkplot.py, per-chapter notebooks with solutions; §0.2).

## Chapter map
- ch 1 — Trustworthy data: survey design, codebook, import, cleaning, validation · diff 1 · 3 exx
- ch 2 — Histograms, outliers as judgment, summaries, effect size · diff 1 · 4 exx
- ch 3 — PMFs; the class size paradox · diff 2 · 4 exx
- ch 4 — CDFs and percentiles · diff 2 · 4 exx
- ch 5 — Fitting model distributions (exponential, normal, lognormal, Pareto) · diff 2 · 5 exx
- ch 6 — PDFs, KDE, moments, skewness · diff 3 · 4 exx
- ch 7 — Scatter plots, covariance, correlation (Pearson, Spearman) · diff 2 · 3 exx
- ch 8 — Estimation: sampling distributions, bias, standard error · diff 2 · 4 exx
- ch 9 — Hypothesis testing by permutation/simulation · diff 3 · 4 exx
- ch 10 — Linear least squares · diff 2 · 4 exx
- ch 11 — Multiple and logistic regression (StatsModels) · diff 3 · 4 exx
- ch 12 — Time series · diff 2 · 4 exx · *skimmed by license: no time-series endpoints in my cohorts*
- ch 13 — Survival analysis, Kaplan-Meier · diff 2 · 4 exx
- ch 14 — Analytic methods: the CLT cash-out · diff 3 · 4 exx

## What depends on what
- 6 ← 4, 5 — the distribution framework unifies CDFs with the fitted models (§6.3)
- 7 ← 2, 4 — relationships are read through distributions and percentiles
- 9 ← 2, 8 — testing revisits the ch 2 first-babies effect with ch 8's sampling machinery ("First babies again", §9.8)
- 13 ← 4, 8 — survival curves are built from CDFs and estimated with ch 8's tools
- 14 ← 8, 9 — the analytic versions of the simulations
- otherwise linear; the full column lives in CONTENTS.md

> ◆ **Beyond the book · Context** — The 6←5 and 13←8 edges are inferred from the section titles and preface pipeline, not from an explicit "this chapter assumes"; treat them as soft until those chapters are read.

## Your questions for this book
1. When my effect is tiny but my n is huge, what should I report — a p-value, an effect size, or both?
2. What actually goes wrong when I drop "outliers" before analysis?
3. Do first babies actually arrive late — and what does honest evidence for a null-ish answer look like?
4. How do I choose summaries for skewed, birth-weight-like variables?
5. What is a p-value under the hood — can I compute one by simulation and trust it?
6. How do I tell sampling error from a real cohort effect?
7. When is a lognormal model justified for biomarker-like data, rather than merely convenient?
8. What does pandas replace in my R workflow, and where will it bite me?

## The reading plan
Book order, ch 12 skimmed by license (revocable). 13 chapters at 2 sessions/week ≈ 7 weeks of pass 2, assuming one chapter per sitting; ch 6, 9, 11, 14 are flagged diff 3 and may split. The plan changes if the first diff-3 chapter overruns badly, or if cohort work makes ch 13 urgent — it can be pulled forward once ch 4 and 8 are recited.
