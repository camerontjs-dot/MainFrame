# Mainframe

Mainframe is the markdown-first workspace I use to organize knowledge by information lifecycle before topic. It solves a practical recall problem: quick captures, durable notes, live state, and project work need different update rules, but they still need to stay easy to find.

The source of truth is the file tree. Scripts and MindGraph can index, check, or summarize parts of the tree, but they do not replace the notes, raw sources, decisions, or project records stored here.

## Lifecycle model

| Path | Purpose | Update rule |
| --- | --- | --- |
| `00_inbox/` | Fast capture zone for unsorted material. | Treat as temporary intake. Move through `01_ingest/` before promoting. |
| `01_ingest/` | Normalization, validation, routing, and rejected items. | Use deterministic workflows where possible. Preserve routing logs locally. |
| `10_knowledge/` | Durable, slower-moving notes and raw evidence references. | Notes need standard metadata. The live `index.md` is local/private; the repo tracks `index.template.md`. Extracted text must point back to source evidence. |
| `20_live/` | Volatile personal and project state, and active research. | Use append-only timelines or explicit snapshots. Do not silently overwrite current state. |
| `30_projects/` | Active work with outcomes and local project workbenches. | Project `README.md` metadata drives the ignored local `30_projects/index.md`; the public repo tracks `30_projects/index.template.md`. |
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

Architecture and workflow changes belong in [DECISIONS.md](DECISIONS.md). Claim discipline is defined in [EPISTEMIC_STANCE.md](EPISTEMIC_STANCE.md). Operational procedure: [.context/workflows/epistemic-standard.md](.context/workflows/epistemic-standard.md) (ADR-029). Canonical sources live locally in `10_knowledge/knowledge-systems/epistemics/`.

## Deterministic scripts

| Script | What it does |
| --- | --- |
| `bin/ingest-minion` | Routes files from `00_inbox/` and `01_ingest/queue/` through the v1 ingest path. Defaults to dry-run behavior unless `--apply` is passed. |
| `bin/fetch-source-text` | Pulls OA full text (or best excerpt) into `type: raw` stubs under `10_knowledge/`. Uses Europe PMC, direct PDF/HTML, and Unpaywall when `UNPAYWALL_EMAIL` is set. |
| `bin/post-route-enrich` | Post-ingest step: `fetch-source-text --apply` for a domain or file, then `mindgraph-refresh`. Companion to `.context/workflows/ingest-minion.md` step 8. |
| `bin/second-brain-batch` | Registers a rolling migration drop as an immutable batch with a manifest, byte-preserving `source-files/` snapshot, duplicate report, and append-only `disposition-ledger.csv`. |
| `bin/sync-project-index` | Generates or checks the ignored local `30_projects/index.md` from project README metadata. `--check` also enforces evidence-based project states: `active` needs activity within 14 days (file mtimes + nested-repo commits), valid state vocabulary, reentry pointers, dual-pool WIP (5 product seats + eval seats, total ceiling 10; ADR-041 / ADR-046). |
| `bin/mindgraph-refresh` | Refreshes the external durable-knowledge MindGraph database from `10_knowledge/`. Supports `--dry-run`. |
| `bin/mindgraph-refresh-projects` | Refreshes the projects MindGraph DB. Lean default (no bulk outputs); `--deep` adds outputs. Supports `--dry-run`, `--full`, `--apply`. |
| `bin/mindgraph-projects-apply` | **Recommended** staged apply (ADR-045): `--plan` → `--stage` → `--promote --receipt …`. Optional `--deep`. See HARNESS for when to re-stage. |
| `bin/workflow-report` | Summarizes redacted local workflow telemetry and reports coverage limits, overall and per client. Supports `--json`. |
| `bin/ingest-status` | Reports ingest lane ages and splits inbox backlog into batch-registered migration files vs organic captures. Supports `--json`. |
| `bin/audit-sweep` | Deterministic discovery of `needs-audit` tagged items (and recent routed material) in `10_knowledge/`. Writes a manifest into `20_live/epistemic-audit/pending-review/` and hands off to the epistemic auditor (`bin/epistemic`). Supports `--dry-run`, `--apply`, `--json`, `--subset`. Companion workflow: `.context/workflows/audit-sweep.md`. |
| `bin/session-open` | Loads session context files in a fixed order. Auto-detects active project from `STATE.md`; supports `--project`, `--print-contents`, and `--json`. |
| `bin/session-close` | Runs end-of-session checks and triggers downstream scripts. `--check` reports what needs doing; `--apply` runs auto actions; `--checkpoint` takes a fast evidence snapshot (wired to the PreCompact hook); `--feed` appends results to `20_live/workstation/session-close-feed.jsonl` for the workstation tracker (ADR-040). |
| `bin/extract-knowledge` | Validates prerequisites and scaffolds a knowledge note from a project. `--check` validates; `--write` creates the scaffold. |
| `bin/eval-schedule` | Runs scheduled MainFrame eval suites (`daily` / `weekly` / `monthly`), writes `20_live/eval-registry/schedule-runs.jsonl`, installs macOS launchd agents, and exposes `check` for staleness. Surfaced in `session-open` / `session-close`. See `20_live/eval-registry/OPERATOR.md` and `.context/workflows/eval-schedule.md`. |
| `bin/eval-registry` | Harvests metric extracts from eval-profile project outputs into `20_live/eval-registry/`. |

