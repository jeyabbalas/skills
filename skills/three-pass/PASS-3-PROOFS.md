Pass 3's derivation work: re-derive one of the paper's contributed equations from its assumptions, with the reader driving and you challenging every step. The product is a derivation the reader owns — and a ledger of exactly which assumptions the result stands on. This is also the sharpest tool for reviewing a paper: an assumption that fails its challenge is a finding.

Table of contents

- [Choosing a target](#choosing-a-target)
- [Protocol](#protocol)
- [Derivation document template](#derivation-document-template)
- [Rules of the game](#rules-of-the-game)

## Choosing a target

Targets are equations the paper *contributes* — derives, proposes, or proves — not standard results it merely uses (those are glossary or equation-page material). Offer the candidates from SKELETON.md's equation inventory; the reader picks. One derivation per session (SKILL.md's budget): a derivation rushed is a derivation trusted for the wrong reason.

## Protocol

1. Open `derivations/deriv-NN-<name>.md` from the template; copy the target equation verbatim with its anchor.
2. **Build the assumptions ledger first.** Walk the relevant section with the reader and list every assumption the derivation will lean on — the stated ones (`§`/`p.`) and the implicit ones you or the reader detect. Challenge each: *why is this reasonable here? when would it break?* Record the verdict in the ledger, not just in chat.
3. **Derive, reader driving.** The reader proposes each step; you check it, and when they're stuck you offer the smallest next question rather than the step itself. Every step carries its justification (algebra, an assumption from the ledger by number, a cited lemma).
4. **Flag every leap the paper makes.** Where the paper jumps ("it follows that…"), either close the gap together and mark the step `(gap in the paper — closed here)`, or record it as an open gap. Never silently smooth over a jump.
5. Close: mark `status: complete` (or leave `in progress` with the next step named), render the page (`page.html`, math per ARTIFACTS.md), turn open gaps into `todo` notes per NOTES-FORMAT.md, log line.

## Derivation document template

```md
# {Paper title} — Derivation {NN}: {equation name}
status: in progress
target: {eq (n) | footnote N | the claim, quoted}, §{…} · p.{…}

## The target
\[ {the equation, verbatim} \]

## Assumptions ledger
| # | assumption | stated? | challenged | verdict |
|---|---|---|---|---|
| A1 | {…} | §{…} / implicit | {when would it break?} | {holds here because… / suspect: …} |

## Derivation
1. {step} — {justification: algebra / A1 / eq (n−1)}
2. …

## Gaps
- {paper's leap or unresolved step} → note N{NNNN}
```

## Rules of the game

- **The ledger is the point.** A finished derivation with an empty ledger means the assumptions went unexamined — go back.
- **Challenge means challenge.** For each assumption ask what breaks without it, and whether the paper's own setting satisfies it. "Everyone assumes this" is not a verdict.
- **Verbatim target, honest steps.** The target is copied exactly; a step nobody can justify yet stays labeled a gap — an honest gap outranks a confident hand-wave.
- **The reader derives; you referee.** If you end up performing the derivation while the reader watches, slow down and hand back the pen.
- **Voice.** Like notes, a derivation document is the session's own voice — no ◆ needed inside it; quotation marks with anchors carry the paper's voice, the ledger's "stated?" column keeps the two apart.
