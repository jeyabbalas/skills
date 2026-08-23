#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pypdf>=4.0", "pdfplumber>=0.11", "pypdfium2>=4.30", "pillow>=10"]
# ///
"""Ingest a book PDF: chapter map, cached chapter text, figure crops.

Run with `uv run scripts/ingest_pdf.py …` (uv resolves the dependencies
automatically). No uv? `python3 -m pip install --user pypdf pdfplumber
pypdfium2 pillow`, then plain `python3 scripts/…`. Neither available? Skip
ingestion: read the PDF natively page-ranged, hand-write CONTENTS.md's chapter
table from the printed table of contents (hand-editing CONTENTS.md is
first-class, not a failure), and have the student save manual screenshots to
the figures/ paths the pages expect.

All subcommands print JSON to stdout, refuse to write into the skill
directory, and treat an existing cache file as authoritative (--force
re-makes it). Coordinates are PDF points, origin at the page's top-left.
Text extraction mangles displayed math — when an equation must be verbatim,
crop the region with `figures` and read the image instead.

  toc PDF [--offset K]
      Outline → chapters with PDF-page ranges (a seed for CONTENTS.md — the
      student confirms it, and a hand-edited CONTENTS.md always wins). With no
      outline: printed-TOC parse; the output then explains the --offset
      calibration (printed page N is not PDF page N). Also reports whether the
      PDF has a text layer at all.

  text PDF --pages A-B --out books/<slug>/extract/chNN.md [--layout] [--force]
      Cache a page range's text (pdfplumber; ~1–2 s per dense page).

  figures PDF --page N [--bbox x0,y0,x1,y1] --out FILE.png [--scale 2]
      Without --bbox: caption candidates on the page with guessed content
      bboxes (matched-content is trustworthy; band-fallback is a generous
      over-crop — verify, then tighten). With --bbox: render the region to
      FILE.png at scale× (default 2×).

  split PDF --chapters 7=201-236,8=237-268 --out books/<slug>/extract/
      Per-chapter PDFs — an escape hatch for viewers that cannot page-range a
      huge file. Prefer page-ranged native reading.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
PIP_HINT = (
    "Preferred: run via `uv run scripts/ingest_pdf.py …`. Without uv: "
    "`python3 -m pip install --user pypdf pdfplumber pypdfium2 pillow` then re-run "
    "with python3. Without either: read the book natively page-ranged and hand-write "
    "CONTENTS.md's chapter table (fallback ladder in LAYOUT.md)."
)

CAPTION = re.compile(r"^\s*(Figure|Fig\.|Table)\s{0,2}(\d+[\.\d]*|[A-Z]\.?\d*)\s*[.:]")
TOC_LINE = re.compile(
    r"^\s*(?:chapter\s+)?(\d{1,3})[.:\s]\s*(.{3,80}?)[\s.·]{2,}(\d{1,4})\s*$", re.I
)
MIN_AREA = 25.0     # ignore vector fragments smaller than this (pt²)
BAND = 420.0        # how far (pt) from a caption content may reach
MIN_OVERLAP = 0.25  # required horizontal overlap between caption and content


def fail(error, hint):
    print(json.dumps({"ok": False, "error": error, "hint": hint}, indent=2))
    sys.exit(1)


def need(module):
    try:
        return __import__(module)
    except ImportError:
        fail(module + " is not installed.", PIP_HINT)


def guard_out(path):
    if SKILL_DIR in Path(path).resolve().parents:
        fail("Refusing to write into the installed skill directory: " + str(path),
             "Pass an --out path inside the study workspace.")


def open_checked(path):
    p = Path(path)
    if not p.is_file():
        fail("File not found: " + str(path), "")
    head = p.read_bytes()[:1024]
    if head[:4] == b"AT&T":
        fail(
            "This is a DjVu file, not a PDF.",
            "Convert it first: install DjVuLibre (brew install djvulibre / apt install "
            "djvulibre-bin), then `ddjvu -format=pdf book.djvu book.pdf`. Re-run on the PDF.",
        )
    if b"%PDF" not in head:
        fail(str(path) + " does not look like a PDF.",
             "Check the file; landing pages often save as HTML.")
    return p


def pypdf_reader(path):
    pypdf = need("pypdf")
    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        try:
            ok = reader.decrypt("")
        except Exception:
            ok = 0
        if not ok:
            fail(
                "This PDF is password-protected.",
                "I can't and won't unlock it. Use your own credentials to save an "
                "unprotected copy, or obtain one from the publisher.",
            )
    return reader


def rnd(vals):
    return [round(v, 1) for v in vals]


# ---------- toc ----------

def flatten_outline(reader):
    flat = []

    def walk(items, level):
        for item in items:
            if isinstance(item, list):
                walk(item, level + 1)
                continue
            try:
                page = reader.get_destination_page_number(item) + 1
            except Exception:
                continue
            flat.append({"level": level, "title": str(item.title or "").strip(), "page": page})

    walk(reader.outline, 1)
    return flat


def add_page_ends(entries, page_count):
    for i, e in enumerate(entries):
        end = page_count
        for later in entries[i + 1:]:
            if later["level"] <= e["level"]:
                end = max(e["page"], later["page"] - 1)
                break
        e["page_end"] = end
    return entries


def guess_chapter_level(entries):
    """The shallowest level holding ≥3 entries whose pages strictly increase
    (skips a front-matter-only top level)."""
    by_level = {}
    for e in entries:
        by_level.setdefault(e["level"], []).append(e)
    for level in sorted(by_level):
        pages = [e["page"] for e in by_level[level]]
        if len(pages) >= 3 and all(a < b for a, b in zip(pages, pages[1:])):
            return level
    return None


def chapter_number(title, ordinal):
    m = re.match(r"^\s*(?:chapter\s+)?(\d{1,3})\b", title, re.I)
    return int(m.group(1)) if m else ordinal


def text_layer_probe(path, page_count):
    pdfplumber = need("pdfplumber")
    sample = sorted({1, max(1, page_count // 2), page_count})
    chars = []
    with pdfplumber.open(str(path)) as pdf:
        for n in sample:
            chars.append(len((pdf.pages[n - 1].extract_text() or "").strip()))
    return (sum(chars) / len(chars)) >= 50


def printed_toc_fallback(path, page_count):
    pdfplumber = need("pdfplumber")
    rows = []
    with pdfplumber.open(str(path)) as pdf:
        for n in range(1, min(40, page_count) + 1):
            text = pdf.pages[n - 1].extract_text() or ""
            hits = [m for m in (TOC_LINE.match(ln) for ln in text.splitlines()) if m]
            if len(hits) >= 3:
                for m in hits:
                    rows.append((int(m.group(1)), m.group(2).strip(" ."), int(m.group(3))))
    seen, chapters = set(), []
    for num, title, page in rows:
        if num in seen:
            continue
        seen.add(num)
        chapters.append({"n": num, "title": title, "page": page})
    chapters.sort(key=lambda c: c["n"])
    return chapters


def cmd_toc(args):
    path = open_checked(args.pdf)
    reader = pypdf_reader(path)
    page_count = len(reader.pages)
    has_text = text_layer_probe(path, page_count)
    result = {"ok": True, "file": str(path), "page_count": page_count,
              "text_layer": has_text}
    if not has_text:
        result["text_note"] = (
            "This looks scanned (little or no text layer). OCR is out of scope — obtain "
            "a text PDF (publisher e-book or library copy); figure crops still work."
        )
    entries = flatten_outline(reader)
    if entries:
        add_page_ends(entries, page_count)
        level = guess_chapter_level(entries)
        chapter_entries = [e for e in entries if e["level"] == level] if level else []
        result.update({
            "source": "outline",
            "page_numbers": "pdf",
            "offset_applied": 0,
            "chapters": [
                {"n": chapter_number(e["title"], i + 1), "title": e["title"],
                 "page_start": e["page"], "page_end": e["page_end"], "level": e["level"]}
                for i, e in enumerate(chapter_entries)
            ],
            "outline": entries,
            "note": ("A seed for CONTENTS.md — verify chapter 1's range before trusting "
                     "the rest. A hand-edited CONTENTS.md always wins."),
        })
        print(json.dumps(result, indent=2))
        return
    chapters = printed_toc_fallback(path, page_count)
    if not chapters:
        result.update({
            "source": "none",
            "chapters": [],
            "note": ("No outline and no parseable printed TOC. Build CONTENTS.md's chapter "
                     "table by hand from the book's own table of contents — that is the "
                     "normal path here, not a failure."),
        })
        print(json.dumps(result, indent=2))
        return
    offset = args.offset or 0
    for i, c in enumerate(chapters):
        c["page_start"] = c.pop("page") + offset
    for i, c in enumerate(chapters):
        c["page_end"] = (chapters[i + 1]["page_start"] - 1) if i + 1 < len(chapters) \
            else page_count
    result.update({
        "source": "printed-toc",
        "page_numbers": "pdf" if offset else "printed",
        "offset_applied": offset,
        "calibration_needed": not offset,
        "chapters": chapters,
        "note": (
            "Ranges come from the PRINTED table of contents. Printed page N is not PDF "
            "page N: open the PDF near chapter 1's printed page, find the PDF page where "
            "chapter 1 actually starts, and re-run with --offset "
            "(actual_pdf_page − printed_page). Or skip the re-run and write corrected "
            "ranges into CONTENTS.md directly — the manifest you hand-edit is the "
            "authority; this output is only a seed."
        ) if not offset else (
            "Offset applied. Verify chapter 1's range in the PDF, then confirm the table "
            "with the student before writing CONTENTS.md."
        ),
    })
    print(json.dumps(result, indent=2))


# ---------- text ----------

def parse_range(spec):
    m = re.match(r"^(\d+)-(\d+)$", spec.strip())
    if not m:
        fail("Could not parse --pages " + repr(spec), "Format: A-B, e.g. 201-236.")
    a, z = int(m.group(1)), int(m.group(2))
    if a > z:
        fail("--pages start exceeds end.", "Format: A-B with A ≤ B.")
    return a, z


def cmd_text(args):
    path = open_checked(args.pdf)
    guard_out(args.out)
    out = Path(args.out)
    if out.exists() and not args.force:
        print(json.dumps({"ok": True, "cached": True, "file": str(out),
                          "note": "existing cache kept; --force re-extracts"}, indent=2))
        return
    a, z = parse_range(args.pages)
    pdfplumber = need("pdfplumber")
    started = time.time()
    parts = ["<!-- extract: {} pages {}–{} · ingest_pdf.py -->".format(path.name, a, z)]
    chars = 0
    with pdfplumber.open(str(path)) as pdf:
        if z > len(pdf.pages):
            fail("Page {} is out of range (1–{}).".format(z, len(pdf.pages)), "")
        for n in range(a, z + 1):
            text = pdf.pages[n - 1].extract_text(layout=args.layout) or ""
            chars += len(text)
            parts.append("<!-- p.{} -->\n{}".format(n, text.rstrip()))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(parts) + "\n")
    print(json.dumps({
        "ok": True, "cached": False, "file": str(out), "pages": args.pages,
        "chars": chars, "seconds": round(time.time() - started, 1),
        "note": ("Displayed math is mangled in extracted text — crop and read the image "
                 "for anything verbatim."),
    }, indent=2))


# ---------- figures ----------

def h_overlap(a, b):
    inter = min(a[2], b[2]) - max(a[0], b[0])
    width = min(a[2] - a[0], b[2] - b[0])
    return (inter / width) if width > 0 else 0.0


def region_bbox(obj):
    return (float(obj["x0"]), float(obj["top"]), float(obj["x1"]), float(obj["bottom"]))


def content_regions(page):
    regions = [region_bbox(o) for o in page.images]
    for o in list(page.rects) + list(page.curves):
        r = region_bbox(o)
        if (r[2] - r[0]) * (r[3] - r[1]) >= MIN_AREA:
            regions.append(r)
    return regions


def guess_bbox(caption, regions, direction):
    cx0, cy0, cx1, cy1 = caption
    picked = []
    for r in regions:
        if h_overlap(r, caption) < MIN_OVERLAP:
            continue
        if direction == "above" and (r[3] <= cy0 + 2) and (cy0 - r[1] <= BAND):
            picked.append(r)
        if direction == "below" and (r[1] >= cy1 - 2) and (r[3] - cy1 <= BAND):
            picked.append(r)
    if not picked:
        return None
    return [min(r[0] for r in picked), min(r[1] for r in picked),
            max(r[2] for r in picked), max(r[3] for r in picked)]


def band_fallback(page, caption, direction):
    cx0, cy0, cx1, cy1 = caption
    words = page.extract_words() or []
    tx0 = min((float(w["x0"]) for w in words), default=page.bbox[0] + 36)
    tx1 = max((float(w["x1"]) for w in words), default=page.bbox[2] - 36)
    if direction == "above":
        top = max(float(page.bbox[1]) + 30, cy0 - BAND)
        return [min(tx0, cx0), top, max(tx1, cx1), cy0 - 4] if cy0 - 4 > top else None
    bottom = min(float(page.bbox[3]) - 30, cy1 + BAND)
    return [min(tx0, cx0), cy1 + 4, max(tx1, cx1), bottom] if bottom > cy1 + 4 else None


def cmd_figures(args):
    path = open_checked(args.pdf)
    if args.bbox:
        guard_out(args.out or "")
        if not args.out:
            fail("--bbox needs --out FILE.png.", "")
        try:
            x0, y0, x1, y1 = (float(v) for v in args.bbox.split(","))
        except ValueError:
            fail("Could not parse --bbox " + repr(args.bbox),
                 "Format: x0,y0,x1,y1 in PDF points, origin top-left.")
        pdfium = need("pypdfium2")
        pdf = pdfium.PdfDocument(str(path))
        if args.page < 1 or args.page > len(pdf):
            fail("Page {} is out of range (1–{}).".format(args.page, len(pdf)), "")
        page = pdf[args.page - 1]
        w, h = page.get_size()
        x0, y0 = max(0.0, x0), max(0.0, y0)
        x1, y1 = min(float(w), x1), min(float(h), y1)
        if x1 <= x0 or y1 <= y0:
            fail("The bbox lies outside the page ({}×{} pt).".format(round(w), round(h)),
                 "Use coordinates from the list mode (points, origin top-left).")
        # top-left-origin bbox → pypdfium2 crop = amounts trimmed (left, bottom, right, top)
        bitmap = page.render(scale=args.scale, crop=(x0, h - y1, w - x1, y0))
        img = bitmap.to_pil()
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out))
        print(json.dumps({"ok": True, "file": str(out), "page": args.page,
                          "bbox": rnd([x0, y0, x1, y1]), "width_px": img.width,
                          "height_px": img.height, "scale": args.scale}, indent=2))
        return
    pdfplumber = need("pdfplumber")
    candidates = []
    with pdfplumber.open(str(path)) as pdf:
        if args.page < 1 or args.page > len(pdf.pages):
            fail("Page {} is out of range (1–{}).".format(args.page, len(pdf.pages)), "")
        page = pdf.pages[args.page - 1]
        regions = content_regions(page)
        for line in page.extract_text_lines() or []:
            m = CAPTION.match(line.get("text", ""))
            if not m:
                continue
            kind = "table" if m.group(1).lower().startswith("table") else "figure"
            direction = "below" if kind == "table" else "above"
            cap = (float(line["x0"]), float(line["top"]),
                   float(line["x1"]), float(line["bottom"]))
            guess = guess_bbox(cap, regions, direction)
            guess_kind = "matched-content" if guess else None
            if guess is None:
                guess = band_fallback(page, cap, direction)
                guess_kind = "band-fallback" if guess else None
            candidates.append({
                "label": "{} {}".format("Table" if kind == "table" else "Figure",
                                        m.group(2).rstrip(".")),
                "kind": kind,
                "page": args.page,
                "caption": line.get("text", "")[:240],
                "caption_bbox": rnd(cap),
                "guessed_content_bbox": rnd(guess) if guess else None,
                "guess_kind": guess_kind,
            })
    print(json.dumps({
        "ok": True, "page": args.page, "candidates": candidates,
        "note": ("guessed_content_bbox is a heuristic (images/drawings near the caption). "
                 "Verify visually; pass a corrected --bbox to render the crop."),
    }, indent=2))


# ---------- split ----------

def cmd_split(args):
    path = open_checked(args.pdf)
    guard_out(args.out)
    pypdf = need("pypdf")
    reader = pypdf_reader(path)
    outdir = Path(args.out)
    written, skipped = [], []
    for part in args.chapters.split(","):
        m = re.match(r"^\s*(\d+)\s*=\s*(\d+)-(\d+)\s*$", part)
        if not m:
            fail("Could not parse --chapters segment " + repr(part),
                 "Format: N=A-B[,N=A-B…], e.g. 7=201-236,8=237-268.")
        ch, a, z = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if a > z or z > len(reader.pages):
            fail("Chapter {} range {}-{} is out of bounds (1–{}).".format(
                ch, a, z, len(reader.pages)), "")
        dest = outdir / "ch{:02d}.pdf".format(ch)
        if dest.exists():
            skipped.append(str(dest))
            continue
        writer = pypdf.PdfWriter()
        for n in range(a, z + 1):
            writer.add_page(reader.pages[n - 1])
        outdir.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as fh:
            writer.write(fh)
        written.append({"chapter": ch, "file": str(dest), "pages": "{}-{}".format(a, z)})
    print(json.dumps({"ok": True, "written": written, "skipped_cached": skipped,
                      "note": "Prefer page-ranged native reading; split only when the "
                              "big file defeats your reader."}, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("toc", help="outline/TOC → chapter page ranges")
    p.add_argument("pdf")
    p.add_argument("--offset", type=int, default=0,
                   help="printed-page → PDF-page offset (printed-TOC fallback only)")
    p.set_defaults(fn=cmd_toc)

    p = sub.add_parser("text", help="cache a page range's text")
    p.add_argument("pdf")
    p.add_argument("--pages", required=True, help="A-B, e.g. 201-236")
    p.add_argument("--out", required=True)
    p.add_argument("--layout", action="store_true", help="layout-preserving (multi-column)")
    p.add_argument("--force", action="store_true", help="re-extract over an existing cache")
    p.set_defaults(fn=cmd_text)

    p = sub.add_parser("figures", help="caption candidates, or render a crop")
    p.add_argument("pdf")
    p.add_argument("--page", type=int, required=True, help="1-based page number")
    p.add_argument("--bbox", default=None, help="x0,y0,x1,y1 in PDF points (crop mode)")
    p.add_argument("--out", default=None, help="output PNG path (crop mode)")
    p.add_argument("--scale", type=float, default=2.0)
    p.set_defaults(fn=cmd_figures)

    p = sub.add_parser("split", help="per-chapter PDFs (escape hatch)")
    p.add_argument("pdf")
    p.add_argument("--chapters", required=True, help="N=A-B[,N=A-B…]")
    p.add_argument("--out", required=True, help="output directory, e.g. books/<slug>/extract/")
    p.set_defaults(fn=cmd_split)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
