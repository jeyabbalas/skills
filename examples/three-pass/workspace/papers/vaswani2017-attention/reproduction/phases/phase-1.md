# Phase 1 — Data: the registry-lookup toy dataset

## Objective

Generate the toy dataset the whole reproduction runs on: examples of 4 key–value records plus a query key, where the answer is the queried record's value. Deterministic, self-checking, and free of positional leaks.

## Paper grounding

- §3.2, p.3: "An attention function can be described as mapping a query and a set of key-value pairs to an output, where the query, keys, values, and output are all vectors." The dataset instantiates exactly that structure — a query, a set of key–value pairs, one right answer.
- §3.2.1, p.4 (context only): later phases will solve this task with scaled dot-product attention, eq (1). The data phase implements no equation.

## Recipe (restated in full from PLAN.md, which is authoritative)

- Universe: 10 key symbols `k0…k9`, 10 value symbols `v0…v9`.
- One example: sample 4 **distinct** keys and 4 **distinct** values; pair them by a uniform random bijection; list the 4 records in random order; pick the query uniformly from the 4 keys; target = the value paired with the query key.
- Schema (JSONL, one example per line, keys in this order):
  `{"pairs": [["k3","v7"],["k0","v2"],["k8","v5"],["k5","v9"]], "query": "k8", "target": "v5"}`
- Sizes: train 2048 · val 256 · test 512, generated as one stream from a single `random.Random(17)`, then split in that order (first 2048 train, next 256 val, last 512 test).
- The distinctness of values within an example is load-bearing: it makes the order-blind baseline's optimal accuracy exactly 25% (phase 3 relies on this).

## Inputs

None — this is the first phase.

## Deliverables

- `papers/vaswani2017-attention/reproduction/code/data.py` — Python 3, **stdlib only** (`random`, `json`, `argparse`, `pathlib`, `collections`). Running it with no arguments writes the three JSONL files; `--check` validates existing files and exits nonzero on any failure.
- `papers/vaswani2017-attention/reproduction/code/data/train.jsonl`, `val.jsonl`, `test.jsonl`.

## Acceptance checks (run from the workspace root; all must pass)

1. Generation: `python3 papers/vaswani2017-attention/reproduction/code/data.py` writes the three files; `wc -l` gives 2048 / 256 / 512.
2. Validity: `python3 papers/vaswani2017-attention/reproduction/code/data.py --check` exits 0, verifying for **every** line of all three files: exactly 4 pairs; 4 distinct keys; 4 distinct values; all symbols within `k0…k9` / `v0…v9`; `query` is one of the 4 keys; `target` equals the value paired with `query`.
3. Determinism: `--check` regenerates the full stream in memory from seed 17 and confirms it matches the files byte-for-byte (so a re-run can never silently produce different data).
4. Leak guards, printed by `--check` and asserted: over train, the queried record's slot index (0–3) has frequency in [0.20, 0.30] for every slot (position must not predict the answer), and every target value `v0…v9` has frequency in [0.06, 0.14] (no degenerate majority class — the trivial majority baseline stays ≈10%).

## Out of scope (later phases own these)

- Tensors, embeddings, or any model code (phase 2).
- Training, baselines, metrics (phase 3).
- Plots and attention inspection (phase 4).
- Do not add dependencies; do not touch other phases' specs or code.
