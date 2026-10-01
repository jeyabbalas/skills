#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8", "pyyaml>=6"]
# ///
"""Tests for scripts/release.py: the version, changelog, and tag rules that
validate_skills.py enforces, `bump`, and the `publish` step CI runs.

Run:  uv run tests/test_release.py
      (fallback: pip install pytest pyyaml && pytest tests/test_release.py)

Every test works in a throwaway repo -- a bare `origin` and a clone of it, two
skills, plugin.json at 0.6.0 -- with git cut off from the user's config and
GitHub replaced by a stand-in that records each `gh` call. The two starting
points (before and after the first release) are built once per session and
copied into each test, since git calls dominate the run time.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
TODAY = "2026-10-01"

SKILL = """\
---
name: {name}
description: "The {name} skill."
---

Body of {name}. Read [GUIDE.md](GUIDE.md) when you need the guide.
"""

README = """\
# Demo

| Skill | What it does |
|---|---|
| [`alpha`](./skills/alpha/SKILL.md) · [changelog](./changelogs/alpha.md) | A. |
| [`beta`](./skills/beta/SKILL.md) · [changelog](./changelogs/beta.md) | B. |
"""


# ------------------------------------------------------------------ helpers


def git(cwd: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise AssertionError(f"git {' '.join(args)} failed:\n{r.stderr}")
    return r.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def push(work: Path, message: str) -> tuple[str, str]:
    """Commit everything and push it; returns (before, after), like a push event."""
    before = git(work, "rev-parse", "--verify", "--quiet", "origin/main", check=False)
    git(work, "add", "-A")
    git(work, "commit", "--quiet", "-m", message)
    git(work, "push", "--quiet", "origin", "main")
    return before, git(work, "rev-parse", "HEAD")


def note(work: Path, name: str, bullet: str = "- Something a user of it would notice.") -> None:
    """Write a bullet under the newest changelog heading, as the maintainer would."""
    path = work / "changelogs" / f"{name}.md"
    lines = path.read_text().splitlines(keepends=True)
    i = next(i for i, line in enumerate(lines) if line.startswith("## "))
    lines.insert(i + 1, f"\n{bullet}\n")
    path.write_text("".join(lines))


def edit(work: Path, name: str, text: str = "revised") -> None:
    (work / "skills" / name / "GUIDE.md").write_text(f"# {name} guide, {text}\n")


def set_plugin_version(work: Path, version: str) -> None:
    path = work / ".claude-plugin" / "plugin.json"
    data = json.loads(path.read_text())
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n")


def set_skill_version_line(work: Path, name: str, line: str) -> None:
    path = work / "skills" / name / "SKILL.md"
    text = path.read_text()
    old = next(ln for ln in text.splitlines() if ln.startswith("  version:"))
    path.write_text(text.replace(old, line))


def messages(rel, work: Path, base: str | None = None) -> list[str]:
    return [f"{where}: {msg}" for where, msg in rel.build(work, base).problems]


def ci_publish(rel, work: Path, monkeypatch, base: str | None):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    try:
        return rel.publish(work, base)
    finally:
        monkeypatch.delenv("GITHUB_ACTIONS")


class FakeGitHub:
    """Stands in for `gh`: remembers releases, every call, and every attempt's notes."""

    def __init__(self):
        self.releases: dict[str, str] = {}
        self.calls: list[list[str]] = []
        self.attempts: list[str] = []
        self.fail_create = False

    def __call__(self, root, args, stdin=None):
        self.calls.append(args)
        if args[:2] == ["release", "view"]:
            return subprocess.CompletedProcess(args, 0 if args[2] in self.releases else 1, "", "")
        if args[:2] == ["release", "create"]:
            self.attempts.append(stdin)
            if self.fail_create:
                self.fail_create = False
                return subprocess.CompletedProcess(args, 1, "", "HTTP 502: Bad Gateway")
            self.releases[args[2]] = stdin
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(f"unexpected gh call: {args}")


# ----------------------------------------------------------------- fixtures


@pytest.fixture(scope="session")
def rel():
    # Registered before it runs: its dataclasses need sys.modules, and
    # validate_skills.py's `import release` must find this same module.
    spec = importlib.util.spec_from_file_location("release", SCRIPTS / "release.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["release"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session", autouse=True)
