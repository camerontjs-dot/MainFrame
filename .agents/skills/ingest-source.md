---
name: ingest-source
description: Walk a single file from 01_ingest/ready/ through the agent-driven enrichment loop — read, classify, find connections, discuss, enrich, hand off to bin/prep-ingest.
status: stub
---

# ingest-source

## Purpose

The end-to-end per-file skill that the [ingest-agent subagent](../../agents/ingest-agent.md) invokes for each file in `01_ingest/ready/`. Encapsulates the full read → classify → connect → discuss → enrich → hand-off pass.

## Status

**Stub** — to be expanded as the agent-ingest pattern matures (ADR-009 Phase 5). The full procedure currently lives inline in [agents/ingest-agent.md](../../agents/ingest-agent.md); this skill will eventually carry the procedure so the agent definition can stay focused on role + guardrails.

## Related

- [classify-note](classify-note.md) — substep for type/domain/tags
- [extract-metadata](extract-metadata.md) — substep for frontmatter enrichment
- [rename-material](rename-material.md) — final renaming step
- [create-source-summary](create-source-summary.md) — for raw items that need a separate searchable note
