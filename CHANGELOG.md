# Changelog

## Unreleased

### Added

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

- Replaced stale legacy naming in `20_live/AGENTS.md` and `.context/workflows/session-open.md` so guidance refers to the current Mainframe primitives.
- Reframed the README MindGraph section to make the paired-but-separate-repo relationship with MindGraph explicit.

### Security

- Hardened `bin/workflow-event` command-head redaction. Leading shell env-var assignments (e.g. `FOO=/tmp/bar cmd`) are skipped and path-shaped heads collapse to `<path>`, so filesystem basenames no longer leak into telemetry. Covered by new `tests/test_workflow_event.py`.

### Notes

- The ingest Minion is manual and deterministic in v1. It does not process `20_live/` state or `30_projects/` records.
- MindGraph remains a complementary retrieval layer. Raw evidence and markdown files in the lifecycle tree remain the source of truth.
