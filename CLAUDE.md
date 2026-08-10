# Repo rules

This repository houses agent skills following the [Agent Skills](https://agentskills.io) standard, distributed via [skills.sh](https://skills.sh) and as a Claude Code plugin.

## Invariants

- Skills live flat under `skills/<name>/`; the directory name equals the frontmatter `name`.
- Every promoted skill has a row in `README.md`'s skills table and an entry in `.claude-plugin/plugin.json`'s `skills` array. Run `claude plugin validate . --strict` after touching either manifest.
- Install commands live only in `README.md`'s install section; change them there first, then propagate anywhere they are quoted.
- Example output lives under `examples/<skill-name>/` — a `README.md` beside the demo files. Nothing under `examples/` is read by skills at runtime; non-redistributable inputs (paper PDFs) and regenerable fixtures stay untracked, with restore commands in the example's README.

## Skill authoring rules

- `SKILL.md` body stays under 500 lines and acts as a router: every sub-file is `UPPER-KEBAB.md` in the skill root, linked from `SKILL.md` exactly one level deep with an explicit loading condition ("Read X.md when Y"). No orphaned sub-files; no duplication — each fact lives in exactly one file.
- Any file over 100 lines starts with a table of contents.
- `./` in skill docs refers to skill-directory siblings only, and the skill directory is read-only at runtime. Workspace paths are written bare (`papers/<slug>/...`), resolving from the user's invocation directory. Nothing may ever be written into an installed skill directory.
- User-invoked skills set `disable-model-invocation: true` (SKILL.md frontmatter) and `policy.allow_implicit_invocation: false` (`agents/openai.yaml`), and their `description` is human-facing (no trigger lists).
- Scripts are EXECUTED, never read as reference: Python with PEP 723 inline metadata, run via `uv run` with a documented pip fallback at each call site; helpful error messages; JSON to stdout where agents parse output.
- Templates and `assets/` are the source of visual consistency for generated pages: skill docs reference template slots and published CSS classes, never ad-hoc styling.
