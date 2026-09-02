#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Build and maintain a schema package's executable surface: assets, tools, pages.

Standard library only - runs with plain `python3` (uv not required). All
subcommands print JSON to stdout and exit non-zero on failure.

Subcommands:

  init PKG
      Create assets/ (vendored rendering library, its embedding worker, the
      stylesheet) and tools/ (validator copy + requirements.txt); stamp
      assets/VERSION. Idempotent.
  refresh-assets PKG
      Overwrite the shipped copies from the skill and re-stamp VERSION -
      upgrades the package's whole executable surface at once.
  dictionary PKG [--title T]
      Build dictionary.html from every schema file. Opens straight from disk.
  playground PKG [--table T]
      Build playground page(s) with schemas and toy fixtures inlined. Without
      --table, builds every table that has a mother file.
  check PKG
      Lint the built surface: asset freshness, page staleness fingerprints,
      parseable inline data, no absolute-path or skill-directory references.
"""

import argparse
import datetime
import hashlib
import json
import re
import shutil
import sys
import urllib.parse
from pathlib import Path, PurePosixPath

SKILL_DIR = Path(__file__).resolve().parent.parent
SYNTHETIC_BASE = "https://schema.local/"
EXCLUDED_DIRS = {"examples", "tools", "assets", ".git", "node_modules", "__pycache__"}
SCHEMA_HINT_KEYS = {"$schema", "$id", "$defs", "properties", "type", "allOf", "oneOf", "anyOf", "items"}

SHIPPED = [
    ("assets/json-schema-data-dictionary.global.js", "assets/json-schema-data-dictionary.global.js"),
    ("assets/embed-worker.js", "assets/embed-worker.js"),
    ("assets/schema-pages.css", "assets/schema-pages.css"),
    ("scripts/validate.py", "tools/validate.py"),
]
# The brand mark is inlined into every page at render time (never copied), so a
# page's fingerprint covers it alongside the template.
BRAND_MARK = "assets/schemify-mark.svg"
REQUIREMENTS = "jsonschema>=4.18\nreferencing>=0.35\n"


def out(payload, code=0):
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(error, hint):
    out({"ok": False, "error": error, "hint": hint}, 1)


def guard(pkg):
    pkg = pkg.resolve()
    if pkg == SKILL_DIR or SKILL_DIR in pkg.parents:
        fail("Refusing to write inside the installed skill directory.",
             "Run against the schema package in the steward's repository.")
    if not pkg.is_dir():
        fail("Package directory not found: {}".format(pkg),
             "Pass the package root (often json_schema/). Create the directory first "
             "if this is intake scaffolding.")
    return pkg


def skill_file(rel):
    path = SKILL_DIR / rel
    if not path.is_file():
        fail("The skill is missing its own file: {}".format(rel),
             "The skill install is incomplete - reinstall it, then retry.")
    return path


def shipped_hash():
    h = hashlib.sha256()
    for src, _ in SHIPPED:
        h.update(skill_file(src).read_bytes())
    return h.hexdigest()[:12]


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def inline_json(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


# ---------------------------------------------------------------- package scan


def load_schemas(pkg):
    docs = {}
    for path in sorted(pkg.rglob("*.json")):
        rel = path.relative_to(pkg)
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts):
            continue
        if rel.name == "manifest.json":
            continue
        try:
            with open(path, encoding="utf-8-sig") as f:
                doc = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            fail("Could not parse {}: {}".format(rel, exc),
                 "Fix the JSON (run `validate.py check` for the full picture), "
                 "then rebuild the page.")
        if isinstance(doc, dict) and SCHEMA_HINT_KEYS & set(doc):
            docs[str(PurePosixPath(rel))] = doc
    if not docs:
        fail("No schema files found under {}.".format(pkg),
             "Pages render schemas; write the mother and category files first "
             "(LAYOUT.md, SCHEMA-PATTERNS.md).")
    return docs


def mothers_of(docs):
    return {PurePosixPath(rel).name[: -len(".schema.json")]: rel
            for rel in docs if rel.endswith(".schema.json")}


def schema_documents(docs):
    return [{"uri": SYNTHETIC_BASE + rel, "name": rel, "schema": doc}
            for rel, doc in sorted(docs.items())]


def fingerprint(template_bytes, version, input_bytes):
    h = hashlib.sha256()
    h.update(template_bytes)
    h.update(version.encode())
    for chunk in input_bytes:
        h.update(chunk)
    return h.hexdigest()[:12]


def package_version(pkg):
    vp = pkg / "assets" / "VERSION"
    return vp.read_text().strip() if vp.is_file() else None


def require_assets(pkg):
    if package_version(pkg) is None:
        fail("The package has no assets/VERSION - assets were never installed.",
             "Run `render.py init {}` first; pages link assets/ relatively.".format(pkg))


# ------------------------------------------------------------- init / refresh


def copy_shipped(pkg):
    copied = []
    for src, dst in SHIPPED:
        target = pkg / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(skill_file(src), target)
        copied.append(dst)
    req = pkg / "tools" / "requirements.txt"
    req.write_text(REQUIREMENTS)
    version = shipped_hash()
    (pkg / "assets" / "VERSION").write_text(version + "\n")
    return copied + ["tools/requirements.txt", "assets/VERSION"], version


def run_init(pkg, args):
    existing = package_version(pkg)
    current = shipped_hash()
    if existing == current:
        out({"ok": True, "package": str(pkg), "assets_version": current,
             "status": "current", "note": "Assets already installed and current."})
    copied, version = copy_shipped(pkg)
    out({"ok": True, "package": str(pkg), "assets_version": version,
         "status": "refreshed" if existing else "installed",
         "written": copied,
         **({"note": "Assets were outdated ({}) and have been refreshed - re-run "
                     "`render.py dictionary` and `render.py playground` so pages "
                     "match.".format(existing)} if existing else {})})


def run_refresh(pkg, args):
    copied, version = copy_shipped(pkg)
    out({"ok": True, "package": str(pkg), "assets_version": version,
         "refreshed": copied,
         "note": "Re-run `render.py dictionary` and `render.py playground` if "
                 "`render.py check` reports stale pages."})


# ----------------------------------------------------------------- page chrome


def template_bytes(name):
    """A page's template plus the brand mark inlined into it - what its fingerprint covers."""
    return skill_file("templates/" + name).read_bytes() + skill_file(BRAND_MARK).read_bytes()


