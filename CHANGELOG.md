# Changelog

## Unreleased

### Added

- `tests/test_ingest_minion.py::test_wikilinks_inside_code_spans_are_ignored`: covers the Phase 5 dogfood edge case where wikilinks that appear inside fenced code blocks or inline code spans (i.e. discussion of the syntax, not real connections) are excluded from the `links:` array.
- `bin/prep-ingest` (backed by [01_ingest/prep_ingest.py](01_ingest/prep_ingest.py)): deterministic `01_ingest/ready/` → `01_ingest/queue/` gate for the ADR-009 two-pass design. Validates strict frontmatter, `status: "extracted"`, canonical filename (`YYYY-MM-DD__domain__type__slug.md`), domain in the `10_knowledge/` whitelist, and no queue collision before promoting a file. Same dry-run-first CLI shape as `bin/ingest-minion`.
- `tests/test_prep_ingest.py` coverage for promotion, dry-run, partial frontmatter, non-extracted status, malformed filenames, filename/frontmatter domain mismatch, unknown domain, destination collision, and empty-directory cases.
- Agent-ingest v2 pass-1 normalization in [01_ingest/minion.py](01_ingest/minion.py): missing/partial frontmatter is filled with deterministic defaults and routed to `01_ingest/ready/` with `status: "skimmed"` instead of being rejected. Strict-valid files continue to stage to `01_ingest/queue/` for pass-2 routing. Body `[[wikilinks]]` are extracted into a `links:` array during normalization.
- New `normalize` event kind for files routed to `01_ingest/ready/`.
- `tests/test_ingest_minion.py` coverage for inbox normalization (no frontmatter, partial frontmatter, wikilink extraction) and `status: extracted` direct-to-queue routing.
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

- [01_ingest/minion.py](01_ingest/minion.py): `extract_wikilinks()` now strips fenced code blocks and inline code spans before scanning for `[[wikilink]]` targets, so notes that *discuss* the wikilink syntax don't pollute the `links:` array with example targets. Discovered while dogfooding Phase 5 against a real captured note.
- [agents/ingest-agent.md](agents/ingest-agent.md): step 8 (hand-off) now references the real `bin/prep-ingest run --dry-run` / `--apply` commands instead of placeholder wording.
- [01_ingest/minion.py](01_ingest/minion.py): split frontmatter parsing into permissive `read_frontmatter()` + strict `validate_strict()`; added `extract_wikilinks()`, `render_frontmatter()`, and `normalize_metadata()`. Status enum extended to include the v2 lifecycle values (`skimmed`, `routed`, `extracted`, `synthesized`, `parked`) per ADR-009.
- [.context/workflows/ingest-minion.md](.context/workflows/ingest-minion.md): documents the now-current two-pass behavior; the "Pending changes (ADR-009)" preamble is removed.
- Root [AGENTS.md](AGENTS.md): updated centralized-skills reference from `/skills` to `.agents/skills/`; added `agents/` line for subagent definitions per ADR-010.
- Removed empty `skills/` folder; replaced by `.agents/skills/` per ADR-010.
- Replaced stale legacy naming in `20_live/AGENTS.md` and `.context/workflows/session-open.md` so guidance refers to the current Mainframe primitives.
- Reframed the README MindGraph section to make the paired-but-separate-repo relationship with MindGraph explicit.

### Security

- Hardened `bin/workflow-event` command-head redaction. Leading shell env-var assignments (e.g. `FOO=/tmp/bar cmd`) are skipped and path-shaped heads collapse to `<path>`, so filesystem basenames no longer leak into telemetry. Covered by new `tests/test_workflow_event.py`.

### Notes

- The ingest Minion is manual and deterministic in v1. It does not process `20_live/` state or `30_projects/` records.
- MindGraph remains a complementary retrieval layer. Raw evidence and markdown files in the lifecycle tree remain the source of truth.