def isolated_git():
    """Git without the user's config, with a fixed identity, outside any CI run."""
    mp = pytest.MonkeyPatch()
    mp.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    mp.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        mp.setenv(f"GIT_{who}_NAME", "Test")
        mp.setenv(f"GIT_{who}_EMAIL", "test@example.com")
    for var in ("RELEASE_BASE", "GITHUB_ACTIONS"):
        mp.delenv(var, raising=False)
    yield
    mp.undo()


def make_repo(at: Path) -> Path:
    """<at>/origin.git, bare, and <at>/work, a clone of it: skills alpha and beta,
    no versions, plugin.json at 0.6.0, all pushed."""
    origin = at / "origin.git"
    git(at, "init", "--quiet", "--bare", "-b", "main", str(origin))
    work = at / "work"
    git(at, "clone", "--quiet", str(origin), str(work))
    git(work, "symbolic-ref", "HEAD", "refs/heads/main")
    for name in ("alpha", "beta"):
        write(work / "skills" / name / "SKILL.md", SKILL.format(name=name))
        edit(work, name, "first draft")
    plugin = {
        "name": "demo-skills",
        "version": "0.6.0",
        "homepage": "https://example.com/demo",
        "skills": ["./skills/alpha", "./skills/beta"],
    }
    write(work / ".claude-plugin" / "plugin.json", json.dumps(plugin, indent=2) + "\n")
    write(work / ".gitignore", ".DS_Store\n")
    write(work / "README.md", README)
    push(work, "Initial commit")
    return work


def copy_repo(template: Path, to: Path) -> Path:
    shutil.copytree(template, to, symlinks=True, dirs_exist_ok=True)
    git(to / "work", "remote", "set-url", "origin", str(to / "origin.git"))
    return to / "work"


@pytest.fixture(scope="session")
def templates(rel, isolated_git, tmp_path_factory):
    """The two starting points: before the first release, and just after it
    (alpha and beta at 1.0.0, tagged, published) with the GitHub it saw."""
    plain = tmp_path_factory.mktemp("plain")
    make_repo(plain)
    after = tmp_path_factory.mktemp("released")
    work = copy_repo(plain, after)
    fake = FakeGitHub()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(rel, "run_gh", fake)
        for name in ("alpha", "beta"):
            rel.bump(work, name, "major", today=TODAY)
            note(work, name, "- First versioned release.")
        before, _ = push(work, "Version every skill")
        out = ci_publish(rel, work, mp, before)
    assert out["ok"] and out["release"]["created"], out
    return {"plain": plain, "released": after, "gh": fake}


@pytest.fixture
def repo(templates, tmp_path):
    """A clone of a bare origin: skills alpha and beta, no versions, plugin.json at 0.6.0."""
    return copy_repo(templates["plain"], tmp_path)


@pytest.fixture
def gh(rel, monkeypatch):
    fake = FakeGitHub()
    monkeypatch.setattr(rel, "run_gh", fake)
    return fake


@pytest.fixture
def released(templates, tmp_path, gh):
    """The repo after its first release: alpha and beta at 1.0.0, tagged and published."""
    gh.releases.update(templates["gh"].releases)
    gh.calls.extend(templates["gh"].calls)
    return copy_repo(templates["released"], tmp_path)


# ------------------------------------------------------------ first release


def test_first_release_needs_versions_then_passes(rel, repo):
    msgs = messages(rel, repo)
    assert "skills/alpha/SKILL.md: no metadata.version -- add it with: uv run scripts/release.py bump alpha <patch|minor|major>" in msgs
    assert ".claude-plugin/plugin.json: version must be X.Y.Z above the published 0.6.0 -- bump sets 1.0.0" in msgs

    out = rel.bump(repo, "alpha", "major", today=TODAY)
    assert (out["to"], out["bundle"]) == ("1.0.0", {"from": "0.6.0", "to": "1.0.0"})
    rel.bump(repo, "beta", "major", today=TODAY)
    assert "changelogs/beta.md: the 1.0.0 entry has no bullets -- say what changed for someone using beta" in messages(rel, repo)

    note(repo, "alpha")
    note(repo, "beta")
    m = rel.build(repo)
    assert m.problems == [] and m.mode == "bootstrap"
    assert m.summary == "First release on next push: alpha 1.0.0, beta 1.0.0 -> demo-skills 1.0.0"


def test_first_release_bundle_must_rise(rel, repo):
    for name in ("alpha", "beta"):
        rel.bump(repo, name, "major", today=TODAY)
        note(repo, name)
    set_plugin_version(repo, "0.6.0")
    assert messages(rel, repo) == [
        ".claude-plugin/plugin.json: version must be X.Y.Z above the published 0.6.0 -- bump sets 1.0.0"
    ]


