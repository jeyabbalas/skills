#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf>=1.24"]
# ///
"""Locate and crop figures/tables in a paper PDF.

Run with `uv run scripts/pdf_figures.py …` (uv resolves PyMuPDF automatically).
No uv? `python3 -m pip install --user pymupdf`, then plain `python3 scripts/…`.
Neither available? Skip extraction: generate the figure page with a placeholder
panel and let the user drop a screenshot at the expected .png path.

Subcommands (all print JSON to stdout; coordinates are PDF points, origin at
the page's top-left — the same frame `crop --bbox` expects):

  list PDF [--page N]
      Page count, document outline, and figure/table caption candidates, each
      with the caption's bbox and a best-guess content bbox (union of image and
      vector-drawing regions above a Figure caption / below a Table caption).
      The guess is a starting point — verify visually before cropping.

  extract PDF --out DIR [--page N]
      Save every embedded raster image as PNG (p<page>-img<n>.png) with a
      manifest of placements. Vector figures have no embedded raster — use crop.

  crop PDF --page N --bbox x0,y0,x1,y1 --out FILE.png [--scale 2]
      Render the page region to FILE.png at scale× resolution (default 2×).

  text PDF --pages 1-2,5
      Plain text of the given pages (1-based; ranges and commas). For harnesses
      that cannot read PDF pages directly.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz  # older PyMuPDF releases
except ImportError:
    print(
        json.dumps(
            {
                "ok": False,
                "error": "PyMuPDF is not installed.",
                "hint": (
                    "Preferred: run via `uv run scripts/pdf_figures.py …`. "
                    "Without uv: `python3 -m pip install --user pymupdf` then re-run "
                    "with python3. Without either: skip extraction — build the figure "
                    "page with a placeholder panel and tell the user which .png path "
                    "a manual screenshot should be saved to."
                ),
            },
            indent=2,
        )
    )
    sys.exit(1)

CAPTION = r"^\s*(Figure|Fig\.|Table)\s{0,2}(\d+|[A-Z]\.?\d*)\s*[.:]"

MIN_AREA = 25.0  # ignore vector fragments smaller than this (pt²)
BAND = 420.0  # how far (pt) from a caption content may reach
MIN_OVERLAP = 0.25  # required horizontal overlap between caption and content


def rnd(rect):
    return [round(v, 1) for v in rect]


def fail(error, hint):
    print(json.dumps({"ok": False, "error": error, "hint": hint}, indent=2))
    sys.exit(1)


def guard_out(path):
    skill_dir = Path(__file__).resolve().parent.parent
    if skill_dir in Path(path).resolve().parents:
        fail(
            "Refusing to write into the installed skill directory: " + str(path),
            "Pass an --out path inside the reading workspace.",
        )


def h_overlap(a, b):
    inter = min(a[2], b[2]) - max(a[0], b[0])
    width = min(a[2] - a[0], b[2] - b[0])
    return (inter / width) if width > 0 else 0.0


def content_regions(page):
    """Candidate content rects: embedded images + clustered vector drawings."""
    regions = [tuple(b[:4]) for b in page.get_text("blocks") if b[6] == 1]
    for d in page.get_drawings():
        r = d["rect"]
        if r.width * r.height >= MIN_AREA:
            regions.append((r.x0, r.y0, r.x1, r.y1))
    return regions


def guess_bbox(caption_bbox, regions, direction):
    """Union content regions above (figures) or below (tables) a caption."""
    cx0, cy0, cx1, cy1 = caption_bbox
    picked = []
    for r in regions:
        if h_overlap(r, caption_bbox) < MIN_OVERLAP:
            continue
        if direction == "above" and (r[3] <= cy0 + 2) and (cy0 - r[1] <= BAND):
            picked.append(r)
        if direction == "below" and (r[1] >= cy1 - 2) and (r[3] - cy1 <= BAND):
            picked.append(r)
    if not picked:
        return None
    return [
        min(r[0] for r in picked),
        min(r[1] for r in picked),
        max(r[2] for r in picked),
        max(r[3] for r in picked),
    ]


def text_span(page):
    """Horizontal extent of the page's text blocks (the column width)."""
    blocks = [b for b in page.get_text("blocks") if b[6] == 0]
    if not blocks:
        return page.rect.x0 + 36, page.rect.x1 - 36
    return min(b[0] for b in blocks), max(b[2] for b in blocks)


def band_fallback(page, caption_bbox, direction):
    """Full-column band adjoining the caption — a generous over-crop for
    vector figures whose drawings hide inside Form XObjects."""
    cx0, cy0, cx1, cy1 = caption_bbox
    tx0, tx1 = text_span(page)
    if direction == "above":
        top = max(page.rect.y0 + 30, cy0 - BAND)
        return [min(tx0, cx0), top, max(tx1, cx1), cy0 - 4] if cy0 - 4 > top else None
    bottom = min(page.rect.y1 - 30, cy1 + BAND)
    return [min(tx0, cx0), cy1 + 4, max(tx1, cx1), bottom] if bottom > cy1 + 4 else None


