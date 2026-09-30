#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27"]
# ///
"""Recheck the links in skill docs against the live web: every URL, and every #anchor.

A skill that routes agents to outside documentation rots quietly: pages move,
anchors get renamed, and the agent lands on a 404, a "this page has moved"
stub, or the top of a long page instead of the section it was sent to.
biowulf alone links some 300 hpc.nih.gov pages and anchors. Third-party sites
flake, so this stays out of CI -- run it periodically and after editing links.

Usage:  uv run scripts/check_links.py [SKILL ...] [--json]
        (fallback: pip install httpx && python3 scripts/check_links.py [SKILL ...])

SKILL is a name under skills/ or a path to a directory or markdown file; the
default is every skill. Every *.md file under it is scanned.

Problems reported:
  http    the page answers with HTTP 400 or above (after retries on 429/5xx)
  error   the page never answers (DNS, TLS, timeout)
  moved   the page says so ("this page has been moved") or meta-refreshes away
  anchor  a URL's #fragment, or a bare anchor written in prose beside a link
          (the "#pitfalls" in "jupyter.html: pitfalls (#pitfalls)"), matches
          no id= or name= attribute -- case-sensitively, as browsers match --
          on the page, or for a bare anchor on any page linked on its line
Not fetched: templated URLs (..., $VAR, {x}, [x], <x>, *), hosts that do not
resolve publicly (localhost, 127.0.0.1, compute nodes such as cn0619, the
reserved example.* domains), and the pages in UNCHECKABLE.

Prints one line per problem, with every file:line that uses it (--json: one
JSON object on stdout instead), and exits 1 if there are any, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit

import httpx

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

URL_RE = re.compile(r"""https?://[^\s<>()"'`\]|]+""")
# `#notes`, (#pitfalls), #int/#sbatch -- prose, not a URL's fragment or a ](#toc) link.
BARE_RE = re.compile(r"""(?<=[`(\s/])#([A-Za-z][\w.:-]*)(?=[`),;\s/]|$)""")
TEMPLATED = re.compile(r"…|\.\.\.|[${}\[\]*]")
RESERVED_HOST = re.compile(r"(^|\.)example\.(com|org|net)$|\.(example|test|invalid|localhost)$")

# Pages a script cannot judge: behind an NIH login or the NIH network,
# JavaScript apps, sites that refuse scripted clients (npmjs.com answers 403),
# and datashare examples (hpc.nih.gov/~user/...). Matched as substrings. A
# page listed here is never checked again, so prefer fixing the link.
UNCHECKABLE = (
    "www.npmjs.com/package/",
    "hpc.nih.gov/dashboard",
    "hpc.nih.gov/nih/accounts/",
    "hpc.nih.gov/nih/test.html",
    "hpc.nih.gov/~",
    "hpcnihapps.cit.nih.gov",
    "hpcondemand.nih.gov",
    "myitsm.nih.gov",
    "itservicedesk.nih.gov",
    "password.nih.gov",
    "boxaccount.nih.gov",
    "nih.sharepoint.com",
    "app.globus.org",
    "cloud.sylabs.io/auth",
)

WORKERS = 8
RETRIES = 2
TIMEOUT = 30


def markdown_files(targets: list[str]) -> list[Path]:
    if not targets:
        return sorted(SKILLS.glob("*/**/*.md"))
    files: list[Path] = []
    for t in targets:
        p = Path(t)
        if not p.exists() and (SKILLS / t).is_dir():
            p = SKILLS / t
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        else:
            sys.exit(f"{t}: not a skill name under skills/, a directory, or a file")
    return files


def display(path: Path) -> str:
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def checkable(url: str, raw: str, next_char: str) -> bool:
    if "..." in raw or TEMPLATED.search(url) or next_char == "<":
        return False
    host = (urlsplit(url).hostname or "").lower()
    if "." not in host or host.startswith("127.") or host == "0.0.0.0" or RESERVED_HOST.search(host):
        return False
    return not any(s in url for s in UNCHECKABLE)


def collect(files: list[Path]):
    """Return {url: places}, {(bare anchor, pages on its line): places}, and the skipped-URL count."""
    urls: dict[str, list[str]] = {}
    bare: dict[tuple[str, tuple[str, ...]], list[str]] = {}
    skipped: set[str] = set()
    for f in files:
        in_code = False
        for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_code = not in_code
            where = f"{display(f)}:{n}"
            spans, pages = [], []
            for m in URL_RE.finditer(line):
                spans.append(m.span())
                raw = m.group(0)
                url = raw.rstrip(".,;:!?")
                if url.endswith("}") and "{" not in url:  # BibTeX: url = {https://...}
                    url = url[:-1]
                if checkable(url, raw, line[m.end() : m.end() + 1]):
                    urls.setdefault(url, []).append(where)
                    pages.append(urldefrag(url).url)
                else:
                    skipped.add(url)
            if in_code or not pages:
                continue
            for m in BARE_RE.finditer(line):
                if line[m.start() - 2 : m.start()] != "](" and not any(a <= m.start() < b for a, b in spans):
                    bare.setdefault((m.group(1), tuple(dict.fromkeys(pages))), []).append(where)
    return urls, bare, len(skipped)