# --------------------------------------------------------- change detection


def test_clean_after_release(rel, released):
    m = rel.build(released)
    assert m.problems == [] and m.mode == "release"
    assert m.summary == "Nothing to release: demo-skills 1.0.0 is current"


def test_edit_without_bump_names_the_command(rel, released):
    edit(released, "alpha")
    [(where, msg)] = rel.build(released).problems
    assert where == "skills/alpha"
    assert "tag alpha--v1.0.0" in msg
    assert "uv run scripts/release.py bump alpha <patch|minor|major>" in msg


def test_untracked_file_counts(rel, released):
    write(released / "skills" / "alpha" / "NOTES.md", "new\n")
    assert [where for where, _ in rel.build(released).problems] == ["skills/alpha"]


def test_ignored_file_does_not_count(rel, released):
    write(released / "skills" / "alpha" / ".DS_Store", "junk")
    assert rel.build(released).problems == []


def test_mode_change_counts(rel, released):
    (released / "skills" / "alpha" / "GUIDE.md").chmod(0o755)
    assert [where for where, _ in rel.build(released).problems] == ["skills/alpha"]


# --------------------------------------------------------------------- bump


def test_bump_patch(rel, released):
    edit(released, "alpha")
    out = rel.bump(released, "alpha", "patch", today=TODAY)
    assert (out["from"], out["to"], out["bundle"]) == ("1.0.0", "1.0.1", {"from": "1.0.0", "to": "1.0.1"})
    assert '  version: "1.0.1"\n' in (released / "skills" / "alpha" / "SKILL.md").read_text()
    assert json.loads((released / ".claude-plugin" / "plugin.json").read_text())["version"] == "1.0.1"
    assert f"\n## 1.0.1 — {TODAY}\n" in (released / "changelogs" / "alpha.md").read_text()


def test_bump_twice_is_harmless(rel, released):
    edit(released, "alpha")
    paths = ["skills/alpha/SKILL.md", "changelogs/alpha.md", ".claude-plugin/plugin.json"]
    rel.bump(released, "alpha", "patch", today=TODAY)
    once = {p: (released / p).read_text() for p in paths}
    rel.bump(released, "alpha", "patch", today=TODAY)
    assert {p: (released / p).read_text() for p in paths} == once


def test_bump_escalation_relevels_the_open_entry(rel, released):
    edit(released, "alpha")
    rel.bump(released, "alpha", "patch", today=TODAY)
    note(released, "alpha", "- Kept across the re-level.")
    out = rel.bump(released, "alpha", "minor", today=TODAY)
    log = (released / "changelogs" / "alpha.md").read_text()
    assert out["to"] == "1.1.0" and out["bundle"]["to"] == "1.1.0"
    assert f"## 1.1.0 — {TODAY}\n\n- Kept across the re-level.\n" in log and "## 1.0.1" not in log
    assert rel.build(released).problems == []


def test_bump_adds_metadata_and_leaves_other_bytes(rel, repo):
    before = (repo / "skills" / "alpha" / "SKILL.md").read_text()
    rel.bump(repo, "alpha", "major", today=TODAY)
    after = (repo / "skills" / "alpha" / "SKILL.md").read_text()
    assert after == before.replace('skill."\n---\n', 'skill."\nmetadata:\n  version: "1.0.0"\n---\n')


def test_bump_keeps_other_metadata(rel, repo):
    path = repo / "skills" / "alpha" / "SKILL.md"
    path.write_text(path.read_text().replace('skill."\n---', 'skill."\nmetadata:\n    author: "me"\n---'))
    rel.bump(repo, "alpha", "major", today=TODAY)
    assert 'metadata:\n    version: "1.0.0"\n    author: "me"\n---' in path.read_text()


def test_new_skill_counts_from_zero(rel, released):
    write(released / "skills" / "gamma" / "SKILL.md", SKILL.format(name="gamma"))
    edit(released, "gamma")
    out = rel.bump(released, "gamma", "minor", today=TODAY)
    assert (out["published"], out["to"], out["bundle"]["to"]) == (None, "0.1.0", "1.1.0")
    note(released, "gamma")
    m = rel.build(released)
    assert m.problems == []
    assert m.summary == "Release on next push: gamma 0.1.0 (new) -> demo-skills 1.1.0"


