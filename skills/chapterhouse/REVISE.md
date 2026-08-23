Revision is the skill's second engine, running orthogonally to the passes: items (cards) cycle on a per-card schedule the ledger determines, and chapters cycle on a coarse Leitner ladder you manage by hand in CONTENTS.md. This file owns the due check every session opens with, the warm-up, the delayed judgment of learning, the ladder's numbers, and the pure Revise session. The scheduling itself is never yours to compute: `revise.py` replays the ledger (law 4, SKILL.md) — you run it, read it, and conduct what it prescribes.

Table of contents

- [The due check](#the-due-check)
- [The warm-up](#the-warm-up)
- [The delayed judgment of learning](#the-delayed-judgment-of-learning)
- [The chapter ladder](#the-chapter-ladder)
- [The cumulative chapter recite](#the-cumulative-chapter-recite)
- [The Revise session](#the-revise-session)

## The due check

Every session but bootstrap opens with `revise.py due` (contract in LAYOUT.md). Read three things from it: the counts (due cards, and any chapter whose ladder date has arrived — the CONTENTS.md `due` column the output echoes), the `dag_flags` (a due card whose chapter has an unread prerequisite — the student jumped around; say so, don't drop it), and `ledger_warnings` (anything non-empty gets fixed *as new lines or deck corrections* before other work — never by editing history). Then propose, in one line, warm-up plus the session's planned unit. **Offer, never impose** — a student who waves the warm-up off today still saw the number, and that is the system working. Note the deferral in the log line so the next session knows the backlog is deliberate.

## The warm-up

A short block before new material — 10–15 minutes, ~5–15 items, the size the student has. Run the `plan` array from `revise.py due` in order: it is already interleaved across chapters and item types with prerequisite material drifted early — do not re-sort it, do not group it by chapter, and do not name an item's chapter before it is graded. Conduct each item by the recite protocol (ASSESS.md), `mode: "revise"` on every ledger line. When the due count dwarfs the block (a month away does this), run the capped plan and say what remains — the scheduler already put the most overdue material first, and tomorrow's `due` recomputes honestly from whatever happened today.

## The delayed judgment of learning

When the previous session ended a chapter, ask once, before this session's warm-up: *"Without looking — chapter {N} in one week: how much of it would you keep? 25, 50, 75, 90, or 99?"* Write it to that chapter's `conf` column (CONTENTS-FORMAT.md). The point is the delay: a next-day estimate is honest where an end-of-session one flatters — and the gap between `conf` and the chapter's measured accuracy is the calibration story the dashboard tells (`revise.py stats`).

## The chapter ladder

Tier A revision, coarse and hand-legible — the single home of these numbers:

| box | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| next gap | 1 d | 3 d | 7 d | 16 d | 35 d | 90 d |

- A chapter enters at **box 1** when its first closed-book recite passes (PASS-2.md), `due` = that day + 1 day.
- A **passing** cumulative recite moves it up one box; `due` = today + the new box's gap. A chapter at box 6 that passes stays at box 6, 90 days at a time — the ladder never retires a chapter; only `closed` status does.
- A **failing** cumulative recite drops it two boxes (floor box 1) — `due` = today + the new gap — and the misses mint or resurface cards, so the item tier picks up the slack where the chapter tier found it.
- Write `box` and `due` into CONTENTS.md at the moment they move, beside the ledger lines that moved them.

## The cumulative chapter recite

What a chapter's ladder date buys: a 5–8 item mini-recite over the *chapter as a whole* — its cues, a sample of its cards weighted toward past misses, and one integration question tying it to a chapter read since ("How does {this chapter's idea} show up in {later chapter}?" — the one item you compose fresh each time). Recite protocol as always (ASSESS.md), `mode: "revise"`. Pass/fail is judged like the original recite, and the ladder moves per the table above. It rides inside a warm-up when it fits, or becomes the Revise session's centerpiece when several chapters come due together.

## The Revise session

The pure-revision dispatch mode (SKILL.md): no new reading, the due queue is the whole agenda. Shape it from the `due` output — due chapter recites first (they inform everything after), then the interleaved item plan, sized to the student's sitting; re-queued misses close the session. It ends like any session: ledger lines all appended, CONTENTS.md columns moved, the checklist run, and a log line whose pass slot reads `revise` — `next:` usually points back at the reading (`next: ch 5`), because revision serves the read, not the other way around. When *nothing* is due anywhere, say so and celebrate briefly — an empty queue is the schedule holding, not a session wasted.