def brand():
    """The inline brand mark and the favicon derived from it - one source file."""
    svg = skill_file(BRAND_MARK).read_text().strip()
    return svg, "data:image/svg+xml," + urllib.parse.quote(svg)


def playground_name(table, multi):
    return "playground-{}.html".format(table) if multi else "playground.html"


def page_nav(tables, multi, current):
    """The masthead's page switcher: the dictionary, then one playground per table.
    `current` is "dictionary" or a table name."""
    items = [("dictionary", "Dictionary", "dictionary.html")]
    for table in tables:
        label = "Playground · " + table if multi else "Playground"
        items.append((table, label, playground_name(table, multi)))
    return "".join(
        '<a class="tab" href="{}"{}>{}</a>'.format(
            href, ' aria-current="page"' if key == current else "", esc(label))
        for key, label, href in items)


# ------------------------------------------------------------------ dictionary


def manifest_study(pkg):
    path = pkg / "manifest.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8-sig") as f:
            card = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    study = card.get("study") if isinstance(card, dict) else None
    return study.strip() if isinstance(study, str) and study.strip() else None


def run_dictionary(pkg, args):
    require_assets(pkg)
    docs = load_schemas(pkg)
    mothers = mothers_of(docs)
    if not mothers:
        fail("No mother file (*.schema.json) found.",
             "Each table needs <table>/<table>.schema.json before a page can mount it.")
    version = package_version(pkg)
    multi = len(mothers) > 1
    mounts, sections = [], []
    for table in sorted(mothers):
        mother = docs[mothers[table]]
        title = mother.get("title", table)
        if multi:
            # Several tables: each section carries its heading and its own playground link.
            sections.append(
                '  <section class="dict-section" data-table="{t}">\n'
                '    <div class="section-head"><h2>{title}</h2>'
                '<a class="chrome" href="{pg}">Validation playground</a></div>\n'
                '    <div class="dict-mount" id="dict-{t}"></div>\n'
                '  </section>'.format(t=esc(table), title=esc(title),
                                      pg=playground_name(table, True)))
        else:
            # One table: the page title and the masthead's Playground tab already cover it.
            sections.append(
                '  <section class="dict-section" data-table="{t}">\n'
                '    <div class="dict-mount" id="dict-{t}"></div>\n'
                '  </section>'.format(t=esc(table)))
        mounts.append({"table": table, "title": title,
                       "rootUri": SYNTHETIC_BASE + mothers[table]})
    single_mother = docs[next(iter(mothers.values()))]
    # One table: the mother's title. Several: the study named by manifest.json
    # (its optional package card), else the package directory's name.
    page_title = args.title or (single_mother.get("title") if not multi else None) \
        or manifest_study(pkg) or pkg.name
    # Single table: the library's own header prints the full description right
    # below, so the page subtitle would only repeat its first sentence.
    subtitle = "" if not multi else \
        "{} tables - {}".format(len(mothers), ", ".join(sorted(mothers)))

    template = skill_file("templates/dictionary.html").read_text()
    mark, favicon = brand()
    documents = schema_documents(docs)
    config = {"package": pkg.name, "generated": datetime.date.today().isoformat(),
              "mounts": mounts}
    fp = fingerprint(template_bytes("dictionary.html"), version,
                     [json.dumps(docs[rel], sort_keys=True).encode()
                      for rel in sorted(docs)])
    html = template
    for token, value in [
        ("{{TITLE}}", esc(page_title)),
        ("{{SUBTITLE}}", esc(subtitle)),
        ("{{PACKAGE_NAME}}", esc(pkg.name)),
        ("{{GENERATED_DATE}}", config["generated"]),
        ("{{ASSETS_VERSION}}", version),
        ("{{PAGE_FINGERPRINT}}", fp),
        ("{{BRAND_MARK}}", mark),
        ("{{FAVICON}}", favicon),
        ("{{PAGE_NAV}}", page_nav(sorted(mothers), multi, "dictionary")),
        ("{{MOUNT_SECTIONS}}", "\n".join(sections)),
        ("{{SCHEMA_DOCUMENTS_JSON}}", inline_json(documents)),
        ("{{PAGE_CONFIG_JSON}}", inline_json(config)),
    ]:
        html = html.replace(token, value)
    (pkg / "dictionary.html").write_text(html)
    out({"ok": True, "page": "dictionary.html", "tables": sorted(mothers),
         "documents": len(documents), "fingerprint": fp,
         "note": "Double-click to open - works over file://. Keyword search is built in; "
                 "the page's Semantic search switch is opt-in and needs the network once."})


