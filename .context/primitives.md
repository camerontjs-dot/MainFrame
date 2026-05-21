# Context Primitives & Metadata

This file defines the basic object types and the required metadata schema for the Second Brain.

## Simplified Metadata Schema
For the initial markdown-first phase, we use a simplified YAML frontmatter schema. This prevents manual entry burnout while still providing enough structure for ingestion and routing.

```yaml
---
title: "Name of the file"
domain: "Broad area (e.g. ai-systems, productivity)"
type: raw | note | live | project | decision
status: queued | active | stable | archived
source: "URL or local path to raw evidence"
tags: ["sensitivity", "etc"]
---
```

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

### 5. Decision
- **Type:** `decision`
- **Location:** `DECISIONS.md` or local project decisions.
- **Rule:** Captures accepted trade-offs. Not for draft brainstorming.
