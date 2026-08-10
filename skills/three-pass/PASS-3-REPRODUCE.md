Pass 3's reproduction work: turn the paper into something that runs. First inventory what reproduction needs, then let the reader choose a track — reuse the authors' code, build a minimal implementation on toy data, or build the full thing. Reproduce = re-derive the paper's own findings; replicate = carry the idea to data the reader cares about. Complex builds run as a phased plan whose phases can execute in independent sessions.

Table of contents

- [The inventory](#the-inventory)
- [INVENTORY.md template](#inventorymd-template)
- [Choosing a track](#choosing-a-track)
- [Track: reuse the authors' code](#track-reuse-the-authors-code)
- [Track: minimal implementation](#track-minimal-implementation)
- [Track: full implementation](#track-full-implementation)
- [The phased plan](#the-phased-plan)
- [Phase prompts](#phase-prompts)
- [The walkthrough](#the-walkthrough)

## The inventory

Before any code: one session hunting down what reproduction requires, into `reproduction/INVENTORY.md`. Identify each algorithm and write its pseudocode *from the paper's description* (cite `§`/`p.` per line block — divergence between pseudocode and prose is a finding). Locate the authors' code (paper links, footnotes, a web search of title + "github"; record commit/tag if found). Inventory the data (what, where, access conditions) and every hyperparameter and training detail the paper states — and, separately, the ones it *doesn't* state (these are reproduction risks; list them explicitly).

## INVENTORY.md template

```md
# Reproduction inventory — {title}

## Algorithms
### {Algorithm name} (§{…} · p.{…})
```text
{pseudocode, line-anchored to the paper}
```

## Authors' code
- {repo URL · commit/tag · license} — or "none found ({date}, searched: {where})"

## Data
- {dataset · size · where · access: open / on request / controlled}

## Hyperparameters & training details
| item | value | source |
|---|---|---|
| {…} | {…} | §{…} / p.{…} |

## Not stated by the paper
- {every detail reproduction needs that the paper omits — each is a risk and a choice you'll have to make}
```

## Choosing a track

Present the three tracks with one honest line each — reuse (fastest to numbers, least understanding built), minimal (understanding per hour is highest; numbers won't match the paper's), full (real reproduction or replication; the long road) — plus what the inventory implies (no code found → reuse is off; controlled data → full means a synthetic mimic). The reader picks; record `track:` in PAPER.md. Tracks compose: minimal first, then grow it toward full, is a fine path.

## Track: reuse the authors' code

Get their repo running as *they* describe (their README, their environment, their versions — isolate the environment and record every deviation you're forced into). Then run the smallest experiment that produces a paper-comparable number, and compare honestly in `walkthrough.md`. While it runs, map their code to the paper: which file implements which section — that mapping is the reuse track's real understanding artifact.

## Track: minimal implementation

Karpathy-style: the smallest program that exercises the paper's core contribution, on data you control.

- **Toy data first.** Design a generative recipe (schema, sizes, seeds — record all three in PLAN.md) that is *minimal but sufficient*: it need not mimic the original schema, but it must exhibit the property the method exploits — chosen so that success is visible (the method should beat an obvious baseline on it, or reproduce a qualitative behavior the paper shows).
- **Minimal means readable.** One file if possible, plain loops before frameworks, no configuration systems, no abstraction the core idea doesn't need. Every component ties to a paper anchor — if a piece of code can't name its `§`, ask whether the paper needs it or you invented it.
- **Build it with the reader**, then walk it (below). The goal is that the reader could rebuild it alone next week.

## Track: full implementation

The complete method. Data: obtain the original if access allows (help the reader through the access process when there is one); otherwise build a full-schema synthetic mimic — same fields, same scales, the complex properties that matter (imbalance, censoring, correlation structure — whatever the paper's analyses depend on), with the generative recipe recorded. Implementation follows the phased plan below — a full build is nearly always phased. Faithfulness first: match the paper's stated details exactly, take every unstated detail from the "Not stated" list as an explicit recorded decision, and only then optimize.

## The phased plan

`reproduction/PLAN.md` is an index over self-contained phase specs — same discipline as LIBRARY.md: gist and link, never the content.

```md
# Reproduction plan — {title}
goal: {verbatim from PAPER.md} · track: {…}
toy data: {generative recipe · sizes · seed} (if applicable)

## Phases
| # | phase | objective (one line) | deliverable | status | spec |
|---|---|---|---|---|---|
| 1 | Data | {…} | code/data.py + fixture | done {date} | phases/phase-1.md |
| 2 | Model | {…} | {…} | in progress | phases/phase-2.md |

## Decisions so far
- {one line each, pointing at the phase that decided it}
```

Each `phases/phase-N.md` must stand alone: **objective**; **paper grounding** (the equations/sections it implements, with anchors); **inputs** (paths of prior phases' outputs in `code/`); **deliverables**; **acceptance checks** (runnable: "pytest passes", "loss falls below X on the fixture", "shapes match eq (4)"); **out of scope** (what later phases own). Self-containment wins over the no-restate law here: a phase spec may repeat the recipe verbatim, with PLAN.md's copy authoritative. Phase outputs live under `code/` (subdirectories like `code/data/`, `code/results/` as the specs choose). Phases small enough that one session finishes one — one phase per session is the budget.

## Phase prompts

For each phase, generate `reproduction/prompts/phase-N-prompt.md` — a prompt the reader can paste into a *fresh* session (or you can hand to a subagent, when the harness has them — prefer that when available, one subagent per phase, sequentially). The prompt must work with no skill installed:

```md
You are implementing phase {N} of a paper reproduction. Work only inside {workspace path}.
Read, in order:
1. papers/{slug}/reproduction/PLAN.md — the plan and decisions so far
2. papers/{slug}/reproduction/phases/phase-{N}.md — your phase spec (your only scope)
3. papers/{slug}/reproduction/INVENTORY.md — only the sections the spec names
4. papers/{slug}/paper.pdf pages {a–b} — only if the spec says so
Implement the phase deliverables into papers/{slug}/reproduction/code/, explaining each piece
to the user as you go and tying it to the paper idea it implements. Stop when every acceptance
check in the spec passes — run them and show the output. Before ending: set this phase's row in
PLAN.md to done with today's date, append any decision you made to "Decisions so far" (one line),
and add one line to the "## Session log" in papers/{slug}/PAPER.md:
- {date} · pass 3 · phase {N}: {what} · next: phase {N+1}
Do not touch other phases' code or specs.
```

Fill every `{…}` concretely when generating — the prompt is finished text, not a template, when it lands in `prompts/`; drop or mark "skip" any read line the phase doesn't need. Tell the reader the workflow: one fresh session per phase, paste the prompt, and come back here between phases if they want the oversight view (you resume by reading PLAN.md's status column alone).

## The walkthrough

After the build (any track), write `walkthrough.md` / `walkthrough.html` (`page.html`; ARTIFACTS.md): component by component, what each piece of code does and which paper idea it implements (anchor every tie), what the run produced versus what the paper reports, and — ◆-marked — where you'd point the reader next (replication targets, ablations worth trying, ideas from their `idea` notes). Then walk it in chat: run the code together, stepping through the mapping. The reproduction is done when the reader can explain the run's numbers, not when the run exits 0.