# ------------------------------------------------------------------ playground


def fixture_dir(pkg, table, multi):
    return pkg / "examples" / (table if multi else "")


def run_playground(pkg, args):
    require_assets(pkg)
    docs = load_schemas(pkg)
    mothers = mothers_of(docs)
    if not mothers:
        fail("No mother file (*.schema.json) found.",
             "Each table needs <table>/<table>.schema.json before a page can mount it.")
    multi = len(mothers) > 1
    tables = [args.table] if args.table else sorted(mothers)
    version = package_version(pkg)
    template = skill_file("templates/playground.html").read_text()
    mark, favicon = brand()
    documents = schema_documents(docs)
    pages = []
    for table in tables:
        if table not in mothers:
            fail("No table named {!r} (found: {}).".format(table, ", ".join(sorted(mothers))),
                 "Table names are the *.schema.json stems.")
        mother_rel = mothers[table]
        mother = docs[mother_rel]
        datasets, dataset_bytes = {}, []
        fdir = fixture_dir(pkg, table, multi)
        for key in ("toy_valid", "toy_invalid"):
            fpath = fdir / (key + ".json")
            if fpath.is_file():
                try:
                    with open(fpath, encoding="utf-8-sig") as f:
                        datasets[key] = json.load(f)
                    dataset_bytes.append(fpath.read_bytes())
                except json.JSONDecodeError as exc:
                    fail("Could not parse {}: {}".format(fpath.relative_to(pkg), exc),
                         "Fix the fixture (`validate.py fixtures` helps), then rebuild.")
        config = {"package": pkg.name, "table": table,
                  "rootUri": SYNTHETIC_BASE + mother_rel,
                  "rootId": mother.get("$id"),
                  "generated": datetime.date.today().isoformat()}
        fp = fingerprint(template_bytes("playground.html"), version,
                         [json.dumps(docs[rel], sort_keys=True).encode()
                          for rel in sorted(docs)] + dataset_bytes)
        html = template
        for token, value in [
            ("{{TITLE}}", esc(mother.get("title", table))),
            ("{{PACKAGE_NAME}}", esc(pkg.name)),
            ("{{TABLE_LABEL}}", esc(table)),
            ("{{GENERATED_DATE}}", config["generated"]),
            ("{{ASSETS_VERSION}}", version),
            ("{{PAGE_FINGERPRINT}}", fp),
            ("{{BRAND_MARK}}", mark),
            ("{{FAVICON}}", favicon),
            ("{{PAGE_NAV}}", page_nav(sorted(mothers), multi, table)),
            ("{{SCHEMA_DOCUMENTS_JSON}}", inline_json(documents)),
            ("{{DATASETS_JSON}}", inline_json(datasets)),
            ("{{PAGE_CONFIG_JSON}}", inline_json(config)),
        ]:
            html = html.replace(token, value)
        name = playground_name(table, multi)
        (pkg / name).write_text(html)
        pages.append({"page": name, "table": table, "fingerprint": fp,
                      "fixtures": sorted(datasets)})
    out({"ok": True, "pages": pages,
         "note": "Serve with `python3 -m http.server 8000` from the package root - "
                 "the page itself explains this if opened over file://."})