def test_bump_refuses_unknown_level_and_skill(rel, released):
    with pytest.raises(rel.ReleaseError, match="level must be one of"):
        rel.bump(released, "alpha", "huge")
    with pytest.raises(rel.ReleaseError, match="no skills/ghost/SKILL.md"):
        rel.bump(released, "ghost", "patch")


# -------------------------------------------------------------------- rules


def test_version_never_goes_back(rel, released):
    set_skill_version_line(released, "alpha", '  version: "0.9.0"')
    assert any("metadata.version 0.9.0 is below the published 1.0.0" in m for m in messages(rel, released))


def test_version_never_skips(rel, released):
    edit(released, "alpha")
    set_skill_version_line(released, "alpha", '  version: "1.0.2"')
    assert any(
        "1.0.2 does not follow the published 1.0.0 -- next is 1.0.1 (patch), 1.1.0 (minor), 2.0.0 (major)" in m
        for m in messages(rel, released)
    )


def test_bump_without_a_change_is_rejected(rel, released):
    rel.bump(released, "alpha", "patch", today=TODAY)
    note(released, "alpha")
    assert any("metadata.version is 1.0.1 but nothing in skills/alpha changed since 1.0.0" in m for m in messages(rel, released))


def test_bundle_takes_the_largest_level(rel, released):
    edit(released, "alpha")
    edit(released, "beta")
    rel.bump(released, "alpha", "patch", today=TODAY)
    out = rel.bump(released, "beta", "minor", today=TODAY)
    note(released, "alpha")
    note(released, "beta")
    m = rel.build(released)
    assert out["bundle"]["to"] == "1.1.0" and m.problems == []
    assert m.summary == "Release on next push: alpha 1.0.1 (patch), beta 1.1.0 (minor) -> demo-skills 1.1.0"


def test_hand_edited_bundle_names_the_value(rel, released):
    edit(released, "alpha")
    rel.bump(released, "alpha", "patch", today=TODAY)
    note(released, "alpha")
    set_plugin_version(released, "2.0.0")
    assert messages(rel, released) == [
        '.claude-plugin/plugin.json: version is "2.0.0"; it must be "1.0.1" -- the bundle moves by its '
        "largest skill change since 1.0.0 (alpha patch); bump sets it"
    ]


def test_manifest_edit_alone_is_not_a_release(rel, released):
    set_plugin_version(released, "1.0.1")
    assert messages(rel, released) == [
        '.claude-plugin/plugin.json: version is "1.0.1"; it must stay "1.0.0" -- no skill changed since it '
        "was published, and manifest edits ride along with the next release"
    ]


def test_removing_a_skill_makes_the_bundle_major(rel, released):
    shutil.rmtree(released / "skills" / "beta")
    (released / "changelogs" / "beta.md").unlink()
    [msg] = messages(rel, released)
    assert 'it must be "2.0.0"' in msg and "(beta removed); set it by hand" in msg
    set_plugin_version(released, "2.0.0")
    m = rel.build(released)
    assert m.problems == [] and m.summary == "Release on next push: beta removed -> demo-skills 2.0.0"


def test_major_needs_a_breaking_bullet(rel, released):
    edit(released, "alpha")
    rel.bump(released, "alpha", "major", today=TODAY)
    note(released, "alpha", "- Reworked the guide.")
    assert messages(rel, released) == [
        "changelogs/alpha.md: 2.0.0 is a major version: its entry needs a **Breaking:** bullet with migration steps"
    ]
    note(released, "alpha", "- **Breaking:** the guide moved; re-read it before your next session.")
    assert rel.build(released).problems == []


# ------------------------------------------------------- spent versions


def test_pushed_version_is_spent_before_ci_tags_it(rel, released):
    edit(released, "alpha")
    rel.bump(released, "alpha", "patch", today=TODAY)
    note(released, "alpha")
    push(released, "alpha: fix")  # its release run never happens
    edit(released, "alpha", "revised again")
    [(where, msg)] = rel.build(released).problems
    assert where == "skills/alpha" and "alpha 1.0.1 was published (pushed in" in msg and "not yet tagged" in msg


def test_stale_local_tags_are_covered_by_origin_main(rel, released, gh, monkeypatch, tmp_path):
    edit(released, "alpha")
    rel.bump(released, "alpha", "patch", today=TODAY)
    note(released, "alpha")
    before, _ = push(released, "alpha: fix")
    ci = tmp_path / "ci"
    git(tmp_path, "clone", "--quiet", str(tmp_path / "origin.git"), str(ci))
    assert ci_publish(rel, ci, monkeypatch, before)["tags"] == ["alpha--v1.0.1", "demo-skills--v1.0.1"]
    assert "alpha--v1.0.1" not in git(released, "tag", "-l").split()  # this clone never fetched it
    edit(released, "alpha", "revised again")
    [(where, msg)] = rel.build(released).problems
    assert where == "skills/alpha" and "alpha 1.0.1 was published" in msg


