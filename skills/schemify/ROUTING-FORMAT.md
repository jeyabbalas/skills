`ROUTING.csv`, beside VARIABLES.csv, is the routing register — every rule the sources state, the steward told you, or you expect, with where each stands. The routing check reconciles it against the mother files, so it stays after cleanup, like VARIABLES.csv. It is an index: the mother owns the encoding, the ledger owns who said so and why, this file owns the lifecycle. How rules are found and decided: ROUTING.md.

## Template

```csv
id,table,trigger,targets,rule,evidence,source,decision,status,notes
R001,,nap_yesterday,nap_minutes,nap_yesterday=0 → nap_minutes=-666 (=1 → not -666),quoted,"dictionary.csv row 9 ""Asked only if nap_yesterday=1""",D010,encoded,
R002,,ever_smoker,cigs_per_day;age_started;years_smoked,ever_smoker=2 → all three 777 (smokers: not 777),implied,"codes sheet B41 ""777 = N/A (never smoker)""",D021,waiting,waits for: tobacco_history
R003,,parity,age_first_birth,parity=0 → age_first_birth=777,inferred,domain: births asked of parous women,D032,proposed,counts (consent D004): 0 of 812 parity-0 rows carry an age
R004,,ever_smoker,cigs_per_day,ever_smoker=2 → cigs_per_day=0 (pin; no twin),steward,steward 2026-09-18,D033,confirmed,encode with tobacco_history
R005,,site_phase,diet_block,phase-2 sites only,quoted,questionnaire p.3,D034,not-enforceable,site_phase never delivered
```

## Rules

- **Fixed ten-column header.** `table` stays blank in single-table packages; a rule never crosses tables or rows.
- **One row is one routing fact** — a gate value and its consequences. A skip/applicability pair is one row and one id, and both halves carry the id in their `$comment` (SKIP-PATTERNS.md).
- **`trigger`** is the gate variable (`;`-separated for an any-of trigger); **`targets`** are the dependents, `;`-separated. Names are schema property names, exactly.
- **`rule`** is a one-line gist in the source's own codes. The mother's `$comment` is the authoritative text; never let the two drift.
- **Ids** are `R001`, `R002`, … zero-padded to three; scan for the highest and increment; never reuse, never delete.
- **`evidence`** is the origin, one of `quoted · implied · steward · inferred` (what each licenses: ROUTING.md). `inferred` rows exist only under a `full` policy.
- **`source`** says where the evidence lives: a SOURCES.md row, a dictionary location, `domain: …`, or `steward {date}`.
- **`decision`** cites the ledger line. Optional for `quoted` and `waiting` rows; required from the moment a row is `proposed` (that line *is* the proposal); **required before an `inferred` row may be `encoded`** — the validator refuses otherwise.
- **Statuses move only on their events**: `waiting` (a named variable is not yet a property — unconverted or deferred) · `proposed` (both ends exist; its `open` ledger line is in the queue) · `confirmed` (the steward's yes; the mother not yet edited — never leave a session here without a `next:` naming it) · `encoded` (the id is in the mother and fixtures exist) · `declined` (the steward's no, or the policy; the line says which) · `not-enforceable` (cross-table, cross-row, an undelivered gate, or beyond the standard).
- **`notes`** holds `waits for: {category or variable}[; …]`, counts from real data, and reasons — nothing the other columns already say.
- **Edited in place, not appended.** History lives in DECISIONS.md; a changed fact rewrites the row and supersedes the line.
- **Header-only means "audited, none"**; a missing file means never audited (ROUTING.md's migration). Reconciled by `validate.py routing` (VALIDATE.md); stays after cleanup (LAYOUT.md).
