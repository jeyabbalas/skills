`papers/<slug>/PAPER.md` is the paper's dossier — the small file a resuming session reads to know what this paper is, why the reader is reading it, and exactly where things stand. Fields update in place; the session log only appends.

## Template

```md
# {Full paper title}

```bibtex
@inproceedings{vaswani2017-attention,
  title     = {…},
  author    = {…},
  year      = {2017},
  …
}
```

status: pass-2
track: —
added: {YYYY-MM-DD}
source: {where paper.pdf came from — URL or "provided by reader"}
bibsource: {where the BibTeX came from — URL}

## Goal
> "{the reader's answer to “What do you want from this paper?”, verbatim}"

## Session log
- {YYYY-MM-DD} · pass 1 · profiled; SKELETON.md written · next: reader decides on pass 2
```

## Rules

- **BibTeX at intake, from day one.** Look it up (arXiv/DBLP/publisher), record where in `bibsource`, and use the paper slug as the citation key. Nothing in this skill needs it yet — a future literature-survey skill gets a bibliography for free.
- **The goal is verbatim.** Ask once at intake — "What do you want from this paper?" — record the answer in the reader's own words, and let it steer every pass. If their goal shifts mid-read, update it and say so in the log line.
- **`status`** is one of `inbox` (registered, unread) · `pass-1` · `pass-2` · `pass-3` · `done` — always the hyphenated form; it means the deepest pass the reader has *committed to*, and it moves only when they decide to go deeper or stop, never on your own. A pass the reader committed to but hasn't started shows on the hub as `○ up next` (its chips fill only once artifacts exist). `done` means the reader closed the paper at whatever depth — closing a context paper at its profile is normal; its log line ends `next: — (closed)`. **`track`** stays `—` until pass 3 reproduction chooses `reuse`, `minimal`, or `full`.
- **One log line per session that touched this paper** — a session that appends no log line did not happen. The line format and its `next:` requirement are defined in SKILL.md's Closing a session. Keep each line one line: the log is an index of sessions, not a journal.
