`SHELF.md`, at the workspace root, is the index of every book — the first (and often only) file a resuming session reads to orient. It is an index, not a store: one row per book, a gist and a link, never a restatement. Detail lives in each book's own files; the dashboard `index.html` renders this file (ARTIFACTS.md).

## Template

```md
# Shelf

| book | status | genre | gist | progress | tags | last touched |
|---|---|---|---|---|---|---|
| [{slug}](books/{slug}/BOOK.md) | pass-2 | practical | {One line: what the book teaches or argues.} | recited 2/13 | {tag}, {tag} | {YYYY-MM-DD} |
```

## Rules

- **One row per book, most recently touched first.** The dashboard mirrors this order.
- **`status`** is one of `inbox` (registered, unread) · `pass-1` · `pass-2` · `pass-3` · `maintenance` · `closed` — always the hyphenated form. It means the deepest pass the student has *committed to*, and it moves only when they decide — never on your own. `maintenance` is what follows pass 3: the passes are finished but the cards keep cycling through revision. `closed` retires the book from revision too — `revise.py` skips it — and its log line ends `next: — (closed)`. (BOOK.md carries the same field; this row is its index gist.)
- **`genre` mirrors CONTENTS.md's classification** (`theoretical` · `practical` · `expository`) — an index gist, decided and reasoned there.
- **The gist is one sentence,** present tense, about the book — not about the student's progress.
- **`progress`** is `recited K/N` — chapters recited over chapters planned (skipped and skimmed chapters leave the denominator).
- **Tags are topical,** lowercase, at most four — the raw material future cross-book work groups by.
- **Touch a row only when something row-level changed** — a book added, `status` moved, the gist sharpened, progress advanced, or a session touched the book (update `last touched`). Session detail never lands here; that is BOOK.md's log.
