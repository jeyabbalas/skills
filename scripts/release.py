#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Versions, changelogs, and release tags for the skills in this repo.

Each skill carries its own version -- `metadata.version` in its SKILL.md
frontmatter -- and lists its changes in changelogs/<skill>.md. The plugin's
`version` in .claude-plugin/plugin.json is the bundle version, derived from the
skills'. A version is spent once it reaches main, so every push that changes a
skill bumps it; CI then tags `<skill>--vX.Y.Z` and `<plugin>--vX.Y.Z` and
publishes a GitHub release. README.md#versions says what each level means.

Usage:  uv run scripts/release.py status [--base REV]
        uv run scripts/release.py bump SKILL patch|minor|major
        uv run scripts/release.py publish [--base REV] [--dry-run]
        (fallback: pip install pyyaml && python3 scripts/release.py ...)

status   JSON report; exits 1 when a rule is broken. validate_skills.py runs
         the same check, so you rarely need this directly.
bump     Sets the skill's version, opens its changelog entry, and sets the
         bundle version. Safe to re-run; the last level given wins.
publish  CI only (the release job in .github/workflows/validate.yml): tags
         every untagged version at HEAD and creates the GitHub release.
         --dry-run prints the tags and notes instead, anywhere.

The base is the last pushed commit: --base, else $RELEASE_BASE (CI passes the
push's `before` or the PR's base), else the merge-base of HEAD and origin/main
-- which every push moves, so a clone that never fetched CI's tags still knows
what it already published.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LEVELS = ("patch", "minor", "major")
NUM = r"(?:0|[1-9]\d*)"
SEMVER = re.compile(rf"^({NUM})\.({NUM})\.({NUM})$")
# The Agent Skills spec forbids "--" in names, so "--v" always splits a tag.
TAG = re.compile(rf"^(?P<name>[a-z0-9]+(?:-[a-z0-9]+)*)--v(?P<ver>{NUM}\.{NUM}\.{NUM})$")
HEADING = re.compile(r"^## (?P<ver>\S+) [—–-] (?P<date>\d{4}-\d{2}-\d{2})\s*$")
METADATA_KEY = re.compile(r"^metadata:[ \t]*$")
VERSION_KEY = re.compile(r"^[ \t]+version:")
QUOTED_VERSION = re.compile(r'^[ \t]+version:[ \t]*"[^"]*"[ \t]*$')
PLUGIN_VERSION = re.compile(r'("version"\s*:\s*)"[^"]*"')
BULLET = re.compile(r"^\s*[-*] +\S")
ZERO_SHA = re.compile(r"^0*$")

CHANGELOG_HEADER = """\
# {name} changelog

Changes to [`{name}`](../skills/{name}/SKILL.md), newest first. What major, minor, and patch mean: [README → Versions](../README.md#versions).
"""

Version = tuple[int, int, int]


class ReleaseError(Exception):
    """The repo can't be checked or changed: not a git work tree, a shallow clone, and so on."""


# ----------------------------------------------------------------- versions


def parse(s: object) -> Version | None:
    m = SEMVER.match(s) if isinstance(s, str) else None
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def fmt(v: Version | None) -> str | None:
    return None if v is None else "%d.%d.%d" % v


def bumped(v: Version, level: str) -> Version:
    major, minor, patch = v
    return {"patch": (major, minor, patch + 1), "minor": (major, minor + 1, 0), "major": (major + 1, 0, 0)}[level]


def step(old: Version, new: Version) -> str | None:
    """The level that takes `old` to `new` in one bump, if any."""
    return next((level for level in LEVELS if bumped(old, level) == new), None)


def highest(levels: list[str]) -> str | None:
    return max(levels, key=LEVELS.index) if levels else None


# ---------------------------------------------------------------------- git


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    except FileNotFoundError:
        raise ReleaseError("git is not installed") from None
    if check and r.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
    return r


