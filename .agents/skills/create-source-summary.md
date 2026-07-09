---
name: create-source-summary
description: For raw items that need a separate searchable note alongside the immutable evidence, create a sibling summary file that links back to the source.
status: active
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

**Active** — delegates directly to the `extraction-agent`.

When invoked (e.g. from `ingest-source` during raw enrichment), immediately pass the target file to the `extraction-agent` (defined in `../../agents/extraction-agent.md`) which handles the actual deep reading and extraction workflow.

Do not attempt to execute the extraction logic manually within this skill; the extraction agent contains the strict guardrails for formatting, routing through `01_ingest/ready/`, and maintaining evidence immutability.

**Integration note (2026-06-13):** Now explicitly called out from the `ingest-source` skill for cases where a raw benefits from a synthesized companion `note`. This supports Fix 3 goals of increasing synthesis rate vs raw accumulation.

## Related

- [ingest-source](ingest-source.md) — the parent skill
- [ADR-007](../../DECISIONS.md) — defines the existing PDF stub-creation behavior
