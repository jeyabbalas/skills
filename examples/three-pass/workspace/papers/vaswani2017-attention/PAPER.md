# Attention Is All You Need

```bibtex
@inproceedings{vaswani2017-attention,
  author    = {Ashish Vaswani and Noam Shazeer and Niki Parmar and
               Jakob Uszkoreit and Llion Jones and Aidan N. Gomez and
               Lukasz Kaiser and Illia Polosukhin},
  title     = {Attention is All you Need},
  booktitle = {Advances in Neural Information Processing Systems 30:
               Annual Conference on Neural Information Processing Systems 2017,
               December 4-9, 2017, Long Beach, CA, {USA}},
  pages     = {5998--6008},
  year      = {2017},
  url       = {https://proceedings.neurips.cc/paper/2017/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html}
}
```

status: pass-3
track: minimal
added: 2026-08-10
source: provided by reader (local PDF) · BibTeX from [DBLP](https://dblp.org/rec/conf/nips/VaswaniSPUJGKP17.bib)

## Goal
> "I keep hearing transformers could apply to my registry data. I want to actually understand attention — what it computes and why it works — well enough to judge whether it fits my problems."

## Session log
- 2026-08-10 · pass 1 · workspace bootstrapped; paper registered; skeleton cached; profile built and presented; gate: reader says yes to pass 2, starting next session · next: pass 2 — summary §1 Introduction, then §3.2 Attention (the reader's goal)
- 2026-08-10 · pass 2 · reader extended the budget: summary §1 + §3 preamble + §3.2 (all three subsections); fig-01 + fig-02 pages, crops tightened and visually verified (SKELETON bboxes updated); eq (1) page; glossary started, 6 terms; notes N0001 (insight: weights computed not fitted), N0002 (todo: verify footnote-4 variance), N0003 (critique: §3.5 sinusoid pin); §4 untouched so Table 1 deferred per reader's own condition · next: pass 2 — summary §4 Why Self-Attention with the Table 1 page, then §3.5 Positional Encoding (N0003 pin waiting)
- 2026-08-10 · pass 1 · relationship map built with bahdanau2014-nmt-attention (map.md; this paper's profile embedded as a map panel; edge iterated to "keeps attention, drops RNN") · next: unchanged — pass 2 summary §4 Why Self-Attention with the Table 1 page, then §3.5 Positional Encoding (N0003 pin waiting)
- 2026-08-10 · pass 2 · reader redirect: hand-added note formalized as N0004 (question — QK^T as kernel matrix, per-head kernels; reader's wording preserved verbatim) and notes page re-rendered; summary §3 note-links line extended with N0004; references unit built (references.md/.html — 6 key references grounded in citing sections, reference map with per-reference cards); kernel question answered ◆ in chat only, note left open · next: pass 2 — summary §4 Why Self-Attention with the Table 1 page, then §3.5 Positional Encoding (N0003 pin waiting; N0004 kernel question open)
- 2026-08-10 · pass 3 · reader redirect at open: one-off jump from mid-pass-2 to derive N0002's target; deriv-01-sqrt-dk-scaling complete (ledger A1–A3 — init-time caveat on independence/unit variance recorded; fn-4 mean-0/variance-d_k derived reader-driven; √d_k = z-score); paper's "extremely small gradients" link (§3.2.1 body, "We suspect") left underived → open gap N0005; N0002 closed — deriv-01; summary §3 links refreshed · next: pass 2 — summary §4 Why Self-Attention with the Table 1 page, then §3.5 Positional Encoding (N0003 pin waiting; N0004 kernel question open; N0005 softmax-gradient gap open)
- 2026-08-10 · pass 3 · reader redirect: reproduction setup, budget extended at reader's request (inventory + plan); INVENTORY.md built (7 algorithms pseudocoded, tensor2tensor §7 p.10, 9 unstated-detail risks); track: minimal recorded; toy data co-designed — registry lookup, distinct keys/values, uniform-weight twin gives provable 25% ceiling, interpretability metrics specified; PLAN.md + phases/phase-1..4.md + prompts/phase-1-prompt.md written; reader will run phase 1 in a fresh session · next: pass 3 — phase 1 via prompts/phase-1-prompt.md (fresh session), then phase 2; here, resume from PLAN.md status column (pass-2 §4 + §3.5 still pending; N0003, N0004, N0005 open)
- 2026-08-10 · pass 3 · phase 1: data generator + fixtures built, checks green · next: phase 2 (spec: reproduction/phases/phase-2.md)
