#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Fetch an academic paper PDF into the reading workspace.

Standard library only — runs with plain `python3` (uv not required).

Accepts, as REF:
  * an arXiv id            1706.03762 · 2401.12345v2 · arXiv:1706.03762 · cs/0301012
  * an arXiv URL           https://arxiv.org/abs/1706.03762 · https://arxiv.org/pdf/1706.03762
  * a direct PDF URL       https://…/paper.pdf
  * a DOI                  10.18653/v1/… · https://doi.org/10.18653/v1/…
                           (resolved to an open-access PDF via the Unpaywall API;
                            requires --email, which Unpaywall asks of all callers)

Prints a single JSON object to stdout: {"ok": true, "path": …, "bytes": …,
"source_url": …, "kind": …} on success, {"ok": false, "error": …, "hint": …}
on failure. Exit code 0 on success, 1 on failure. Downloads are verified to be
real PDFs (magic bytes) — an HTML landing/paywall page is reported as failure.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (compatible; three-pass-skill/1.0; "
    "+https://github.com/jeyabbalas/skills)"
)

ARXIV_NEW = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")
ARXIV_OLD = re.compile(r"^([a-z-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?$")
DOI = re.compile(r"^10\.\d{4,9}/\S+$")


def fail(error, hint):
    print(json.dumps({"ok": False, "error": error, "hint": hint}, indent=2))
    sys.exit(1)


def http_get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


def classify(ref, email):
    """Return (kind, pdf_url) for the reference, resolving DOIs via Unpaywall."""
    r = ref.strip()
    r = re.sub(r"^arxiv:", "", r, flags=re.I).strip()

    m = re.match(r"^https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/(.+?)(?:\.pdf)?(?:[?#].*)?$", r)
    if m:
        r = m.group(1)
    if ARXIV_NEW.match(r) or ARXIV_OLD.match(r):
        return "arxiv", "https://arxiv.org/pdf/" + r

    m = re.match(r"^https?://(?:dx\.)?doi\.org/(.+)$", r)
    if m:
        r = m.group(1)
    if DOI.match(r):
        if not email:
            fail(
                "A DOI lookup needs --email (the Unpaywall API requires a contact address).",
                "Re-run with --email you@example.org, or find an open-access PDF URL "
                "(arXiv, publisher, PubMed Central, author page) and pass that instead.",
            )
        api = "https://api.unpaywall.org/v2/{}?email={}".format(r, email)
        try:
            with http_get(api, timeout=30) as resp:
                data = json.load(resp)
        except (urllib.error.URLError, ValueError) as exc:
            fail(
                "Unpaywall lookup failed for DOI {}: {}".format(r, exc),
                "Search the web for an open-access copy (arXiv, PubMed Central, author "
                "page); if none exists, ask the user to download the PDF and provide its path.",
            )
        loc = data.get("best_oa_location") or {}
        pdf = loc.get("url_for_pdf") or loc.get("url")
        if not pdf:
            fail(
                "No open-access copy known to Unpaywall for DOI " + r,
                "Ask the user to download the PDF through their institutional access "
                "and provide its path.",
            )
        return "doi", pdf

    if re.match(r"^https?://", r):
        return "url", r

    fail(
        "Could not interpret the reference: " + ref,
        "Pass an arXiv id, an arXiv/DOI/PDF URL, or a DOI. For a bare paper title, "
        "search the web first to find one of those identifiers.",
    )


def main():
    ap = argparse.ArgumentParser(description="Download a paper PDF into the workspace.")
    ap.add_argument("ref", help="arXiv id, arXiv/PDF URL, or DOI")
    ap.add_argument("--out", required=True, help="output path, e.g. papers/<slug>/paper.pdf")
    ap.add_argument("--email", default=None, help="contact email (required for DOI lookups)")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()

    out = Path(args.out)
    skill_dir = Path(__file__).resolve().parent.parent
    if skill_dir in out.resolve().parents:
        fail(
            "Refusing to write into the installed skill directory: " + str(out),
            "Pass an --out path inside the reading workspace, e.g. papers/<slug>/paper.pdf",
        )

    kind, url = classify(args.ref, args.email)
    try:
        with http_get(url, timeout=args.timeout) as resp:
            data = resp.read()
            final_url = resp.geturl()
    except urllib.error.HTTPError as exc:
        fail(
            "HTTP {} fetching {}".format(exc.code, url),
            "The paper may be paywalled or the link stale. Search for an open-access "
            "copy; if none exists, ask the user to download the PDF and provide its path.",
        )
    except urllib.error.URLError as exc:
        fail(
            "Network error fetching {}: {}".format(url, exc.reason),
            "Check connectivity and retry; or ask the user to download the PDF "
            "and provide its path.",
        )

    if b"%PDF" not in data[:1024]:
        fail(
            "The response from {} is not a PDF (got {} bytes starting {!r}).".format(
                final_url, len(data), data[:40]
            ),
            "This is usually a landing or paywall page. Find the direct PDF link, or "
            "ask the user to download the PDF and provide its path.",
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(
        json.dumps(
            {
                "ok": True,
                "path": str(out),
                "bytes": len(data),
                "source_url": final_url,
                "kind": kind,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