def run_gh(root: Path, args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    """A GitHub CLI call -- module-level so tests can stand in for GitHub."""
    try:
        return subprocess.run(["gh", *args], cwd=root, input=stdin, capture_output=True, text=True)
    except FileNotFoundError:
        raise ReleaseError("the GitHub CLI (gh) is not installed") from None


@dataclasses.dataclass(frozen=True)
class Tag:
    name: str
    commit: str


def read_tags(root: Path) -> dict[str, dict[Version, Tag]]:
    """{name: {version: tag}} for every `<name>--vX.Y.Z` tag."""
    out = git(root, "for-each-ref", "--format=%(refname:strip=2)%00%(objectname)%00%(*objectname)", "refs/tags").stdout
    tags: dict[str, dict[Version, Tag]] = {}
    for line in out.splitlines():
        ref, obj, peeled = line.split("\0")
        if m := TAG.match(ref):
            tags.setdefault(m["name"], {})[parse(m["ver"])] = Tag(ref, peeled or obj)
    return tags


def resolve_base(root: Path, given: str | None, bundle_tags: dict[Version, Tag]) -> tuple[str | None, str]:
    """(commit, how it was found) for the last pushed commit."""
    if given and not ZERO_SHA.match(given):
        r = git(root, "rev-parse", "--verify", "--quiet", f"{given}^{{commit}}", check=False)
        if r.returncode == 0:
            return r.stdout.strip(), f"given ({given[:12]})"
        print(f"release.py: base {given} is not in this clone (history rewritten?); falling back", file=sys.stderr)
    r = git(root, "merge-base", "HEAD", "origin/main", check=False)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip(), "merge-base of HEAD and origin/main"
    if bundle_tags:
        tag = bundle_tags[max(bundle_tags)]
        return tag.commit, f"newest bundle tag {tag.name}"
    return None, "none -- no origin/main and no bundle tag"


# -------------------------------------------------------------- frontmatter


def split_frontmatter(text: str) -> str | None:
    """The raw frontmatter block, read the way validate_skills.py reads it."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    return None if end == -1 else text[4 : end + 1]


def metadata_span(lines: list[str]) -> tuple[int, int] | None:
    """[start, end) of the top-level `metadata:` block among frontmatter lines."""
    for i, line in enumerate(lines):
        if METADATA_KEY.match(line.rstrip("\n")):
            j = i + 1
            while j < len(lines) and (lines[j][:1] in (" ", "\t") or not lines[j].strip()):
                j += 1
            return i, j
    return None


def read_version(text: str) -> tuple[str | None, str | None]:
    """(version, problem) from SKILL.md text. The version is returned whenever it
    is a valid X.Y.Z string; the problem covers quoting too."""
    raw = split_frontmatter(text)
    if raw is None:
        return None, "missing or unterminated '---' frontmatter block"
    try:
        fm = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None, "frontmatter is not valid YAML"
    if not isinstance(fm, dict):
        return None, "frontmatter is not a mapping"
    meta = fm.get("metadata")
    if not isinstance(meta, dict) or "version" not in meta:
        return None, None
    value = meta["version"]
    lines = raw.splitlines()
    span = metadata_span(lines)
    line = next((ln for ln in lines[span[0] + 1 : span[1]] if VERSION_KEY.match(ln)), None) if span else None
    version = value if parse(value) else None
    if version is None or line is None or not QUOTED_VERSION.match(line):
        found = line.strip() if line else f"version: {value!r}"
        return version, (
            f'metadata.version must be a double-quoted "X.Y.Z" on its own line under metadata: '
            f"(found `{found}`; an unquoted 1.10 is read as the number 1.1)"
        )
    return version, None


def without_version(text: str) -> str:
    """SKILL.md text minus its metadata.version line -- what a bump alone leaves unchanged."""
    raw = split_frontmatter(text)
    if raw is None:
        return text
    lines = raw.splitlines(keepends=True)
    span = metadata_span(lines)
    if span is None:
        return text
    i, j = span
    rest = [ln for ln in lines[i + 1 : j] if not VERSION_KEY.match(ln)]
    block = [lines[i], *rest] if any(ln.strip() for ln in rest) else []
    return "---\n" + "".join(lines[:i] + block + lines[j:]) + text[4 + len(raw) :]


def set_version(text: str, version: str) -> str:
    """SKILL.md text with metadata.version set, every other byte left alone."""
    raw = split_frontmatter(text)
    if raw is None:
        raise ReleaseError("SKILL.md has no '---' frontmatter block")
    lines = raw.splitlines(keepends=True)
    entry = f'version: "{version}"\n'
    span = metadata_span(lines)
    if span is None:
        lines.append("metadata:\n  " + entry)
    else:
        i, j = span
        k = next((k for k in range(i + 1, j) if VERSION_KEY.match(lines[k])), None)
        if k is not None:
            lines[k] = re.match(r"[ \t]+", lines[k])[0] + entry
        else:
            children = [ln for ln in lines[i + 1 : j] if ln.strip()]
            lines.insert(i + 1, (re.match(r"[ \t]+", children[0])[0] if children else "  ") + entry)
    return "---\n" + "".join(lines) + text[4 + len(raw) :]


# ---------------------------------------------------------------- changelog


@dataclasses.dataclass
class Entry:
    version: str
    date: str
    line: int  # index of the heading line
    body: list[str]  # lines up to the next heading


def read_changelog(text: str) -> tuple[list[Entry], list[str]]:
    lines = text.splitlines()
    heads = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    entries, problems = [], []
    for k, i in enumerate(heads):
        m = HEADING.match(lines[i])
        if not m or not parse(m["ver"]):
            problems.append(f"heading {lines[i]!r} is not '## X.Y.Z — YYYY-MM-DD'")
            continue
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        entries.append(Entry(m["ver"], m["date"], i, lines[i + 1 : end]))
    return entries, problems


def trimmed(lines: list[str]) -> list[str]:
    text = "\n".join(lines).strip("\n")
    return text.split("\n") if text else []


# -------------------------------------------------------------------- model


@dataclasses.dataclass
class SkillState:
    version: str | None
    published: str | None  # highest version tagged or pushed (None: never released)
    state: str  # new | pending | published | needs-bump | invalid
    level: str | None  # bump since `published`, for new and pending skills
    tag: str | None
    tagged: bool


@dataclasses.dataclass
class Model:
    root: Path
    base: str | None
    base_from: str
    mode: str  # bootstrap (first release) | release
    plugin: str
    homepage: str | None
    bundle: dict
    bundle_at_base: Version | None
    skills: dict[str, SkillState]
    removed: list[str]
    tags: dict[str, dict[Version, Tag]]
    problems: list[tuple[str, str]]
    summary: str


@dataclasses.dataclass
class Report:
    problems: list[tuple[str, str]]
    summary: str


def skill_names(root: Path) -> list[str]:
    d = root / "skills"
    return sorted(p.name for p in d.iterdir() if (p / "SKILL.md").is_file()) if d.is_dir() else []


def skills_at(root: Path, rev: str | None) -> dict[str, str | None]:
    """{skill: version} at a commit; the version is None when absent or invalid."""
    if rev is None:
        return {}
    out = git(root, "ls-tree", "-d", "--name-only", "-z", rev, "skills/").stdout
    found = {}
    for path in filter(None, out.split("\0")):
        r = git(root, "show", f"{rev}:{path}/SKILL.md", check=False)
        if r.returncode == 0:
            found[path.split("/", 1)[1]] = read_version(r.stdout)[0]
    return found


def plugin_version_at(root: Path, rev: str | None) -> Version | None:
    if rev is None:
        return None
    r = git(root, "show", f"{rev}:.claude-plugin/plugin.json", check=False)
    try:
        return parse(json.loads(r.stdout).get("version")) if r.returncode == 0 else None
    except json.JSONDecodeError:
        return None


class Changes:
    """Whether skills/<name> in the working tree differs from a commit, a version
    bump aside. Untracked files count; ignored ones don't. One diff per commit."""

    def __init__(self, root: Path):
        self.root = root
        out = git(root, "ls-files", "--others", "--exclude-standard", "-z", "--", "skills").stdout
        self.untracked = set(out.split("\0")) - {""}
        self.diffs: dict[str, set[str]] = {}

    def __call__(self, ref: str, name: str) -> bool:
        if ref not in self.diffs:
            out = git(self.root, "diff", "--name-only", "-z", ref, "--", "skills").stdout
            self.diffs[ref] = set(out.split("\0")) - {""}
        prefix = f"skills/{name}/"
        files = {f for f in self.diffs[ref] | self.untracked if f.startswith(prefix)}
        skill_md = f"{prefix}SKILL.md"
        if files - {skill_md}:
            return True
        if skill_md not in files:
            return False
        now = (self.root / skill_md).read_text() if (self.root / skill_md).is_file() else ""
        then = git(self.root, "show", f"{ref}:{skill_md}", check=False).stdout
        return without_version(now) != without_version(then)


def read_plugin(root: Path) -> dict:
    try:
        return json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise ReleaseError(f".claude-plugin/plugin.json is unreadable ({e})") from None


def build(root: Path = ROOT, base: str | None = None) -> Model:
    """Everything the three commands need, checked against the rules in README.md#versions."""
    inside, shallow = (git(root, "rev-parse", "--is-inside-work-tree", "--is-shallow-repository", check=False)
                       .stdout.split() + ["", ""])[:2]
    if inside != "true":
        raise ReleaseError(f"{root} is not a git work tree -- release checks need the repo's history")
    if shallow == "true":
        raise ReleaseError(
            "this clone is shallow -- release checks need full history and tags "
            "(CI: actions/checkout with fetch-depth: 0; locally: git fetch --unshallow)"
        )
    plugin = read_plugin(root)
    plugin_name = plugin.get("name") or "plugin"
    tags = read_tags(root)
    bundle_tags = tags.get(plugin_name, {})
    base_sha, base_from = resolve_base(root, base if base is not None else os.environ.get("RELEASE_BASE"), bundle_tags)
    at_base = skills_at(root, base_sha)
    bundle_at_base = plugin_version_at(root, base_sha)
    bootstrap = not bundle_tags and not any(at_base.values())
    names = skill_names(root)
    changed = Changes(root)
    problems: list[tuple[str, str]] = []
    skills: dict[str, SkillState] = {}

    for name in names:
        where = f"skills/{name}/SKILL.md"
        hint = f"uv run scripts/release.py bump {name} <patch|minor|major>"
        version, problem = read_version((root / where).read_text())
        if problem:
            problems.append((where, problem))
        mine = tags.get(name, {})
        published = max((v for v in (max(mine, default=None), parse(at_base.get(name))) if v), default=None)
        v = parse(version)
        st = skills[name] = SkillState(
            version, fmt(published), "invalid", None, f"{name}--v{version}" if v else None, bool(v and v in mine)
        )
        if v is None:
            if problem is None:
                problems.append((where, f"no metadata.version -- add it with: {hint}"))
            continue
        if published is None:
            st.state, st.level = "new", "minor"
        else:
            release = mine.get(published)
            ref = release.commit if release else base_sha
            how = f"tag {release.name}" if release else f"pushed in {base_sha[:7]}, not yet tagged"
            if v < published:
                problems.append((where, (
                    f"metadata.version {version} is below the published {fmt(published)} -- versions never go "
                    f"back; a revert ships as a new version: uv run scripts/release.py bump {name} patch"
                )))
            elif v == published:
                if changed(ref, name):
                    st.state = "needs-bump"
                    problems.append((f"skills/{name}", (
                        f"changed since {name} {version} was published ({how}), but metadata.version is still "
                        f"{version} -- run: {hint} (README.md#versions says which), then write its changelog bullets"
                    )))
                else:
                    st.state = "published"
            elif (level := step(published, v)) is None:
                nexts = ", ".join(f"{fmt(bumped(published, lv))} ({lv})" for lv in LEVELS)
                problems.append((where, (
                    f"metadata.version {version} does not follow the published {fmt(published)} -- "
                    f"next is {nexts}; bump sets it"
                )))
            elif not changed(ref, name):
                problems.append((f"skills/{name}", (
                    f"metadata.version is {version} but nothing in skills/{name} changed since {fmt(published)} -- "
                    f'set it back to "{fmt(published)}" and drop the {version} changelog entry'
                )))
            else:
                st.state, st.level = "pending", level
        check_changelog(root, name, st, problems)

    changelogs = root / "changelogs"
    for path in sorted(changelogs.glob("*.md")) if changelogs.is_dir() else []:
        if path.stem not in names:
            problems.append((f"changelogs/{path.name}", f"no skills/{path.stem}/ -- a removed skill's changelog goes with it"))

    removed = sorted(set(at_base) - set(names))
    changes = [(n, s.level, "new" if s.state == "new" else s.level) for n, s in skills.items() if s.state in ("new", "pending")]
    level = highest([lv for _, lv, _ in changes] + ["major"] * bool(removed))
    pv = parse(plugin.get("version"))
    tagged_bundle = max(bundle_tags, default=None)
    published_bundle = max((v for v in (tagged_bundle, bundle_at_base) if v), default=None)
    expected = None
    where = ".claude-plugin/plugin.json"
    if pv is None:
        problems.append((where, f'version must be a "X.Y.Z" string (found {plugin.get("version")!r})'))
    elif bootstrap:
        if bundle_at_base and pv <= bundle_at_base:
            problems.append((where, (
                f"version must be X.Y.Z above the published {fmt(bundle_at_base)} -- "
                f"bump sets {fmt(bumped(bundle_at_base, 'major'))}"
            )))
    else:
        start = published_bundle or (0, 0, 0)
        expected = bumped(start, level) if level else start
        if pv != expected:
            if level:
                why = ", ".join([f"{n} {kind}" for n, _, kind in changes] + [f"{n} removed" for n in removed])
                fix = "set it by hand (bump has no skill to run on)" if removed and not changes else "bump sets it"
                msg = (
                    f'version is "{fmt(pv)}"; it must be "{fmt(expected)}" -- the bundle moves by its largest '
                    f"skill change since {fmt(start)} ({why}); {fix}"
                )
            else:
                msg = (
                    f'version is "{fmt(pv)}"; it must stay "{fmt(start)}" -- no skill changed since it was '
                    f"published, and manifest edits ride along with the next release"
                )
            problems.append((where, msg))

    bundle = {
        "name": plugin_name,
        "version": plugin.get("version"),
        "published": fmt(published_bundle),
        "expected": fmt(expected),
        "level": level,
        "tag": f"{plugin_name}--v{fmt(pv)}" if pv else None,
        "tagged": bool(pv and pv in bundle_tags),
    }
    return Model(
        root, base_sha, base_from, "bootstrap" if bootstrap else "release", plugin_name, plugin.get("homepage"),
        bundle, bundle_at_base, skills, removed, tags, problems,
        summarize(plugin_name, bundle, skills, removed, bootstrap),
    )


def check_changelog(root: Path, name: str, st: SkillState, problems: list[tuple[str, str]]) -> None:
    where = f"changelogs/{name}.md"
    path = root / where
    if not path.is_file():
        problems.append((where, f"missing -- uv run scripts/release.py bump {name} <patch|minor|major> creates it"))
        return
    entries, bad = read_changelog(path.read_text())
    problems.extend((where, b) for b in bad)
    if not entries:
        problems.append((where, f"no entries -- the newest must be '## {st.version} — YYYY-MM-DD' (bump writes it)"))
        return
    top = entries[0]
    if top.version != st.version:
        problems.append((where, (
            f"newest entry is {top.version} but skills/{name} is at {st.version} -- "
            f"the top heading must be '## {st.version} — YYYY-MM-DD' (bump writes it)"
        )))
    elif not any(BULLET.match(ln) for ln in top.body):
        problems.append((where, f"the {top.version} entry has no bullets -- say what changed for someone using {name}"))
    elif st.state == "pending" and st.level == "major" and "**Breaking:**" not in "\n".join(top.body):
        problems.append((where, f"{top.version} is a major version: its entry needs a **Breaking:** bullet with migration steps"))
    versions = [parse(e.version) for e in entries]
    if any(a <= b for a, b in zip(versions, versions[1:])):
        problems.append((where, "entries must run newest first, each version once"))


def summarize(plugin: str, bundle: dict, skills: dict[str, SkillState], removed: list[str], bootstrap: bool) -> str:
    fresh = [(n, s) for n, s in skills.items() if s.state in ("new", "pending")]
    if bootstrap:
        if not fresh:
            return "First release: no skill has a metadata.version yet"
        text = "First release on next push: " + ", ".join(f"{n} {s.version}" for n, s in fresh)
        return text + f" -> {plugin} {bundle['version']}"
    if fresh or removed:
        parts = [f"{n} {s.version} ({'new' if s.state == 'new' else s.level})" for n, s in fresh]
        return "Release on next push: " + ", ".join(parts + [f"{n} removed" for n in removed]) + f" -> {plugin} {bundle['version']}"
    text = f"Nothing to release: {plugin} {bundle['version']} is current"
    waiting = [f"{n} {s.version}" for n, s in skills.items() if s.state == "published" and not s.tagged]
    if bundle["tag"] and not bundle["tagged"]:
        waiting.append(f"{plugin} {bundle['version']}")
    return text + (f"; not yet tagged: {', '.join(waiting)} (the next release run tags them)" if waiting else "")


def check(root: Path = ROOT, base: str | None = None) -> Report:
    """The release rules, for validate_skills.py."""
    m = build(root, base)
    return Report(m.problems, m.summary)


def status(m: Model) -> dict:
    return {
        "ok": not m.problems,
        "mode": m.mode,
        "base": {"rev": m.base, "from": m.base_from},
        "bundle": m.bundle,
        "skills": {n: dataclasses.asdict(s) for n, s in m.skills.items()},
        "removed": m.removed,
        "summary": m.summary,
        "problems": [{"where": w, "message": msg} for w, msg in m.problems],
    }


# --------------------------------------------------------------------- bump


def bump(root: Path, name: str, level: str, today: str | None = None) -> dict:
    if level not in LEVELS:
        raise ReleaseError(f"level must be one of {', '.join(LEVELS)} -- README.md#versions says which")
    skill_md = root / "skills" / name / "SKILL.md"
    if not skill_md.is_file():
        raise ReleaseError(f"no skills/{name}/SKILL.md")
    text = skill_md.read_text()
    raw = split_frontmatter(text)
    try:
        fm = yaml.safe_load(raw) if raw is not None else None
    except yaml.YAMLError:
        fm = None
    if not isinstance(fm, dict):
        raise ReleaseError(f"skills/{name}/SKILL.md frontmatter doesn't parse -- fix it first (validate_skills.py says how)")
    if "metadata" in fm and metadata_span(raw.splitlines()) is None:
        raise ReleaseError(f"skills/{name}/SKILL.md writes metadata inline -- rewrite it as an indented block")

    m = build(root)
    st = m.skills[name]
    published = parse(st.published)
    target = fmt(bumped(published or (0, 0, 0), level))
    if (new_text := set_version(text, target)) != text:
        skill_md.write_text(new_text)

    heading = f"## {target} — {today or dt.date.today().isoformat()}"
    path = root / "changelogs" / f"{name}.md"
    if not path.is_file():
        path.parent.mkdir(exist_ok=True)
        path.write_text(CHANGELOG_HEADER.format(name=name) + f"\n{heading}\n\n")
    else:
        log = path.read_text()
        lines = log.splitlines(keepends=True)
        entries, _ = read_changelog(log)
        top = entries[0] if entries else None
        if top and (published is None or parse(top.version) > published):
            lines[top.line] = heading + "\n"  # still unreleased: re-level it, keep its bullets
        elif top:
            lines[top.line : top.line] = [heading + "\n", "\n"]
        else:
            lines = [log.rstrip("\n") + "\n\n" + heading + "\n\n"]
        path.write_text("".join(lines))

    m = build(root)
    current = parse(m.bundle["version"])
    if m.mode == "bootstrap":
        floor = m.bundle_at_base
        new = current if current and (floor is None or current > floor) else bumped(floor or (0, 0, 0), "major")
    else:
        new = parse(m.bundle["expected"]) or current
    if new and new != current:
        plugin_path = root / ".claude-plugin" / "plugin.json"
        ptext, n = PLUGIN_VERSION.subn(rf'\g<1>"{fmt(new)}"', plugin_path.read_text(), count=1)
        if not n:
            raise ReleaseError('.claude-plugin/plugin.json has no "version" to set')
        plugin_path.write_text(ptext)
    return {
        "ok": True,
        "skill": name,
        "from": st.version,
        "to": target,
        "level": level,
        "published": st.published,
        "bundle": {"from": fmt(current), "to": fmt(new or current)},
        "changelog": f"changelogs/{name}.md",
        "next": (
            f"Under '{heading}' in changelogs/{name}.md, write what changed for someone using {name}; "
            "then run uv run scripts/validate_skills.py"
        ),
    }


# ------------------------------------------------------------------ publish


def release_notes(m: Model, head: str) -> tuple[str, str]:
    """(title, body). Built against tags that don't point at HEAD, so a re-run says the same."""
    sections, released = [], []
    for name, st in m.skills.items():
        earlier = [v for v, t in m.tags.get(name, {}).items() if t.commit != head]
        last = max(earlier, default=None)
        entries, _ = read_changelog((m.root / "changelogs" / f"{name}.md").read_text())
        fresh = entries[:1] if last is None else [e for e in entries if parse(e.version) > last]
        if not fresh:
            continue
        released.append(f"{name} {st.version}")
        lines = [f"## {name} {st.version}", ""]
        if len(fresh) == 1:
            lines += trimmed(fresh[0].body)
        else:
            for e in fresh:
                lines += [f"### {e.version} — {e.date}", "", *trimmed(e.body), ""]
        sections.append("\n".join(lines).rstrip())

    earlier_bundles = {v: t for v, t in m.tags.get(m.plugin, {}).items() if t.commit != head}
    if earlier_bundles:
        before = skills_at(m.root, earlier_bundles[max(earlier_bundles)].commit)
        gone = sorted(set(before) - set(m.skills))
        if gone:
            lines = ["## Removed", ""]
            for name in gone:
                mine = m.tags.get(name, {})
                last = f" -- last released as `{mine[max(mine)].name}`" if mine else ""
                lines.append(f"- `{name}`{last}.")
            sections.append("\n".join(lines))

    version = m.bundle["version"]
    footer = [
        "---",
        "",
        f"Skill versions in {m.plugin} {version}: " + " · ".join(f"{n} {s.version}" for n, s in m.skills.items()),
    ]
    if m.homepage:
        footer += ["", f"To install or pin this release, see [Pin a version]({m.homepage}#pin-a-version)."]
    title = f"{m.plugin} {version}" + (f" — {', '.join(released)}" if released else "")
    return title, "\n\n".join([*sections, "\n".join(footer)]) + "\n"


def publish(root: Path, base: str | None = None, dry_run: bool = False) -> dict:
    if not dry_run:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            raise ReleaseError(
                "publish runs in CI (the release job in .github/workflows/validate.yml) -- "
                "preview it with: uv run scripts/release.py publish --dry-run"
            )
        if dirty := git(root, "status", "--porcelain", "--", "skills", "changelogs", ".claude-plugin").stdout.strip():
            raise ReleaseError(f"uncommitted changes -- publish only tags commits:\n{dirty}")
        git(root, "fetch", "--quiet", "--tags", "--force", "origin")
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    result = {"ok": True, "dry_run": dry_run, "head": head, "skipped": None, "tags": [], "release": None}

    # A re-run of an older push's job: the newer release already covers it.
    plugin = read_plugin(root)
    name, pv = plugin.get("name") or "plugin", parse(plugin.get("version"))
    newest = max(read_tags(root).get(name, {}), default=None)
    if pv and newest and pv < newest:
        result["skipped"] = f"superseded by {name}--v{fmt(newest)}"
        return result

    m = build(root, base)
    if m.problems:
        return {"ok": False, "problems": [{"where": w, "message": msg} for w, msg in m.problems]}
    bundle_tag = m.bundle["tag"]
    missing = [st.tag for st in m.skills.values() if not st.tagged]
    existing = m.tags.get(m.plugin, {}).get(pv)
    if existing is None:
        missing.append(bundle_tag)
    elif existing.commit != head:
        if missing:
            raise ReleaseError(f"{bundle_tag} already exists, but {', '.join(missing)} are untagged -- bump the bundle")
        result["skipped"] = f"nothing to release: {bundle_tag} is already published"
        return result

    title, notes = release_notes(m, head)
    result["tags"] = missing
    result["release"] = {"tag": bundle_tag, "title": title, "notes": notes, "created": False}
    if dry_run:
        return result
    for tag in missing:
        tag_name, ver = TAG.match(tag).group("name", "ver")
        git(root, "tag", "-a", tag, "-m", f"{tag_name} {ver}", "HEAD")
    if missing:
        git(root, "push", "--atomic", "origin", *(f"refs/tags/{t}" for t in missing))
    if run_gh(root, ["release", "view", bundle_tag]).returncode != 0:
        r = run_gh(
            root,
            ["release", "create", bundle_tag, "--verify-tag", "--latest", "--title", title, "--notes-file", "-"],
            stdin=notes,
        )
        if r.returncode != 0:
            raise ReleaseError(f"gh release create {bundle_tag} failed: {(r.stderr or r.stdout).strip()}")
        result["release"]["created"] = True
    return result


# --------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release.py", description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status", help="JSON report of versions and rule problems")
    p.add_argument("--base", help="last pushed commit (default: $RELEASE_BASE, else merge-base with origin/main)")
    p = sub.add_parser("bump", help="set a skill's next version, its changelog heading, and the bundle version")
    p.add_argument("skill")
    p.add_argument("level", help="patch, minor, or major -- README.md#versions says which")
    p = sub.add_parser("publish", help="CI: tag untagged versions at HEAD and create the GitHub release")
    p.add_argument("--base", help="last pushed commit (default: $RELEASE_BASE, else merge-base with origin/main)")
    p.add_argument("--dry-run", action="store_true", help="print the tags and notes without creating anything")
    args = parser.parse_args(argv)

    try:
        if args.cmd == "status":
            out = status(build(ROOT, args.base))
        elif args.cmd == "bump":
            out = bump(ROOT, args.skill, args.level)
        else:
            out = publish(ROOT, args.base, args.dry_run)
    except ReleaseError as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=2, ensure_ascii=False))
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