def cmd_list(args):
    doc = fitz.open(args.pdf)
    pages = range(len(doc)) if args.page is None else [args.page - 1]
    import re

    cap_re = re.compile(CAPTION)
    candidates = []
    for pno in pages:
        if pno < 0 or pno >= len(doc):
            fail("Page {} is out of range (1–{}).".format(args.page, len(doc)), "")
        page = doc[pno]
        blocks = [b for b in page.get_text("blocks") if b[6] == 0]
        regions = content_regions(page)
        for b in blocks:
            text = b[4].strip()
            m = cap_re.match(text)
            if not m:
                continue
            kind = "table" if m.group(1).lower().startswith("table") else "figure"
            direction = "below" if kind == "table" else "above"
            guess = guess_bbox(b[:4], regions, direction)
            guess_kind = "matched-content" if guess else None
            if guess is None:
                guess = band_fallback(page, b[:4], direction)
                guess_kind = "band-fallback" if guess else None
            candidates.append(
                {
                    "label": "{} {}".format(
                        "Table" if kind == "table" else "Figure", m.group(2).rstrip(".")
                    ),
                    "kind": kind,
                    "page": pno + 1,
                    "caption": text[:240],
                    "caption_bbox": rnd(b[:4]),
                    "guessed_content_bbox": rnd(guess) if guess else None,
                    "guess_kind": guess_kind,
                }
            )
    toc = [
        {"level": lvl, "title": title, "page": page}
        for lvl, title, page in doc.get_toc(simple=True)
    ]
    print(
        json.dumps(
            {
                "ok": True,
                "page_count": len(doc),
                "outline": toc,
                "candidates": candidates,
                "note": (
                    "guessed_content_bbox is a heuristic (images/drawings near the "
                    "caption). Verify visually; pass a corrected --bbox to crop if needed."
                ),
            },
            indent=2,
        )
    )


def cmd_extract(args):
    guard_out(args.out)
    doc = fitz.open(args.pdf)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    pages = range(len(doc)) if args.page is None else [args.page - 1]
    saved = []
    for pno in pages:
        page = doc[pno]
        for i, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]
            try:
                bbox = page.get_image_bbox(img)
            except ValueError:
                bbox = None
            pix = fitz.Pixmap(doc, xref)
            if pix.colorspace and pix.colorspace.n > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            name = "p{:02d}-img{}.png".format(pno + 1, i)
            pix.save(outdir / name)
            saved.append(
                {
                    "file": str(outdir / name),
                    "page": pno + 1,
                    "bbox": rnd([bbox.x0, bbox.y0, bbox.x1, bbox.y1]) if bbox else None,
                    "width_px": pix.width,
                    "height_px": pix.height,
                }
            )
    print(
        json.dumps(
            {
                "ok": True,
                "images": saved,
                "note": (
                    "Vector-drawn figures have no embedded raster image — render "
                    "those with crop."
                ),
            },
            indent=2,
        )
    )


def cmd_crop(args):
    guard_out(args.out)
    doc = fitz.open(args.pdf)
    if args.page < 1 or args.page > len(doc):
        fail("Page {} is out of range (1–{}).".format(args.page, len(doc)), "")
    page = doc[args.page - 1]
    try:
        x0, y0, x1, y1 = (float(v) for v in args.bbox.split(","))
    except ValueError:
        fail("Could not parse --bbox {!r}.".format(args.bbox), "Format: x0,y0,x1,y1 in points.")
    clip = fitz.Rect(x0, y0, x1, y1) & page.rect
    if clip.is_empty:
        fail(
            "The bbox lies outside the page ({}×{} pt).".format(
                round(page.rect.width), round(page.rect.height)
            ),
            "Use coordinates from `list` (PDF points, origin top-left).",
        )
    pix = page.get_pixmap(matrix=fitz.Matrix(args.scale, args.scale), clip=clip)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pix.save(out)
    print(
        json.dumps(
            {
                "ok": True,
                "file": str(out),
                "page": args.page,
                "bbox": rnd([clip.x0, clip.y0, clip.x1, clip.y1]),
                "width_px": pix.width,
                "height_px": pix.height,
                "scale": args.scale,
            },
            indent=2,
        )
    )


def cmd_text(args):
    doc = fitz.open(args.pdf)
    pages = []
    for part in args.pages.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))
    out = []
    for pno in pages:
        if pno < 1 or pno > len(doc):
            fail("Page {} is out of range (1–{}).".format(pno, len(doc)), "")
        out.append({"page": pno, "text": doc[pno - 1].get_text("text")})
    print(json.dumps({"ok": True, "pages": out}, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="find figure/table caption candidates")
    p.add_argument("pdf")
    p.add_argument("--page", type=int, default=None, help="1-based page filter")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("extract", help="save embedded raster images")
    p.add_argument("pdf")
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--page", type=int, default=None, help="1-based page filter")
    p.set_defaults(fn=cmd_extract)

    p = sub.add_parser("text", help="plain text of given pages")
    p.add_argument("pdf")
    p.add_argument("--pages", required=True, help="1-based pages, e.g. 1-2,5")
    p.set_defaults(fn=cmd_text)

    p = sub.add_parser("crop", help="render a page region to PNG")
    p.add_argument("pdf")
    p.add_argument("--page", type=int, required=True, help="1-based page number")
    p.add_argument("--bbox", required=True, help="x0,y0,x1,y1 in PDF points")
    p.add_argument("--out", required=True, help="output PNG path")
    p.add_argument("--scale", type=float, default=2.0)
    p.set_defaults(fn=cmd_crop)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
