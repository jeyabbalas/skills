# Jeya's Agent Skills

Agent skills I use for my own work, shared so you (or your agent) can install them too. Skills follow the [Agent Skills](https://agentskills.io) standard — a `SKILL.md` plus supporting files — and work with Claude Code, Codex, Cursor, and other compatible harnesses.

## Skills

| Skill | What it does | Invocation |
|---|---|---|
| [`three-pass`](./skills/three-pass/SKILL.md) | Read an academic paper together in three passes of increasing depth — a bird's-eye profile, an interactive close reading, and a line-by-line derivation or reproduction — building a reading workspace that remembers you and your papers across sessions. | User-invoked |
| [`handoff`](./skills/handoff/SKILL.md) | Compact the current conversation into a portable handoff document, so a fresh agent — in another harness, another directory, or another person's hands — can pick the work up without you re-explaining it. | User-invoked |

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
npx skills@latest add jeyabbalas/skills --skill three-pass handoff
```

Names are space-separated after one `--skill`; drop the ones you don't want. This copies the skills into your project as files you own. Pull updates with `npx skills@latest update`.

### Or just tell your agent

Paste this to any coding agent and it will install the skills itself:

> Install the agent skills `three-pass` and `handoff` from the GitHub repo `jeyabbalas/skills`. Preferred route: run `npx skills@latest add jeyabbalas/skills --skill three-pass handoff` and accept the defaults for the agent you are running in. If you are Claude Code and prefer the managed plugin, instead run `/plugin marketplace add jeyabbalas/skills` then `/plugin install jeyabbalas-skills@jeyabbalas`. If both routes fail, clone `https://github.com/jeyabbalas/skills` to a temporary directory and copy the folders `skills/three-pass/` (including its `scripts/`, `templates/`, and `assets/`) and `skills/handoff/` into your skills directory (Claude Code: `~/.claude/skills/`). Finish by verifying both skills are listed as available and telling me the exact phrase to invoke each one.

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

## Credits

`handoff` is copied as-is from Matt Pocock's [mattpocock/skills](https://github.com/mattpocock/skills) (`skills/productivity/handoff/`), MIT-licensed; his notice travels with it in [`skills/handoff/LICENSE`](./skills/handoff/LICENSE).

## License

[MIT](./LICENSE)
