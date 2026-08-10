# Attention Is All You Need — Derivation 01: the √d_k scaling · eq (1)

status: complete
target: eq (1), §3.2.1 · p.4 — the \(1/\sqrt{d_k}\) scaling factor, justified by footnote 4

## The target

Equation (1), verbatim (§3.2.1, p.4):

\[ \mathrm{Attention}(Q, K, V) = \mathrm{softmax}\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V \]

The claim derived here is footnote 4's, the paper's justification for the \(\sqrt{d_k}\):

> "To illustrate why the dot products get large, assume that the components of q and k are independent random variables with mean 0 and variance 1. Then their dot product, q · k = Σ_{i=1}^{d_k} q_i k_i, has mean 0 and variance d_k." (footnote 4, p.4)

The sentence it annotates, in the body: "We suspect that for large values of d_k, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients" (§3.2.1, p.4).

## Assumptions ledger

| # | assumption | stated? | challenged | verdict |
|---|---|---|---|---|
| A1 | Every component \(q_i\), \(k_i\) has mean 0 and variance 1 | fn 4, p.4 ("mean 0 and variance 1") | In the model, \(q\) and \(k\) are outputs of learned projections \(QW_i^Q\), \(KW_i^K\) (§3.2.2, p.5); training moves means and variances freely, and nothing in the architecture re-normalizes per component. Breaks: any trained network. | Reader's verdict: plausible at initialization (suitably scaled random weights), nothing enforces it after training. Derivation stands as an initialization-time illustration — the paper's own framing ("To illustrate", fn 4) — with this caveat recorded. |
| A2 | All \(2d_k\) components — within \(q\), within \(k\), and \(q\) versus \(k\) — are mutually independent | fn 4, p.4 says only "independent"; mutual independence is our reading, and the derivation needs it | Load-bearing twice: factorizing \(\mathbb{E}[q_i^2k_i^2]\) (step 4) and killing the cross terms \(\mathbb{E}[q_ik_iq_jk_j]\) (step 5) — the latter needs the full four-way factorization, which pairwise independence alone would not give. Breaks: \(q\) and \(k\) are computed from the same token stream, so their independence is the first casualty of training. | Holds under the footnote's reading at initialization; suspect after training, same caveat as A1. |
| A3 | Second moments exist and are finite; no distributional shape is assumed | implicit | Without finite \(\mathbb{E}[q_i^2k_i^2]\) the variance of a term is undefined. | Holds — A1 + A2 give \(\mathbb{E}[q_i^2k_i^2] = 1\). Worth saying aloud: normality is never used; the whole argument is first and second moments only. |

## Derivation

Reader-driven, 2026-08-10; each step carries its justification.

1. \(q \cdot k = \sum_{i=1}^{d_k} q_i k_i\) — definition of the dot product; one entry of \(QK^{\top}\) in eq (1), before scaling.
2. \(\mathbb{E}[q_i k_i] = \mathbb{E}[q_i]\,\mathbb{E}[k_i] = 0\) — A2 (\(q_i\) independent of \(k_i\)), then A1 (both means 0).
3. \(\mathbb{E}[q \cdot k] = \sum_{i=1}^{d_k} \mathbb{E}[q_i k_i] = 0\) — linearity of expectation (needs nothing beyond step 2). *Footnote 4's mean claim, done.*
4. \(\operatorname{Var}(q_i k_i) = \mathbb{E}[q_i^2 k_i^2] - \big(\mathbb{E}[q_i k_i]\big)^2 = \mathbb{E}[q_i^2]\,\mathbb{E}[k_i^2] = 1\) — the subtracted square is 0 by step 2 (the reader's "variance is E[q_i^2 k_i^2]" holds *because* the term has mean 0); A2 factorizes the product (\(q_i^2\) and \(k_i^2\) are functions of independent variables); A1 gives \(\mathbb{E}[q_i^2] = \operatorname{Var}(q_i) + (\mathbb{E}[q_i])^2 = 1\) — using mean 0 again, not variance alone.
5. For \(i \neq j\): \(\operatorname{Cov}(q_i k_i,\, q_j k_j) = \mathbb{E}[q_i k_i q_j k_j] - \mathbb{E}[q_i k_i]\,\mathbb{E}[q_j k_j] = \mathbb{E}[q_i]\mathbb{E}[k_i]\mathbb{E}[q_j]\mathbb{E}[k_j] - 0 = 0\) — A2's mutual independence factorizes the fourth moment across the four distinct variables; this is the step pairwise independence would not license. *Terms uncorrelated, as the reader claimed — ground supplied.*
6. \(\operatorname{Var}(q \cdot k) = \sum_{i=1}^{d_k} \operatorname{Var}(q_i k_i) = d_k \cdot 1 = d_k\) — variance of a sum of pairwise-uncorrelated terms is the sum of the variances (bilinearity of covariance), steps 4–5. *Footnote 4's variance claim, done — the footnote is fully derived.*
7. \(\operatorname{sd}(q \cdot k) = \sqrt{d_k}\), and \(\operatorname{Var}\!\left(\frac{q \cdot k}{\sqrt{d_k}}\right) = \frac{d_k}{d_k} = 1\) with mean still 0 — \(\operatorname{Var}(aX) = a^2 \operatorname{Var}(X)\). The typical magnitude of an unscaled score grows like \(\sqrt{d_k}\); dividing by \(\sqrt{d_k}\) is a z-score, returning eq (1)'s logits to mean 0, variance 1 for every \(d_k\). (Dividing by \(d_k\) instead would send the variance to \(1/d_k\) — scores collapse toward 0 and the softmax flattens toward uniform as \(d_k\) grows.)

What is established: under A1–A3, unscaled dot-product scores have standard deviation \(\sqrt{d_k}\), and the \(1/\sqrt{d_k}\) in eq (1) restores unit variance. What is not established: that this prevents small gradients — see Gaps.

## Gaps

- The paper's motivating chain has a second link the derivation does not touch: "We suspect that for large values of d_k, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients" (§3.2.1, p.4 — main text; footnote 4 attaches to this sentence and illustrates only the magnitude half). The large-logits ⇒ vanishing-softmax-gradients link is hedged by the paper itself ("We suspect") and derived nowhere in it; the reader chose to stop at the variance level, so it stays an open gap rather than a closed step. → note [N0005](../notes.html#note-N0005)
