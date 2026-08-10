The Feynman sitting inverts the roles: the reader explains the paper, you play a chosen audience and probe. The goal is to surface what the reader only *thinks* they understand — and what the paper itself never actually says. Gaps are findings, not failures.

Table of contents

- [Protocol](#protocol)
- [The roles](#the-roles)
- [Probing well](#probing-well)
- [Transcript record](#transcript-record)

## Protocol

1. **Ask which role to play** (menu below) and how much they want to cover — the whole paper or one section.
2. **Stay in character** while the reader explains. Interrupt the way that character would: short, curious, one question at a time.
3. **Probe against the paper**, silently checking SKELETON.md for territory their explanation skipped, and the paper's claims for places their version diverges.
4. **Break character to close.** Reflect back: what landed clearly, where the explanation wobbled, what was skipped, and — kept distinct — *gaps in their understanding* versus *gaps in the paper itself* (things the paper genuinely never explains).
5. **Record**: write the transcript file (below), turn each gap into a `todo` note per NOTES-FORMAT.md with an anchor, and append the session-log line. A sitting that found no gaps is worth recording too — that's the reader clearing the bar.

The sitting ends when the reader ends it; never grade, never lecture mid-explanation.

## The roles

- **Five-year-old** — no jargon survives; every term must become a picture or a story; asks "why?" chains ("but why does it look at all the words at once?").
- **High-schooler** — basic algebra fine; asks for the concrete example behind each abstraction; wants to know what problem this solves in the real world.
- **Expert from another domain** — rigorous but foreign (ask which domain, or pick from READER.md's "at home in"); accepts math, challenges the field's unstated assumptions ("in my field we'd never assume i.i.d. here — why is that fine?").
- **Peer** — same field; probes methodology, baselines, and whether the claims outrun the evidence; the friendliest version of a tough reviewer.

The reader may invent a different audience — take it.

## Probing well

- One question at a time; let them finish before the next.
- Prefer questions the paper answers — the miss then tells you exactly what to revisit.
- When an explanation is fluent but wrong, don't correct in character — ask the follow-up that lets them hear it ("wait, so the model reads the words in order?").
- Track, don't announce: keep the running gap list for the close, so the sitting stays a conversation rather than a quiz being scored.

## Transcript record

`feynman/0001-<role>.md` (numbering rules in LAYOUT.md) — a record, not a page; no HTML render:

```md
# Feynman sitting {NNNN} — {role} · {YYYY-MM-DD}
scope: {whole paper | §N}

## What the reader explained well
- {…}

## Where it wobbled
- {claim as explained} → {what the paper actually says} (§/p.)

## Gaps in the reader's understanding
- {…} → note N{NNNN}

## Gaps in the paper
- {what the paper never explains or justifies} → note N{NNNN}
```
