# Reproduction inventory — Attention Is All You Need

Everything a reproduction of the Transformer needs, hunted down from the paper itself. Pseudocode is ours, line-anchored to the paper; nothing in quotation marks is reconstructed.

## Algorithms

### Scaled Dot-Product Attention (§3.2.1 · p.4 · eq (1))

\[ \mathrm{Attention}(Q, K, V) = \mathrm{softmax}\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V \]

```text
input:  Q (n_q × d_k), K (m × d_k), V (m × d_v)      # queries/keys dim d_k, values dim d_v — §3.2.1 p.4
scores  = Q @ K.T                                    # dot products of each query with all keys — §3.2.1 p.4
scores  = scores / sqrt(d_k)                         # the scaling; motivation in footnote 4 — §3.2.1 p.4
[mask]  scores[illegal] = -inf                       # decoder masking, inside the softmax input — §3.2.3 p.5
weights = softmax(scores, axis=keys)                 # the weights on the values — §3.2.1 p.4
output  = weights @ V                                # weighted sum of the values — §3.2 p.3–4
```

- Footnote 4 (p.4): with q, k components independent, mean 0, variance 1, the dot product q·k has mean 0 and variance d_k — the reason for the scale. Derived by hand in [deriv-01](../derivations/deriv-01-sqrt-dk-scaling.md); the further link to small softmax gradients is the paper's "We suspect" and remains open (note N0005).

### Multi-Head Attention (§3.2.2 · p.4–5)

```text
for i in 1..h:                                       # h parallel heads — §3.2.2 p.5
    head_i = Attention(Q W_i^Q, K W_i^K, V W_i^V)    # learned projections to d_k, d_k, d_v — p.4–5
output = Concat(head_1, …, head_h) @ W^O             # concatenate, project once more — p.5
# shapes: W_i^Q, W_i^K ∈ R^{d_model×d_k}, W_i^V ∈ R^{d_model×d_v}, W^O ∈ R^{h·d_v×d_model} — p.5
# paper setting: h = 8, d_k = d_v = d_model/h = 64 — p.5
```

### Encoder and decoder stacks (§3.1 · p.3; attention placements §3.2.3 · p.5)

```text
encoder layer (×N=6):                                # stack of N = 6 identical layers — §3.1 p.3
    x = LayerNorm(x + MultiHeadSelfAttn(x))          # sub-layer 1, residual + layer norm — §3.1 p.3
    x = LayerNorm(x + FFN(x))                        # sub-layer 2 — §3.1 p.3
decoder layer (×N=6):                                # §3.1 p.3
    y = LayerNorm(y + MaskedMultiHeadSelfAttn(y))    # no attending to later positions — §3.1 p.3
    y = LayerNorm(y + MultiHeadAttn(Q=y, K,V=enc))   # encoder-decoder attention — §3.2.3 p.5
    y = LayerNorm(y + FFN(y))
# all sub-layers and embeddings output d_model = 512 — §3.1 p.3
# output embeddings offset by one position (with the mask ⇒ auto-regressive) — §3.1 p.3
```

### Position-wise feed-forward network (§3.3 · p.5 · eq (2))

```text
FFN(x) = max(0, x W1 + b1) W2 + b2                   # two linear maps, ReLU between — §3.3 p.5
# applied identically at every position; d_model = 512 outside, d_ff = 2048 inside — §3.3 p.5
```

### Embeddings and output softmax (§3.4 · p.5)

```text
tokens → learned embeddings of dim d_model, multiplied by sqrt(d_model)     # §3.4 p.5
decoder output → shared linear + softmax → next-token probabilities         # §3.4 p.5
# one weight matrix shared by both embedding layers and the pre-softmax linear — §3.4 p.5
```

### Sinusoidal positional encoding (§3.5 · p.6)

```text
PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))        # §3.5 p.6
PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))        # §3.5 p.6
# added to the input embeddings at the bottoms of both stacks — §3.5 p.6
# learned positional embeddings performed near-identically (Table 3 row (E) p.9) — §3.5 p.6
```

