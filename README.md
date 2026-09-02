# Jeya's Agent Skills

Agent skills I use for my own work, shared so you (or your agent) can install them too. Skills follow the [Agent Skills](https://agentskills.io) standard — a `SKILL.md` plus supporting files — and work with Claude Code, Codex, Cursor, and other compatible harnesses.

## Skills

| Skill | What it does | Invocation |
|---|---|---|
| [`three-pass`](./skills/three-pass/SKILL.md) | Read an academic paper together in three passes of increasing depth — a bird's-eye profile, an interactive close reading, and a line-by-line derivation or reproduction — building a reading workspace that remembers you and your papers across sessions. | User-invoked |
| [`handoff`](./skills/handoff/SKILL.md) | Compact the current conversation into a portable handoff document, so a fresh agent — in another harness, another directory, or another person's hands — can pick the work up without you re-explaining it. | User-invoked |
| [`schemify`](./skills/schemify/SKILL.md) | Turn a bespoke data dictionary — Excel, CSV, PDF, whatever the study ships — into a validated package of interlinked JSON Schema files, working with you as the data steward: interviews for what the files don't say, toy-data unit tests for every rule (skip patterns and sentinel codes included), browsable web pages for feedback, and progress that persists across sessions. | User-invoked |
| [`chapterhouse`](./skills/chapterhouse/SKILL.md) | Study a whole academic book together — chapter by chapter, or section by section when the going is steep — in three passes of increasing depth — an inspectional survey that maps and plans the read, an analytical read where every chapter ends in a closed-book recitation, and a synthesis pass of critique, re-creation, and a cumulative exam — building a study workspace of Cornell notes, flashcard decks, and a spaced-revision schedule that remembers you, your books, and what's due across sessions. | User-invoked |

## Install

Two routes, two philosophies. The **Claude Code plugin** installs the whole set as a managed, read-only bundle that updates when I ship. **[skills.sh](https://skills.sh)** copies editable skill files into your project, so you can hack on them and make them your own. Pick one — installing both leaves you with every skill twice.

### Claude Code (plugin)

```
/plugin marketplace add jeyabbalas/skills
/plugin install jeyabbalas-skills@jeyabbalas
```

Update later with `/plugin marketplace update jeyabbalas`.

### Any agent (Claude Code, Codex, Cursor, …) — via skills.sh

```bash
npx skills@latest add jeyabbalas/skills --skill three-pass handoff schemify chapterhouse
```

Names are space-separated after one `--skill`; drop the ones you don't want. This copies the skills into your project as files you own. Pull updates with `npx skills@latest update`.

### Or just tell your agent

Paste this to any coding agent and it will install the skills itself:

> Install the agent skills `three-pass`, `handoff`, `schemify`, and `chapterhouse` from the GitHub repo `jeyabbalas/skills`. Preferred route: run `npx skills@latest add jeyabbalas/skills --skill three-pass handoff schemify chapterhouse` and accept the defaults for the agent you are running in. If you are Claude Code and prefer the managed plugin, instead run `/plugin marketplace add jeyabbalas/skills` then `/plugin install jeyabbalas-skills@jeyabbalas`. If both routes fail, clone `https://github.com/jeyabbalas/skills` to a temporary directory and copy the folders `skills/three-pass/` (including its `scripts/`, `templates/`, and `assets/`), `skills/handoff/`, `skills/schemify/` (including its `scripts/`, `templates/`, and `assets/`), and `skills/chapterhouse/` (including its `scripts/`, `templates/`, and `assets/`) into your skills directory (Claude Code: `~/.claude/skills/`). Finish by verifying all four skills are listed as available and telling me the exact phrase to invoke each one.

## Using `three-pass`

Invoke it in the directory you want to use as your reading workspace:

```
/three-pass path/to/paper.pdf
/three-pass 1706.03762
/three-pass "Attention Is All You Need"
```

The first run introduces the three-pass method and interviews you about your background; every later session resumes from the markdown state the skill keeps in the workspace.

A complete example workspace — two papers, all three passes, every artifact type — lives in [`examples/three-pass/`](./examples/three-pass/), with a README of copy-able prompts.

## Using `handoff`

Invoke it at the moment the work has to travel, optionally naming what the next session is for:

```
/handoff
/handoff "continue the reproduction in the prototype repo, under Codex"
```

It writes one markdown file to your OS's temporary directory: the live thread — what's in flight, why, what's next — plus a *suggested skills* section for the next agent. Secrets are redacted, and anything already written down (specs, plans, ADRs, issues, commits, diffs) is referenced by path or URL rather than copied.

Reach for it only when something is moving: a different harness, a different directory, a colleague, or a side task you want a second agent to fork off while your own session stays open. If nothing is moving, `/compact` is the cheaper move. Ask for the path back and copy the file somewhere durable — temp directories get cleared between sessions and on reboot.

## Using `schemify`

Invoke it in the repository where the JSON Schema package should live, pointing at your data dictionary — however bespoke its format:

```
/schemify path/to/data_dictionary.xlsx
/schemify metadata/                      (a directory of dictionary files)
/schemify                                (resume — it proposes the next step from its notes)
/schemify review the sentinel decisions
```

The first run inventories the dictionary, interviews you about the study — what is one row? which codes mean missing or not-applicable? — proposes topic categories for you to approve, then converts category by category, validating each against toy PASS/FAIL data (survey skip patterns and sentinel codes included) and re-rendering two web pages for your review: `dictionary.html`, a searchable, printable data dictionary that opens by double-click — keyword search built in, semantic search a switch away — and `playground.html`, a live validator you can drop your own JSON or CSV into, entirely in your browser. Large dictionaries deliberately run over several sittings: progress, every judgment call, and every source live as markdown beside the schemas, so any later `/schemify` picks up exactly where the last session stopped, and the closing review walks each decision with you before the working files are cleaned away. The finished package stands alone — schemas, toy data, a bundled validator, and the pages — usable by collaborators and CI without this skill installed.

A complete example package — a small synthetic sleep-diary study, source dictionary included — lives in [`examples/schemify/`](./examples/schemify/), with a README of copy-able prompts.

## Using `chapterhouse`

Invoke it in the directory you want as your study workspace, pointing at your book:

```
/chapterhouse path/to/book.pdf
/chapterhouse path/to/book.epub
/chapterhouse                    (resume — the due check runs first, then the next: pointer)
/chapterhouse revise             (a pure revision session: whatever the schedule says is due)
```

The first run introduces the method — Adler's inspectional/analytical/syntopical reading, SQ3R, retrieval practice, spaced repetition — and interviews you about your background and study cadence. Pass 1 maps the book (chapters, difficulty, prerequisites), classifies what kind of book it is, offers to collect the questions you want it to answer — reading cover to cover is a fine answer — and plans the read at chapter or section pace. Pass 2 takes one chapter, or one section when the going is steep, per session into a Cornell note and will not mark a chapter done without a closed-book recitation — misses become flashcards. If a book is too hard to read unaided, ask for scaffolded reading: before each section, it prepares the assumed background and a step-by-step guide so you can read the book's own pages on your own. Pass 3 is critique, re-creation from memory, and a cumulative exam. Every session opens by checking what the review ledger says is due, and everything renders into a local, printable study site: chapter pages, quiz decks (printable as questions-only or with the answer key), a progress dashboard with calibration scores, and a chapter prerequisite map.

A complete example workspace — Allen Downey's *Think Stats* surveyed, two chapters studied with real decks and review history, and a third chapter mid-study in scaffolded, section-paced mode — lives in [`examples/chapterhouse/`](./examples/chapterhouse/), with a README of copy-able prompts.

## Credits

`handoff` is copied as-is from Matt Pocock's [mattpocock/skills](https://github.com/mattpocock/skills) (`skills/productivity/handoff/`), MIT-licensed; his notice travels with it in [`skills/handoff/LICENSE`](./skills/handoff/LICENSE).

## License

[MIT](./LICENSE)
