# Jeya's Agent Skills

Agent skills I use for my own work, shared so you (or your agent) can install them too. Skills follow the [Agent Skills](https://agentskills.io) standard — a `SKILL.md` plus supporting files — and work with Claude Code, Codex, Cursor, and other compatible harnesses.

## Skills

| Skill | What it does | Invocation |
|---|---|---|
| [`three-pass`](./skills/three-pass/SKILL.md) | Read an academic paper together in three passes of increasing depth — a bird's-eye profile, an interactive close reading, and a line-by-line derivation or reproduction — building a reading workspace that remembers you and your papers across sessions. | User-invoked |

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
npx skills@latest add jeyabbalas/skills --skill=three-pass
```

This copies the skill into your project as files you own. Pull updates with `npx skills@latest update three-pass`.

### Or just tell your agent

Paste this to any coding agent and it will install the skill itself:

> Install the agent skill `three-pass` from the GitHub repo `jeyabbalas/skills`. Preferred route: run `npx skills@latest add jeyabbalas/skills --skill=three-pass` and accept the defaults for the agent you are running in. If you are Claude Code and prefer the managed plugin, instead run `/plugin marketplace add jeyabbalas/skills` then `/plugin install jeyabbalas-skills@jeyabbalas`. If both routes fail, clone `https://github.com/jeyabbalas/skills` to a temporary directory and copy the entire `skills/three-pass/` folder (including `scripts/`, `templates/`, and `assets/`) into your skills directory (Claude Code: `~/.claude/skills/three-pass`). Finish by verifying the skill is listed as available and telling me the exact phrase to invoke it.

## Using `three-pass`

Invoke it in the directory you want to use as your reading workspace:

```
/three-pass path/to/paper.pdf
/three-pass 1706.03762
/three-pass "Attention Is All You Need"
```

The first run introduces the three-pass method and interviews you about your background; every later session resumes from the markdown state the skill keeps in the workspace.

A complete example workspace — two papers, all three passes, every artifact type — lives in [`examples/three-pass/`](./examples/three-pass/), with a README of copy-able prompts.

## License

[MIT](./LICENSE)