The ingest Minion workflow is documented in [.context/workflows/ingest-minion.md](.context/workflows/ingest-minion.md). ADR-007 in [DECISIONS.md](DECISIONS.md) records why v1 is manual, dry-run-first, and limited to deterministic routing. ADR-008 records the session lifecycle scripts boundary.
ADR-011 records the suggestion-first inbox rule: first-pass intake should guide the ingest-agent instead of dead-lettering recoverable captures, while strict rejects remain part of the `queue/ → 10_knowledge/` gate.
ADR-019 adds tiered batch ingest for registered migration backlogs: files matching a named rule in [.context/routing-policy.md](.context/routing-policy.md) route in bulk behind one review table, exceptions queue for the operator, and routed clips are tagged `needs-audit` for continuous post-route auditing.

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

Warnings in the dry run are suggestions for the ingest-agent. They do not move files to `01_ingest/rejected/` during pass 1.

Apply the planned ingest moves after reviewing the dry run:

```bash
bin/ingest-minion run --apply
```

Route a raw PDF without a convention-named domain only after the destination domain exists:

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

Register a second-brain migration drop without mutating the source inbox:

```bash
bin/second-brain-batch \
  --batch-id YYYY-MM-DD-NNN \
  --source 00_inbox \
  --source-label "old second-brain export"
```

Regenerate the local project index after project README metadata changes:

```bash
bin/sync-project-index --write
```

Check that the local project index is current:

```bash
bin/sync-project-index --check
```

Review local workflow telemetry:

```bash
bin/workflow-report --days 7
```

Check ingest lane ages and migration-backlog composition:

```bash
bin/ingest-status
```

Run a process evaluation with a baseline, representative outcome samples, and
a post-change rerun:

See [.context/workflows/process-evaluation.md](.context/workflows/process-evaluation.md).

The end-to-end operator walkthrough for a working session is
[.context/workflows/session-guide.md](.context/workflows/session-guide.md).

**Client configuration note (Fix 5):** Hook telemetry for Claude, Codex, Antigravity, and Aider is currently in per-client dotfiles (.claude/, .codex/, .antigravity/). A future unification generator could centralize definitions (see .context/ or scripts/) to reduce maintenance while keeping `bin/workflow-event` as the single source for redacted events.

Load session context at the start of a work session:

```bash
bin/session-open
```

Load context with file contents for a specific project:

```bash
bin/session-open --project my-project --print-contents
```

Check what needs doing before closing a session:

```bash
bin/session-close --check
```

Run end-of-session auto actions (index sync, MindGraph refresh, telemetry):

```bash
bin/session-close --apply
```

Validate prerequisites for extracting knowledge from a project:

```bash
bin/extract-knowledge --project my-project --domain ai-systems --title "Lessons from My Project" --check
```

Scaffold the knowledge note after validation passes:

```bash
bin/extract-knowledge --project my-project --domain ai-systems --title "Lessons from My Project" --write
```

Run the full test suite:

```bash
python3 -m unittest discover -s tests
```

Review navigation/synthesis signals and generate handoff draft:

```bash
bin/knowledge-report --domain agents
bin/session-close --apply   # writes 20_live/last-handoff-draft.md (ignored)
bin/audit-sweep --dry-run --subset regulated-systems
```

## MindGraph boundary

Mainframe is the markdown-first workspace. MindGraph is the complementary retrieval engine. The engine source is embedded directly at the root under `mindgraph/`, with `30_projects/mindgraph/` maintained as an upgrade sandbox and `30_projects/mindgraph-eval/` kept separate for retrieval-quality measurement. The operating boundary is recorded in ADR-031 and other decisions in [DECISIONS.md](DECISIONS.md).

By default, `bin/mindgraph-refresh` ingests `10_knowledge/` into `~/.mindgraph/mainframe.sqlite` with durable-knowledge provenance. `bin/mindgraph-refresh-projects` ingests an optional ignored local manifest (`30_projects/mindgraph-projects.json`) or its built-in curated project list into `~/.mindgraph/mainframe-projects.sqlite` with project-status provenance. The wrapper `bin/mindgraph` resolves the real MindGraph binary from `MINDGRAPH_BIN`, the root venv at `mindgraph/.venv/bin/mindgraph`, `git config mainframe.mindgraphBin`, or `PATH`.

The MindGraph Query Station is a MainFrame interpreter over the separate knowledge and project databases, not a merged graph. It lives in the `workstation/` component, which is not part of this public skeleton. Its v1 modes are `knowledge`, `projects`, and grouped `federated`; for unfinished station modes, run explicit CLI queries against both DBs and keep results grouped by lifecycle/trust zone.

Root MindGraph also provides an opt-in loopback Streamable HTTP daemon and an
official-SDK stdio proxy. It opens both indexes read-only but requires one
explicit scope per call and returns the scope trust profile; it never blends
the stores. The default MCP example remains the single-database stdio path.

Returned chunks are retrieval nominations, not verification. Inspect the underlying note and source evidence before treating a result as true.
