# schemify example — the LARK sleep-diary study

This is a complete schemify run, committed as it finished. The input was `workspace/source/dictionary.csv` — a deliberately typical bespoke data dictionary: eleven variables, codes and missing codes mixed into one "Coding / Values" column, a routing note in prose ("Asked only if nap_yesterday=1"), and one variable whose coding sheet is missing. The simulated steward was the study coordinator: they confirmed the grain and the sentinel policy, approved the two proposed categories, supplied the site list for a link key the dictionary never mentions, corrected the bedtime encoding, and chose to keep the working files at cleanup — so `PROGRESS.md`, `DECISIONS.md`, and `SOURCES.md` show exactly what schemify's state looks like at the end of a run (a steward who chooses "clean" would have those three folded into the README and deleted).

The conversion exercises most of the skill's machinery: labeled `oneOf` codes, bounded `anyOf` measures with sentinel branches, string codes with leading zeros, anchored id/date/time patterns, a skip/applicability conditional pair in the mother file, a superseded decision (D008 → D009), a deferred variable held as an open item (D013), toy PASS/FAIL fixtures with a ground-truth ledger, and both rendered pages.

## Browse it

- `workspace/json_schema/dictionary.html` — double-click it; the searchable, printable data dictionary works straight from disk, offline.
- `workspace/json_schema/playground.html` — needs a local server: `cd workspace/json_schema && python3 -m http.server 8000`, then open `http://localhost:8000/playground.html`. Click **Toy FAIL data** and hover the tinted cells — each seeded violation is explained on the cell, skip-pattern rules in the study's own words. Drop any `.json`/`.csv` onto **Check your own file**; nothing you upload leaves your browser.
- `workspace/json_schema/README.md` — the package's own front door: conventions, sentinel table, enforced routing rules, what is documented but not enforced, and the surviving open item.
- Re-run the checks yourself: `uv run workspace/json_schema/tools/validate.py summary workspace/json_schema` (or `pip install -r workspace/json_schema/tools/requirements.txt` and use `python3`). Expect: 4 schema files valid, toy PASS clean, 9/9 seeded violations caught, coverage 11/12 with one deferred.

## Restoring what git leaves out

Nothing — everything here is committed, including the rendered pages and the copied `assets/` and `tools/`. If you refresh the assets from a newer skill version (`render.py refresh-assets workspace/json_schema`), rebuild the pages afterwards (`render.py dictionary …`, `render.py playground …`).

## How to prompt the agent

Starting a run like this one, in a fresh directory containing your dictionary:

```
/schemify source/dictionary.csv
```

Mid-run, in later sessions:

```
/schemify                                   (resume from PROGRESS.md's next: pointer)
/schemify convert the sleep category
/schemify what does -666 mean in nap_minutes?
```

Steering and finishing:

```
/schemify the bedtime values are always zero-padded 24-hour — tighten it
/schemify review                            (walk every decision, finish the README)
/schemify review the sentinel decisions     (a scoped review, any time)
```

One honest note: this example was produced by the skill's author exercising the skill's own playbooks and scripts end-to-end (the fixtures, pages, and validation output are real script output); the steward's side of the conversation is simulated, as the intro says.
