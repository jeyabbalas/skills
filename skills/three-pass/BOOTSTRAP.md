The first-ever session in a workspace: introduce the method, learn who you're reading with, and create the two files every later session depends on. This runs exactly once per workspace — READER.md's existence is the never-again flag.

Table of contents

- [Steps](#steps)
- [Introducing the method](#introducing-the-method)
- [The interview](#the-interview)
- [READER.md template](#readermd-template)
- [READER.md rules](#readermd-rules)

## Steps

1. **Introduce the method** (below) in at most ten lines of conversation. Done when the reader knows what the three passes are and that this directory will remember everything.
2. **Interview the reader** — all six questions in one message (grouped, skimmable). If they mention having used this skill in another workspace, offer to copy that workspace's READER.md instead (they paste it or give the path; confirm it still fits). Done when the reader confirms your one-paragraph read-back of their profile.
3. **Create the state**: run `workspace.py init` (contract in LAYOUT.md), write READER.md from the template below, and write LIBRARY.md as an empty index per LIBRARY-FORMAT.md. Done when all three exist.
4. **Continue into the paper** they brought — bootstrap never ends a session by itself. Follow SKILL.md's New paper (or Survey) mode.

## Introducing the method

Adapt, don't recite — but keep it this short and credit the sources:

> We'll read in three passes, each deeper than the last — the method is S. Keshav's "How to Read a Paper", in the spirit of Adler's *How to Read a Book*.
> **Pass 1 — bird's-eye** (~minutes): a concise profile of the paper — what it is, what it claims, whether it deserves more of your time.
> **Pass 2 — analytical** (~an hour+, over sessions): we read it together, section by section — glossary, figures, equations, margin notes; you talk back to the paper.
> **Pass 3 — line-by-line**: re-derive the math, challenge every assumption, and reproduce or replicate the results in code.
> You decide at each gate whether to go deeper. Everything we learn lives in this directory as markdown and web pages, so any future session picks up exactly where we left off.

## The interview

Ask all six at once, then read their answers back in one paragraph for confirmation:

1. **Field** — what's your home field or training?
2. **Level** — student, researcher, practitioner, something else?
3. **This paper's domain** — how familiar are you with it? (This calibrates how much background I fill in.)
4. **Explanations** — what works for you: concrete examples first, formalism first, analogies, code?
5. **Math** — comfortable with what level? (e.g., linear algebra and probability fine, measure theory no)
6. **Finish line** — when you read a paper, what does "done" usually mean: ideas skimmed, deep understanding, able to reproduce it, reviewing it?

Push back on vague answers once ("what would you *do* with this paper if the read succeeds?") — a sharp profile is worth thirty seconds of friction.

## READER.md template

```md
# Reader

field: {home field / training}
level: {student | researcher | practitioner | …}
math: {comfort level, concretely}
finish line: {what "done" usually means for them}

## Domains
- at home in: {…}
- learning: {…}

## How to explain
- {register that works: e.g., concrete example before formalism; diagrams over prose; code speaks loudest}

## Observed preferences
- {YYYY-MM-DD} — {a correction or preference that recurred, one line}
```

## READER.md rules

- **Write once, from the interview.** Update a field only when the reader volunteers new background or corrects how you explain things.
- **Append to Observed preferences when a correction recurs** — once is conversation, twice is a preference. One line each, dated.
- **Never re-interview a populated READER.md.** Resuming sessions read it silently and just talk right.
- **It's theirs to read.** Plain markdown in their directory — write nothing there you wouldn't say to them.
