# Reproduction plan — Attention Is All You Need
goal: "I keep hearing transformers could apply to my registry data. I want to actually understand attention — what it computes and why it works — well enough to judge whether it fits my problems." · track: minimal
toy data: registry-lookup (4 key–value records + query → the paired value) · train 2048 / val 256 / test 512 · data seed 17, train seed 42 — full recipe below (authoritative)

## Toy data recipe (authoritative)

- **Universe**: 10 key symbols `k0…k9`, 10 value symbols `v0…v9`.
- **One example**: sample 4 *distinct* keys and 4 *distinct* values; pair them by a uniform random bijection; list the 4 records in random order; pick the query uniformly from the 4 keys; target = the value paired with the query key.
- **Schema** (JSONL, one example per line):
  `{"pairs": [["k3","v7"],["k0","v2"],["k8","v5"],["k5","v9"]], "query": "k8", "target": "v5"}`
- **Sizes**: train 2048 · val 256 · test 512, generated as one stream then split in that order.
- **Seeds**: data seed **17** (single `random.Random(17)` stream); model init + training seed **42**.
- **Why sufficient**: retrieval-by-content is exactly what eq (1) computes — a query scored against keys, weights on values (§3.2, p.3–4). Success is visible two ways: (a) an order/binding-blind pooled model has Bayes-optimal accuracy **exactly 25%** (conditioned on key-set, value-set, and query, the pairing is a uniform bijection), while attention can reach ~100%; (b) each example's attention is one row of 4 weights — small enough to plot and score for landing on the correct record.

## Phases

| # | phase | objective (one line) | deliverable | status | spec |
|---|---|---|---|---|---|
| 1 | Data | Generate the registry-lookup dataset per the recipe, with self-checks and leak guards | code/data.py + code/data/*.jsonl | done 2026-08-10 | phases/phase-1.md |
| 2 | Attention core | Hand-write eq (1) and the shared record embedder; unit-test against hand-computed values | code/attention.py (+ built-in tests) | not started | phases/phase-2.md |
| 3 | Train & compare | Train attention model vs uniform-weight twin; demonstrate the provable gap | code/model.py, code/train.py, code/results/metrics.json + model.pt | not started | phases/phase-3.md |
| 4 | See the weights | Heatmaps + interpretability metrics + record-shuffle invariance test | code/inspect_attention.py, code/results/attn-*.png/json, results.md | not started | phases/phase-4.md |

After phase 4: the walkthrough (`walkthrough.md`, built together back in this workspace) — not a phase.

## Decisions so far

- Records are composite slots (key-embed + value-embed summed), not a flat token sequence — isolates content-based retrieval; the flat-sequence + positional-encoding variant is a growth path, not in scope (plan).
- Baseline = the identical architecture with attention weights frozen at uniform ¼ — the only difference is eq (1)'s computed weights; gives the provable 25% ceiling (plan).
- Keys and values drawn *distinct within an example* so the 25% ceiling is exact (plan).
- Single head, no FFN/LayerNorm/stacking; multi-head (§3.2.2) and positional encoding (§3.5) are growth paths (plan).
- PyTorch for phases 2–4, autograd only — the attention forward is hand-written from eq (1), never `nn.MultiheadAttention`; phase 1 is stdlib-only (plan).
- Fixed Adam lr 1e-3; the paper's eq (3) warmup schedule is not reproduced at toy scale (plan).
- Byte-level determinism pinned in data.py: fixed per-example rng draw order (sample keys, sample values, shuffle values = the bijection, shuffle records, choose query) and a shared line renderer reproducing the phase-1 schema example byte-for-byte; --check regenerates from seed 17 and compares bytes (phase 1)
