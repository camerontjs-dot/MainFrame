---
name: create-source-summary
description: For raw items that need a separate searchable note alongside the immutable evidence, create a sibling summary file that links back to the source.
status: stub
---

# create-source-summary

## Purpose

Some raw items (PDFs, long transcripts, scraped articles) are too dense for retrieval as-is. The ingest minion already creates a markdown stub for PDFs (per [ADR-007](../../DECISIONS.md)); this skill is the agent-driven version for markdown raw items that warrant a synthesized companion note.

The original raw file is preserved as evidence. A new `note`-type file is created alongside it, containing:
- Summary of the source
- Key claims or extracted facts
- Wikilinks to existing knowledge
- Citation back to the raw source

## Status

**Stub** — to be expanded. Initial guidance:
- Only invoke when the user explicitly requests a summary, or when the raw item is large enough that direct retrieval would be unhelpful.
- The summary file follows normal `note` rules: `type: note`, populated `domain`, links to the raw via `source:` or `[[wikilink]]`.
- Don't summarize unless asked. Most raw items live fine as evidence with frontmatter alone.

## Related

- [ingest-source](ingest-source.md) — the parent skill
- [ADR-007](../../DECISIONS.md) — defines the existing PDF stub-creation behavior
