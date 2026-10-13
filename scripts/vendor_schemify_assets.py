#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Re-vendor or verify the browser libraries schemify uses: json-schema-data-dictionary (vendored)
and data-table (pinned in site/app.js, loaded from jsDelivr).

The data dictionary in every schemify workspace and package is drawn by the IIFE build
of json-schema-data-dictionary, copied byte-for-byte into
skills/schemify/assets/json-schema-data-dictionary.global.js. Its version and sha256 are
recorded in skills/schemify/assets/VENDORED.md; this script keeps the two in step.

Usage:  uv run scripts/vendor_schemify_assets.py --check            (verify the file and the data-table pin against VENDORED.md)
        uv run scripts/vendor_schemify_assets.py --version 0.8.0    (download that version, then update VENDORED.md)

Prints JSON to stdout. Exits 0 when the file matches (or was written), 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "skills" / "schemify" / "assets"
TARGET = ASSETS / "json-schema-data-dictionary.global.js"
VENDORED = ASSETS / "VENDORED.md"
URL = "https://cdn.jsdelivr.net/npm/json-schema-data-dictionary@{v}/dist/json-schema-data-dictionary.global.js"


def out(payload: dict, code: int = 0) -> None:
    print(json.dumps(payload, indent=2))
    sys.exit(code)


def recorded() -> tuple[str | None, str | None]:
    text = VENDORED.read_text(encoding="utf-8")
    ver = re.search(r"json-schema-data-dictionary`\]\([^)]*\) v(\d+\.\d+\.\d+)", text)
    sha = re.search(r"sha256: `([0-9a-f]{64})`", text)
    return (ver.group(1) if ver else None, sha.group(1) if sha else None)


APP = ASSETS / "site" / "app.js"


def datatable_pin_problems() -> list[str]:
    """site/app.js pins data-table (version + worker file); VENDORED.md records the same pin."""
    text = VENDORED.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8") if APP.exists() else ""
    want_v = re.search(r"@jeyabbalas/data-table`\]\([^)]*\) v(\d+\.\d+\.\d+)", text)
    want_w = re.search(r"dist/assets/(worker-[A-Za-z0-9_-]+\.js)", text)
    got_v = re.search(r'version: "(\d+\.\d+\.\d+)", worker: "assets/(worker-[A-Za-z0-9_-]+\.js)"', app)
    if not (want_v and want_w):
        return ["VENDORED.md has no data-table section with a version and a worker file name."]
    if not got_v:
        return ["site/app.js has no data-table pin (DT.version / DT.worker)."]
    problems = []
    if got_v.group(1) != want_v.group(1):
        problems.append(f"site/app.js pins data-table {got_v.group(1)}; VENDORED.md records {want_v.group(1)}.")
    if got_v.group(2) != want_w.group(1):
        problems.append(f"site/app.js starts {got_v.group(2)}; VENDORED.md records {want_w.group(1)}.")
    return problems


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="verify the vendored file against VENDORED.md")
    g.add_argument("--version", help="download this version of json-schema-data-dictionary")
    a = p.parse_args()
    ver, sha = recorded()
    if a.check:
        if not TARGET.exists():
            out({"ok": False, "error": f"{TARGET} is missing.", "hint": f"Run with --version {ver or '<x.y.z>'}."}, 1)
        actual = hashlib.sha256(TARGET.read_bytes()).hexdigest()
        if actual != sha:
            out({"ok": False, "error": "the vendored file does not match VENDORED.md", "recorded": sha, "actual": actual,
                 "hint": "Restore it with --version, or update VENDORED.md if the upgrade was deliberate."}, 1)
        pin = datatable_pin_problems()
        if pin:
            out({"ok": False, "error": " ".join(pin),
                 "hint": "Keep DT.version and DT.worker in site/app.js and the data-table section of VENDORED.md in step."}, 1)
        out({"ok": True, "version": ver, "sha256": actual, "dataTable": "pin matches VENDORED.md"})
    url = URL.format(v=a.version)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "schemify-vendor"})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
    except (urllib.error.URLError, OSError) as exc:
        out({"ok": False, "error": f"could not fetch {url}: {exc}", "hint": "Check the version and the network; nothing was written."}, 1)
    if b"JsonSchemaDataDictionary" not in body:
        out({"ok": False, "error": "the download does not define the JsonSchemaDataDictionary global", "hint": "Is this the IIFE build?"}, 1)
    TARGET.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    out({"ok": True, "version": a.version, "sha256": digest, "bytes": len(body),
         "next": "Update the version and sha256 in skills/schemify/assets/VENDORED.md, check the exports and markup it lists, "
                 "then refresh-assets and build the example workspace."})


if __name__ == "__main__":
    main()
