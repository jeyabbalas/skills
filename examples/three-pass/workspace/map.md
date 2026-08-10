# Reading room — relationship map

How the library's papers relate. Layout logic: time flows left to right — older work left, later work right; the edge points from the later paper to the earlier one it builds on.

```yaml map-data
nodes:
  - {id: bahdanau2014-nmt-attention, label: "Jointly Align & Translate", sub: "Bahdanau · 2014",
     title: "Neural Machine Translation by Jointly Learning to Align and Translate", col: 0, row: 0,
     href: "papers/bahdanau2014-nmt-attention/index.html"}
  - {id: vaswani2017-attention, label: "Attention Is All You Need", sub: "Vaswani · 2017",
     title: "Attention Is All You Need", col: 1, row: 0,
     href: "papers/vaswani2017-attention/index.html"}
edges:
  - {from: vaswani2017-attention, to: bahdanau2014-nmt-attention, label: "keeps attention, drops RNN", kind: builds-on}
```

## Edges, grounded

- **vaswani2017-attention → bahdanau2014-nmt-attention** · builds-on · "keeps attention, drops RNN" — Vaswani et al. cite Bahdanau et al. as the origin of attention in NMT (their [2]; §1 p.2) and contrast their scaled dot-product attention with its additive alignment model (§3.2.1 p.4); Bahdanau et al. introduce that mechanism inside a recurrent decoder (§3.1 p.3–4), which the Transformer removes. (Reader's phrasing, trimmed to the 4-word label cap.)

## Nodes

- [Neural Machine Translation by Jointly Learning to Align and Translate](papers/bahdanau2014-nmt-attention/profile.md) — Bahdanau, Cho, Bengio · ICLR 2015
- [Attention Is All You Need](papers/vaswani2017-attention/profile.md) — Vaswani et al. · NeurIPS 2017
