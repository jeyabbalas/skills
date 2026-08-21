`DECISIONS.md`, beside PROGRESS.md, is the package's memory of judgment — every place the schemas say more, less, or other than the source dictionary, and on whose authority. The end review is a walk of this file; a clean ledger is what makes the package defensible. Entries append; nothing is deleted.

## Template

```md
# Decisions — {study name}

- D001 · {YYYY-MM-DD} · package · sentinels adopted from source: -666/-777/-888 · dictionary §1.2 states them · user-confirmed · active
- D002 · {YYYY-MM-DD} · sleep_diary/sleep.sleep_minutes · numeric branch bounded 0–960 · dictionary states no bounds; rejects the impossible, not the rare · agent-decided · active
- D003 · {YYYY-MM-DD} · sleep_diary/sleep.caffeine_after_noon · is -888 the only missing code here? · label sheet lists none, questionnaire shows "don't know" box · open · active
- D004 · {YYYY-MM-DD} · not-enforceable · sleep_minutes ≤ time in bed · arithmetic across columns; JSON Schema cannot compare fields · agent-decided · active
```

One line per decision: `D{NNN} · date · scope · decision · why/source · confidence · status`.

## Rules

- **What earns a line**: adopting or adapting a sentinel; a bound the source doesn't state; an interpretation of ambiguous or contradictory coding; a variable renamed or re-typed; a category assignment the steward might dispute; a skip pattern inferred rather than quoted; anything excluded, added, or left unenforced (scope `not-enforceable`); every real-data ruling. Transcribing what the source states verbatim is not a decision.
- **Confidence is the review's sort key**: `user-confirmed` (the steward said so; the why names when) · `agent-decided` (your judgment, not yet ratified) · `open` (unresolved — the decision column holds the *question*; the open lines are the question queue ELICIT.md batches).
- **Resolution edits confidence in place and nothing else** — `open` becomes `user-confirmed ({date})` when answered; apply the answer to the schemas in the same session or make it the `next:` unit.
- **Supersede, never rewrite.** A changed ruling appends a new line and sets the old line's status to `superseded-by D{NNN}`. Ended lines keep telling the history.
- **Ids** are `D001`, `D002`, … zero-padded to three; scan for the highest and increment; never reuse.
- **Scope is a uniform path** — `package`, `{table}`, `{table}/{category}`, `{table}/{category}.{variable}`, or `not-enforceable` — so grep carves the ledger: `grep "· open ·"` is the question queue, `grep "not-enforceable"` is the README's unenforced list, `grep "sleep\."` is one variable's history.
