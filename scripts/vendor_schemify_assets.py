#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Re-vendor the browser libraries that schemify's playground page loads.

The failure this guards against: loading the table engine cross-origin. The
library builds its worker URL as `new URL("assets/worker-<hash>.js",
import.meta.url)`, so served from a CDN the worker either 404s or is refused,
and the page dies with "Worker error: undefined". Vendored beside the page, the
same construction resolves same-origin and just works.

The chunk filenames carry content hashes that change on every upstream release,
so the file list is discovered from the jsDelivr package index rather than kept
by hand. Sourcemaps and type declarations are skipped -- the browser never
needs them, and they are four times the weight of the code.

Usage:  uv run scripts/vendor_schemify_assets.py            (re-vendor + verify)
        uv run scripts/vendor_schemify_assets.py --check     (verify only)

Prints JSON to stdout. Exits 0 when every file matches MANIFEST.sha256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "skills" / "schemify" / "assets" / "vendor"
MANIFEST = VENDOR / "MANIFEST.sha256"

DATA_TABLE = "@jeyabbalas/data-table@0.7.0"
JSDELIVR = "https://cdn.jsdelivr.net/npm/"
JSDELIVR_INDEX = "https://data.jsdelivr.com/v1/packages/npm/{}?structure=flat"

# Everything the browser loads, dropping sourcemaps and .d.ts. `dist/` is
# flattened onto `data-table/` so the package's own `assets/worker-*.js`
# subdirectory -- which import.meta.url resolution depends on -- is preserved.
SKIP_SUFFIXES = (".map", ".d.ts")
KEEP_ROOT_FILES = ("LICENSE",)

# Single-file ESM builds. esm.sh keeps `ajv` external in its ajv-formats plugin
# build, so we take the formats table itself and register it on the validator by
# hand; see assets/VENDORED.md for why that is the honest choice here.
ESM_BUNDLES = [
    ("ajv-2020.mjs", "https://esm.sh/ajv@8.17.1/es2022/dist/2020.bundle.mjs"),
    ("ajv-formats.mjs", "https://esm.sh/ajv-formats@3.0.1/es2022/dist/formats.bundle.mjs"),
]


def out(payload, code=0):
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(code)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "schemify-vendor"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        out({"ok": False, "error": f"Could not fetch {url}: {exc}",
             "hint": "Check the network, then re-run. Nothing was written."}, 1)


def data_table_files() -> list[str]:
    """Package-relative paths the browser needs, from jsDelivr's file index."""
    index = json.loads(fetch(JSDELIVR_INDEX.format(DATA_TABLE)))
    names = []
    for entry in index.get("files", []):
        name = entry["name"]                      # e.g. /dist/assets/worker-x.js
        if name.endswith(SKIP_SUFFIXES):
            continue
        if name.startswith("/dist/"):
            names.append(name)
        elif name.lstrip("/") in KEEP_ROOT_FILES:
            names.append(name)
    if not any(n.startswith("/dist/assets/worker-") for n in names):
        out({"ok": False,
             "error": f"{DATA_TABLE} has no dist/assets/worker-*.js chunk.",
             "hint": "The upstream layout changed; re-read the worker wiring in "
                     "templates/playground.html before bumping the version."}, 1)
    return sorted(names)


def local_path(remote: str) -> Path:
    """dist/foo.js -> data-table/foo.js; LICENSE -> data-table/LICENSE."""
    rel = remote.lstrip("/")
    if rel.startswith("dist/"):
        rel = rel[len("dist/"):]
    return VENDOR / "data-table" / rel


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_manifest(entries: dict[str, str]) -> None:
    lines = [f"{digest}  {path}" for path, digest in sorted(entries.items())]
    MANIFEST.write_text("\n".join(lines) + "\n")


def read_manifest() -> dict[str, str]:
    if not MANIFEST.is_file():
        return {}
    entries = {}
    for line in MANIFEST.read_text().splitlines():
        if line.strip():
            digest, path = line.split("  ", 1)
            entries[path] = digest
    return entries


def run_check():
    expected = read_manifest()
    if not expected:
        out({"ok": False, "error": "No MANIFEST.sha256 in assets/vendor/.",
             "hint": "Run `uv run scripts/vendor_schemify_assets.py` to vendor."}, 1)
    problems = []
    for rel, digest in expected.items():
        path = VENDOR / rel
        if not path.is_file():
            problems.append({"file": rel, "issue": "missing"})
        elif sha256(path.read_bytes()) != digest:
            problems.append({"file": rel, "issue": "modified since vendoring"})
    on_disk = {str(p.relative_to(VENDOR)) for p in VENDOR.rglob("*") if p.is_file()}
    for rel in sorted(on_disk - set(expected) - {MANIFEST.name}):
        problems.append({"file": rel, "issue": "not in the manifest"})
    out({"ok": not problems, "vendored": len(expected), "problems": problems,
         **({"hint": "Re-run without --check to restore the vendored files."}
            if problems else {})}, 1 if problems else 0)


def run_vendor():
    remotes = data_table_files()
    staged: dict[Path, bytes] = {}
    for remote in remotes:
        staged[local_path(remote)] = fetch(JSDELIVR + DATA_TABLE + remote)
    for name, url in ESM_BUNDLES:
        body = fetch(url)
        if b"from\"/" in body or b'from "/' in body:
            out({"ok": False,
                 "error": f"{url} is not self-contained (it imports other modules).",
                 "hint": "Vendoring it would need an import map. Pick a bundled "
                         "build, or keep the previous pinned version."}, 1)
        staged[VENDOR / name] = body

    if VENDOR.exists():
        shutil.rmtree(VENDOR)                 # hash-named chunks must not accumulate
    entries = {}
    for path, body in staged.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        entries[str(path.relative_to(VENDOR))] = sha256(body)
    write_manifest(entries)
    total = sum(len(b) for b in staged.values())
    out({"ok": True, "vendor_dir": str(VENDOR.relative_to(ROOT)),
         "files": len(entries), "bytes": total,
         "data_table": DATA_TABLE,
         "note": "Re-stamp packages with `render.py refresh-assets <pkg>` and "
                 "rebuild their pages."})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the vendored files against MANIFEST.sha256")
    args = parser.parse_args()
    run_check() if args.check else run_vendor()


if __name__ == "__main__":
    main()
