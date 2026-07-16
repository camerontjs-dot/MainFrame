# 30_projects - Project Lifecycle Rules

This directory contains active work with concrete outcomes. Project folders may include the full local workbench for that outcome, but the outer MainFrame repo treats project contents as private ignored state.

## Project States (ADR-041: evidence-based, WIP-capped)

`bin/sync-project-index --check` enforces these semantics and fails loudly
when a state contradicts observed activity (file mtimes + nested-repo
commits, bounded scan — the same derivation `bin/session-close --checkpoint`
uses). Self-reported `updated:` is display metadata only; activity truth
comes from evidence.

- `active`: Work is moving now. Requires activity evidence within the last
  14 days **and** a `next_action`. **WIP cap: at most 5 projects may be
  `active`.** Activating a sixth means pausing one first — visibly.
- `paused`: Deliberately shelved; the healthy default for real-but-not-now
  work. Requires a `next_action` reentry pointer. No evidence requirement.
- `planned`: Registered but not started; name the activation gate in
  `next_action`.
- `blocked`: Waiting on an external dependency or unresolved decision.
- `suspended`: Indefinite hold, heavier than `paused` (whole system parked,
  e.g. epistemic-research-system).
- `shipped`: The outcome is complete enough to preserve, but may still
  receive maintenance.
- `trashed`: The project should leave active navigation and move to
  `90_archive/` (use the archive-project workflow).

Any other state string is a checker error.

High-churn private projects may carry a **nested local git repo** at the
project root (ADR-042). The outer MainFrame repo ignores `30_projects/*`, so
nothing conflicts, and nested commits become the project's activity evidence.
Local-only — no remotes by default; any future remote must be private and pass
a leak-detection review first.

## Required README Metadata
Each project folder must have a `README.md` with YAML frontmatter:

```yaml
---
title: "Project name"
domain: "Broad area"
type: "project"
status: "active"
project_state: "active"
goal: "Outcome this project is meant to produce"
next_action: "Single next step"
updated: "YYYY-MM-DD"
source: "local"
tags: []
---
```

## Workbench Layout
Project folders contain both coordination records and the working project itself. The four coordination entries are required for tracked outcomes; lighter experiments may start with fewer (see create-project workflow for light mode + graduation). The rest exist as needed:

```text
30_projects/<slug>/
  README.md        # required — frontmatter above
  log.md           # required for full projects — append-only work log...
  decisions.md     # required for full projects
  plans/           # required for full projects
    ...
  raw-materials/   # optional
  outputs/         # optional
  workbench/       # optional — nested repo...
```

**Synthesis & extraction (Fix 3):** After meaningful work, use `bin/extract-knowledge --project <slug> --domain <...> --write` (or the new audit-sweep synthesis signals) to push reusable lessons into `10_knowledge/`. Do not leave durable knowledge trapped in project workbenches.

**Craft / trial-and-error research:** Use `.context/workflows/craft-research-loop.md` and `bin/craft-research-loop` for product bake-offs and stack trials (image lab, integration prototypes). Close every trial with keep|kill|iterate + proof index. Do **not** put craft smokes on `last-eval-action.md` unless promoted via experiment-loop.

The `workbench/` directory may be a nested Git repository, a local source tree, or a collection of drafts and artifacts. A workbench may keep its own internal records (STATUS, DECISIONS, ADRs); the project-level files above stay the coordination surface and point into the workbench rather than duplicating it. Keep reusable lessons in `10_knowledge/` only after an explicit extraction step.

`30_projects/index.md` is a generated local index and is ignored by Git because it can list private projects. The public repo keeps `30_projects/index.template.md` to document the shape without exposing the live project inventory.

## Planning Standard

All planning documents live in `plans/`. Flat plan files are fine for small or single-track work. Phased work uses `plans/phases/phase-<n>-<slug>.md`, one file per phase, following this template:

```text
# Phase <N> — <Title>

Status: planned | active | complete
Started: YYYY-MM-DD or —
Completed: YYYY-MM-DD or —

## Goal
What the phase produces and why, naming the source of the work
(analysis, finding, decision, or MindGraph query).

## Non-Negotiable Boundaries
Constraints the phase must not cross: contracts, dependencies,
scope exclusions.

## Unit Stance
Unit ordering and rationale. Build in testable units; stop at each
green boundary before the next unit; do not stack untested units.

## Unit Plan

### Unit 1 — <Title>
Scope: one or two lines.

- [ ] Task checkboxes

Green boundary:

- [ ] Unit-specific checks
- [ ] Standard verification chain (see Verification) green

## Verification
The commands run at every unit boundary.

## Tie-Off Review

- [ ] All deliverables present and tested
- [ ] Planning changelog / project log updated
- [ ] Master plan (or README next_action) updated
- [ ] Handoff notes written below
- [ ] Any blocked item is explicit and does not hide behind a green
      phase status

## Handoff Notes
(written at tie-off)
```