def test_unbumped_change_under_a_later_push_is_caught_by_its_tag(rel, released):
    edit(released, "alpha")
    push(released, "alpha: unbumped")  # CI's validate fails on this push
    write(released / "README.md", README + "\nMore.\n")
    before, _ = push(released, "README: more")
    [(where, msg)] = rel.build(released, before).problems
    assert where == "skills/alpha" and "(tag alpha--v1.0.0)" in msg


def test_missing_base_falls_back(rel, released, capsys):
    m = rel.build(released, "1234567890abcdef1234567890abcdef12345678")
    assert m.base_from == "merge-base of HEAD and origin/main" and m.problems == []
    assert "is not in this clone" in capsys.readouterr().err


def test_shallow_clone_is_refused(rel, released, tmp_path):
    shallow = tmp_path / "shallow"
    git(tmp_path, "clone", "--quiet", "--depth", "1", (tmp_path / "origin.git").as_uri(), str(shallow))
    with pytest.raises(rel.ReleaseError, match="shallow"):
        rel.build(shallow)


# ---------------------------------------------------------------- changelog


def test_changelog_top_must_match_the_version(rel, released):
    path = released / "changelogs" / "alpha.md"
    path.write_text(path.read_text().replace("## 1.0.0", "## 1.0.9"))
    assert any("newest entry is 1.0.9 but skills/alpha is at 1.0.0" in m for m in messages(rel, released))


def test_changelog_runs_newest_first(rel, released):
    path = released / "changelogs" / "alpha.md"
    path.write_text(path.read_text() + f"\n## 0.5.0 — {TODAY}\n\n- b\n\n## 0.7.0 — {TODAY}\n\n- c\n")
    assert messages(rel, released) == ["changelogs/alpha.md: entries must run newest first, each version once"]


def test_changelog_heading_format(rel, released):
    path = released / "changelogs" / "alpha.md"
    path.write_text(path.read_text().replace("## 1.0.0 — ", "## v1.0.0 — "))
    assert any("is not '## X.Y.Z — YYYY-MM-DD'" in m for m in messages(rel, released))


def test_changelog_accepts_any_dash(rel, released):
    path = released / "changelogs" / "alpha.md"
    text = path.read_text()
    for dash in ("-", "–"):
        path.write_text(text.replace(" — ", f" {dash} "))
        assert rel.build(released).problems == []


def test_orphan_changelog(rel, released):
    write(released / "changelogs" / "ghost.md", "# ghost changelog\n")
    assert messages(rel, released) == [
        "changelogs/ghost.md: no skills/ghost/ -- a removed skill's changelog goes with it"
    ]


# -------------------------------------------------------------- frontmatter


def test_unquoted_float_version_is_rejected(rel, released):
    set_skill_version_line(released, "alpha", "  version: 1.10")
    [msg] = messages(rel, released)
    assert msg.startswith("skills/alpha/SKILL.md: metadata.version must be a double-quoted")
    assert "found `version: 1.10`" in msg


def test_unquoted_semver_breaks_the_quoting_rule(rel, released):
    set_skill_version_line(released, "alpha", "  version: 1.0.0")
    [msg] = messages(rel, released)
    assert "double-quoted" in msg and "found `version: 1.0.0`" in msg


# ------------------------------------------------------------------ publish


def test_publish_dry_run(rel, repo, gh):
    for name in ("alpha", "beta"):
        rel.bump(repo, name, "major", today=TODAY)
        note(repo, name, f"- First versioned release of {name}.")
    out = rel.publish(repo, dry_run=True)
    assert out["tags"] == ["alpha--v1.0.0", "beta--v1.0.0", "demo-skills--v1.0.0"]
    assert out["release"]["title"] == "demo-skills 1.0.0 — alpha 1.0.0, beta 1.0.0"
    notes = out["release"]["notes"]
    assert "## alpha 1.0.0\n\n- First versioned release of alpha." in notes
    assert "Skill versions in demo-skills 1.0.0: alpha 1.0.0 · beta 1.0.0" in notes
    assert "(https://example.com/demo#pin-a-version)" in notes
    assert git(repo, "tag", "-l") == "" and gh.calls == []


