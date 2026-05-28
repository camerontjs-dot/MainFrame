# Changelog

## Unreleased

### Added

- ADR-009 (Accepted) in [DECISIONS.md](DECISIONS.md): two-pass ingest with agent-driven middle. Extends ADR-007 by adding a sub-agent enrichment step between deterministic minion passes; preserves the strict `queue/ → 10_knowledge/` quality gate.
- ADR-010 (Accepted) in [DECISIONS.md](DECISIONS.md): cross-tool agent layout (`.agents/skills/` for portable skills, `agents/` for subagent definitions). Keeps Claude-Code-specific config under `.claude/`.
- [agents/ingest-agent.md](agents/ingest-agent.md): subagent definition for the ingest enrichment middle pass — role, tools, procedure, guardrails.
- [01_ingest/AGENTS.md](01_ingest/AGENTS.md): defensive constraints for the ingest layer (no auto-routing, no body modification, raw items immutable, no domain guessing, read-only access to durable knowledge).
- [.agents/skills/](.agents/skills/) stubs for the planned ingest skill set: `ingest-source`, `rename-material`, `classify-note`, `extract-metadata`, `create-source-summary`.
- Status lifecycle extension in [.context/primitives.md](.context/primitives.md): added `skimmed`, `routed`, `extracted`, `synthesized`, `parked`; added `links:` field populated by minion link extraction.
- `bin/session-open` for deterministic session context loading in a fixed order with auto-detection of active project from `STATE.md`.
- `bin/session-close` for end-of-session checks and downstream script triggers (`sync-project-index`, `mindgraph-refresh`, `workflow-report`) with `--check`/`--apply` modes.
- `bin/extract-knowledge` for validating prerequisites and scaffolding knowledge notes extracted from projects with correct metadata.
- `unittest` coverage for session-open (14 tests), session-close (13 tests), and extract-knowledge (14 tests).
- ADR-008 in [DECISIONS.md](DECISIONS.md) for the session lifecycle scripts boundary.
- Script sections in workflow docs for `session-open`, `session-close`, and `extract-knowledge`.
- `bin/ingest-minion` for dry-run-first routing from `00_inbox/` and `01_ingest/queue/` into existing `10_knowledge/<domain>/` folders.
- Markdown frontmatter validation against the standard Mainframe metadata keys defined in [.context/primitives.md](.context/primitives.md).
- Raw PDF handling that preserves the PDF under `10_knowledge/<domain>/raw/` and writes a MindGraph-compatible Markdown stub beside it.
- Ingest workflow documentation in [.context/workflows/ingest-minion.md](.context/workflows/ingest-minion.md).
- ADR-007 in [DECISIONS.md](DECISIONS.md) for the deterministic ingest Minion v1 boundary.
- `unittest` coverage for ingest routing guardrails, including dry runs, missing metadata, unknown domains, raw PDF stubs, and destination collisions.
- Public `README.md` covering the lifecycle model, metadata schema, deterministic scripts, safe operating rules, and the MindGraph boundary.
- MIT `LICENSE`.

### Changed

- Root [AGENTS.md](AGENTS.md): updated centralized-skills reference from `/skills` to `.agents/skills/`; added `agents/` line for subagent definitions per ADR-010.
- [.context/workflows/ingest-minion.md](.context/workflows/ingest-minion.md): added "Pending changes (ADR-009)" section describing the v2 normalize-instead-of-reject behavior and link extraction. V1 behavior remains current until ADR-009 ratifies.
- Removed empty `skills/` folder; replaced by `.agents/skills/` per ADR-010.
- Replaced stale legacy naming in `20_live/AGENTS.md` and `.context/workflows/session-open.md` so guidance refers to the current Mainframe primitives.
- Reframed the README MindGraph section to make the paired-but-separate-repo relationship with MindGraph explicit.

### Security

- Hardened `bin/workflow-event` command-head redaction. Leading shell env-var assignments (e.g. `FOO=/tmp/bar cmd`) are skipped and path-shaped heads collapse to `<path>`, so filesystem basenames no longer leak into telemetry. Covered by new `tests/test_workflow_event.py`.

### Notes

- The ingest Minion is manual and deterministic in v1. It does not process `20_live/` state or `30_projects/` records.
- MindGraph remains a complementary retrieval layer. Raw evidence and markdown files in the lifecycle tree remain the source of truth.
