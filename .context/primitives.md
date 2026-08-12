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
links: ["trailing-slug-or-full-stem"]  # graph + ingest metadata; see Link Convention below
---
```

## Link Convention (ADR-033)

MainFrame uses **two equivalent graph channels**. MindGraph indexes **both** at ingest:

| Channel | Location | Purpose |
|---------|----------|---------|
| `links:` | YAML frontmatter | Fast authoring, ingest metadata, machine scan |
| `[[wikilinks]]` | Body (Truth section) | Human-readable prose, relationship labels |

**Rules:**

1. **Either channel is sufficient** for graph edges and `--expand`. Using both is fine; duplicates dedupe at ingest.
2. **Prefer canonical trailing slugs** for targets inside the same index scope, e.g. `gxp-pharma-source-catalog` resolves to `2026-06-13__regulated-systems__raw__gxp-pharma-source-catalog.md` when unique. Use the **full filename stem** when the slug is ambiguous across domains/dates.
3. **Do not wikilink `30_projects/` paths** in `10_knowledge/` notes. Reference projects in prose (`30_projects/example-project/`) until a reviewed bridge registry exists. Concrete project names belong in that project's own repo or private workbench, not in MainFrame durable notes.
4. **Ingest minion** still mirrors body `[[wikilinks]]` → `links:` during pass-1 normalization. That sync is one-way (body → frontmatter); authors may also write `links:` directly.
5. **Raw immutability unchanged:** for `type: raw`, add connections via frontmatter `links:` and/or an appended `## Connections` section — not inline body edits.

**Non-resolving targets** (project slugs, external URLs, ambiguous slugs) may remain in `links:` as intent markers; they stay dangling in the graph until the target exists or a bridge is approved.

### Graph authorship and review disposition

Body wikilinks remain the canonical readable edge. Existing untyped links are
valid and do not need to be rewritten. For new typed body links, use only the
small optional vocabulary already accepted by the parser:
`evidence`, `extends`, `contrasts`, `implements`, or `navigation`, written as
`[[target]] (relationship)`. A relationship label is descriptive metadata, not
claim verification.

Use a canonical path or full filename stem when a slug is not unique. A
trailing slug is a safe alias only when the current parser resolves it to one
target in the same ingest scope. Do not fuzzy-select, invent, or bulk-add
links. A source rename requires an audit before and after the rename; only an
unambiguous canonical/alias resolution may be reviewed for repair, followed by
the normal refresh and probe sequence.

Raw evidence documents are expected to be leaves by default. Their zero
resolved authored outbound links are an informational classification queue,
not a health failure and not proof that every raw item is intentionally
isolated. Curated `type: note` documents should have at least one supported
resolved relationship when one exists. If source inspection finds no valid
relationship, record `graph_disposition: reviewed-no-link` or
`graph_disposition: standalone` in the note's frontmatter; never add a
fabricated edge to satisfy a metric. The audit reports these valid dispositions
as reviewed/informational rather than actionable zero-outbound defects.

## Optional Source Metadata

Captured material may include additional provenance fields when they are available. These fields are optional and should not block ingest:

```yaml
author: ["Name or [[wikilink]]"]
published: "YYYY-MM-DD"
created: "YYYY-MM-DD"
modified: "YYYY-MM-DD"
retrieved_at: "YYYY-MM-DD"
source_type: web-clip | pdf | document | spreadsheet | csv | image | audio | video | manual
description: "Source-provided summary, subject, or excerpt"
keywords: ["source-provided", "keywords"]
```

Optional metadata is advisory. Preserve it when present, but do not treat PDF/document metadata as verified publication facts without source review.

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
- **README Metadata Extension:** `project_state`, `goal`, `next_action`, and `updated` drive the local ignored `30_projects/index.md` via `bin/sync-project-index`. The public repo keeps `30_projects/index.template.md`. The live `10_knowledge/index.md` is also local/private; the public repo keeps `10_knowledge/index.template.md`.

### 5. Decision
- **Type:** `decision`
- **Location:** `DECISIONS.md` or local project decisions.
- **Rule:** Captures accepted trade-offs. Not for draft brainstorming.
