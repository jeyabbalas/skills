# Attention Is All You Need — Detailed summary

Pass 2 apparatus. This file grows section by section as we read together; sections marked *(not yet read together)* are unvisited. Every bullet is the paper's content, anchored (§/p.); blockquotes starting ◆ are beyond the paper.

## 1 · Introduction

- Recurrent neural networks — LSTM [13] and gated recurrent [7] networks in particular — are "firmly established as state of the art approaches in sequence modeling and transduction problems" such as language modeling and machine translation [35, 2, 5] (§1, p.2).
- Recurrent models factor computation along the symbol positions of the sequences: they generate hidden states \(h_t\) as a function of the previous hidden state \(h_{t-1}\) and the input for position \(t\). "This inherently sequential nature precludes parallelization within training examples," which becomes critical at longer sequence lengths, since memory constraints limit batching across examples (§1, p.2).
- Factorization tricks [21] and conditional computation [32] have improved computational efficiency, but "The fundamental constraint of sequential computation, however, remains." (§1, p.2)
- Attention mechanisms are already integral to strong sequence models because they allow "modeling of dependencies without regard to their distance in the input or output sequences" [2, 19] — yet in all but a few cases [27] they are used *in conjunction with* a recurrent network (§1, p.2).
- The contribution: "the Transformer, a model architecture eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output." It "allows for significantly more parallelization" and reaches a new state of the art in translation quality "after being trained for as little as twelve hours on eight P100 GPUs" (§1, p.2).

> ◆ **Beyond the paper · Personal** — In your terms: a recurrent model is an iterative fit — position \(t\)'s state needs position \(t-1\)'s state, so the computation cannot be vectorized across the sequence, the way a GEE fit with a serial working correlation must sweep observation by observation. The Transformer's bet is that you can delete that chain and let every position consult every other position directly, so the whole sequence is processed at once, like one matrix operation on a full design matrix.

## 2 · Background

*(not yet read together)*

## 3 · Model Architecture

- Most competitive neural sequence transduction models share an **encoder-decoder** structure [5, 2, 35]: the encoder maps an input sequence of symbol representations \((x_1, ..., x_n)\) to continuous representations \(z = (z_1, ..., z_n)\); given \(z\), the decoder generates the output sequence \((y_1, ..., y_m)\) one element at a time (§3, p.2).
- "At each step the model is auto-regressive [10], consuming the previously generated symbols as additional input when generating the next." (§3, p.2)
- The Transformer keeps this overall shape, "using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder" — the left (encoder) and right (decoder) halves of [Figure 1](figures/fig-01.html) (§3, p.3).

### 3.1 Encoder and Decoder Stacks

*(not yet read together)*

### 3.2 Attention

- "An attention function can be described as mapping a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors." (§3.2, p.3)
- "The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query with the corresponding key." (§3.2, p.3–4)
- Both attention variants used here are drawn in [Figure 2](figures/fig-02.html).

