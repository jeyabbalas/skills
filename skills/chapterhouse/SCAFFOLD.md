Scaffold mode is for the book the student cannot yet read unaided — too dense, or assuming background they don't have. The pass-2 loop inverts: instead of reading together first, you **equip** the student with an agent-authored guide — the assumed background, a slow walkthrough, a self-test — so they can read the section alone; a later step captures the note and runs the unchanged graded recite. The guide is yours by design (GUIDE-FORMAT.md); the note stays theirs (NOTES-FORMAT.md). When the mode is off, nothing in this file applies and pass 2 runs exactly as PASS-2.md writes it.

Table of contents

- [Entering and leaving](#entering-and-leaving)
- [The inverted loop](#the-inverted-loop)
- [The equip session](#the-equip-session)
- [Reading alone](#reading-alone)
- [The capture session](#the-capture-session)
- [Bookkeeping](#bookkeeping)

## Entering and leaving

The student can ask for the mode at any time, at any gate — that alone enters it, no ceremony. Four signals make you **offer** it (one line, once per signal — offer, never impose):

1. A read-together session that fails or gets redone — "too cryptic", "I didn't follow any of that".
2. A failed recite whose misses trace to background the book never taught, rather than the chapter's own content.
3. Three or more prerequisite questions from the student inside one section's read.
4. At the pass-1 gate, when STUDENT.md's `math:`/`code:` lines sit visibly below what the survey shows the book assumes.

A declined offer is noted in the session log; don't re-offer on the same signal. Entering writes three things: the `support:` line in BOOK.md (grammar in BOOK-FORMAT.md — book-wide, or scoped `· ch N, M only`), a dated line in STUDENT.md's Observed preferences naming the discovered need, and a log line naming the trigger.

**Leaving is the student's, like every escalation.** At any chapter's Review, ask one line — "still want guides for the next chapter?" Stepping down edits or removes the `support:` line, with a log line; existing guides stay on disk — they are study artifacts, not mode state. Stepping back up is the same edit in reverse.

## The inverted loop

Survey → Question → **Equip → read alone → Capture + Recite** → Review. Survey and Question run as PASS-2.md writes them (prequestions stay an offer). The recite, the ledger, the ladder, and "no recite, no done" are untouched — the mode changes how the student gets *to* the reading, never how the reading is tested. The natural unit is the section (PASS-2.md's Section pacing); a book without usable sections scaffolds chapter by chapter.

## The equip session

One session builds what the next read needs — from the open pages, errata checked first, never from memory of similar books:

1. **Diagnose.** From the section's pages plus STUDENT.md's `math:`/`code:` lines, list the background the section silently assumes that the student doesn't own. Warm-up misses and the last capture's questions are evidence too.
2. **Write the foundations** the diagnosis found into `guides/chNN-foundations.md` (GUIDE-FORMAT.md) — created at the chapter's first guide, appended thereafter, F-numbers never renumbered.
3. **Write the section guide** `guides/chNN-sMM-<slug>.md`: the walkthrough in the four-beat rhythm, the self-test, the problem path when the section has exercises.
4. **Run the foundations checks live, ungraded** — they are prerequisite diagnostics, not book retrieval (ASSESS.md: no confidence ritual, no ledger line). A miss deepens the guide: a new F-item, or an escape-hatch link. A gap that will clearly recur *may* mint an ordinary chapter card, anchored to the book passage that assumes the background — the default is no card.
5. **Offer widgets or a lab** when STUDENT.md's How-to-explain asks for visual or interactive work (GUIDE-FORMAT.md; lab rules in ARTIFACTS.md) — offered, never imposed.

Close with the renders and the pointer: `next: read §N.M alone with guide chNN-sMM; then capture + recite`.

## Reading alone

Between sessions normally; in-session for a short section (you stay silent; reactive-work rules apply — a question is not a commission). The guide's own How-to-use section carries the contract: foundations first, skipping what the checks say they own; the walkthrough beside the book, not instead of it; the self-test out loud at the end; bring whatever broke to the next session. The guide prepares the read — the book's own text is still the read.

## The capture session

The polarity of PASS-2.md's Read-together flips — they read it, so the session opens with *"you read it — tell me"*:

1. **Say-back first.** The student states the section's argument, closed book; their version goes into the note's `## Argument` — which in scaffold mode is *only* ever the student's say-back, never a copy of the guide (your re-teaching already exists there; NOTES-FORMAT.md). An Argument waiting on the student is left visibly pending, not filled by you.
2. **Capture as usual.** Terms, Propositions, at least one Worked example — the sections you always draft (NOTES-FORMAT.md), from the open pages, shaped by what the student's questions surfaced. What broke during the solo read deepens the guide, logged.
3. **Recite, closed book** — ASSESS.md's protocol over the sections read so far, exactly as PASS-2.md runs it: cues plus new cards, confidence, rubrics, ledger lines. The guide's self-test was the rehearsal; this is the graded exit.

A capture that finds nothing captured — the solo read didn't land — is a finding, not a failure: deepen the guide at the break, and the retry is the `next:` pointer.

## Bookkeeping

- **Log lines** stay `pass 2`, the body naming the session shape:
  `- 2026-08-29 · pass 2 · equip §1.2: guide ch01-s02 + foundations F11–F13, checks run · next: read §1.2 alone (guide beside book), then capture + recite`
  `- 2026-08-31 · pass 2 · capture §1.2: say-back → Argument; recite C13–C18 passed · next: equip §1.3`
- **Status**: the first equip moves the chapter `unread` → `reading`; the annotation gist and its limits are CONTENTS-FORMAT.md's. The chapter reaches `recited` only per PASS-2.md — the mode never shortcuts it.
- **Pages**: guides render per ARTIFACTS.md and join the book hub's artifact rows; the closing checklist is SKILL.md's, unchanged.
- **The step-down question** at each chapter's Review (above) is part of closing a chapter in this mode.