def fetch(client: httpx.Client, url: str) -> tuple[int, str, str]:
    """Return (status, html, error) for one page; status 0 means it never answered."""
    error = ""
    for attempt in range(RETRIES + 1):
        if attempt:
            time.sleep(3 * attempt)
        try:
            with client.stream("GET", url) as r:
                if r.status_code == 429 or r.status_code >= 500:
                    error = f"HTTP {r.status_code}"
                    continue
                # Read the body only when it can hold anchors, never a download.
                if "html" not in r.headers.get("content-type", ""):
                    return r.status_code, "", ""
                r.read()
                return r.status_code, r.text, ""
        except Exception as e:  # a page that cannot be fetched is a finding, not a crash
            error = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
    return (int(error.split()[1]) if error.startswith("HTTP ") else 0), "", error


def moved(html: str) -> str:
    """Why an HTTP-200 page is really a pointer elsewhere, or ""."""
    for tag in re.findall(r"(?is)<meta\b[^>]*>", html):
        if re.search(r"(?i)http-equiv\s*=\s*[\"']?refresh", tag) and (m := re.search(r"(?i)url\s*=\s*[\"']?([^\"'>\s]+)", tag)):
            return f"meta refresh to {m.group(1)}"
    if re.search(r"(?i)\bthis page (?:has )?(?:been )?moved\b", html):
        return 'the page says "this page has moved"'
    return ""


def has_anchor(html: str, anchor: str) -> bool:
    for a in {anchor, unquote(anchor)}:
        # GitHub renders README headings as id="user-content-<slug>".
        attr = r"""(?<![\w-])(?i:id|name)\s*=\s*["']?(?:user-content-)?""" + re.escape(a) + r"""(?:["'\s/>]|$)"""
        if re.search(attr, html):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("skills", nargs="*", metavar="SKILL", help="skill name, directory, or markdown file (default: every skill)")
    ap.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    args = ap.parse_args()

    urls, bare, skipped = collect(markdown_files(args.skills))
    by_page: dict[str, list[str]] = {}
    for url, where in urls.items():
        by_page.setdefault(urldefrag(url).url, []).extend(where)
    pages = sorted(by_page)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; skills-link-check; +https://github.com/jeyabbalas/skills)"}
    with httpx.Client(follow_redirects=True, timeout=TIMEOUT, headers=headers) as client:
        with ThreadPoolExecutor(WORKERS) as pool:
            fetched = dict(zip(pages, pool.map(lambda p: fetch(client, p), pages)))

    problems: list[dict] = []

    def report(kind: str, url: str, detail: str, where: list[str]) -> None:
        problems.append({"kind": kind, "url": url, "detail": detail, "where": list(dict.fromkeys(where))})

    bad: set[str] = set()
    for page in pages:
        status, html, error = fetched[page]
        if error or status >= 400:
            report("http" if status else "error", page, error or f"HTTP {status}", by_page[page])
        elif why := moved(html):
            report("moved", page, why, by_page[page])
        else:
            continue
        bad.add(page)
    for url, where in sorted(urls.items()):
        page, fragment = urldefrag(url)
        if fragment and page not in bad and fetched[page][1] and not has_anchor(fetched[page][1], fragment):
            report("anchor", url, f'no id or name "{fragment}" on the page', where)
    for (anchor, on), where in sorted(bare.items()):
        htmls = [fetched[p][1] for p in on if p not in bad and fetched[p][1]]
        if htmls and not any(has_anchor(h, anchor) for h in htmls):
            report("anchor", f"#{anchor}", f'no id or name "{anchor}" on {" or ".join(on)}', where)

    if args.json:
        print(json.dumps({"urls": len(urls), "bare_anchors": len(bare), "pages": len(pages), "skipped": skipped, "problems": problems}, indent=2))
    else:
        for p in problems:
            print(f"{p['kind']}: {p['url']} -- {p['detail']}\n    in {', '.join(p['where'])}")
        print(f"checked {len(urls)} URLs and {len(bare)} bare anchors on {len(pages)} pages ({skipped} URLs skipped); {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
