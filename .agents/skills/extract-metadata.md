---
name: extract-metadata
description: Fill in remaining frontmatter fields (source, links, etc.) and update status as the file progresses through agent enrichment.
status: stub
---

# extract-metadata

## Purpose

After [classify-note](classify-note.md) has set `domain`, `type`, and `tags`, fill in the rest of the frontmatter:
- **`source`** — preserve if already set; otherwise infer from filename, body, or capture context.
- **`links`** — preserve the minion-extracted array; add agent-proposed connections.
- **`status`** — transition `skimmed → routed` when starting work, `routed → extracted` when done.

## Status

**Stub** — to be expanded. Initial guidance:
- Source is provenance — preserve original URLs, file paths, or attribution.
- Don't fabricate sources. If unknown, set `source: "unknown"` and surface to user.
- Status transitions are explicit signals to `bin/prep-ingest`; don't skip the intermediate `routed` state.

## Related

- [ingest-source](ingest-source.md) — the parent skill
- [.context/primitives.md](../../.context/primitives.md) — schema and status lifecycle
