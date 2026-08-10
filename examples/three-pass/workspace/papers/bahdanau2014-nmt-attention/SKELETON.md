# Skeleton — Neural Machine Translation by Jointly Learning to Align and Translate
pages: 15 · pdf: paper.pdf

## Outline
- 1 Introduction — p.1–2
- 2 Background: Neural Machine Translation — p.2–3
  - 2.1 RNN Encoder–Decoder — p.2–3
- 3 Learning to Align and Translate — p.3–4
  - 3.1 Decoder: General Description — p.3–4
  - 3.2 Encoder: Bidirectional RNN for Annotating Sequences — p.4
- 4 Experiment Settings — p.4–5
  - 4.1 Dataset — p.4–5
  - 4.2 Models — p.5
- 5 Results — p.5–8
  - 5.1 Quantitative Results — p.5–6
  - 5.2 Qualitative Analysis — p.7–8
    - 5.2.1 Alignment — p.7
    - 5.2.2 Long Sentences — p.7–8
- 6 Related Work — p.8–9
  - 6.1 Learning to Align — p.8
  - 6.2 Neural Networks for Machine Translation — p.9
- 7 Conclusion — p.9
- Acknowledgments · References — p.10–11
- A Model Architecture — p.12–14
  - A.1 Architectural Choices — p.12 (A.1.1 RNN; A.1.2 Alignment Model)
  - A.2 Detailed Description of the Model — p.13–14 (A.2.1 Encoder p.13; A.2.2 Decoder p.13–14; A.2.3 Model Size p.14)
- B Training Procedure — p.14–15
  - B.1 Parameter Initialization — p.14
  - B.2 Training — p.14–15
- C Translations of Long Sentences — p.15

## Figures & tables
- Figure 1 · p.3 · model generating t-th target word · bbox [387.4,365.7,501.8,496.8] (matched-content)
- Figure 2 · p.5 · BLEU vs sentence length, four models · bbox [108.0,30.0,504.0,112.8] (band-fallback)
- Figure 3 · p.6 · four sample alignment weight matrices · bbox [108.0,122.9,504.0,506.0] (matched-content)
- Table 1 · p.7 · BLEU scores, all vs no-UNK · bbox [108.0,198.0,504.0,614.0] (band-fallback — table sits top-left beside its caption; verify before crop)
- Table 2 · p.14 · training statistics per model · bbox [108.0,208.2,504.0,624.2] (band-fallback)
- Table 3 · p.15 · long-sentence translations compared · bbox [108.0,728.7,520.4,762.0] (band-fallback — caption above full-page table; verify)

## Equations
- eq (1) · §2.1 · p.2 · RNN hidden state; sentence vector c from hidden states
- eq (2) · §2.1 · p.3 · translation probability as ordered conditionals
- eq (3) · §2.1 · p.3 · RNN form of each conditional, fixed context c
- eq (4) · §3.1 · p.3 · conditional with a distinct context vector c_i per target word
- eq (5) · §3.1 · p.3 · context vector as weighted sum of annotations
- eq (6) · §3.1 · p.3 · attention weights: softmax over alignment scores e_ij
- eq (7) · §A.2.1 · p.13 · annotation = forward and backward states concatenated
- unnumbered · §A.1.2 · p.12 · the alignment model a: single-layer MLP scoring (s_i-1, h_j)
- §A.1–A.2, B · p.12–14 · remaining display equations (gated unit, deep output) are unnumbered

## Key references
(the paper cites author–year, no bracket numbers)
- Cho et al. 2014a — RNN Encoder–Decoder: the framework extended here and the RNNencdec baseline; also source of the gated hidden unit · cited in §1, §2.1, §4, §A.1.1
- Sutskever et al. 2014 — LSTM seq2seq; co-definer of the encoder–decoder family, near-SOTA on En→Fr · cited in §1, §2, §2.1
- Cho et al. 2014b — evidence that the basic encoder–decoder deteriorates on long sentences — the motivating problem · cited in §1, §7
- Kalchbrenner & Blunsom 2013 — early single-network neural translation model · cited in §1, §2, §6.2
- Graves 2013 — closest prior for learned alignment (handwriting synthesis), but monotonic-only · cited in §6.1
- Schuster & Paliwal 1997 — the bidirectional RNN used as the encoder · cited in §3.2
- Koehn et al. 2003 / Koehn 2010 — the phrase-based SMT system (Moses) the model is measured against · cited in §1, §5.1
