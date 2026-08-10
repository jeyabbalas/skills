# Attention Is All You Need — key references

What this paper leans on, and why. The six works below come from the key-references list cached in SKELETON.md; every "what it is" and "why it matters" statement is grounded in where this paper cites the work (§/p.). Full citations are transcribed verbatim from the paper's reference list (p.10–12). Reading any of these in full is its own pass-1 — a new paper for the library.

## The references that matter

The paper's story runs through three groups: the **recurrent lineage it replaces** ([13], [35], [38]), the **attention it keeps** ([2]), and the **convolutional rivals it out-parallelizes** ([18], [9]).

### [2] Bahdanau 2014 — the attention it keeps

> "Dzmitry Bahdanau, Kyunghyun Cho, and Yoshua Bengio. Neural machine translation by jointly learning to align and translate. CoRR, abs/1409.0473, 2014."

- **What it is**: the paper that introduced attention for neural machine translation — a decoder that soft-searches the source sentence, weighting every source position, instead of decoding from one fixed-length vector. (It is in our library: [profile](../bahdanau2014-nmt-attention/profile.html) · [hub](../bahdanau2014-nmt-attention/index.html).)
- **Why this paper leans on it**: three distinct debts. (1) Attention itself — the mechanism "allowing modeling of dependencies without regard to their distance in the input or output sequences [2, 19]" that the Transformer promotes from add-on to entire architecture (§1, p.2). (2) The contrast case: Bahdanau's mechanism is the "additive attention" that "computes the compatibility function using a feed-forward network with a single hidden layer," against which scaled dot-product attention is defined and justified (§3.2.1, p.4). (3) The encoder-decoder attention pattern the Transformer's decoder "mimics" — queries from the decoder, keys and values from the encoder, "such as [38, 2, 9]" (§3.2.3, p.5).
- **Link**: [arXiv:1409.0473](https://arxiv.org/abs/1409.0473) (id from the citation itself).

> ◆ **Beyond the paper · Personal** — For your goal this is the ancestral thread: the "weighted averaging where the weights are computed on the fly" you already unpacked in Bahdanau's setting is exactly what this paper keeps when it throws the recurrence away.

### [13] Hochreiter 1997 — the recurrence being replaced

> "Sepp Hochreiter and Jürgen Schmidhuber. Long short-term memory. Neural computation, 9(8):1735–1780, 1997."

- **What it is**: the LSTM — the long short-term memory recurrent network.
- **Why this paper leans on it**: it names the incumbent. LSTM is cited first in the paper's first sentence as what has "been firmly established as state of the art approaches in sequence modeling and transduction problems" (§1, p.2) — the recurrent world whose "inherently sequential nature precludes parallelization" (§1, p.2) and which the Transformer is built to replace.
- **Link** (located via web lookup): [doi:10.1162/neco.1997.9.8.1735](https://doi.org/10.1162/neco.1997.9.8.1735).

### [35] Sutskever 2014 — the encoder-decoder shape it keeps

> "Ilya Sutskever, Oriol Vinyals, and Quoc VV Le. Sequence to sequence learning with neural networks. In Advances in Neural Information Processing Systems, pages 3104–3112, 2014."

- **What it is**: the sequence-to-sequence learning paradigm with neural networks (per its title) — one of the encoder-decoder models the paper treats as the field's standard shape.
- **Why this paper leans on it**: the Transformer keeps this paradigm's skeleton while changing everything inside it. It is cited among the state-of-the-art transduction approaches (§1, p.2) and again for the structure the Transformer inherits: "Most competitive neural sequence transduction models have an encoder-decoder structure [5, 2, 35]" — encoder to continuous representations, auto-regressive decoder (§3, p.2).
- **Link** (located via web lookup): [arXiv:1409.3215](https://arxiv.org/abs/1409.3215).

### [38] Wu 2016 — the recurrent state of the art it beats

> "Yonghui Wu, Mike Schuster, Zhifeng Chen, Quoc V Le, Mohammad Norouzi, Wolfgang Macherey, Maxim Krikun, Yuan Cao, Qin Gao, Klaus Macherey, et al. Google's neural machine translation system: Bridging the gap between human and machine translation. arXiv preprint arXiv:1609.08144, 2016."

- **What it is**: GNMT — Google's recurrent neural machine translation system (per its title), cited as recent work pushing "the boundaries of recurrent language models and encoder-decoder architectures" (§1, p.2).
- **Why this paper leans on it**: it is both the benchmark and a parts supplier. Benchmark: "GNMT + RL" is the strongest recurrent baseline in Table 2 (24.6 / 39.92 BLEU vs the big Transformer's 28.4 / 41.8; p.8). Parts: the English-French "32000 word-piece vocabulary [38]" (§5.1, p.7), word-piece sentence representations in the complexity argument (§4, p.7), and the inference settings — "beam search with a beam size of 4 and length penalty α = 0.6 [38]", early termination (§6.1, p.8).
- **Link**: [arXiv:1609.08144](https://arxiv.org/abs/1609.08144) (id from the citation itself).

### [18] Kalchbrenner 2017 — convolutional rival, logarithmic paths

> "Nal Kalchbrenner, Lasse Espeholt, Karen Simonyan, Aaron van den Oord, Alex Graves, and Koray Kavukcuoglu. Neural machine translation in linear time. arXiv preprint arXiv:1610.10099v2, 2017."

- **What it is**: ByteNet — a convolutional model that shares the Transformer's motivation, "reducing sequential computation," computing "hidden representations in parallel for all input and output positions" (§2, p.2).
- **Why this paper leans on it**: it sets up the path-length argument. In ByteNet the number of operations relating two positions grows "logarithmically" with their distance — via "O(log_k(n)) in the case of dilated convolutions [18]" — which "makes it more difficult to learn dependencies between distant positions"; the Transformer reduces this to a constant (§2, p.2; §4, p.7). It also appears as a Table 2 baseline (23.75 BLEU EN-DE, p.8).
- **Link**: [arXiv:1610.10099](https://arxiv.org/abs/1610.10099) (id from the citation itself).

### [9] Gehring 2017 — convolutional rival, linear paths

> "Jonas Gehring, Michael Auli, David Grangier, Denis Yarats, and Yann N. Dauphin. Convolutional sequence to sequence learning. arXiv preprint arXiv:1705.03122v2, 2017."

- **What it is**: ConvS2S — the other convolutional sequence-to-sequence rival built on the same goal of parallel computation (§2, p.2).
- **Why this paper leans on it**: the same distance argument, worse case — operations grow "linearly for ConvS2S" (§2, p.2) — plus two borrowings: it is one of the models whose encoder-decoder attention the Transformer mimics ("such as [38, 2, 9]", §3.2.3, p.5), and it is the source of the "learned positional embeddings [9]" the paper tests against its sinusoids, with "nearly identical results" (§3.5, p.6). Also a Table 2 baseline (25.16 / 40.46 BLEU, p.8).
- **Link**: [arXiv:1705.03122](https://arxiv.org/abs/1705.03122) (id from the citation itself).

## Reference map

Layout logic: the Transformer sits center; the recurrent lineage it replaces runs down the left column (time flowing top to bottom), the convolutional rivals it out-parallelizes down the right. Every edge points from this paper to a work it cites.

```yaml map-data
nodes:
  - {id: hochreiter1997-lstm, label: "LSTM", sub: "Hochreiter · 1997",
     title: "Long short-term memory", col: 0, row: 0}
  - {id: sutskever2014-seq2seq, label: "Seq2Seq Learning", sub: "Sutskever · 2014",
     title: "Sequence to sequence learning with neural networks", col: 0, row: 1}
  - {id: bahdanau2014-nmt-attention, label: "Jointly Align & Translate", sub: "Bahdanau · 2014",
     title: "Neural machine translation by jointly learning to align and translate", col: 0, row: 2,
     href: "../bahdanau2014-nmt-attention/index.html"}
  - {id: wu2016-gnmt, label: "GNMT", sub: "Wu · 2016",
     title: "Google's neural machine translation system", col: 0, row: 3}
  - {id: vaswani2017-attention, label: "Attention Is All You Need", sub: "Vaswani · 2017",
     title: "Attention Is All You Need", col: 1, row: 2, href: "index.html"}
  - {id: kalchbrenner2017-bytenet, label: "ByteNet", sub: "Kalchbrenner · 2017",
     title: "Neural machine translation in linear time", col: 2, row: 1}
  - {id: gehring2017-convs2s, label: "ConvS2S", sub: "Gehring · 2017",
     title: "Convolutional sequence to sequence learning", col: 2, row: 2}
edges:
  - {from: vaswani2017-attention, to: hochreiter1997-lstm, label: "recurrence it replaces", kind: contrasts}
  - {from: vaswani2017-attention, to: sutskever2014-seq2seq, label: "encoder-decoder shape kept", kind: builds-on}
  - {from: vaswani2017-attention, to: bahdanau2014-nmt-attention, label: "attention it keeps", kind: builds-on}
  - {from: vaswani2017-attention, to: wu2016-gnmt, label: "recurrent SOTA beaten", kind: contrasts}
  - {from: vaswani2017-attention, to: kalchbrenner2017-bytenet, label: "conv rival, log paths", kind: contrasts}
  - {from: vaswani2017-attention, to: gehring2017-convs2s, label: "conv rival, linear paths", kind: contrasts}
```

### Edges, grounded

- **→ hochreiter1997-lstm** · contrasts · "recurrence it replaces" — LSTM is named as the established state of the art in sequence transduction (§1, p.2); the Transformer is "a model architecture eschewing recurrence" entirely (§1, p.2).
- **→ sutskever2014-seq2seq** · builds-on · "encoder-decoder shape kept" — cited for the encoder-decoder structure "most competitive neural sequence transduction models have" (§3, p.2), which the Transformer keeps.
- **→ bahdanau2014-nmt-attention** · builds-on · "attention it keeps" — origin of attention in NMT (§1, p.2); the additive-attention contrast case for scaled dot-product attention (§3.2.1, p.4); the encoder-decoder attention pattern mimicked (§3.2.3, p.5).
- **→ wu2016-gnmt** · contrasts · "recurrent SOTA beaten" — the strongest recurrent baseline in Table 2 (§6.1, p.8); also supplies the word-piece vocabulary (§5.1, p.7) and beam-search settings (§6.1, p.8).
- **→ kalchbrenner2017-bytenet** · contrasts · "conv rival, log paths" — parallel convolutional predecessor whose position-distance cost grows logarithmically (§2, p.2; §4, p.7); Table 2 baseline (p.8).
- **→ gehring2017-convs2s** · contrasts · "conv rival, linear paths" — parallel convolutional rival whose cost grows linearly (§2, p.2); also source of the learned positional embeddings tested in §3.5 (p.6); Table 2 baseline (p.8).
