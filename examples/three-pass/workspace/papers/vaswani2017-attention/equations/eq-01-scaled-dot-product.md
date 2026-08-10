# Attention Is All You Need — Equation (1): Scaled Dot-Product Attention

```yaml equation-data
latex_clean: "\\mathrm{Attention}(Q, K, V) = \\mathrm{softmax}\\left(\\frac{QK^{\\top}}{\\sqrt{d_k}}\\right)V"
latex_annotated: "\\mathrm{Attention}(\\htmlClass{term t1 term-q}{Q}, \\htmlClass{term t2 term-k}{K}, \\htmlClass{term t3 term-v}{V}) = \\htmlClass{term t4 term-softmax}{\\mathrm{softmax}}\\left(\\frac{\\htmlClass{term t1 term-q}{Q}\\htmlClass{term t2 term-k}{K^{\\top}}}{\\htmlClass{term t5 term-scale}{\\sqrt{d_k}}}\\right)\\htmlClass{term t3 term-v}{V}"
terms:
  - {id: q, slot: t1, math: "Q", meaning: "The queries, \"packed together into a matrix Q\"; queries (and keys) have dimension d_k (§3.2.1, p.4).", intuition: "One row per position that is asking for information — the profile it wants matched."}
  - {id: k, slot: t2, math: "K^{\\top}", meaning: "The keys, packed into matrix K; QKᵀ computes \"the dot products of the query with all keys\" (§3.2.1, p.4).", intuition: "What every position advertises about itself; a big dot product with a query means \"relevant to that query.\""}
  - {id: v, slot: t3, math: "V", meaning: "The values, packed into matrix V, of dimension d_v; the output is \"a weighted sum of the values\" (§3.2, p.3–4).", intuition: "The content that actually gets averaged — keys decide how much, values decide of what."}
  - {id: softmax, slot: t4, math: "\\mathrm{softmax}", meaning: "Applied to the scaled scores \"to obtain the weights on the values\" (§3.2.1, p.4).", intuition: "The multinomial-logit link: real-valued scores in, positive weights that sum to 1 out — turning scores into an averaging scheme."}
  - {id: scale, slot: t5, math: "\\sqrt{d_k}", meaning: "\"divide each by √dk\" (§3.2.1, p.4); footnote 4: with independent mean-0, variance-1 components, q·k has mean 0 and variance d_k (p.4).", intuition: "A z-score: the raw dot product's spread grows like √d_k, so dividing by √d_k keeps scores at unit variance no matter how wide the keys are."}
```

## What it says

Every query is scored against every key by dot product; the scores are divided by \(\sqrt{d_k}\); a softmax turns each query's scores into weights; the output for each query is the weight-averaged sum of the values. Matrix form processes "a set of queries simultaneously" (§3.2.1, p.4): with \(n\) queries and \(m\) key–value pairs, \(QK^{\top}\) is the \(n \times m\) score table, and the result is one \(d_v\)-dimensional output row per query.

## Intuition

A learned kernel smoother. For each position, prediction = weighted average of other positions' values, weights = normalized similarity between this position's query and the others' keys. Nothing in the weights is a fitted constant — they are recomputed from the data every time; what training fits are the projections that produce \(Q\), \(K\), \(V\) (§3.2.2, p.5).

## Term by term

(Rendered from the `equation-data` block above — hover a term on the page to highlight its legend row.)

## Where it's used

- Inside every head of multi-head attention: \(\mathrm{head}_i = \mathrm{Attention}(QW_i^Q, KW_i^K, VW_i^V)\) (§3.2.2, p.5).
- All three attention sites of the model — encoder-decoder attention, encoder self-attention, decoder self-attention (§3.2.3, p.5).
- The decoder's masking lives inside this equation: illegal connections are set to \(-\infty\) "in the input of the softmax" so their weights vanish (§3.2.3, p.5).

> ◆ **Beyond the paper · Context** — Dot-product (multiplicative) attention predates this paper [2, 3 cited §3.2.1, p.4]; the contribution named here is the \(1/\sqrt{d_k}\) scaling. The variance argument for it is a footnote-level heuristic, not a theorem — the reader has pinned verifying it by hand: margin notes [N0002](../notes.html#note-N0002), and the weights-vs-coefficients bridge is [N0001](../notes.html#note-N0001).

Figure: [Figure 2](../figures/fig-02.html) draws this pipeline.
