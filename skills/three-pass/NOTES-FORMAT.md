`papers/<slug>/notes.md` is the paper's margin: the durable record of what the conversation changed — questions worth keeping, realizations, critiques, tasks, ideas. One file per paper; entries append; nothing is ever deleted. `notes.html` renders it searchable (ARTIFACTS.md). Derivation gaps and Feynman findings land here too, as `todo` entries.

## Template (one entry, appended at the top of the entry list)

```md
## N0007 · {YYYY-MM-DD} · {type}
anchor: §{3.2} · p.{5} · "{first six-to-ten words of the passage, verbatim}"
tags: {tag}, {tag}
status: active

**{One-line gist}**

> "{longer verbatim quote, only if the six-to-ten anchor words aren't enough}"

{2–6 lines distilling the exchange — the resolution, not the transcript.}
```

`type` is one of `question` (open, worth returning to) · `insight` (something clicked) · `critique` (the reader challenges the paper) · `todo` (work spawned — a gap to close, a derivation to check) · `idea` (future work building on the paper).

## When to write a note

Write one when the exchange **changed what the reader understands or believes** about the paper:

1. Something clicked — the reader said, in substance, "ah, so *that's* why".
2. The reader voiced a challenge to a claim, method, or assumption.
3. A confusion was resolved after real back-and-forth (the resolution is the note).
4. Work was spawned — a passage to revisit, a derivation to verify, an idea to build on.

What does **not** qualify: material merely covered, and questions answered in one turn and moved past. Answering is not noting.

Notes are the conversation's own voice — the one place the ◆ demarcation is not needed. Inside an entry, only quotation marks carry the paper's voice; everything else is understood to be the reader's and yours.

## The anchor

`§3.2 · p.5 · "first six-to-ten words verbatim"` — section per SKELETON.md's numbering (SKELETON.md is the numbering authority everywhere), page for a one-shot PDF re-read, and the verbatim words so the spot is grep-recoverable in the PDF text even if the section number was misjudged. Notes about the paper as a whole use `anchor: whole paper`.

## Numbering

Entries are `N0001`, `N0002`, … zero-padded to four. Scan the file for the highest number and increment; never reuse a number. The highest number is the paper's engagement odometer — a resuming session can read it at a glance.

## Status changes

`status` starts `active`. Two ways it ends:

- **Superseded** — a later entry corrects this one: set `status: superseded-by N00NN` and leave everything else untouched.
- **Closed** — the work a `todo` (or the question a `question`) named is done: set `status: closed — {what closed it}`, e.g. `closed — deriv-01`, `closed — answered in N0007`.

Ended notes keep rendering, visibly retired — how understanding evolved is itself signal. The entry date is the day the entry is *written*; when the thought predates it (a hand note formalized later), say so in the body.

## Searching

The uniform fields make grep the search interface:

```sh
grep -n -i "softmax" papers/<slug>/notes.md          # by content
grep -n "§3.2" papers/<slug>/notes.md                # by place in the paper
grep -n "· todo$" papers/<slug>/notes.md             # open work items
grep -rn -i "positional" papers/*/notes.md           # across every paper
```

On the page, the same fields feed the live filter.
