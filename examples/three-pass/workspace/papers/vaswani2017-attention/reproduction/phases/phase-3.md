# Phase 3 — Train & compare: computed weights vs frozen weights

## Objective

Train two models that differ in exactly one thing — whether the weighted sum's weights are computed by eq (1) or frozen at uniform ¼ — and demonstrate the gap: attention near-perfect, the frozen twin pinned at its provable 25% ceiling.

## Paper grounding

- §3.2, p.3–4: "The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query with the corresponding key." The experiment isolates the clause "computed by a compatibility function": the baseline keeps the weighted sum and deletes only the computing.
- §3.2.1, p.4, eq (1): the attention model's weights.
- ◆ Beyond the paper: the uniform-weight twin and the 25% ceiling are ours, constructed for the contrast. Ceiling argument: mean-pooling additive record embeddings yields a function of only (key multiset, value multiset, query); conditioned on those, the generator's pairing is a uniform bijection, so the target is uniform over the 4 (distinct) present values → no such model exceeds 25% expected accuracy.

## Inputs

- `papers/vaswani2017-attention/reproduction/code/data/{train,val,test}.jsonl` — phase 1 (schema: `{"pairs": [["k3","v7"],…×4], "query": "k8", "target": "v5"}`, keys `k0…k9`, values `v0…v9`).
- `papers/vaswani2017-attention/reproduction/code/attention.py` — phase 2 (`scaled_dot_product_attention`, `RecordEmbedder(d=32)`).

## Deliverables

- `papers/vaswani2017-attention/reproduction/code/model.py`:
  - `AttentionLookup`: shared `RecordEmbedder(d=32)`; learned `W_Q, W_K, W_V` (32×32); `output, weights = scaled_dot_product_attention(q W_Q, S W_K, S W_V)`; logits over the 10 values via one linear layer on the output. Must expose the attention weights on the forward pass (phase 4 reads them).
  - `UniformPoolBaseline`: the *same* `RecordEmbedder`; pooled = mean(S, over the 4 records); logits = MLP([pooled ; q], one hidden layer of 64, ReLU). No attention anywhere.
- `papers/vaswani2017-attention/reproduction/code/train.py`: trains both models identically — Adam lr 1e-3, batch 64, up to 3000 steps, early stop when val accuracy ≥ 0.99, seed 42 (`torch.manual_seed`, and Python-level shuffling seeded 42) — then evaluates on test, prints a comparison table with both parameter counts, and writes results.
- `papers/vaswani2017-attention/reproduction/code/results/metrics.json` — at least: `attention_test_acc`, `baseline_test_acc`, `order_blind_ceiling: 0.25`, `steps_run` per model, `seed: 42`.
- `papers/vaswani2017-attention/reproduction/code/results/model.pt` — the trained `AttentionLookup` state dict (phase 4 loads it).

## Acceptance checks (all must pass)

1. `uv run --with torch python papers/vaswani2017-attention/reproduction/code/train.py` completes on CPU in under 5 minutes and exits 0.
2. Printed and in `metrics.json`: attention test accuracy ≥ **0.95**.
3. Printed and in `metrics.json`: baseline test accuracy ≤ **0.35** (analytic ceiling 0.25; slack for finite-sample wiggle), and the printed table shows the 0.25 ceiling beside it.
4. `results/model.pt` exists and reloads: rerunning evaluation from the checkpoint reproduces the attention test accuracy to ±0.001.
5. Both models trained with the identical budget and seed — asserted in code (same step cap, same optimizer settings), and parameter counts printed so the reader can see the baseline is not starved.

## Out of scope (other phases own these)

- Changing the data or its generator (phase 1) or `attention.py` (phase 2).
- Plots, heatmaps, weight inspection beyond exposing them (phase 4).
- Hyperparameter search — the values above are fixed by PLAN.md; if a check fails, fix bugs, don't tune.
