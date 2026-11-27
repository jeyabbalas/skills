#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["dulwich>=1.0,<2"]
# ///
"""Version a schemify workspace on a computer without the git program.

schemify.py runs this when `git` is not installed, so the workspace keeps its history
anyway: dulwich, a Git written in Python, writes an ordinary Git repository, which
git itself reads once it is installed. Nothing here needs administrator rights.

Usage (schemify.py runs it; agents use schemify.py's commit, history and restore):
  uv run <skill-dir>/scripts/gitless.py snapshot --ws WS --message M [--first M] [--their-repo]
  uv run <skill-dir>/scripts/gitless.py history  --ws WS [--file F] [--limit N]
  uv run <skill-dir>/scripts/gitless.py restore  --ws WS --commit C --file F
Fallback:  Python 3.10+: python3 -m pip install --user "dulwich>=1.0,<2", then python3 <skill-dir>/scripts/gitless.py ...

Each command prints one JSON object. `snapshot` commits everything in the workspace
and nothing beside it. Inside a repository of the user's own it commits only with
--their-repo (they agreed), and never while they have other changes staged.
Exit codes: 0 ok, 1 error ("error", "hint").
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def out(payload: dict, code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(code)


try:
    from dulwich import porcelain
    from dulwich.ignore import IgnoreFilterManager
    from dulwich.object_store import tree_lookup_path
    from dulwich.objectspec import parse_commit
    from dulwich.repo import Repo
except ImportError as exc:                       # run without uv and without dulwich installed
    out({"ok": False, "error": f"dulwich is not installed: {exc}",
         "hint": "Run it with uv, or install it: python3 -m pip install --user \"dulwich>=1.0,<2\""}, 1)

FALLBACK_ID = b"schemify <schemify@localhost>"


def find_root(ws: Path) -> Path | None:
    for d in (ws, *ws.parents):
        if (d / ".git").exists():
            return d
    return None


def prefix_of(ws: Path, root: Path) -> str:
    rel = ws.relative_to(root).as_posix()
    return "" if rel == "." else rel + "/"


def identity(repo: Repo) -> bytes:
    cfg = repo.get_config_stack()
    try:
        return cfg.get((b"user",), b"name") + b" <" + cfg.get((b"user",), b"email") + b">"
    except KeyError:                             # no identity configured: never set the person's
        return FALLBACK_ID


def staged_paths(repo: Repo) -> list[str]:
    st = porcelain.status(repo, untracked_files="no")
    return [p.decode() if isinstance(p, bytes) else p for paths in st.staged.values() for p in paths]


def snapshot(ws: Path, message: str, first: str | None, theirs_ok: bool) -> dict:
    root = find_root(ws)
    if root and root != ws:
        if IgnoreFilterManager.from_repo(Repo(str(root))).is_ignored(prefix_of(ws, root)):
            root = None                          # their repository leaves the workspace out: give it its own
        elif not theirs_ok:                      # never a commit in someone's repository before they agree
            return {"repo": str(root), "own": False, "created": False, "via": "dulwich", "commit": None, "ask": True}
    created = root is None
    if created:
        porcelain.init(str(ws))
        Repo(str(ws)).refs.set_symbolic_ref(b"HEAD", b"refs/heads/main")
        root = ws
    repo = Repo(str(root))
    info = {"repo": str(root), "own": root == ws, "created": created, "via": "dulwich"}
    prefix = prefix_of(ws, root)
    if prefix and any(not p.startswith(prefix) for p in staged_paths(repo)):
        return {**info, "commit": None,
                "error": "the repository has other changes staged; to leave them alone, nothing was committed"}
    porcelain.add(repo, paths=[str(ws)])
    if not staged_paths(repo):
        return {**info, "commit": None}
    who = identity(repo)
    sha = porcelain.commit(repo, message=(first if created and first else message).encode("utf-8"),
                           author=who, committer=who)
    return {**info, "commit": sha.decode()[:7]}


def history(ws: Path, file: str | None, limit: int) -> dict:
    root = find_root(ws)
    if not root:
        return {"via": "dulwich", "commits": []}
    repo = Repo(str(root))
    prefix = prefix_of(ws, root)
    target = (prefix + (file or "")).rstrip("/")
    try:
        walker = repo.get_walker(max_entries=limit, paths=[target.encode()] if target else None)
        entries = list(walker)
    except KeyError:                             # no commit yet
        return {"via": "dulwich", "commits": []}
    commits = []
    for entry in entries:
        c = entry.commit
        changes = entry.changes()
        flat = [x for ch in changes for x in (ch if isinstance(ch, list) else [ch])]
        files = sorted({(x.new or x.old).path.decode()[len(prefix):] for x in flat
                        if (x.new or x.old) and (x.new or x.old).path and (x.new or x.old).path.decode().startswith(prefix)})
        commits.append({"commit": c.id.decode()[:7],
                        "date": datetime.fromtimestamp(c.commit_time, timezone.utc).date().isoformat(),
                        "message": c.message.decode("utf-8", "replace").splitlines()[0] if c.message else "",
                        "files": files[:20], **({"moreFiles": len(files) - 20} if len(files) > 20 else {})})
    return {"via": "dulwich", "commits": commits}


def restore(ws: Path, commit: str, file: str) -> dict:
    root = find_root(ws)
    if not root:
        out({"ok": False, "error": "the workspace has no history yet", "hint": "Nothing to restore from."}, 1)
    dest = (ws / file).resolve()
    if ws not in dest.parents:
        out({"ok": False, "error": f"{file} is not inside the workspace", "hint": "Give a path relative to schemify/."}, 1)
    repo = Repo(str(root))
    try:
        c = parse_commit(repo, commit.encode())
    except KeyError:
        out({"ok": False, "error": f"no commit {commit}", "hint": "Take a commit from `schemify.py history`."}, 1)
    try:
        _, sha = tree_lookup_path(repo.__getitem__, c.tree, (prefix_of(ws, root) + Path(file).as_posix()).encode())
    except KeyError:
        out({"ok": False, "error": f"{file} is not in commit {commit}",
             "hint": "`schemify.py history <file>` lists the commits that hold it."}, 1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(repo[sha].data)
    return {"via": "dulwich", "restored": Path(file).as_posix(), "from": c.id.decode()[:7]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["snapshot", "history", "restore"])
    ap.add_argument("--ws", required=True)
    ap.add_argument("--message")
    ap.add_argument("--first")
    ap.add_argument("--file")
    ap.add_argument("--commit")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--their-repo", action="store_true", help="the person agreed to commits in their repository")
    a = ap.parse_args()
    ws = Path(a.ws).expanduser().resolve()
    if not (ws / "state" / "project.json").is_file():
        out({"ok": False, "error": f"no schemify workspace at {a.ws}", "hint": "Pass the folder that holds state/project.json."}, 1)
    try:
        if a.command == "snapshot":
            if not a.message:
                out({"ok": False, "error": "snapshot needs --message", "hint": "Say what changed."}, 1)
            out({"ok": True, **snapshot(ws, a.message, a.first, a.their_repo)})
        if a.command == "history":
            out({"ok": True, **history(ws, a.file, max(1, a.limit))})
        if not (a.commit and a.file):
            out({"ok": False, "error": "restore needs --commit and --file", "hint": "Both come from `history`."}, 1)
        out({"ok": True, **restore(ws, a.commit, a.file)})
    except SystemExit:
        raise
    except Exception as exc:                     # never a bare traceback
        out({"ok": False, "error": f"dulwich failed: {exc!r}",
             "hint": "The files are saved; only the version history failed. Mention it once and carry on."}, 1)


if __name__ == "__main__":
    main()
