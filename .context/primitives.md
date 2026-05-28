# Context Primitives & Metadata

This file defines the basic object types and the required metadata schema for the Mainframe.

## Simplified Metadata Schema
For the initial markdown-first phase, we use a simplified YAML frontmatter schema. This prevents manual entry burnout while still providing enough structure for ingestion and routing.

```yaml
---
title: "Name of the file"
domain: "Broad area (e.g. ai-systems, productivity)"
type: raw | note | live | project | decision
status: queued | skimmed | routed | extracted | active | synthesized | stable | archived | parked
source: "URL or local path to raw evidence"
tags: ["sensitivity", "etc"]
links: ["wikilink-targets-extracted-from-body"]  # populated by ingest-minion during normalization
---
```

## Status Lifecycle

The `status` field encodes where a file is in its lifecycle. Pending ADR-009 ratification:

| Status | Location | Meaning |
|---|---|---|
| `queued` | `01_ingest/queue/` or `01_ingest/ready/` | In ingest pipeline, awaiting any work |
| `skimmed` | `01_ingest/ready/` | Minion normalized; agent pending |
| `routed` | `01_ingest/ready/` | Agent has assigned domain/tags; enrichment in progress |
| `extracted` | `01_ingest/queue/` | Agent enrichment complete; ready for minion pass-2 |
| `synthesized` | `10_knowledge/<domain>/` | Durable knowledge, agent-enriched |
| `active` | `20_live/` | Current state, live record |
| `stable` | `10_knowledge/` | Settled durable knowledge |
| `archived` | `90_archive/` | Preserved, not active |
| `parked` | any | Set aside; not useful yet, duplicate, or too speculative |

## Primitives

### 1. Raw Item
- **Type:** `raw`
- **Location:** `00_inbox` or `01_ingest/queue`
- **Rule:** Do not edit the content. Keep it as immutable evidence.

### 2. Note
- **Type:** `note`
- **Location:** `10_knowledge`
- **Rule:** Synthesized, extracted, or durable concepts. Must have a `source` if it derives from evidence.

### 3. Live Record
- **Type:** `live`
- **Location:** `20_live`
- **Rule:** Represents current state. Must not silently overwrite history. Use snapshots or append-only timelines.

### 4. Project Record
- **Type:** `project`
- **Location:** `30_projects`
- **Rule:** Tracks active outcomes. Requires a state, goal, and next action.
- **README Metadata Extension:** `project_state`, `goal`, `next_action`, and `updated` drive `30_projects/index.md` via `bin/sync-project-index`.

### 5. Decision
- **Type:** `decision`
- **Location:** `DECISIONS.md` or local project decisions.
- **Rule:** Captures accepted trade-offs. Not for draft brainstorming.
