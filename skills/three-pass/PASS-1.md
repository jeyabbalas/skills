Pass 1 is the bird's-eye view: acquire the paper, cache its anatomy, and produce a profile terse enough to read in five minutes — enough for the reader to decide whether the paper deserves a real read. Conciseness is the discipline of this pass: every field below has a cap, and the caps win.

Table of contents

- [Acquiring the paper](#acquiring-the-paper)
- [Registering](#registering)
- [Reading for the skeleton](#reading-for-the-skeleton)
- [SKELETON.md template](#skeletonmd-template)
- [The paper profile](#the-paper-profile)
- [Profile template](#profile-template)
- [Presenting pass 1](#presenting-pass-1)
- [Survey mode: several papers at once](#survey-mode-several-papers-at-once)
- [The relationship map](#the-relationship-map)

## Acquiring the paper

- **Given a file path**: verify it opens and is a PDF; then register.
- **Given an identifier or URL** (arXiv id, DOI, link): EXECUTE `fetch_paper.py` (contract and fallbacks in LAYOUT.md).
- **Given only a title or description**: search the web first to resolve it to an arXiv id, DOI, or direct PDF link — prefer arXiv, the publisher's open-access copy, PubMed Central, or the author's page — then fetch. Confirm with the reader you found the right paper (title + authors + year) before downloading.
- **When the download fails** (paywall, dead link): stop and ask the reader to download the PDF through their own access and give you the path. Never scrape around a paywall.

## Registering

1. Choose the slug (rules in LAYOUT.md) and EXECUTE `workspace.py add-paper --slug <slug> --pdf <path>`.
2. Write PAPER.md per PAPER-FORMAT.md — look up the BibTeX now (arXiv papers: fetch `https://arxiv.org/bibtex/<id>`; otherwise DBLP's search API, else the publisher page), and ask the one goal question: **"What do you want from this paper?"** Record the answer verbatim.
3. Add the LIBRARY.md row (LIBRARY-FORMAT.md), status `pass-1` (or `inbox` if the reader wants register-only).

## Reading for the skeleton

Page through the PDF once, in ranged reads, writing SKELETON.md as you go — after this pass, no session ever reads the PDF without first taking a page range from SKELETON.md:

1. EXECUTE `pdf_figures.py list` — the outline seeds the section tree; the candidates seed the figure/table inventory with pages, captions, and crop bboxes.
2. Read pages 1–2 fully (title, abstract, introduction). (All PDF reads: use your harness's page-ranged PDF reading; if it can't read PDFs, EXECUTE `pdf_figures.py text --pages …` instead — LAYOUT.md.)
3. Sweep the body for structure, not content: confirm section boundaries and page ranges, note where each numbered equation lives, skim first/last sentences of sections.
4. Read the conclusion pages fully.
5. Scan the reference list only to spot the handful of works the paper leans on (the ones cited in the introduction, background, and method comparisons).

## SKELETON.md template

```md
# Skeleton — {title}
pages: {N} · pdf: paper.pdf

## Outline
- 1 Introduction — p.2–2
- 3 Model Architecture — p.2–7
  - 3.2 Attention — p.3–5
    - 3.2.1 Scaled Dot-Product Attention — p.4
{the paper's own numbering; if it has none, assign 1, 2, 3 … here — this file is then
the numbering authority for anchors, summary sections, and page links everywhere}

## Figures & tables
- Figure 1 · p.3 · {caption gist, ≤8 words} · bbox [x0,y0,x1,y1] ({guess_kind})
- Table 1 · p.6 · {gist} · —

## Equations
- eq (1) · §3.2.1 · p.4 · {name, e.g. scaled dot-product attention}

## Key references
- [{n}] {Surname year} — {why the paper leans on it, ≤1 line} · cited in §{…}
```

Write it during the paging read; afterwards correct it in place only when an error surfaces. Coverage lives elsewhere — this file records *where things are*, never what you think of them.

## The paper profile

Fill `profile.md` from the skeleton read. Three standing constraints:

- **Respect the caps.** They are the point of pass 1. When a field wants to grow, cut.
- **Cite everything.** Every field ends with its source in the paper (`§`/`p.`). A claim you cannot anchor does not go in. When the paper is silent on a field, write "the paper does not say."
- **Authors are the one web-sourced field.** Look up the first and last author (background relative to this problem, institution, department) and link the source for each fact; anything inferred beyond sources is ◆. If the lookup is unavailable or finds nothing reliable, write "not verified this session" for that author — never fill from memory.

## Profile template

```md
# {Title} — paper profile

**Paper type**: {what kind of paper this is — empirical / theory / systems / survey / position …} (§/p.)
**In brief**: {1–3 lines: what the paper does and shows.}

## Title, decoded
{Unpack each load-bearing term of the title for this reader — one line per term, calibrated to READER.md.}

## Abstract, unpacked
- {each important point of the abstract as its own short bullet}

## Outline
- {N} {Section title} — {what it contains, one short line}
  - {nested for subsections}

## Problem & background
{1–3 lines: the problem, why it matters, and the essential concepts an outsider needs.} (§/p.)

## Authors
- {First author} — {background, institution, department} ([source]({url}))
- {Last author} — {…} ([source]({url}))

## Related work that matters
- {Surname year [n]} — {one sentence: what it is and how it ties to this paper's problem, the prior state of the art, or the method}. (§/p.)
{1–5 entries, no more}

## Hypothesis & claims
{1–3 sentences: what the authors propose, how the method differs from the related work above, the main hypothesis, the claims, and the core assumptions.} (§/p.)

## Main results
{1–3 sentences: the headline results, tied to the hypothesis and the problem.} (§/p.)

## Conclusions
{1–3 sentences: what the authors conclude.} (§/p.)
```

## Presenting pass 1

1. Render `profile.html` and the paper hub, refresh the library dashboard (ARTIFACTS.md), and open the profile for the reader (serving notes in LAYOUT.md).
2. Give a three-sentence spoken version in chat — type, claim, result.
3. Ask the gate question: **worth a pass 2?** Record their decision (PAPER.md status + log line). On a yes — now or "next time" — propose the entry unit for the `next:` pointer: summary §1 by default, or the section closest to their goal (say which and why). Never start pass 2 in the same breath unless they ask.

## Survey mode: several papers at once

Run Acquiring → Registering → skeleton → profile for each paper, sequentially — at most **four profiles per session**; more papers than that wait for the next session (say so, and log the remainder as `inbox`). Then build the relationship map, and end with one question: which of these, if any, go to pass 2?

## The relationship map

`map.md` / `map.html` at the workspace root (data schema and iteration rules in ARTIFACTS.md). The map is a claim about how the papers relate — ground it:

- An edge exists because one paper cites the other, they attack the same problem, or they share a method — and the label says which, in ≤4 words. An edge you inferred without support in any of the papers is a ◆ claim; say so when presenting.
- Nodes carry no detail — clicking one reveals the full profile panel; the map only arranges and links.
- Present the layout logic in one line ("time flows left to right; rows share a problem"), then iterate: the reader asks for moves and relabels, you edit the data block and re-render. The map is done when the reader says it matches their mental model.
