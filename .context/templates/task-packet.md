---
packet_version: 1
task_id: "replace-with-task-id"
project_slug: "replace-with-project-slug"
title: "Replace with task title"
status: "draft"
task_kind: "code"
agent_profile: "local-qwen25-coder-14b"
workdir: "workbench"
timeout_seconds: 900
editable_files: ["src/example.py"]
create_files: ["tests/test_example.py"]
read_only_files: ["AGENTS.md", "plans/phases/current-phase.md"]
verification_commands: ["python3 -m unittest -q"]
mindgraph_mode: "off"
knowledge_queries: []
# Optional routing (see .context/harness-routing.json):
# task_category: "mechanical-edit"
# executor: "local"
# harness_recommendation: "H1-packet"
# allow_fusion_plan: false
# needs_deliberation: false
#
# When planning depends on vault/project context:
# mindgraph_mode: "curated"
# knowledge_queries: ["exact knowledge query string"]
# and fill ## MindGraph Query Pass below (see .context/templates/mindgraph-query-pass.md)
---

# Task Packet

## Goal

State the single outcome this task must produce.

## Context and plan references

Name the governing plan, decisions, contracts, and files the implementer must
read. The packet summarizes them but does not replace them.

Before writing a `ready` packet for non-trivial work, run dual MindGraph queries
(or set `mindgraph_mode: "curated"`) and record a Query Pass — either in the
optional section below or linked from a plan. See
`.context/templates/mindgraph-query-pass.md`.

## Required implementation

Describe the exact behavioral and file-level change. Resolve design choices
before marking the packet ready.

## Non-negotiable boundaries

List scope exclusions, compatibility requirements, and behaviors that must not
change.

## Acceptance criteria

List observable conditions that external verification can establish.

## Stop conditions

Name discoveries that require escalation rather than improvisation.

## Expected handoff

Require a concise summary of changed files, verification not claimed as run by
the agent, blockers, and remaining risks.

## MindGraph Query Pass

Optional for `mindgraph_mode: "off"`. **Fill when `mindgraph_mode: "curated"`**
(or when the packet author used dual-index planning). Do not leave REPLACE
placeholders in a ready curated packet.

```text
intent: REPLACE — decision this retrieval supports
doctor: REPLACE — overall line from `bin/mindgraph doctor`
knowledge_query: REPLACE
projects_query: REPLACE

knowledge (durable_knowledge):
- path: REPLACE
  reason: REPLACE

projects (project_status):
- path: REPLACE
  reason: REPLACE

weak_or_excluded:
- REPLACE or none

source_inspection_required:
- REPLACE or none

do_not_merge_without_trust_labels: true
```
