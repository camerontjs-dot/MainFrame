---
name: classify-note
description: Assign domain, type, and tags to a file based on its content. Propose to user for confirmation before applying.
status: stub
---

# classify-note

## Purpose

Read a file in `01_ingest/ready/` and propose:
- **`domain`** — one of the existing `10_knowledge/<domain>/` subdirectories.
- **`type`** — `raw` (unprocessed evidence) or `note` (synthesized content).
- **`tags`** — free-form, lowercase, kebab-case topic markers.

## Status

**Stub** — to be expanded. Initial guidance:
- Use existing notes in the candidate domain as calibration. If the file doesn't fit any existing domain, leave `domain: ""` and surface the gap rather than creating a new domain (per [ADR-007](../../DECISIONS.md), new domains are created manually).
- Distinguish `raw` from `note`: raw is evidence (clippings, transcripts, papers); note is synthesis or working knowledge.
- Tags should add retrieval value, not restate the title.

## Related

- [ingest-source](ingest-source.md) — the parent skill
- [extract-metadata](extract-metadata.md) — fills in the rest of frontmatter