> ◆ **Beyond the paper · Personal** — The weights in that weighted sum are not regression coefficients. A fitted coefficient is a parameter: estimated once, then fixed for every new observation. An attention weight is computed fresh for every query from query–key similarity, and the weights across values sum to 1 (the softmax). The nearest older relative in your toolkit is kernel smoothing — Nadaraya–Watson — where each prediction is a weighted average of observed values and the weights come from similarity, not from fitting. Attention is that, with the similarity function itself learned. (Margin note [N0001](notes.html#note-N0001).)

#### 3.2.1 Scaled Dot-Product Attention

- The paper's variant is named "Scaled Dot-Product Attention" (Figure 2, left). Queries and keys have dimension \(d_k\), values dimension \(d_v\). "We compute the dot products of the query with all keys, divide each by \(\sqrt{d_k}\), and apply a softmax function to obtain the weights on the values." (§3.2.1, p.4)
- In practice queries are processed as a batch, packed into a matrix \(Q\), with keys and values packed into \(K\) and \(V\):
  \[ \mathrm{Attention}(Q, K, V) = \mathrm{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V \qquad \text{(1)} \]
  (§3.2.1, p.4, eq. (1) — term-by-term on the [equation page](equations/eq-01-scaled-dot-product.html).)
- The two common attention families: **additive attention** [2], which scores query–key compatibility with a one-hidden-layer feed-forward network, and **dot-product (multiplicative) attention**, identical to this algorithm except for the \(1/\sqrt{d_k}\) scaling. They are "similar in theoretical complexity," but dot-product attention "is much faster and more space-efficient in practice" because it can use highly optimized matrix-multiplication code (§3.2.1, p.4).
- Why scale at all: for small \(d_k\) the two families perform similarly, but "additive attention outperforms dot product attention without scaling for larger values of \(d_k\)" [3]. "We suspect that for large values of \(d_k\), the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients." The \(1/\sqrt{d_k}\) scaling counteracts this (§3.2.1, p.4).
- Footnote 4 (p.4) carries the variance argument: assume the components of \(q\) and \(k\) are independent random variables with mean 0 and variance 1; then \(q \cdot k = \sum_{i=1}^{d_k} q_i k_i\) has mean 0 and variance \(d_k\) — so the typical size of an unscaled dot product grows like \(\sqrt{d_k}\), and dividing by \(\sqrt{d_k}\) brings the variance back to 1. (Verified by hand in [deriv-01](derivations/deriv-01-sqrt-dk-scaling.md); pin [N0002](notes.html#note-N0002) closed, gap [N0005](notes.html#note-N0005) open.)

#### 3.2.2 Multi-Head Attention

- Rather than one attention function over \(d_{model}\)-dimensional queries, keys, and values, the paper projects them \(h\) times "with different, learned linear projections" to \(d_k\), \(d_k\), and \(d_v\) dimensions, runs the attention function on each projected version in parallel, concatenates the \(d_v\)-dimensional outputs, and projects once more (§3.2.2, p.4–5; Figure 2, right).
- "Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions. With a single attention head, averaging inhibits this." (§3.2.2, p.5)
- Formally: \(\mathrm{MultiHead}(Q, K, V) = \mathrm{Concat}(\mathrm{head}_1, ..., \mathrm{head}_h)W^O\) with \(\mathrm{head}_i = \mathrm{Attention}(QW_i^Q, KW_i^K, VW_i^V)\), where \(W_i^Q \in \mathbb{R}^{d_{model} \times d_k}\), \(W_i^K \in \mathbb{R}^{d_{model} \times d_k}\), \(W_i^V \in \mathbb{R}^{d_{model} \times d_v}\), and \(W^O \in \mathbb{R}^{h d_v \times d_{model}}\) (§3.2.2, p.5).
- Settings: \(h = 8\) parallel heads, \(d_k = d_v = d_{model}/h = 64\). "Due to the reduced dimension of each head, the total computational cost is similar to that of single-head attention with full dimensionality." (§3.2.2, p.5)

#### 3.2.3 Applications of Attention in our Model

The Transformer uses multi-head attention in three ways (§3.2.3, p.5):

- **Encoder-decoder attention**: the queries come from the previous decoder layer, and "the memory keys and values come from the output of the encoder," so every decoder position can attend over all input positions — mimicking the typical encoder-decoder attention of sequence-to-sequence models [38, 2, 9].
- **Encoder self-attention**: all of the keys, values, and queries come from the same place — the output of the previous encoder layer; each position attends to all positions of the previous layer.
- **Decoder self-attention**: each decoder position attends to all decoder positions up to and including itself. "We need to prevent leftward information flow in the decoder to preserve the auto-regressive property." Implemented inside scaled dot-product attention "by masking out (setting to \(-\infty\)) all values in the input of the softmax which correspond to illegal connections."

### 3.3 Position-wise Feed-Forward Networks

*(not yet read together)*

### 3.4 Embeddings and Softmax

*(not yet read together)*

### 3.5 Positional Encoding

*(not yet read together)*

Margin notes on this section: [N0001 — attention weights are computed, not fitted](notes.html#note-N0001) · [N0002 — verify the variance-\(d_k\) argument](notes.html#note-N0002) · [N0003 — not sold on the sinusoidal justification (§3.5)](notes.html#note-N0003) · [N0004 — is QK^T a kernel matrix as in GP regression? (§3.2.1)](notes.html#note-N0004) · [N0005 — derive the large-logits ⇒ small-softmax-gradients link (§3.2.1)](notes.html#note-N0005)

## 4 · Why Self-Attention

*(not yet read together)*

## 5 · Training

*(not yet read together)*

## 6 · Results

*(not yet read together)*

## 7 · Conclusion

*(not yet read together)*

## Attention Visualizations (appendix)

*(not yet read together)*
