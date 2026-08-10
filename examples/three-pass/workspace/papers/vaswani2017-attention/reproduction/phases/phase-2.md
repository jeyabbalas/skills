# Phase 2 — Attention core: eq (1) by hand, unit-tested

## Objective

Hand-write scaled dot-product attention exactly as the paper defines it, plus the record embedder both phase-3 models will share. No training here — correctness by unit test.

## Paper grounding

- §3.2.1, p.4, eq (1): Attention(Q, K, V) = softmax(QKᵀ / √d_k) V. Pipeline per the paper: dot products of the query with all keys → divide each by √d_k → softmax → weights on the values → weighted sum of values (§3.2, p.3–4).
- Footnote 4, p.4: for independent mean-0 variance-1 components, q·k has mean 0 and variance d_k — the reason the scale exists. The test suite must fail if the √d_k division is dropped.
- §3.2.2, p.4–5 (context only): the paper wraps this in h=8 projected heads; this build uses a single head with learned projections W_Q, W_K, W_V — the projections are the per-head projections of §3.2.2 with h=1.

## Inputs

- The data schema from `papers/vaswani2017-attention/reproduction/phases/phase-1.md` (4 records of [key, value] symbols `k0…k9`/`v0…v9`, plus a query key). Files under `reproduction/code/data/` exist but are not needed for the tests.

## Deliverables

`papers/vaswani2017-attention/reproduction/code/attention.py` (PyTorch; run tests via `uv run --with torch python …/attention.py --test`):

- `scaled_dot_product_attention(Q, K, V) -> (output, weights)` — the eq (1) forward, written out (matmul, divide by √d_k, softmax, matmul); returns the weights too, phase 4 depends on that. Never call `torch.nn.functional.scaled_dot_product_attention` or `nn.MultiheadAttention`.
- `RecordEmbedder(d=32)` — maps one example dict to `(S, q)`: record embeddings `S ∈ R^{4×32}` with `S_i = E_key[key_i] + E_val[value_i]`, and query embedding `q = E_key[query] ∈ R^{32}`. Two embedding tables (10 keys, 10 values). Both phase-3 models must share this module unchanged.

## Acceptance checks (all must pass; `uv run --with torch python papers/vaswani2017-attention/reproduction/code/attention.py --test` exits 0)

1. Shapes: Q `(n_q, d_k)`, K `(m, d_k)`, V `(m, d_v)` → output `(n_q, d_v)`, weights `(n_q, m)`; batched leading dims pass through.
2. Weights are a distribution: nonnegative, each row sums to 1 (tol 1e-6).
3. Convexity: output rows equal `weights @ V` exactly — verified against a manual softmax computed with plain `torch.exp` in the test.
4. Hand-computed case, exact to 1e-6: `Q=[[1,0]]`, `K=[[1,0],[0,1]]`, `V=[[10,0],[0,10]]`, d_k=2 → scores `[0.7071067811865475, 0.0]`, weights `[0.6697615493266569, 0.3302384506733431]`, output `[6.697615493266569, 3.302384506733431]`.
5. Scale guard: the same case computed *without* the √d_k division gives first weight `0.7310585786300049`; the test asserts the implementation does **not** produce that value (a dropped scale fails loudly).
6. Embedder: `RecordEmbedder(d=32)` on the schema example from phase 1 returns shapes `(4, 32)` and `(32,)`; two records sharing a key but not a value embed differently, and additivity holds: `S_i == E_key[key_i] + E_val[value_i]` (tol 1e-6).

## Out of scope (later phases own these)

- Classification head, baseline, training loop (phase 3).
- Plots, interpretability metrics (phase 4).
- Multi-head attention and positional encodings — recorded growth paths, not in this build.
- Do not touch other phases' specs or code; do not modify `data.py` or the data files.
