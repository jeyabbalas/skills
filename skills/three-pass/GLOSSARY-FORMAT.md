`papers/<slug>/GLOSSARY.md` is the glossary's source of truth — a reference the reader returns to, built one blocked term at a time. `glossary.html` is its render (ARTIFACTS.md); edits happen only here.

## Template

```md
# Glossary — {paper title}

## {Term}
{1–3 sentences defining the term in this reader's register, tied to how the paper uses it.}
**Link**: [{authoritative source, named}]({url})
*Tags*: {tag}, {tag} · *first needed*: §{N}
```

## Rules

- **Alphabetical by term.** The page's A–Z filter assumes it; insertion order carries no meaning here.
- **Write for this reader.** The definition is in the register READER.md prescribes. A term the reader already owns does not belong in their glossary.
- **Offer, don't push.** When a term was load-bearing in an exchange, offer one line — "add *variational posterior* to the glossary?" — and write it only on yes.
- **Authoritative links only.** A textbook, a review article, the term's original paper, canonical documentation. If the best source you can find is a content farm, leave the link off.
- **Edit in place; removal is allowed.** A glossary is a reference, not a record — stale or outgrown entries go. (Realizations and corrections belong in `notes.md`, which never deletes.)
- **Definition, not discussion.** If the entry is growing paragraphs of insight, that insight is a margin note; keep the gloss tight and link out for depth.
