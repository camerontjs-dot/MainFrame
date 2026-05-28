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

## ADR-008: Session Lifecycle Scripts
**Status**: Accepted
**Date**: 2026-05-27
**Context**: The session-open, session-close, and extract-knowledge workflows are manual checklists in `.context/workflows/`. Their deterministic steps (file existence checks, downstream script invocation, context ordering, scaffold generation) can be scripted without removing judgment from the agent.
**Decision**: Add `bin/session-open`, `bin/session-close`, and `bin/extract-knowledge` as self-contained Python scripts following the existing conventions (check/apply modes, structured result objects, no shared library). The scripts automate only deterministic operations. Narrative judgment (STATE.md writing, DECISIONS.md review, knowledge content) remains explicitly manual.
**Rationale**: Consistent with ADR-007's approach of scripting deterministic work while keeping judgment manual. Session boundaries are the highest-frequency workflows and the most prone to step omission.

## ADR-009: Two-Pass Ingest with Agent-Driven Middle
**Status**: Accepted
**Date**: 2026-05-27
**Context**: The v1 ingest minion (ADR-007) is a strict file sorter — files in `00_inbox/` without complete YAML frontmatter are rejected to `01_ingest/rejected/`. This defeats `00_inbox/` as a fast capture zone. The original second-brain planning (`/Users/admin/Desktop/Workbench planning/second-brain-redesign/raw-processing.md`) defined a `new → skimmed → routed → extracted → synthesized` lifecycle with judgment-driven enrichment between deterministic passes; only the deterministic pass exists today.
**Decision**: Extend the ingest pipeline to a two-pass architecture:
1. **Minion pass 1 (deterministic):** Normalize frontmatter (instead of rejecting), extract `[[wikilinks]]` from body into a `links:` array, stage to `01_ingest/ready/` with `status: skimmed`.
2. **Ingest-agent (subagent, judgment):** Reads files in `ready/`, classifies (domain/type/tags), proposes connections (using `links:` + MindGraph when operational), discusses with user, enriches, renames to convention, sets `status: extracted`.
3. **`bin/prep-ingest` (deterministic):** Validates extracted files and moves to `01_ingest/queue/`.
4. **Minion pass 2 (deterministic):** Existing strict routing from `queue/ → 10_knowledge/<domain>/`. Unchanged from ADR-007.

Extends the status enum in `.context/primitives.md` with: `skimmed`, `routed`, `extracted`, `synthesized`, `parked`.
**Rationale**: Applies the "Minions vs Sub-agents" routing rule from `/Users/admin/Desktop/Workbench planning/second-brain-redesign/gbrain-adaptations.md` — deterministic work in scripts, judgment work in sub-agents. Preserves the v1 quality gate at `queue/ → 10_knowledge/` (the strict ADR-007 routing is unchanged) while loosening the entry point so `00_inbox/` can be a real capture zone. Deterministic link extraction (also from gbrain-adaptations §2) means connection-finding doesn't depend on MindGraph being operational.

## ADR-010: Cross-Tool Agent Layout (`.agents/` and `agents/`)
**Status**: Accepted
**Date**: 2026-05-27
**Context**: The empty `live-asset/Mainframe/skills/` folder doesn't follow a clear convention. Mainframe is used across multiple agent tools (Claude, Codex, occasionally Google), so a Claude-Code-native layout (`.claude/agents/`, `.claude/skills/`) would not be portable. We need a layout that's recognized across agent tooling.
**Decision**: Adopt the cross-tool convention:
- **`.agents/skills/`** — reusable skill definitions (dotfile because skills are agent configuration, not user-facing content).
- **`agents/`** — top-level named subagent definitions (visible at root because subagents are first-class collaborators).

Claude-Code-specific settings continue to live in `.claude/`. The empty `skills/` folder is deleted and replaced by `.agents/skills/`. Root `AGENTS.md` is updated to reference the new layout.
**Rationale**: `.agents/` and `agents/` are recognized across Claude, Codex, and other agent runtimes. Keeping multi-tool config under `.agents/` and Claude-specific config under `.claude/` cleanly separates portable agent contracts from tool-specific settings. The `agents/` folder being visible signals that subagents are part of the system's public contract, not internal config.
