#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Check the repo invariants that break distribution silently.

The failure this guards against: a SKILL.md whose YAML frontmatter does not
parse is not reported as an error by the skills.sh installer -- the skill is
just dropped from the repo's listing, so `skills add ... --skill <name>` says
the skill does not exist. An unquoted ": " inside a description is enough.

Usage:  uv run scripts/validate_skills.py
        (fallback: pip install pyyaml && python3 scripts/validate_skills.py)

Exits 0 when every check passes, 1 otherwise, printing one line per failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
MAX_SKILL_BODY_LINES = 500
TOC_LINE_THRESHOLD = 100

failures: list[str] = []


def fail(where: str, msg: str) -> None:
    failures.append(f"{where}: {msg}")


def split_frontmatter(text: str) -> str | None:
    """Return the raw frontmatter block, or None if the delimiters are absent."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    return None if end == -1 else text[4 : end + 1]


def check_skill(d: Path) -> None:
    name = d.name
    sk = d / "SKILL.md"
    if not sk.is_file():
        fail(f"skills/{name}", "no SKILL.md")
        return

    text = sk.read_text()
    raw = split_frontmatter(text)
    if raw is None:
        fail(f"skills/{name}/SKILL.md", "missing or unterminated '---' frontmatter block")
        return

    try:
        fm = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        detail = str(e).splitlines()[0]
        fail(
            f"skills/{name}/SKILL.md",
            f"frontmatter is not valid YAML ({detail}) -- installers drop this skill silently. "
            "A ':' or '#' in a plain scalar is the usual cause; wrap the value in double quotes.",
        )
        return
    if not isinstance(fm, dict):
        fail(f"skills/{name}/SKILL.md", "frontmatter is not a mapping")
        return

    if fm.get("name") != name:
        fail(f"skills/{name}/SKILL.md", f"name is {fm.get('name')!r}, must equal the directory name {name!r}")
    if not str(fm.get("description", "")).strip():
        fail(f"skills/{name}/SKILL.md", "description is missing or empty")

    # House rule: quote the free-text scalars, so an edit that introduces a
    # colon cannot turn into the silent-drop bug above.
    for key in ("description", "argument-hint"):
        m = re.search(rf"^{re.escape(key)}: (.+)$", raw, re.M)
        if m and not (m.group(1).startswith('"') and m.group(1).endswith('"')):
            fail(f"skills/{name}/SKILL.md", f"{key} must be wrapped in double quotes")

    body = text[len(raw) + 8 :]
    if (n := len(body.splitlines())) > MAX_SKILL_BODY_LINES:
        fail(f"skills/{name}/SKILL.md", f"body is {n} lines, limit is {MAX_SKILL_BODY_LINES}")

    for sub in sorted(p for p in d.glob("*.md") if p.name != "SKILL.md"):
        rel = f"skills/{name}/{sub.name}"
        sub_text = sub.read_text()
        if f"({sub.name})" not in body and f"(./{sub.name})" not in body:
            fail(rel, "not linked from SKILL.md (orphaned sub-file)")
        if len(sub_text.splitlines()) > TOC_LINE_THRESHOLD and "table of contents" not in sub_text[:4000].lower():
            fail(rel, f"over {TOC_LINE_THRESHOLD} lines but has no table of contents")

    for cfg in sorted((d / "agents").glob("*.y*ml")) if (d / "agents").is_dir() else []:
        rel = f"skills/{name}/agents/{cfg.name}"
        try:
            agent = yaml.safe_load(cfg.read_text())
        except yaml.YAMLError as e:
            fail(rel, f"not valid YAML ({str(e).splitlines()[0]})")
            continue
        if cfg.stem == "openai" and fm.get("disable-model-invocation") is True:
            implicit = (agent or {}).get("policy", {}).get("allow_implicit_invocation")
            if implicit is not False:
                fail(
                    rel,
                    "SKILL.md sets disable-model-invocation: true, so this file must set "
                    "policy.allow_implicit_invocation: false",
                )


def check_manifests(names: list[str]) -> None:
    plugin_path = ROOT / ".claude-plugin" / "plugin.json"
    try:
        listed = json.loads(plugin_path.read_text()).get("skills", [])
    except (OSError, json.JSONDecodeError) as e:
        fail(".claude-plugin/plugin.json", f"unreadable ({e})")
    else:
        expected = {f"./skills/{n}" for n in names}
        for missing in sorted(expected - set(listed)):
            fail(".claude-plugin/plugin.json", f"skills array is missing {missing!r}")
        for extra in sorted(set(listed) - expected):
            fail(".claude-plugin/plugin.json", f"skills array lists {extra!r}, which is not a skill directory")

    readme = (ROOT / "README.md").read_text()
    for n in names:
        if f"](./skills/{n}/SKILL.md)" not in readme:
            fail("README.md", f"no skills-table row linking ./skills/{n}/SKILL.md")


def main() -> int:
    if not SKILLS.is_dir():
        print(f"no skills/ directory under {ROOT}", file=sys.stderr)
        return 1

    dirs = sorted(d for d in SKILLS.iterdir() if d.is_dir())
    for d in dirs:
        check_skill(d)
    check_manifests([d.name for d in dirs])

    if failures:
        print(f"{len(failures)} problem(s) found:\n")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"OK: {len(dirs)} skill(s) valid -- {', '.join(d.name for d in dirs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
