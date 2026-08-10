# Neural Machine Translation by Jointly Learning to Align and Translate — paper profile

**Paper type**: empirical — proposes a model extension and validates it on WMT '14 English-to-French translation (Abstract p.1; §4–5 p.4–8)
**In brief**: Adds a learned soft-search — the mechanism soon named attention — to the RNN encoder–decoder: instead of decoding from one fixed-length sentence vector, the decoder builds, for every output word, a weighted average over per-word source annotations, with weights from a jointly trained alignment network. This removes the collapse on long sentences and reaches quality comparable to the phrase-based state of the art. (Abstract p.1; §3 p.3–4; §5 p.5–8)

## Title, decoded

- **Neural Machine Translation** — translating with "a single, large neural network that reads a sentence and outputs a correct translation", trained end to end — versus the then-dominant phrase-based systems built of "many small sub-components that are tuned separately" (§1, p.1).
- **Jointly Learning** — the alignment part is not a separate pipeline stage: it is a small feedforward network "jointly trained with all the other components", possible because the soft alignment lets gradients flow through it (§3.1, p.3–4).
- **to Align and Translate** — align = decide, for the word being produced, which source words matter right now (the weights); translate = produce the word. One model does both simultaneously (§3.1, p.3–4; §5.2.1, p.7).

> ◆ **Beyond the paper · Personal** — This is the paper where your "weighted averaging where the weights are computed on the fly" picture enters translation: eq. (5) is exactly a Nadaraya–Watson-style weighted mean of source-word summaries, and eq. (6)'s weights are recomputed for every output word from a learned score — no fixed kernel, no fixed bandwidth.

## Abstract, unpacked

- Neural machine translation builds "a single neural network that can be jointly tuned to maximize the translation performance", unlike traditional statistical MT. (p.1)
- Recent NMT models are encoder–decoders that "encode a source sentence into a fixed-length vector from which a decoder generates a translation". (p.1)
- Conjecture: "the use of a fixed-length vector is a bottleneck" for this architecture. (p.1)
- Proposal: let the model "automatically (soft-)search for parts of a source sentence that are relevant to predicting a target word", with no explicit hard segmentation. (p.1)
- Result: translation "comparable to the existing state-of-the-art phrase-based system" on English-to-French. (p.1)
- The learned (soft-)alignments "agree well with our intuition". (p.1)

## Outline

- 1 Introduction — the fixed-length-vector bottleneck; the proposed joint align-and-translate fix (p.1–2)
- 2 Background: Neural Machine Translation — translation as probability maximization; the RNN Encoder–Decoder being extended (p.2–3)
- 3 Learning to Align and Translate — the new decoder (per-word context vectors, softmax weights) and the bidirectional-RNN encoder (p.3–4)
- 4 Experiment Settings — WMT '14 En→Fr; RNNencdec vs RNNsearch, trained at lengths 30 and 50 (p.4–5)
- 5 Results — BLEU vs baseline and Moses; alignment visualizations; long-sentence behavior (p.5–8)
- 6 Related Work — Graves's monotonic alignment; neural add-ons to statistical MT (p.8–9)
- 7 Conclusion — soft-search fixes the bottleneck; comparable to phrase-based SMT (p.9)
- A–C Appendices — gated units, the alignment MLP, full architecture, training procedure, long-sentence samples (p.12–15)

## Problem & background

An encoder–decoder "needs to be able to compress all the necessary information of a source sentence into a fixed-length vector", which makes long sentences hard — especially ones longer than those in training — and prior work showed performance "deteriorates rapidly" as input length grows (§1, p.1). Background an outsider needs: translation is choosing the target sentence maximizing \(p(\mathbf{y} \mid \mathbf{x})\); an encoder RNN reads the source into hidden states, and a decoder RNN emits the translation one word at a time, conditioned on the words it already produced (§2–2.1, p.2–3).

## Authors

