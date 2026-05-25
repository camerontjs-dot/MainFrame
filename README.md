# Mainframe

Mainframe is the markdown-first workspace I use to organize knowledge by information lifecycle before topic. It solves a practical recall problem: quick captures, durable notes, live state, and project work need different update rules, but they still need to stay easy to find.

The source of truth is the file tree. Scripts and MindGraph can index, check, or summarize parts of the tree, but they do not replace the notes, raw sources, decisions, or project records stored here.

## Lifecycle model

| Path | Purpose | Update rule |
| --- | --- | --- |
| `00_inbox/` | Fast capture zone for unsorted material. | Treat as temporary intake. Move through `01_ingest/` before promoting. |
| `01_ingest/` | Normalization, validation, routing, and rejected items. | Use deterministic workflows where possible. Preserve routing logs locally. |
| `10_knowledge/` | Durable, slower-moving notes and raw evidence references. | Notes need standard metadata. Extracted text must point back to source evidence. |
| `20_live/` | Volatile state such as finance, job hunt, and active research. | Use append-only timelines or explicit snapshots. Do not silently overwrite current state. |
| `30_projects/` | Active work with outcomes and next actions. | Project `README.md` metadata drives `30_projects/index.md`. |
| `90_archive/` | Preserved material that should not clutter active navigation. | Archive without deleting raw evidence or rewriting history. |

Local `AGENTS.md` files may add stricter rules inside a lifecycle folder. The main examples today are `20_live/AGENTS.md` and `30_projects/AGENTS.md`.

## Metadata

Finalized markdown notes use the schema defined in [.context/primitives.md](.context/primitives.md):

```yaml
---
title: "Name of the file"
domain: "Broad area"
type: raw | note | live | project | decision
status: queued | active | stable | archived
source: "URL or local path to raw evidence"
tags: ["sensitivity", "etc"]
---
```

Project records extend that schema with `project_state`, `goal`, `next_action`, and `updated`. See `30_projects/AGENTS.md` for the exact project README shape.

Architecture and workflow changes belong in [DECISIONS.md](DECISIONS.md). Claim discipline is defined in [EPISTEMIC_STANCE.md](EPISTEMIC_STANCE.md).

## Deterministic scripts

| Script | What it does |
| --- | --- |
| `bin/ingest-minion` | Routes files from `00_inbox/` and `01_ingest/queue/` through the v1 ingest path. Defaults to dry-run behavior unless `--apply` is passed. |
| `bin/sync-project-index` | Generates or checks `30_projects/index.md` from project README metadata. |
| `bin/mindgraph-refresh` | Refreshes the external MindGraph database from `10_knowledge/`. Supports `--dry-run`. |
| `bin/workflow-report` | Summarizes redacted local workflow telemetry from ignored `20_live/workflow-metrics/events/`. |

The ingest Minion workflow is documented in [.context/workflows/ingest-minion.md](.context/workflows/ingest-minion.md). ADR-007 in [DECISIONS.md](DECISIONS.md) records why v1 is manual, dry-run-first, and limited to deterministic routing.

## Safe operating rules

Preserve provenance. Raw sources are evidence. Extracted text and generated stubs are searchable working copies, not replacements for the original material.

Do not silently overwrite history. If a destination already exists, the deterministic ingest path blocks instead of replacing it. Project logs, decisions, and live records should append or snapshot.

Treat `20_live/` as volatile. Current-state claims need dates, and high-risk domains need source-backed verification before promotion.

Keep generated and personal state out of the tracked surface. The repo ignores inbox captures, ingest queues, processed knowledge domains, live telemetry, project contents, archive contents, local MCP config, local databases, and `STATE.md`.

## Common workflows

Start an ingest pass with a dry run:

```bash
bin/ingest-minion run --dry-run
```

Apply the planned ingest moves after reviewing the dry run:

```bash
bin/ingest-minion run --apply
```

Route a raw PDF without a convention-named domain after reviewing the generated plan:

```bash
bin/ingest-minion run --dry-run --domain ai-systems
bin/ingest-minion run --apply --domain ai-systems
```

Refresh MindGraph after durable knowledge changes:

```bash
bin/mindgraph-refresh
```

Preview the MindGraph refresh command path:

```bash
bin/mindgraph-refresh --dry-run
```

Query the Mainframe MindGraph database:

```bash
bin/mindgraph query "agentic design patterns"
```

Regenerate the project index after project README metadata changes:

```bash
bin/sync-project-index --write
```

Check that the project index is current:

```bash
bin/sync-project-index --check
```

Review local workflow telemetry:

```bash
bin/workflow-report --days 7
```

Run the ingest Minion unit tests:

```bash
python3 -m unittest tests/test_ingest_minion.py
```

## MindGraph boundary

MindGraph is an external retrieval layer for Mainframe. The operating boundary is recorded in ADR-002 and ADR-005 in [DECISIONS.md](DECISIONS.md).

By default, `bin/mindgraph-refresh` ingests `10_knowledge/` into `~/.mindgraph/mainframe.sqlite`. The wrapper `bin/mindgraph` resolves the real MindGraph binary from `MINDGRAPH_BIN`, `git config mainframe.mindgraphBin`, or `PATH`.

Returned chunks are retrieval nominations, not verification. Inspect the underlying note and source evidence before treating a result as true.
