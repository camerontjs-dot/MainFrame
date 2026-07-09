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
---

# Task Packet

## Goal

State the single outcome this task must produce.

## Context and plan references

Name the governing plan, decisions, contracts, and files the implementer must
read. The packet summarizes them but does not replace them.

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
