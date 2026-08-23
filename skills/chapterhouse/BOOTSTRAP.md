The first-ever session in a workspace: introduce the method, learn who you're studying with, and create the two files every later session depends on. This runs exactly once per workspace — STUDENT.md's existence is the never-again flag.

Table of contents

- [Steps](#steps)
- [Introducing the method](#introducing-the-method)
- [The interview](#the-interview)
- [STUDENT.md template](#studentmd-template)
- [STUDENT.md rules](#studentmd-rules)

## Steps

1. **Introduce the method** (below) in at most ten lines of conversation. Done when the student knows what the three passes are, that chapters end in a closed-book recitation, and that this directory will remember everything — including what they're due to review.
2. **Interview the student** — all seven questions in one message (grouped, skimmable). If a `READER.md` from the three-pass paper skill sits in this directory, offer to seed STUDENT.md from it and ask only the deltas (coding comfort, cadence); if they've used *this* skill elsewhere, offer to copy that workspace's STUDENT.md instead. Done when the student confirms your one-paragraph read-back of their profile.
3. **Create the state**: run `workspace.py init` (contract in LAYOUT.md), write STUDENT.md from the template below, and write SHELF.md as an empty index per SHELF-FORMAT.md. Done when all three exist.
4. **Continue into the book** they brought — bootstrap never ends a session by itself. Follow SKILL.md's New book mode.

## Introducing the method

Adapt, don't recite — but keep it this short and credit the sources:

> We'll study the whole book in three passes — the method draws on M. Adler's *How to Read a Book*, F. Robinson's SQ3R, and what learning science actually validates: testing yourself and spacing the reviews.
> **Pass 1 — inspectional survey** (a session or two): map the book — chapters, difficulty, what depends on what — classify what kind of book it is, write down the questions you want it to answer, and plan the read. Then decide: is this the right book?
> **Pass 2 — analytical read** (the long middle, one chapter per session): we read each chapter together into structured notes, and the chapter ends with a closed-book quiz — misses become flashcards.
> **Pass 3 — synthesis**: critique the book, re-create its core results from memory, sit a cumulative exam.
> And woven through everything: each session opens with whatever your flashcards and chapters say is due for review. You decide at every gate whether to go deeper. It all lives in this directory as markdown and web pages, so any future session picks up exactly where we left off.

## The interview

Ask all seven at once, then read their answers back in one paragraph for confirmation:

1. **Field** — what's your home field or training?
2. **Level** — student, researcher, practitioner, something else?
3. **Math** — comfortable with what level, concretely? (e.g., algebra and probability fine, real analysis no — this calibrates how derivation practice starts)
4. **Code** — which languages, how comfortable? (this gates whether exercises include programming problems)
5. **Goals** — what is studying whole books usually *for*, for you: an exam, research depth, changing practice? (each book gets its own goal later; this is the standing one)
6. **Time** — roughly how many sessions a week, and how long is one? (this sizes reading plans and keeps review gaps honest)
7. **Explanations** — what works for you: concrete examples first, formalism first, analogies, code?

Push back on vague answers once ("what would you *do* with this book if the study succeeds?") — a sharp profile is worth thirty seconds of friction.

## STUDENT.md template

```md
# Student

field: {home field / training}
level: {student | researcher | practitioner | …}
math: {comfort level, concretely}
code: {languages · comfort}
goals: {what studying books is for, standing}
cadence: {sessions/week × minutes — e.g., 2 × 60}

## Domains
- at home in: {…}
- learning: {…}

## How to explain
- {register that works: e.g., concrete example before formalism; diagrams over prose; code speaks loudest}

## Observed preferences
- {YYYY-MM-DD} — {a correction or preference that recurred, one line}
```

## STUDENT.md rules

- **Write once, from the interview.** Update a field only when the student volunteers new background or corrects how you explain things; `cadence` may also update when reality diverges from the answer — say so when you do.
- **Append to Observed preferences when a correction recurs** — once is conversation, twice is a preference. One line each, dated.
- **Never re-interview a populated STUDENT.md.** Resuming sessions read it silently and just talk right.
- **It's theirs to read.** Plain markdown in their directory — write nothing there you wouldn't say to them.
