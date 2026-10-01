# Repo rules

This repository houses agent skills following the [Agent Skills](https://agentskills.io) standard, distributed via [skills.sh](https://skills.sh) and as a Claude Code plugin.

## Invariants

- Skills live flat under `skills/<name>/`; the directory name equals the frontmatter `name`.
- Every promoted skill has a row in `README.md`'s skills table, linking its `SKILL.md` and its changelog, and an entry in `.claude-plugin/plugin.json`'s `skills` array. Run `claude plugin validate . --strict` after touching either manifest.
- `uv run scripts/validate_skills.py` enforces the invariants on this list — frontmatter, manifests, layout, versions — and CI (`.github/workflows/validate.yml`) runs it on every push and PR. Run it before committing any change under `skills/`, `changelogs/`, `README.md`, or `.claude-plugin/`. Its version checks read git history and tags, so it needs a full clone.
- Every push to main that changes a skill is a release, cut by CI. Once `validate` passes, its `release` job tags the pushed commit `<skill>--vX.Y.Z` for each version not yet tagged and `jeyabbalas-skills--vX.Y.Z` for the bundle, then publishes a GitHub release built from the changelogs. Never create, move, or delete those tags. Never reuse a version: once pushed, a version is spent, even if CI never tagged it.
- A skill's version is `metadata.version` in its `SKILL.md` frontmatter, a double-quoted `"X.Y.Z"`. The bundle's is `version` in `.claude-plugin/plugin.json`, derived from the skills'. Set neither by hand.
  - After changing anything under `skills/<name>/`, run `uv run scripts/release.py bump <name> <patch|minor|major>`. Choose the level by `README.md`'s Versions section; between two, take the higher.
  - One bump per skill per push. Re-running is safe, and the last level given wins.
  - `validate_skills.py` names every skill that needs a bump. `uv run scripts/release.py status` shows what the next push will release.
  - A new skill starts with `bump <name> major`, or `minor` for a 0.1.0 trial.
  - Removing a skill makes the bundle major. Set `plugin.json` to the version `validate_skills.py` names.
- Each skill's changes are listed in `changelogs/<name>.md`, newest first, under the `## X.Y.Z — YYYY-MM-DD` headings that `bump` writes.
  - Under each heading, write bullets on what changed for someone using the skill, not on the commits. Commits that go out in one push share one entry.
  - A major entry needs a `**Breaking:**` bullet with migration steps.
  - When a change touches what a skill copies into workspaces, the entry tells users to run `refresh-assets`. That means three-pass and chapterhouse `assets/`, and schemify's `SHIPPED` files, `scripts/validate.py` included.
  - Changelogs are exempt from the table-of-contents rule. A removed skill's changelog goes with it.
- `uv run scripts/check_links.py [skill ...]` rechecks every URL and `#anchor` in the skills' docs against the live web, including pages that now only say they have moved. Third-party sites flake, so it stays out of push and PR checks: `.github/workflows/links.yml` runs it on the 1st of each month and fails, emailing whoever last edited its schedule, when a link breaks. GitHub's runners are off the NIH network, so pages restricted to it answer 403 there, and hosts that exist only inside it (`*.ncifcrf.gov`) don't resolve; both are listed as unverified. A run from the NIH network or VPN covers them. Run it yourself after editing links.
- Frontmatter `description` and `argument-hint` values are always double-quoted. An unquoted `": "` makes the YAML unparseable, and installers respond by dropping the skill from their listing with no error — the skill simply appears not to exist.
- Install commands live only in `README.md`'s install section; change them there first, then propagate anywhere they are quoted.
- Example output lives under `examples/<skill-name>/` — a `README.md` beside the demo files. Nothing under `examples/` is read by skills at runtime; non-redistributable inputs (paper PDFs) and regenerable fixtures stay untracked, with restore commands in the example's README.

## Skill authoring rules

- `SKILL.md` body stays under 500 lines and acts as a router: every sub-file is `UPPER-KEBAB.md` in the skill root, linked from `SKILL.md` exactly one level deep with an explicit loading condition ("Read X.md when Y"). No orphaned sub-files; no duplication — each fact lives in exactly one file.
- Any file over 100 lines starts with a table of contents.
- `./` in skill docs refers to skill-directory siblings only, and the skill directory is read-only at runtime. Workspace paths are written bare (`papers/<slug>/...`), resolving from the user's invocation directory. Nothing may ever be written into an installed skill directory.
- User-invoked skills set `disable-model-invocation: true` (SKILL.md frontmatter) and `policy.allow_implicit_invocation: false` (`agents/openai.yaml`), and their `description` is human-facing (no trigger lists).
- Scripts are EXECUTED, never read as reference: Python with PEP 723 inline metadata, run via `uv run` with a documented pip fallback at each call site; helpful error messages; JSON to stdout where agents parse output.
- Templates and `assets/` are the source of visual consistency for generated pages: skill docs reference template slots and published CSS classes, never ad-hoc styling.
