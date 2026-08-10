# `three-pass` — example workspace

A real reading workspace produced by the [`three-pass`](../../skills/three-pass/SKILL.md) skill during its verification dry-run, kept here so you can see what the skill builds before you install it. The simulated reader was a cancer-epidemiology postdoc who had never touched neural networks; they read **Attention Is All You Need** (Vaswani et al., 2017) through all three passes and profiled **Neural Machine Translation by Jointly Learning to Align and Translate** (Bahdanau et al., 2014) beside it.

## Browse it

Open `workspace/index.html` in a browser — the pages work straight from disk. Worth clicking through:

- **Library dashboard** (`index.html`) and the **relationship map** (`map.html`) — click a node to unfold that paper's full profile in place.
- **The paper hub** (`papers/vaswani2017-attention/index.html`) — every artifact with its status, plus the reader's goal for the paper.
- **Pass 1**: the terse, fully §/page-cited `profile.html` — including a ◆ *Beyond the paper* critique flagging an inconsistency in the paper's own reported BLEU numbers.
- **Pass 2**: the section-by-section `summary.html`, the filterable `glossary.html` and `notes.html`, figure and table pages with 2× crops, and the interactive `equations/eq-01-scaled-dot-product.html` — hover or click a term of the equation and its legend row lights up.
- **Pass 3**: `derivations/deriv-01-sqrt-dk-scaling.html`, whose assumptions ledger surfaces that the paper's variance footnote quietly needs mutually independent components — and `reproduction/`: the inventory, the phased plan, a paste-able phase prompt, and the phase-1 data generator that a fresh session implemented from that prompt alone, with no skill installed.

Every page has a printable sister markdown file — in this skill, markdown is the source of truth and HTML is a disposable render. Everything unmarked restates the paper with a `§`/page citation; everything the agent added is marked ◆.

## Restoring what git leaves out

Two pieces are deliberately untracked:

- **`papers/*/paper.pdf`** — both papers are distributed under arXiv's non-exclusive license, which doesn't allow third-party redistribution. Restore them from this directory:

  ```bash
  python3 ../../skills/three-pass/scripts/fetch_paper.py 1706.03762 --out workspace/papers/vaswani2017-attention/paper.pdf
  python3 ../../skills/three-pass/scripts/fetch_paper.py 1409.0473 --out workspace/papers/bahdanau2014-nmt-attention/paper.pdf
  ```

- **`reproduction/code/data/*.jsonl`** — the phase-1 fixtures regenerate byte-identically (the generator is seeded):

  ```bash
  python3 workspace/papers/vaswani2017-attention/reproduction/code/data.py
  ```

The figure PNGs are small cropped excerpts kept so the figure pages render; each figure page cites the exact source page. One line was edited during the copy: the dry-run's throwaway absolute path in `reproduction/prompts/phase-1-prompt.md` is now a placeholder — a real generated prompt carries your workspace's actual path.

## How to prompt the agent

Install the skill first — routes are in the [repo README](../../README.md#install). Invoke it **in the directory you want as your reading workspace**; every session's memory lives there as markdown, so independent sessions pick up where you left off. In harnesses without slash commands, say the same things in prose: "Use the three-pass skill: …".

**Bringing a paper.** The first-ever run also gives a ten-line introduction to the method and asks six questions about your background, so explanations land at your level from then on:

```
/three-pass ~/Downloads/attention.pdf
/three-pass 1706.03762
/three-pass https://arxiv.org/abs/1409.0473
/three-pass "Attention Is All You Need"
/three-pass 10.1038/nature14539
```

Paywalled paper? The skill won't scrape around it — download it through your own access and hand over the path.

**Pass 1 — bird's-eye.** A cited profile per paper; a relationship map once there are several:

```
/three-pass paper-a.pdf paper-b.pdf paper-c.pdf
How does this paper relate to the others in my library?
Move the Bahdanau node to the left column and label that edge "replaces recurrence".
Which of these is worth a pass 2, given my goal?
```

**Pass 2 — the close read.** One top-level section per sitting is the default pace:

```
/three-pass                    (in the workspace, with nothing named: resumes at the last "next:" pointer)
Let's read §3 together.
What does the mask in equation 3 actually do?
Make a page for Figure 2.
Add "autoregressive" to the glossary.
Note this down — I want to come back to it.
What were my open questions about §3?
Let me explain multi-head attention back to you; probe me like a peer reviewer.
Build the references page.
```

That second-to-last one starts a Feynman sitting — the agent plays a five-year-old, a high-schooler, an out-of-domain expert, or a peer, and probes your explanation for gaps.

**Pass 3 — line by line:**

```
Let's re-derive the √dk scaling and challenge every assumption.
Inventory what a reproduction of this paper needs.
Set up a reproduction plan — minimal track, on toy data I can control.
Generate the phase-1 prompt.
Walk me through the code against the paper.
```

Phase prompts are meant to be pasted into a *fresh* session each; come back to the reading workspace between phases for the oversight view.

Escalation is always yours: each pass ends with the skill presenting what it built and asking whether to go deeper — it never advances on its own.