### Learning-rate schedule (§5.3 · p.7 · eq (3))

```text
lrate = d_model^-0.5 · min(step^-0.5, step · warmup_steps^-1.5)   # §5.3 p.7
# linear warmup for warmup_steps = 4000, then inverse-sqrt decay — §5.3 p.7
```

## Authors' code

- https://github.com/tensorflow/tensor2tensor — stated in §7 Conclusion, p.10 ("The code we used to train and evaluate our models is available at…"). Commit/tag: none pinned by the paper. License: not stated in the paper — check the repository before reuse.

## Data

- WMT 2014 English–German · ~4.5M sentence pairs · byte-pair encoding, shared source–target vocabulary ~37,000 tokens (§5.1 p.7) · access: public WMT shared-task distribution ◆
- WMT 2014 English–French · 36M sentences · 32,000 word-piece vocabulary (§5.1 p.7) · access: public WMT shared-task distribution ◆
- Constituency parsing: WSJ portion of Penn Treebank, ~40K sentences, 16K vocab; semi-supervised ~17M sentences, 32K vocab (§6.3 p.9) · access: PTB is licensed (LDC) ◆

## Hyperparameters & training details

| item | value | source |
|---|---|---|
| layers N (encoder and decoder) | 6 | §3.1 p.3 |
| d_model | 512 | §3.1 p.3 |
| heads h | 8 | §3.2.2 p.5 |
| d_k = d_v | 64 (= d_model / h) | §3.2.2 p.5 |
| d_ff | 2048 | §3.3 p.5 |
| batch size | ≈25,000 source + 25,000 target tokens, length-bucketed | §5.1 p.7 |
| steps · wall clock | base 100K (~12 h, 0.4 s/step) · big 300K (3.5 d, 1.0 s/step) | §5.2 p.7 |
| hardware | 1 machine, 8 × NVIDIA P100 | §5.2 p.7 |
| optimizer | Adam, β1 = 0.9, β2 = 0.98, ε = 10⁻⁹ | §5.3 p.7 |
| lr schedule | eq (3), warmup_steps = 4000 | §5.3 p.7 |
| residual dropout P_drop | 0.1 base (applied to sub-layer outputs and to embedding+PE sums) | §5.4 p.7–8 |
| label smoothing ε_ls | 0.1 | §5.4 p.8 |
| big model | d_model 1024 · d_ff 4096 · h 16 · P_drop 0.3 · 300K steps · 213M params | Table 3 p.9 |
| big En–Fr exception | P_drop = 0.1 rather than 0.3 | §6.1 p.8 |
| checkpointing | average last 5 (base, 10-min interval) / last 20 (big) | §6.1 p.8 |
| inference | beam 4 · length penalty α = 0.6 · max output = input + 50, early stop | §6.1 p.8 |
| base params | 65M | Table 3 p.9 |
| parsing variant | 4 layers, d_model 1024; beam 21, α = 0.3, max output = input + 300 | §6.3 p.9–10 |

## Not stated by the paper

Each is a reproduction risk and a choice a reproducer must make explicitly:

- Weight initialization — no scheme, gain, or distribution given anywhere.
- Layer-norm ε and any pre/post details beyond the LayerNorm(x + Sublayer(x)) formula (§3.1 p.3).
- Attention-weight dropout — §6.3 (p.9) mentions selecting "attention and residual" dropout for parsing, but §5.4 defines only residual and embedding-sum dropout; where and at what rate dropout hits the attention weights in the translation models is not specified.
- BPE/word-piece pipeline details — merge-operation counts, tokenizer, preprocessing/casing, detokenization at eval.
- BLEU computation — script, tokenization, case handling are not stated.
- Gradient clipping — not mentioned either way.
- Random seeds — never stated; single-run results.
- Length-bucketing algorithm specifics for the ~25K-token batches (§5.1 p.7 gives only the budget).
- Parsing learning rates and the "small number of experiments" search space (§6.3 p.9).
