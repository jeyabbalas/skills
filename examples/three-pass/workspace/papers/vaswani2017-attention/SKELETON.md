# Skeleton — Attention Is All You Need
pages: 15 · pdf: paper.pdf

(arXiv:1706.03762v7, 2 Aug 2023; NeurIPS 2017 paper)

## Outline
- Title, abstract, author contributions — p.1
- 1 Introduction — p.2
- 2 Background — p.2
- 3 Model Architecture — p.2–6
  - 3.1 Encoder and Decoder Stacks — p.3
  - 3.2 Attention — p.3–5
    - 3.2.1 Scaled Dot-Product Attention — p.4
    - 3.2.2 Multi-Head Attention — p.4–5
    - 3.2.3 Applications of Attention in our Model — p.5
  - 3.3 Position-wise Feed-Forward Networks — p.5
  - 3.4 Embeddings and Softmax — p.5
  - 3.5 Positional Encoding — p.6
- 4 Why Self-Attention — p.6–7
- 5 Training — p.7–8
  - 5.1 Training Data and Batching — p.7
  - 5.2 Hardware and Schedule — p.7
  - 5.3 Optimizer — p.7
  - 5.4 Regularization — p.7–8
- 6 Results — p.8–10
  - 6.1 Machine Translation — p.8
  - 6.2 Model Variations — p.8–9
  - 6.3 English Constituency Parsing — p.9–10
- 7 Conclusion — p.10
- References [1]–[40] — p.10–12
- Attention Visualizations (unnumbered appendix) — p.13–15

## Figures & tables
- Figure 1 · p.3 · Transformer model architecture · bbox [186.0,66.0,424.0,400.0] (verified 2026-08-10)
- Figure 2 · p.4 · scaled dot-product + multi-head attention · bbox [144.0,70.0,468.0,243.0] (verified 2026-08-10)
- Table 1 · p.6 · complexity, path length by layer type · bbox [106.8,107.0,505.7,523.0] (band-fallback)
- Table 2 · p.8 · BLEU vs training cost, WMT 2014 · bbox [107.6,96.1,505.2,512.1] (band-fallback)
- Table 3 · p.9 · architecture-variation ablations, newstest2013 · bbox [107.5,117.9,505.2,533.9] (band-fallback)
- Table 4 · p.10 · constituency parsing, WSJ Section 23 · bbox [107.5,96.1,505.7,512.1] (band-fallback)
- Figure 3 · p.13 · long-distance dependency attention example · bbox [119.7,84.3,504.7,302.1] (matched-content)
- Figure 4 · p.14 · anaphora-resolution attention heads · bbox [122.0,217.1,503.7,604.0] (matched-content)
- Figure 5 · p.15 · sentence-structure head behaviour · bbox [120.8,231.6,499.4,543.4] (matched-content)

## Equations
- eq (1) · §3.2.1 · p.4 · scaled dot-product attention
- eq (2) · §3.3 · p.5 · position-wise feed-forward network
- eq (3) · §5.3 · p.7 · learning-rate schedule
- unnumbered · §3.2.2 · p.5 · multi-head attention (MultiHead, head_i)
- unnumbered · §3.5 · p.6 · sinusoidal positional encodings PE(pos,2i), PE(pos,2i+1)

## Key references
- [2] Bahdanau 2014 — attention for NMT; the additive-attention contrast in §3.2.1 · cited in §1, §2, §3.2.1, §3.2.3
- [35] Sutskever 2014 — the encoder-decoder sequence-to-sequence paradigm · cited in §1, §3
- [38] Wu 2016 (GNMT) — the recurrent NMT state of the art it beats; also word-piece vocab, beam settings · cited in §1, §5.1, §6.1
- [9] Gehring 2017 (ConvS2S) — convolutional rival; also source of learned positional embeddings · cited in §2, §3.5, §6.1
- [18] Kalchbrenner 2017 (ByteNet) — convolutional predecessor motivating the path-length argument · cited in §2, §4, §6.1
- [13] Hochreiter 1997 — LSTM, the recurrence being replaced · cited in §1
