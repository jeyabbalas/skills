#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["beautifulsoup4>=4.12", "markdownify>=0.13"]
# ///
"""Ingest an EPUB book: chapter map, chapter text as markdown, images.

Run with `uv run scripts/ingest_epub.py …` (uv resolves the dependencies
automatically). No uv? `toc` and `images` are standard-library only — plain
`python3 scripts/…` always works for them; `text` additionally needs
`python3 -m pip install --user beautifulsoup4 markdownify`. Neither available
for `text`? Extract the chapter's raw XHTML with
`unzip -p book.epub OEBPS/ch07.xhtml` and read the HTML directly — no cached
extract/chNN.md, but nothing is blocked.

All subcommands print JSON to stdout and refuse to write into the skill
directory. DRM-protected EPUBs are refused honestly, never unlocked.

  toc EPUB
      Spine + table of contents → chapters as contiguous spine runs (a seed
      for CONTENTS.md — the student confirms it, and a hand-edited CONTENTS.md
      always wins). EPUBs have no printed pages: CONTENTS.md's pages column
      holds the spine run (e.g. "spine 3–5").

  text EPUB --chapter N --out books/<slug>/extract/chNN.md [--force]
      The chapter's XHTML converted to markdown and cached (an existing cache
      short-circuits; --force re-extracts). Math in EPUBs may be MathML or
      images — verbatim equations are safer read from the original XHTML or
      the extracted image.

  images EPUB --chapter N --out books/<slug>/figures/
      Extract the images the chapter references, bytes untouched, as
      chNN-img-KK.<ext>; rename the keepers per LAYOUT.md's figure naming.
"""

import argparse
import json
import posixpath
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent


def fail(error, hint):
    print(json.dumps({"ok": False, "error": error, "hint": hint}, indent=2))
    sys.exit(1)


def guard_out(path):
    if SKILL_DIR in Path(path).resolve().parents:
        fail("Refusing to write into the installed skill directory: " + str(path),
             "Pass an --out path inside the study workspace.")


def local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def find_all(root, name):
    return [el for el in root.iter() if local(el.tag) == name]


def resolve(base_dir, href):
    return posixpath.normpath(posixpath.join(base_dir, urllib.parse.unquote(href)))


