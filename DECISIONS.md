# Architecture Decision Records (ADRs)

This file captures meaningful project choices, especially trade-offs affecting reproducibility, scope, evidence quality, or system behavior.

## ADR-001: Centralized vs Local Agent Instructions
**Status**: Accepted
**Date**: 2026-05-20
**Context**: Should each lifecycle folder contain its own `AGENTS.md` file, or should all instructions be centralized?
**Decision**: We will enforce a global `AGENTS.md` at the root, and keep repeatable workflows in `skills/`. We will ONLY place local `AGENTS.md` files in subdirectories that have special defensive rules or processes (e.g. `20_live`).
**Rationale**: Prevents agent context bloat and repetitive instructions while still allowing for localized safety rules.

## ADR-002: MindGraph Integration Strategy
**Status**: Accepted
**Date**: 2026-05-20
**Context**: Should the MindGraph GraphRAG system be deeply coupled into the Mainframe ingest pipeline?
**Decision**: MindGraph will remain a separate project and will be wired in as a complementary RAG feature. The Mainframe will have its own ingest pipeline, but will use the same tracking/metadata schema so MindGraph can index it effectively.
**Rationale**: Keeps the Mainframe ingestion simple and markdown-first, separating the graph database concerns from the file organization concerns.

## ADR-003: Automation Tooling for Ingest
**Status**: Superseded by ADR-007
**Date**: 2026-05-20
**Context**: The `01_ingest` pipeline requires metadata validation and graph extraction. Relying entirely on LLMs for this is token-heavy.
**Decision**: We will plan to create lightweight CLI/bash scripts ("Minions") in a future session to handle deterministic routing.
**Rationale**: Saves tokens and increases reliability for repetitive, rule-based operations.

## ADR-004: Project Lifecycle Automation
**Status**: Accepted
**Date**: 2026-05-22
**Context**: The `30_projects` area needs low-friction status recall without requiring agents to copy the same status into multiple files by hand.
**Decision**: Project folders will use `README.md` frontmatter as the single machine-readable status source. The project README extends the standard metadata schema with `project_state`, `goal`, `next_action`, and `updated`. The `bin/sync-project-index` script generates `30_projects/index.md` from those fields, and Git pre-commit checks that the index is current.
**Rationale**: Keeps navigation accurate while preserving one editable project status surface. The generated index prevents manual drift.

## ADR-005: Mainframe MindGraph Operating Boundary
**Status**: Accepted
**Date**: 2026-05-22
**Context**: The MindGraph MCP wrapper is now complete in the portfolio asset, but Mainframe still needs a local integration policy.
**Decision**: Mainframe will use MindGraph as an external complementary retrieval layer through `bin/mindgraph`, `bin/mindgraph-refresh`, and the optional `.mcp.json.example`. The default database is `~/.mindgraph/mainframe.sqlite`. The default ingest scope is `10_knowledge/`, not the vault root.
**Rationale**: `10_knowledge/` keeps search focused on durable notes and avoids adding operating contracts, workflow files, and empty index stubs to retrieval results. The database stays outside the repo so Git history stays clean.

## ADR-006: Workflow Telemetry Split
**Status**: Accepted
**Date**: 2026-05-22
**Context**: We want to improve workflow efficiency over time, including tool-call patterns, without confusing Git hooks with AI-client hooks or leaking sensitive content into logs.
**Decision**: Git hooks enforce deterministic repository hygiene: project index checks before commit and nonblocking MindGraph refresh after commit. Tool-call telemetry lives in Claude Code hook configuration at `.claude/settings.json`, which calls `bin/workflow-event` for session and tool lifecycle events. Telemetry is metadata-only, append-only, local, and ignored under `20_live/workflow-metrics/`.
**Rationale**: Git hooks can see repository transitions but not AI tool-call intent or duration. Claude Code hooks can see tool lifecycle metadata, including post-tool timing, so they are the right layer for workflow measurement. Keeping logs redacted and ignored respects the volatility constraints of `20_live`.

## ADR-007: Deterministic Ingest Minion V1
**Status**: Accepted
**Date**: 2026-05-23
**Context**: Files captured in `00_inbox/` need deterministic staging, metadata validation, routing, and raw-evidence stub generation without spending LLM tokens on repeatable work.
**Decision**: Mainframe will use `bin/ingest-minion` as a manual, dry-run-first CLI for the v1 ingest path. The script stages files through `01_ingest/queue/`, validates Markdown against the approved metadata schema, routes `note` and `raw` Markdown into existing `10_knowledge/<domain>/` directories, and converts convention-named PDFs into immutable raw files plus MindGraph-compatible Markdown stubs.
**Rationale**: A manual CLI keeps ingest behavior inspectable and low-risk while preserving provenance. Existing knowledge-domain directories act as the whitelist, and MindGraph refresh remains a separate workflow.
