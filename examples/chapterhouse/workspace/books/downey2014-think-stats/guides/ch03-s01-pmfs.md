# §3.1 — Pmfs: a guide
book: downey2014-think-stats · for: §3.1 (PDF 51–52 · printed 31–32) · foundations: ch03-foundations.md · note: ../notes/ch03-pmfs.md

> ◆ **Beyond the book** — this whole guide is mine, not Downey's; it prepares your own read of §3.1, it does not replace it. The book's own words appear only in quotation marks with printed page numbers.

## How to use this guide

Foundations first: before S1, own F1–F3 in [ch03-foundations.md](ch03-foundations.md) — each check tells you whether to skip. Then take the steps in order, beside the open book; each follows the same rhythm: **what it says** → **the book's own words** → **a picture** (in your register, usually four lines of runnable code) → **a check you can do in your head**. Say the self-test out loud, then read the book's own pp. 31–32 unaided, and bring whatever breaks to the capture session.

## Foundations

Before S1, own: F1, F2, F3 → [ch03-foundations.md](ch03-foundations.md). New gaps found during the read get written there, never here.

## The section, step by step

### S1 — A PMF is the histogram, divided through by n

**What it says.** Chapter 2's `Hist` counted values. A PMF re-expresses the same distribution in probabilities: each value maps to its frequency as a fraction of the sample size, so different-sized groups become comparable — the exact fix chapter 2's ending asked for.

> "Another way to represent a distribution is a probability mass function (PMF), which maps from each value to its probability. A probability is a frequency expressed as a fraction of the sample size, n. To get from frequencies to probabilities, we divide through by n, which is called normalization." (p. 31)

**Picture.** The histogram's bars, each divided by the same total:

```python
freqs = {1: 2, 2: 2, 3: 1}          # a Hist, as a mapping (F1)
n = 5
pmf = {x: f / n for x, f in freqs.items()}   # {1: 0.4, 2: 0.4, 3: 0.2}
```

**Check.** In R terms: your `table(x)` is the Hist — what one operation turns it into the PMF?
*Answer: divide by `sum(table(x))` — normalization.*

### S2 — Building one by hand, three lines

**What it says.** The book constructs the mapping with a plain dict and a loop — F1's dict, F2's unpacking, nothing else:

> "Given a Hist, we can make a dictionary that maps from each value to its probability:
> `n = hist.Total()` · `d = {}` · `for x, freq in hist.Items(): d[x] = freq / n`" (p. 31)

**Picture.** Run it on chapter 2's pregnancy-length Hist and spot-check one value against `table(prglngth)/length(prglngth)` in your head.

**Check.** Why does the loop need no pre-allocation of `d`?
*Answer: dict assignment creates the key on first write (F1's check).*

### S3 — The Pmf class: same toolbox as Hist, floats instead of counts

**What it says.** `thinkstats2.Pmf` packages S2's idea. The constructor eats the same things `Hist` eats, and the two classes share methods by inheritance (F3) — the difference is only what the values are.

> "`>>> pmf = thinkstats2.Pmf([1, 2, 2, 3, 5])` · `Pmf({1: 0.2, 2: 0.4, 3: 0.2, 5: 0.2})` — The Pmf is normalized so total probability is 1." (p. 31)

> "The biggest difference is that a Hist maps from values to integer counters; a Pmf maps from values to floating-point probabilities." (p. 31)

Lookup is `pmf.Prob(2)` or, equivalently, `pmf[2]` — "The bracket operator is equivalent" (p. 32).

**Check.** For the pmf above: `pmf.Prob(2)`?
*Answer: 0.4 — the value 2 appeared twice in five.*

### S4 — Modifying a Pmf can silently break normalization

**What it says.** `Incr` adds to one probability, `Mult` scales one — and after either, the probabilities may no longer sum to 1. `Total()` reports the sum; `Normalize()` repairs it; `Copy()` protects the original. (§3.4 will use exactly this Incr/Mult-then-Normalize move to bias and unbias a distribution.)

> "If you modify a Pmf, the result may not be normalized; that is, the probabilities may no longer add up to 1." (p. 32)

**Picture.** The book's own run, traced: start `{1: .2, 2: .4, 3: .2, 5: .2}` → `Incr(2, 0.2)` → 2 holds 0.6, total 1.2 → `Mult(2, 0.5)` → 2 holds 0.3, total 0.9 → `Normalize()` → total 1.0.

> "My notation in this section might seem inconsistent, but there is a system: I use Pmf for the name of the class, pmf for an instance of the class, and PMF for the mathematical concept of a probability mass function." (p. 33)

**Check.** After `Incr` and `Mult` above, what does `pmf.Total()` return, and is the object still a PMF in the mathematical sense?
*Answer: 0.9 — no; not until `Normalize()` runs.*

## Self-test

A one-minute self-test on §3.1. Answer out loud before reading on — the recite will ask these in harder clothing.

1. What does a PMF map from, and to?
2. What is normalization, in one sentence?
3. Hist vs Pmf — the one biggest difference?
4. Two ways to look up the probability of a value in a `pmf`?
5. Which operations can leave a Pmf un-normalized, and what repairs it?

*Answers: 1. each value → its probability. 2. dividing frequencies by the sample size n. 3. Hist maps to integer counts, Pmf to floating-point probabilities. 4. `pmf.Prob(x)` and `pmf[x]`. 5. `Incr` and `Mult`; `Normalize()` (check with `Total()`).*