def test_publish_tags_and_releases(rel, released, gh, tmp_path):
    origin = tmp_path / "origin.git"
    assert git(origin, "tag", "-l").split() == ["alpha--v1.0.0", "beta--v1.0.0", "demo-skills--v1.0.0"]
    assert git(origin, "cat-file", "-t", "alpha--v1.0.0") == "tag"  # annotated
    assert "tagger Test <test@example.com>" in git(origin, "cat-file", "-p", "alpha--v1.0.0")
    [create] = [c for c in gh.calls if c[:2] == ["release", "create"]]
    assert create[2] == "demo-skills--v1.0.0"
    assert "--verify-tag" in create and "--latest" in create and create[-2:] == ["--notes-file", "-"]


def test_publish_rerun_after_a_github_failure(rel, released, gh, monkeypatch):
    edit(released, "alpha")
    rel.bump(released, "alpha", "patch", today=TODAY)
    note(released, "alpha")
    before, _ = push(released, "alpha: fix")
    gh.fail_create = True
    with pytest.raises(rel.ReleaseError, match="HTTP 502"):
        ci_publish(rel, released, monkeypatch, before)
    out = ci_publish(rel, released, monkeypatch, before)
    assert out["tags"] == [] and out["release"]["created"] is True
    assert gh.releases["demo-skills--v1.0.1"] == gh.attempts[-2]  # the same notes as the failed attempt


def test_publish_readme_only_push_releases_nothing(rel, released, gh, monkeypatch):
    write(released / "README.md", README + "\nMore.\n")
    before, _ = push(released, "README: more")
    out = ci_publish(rel, released, monkeypatch, before)
    assert out["skipped"] == "nothing to release: demo-skills--v1.0.0 is already published"
    assert list(gh.releases) == ["demo-skills--v1.0.0"]


def test_publish_superseded_run_skips(rel, released, gh, monkeypatch):
    first = git(released, "rev-parse", "HEAD")
    edit(released, "alpha")
    rel.bump(released, "alpha", "patch", today=TODAY)
    note(released, "alpha")
    before, _ = push(released, "alpha: fix")
    ci_publish(rel, released, monkeypatch, before)
    git(released, "checkout", "--quiet", first)
    out = ci_publish(rel, released, monkeypatch, None)
    assert out["skipped"] == "superseded by demo-skills--v1.0.1"


def test_publish_notes_cover_versions_never_tagged(rel, released, gh, monkeypatch):
    edit(released, "alpha")
    rel.bump(released, "alpha", "patch", today=TODAY)
    note(released, "alpha", "- First fix.")
    push(released, "alpha: first fix")  # its release run never happens
    edit(released, "alpha", "revised again")
    rel.bump(released, "alpha", "patch", today=TODAY)
    note(released, "alpha", "- Second fix.")
    before, _ = push(released, "alpha: second fix")
    out = ci_publish(rel, released, monkeypatch, before)
    assert out["tags"] == ["alpha--v1.0.2", "demo-skills--v1.0.2"]
    assert out["release"]["title"] == "demo-skills 1.0.2 — alpha 1.0.2"
    notes = out["release"]["notes"]
    assert f"### 1.0.2 — {TODAY}\n\n- Second fix." in notes and f"### 1.0.1 — {TODAY}\n\n- First fix." in notes
    assert "## beta" not in notes


def test_publish_refuses_outside_ci(rel, released):
    with pytest.raises(rel.ReleaseError, match="runs in CI"):
        rel.publish(released)


# -------------------------------------------------------------- integration


def test_validate_skills_runs_the_release_checks(rel, repo, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("validate_skills", SCRIPTS / "validate_skills.py")
    vs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vs)
    monkeypatch.setattr(vs, "ROOT", repo)
    monkeypatch.setattr(vs, "SKILLS", repo / "skills")
    monkeypatch.setattr(vs, "failures", [])

    for name in ("alpha", "beta"):
        rel.bump(repo, name, "major", today=TODAY)
    assert vs.main() == 1
    assert "changelogs/alpha.md: the 1.0.0 entry has no bullets" in capsys.readouterr().out

    vs.failures.clear()
    note(repo, "alpha")
    note(repo, "beta")
    assert vs.main() == 0
    out = capsys.readouterr().out
    assert "OK: 2 skill(s) valid -- alpha, beta" in out
    assert "First release on next push: alpha 1.0.0, beta 1.0.0 -> demo-skills 1.0.0" in out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
