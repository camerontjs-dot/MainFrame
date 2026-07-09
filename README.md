# MainFrame

MainFrame is a markdown-first workspace that organizes knowledge by **information lifecycle** before topic. Capture, durable notes, live state, and project work need different update rules — MainFrame keeps those rules explicit in the file tree so agents and humans can work safely in the same place.

The source of truth is the directory layout. Scripts can route, check, or summarize parts of the tree. They do not replace notes, raw evidence, decisions, or project records.

> **Stage 1 public surface.** This release is the bare operating system: lifecycle folders, contracts, deterministic ingest and session tooling, and agent skills for knowledge work. A paired local retrieval engine (**MindGraph**) and a pixel agent control room ship in later stages. They are not required to use Stage 1.

## Lifecycle model

| Path | Purpose | Update rule |
| --- | --- | --- |
| `00_inbox/` | Fast capture for unsorted material | Temporary intake; promote through `01_ingest/` |
| `01_ingest/` | Normalization, validation, routing, rejects | Prefer deterministic workflows; keep routing logs local |
| `10_knowledge/` | Durable notes and raw evidence references | Standard metadata; live index stays local; extracted text points back to sources |
| `20_live/` | Volatile operational state and dashboards | Append-only timelines or explicit snapshots — do not silently overwrite |
| `30_projects/` | Active work with outcomes and workbenches | Project `README.md` metadata drives a generated local index; the public repo tracks only templates |
| `90_archive/` | Preserved material off the active path | Archive without deleting evidence or rewriting history |

Local `AGENTS.md` files may add stricter rules inside a lifecycle folder.

## Metadata

Finalized markdown notes use the schema in [`.context/primitives.md`](.context/primitives.md):

```yaml
---
title: "Name of the file"
domain: "Broad area"
type: raw | note | live | project | decision
status: queued | active | stable | archived
source: "URL or path to raw evidence"
tags: ["example"]
---
```

Project records extend that schema with `project_state`, `goal`, `next_action`, and `updated`. See [`30_projects/AGENTS.md`](30_projects/AGENTS.md).

Claim discipline is defined in [`EPISTEMIC_STANCE.md`](EPISTEMIC_STANCE.md). Framework-level architecture notes live in [`docs/architecture.md`](docs/architecture.md).

## Deterministic core scripts

| Script | What it does |
| --- | --- |
| `bin/ingest-minion` | Routes inbox and queue material through the v1 ingest path (dry-run by default) |
| `bin/prep-ingest` | Prepares captures for the ingest lane |
| `bin/ingest-status` | Reports lane ages and backlog composition |
| `bin/session-open` / `bin/session-close` | Fixed session start and end checks |
| `bin/sync-project-index` | Generates or checks the local project index from README metadata |
| `bin/extract-knowledge` | Scaffolds a knowledge note from a project when promotion is ready |
| `bin/workflow-event` / `bin/workflow-report` | Redacted local workflow telemetry append and summary |
| `bin/fetch-source-text` | Best-effort open-access full text into `type: raw` stubs |
| `bin/task-packet` | Validates reviewed local-agent task packets |

Ingest workflow: [`.context/workflows/ingest-minion.md`](.context/workflows/ingest-minion.md).

## Safe operating rules

1. **Preserve provenance.** Raw sources are evidence. Extracted text is a working copy.
2. **Do not silently overwrite history.** Block on collisions; append or snapshot instead.
3. **Treat live state as volatile.** Date current-state claims; verify high-risk domains before promotion.
4. **Keep personal and generated state out of git.** Inbox captures, knowledge domains, live telemetry, project contents, local databases, and session state stay ignored. This public tree tracks contracts, scripts, templates, and tests.

## Quick start

```bash
# From a fresh clone
python3 -m unittest discover -s tests -v

# Dry-run ingest (no file moves)
bin/ingest-minion run --dry-run
```

Optional environment:

```bash
export UNPAYWALL_EMAIL=you@example.com   # for bin/fetch-source-text
```

## What this release does not include

- Your private knowledge corpus, live dashboards, or project workbenches
- The **MindGraph** retrieval package (planned Stage 2 reveal)
- The **pixel agent tracker / workstation** (planned Stage 3 reveal)
- Private skill packs, outreach tooling, or market-ops scripts

## Agent contracts

Root agent behavior: [`AGENTS.md`](AGENTS.md). Harness policy summary: [`HARNESS.md`](HARNESS.md). Named subagents under `agents/`. Skills under `.agents/skills/`. Operator workflows under `.context/workflows/`.

## License

MIT — see [`LICENSE`](LICENSE).
