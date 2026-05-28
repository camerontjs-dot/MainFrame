# 01_ingest - Local Rules

> [!WARNING]
> This folder is the boundary between fast capture and durable knowledge. The agent has judgment authority here, but raw evidence must never be silently modified.

## Defensive Constraints

1. **Never auto-route without confirmation.** Files in `ready/` await user-confirmed enrichment before moving to `queue/`. The sub-agent (`agents/ingest-agent.md`) proposes; the user accepts.
2. **Never edit body content during enrichment.** Frontmatter and appended `## Connections` sections only. The original body is evidence — preserve it verbatim.
3. **Raw items are immutable.** Files with `type: raw` may have their frontmatter updated (status, tags, links) but their body and original filename must be preserved.
4. **No domain guessing.** When the domain is unclear, leave `domain: ""` and ask the user. Don't pick the closest existing domain to avoid asking.
5. **Read-only access to durable knowledge.** The ingest sub-agent may read `10_knowledge/` for connection-finding but writes only to files inside `01_ingest/`.
6. **Status transitions are explicit.** The sub-agent sets `status: routed` when it begins enrichment and `status: extracted` when it finishes. `bin/prep-ingest` is the gate from `ready/ → queue/`.

## Layer Subdirectories

- `queue/` — files with `status: extracted`, awaiting deterministic routing by `bin/ingest-minion run --apply`.
- `ready/` — files with `status: skimmed` or `routed`, awaiting agent work.
- `processing/` — reserved for future per-file work-in-progress; not currently used.
- `rejected/` — dead-letter for unprocessable files (binary garbage, encoding errors). Not a normal destination after ADR-009.
- `renamed/` — reserved for future filename-only-change staging; not currently used.

## Procedure

The agent-driven procedure lives in [agents/ingest-agent.md](../agents/ingest-agent.md). The deterministic pieces live in `bin/ingest-minion` (normalize + route) and `bin/prep-ingest` (ready → queue validation).
