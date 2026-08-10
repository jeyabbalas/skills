# Attention Is All You Need — paper profile

**Paper type**: empirical — proposes a new architecture and validates it on machine-translation and parsing benchmarks (Abstract p.1; §6 p.8–10)
**In brief**: Introduces the Transformer, the first sequence-to-sequence model built entirely on attention — no recurrence, no convolutions. It beats the state of the art on two WMT 2014 translation benchmarks while training in a fraction of the time, and generalizes to English constituency parsing. (Abstract p.1; §7 p.10)

## Title, decoded

- **Attention** — the paper's core operation: "mapping a query and a set of key-value pairs to an output", where "the output is computed as a weighted sum of the values" and each weight comes from how compatible the query is with that value's key (§3.2, p.3–4).
- **Is All You Need** — the claim: the "complex recurrent or convolutional neural networks" that dominated sequence modeling can be dispensed with "entirely"; attention alone carries the model (Abstract p.1; §1 p.2).

> ◆ **Beyond the paper · Personal** — Bridge from your world: attention is close in spirit to kernel smoothing (Nadaraya–Watson): predict for a point by taking a weighted average of other points' values, weights set by similarity. Here the "similarity" is learned, and everything is vectors — but "data-dependent weighted average" is the right first mental model, before any neural-network machinery.

## Abstract, unpacked

- Dominant sequence transduction (sequence-to-sequence) models are "complex recurrent or convolutional neural networks" with an encoder and a decoder; the best also connect the two through attention. (p.1)
- Proposes the Transformer, "based solely on attention mechanisms, dispensing with recurrence and convolutions entirely". (p.1)
- On two machine-translation tasks: superior quality, more parallelizable, "significantly less time to train". (p.1)
- WMT 2014 English→German: 28.4 BLEU, over 2 BLEU above the previous best including ensembles. (p.1)
- WMT 2014 English→French: 41.8 BLEU, a new single-model state of the art, after 3.5 days on eight GPUs — "a small fraction of the training costs of the best models". (p.1)
- Also generalizes to English constituency parsing, with large and limited training data. (p.1)

## Outline

- [1 Introduction](summary.html#sec-1) — RNNs are state of the art but inherently sequential; the Transformer drops recurrence for attention (p.2)
- [2 Background](summary.html#sec-2) — convolutional attempts (ByteNet, ConvS2S) and self-attention precedents (p.2)
- [3 Model Architecture](summary.html#sec-3) — encoder-decoder stacks; attention (scaled dot-product, multi-head, its three uses); feed-forward layers; embeddings; positional encoding (p.2–6)
- [4 Why Self-Attention](summary.html#sec-4) — complexity, parallelism, and path-length comparison vs recurrent and convolutional layers (p.6–7)
- [5 Training](summary.html#sec-5) — data, hardware, Adam schedule, regularization (p.7–8)
- [6 Results](summary.html#sec-6) — translation records, ablations, parsing transfer (p.8–10)
- [7 Conclusion](summary.html#sec-7) — first all-attention transduction model; future directions (p.10)
- [Appendix: Attention Visualizations](summary.html#sec-appendix) — example attention patterns (p.13–15)

## Problem & background

Recurrent sequence models compute a hidden state \(h_t\) from \(h_{t-1}\), so computation cannot be parallelized within a training example — "critical at longer sequence lengths" (§1, p.2). Attention already let models relate positions "without regard to their distance", but was almost always bolted onto a recurrent network (§1, p.2). Background an outsider needs: sequence transduction = mapping an input sequence to an output sequence (e.g. translation); the standard shape is an encoder (input → continuous representations) and an auto-regressive decoder (one output symbol at a time, feeding on its own previous outputs) (§3, p.2).

## Authors

- Ashish Vaswani (first listed) — Google Brain (p.1); PhD in computer science at the University of Southern California, previously at USC's Information Sciences Institute; later co-founded Adept AI and Essential AI ([source](https://en.wikipedia.org/wiki/Ashish_Vaswani))
- Illia Polosukhin (last listed) — engineering manager at Google Research at the time (p.1, mark ‡); left to co-found NEAR (initially Near.ai, a program-synthesis startup) in 2017 ([source](https://en.wikipedia.org/wiki/Illia_Polosukhin))
- The paper states: "Equal contribution. Listing order is random." (p.1, footnote)

> ◆ **Beyond the paper · Personal** — So unlike author lists in epidemiology, first/last position here signals nothing about seniority or contribution.

## Related work that matters

- Bahdanau 2014 [2] — introduced attention in neural machine translation (jointly with an RNN), letting models link positions regardless of distance; the Transformer keeps the attention and drops the RNN, and its "additive attention" is the contrast case for scaled dot-product attention. (§1 p.2; §3.2.1 p.4)
- Sutskever 2014 [35] — RNN encoder-decoder sequence-to-sequence learning; the paradigm whose overall shape the Transformer inherits. (§1 p.2; §3 p.2)
- Wu 2016 (GNMT) [38] — Google's recurrent translation system, the strongest recurrent baseline in Table 2; also the source of the word-piece vocabulary and beam-search settings used here. (§5.1 p.7; §6.1 p.8)
- Gehring 2017 (ConvS2S) [9] — convolutional sequence-to-sequence model: parallel like the Transformer, but relating two positions costs a number of operations growing linearly with their distance. (§2 p.2)
- Kalchbrenner 2017 (ByteNet) [18] — convolutional predecessor where that cost grows logarithmically; both motivate the Transformer's constant number of operations between any two positions. (§2 p.2)

## Hypothesis & claims

The authors propose that recurrence is unnecessary: an architecture "relying entirely on an attention mechanism to draw global dependencies between input and output" can beat recurrent and convolutional encoder-decoders while parallelizing far better (§1, p.2). The key design bets: short, constant-length paths between any pair of positions make long-range dependencies easier to learn (§4, Table 1, p.6), and multi-head attention counteracts the "reduced effective resolution" that plain attention averaging causes (§2, p.2).

## Main results

The big Transformer sets a new WMT 2014 English→German state of the art at 28.4 BLEU, over 2.0 BLEU above all previous models including ensembles, and reaches 41.8 BLEU on English→French (Table 2) at less than 1/4 the training cost of the previous best single model; even the base model beats all previously published models at a fraction of the cost (§6.1, Table 2, p.8). A 4-layer Transformer also reaches 92.7 F1 on WSJ constituency parsing (semi-supervised), above all previously reported models except one (§6.3, Table 4, p.9–10).

> ◆ **Beyond the paper · Critique** — Small internal inconsistency: §6.1's prose reports the English→French big model at "a BLEU score of 41.0" (p.8), while the abstract (p.1) and Table 2 (p.8) both say 41.8.

## Conclusions

The Transformer is "the first sequence transduction model based entirely on attention"; for translation it trains "significantly faster than architectures based on recurrent or convolutional layers" and sets a new state of the art on both WMT 2014 tasks (§7, p.10). The authors plan to extend it to other modalities (images, audio, video), investigate local restricted attention, and make generation less sequential; code is at github.com/tensorflow/tensor2tensor (§7, p.10).
