`LIBRARY.md`, at the workspace root, is the index of every paper — the first (and often only) file a resuming session reads to orient. It is an index, not a store: one row per paper, a gist and a link, never a restatement. Detail lives in each paper's own files; the dashboard `index.html` renders this file (ARTIFACTS.md).

## Template

```md
# Library

| paper | status | gist | tags | last touched |
|---|---|---|---|---|
| [{slug}](papers/{slug}/PAPER.md) | pass-2 | {One line: what the paper does or claims.} | {tag}, {tag} | {YYYY-MM-DD} |
```

## Rules

- **One row per paper, most recently touched first.** The dashboard mirrors this order.
- **Touch a row only when something row-level changed** — a paper added, `status` moved, the gist sharpened, or a session touched the paper (update `last touched`). Session detail never lands here; that is PAPER.md's log.
- **The gist is one sentence,** present tense, about the paper — not about the reader's progress.
- **Tags are topical,** lowercase, at most four — the raw material future cross-paper work (surveys, maps) will group by.
