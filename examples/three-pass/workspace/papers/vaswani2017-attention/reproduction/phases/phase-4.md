# Phase 4 — See the weights: interpretability, measured

## Objective

Show the mechanism, not just the score: plot the attention rows, quantify that they land on the correct record, and demonstrate that with no positions injected the model is order-blind in the right way (weights follow shuffled records; predictions don't move).

## Paper grounding

- §4, p.7: "As side benefit, self-attention could yield more interpretable models. We inspect attention distributions from our models and present and discuss examples in the appendix." The appendix visualizations (Figures 3–5, pp.13–15) are the paper's qualitative evidence; this phase reproduces that *kind* of evidence in miniature — attention rows you can read.
- §3.5, p.6: positional encodings exist because attention alone has no notion of order. This build injects none — so record order must be immaterial. The shuffle test turns that motivation into a checkable prediction. ◆ Beyond the paper: the shuffle test itself is our construction.

## Inputs

- `papers/vaswani2017-attention/reproduction/code/data/test.jsonl` — phase 1.
- `papers/vaswani2017-attention/reproduction/code/attention.py`, `code/model.py` — phases 2–3.
- `papers/vaswani2017-attention/reproduction/code/results/model.pt` — the trained attention model from phase 3.

## Deliverables

- `papers/vaswani2017-attention/reproduction/code/inspect_attention.py` (`uv run --with torch --with matplotlib python … `):
  - Computes, over the full test set: `argmax_on_correct` (fraction of examples where the largest attention weight sits on the record holding the queried key) and `mean_mass_on_correct` (mean attention weight on that record).
  - Shuffle test: for every test example, apply a random permutation to the 4 records; assert the predicted value is identical pre/post for every example, and count how often the argmax weight moves *with* the correct record.
  - Renders `code/results/attn-examples.png`: 8 test examples, each drawn as a 1×4 weight row (grayscale or single-hue cells with the numeric weight printed in each cell), records labeled with their `key:value` symbols, the query printed above, the correct record outlined.
- `papers/vaswani2017-attention/reproduction/code/results/attn-metrics.json` — the three metrics plus test-set size.
- `papers/vaswani2017-attention/reproduction/code/results/results.md` — half a page: the metrics table, the image inlined, two sentences on what the weights show.

## Acceptance checks (all must pass)

1. `uv run --with torch --with matplotlib python papers/vaswani2017-attention/reproduction/code/inspect_attention.py` exits 0 on CPU.
2. `argmax_on_correct ≥ 0.90` over the 512 test examples.
3. `mean_mass_on_correct ≥ 0.80`.
4. Shuffle test: predictions identical for **all** test examples after record permutation, and argmax-follows-the-record ≥ 0.90.
5. `attn-examples.png` exists, shows 8 examples with labeled records and visibly concentrated weights; `results.md` embeds it and the metrics.

## Out of scope

- Retraining or touching any code from phases 1–3 (load `model.pt` as-is; if it is missing, stop and report — do not retrain).
- Multi-head attention, positional encodings, flat-token variants — growth paths beyond this plan.
- The reader-facing walkthrough page (`walkthrough.md`) — built later, together, outside the phases.
