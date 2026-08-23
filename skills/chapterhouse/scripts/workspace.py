#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Scaffold and lint a chapterhouse study workspace.

Standard library only — runs with plain `python3` (uv not required). All
subcommands print JSON to stdout and exit non-zero on failure.

  init [DIR]            Create assets/ (copying book-study.css/js from the
                        installed skill) and books/ in DIR (default: cwd).
                        Idempotent; reports if existing assets are outdated.
                        Never touches paper-reader.* or a bare VERSION — a
                        shelf may share its directory with a three-pass
                        reading workspace.
  add-book --slug S [--file PATH] [DIR]
                        Validate the slug (surname+year-short-title, e.g.
                        downey2014-think-stats), create books/S/, and copy the
                        book to books/S/book.pdf or book.epub when --file is
                        given (magic-byte checked; DjVu refused with a
                        conversion hint). Deeper directories are created
                        lazily by later work.
  refresh-assets [DIR]  Overwrite assets/book-study.* from the skill copy
                        (upgrades every page at once). Touches nothing else.
  check [DIR]           Lint the workspace: every .html has a same-basename
                        sister .md (case-insensitive; assets/ exempt), every
                        relative href/src resolves, no absolute-path or
                        skill-directory references inside pages.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = ["book-study.css", "book-study.js"]
STAMP = "VERSION-book-study"
SLUG = re.compile(r"^[a-z][a-z-]*[0-9]{4}-[a-z0-9][a-z0-9-]{0,48}$")
LINK = re.compile(r'(?:href|src)="([^"]+)"')


def out(payload, code=0):
    print(json.dumps(payload, indent=2))
    sys.exit(code)


def asset_version():
    h = hashlib.sha256()
    for name in ASSETS:
        h.update((SKILL_DIR / "assets" / name).read_bytes())
    return h.hexdigest()[:12]


def copy_assets(root):
    (root / "assets").mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        shutil.copy2(SKILL_DIR / "assets" / name, root / "assets" / name)
    version = asset_version()
    (root / "assets" / STAMP).write_text(version + "\n")
    return version


def cmd_init(args):
    root = Path(args.dir)
    created = []
    if not (root / "books").exists():
        (root / "books").mkdir(parents=True)
        created.append("books/")
    stamp = root / "assets" / STAMP
    if not stamp.exists():
        version = copy_assets(root)
        created.append("assets/ (version {})".format(version))
        out({"ok": True, "created": created, "assets_version": version})
    current = stamp.read_text().strip()
    latest = asset_version()
    out(
        {
            "ok": True,
            "created": created,
            "assets_version": current,
            "note": (
                "assets are up to date"
                if current == latest
                else "assets are outdated (skill has {}) — run refresh-assets".format(latest)
            ),
        }
    )


def book_kind(path):
    """Return 'pdf' or 'epub' after verifying magic bytes; fail on anything else."""
    head = path.read_bytes()[:1024]
    if head[:4] == b"AT&T":
        out(
            {
                "ok": False,
                "error": path.name + " is a DjVu file, not a PDF or EPUB.",
                "hint": (
                    "Convert it first: install DjVuLibre (brew install djvulibre / "
                    "apt install djvulibre-bin), run `ddjvu -format=pdf {} book.pdf`, "
                    "then re-run add-book with the PDF."
                ).format(path.name),
            },
            1,
        )
    if b"%PDF" in head:
        return "pdf"
    if head[:2] == b"PK" and zipfile.is_zipfile(path):
        try:
            with zipfile.ZipFile(path) as zf:
                if zf.read("mimetype").strip() == b"application/epub+zip":
                    return "epub"
        except (KeyError, zipfile.BadZipFile):
            pass
    out(
        {
            "ok": False,
            "error": path.name + " does not look like a PDF or an EPUB.",
            "hint": "Check the download; landing pages often save as HTML.",
        },
        1,
    )


def cmd_add_book(args):
    root = Path(args.dir)
    if not SLUG.match(args.slug):
        out(
            {
                "ok": False,
                "error": "Slug {!r} does not match the convention.".format(args.slug),
                "hint": (
                    "surname+year-short-title, lowercase kebab, ≤40 chars of title: "
                    "downey2014-think-stats, weinberg2013-biology-of-cancer"
                ),
            },
            1,
        )
    book_dir = root / "books" / args.slug
    if book_dir.exists():
        out(
            {
                "ok": False,
                "error": "books/{} already exists.".format(args.slug),
                "hint": (
                    "If this is a different book, extend the short title with more "
                    "title words until unique (never numeric suffixes)."
                ),
            },
            1,
        )
    book_dir.mkdir(parents=True)
    result = {"ok": True, "dir": str(book_dir)}
    if args.file:
        src = Path(args.file)
        if not src.is_file():
            out({"ok": False, "error": "Book file not found: " + args.file, "hint": ""}, 1)
        kind = book_kind(src)
        dest = book_dir / ("book." + kind)
        shutil.copy2(src, dest)
        result["file"] = str(dest)
        result["format"] = kind
    out(result)


def cmd_refresh(args):
    root = Path(args.dir)
    if not (root / "assets").exists():
        out({"ok": False, "error": "No assets/ here — run init first.", "hint": ""}, 1)
    version = copy_assets(root)
    out({"ok": True, "assets_version": version})


def check_links(html_file, root, problems):
    text = html_file.read_text(errors="replace")
    for target in LINK.findall(text):
        if re.match(r"^(https?:|mailto:|data:|#|javascript:)", target):
            continue
        clean = target.split("#")[0].split("?")[0]
        if not clean:
            continue
        if clean.startswith("/") or clean.startswith("file:"):
            problems.append(
                {"file": str(html_file.relative_to(root)), "issue": "absolute path: " + target}
            )
            continue
        if ".claude/skills" in clean or "skills/chapterhouse/" in clean:
            problems.append(
                {
                    "file": str(html_file.relative_to(root)),
                    "issue": "references the installed skill directory: " + target,
                }
            )
            continue
        if not (html_file.parent / clean).exists():
            problems.append(
                {"file": str(html_file.relative_to(root)), "issue": "broken link: " + target}
            )


def cmd_check(args):
    root = Path(args.dir)
    problems = []
    for html_file in sorted(root.rglob("*.html")):
        rel = html_file.relative_to(root)
        if rel.parts and rel.parts[0] == "assets":
            continue
        siblings = {p.stem.lower(): p for p in html_file.parent.glob("*.md")}
        if html_file.stem.lower() not in siblings:
            problems.append(
                {"file": str(rel), "issue": "no sister markdown ({}.md)".format(html_file.stem)}
            )
        check_links(html_file, root, problems)
    ok = not problems
    out({"ok": ok, "problems": problems}, 0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("dir", nargs="?", default=".")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("add-book")
    p.add_argument("--slug", required=True)
    p.add_argument("--file", default=None)
    p.add_argument("dir", nargs="?", default=".")
    p.set_defaults(fn=cmd_add_book)

    p = sub.add_parser("refresh-assets")
    p.add_argument("dir", nargs="?", default=".")
    p.set_defaults(fn=cmd_refresh)

    p = sub.add_parser("check")
    p.add_argument("dir", nargs="?", default=".")
    p.set_defaults(fn=cmd_check)

    args = ap.parse_args()
    if Path(args.dir).resolve() == SKILL_DIR or SKILL_DIR in Path(args.dir).resolve().parents:
        out(
            {
                "ok": False,
                "error": "Refusing to operate inside the installed skill directory.",
                "hint": "Run from the study workspace (the directory the skill was invoked in).",
            },
            1,
        )
    args.fn(args)


if __name__ == "__main__":
    main()
