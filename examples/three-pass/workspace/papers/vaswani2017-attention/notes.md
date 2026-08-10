# Notes — Attention Is All You Need

Margin-note stream; entries append, newest first; nothing is deleted (NOTES-FORMAT).

## N0005 · 2026-08-10 · todo
anchor: §3.2.1 · p.4 · "We suspect that for large values"
tags: scaling, softmax, gradients, derivation-gap
status: active

**Derive the second link: why large-magnitude logits give the softmax "extremely small gradients"**

> "We suspect that for large values of d_k, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients."

[deriv-01](derivations/deriv-01-sqrt-dk-scaling.md) verified footnote 4's half of the chain: unscaled scores have sd √d_k, and dividing by √d_k restores unit variance. This half — large logits ⇒ vanishing softmax gradients — the paper hedges as "We suspect" and never derives; we recorded it as deriv-01's open gap rather than deriving it (the reader was satisfied stopping at the variance level, 2026-08-10). To close: compute the softmax Jacobian diag(p) − pp^T and show it vanishes as one logit dominates.

## N0004 · 2026-08-09 · question
anchor: §3.2.1 · p.4 · "In practice, we compute the attention function on"
tags: kernels, multi-head, regression-bridge
status: active

**Is QK^T a kernel matrix as in GP regression — and does each head learn a different kernel?**

I re-read 3.2 on paper. The QK^T matrix is basically a similarity matrix between all positions - like a kernel matrix in GP regression?? check this against multi-head: does each head learn a different kernel?

*(The reader's own words, hand-added at the bottom of this file the night before 2026-08-10; formalized into the note schema on 2026-08-10 — wording untouched.)*

## N0003 · 2026-08-10 · critique
anchor: §3.5 · p.6 · "We chose this function because we hypothesized it would allow"
tags: positional-encoding, revisit
status: active

**Not sold on the sinusoidal positional-encoding justification**

> "We chose this function because we hypothesized it would allow the model to easily learn to attend by relative positions, since for any fixed offset k, PEpos+k can be represented as a linear function of PEpos."

The reader finds the sinusoid choice arbitrary and does not buy §3.5's justification yet. The paper offers a hypothesis (relative positions become a linear function, quoted above), a second speculation that sinusoids "may allow the model to extrapolate to sequence lengths longer than the ones encountered during training" (§3.5, p.6), and reports that learned embeddings "produced nearly identical results (see Table 3 row (E))" (§3.5, p.6). Pinned to revisit when §3.5 gets its planned read — queued for next session.

## N0002 · 2026-08-10 · todo
anchor: §3.2.1 · p.4 · "To illustrate why the dot products get large"
tags: scaling, variance, derivation
status: closed — deriv-01

**Verify footnote 4's variance argument by hand**

> "assume that the components of q and k are independent random variables with mean 0 and variance 1. Then their dot product, q · k = Σ_{i=1}^{d_k} q_i k_i, has mean 0 and variance d_k."

Why √d_k and not d_k: the dot product's standard deviation — its typical magnitude — is √d_k under footnote 4's assumptions, so dividing by √d_k standardizes the scores back to variance 1 (a z-score); dividing by d_k would shrink variance to 1/d_k and flatten the softmax toward uniform. The paper's stated concern is the unscaled direction: large-magnitude scores push the softmax where gradients are "extremely small" (§3.2.1, p.4). The reader wants to verify the mean/variance computation themselves — a natural first derivation if the paper goes to pass 3.

## N0001 · 2026-08-10 · insight
anchor: §3.2 · p.3 · "The output is computed as a weighted sum"
tags: attention, regression-bridge
status: active

**Attention weights are computed, not fitted — kernel smoothing, not regression coefficients**

> "The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query with the corresponding key."

The reader asked whether attention weights are like regression coefficients. Resolution: a coefficient is a parameter — estimated once, fixed for all new observations; an attention weight is data-dependent — recomputed for every query from query–key compatibility (§3.2, p.3–4) and softmax-normalized to sum to 1. Closest classical relative: Nadaraya–Watson kernel-smoothing weights. What is learned are the projections defining the similarity (W_i^Q, W_i^K, W_i^V, §3.2.2, p.5), not the weights. The reader's own formulation, verbatim: "Weighted averaging where the weights are computed on the fly."