- Dzmitry Bahdanau (first) — then at Jacobs University Bremen, Germany (p.1); later PhD at Mila under Yoshua Bengio; credits the ICLR 2015 paper with inventing "the content-based neural attention" now core to NLP; today research scientist at Element AI (acquired by ServiceNow), core industry member of Mila, adjunct professor at McGill ([source](https://rizar.github.io/))
- Yoshua Bengio (last) — professor, Université de Montréal; founder of Mila and its scientific director until 2025; co-director of CIFAR's Learning in Machines & Brains program — the paper marks him "CIFAR Senior Fellow" (p.1, footnote); introduced the neural probabilistic language model; 2018 Turing Award with Hinton and LeCun ([source](https://en.wikipedia.org/wiki/Yoshua_Bengio))

## Related work that matters

(The paper cites author–year, with no bracket numbers.)

- Cho et al. 2014a — the RNN Encoder–Decoder this paper extends; also supplies the RNNencdec baseline and the gated hidden unit used in both models. (§1 p.1; §2.1 p.2; §4 p.4)
- Sutskever et al. 2014 — the LSTM sequence-to-sequence model, the other pillar of the encoder–decoder family, near phrase-based-level on En→Fr. (§1 p.1; §2 p.2)
- Cho et al. 2014b — the motivating evidence: a basic encoder–decoder's performance "deteriorates rapidly" as sentence length grows. (§1 p.1; §7 p.9)
- Graves 2013 — closest prior for learned alignment (handwriting synthesis), but its alignment moves only monotonically — a "severe limitation" for translation, where reordering is needed. (§6.1 p.8)
- Koehn et al. 2003 — the phrase-based statistical MT tradition (Moses) that sets the bar the model is measured against. (§1 p.1; §5.1 p.5)

## Hypothesis & claims

The conjecture: the single fixed-length vector is the bottleneck (Abstract p.1). The proposal: encode the source with a bidirectional RNN into one annotation per word, and have the decoder form a fresh context vector for every output word — a weighted sum whose weights come from a jointly trained feedforward alignment model — which "implements a mechanism of attention in the decoder" (§3.1–3.2, p.3–4). Claims: this beats the basic encoder–decoder at every sentence length, most visibly on long sentences, and reaches phrase-based-comparable quality with a single model (§1, p.2). A stated design assumption: each annotation carries the whole sentence but with "a strong focus on the parts surrounding" its word (§3.1, p.3).

## Main results

RNNsearch outperforms RNNencdec in every configuration; the long-trained RNNsearch-50⋆ reaches 28.45 BLEU on the full test set vs 33.30 for Moses — and on sentences without unknown words it scores 36.15, above Moses's 35.63 (Table 1, p.7; §5.1 p.5). RNNsearch-50 shows "no performance deterioration even with sentences of length 50 or more", while RNNencdec drops sharply with length (Fig. 2, §5.1, p.5–6). The learned weight matrices show largely monotonic, linguistically plausible alignments that handle reordering, e.g. [zone] ↔ [Area] (§5.2.1, Fig. 3, p.6–7).

## Conclusions

The fixed-length vector is problematic for long sentences; letting the model (soft-)search the source while generating each target word fixes this, with every part — alignment included — trained jointly (§7, p.9). Reaching quality comparable to phrase-based SMT is "a striking result" for an approach the authors note "has only been proposed as recently as this year"; the challenge left is rare and unknown words (§7, p.9).

> ◆ **Beyond the paper · Context** — For your goal — attention before Vaswani dropped the recurrence: here attention lives *inside* a recurrent model. The thing asking is the decoder RNN's previous state \(s_{i-1}\); the things attended to are BiRNN annotations \(h_j\) (playing both the key and value roles, undivided); the score is a small feedforward net (Appendix A.1.2, p.12) — the "additive attention" that Vaswani et al. later name and contrast with their scaled dot product (their §3.2.1). What the Transformer keeps: softmax-weighted averaging of vectors. What it drops: the RNNs that produce \(s\) and \(h\). See [Attention Is All You Need — profile](../vaswani2017-attention/profile.md).
