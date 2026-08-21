# Decisions — LARK sleep-diary study

- D001 · 2026-08-21 · package · sentinels adopted from source: -666 structural NA, -888 don't know · the dictionary's Coding column states them; no others appear · user-confirmed · active
- D002 · 2026-08-21 · package · grain: one row is one participant-night · steward interview · user-confirmed · active
- D003 · 2026-08-21 · package · two categories: Participant (baseline traits) and Sleep (nightly diary) · dictionary has no sections; grouping proposed from variable meaning; steward approved the table whole · user-confirmed · active
- D004 · 2026-08-21 · sleep_diary/participant.site_id · added; string codes "01"–"05" with clinic names · not in the dictionary; steward instructed it as the link key and supplied the site list · user-confirmed · active
- D005 · 2026-08-21 · sleep_diary/sleep.sleep_minutes · numeric branch bounded 0–960 · dictionary states no bounds; rejects the impossible (16 h), not the rare · agent-decided · user-confirmed (review 2026-08-21) · active
- D006 · 2026-08-21 · sleep_diary/sleep.nap_minutes · numeric branch bounded 0–600 · dictionary states no bounds; a 10-hour nap is already implausible · agent-decided · user-confirmed (review 2026-08-21) · active
- D007 · 2026-08-21 · package · $id base https://schemas.example.org/lark/ (non-dereferenceable; replace before publishing) · house rule; no namespace stated by the source · agent-decided · user-confirmed (review 2026-08-21) · active
- D008 · 2026-08-21 · sleep_diary/sleep.bedtime · encode as free string · dictionary says only "hh:mm 24-hour clock" · agent-decided · superseded-by D009
- D009 · 2026-08-21 · sleep_diary/sleep.bedtime · anchored pattern ^([01][0-9]|2[0-3]):[0-5][0-9]$ · steward confirmed times are always zero-padded 24-hour · user-confirmed · active
- D010 · 2026-08-21 · sleep_diary/sleep.nap_minutes · skip/applicability pair on nap_yesterday · dictionary note "Asked only if nap_yesterday=1"; pair inferred and encoded in the mother file · agent-decided · user-confirmed (review 2026-08-21) · active
- D011 · 2026-08-21 · not-enforceable · participant_id + diary_date unique across rows · JSON Schema cannot compare rows beyond whole-record uniqueItems · agent-decided · active
- D012 · 2026-08-21 · not-enforceable · sleep_minutes ≤ bedtime-to-wake interval · arithmetic across columns; JSON Schema cannot compare fields · agent-decided · active
- D013 · 2026-08-21 · sleep_diary/sleep.melatonin_use · what are the supplement codes? · dictionary row 11 points at a coding sheet missing from this version · open · active
- D014 · 2026-08-21 · package · no real data in the repo; toy fixtures are the only test data · steward interview · user-confirmed · active