class Epub:
    def __init__(self, path):
        p = Path(path)
        if not p.is_file():
            fail("File not found: " + str(path), "")
        if not zipfile.is_zipfile(p):
            fail(str(path) + " is not an EPUB (not a ZIP container).",
                 "Check the file; landing pages often save as HTML.")
        self.zf = zipfile.ZipFile(p)
        self.names = set(self.zf.namelist())
        self._drm_gate()
        self._read_opf()

    def read(self, name):
        return self.zf.read(name)

    def _drm_gate(self):
        enc = "META-INF/encryption.xml"
        if enc not in self.names:
            self.font_obfuscation_only = False
            return
        try:
            root = ET.fromstring(self.read(enc))
        except ET.ParseError:
            fail("This EPUB carries an unreadable encryption.xml.",
                 "Treat it as DRM-protected: I can't and won't unlock it. Obtain a "
                 "DRM-free copy from the publisher.")
        uris = []
        for ref in find_all(root, "CipherReference"):
            uri = urllib.parse.unquote(ref.get("URI", ""))
            if uri:
                uris.append(uri.lstrip("/"))
        fonts = {".otf", ".ttf", ".woff", ".woff2"}
        non_font = [u for u in uris if Path(u).suffix.lower() not in fonts]
        if non_font:
            fail(
                "This EPUB is DRM-protected (encrypted content: {}).".format(
                    ", ".join(non_font[:3]) + ("…" if len(non_font) > 3 else "")),
                "I can't and won't unlock it. Obtain a DRM-free copy — many publishers "
                "sell them directly — or a different format.",
            )
        self.font_obfuscation_only = bool(uris)

    def _read_opf(self):
        try:
            container = ET.fromstring(self.read("META-INF/container.xml"))
        except (KeyError, ET.ParseError):
            fail("No readable META-INF/container.xml — not a valid EPUB.", "")
        rootfiles = find_all(container, "rootfile")
        if not rootfiles:
            fail("container.xml names no rootfile.", "")
        self.opf_path = rootfiles[0].get("full-path")
        self.opf_dir = posixpath.dirname(self.opf_path)
        opf = ET.fromstring(self.read(self.opf_path))
        self.version = opf.get("version", "?")
        self.title = next((el.text or "" for el in find_all(opf, "title")), "").strip()
        self.creators = [el.text.strip() for el in find_all(opf, "creator") if el.text]
        self.manifest = {}
        for item in find_all(opf, "item"):
            self.manifest[item.get("id")] = {
                "href": resolve(self.opf_dir, item.get("href", "")),
                "media_type": item.get("media-type", ""),
                "properties": item.get("properties", "") or "",
            }
        self.href_to_id = {v["href"]: k for k, v in self.manifest.items()}
        spine_el = next(iter(find_all(opf, "spine")), None)
        self.spine = []
        self.ncx_id = spine_el.get("toc") if spine_el is not None else None
        for ref in (find_all(spine_el, "itemref") if spine_el is not None else []):
            if ref.get("linear", "yes") != "no":
                self.spine.append(ref.get("idref"))
        self.spine_hrefs = [self.manifest[i]["href"] for i in self.spine
                            if i in self.manifest]

    # ---- table of contents → (label, href, fragment) triples ----

    def toc_entries(self):
        nav_id = next((k for k, v in self.manifest.items() if "nav" in v["properties"]),
                      None)
        if nav_id:
            entries = self._toc_from_nav(self.manifest[nav_id]["href"])
            if entries:
                return entries, "epub3-nav"
        ncx_id = self.ncx_id or next(
            (k for k, v in self.manifest.items()
             if v["media_type"] == "application/x-dtbncx+xml"), None)
        if ncx_id and ncx_id in self.manifest:
            entries = self._toc_from_ncx(self.manifest[ncx_id]["href"])
            if entries:
                return entries, "ncx"
        return [], "none"

    def _toc_from_nav(self, href):
        try:
            root = ET.fromstring(self.read(href))
        except (KeyError, ET.ParseError):
            return []
        base = posixpath.dirname(href)
        toc_nav = None
        for nav in find_all(root, "nav"):
            types = [v for k, v in nav.attrib.items() if local(k) == "type"]
            if any("toc" in t for t in types):
                toc_nav = nav
                break
        if toc_nav is None:
            toc_nav = next(iter(find_all(root, "nav")), None)
        if toc_nav is None:
            return []
        ol = next(iter(find_all(toc_nav, "ol")), None)
        if ol is None:
            return []
        entries = []
        for li in (el for el in ol if local(el.tag) == "li"):
            a = next(iter(find_all(li, "a")), None)
            if a is None or not a.get("href"):
                continue
            target = urllib.parse.unquote(a.get("href"))
            frag = None
            if "#" in target:
                target, frag = target.split("#", 1)
            label = "".join(a.itertext()).strip()
            entries.append({"label": label, "href": resolve(base, target), "frag": frag})
        return entries

    def _toc_from_ncx(self, href):
        try:
            root = ET.fromstring(self.read(href))
        except (KeyError, ET.ParseError):
            return []
        base = posixpath.dirname(href)
        nav_map = next(iter(find_all(root, "navMap")), None)
        if nav_map is None:
            return []
        entries = []
        for point in (el for el in nav_map if local(el.tag) == "navPoint"):
            text = next((t.text or "" for t in find_all(point, "text")), "").strip()
            content = next(iter(find_all(point, "content")), None)
            if content is None:
                continue
            target = urllib.parse.unquote(content.get("src", ""))
            frag = None
            if "#" in target:
                target, frag = target.split("#", 1)
            entries.append({"label": text, "href": resolve(base, target), "frag": frag})
        return entries

    # ---- chapters = contiguous spine runs (fragment splits within one file) ----

    def chapters(self):
        entries, source = self.toc_entries()
        spine_index = {h: i for i, h in enumerate(self.spine_hrefs)}
        anchored = [e for e in entries if e["href"] in spine_index]
        if len(anchored) < 3:
            chapters = []
            for i, href in enumerate(self.spine_hrefs):
                chapters.append({"n": i + 1, "title": Path(href).name, "spine": [i, i],
                                 "files": [href], "fragment": None})
            return chapters, "spine-fallback", (
                "TOC too thin or unresolvable — chapter boundaries are per-file guesses; "
                "hand-edit CONTENTS.md.")
        chapters = []
        for k, e in enumerate(anchored):
            start = spine_index[e["href"]]
            nxt = anchored[k + 1] if k + 1 < len(anchored) else None
            if nxt and nxt["href"] == e["href"]:
                chapters.append({"n": k + 1, "title": e["label"],
                                 "spine": [start, start], "files": [e["href"]],
                                 "fragment": {"file": e["href"], "from": e["frag"],
                                              "to": nxt["frag"]}})
                continue
            end = (spine_index[nxt["href"]] - 1) if nxt else len(self.spine_hrefs) - 1
            end = max(start, end)
            files = self.spine_hrefs[start:end + 1]
            frag = ({"file": e["href"], "from": e["frag"], "to": None}
                    if e["frag"] else None)
            chapters.append({"n": k + 1, "title": e["label"], "spine": [start, end],
                             "files": files, "fragment": frag})
        return chapters, source, None


def pick_chapter(book, n):
    chapters, source, warn = book.chapters()
    match = next((c for c in chapters if c["n"] == n), None)
    if match is None:
        fail("No chapter {} in the map (1–{}).".format(n, len(chapters)),
             "Run `toc` to see the chapter map.")
    return match, source, warn