# ----------------------------------------------------------------------- check


FINGERPRINT_RE = re.compile(r'data-fingerprint="([0-9a-f]{12})"')
INLINE_JSON_RE = re.compile(
    r'<script type="application/json" class="([\w-]+)">(.*?)</script>', re.S)
BAD_REF_RE = re.compile(r'(?:href|src)="(/[^"]*|[a-zA-Z]:\\[^"]*|file://[^"]*)"')


def run_check(pkg, args):
    problems = []
    current = shipped_hash()
    installed = package_version(pkg)
    if installed is None:
        problems.append({"file": "assets/VERSION", "issue": "assets never installed",
                         "hint": "Run `render.py init {}`.".format(pkg)})
    elif installed != current:
        problems.append({"file": "assets/VERSION",
                         "issue": "assets are outdated (package {}, skill {})".format(
                             installed, current),
                         "hint": "Run `render.py refresh-assets {}` then rebuild "
                                 "the pages.".format(pkg)})

    docs = {}
    try:
        docs = load_schemas(pkg)
    except SystemExit:
        raise
    mothers = mothers_of(docs)
    multi = len(mothers) > 1
    schema_bytes = [json.dumps(docs[rel], sort_keys=True).encode()
                    for rel in sorted(docs)]

    for page in sorted(pkg.glob("*.html")):
        html = page.read_text(errors="replace")
        m = FINGERPRINT_RE.search(html)
        if not m:
            problems.append({"file": page.name, "issue": "no data-fingerprint",
                             "hint": "Rebuild the page with render.py - hand-made "
                                     "pages can't be checked for staleness."})
            continue
        if page.name == "dictionary.html":
            expected = fingerprint(template_bytes("dictionary.html"), installed or "",
                                   schema_bytes)
        elif page.name.startswith("playground"):
            table = page.name[len("playground-"):-len(".html")] \
                if page.name.startswith("playground-") else \
                (next(iter(mothers)) if mothers else "")
            dataset_bytes = []
            for key in ("toy_valid", "toy_invalid"):
                fpath = fixture_dir(pkg, table, multi) / (key + ".json")
                if fpath.is_file():
                    dataset_bytes.append(fpath.read_bytes())
            expected = fingerprint(template_bytes("playground.html"), installed or "",
                                   schema_bytes + dataset_bytes)
        else:
            continue
        if m.group(1) != expected:
            problems.append({"file": page.name,
                             "issue": "stale (inputs changed since render)",
                             "hint": "Re-run `render.py {} {}`.".format(
                                 "dictionary" if page.name == "dictionary.html"
                                 else "playground", pkg)})
        for cls, blob in INLINE_JSON_RE.findall(html):
            try:
                json.loads(blob)
            except json.JSONDecodeError:
                problems.append({"file": page.name,
                                 "issue": "inline {} data does not parse".format(cls),
                                 "hint": "Rebuild the page with render.py; never "
                                         "hand-edit inline data."})
        for match in BAD_REF_RE.findall(html):
            problems.append({"file": page.name,
                             "issue": "absolute or local-path reference: {}".format(
                                 match[:80]),
                             "hint": "Pages may reference only package-relative "
                                     "paths and https URLs."})
        if str(SKILL_DIR) in html:
            problems.append({"file": page.name,
                             "issue": "references the installed skill directory",
                             "hint": "Rebuild with render.py; the package must "
                                     "stand alone."})
    out({"ok": not problems, "package": str(pkg), "problems": problems,
         **({"hint": "Fix the problems above, most via a rebuild."} if problems else {})})


# ------------------------------------------------------------------------ main


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("init", "refresh-assets", "dictionary", "playground", "check"):
        p = sub.add_parser(name)
        p.add_argument("package")
        if name == "dictionary":
            p.add_argument("--title")
        if name == "playground":
            p.add_argument("--table")
    args = parser.parse_args()
    pkg = guard(Path(args.package))
    {"init": run_init, "refresh-assets": run_refresh, "dictionary": run_dictionary,
     "playground": run_playground, "check": run_check}[args.cmd](pkg, args)


if __name__ == "__main__":
    main()
