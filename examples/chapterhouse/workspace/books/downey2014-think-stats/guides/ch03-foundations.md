# Ch 3 — Foundations
book: downey2014-think-stats · for: ch 3 · note: ../notes/ch03-pmfs.md

> ◆ **Beyond the book** — everything in this file is mine, not Downey's: the Python the chapter assumes without teaching, mapped once onto the R you already own. Skip any item you already have — the check tells you. The book's own words appear only in quotation marks with printed pages.

### F1 — The Python dict is your named vector, used as a mapping

§3.1 builds a PMF with three lines the book never explains: `d = {}` makes an empty **dict**, and `d[x] = freq / n` files a value under a key (p. 31). A dict is Python's mapping type — R's named vector or named list, but with real keys instead of character names:

| move | R | Python |
|---|---|---|
| make one | `d <- c("1"=0.2, "2"=0.4)` | `d = {1: 0.2, 2: 0.4}` |
| look up | `d[["2"]]` | `d[2]` |
| add / overwrite | `d[["5"]] <- 0.2` | `d[5] = 0.2` |

Two differences that bite R hands: keys keep their type (`d[2]` and `d["2"]` are different entries), and there is no partial matching — a missing key is a `KeyError`, not `NULL`.

*Check:* after `d = {}` then `d[1] = 0.4` then `d[1] = 0.2`, what is `d[1]`?
*Answer: 0.2 — assignment to an existing key overwrites; that is why the book's loop needs no pre-allocation.*

### F2 — Tuple unpacking drives Python's loops

The book's loop header is `for x, freq in hist.Items():` (p. 31). `Items()` yields **pairs**, and `x, freq = pair` splits one pair into two names — that is **tuple unpacking**, and it is everywhere in idiomatic Python. R has no direct analogue; the nearest habit is looping over `names(v)` and indexing back in, which is exactly the clumsiness unpacking removes.

*Check:* looping `for x, freq in [(1, 2), (2, 2), (5, 1)]:` — what are `x` and `freq` on the second pass?
*Answer: x = 2, freq = 2.*

### F3 — Reading Python classes: `obj.Method()`, `obj[key]`, inheritance

Three idioms you must read (not write) all through this book:

- `pmf.Prob(2)` — a **method**: a function that travels with the object. R's S3 spelling would be `Prob(pmf, 2)`; Python puts the object first, before the dot.
- `pmf[2]` — the bracket operator is also a method, one the class chose to support; here it is defined to do the same lookup as `Prob`.
- "they inherit many of their methods from a common parent class" (p. 31) — **inheritance**: `Hist` and `Pmf` share one toolbox (`Values`, `Items`, …), so what you learned on `Hist` in chapter 2 transfers unchanged.

*Check:* do `pmf.Prob(2)` and `pmf[2]` differ?
*Answer: no — the bracket form is defined as the same lookup; the book says "The bracket operator is equivalent" (p. 32).*

### If a foundation is missing

- ◆ **Source** — [The Python Tutorial §5.5–5.6, "Dictionaries" and "Looping Techniques"](https://docs.python.org/3/tutorial/datastructures.html#dictionaries) — for F1 and F2: ten minutes, official, with the `items()` loop shown exactly as the book uses it.
- ◆ **Source** — [pandas: "Comparison with R / R libraries"](https://pandas.pydata.org/docs/getting_started/comparison/comparison_with_r.html) — the standing R→Python phrasebook; keep it open from §3.5 (DataFrame indexing) onward.