def slice_fragment(html, frag):
    """Approximate in-file split: the byte range from the element carrying
    id=frag['from'] to the element carrying id=frag['to'] (document order)."""
    def anchor_pos(fragment_id):
        if not fragment_id:
            return None
        m = re.search(r"""<[^>]*\bid\s*=\s*["']{}["']""".format(re.escape(fragment_id)),
                      html)
        return m.start() if m else None

    start = anchor_pos(frag.get("from")) or 0
    end = anchor_pos(frag.get("to"))
    return html[start:end] if end else html[start:]


def cmd_toc(args):
    book = Epub(args.epub)
    chapters, source, warn = book.chapters()
    out = {
        "ok": True, "file": args.epub, "title": book.title, "creators": book.creators,
        "epub_version": book.version, "toc_source": source, "drm": False,
        "font_obfuscation_only": book.font_obfuscation_only,
        "spine_items": len(book.spine_hrefs),
        "chapters": chapters,
        "note": ("A seed for CONTENTS.md; hand-edited CONTENTS.md always wins. EPUBs have "
                 "no printed pages — the pages column holds the spine run instead "
                 "(e.g. \"spine 3–5\")."),
    }
    if warn:
        out["warning"] = warn
    print(json.dumps(out, indent=2))


def cmd_text(args):
    guard_out(args.out)
    out = Path(args.out)
    if out.exists() and not args.force:
        print(json.dumps({"ok": True, "cached": True, "file": str(out),
                          "note": "existing cache kept; --force re-extracts"}, indent=2))
        return
    try:
        from bs4 import BeautifulSoup
        from markdownify import markdownify
    except ImportError:
        fail(
            "beautifulsoup4/markdownify are not installed (needed only by `text`).",
            "Preferred: run via `uv run scripts/ingest_epub.py …`. Without uv: "
            "`python3 -m pip install --user beautifulsoup4 markdownify`. Without either: "
            "`unzip -p book.epub <chapter file>` and read the raw XHTML directly.",
        )
    book = Epub(args.epub)
    chapter, _, _ = pick_chapter(book, args.chapter)
    parts = ["<!-- extract: {} chapter {} · ingest_epub.py -->".format(
        Path(args.epub).name, args.chapter)]
    chars = 0
    images = []
    for href in chapter["files"]:
        try:
            html = book.read(href).decode("utf-8", errors="replace")
        except KeyError:
            fail("Spine file missing from the archive: " + href, "The EPUB may be damaged.")
        if chapter["fragment"] and chapter["fragment"]["file"] == href:
            html = slice_fragment(html, chapter["fragment"])
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()
        for img in soup.find_all("img"):
            if img.get("src"):
                images.append(resolve(posixpath.dirname(href), img["src"]))
        text = markdownify(str(soup), heading_style="ATX").strip()
        chars += len(text)
        parts.append("<!-- file: {} -->\n{}".format(href, text))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(parts) + "\n")
    print(json.dumps({
        "ok": True, "cached": False, "file": str(out), "chapter": args.chapter,
        "files": chapter["files"], "chars": chars,
        "images_referenced": sorted(set(images)),
        "note": ("Image references point inside the EPUB — extract them with `images`. "
                 "Math may be MathML or images; read equations from the original XHTML "
                 "or the extracted image when they must be verbatim."),
    }, indent=2))


def cmd_images(args):
    guard_out(args.out)
    book = Epub(args.epub)
    chapter, _, _ = pick_chapter(book, args.chapter)
    referenced = set()
    for href in chapter["files"]:
        try:
            html = book.read(href).decode("utf-8", errors="replace")
        except KeyError:
            continue
        for m in re.finditer(r"""(?:src|href|xlink:href)\s*=\s*["']([^"']+)["']""", html):
            target = resolve(posixpath.dirname(href), m.group(1))
            referenced.add(target)
    image_hrefs = [v["href"] for v in book.manifest.values()
                   if v["media_type"].startswith("image/") and v["href"] in referenced]
    outdir = Path(args.out)
    written = []
    for k, href in enumerate(sorted(image_hrefs), 1):
        ext = Path(href).suffix or ".img"
        name = "ch{:02d}-img-{:02d}{}".format(args.chapter, k, ext)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / name).write_bytes(book.read(href))
        media = next(v["media_type"] for v in book.manifest.values() if v["href"] == href)
        written.append({"file": str(outdir / name), "source": href, "media_type": media})
    print(json.dumps({
        "ok": True, "written": written, "count": len(written),
        "note": "Rename the keepers to chNN-fig-MM.png per LAYOUT.md's figure naming.",
    }, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("toc", help="spine + TOC → chapter map")
    p.add_argument("epub")
    p.set_defaults(fn=cmd_toc)

    p = sub.add_parser("text", help="chapter XHTML → markdown cache")
    p.add_argument("epub")
    p.add_argument("--chapter", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--force", action="store_true", help="re-extract over an existing cache")
    p.set_defaults(fn=cmd_text)

    p = sub.add_parser("images", help="extract the chapter's images")
    p.add_argument("epub")
    p.add_argument("--chapter", type=int, required=True)
    p.add_argument("--out", required=True, help="output directory, e.g. books/<slug>/figures/")
    p.set_defaults(fn=cmd_images)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