Rules:
- The frame is fixed: `Goal` first; `Tie-Off Review` and `Handoff Notes` last. Phase-specific sections (fixture expectations, file maps, impact tables) may be inserted between `Unit Plan` and `Tie-Off Review`.
- Log planning changes in `plans/CHANGELOG.md` when the project keeps one (`YYYY-MM-DD | [scope] | description`, newest first); otherwise in the project `log.md`.
- Completed or historical plans are never rewritten to a newer template. The standard binds new and still-active plans only.
- **MindGraph Querying**: Prior to initializing any new project plan or phase, query both the Knowledge and Projects MindGraph indexes through the MindGraph Query Station when available, or with `bin/mindgraph query` plus `MINDGRAPH_DB_PATH="$HOME/.mindgraph/mainframe-projects.sqlite"` as the CLI equivalent. Document the query strings, durable-knowledge nominations, project-context nominations, weak/excluded hits, and files that still need source inspection in the plan's `Goal` or the project `log.md`.

## Delegation Packet Standard

When a prepared implementation task is delegated to a local agent, store its
reviewed contract at:

```text
30_projects/<slug>/plans/task-packets/<task-id>.md
```

Start from `.context/templates/task-packet.md`. A packet is written or refined
by a frontier model and reviewed by the operator before its status becomes
`ready`. It must resolve scope, implementation choices, acceptance criteria,
external verification, and stop conditions. Run state and outcomes belong in
evaluation receipts, never in the ready packet.

Validate and compile packets with:

```bash
bin/task-packet validate <packet-path>
bin/task-packet validate --require-ready <packet-path>
bin/task-packet compile
```

Only `ready` packets may execute. The compiled
`30_projects/task_packets_manifest.json` is generated local state for runners
and the workstation; the compiler rejects changes to a previously compiled
ready contract. Retire it or create a new task id instead. The Markdown packet
remains the source of truth. See
`.context/workflows/delegate-local-task.md`.

## Local Coder Capabilities & Delegation Limits

Based on empirical runs in the `agent-harness-eval` matrix under the `H1-packet` harness, delegation to local coder agent profiles must adhere to the following routing, scope, and verification boundaries:

### 1. Model Routing Matrix
- **Multi-File Coordination** (up to 4 files): Route **only** to `local-qwen25-coder-14b`. (Qwen3 and Qwen3.5 profiles fail on multi-file changes and are prone to false completion claims).
- **Large Context / Search-Heavy Reference**: Route to `local-qwen3-14b` or `local-qwen35-9b` (Qwen2.5-coder is extremely fragile under large contexts). However, tasks assigned to Qwen3/3.5 **must be restricted to single-file edits**.

### 2. Scope Boundaries
- **Editable Limit**: Maximum of **4 files** for `local-qwen25-coder-14b`, and **1 file** for `local-qwen3-14b` or `local-qwen35-9b`.
- **Commit Restriction**: Local agents are strictly prohibited from creating Git commits. The operator maintains exclusive authority over git tree state and merges.

### 3. Context Limits
- **Read-Only Volume**: For `local-qwen25-coder-14b`, reference context files (`read_only_files`) must be minimal and clean (under 100 lines total).
- **Aider Warning**: Stop and split the task immediately if Aider reports that the estimated context exceeds the model's limit.

### 4. Verification Requirements
- Every packet **must** declare at least one deterministic verification command.
- Runs are accepted only when external verification commands pass with exit code `0`.
- If verification fails, a single fresh-context repair run (`H2-repair` logic) may be performed with the error output and current diff appended.

## Agent Protocol
1. Create projects with the `create-project` workflow.
2. Prior to writing plans or task packets, query both MindGraph databases (Knowledge & Projects) for relevant prior context, patterns, or similar work. Preserve the output as a grouped `MindGraph Query Pass`; do not collapse durable knowledge and project status into one unlabelled summary.
3. Update a project's `README.md`, `log.md`, and `decisions.md` rather than copying status into multiple places.
4. Regenerate the local `30_projects/index.md` with `bin/sync-project-index --write`; do not hand-edit it.
5. When archiving, use the `archive-project` workflow so knowledge extraction and status cleanup happen first.
6. Preserve project history. Move or append; do not silently overwrite logs or decisions.
7. New phase plans follow the Planning Standard above; do not retrofit completed plans.
8. Delegate local-agent implementation only from a reviewed `ready` task packet; keep verification outside the executing agent.
