You are implementing phase 1 of a reproduction of "Attention Is All You Need" (Vaswani et al., 2017). Work only inside this workspace directory, and use it as your working directory:

<the absolute path of this workspace directory on your machine>

All paths below are relative to that directory. Read, in order:

1. papers/vaswani2017-attention/reproduction/PLAN.md — the plan, the authoritative toy-data recipe, and decisions so far
2. papers/vaswani2017-attention/reproduction/phases/phase-1.md — your phase spec; it is your only scope and restates the full recipe
3. papers/vaswani2017-attention/reproduction/INVENTORY.md — skip: the phase-1 spec names no inventory sections
4. papers/vaswani2017-attention/paper.pdf — skip: the phase-1 spec requires no paper pages; every quote you need is in the spec

Implement the phase deliverables into papers/vaswani2017-attention/reproduction/code/, explaining each piece to the user as you go and tying it to the paper idea it implements: this dataset instantiates the structure attention consumes — a query and a set of key–value pairs (spec's §3.2 anchor). It is Python 3 standard library only: data.py plus the three generated JSONL files under code/data/.

Stop when every acceptance check in the spec passes — run them and show the output:

1. python3 papers/vaswani2017-attention/reproduction/code/data.py — writes code/data/train.jsonl (2048 lines), val.jsonl (256), test.jsonl (512)
2. python3 papers/vaswani2017-attention/reproduction/code/data.py --check — exits 0: per-line validity (4 pairs; distinct keys; distinct values; symbols in k0…k9/v0…v9; query among the keys; target is the queried key's paired value), byte-for-byte determinism against a regeneration from seed 17, and the leak guards (queried-slot frequencies each in [0.20, 0.30]; target-value frequencies each in [0.06, 0.14])

Before ending, do exactly this bookkeeping and nothing more:

- In papers/vaswani2017-attention/reproduction/PLAN.md, set the phase-1 row's status to: done <today's date, YYYY-MM-DD>
- If you made any decision the spec left open, append it to PLAN.md's "## Decisions so far" as one line ending in "(phase 1)"
- Append one line to the "## Session log" section of papers/vaswani2017-attention/PAPER.md, formatted exactly:
  - <today's date, YYYY-MM-DD> · pass 3 · phase 1: data generator + fixtures built, checks green · next: phase 2 (spec: reproduction/phases/phase-2.md)

Do not touch other phases' code or specs, and change nothing in the workspace beyond the deliverables and the two bookkeeping files named above. Markdown files elsewhere in the workspace have paired .html renders — none of them concern this phase; do not edit any .html file.
