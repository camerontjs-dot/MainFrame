# Changelog

## 2026-07-13 — Process gap P0–P2 implementation

- **G1** Irregularity lifecycle: `bin/eval-registry dispose|list-open-high` + `20_live/eval-registry/irregularity-dispositions.jsonl`; portfolio triage ignores accepted_risk/waived/superseded.
- **G2/G8** Lane preflight emits `next_phase`, `blocker`, `suggested_command`; `bin/research-lane-loop doctor --all-active`.
- **G3** Harvest re-upgrades placeholder scaffolds; `--project` / `--force` flags.
- **G4** `research-lane-loop handoff-project --slug --to <project>`.
- **G5** Craft close `--blocked-on operator` keeps severity info.
- **G6** Operator-gated highs no longer alone force portfolio severity high.
- **G7** skill-eval linter aliases Procedure/Guardrails/Use for; craft + research-lane skills lint PASS.
- **G9–G11, G13** Canary unbuffered; PATH-safe wrappers; structured proof index; freshness watch-only.
- Gap analysis: `30_projects/mainframe-process-eval/outputs/2026-07-13-three-loop-process-gaps.md`.


## Unreleased

### Added

- ADR-043 (Accepted) in [DECISIONS.md](DECISIONS.md): research-lane-loop as the completion unit for portfolio research — one lane × one phase from source-literature through knowledge synthesis. Workflow `.context/workflows/research-lane-loop.md`, skill `.agents/skills/research-lane-loop/SKILL.md`; pointers from HARNESS, knowledge-routing, research-lanes-strategy README/template, source-literature handoff.
- Research-loop hardening (2026-07-13): `bin/lane-intake` P0↔`immediate` aliases + status prefix match; `bin/research-lane-loop` preflight/doctor/audit-indexes (resume class A–D, stale capture-index repair); tests `tests/test_lane_intake.py`, `tests/test_research_lane_loop.py`.
- MindGraph doctor (MH01, 2026-07-13): `bin/mindgraph doctor|status` dual-index diagnostics; query fail-fast on missing `documents_fts`/`vec_chunks`/etc.; workspace stub detection; tests `mindgraph/tests/test_doctor.py`. Archive clarified as lane-close micro-loop (not default research pass step).
- Query Pass templates (2026-07-13): `.context/templates/mindgraph-query-pass.md`; task-packet optional section + validator; create-project / mindgraph-refresh / delegate-local-task wired. C28 research lane archived to `lanes/completed/` after lane-close dogfood.
- Project experiment loop (2026-07-13): `.context/workflows/project-experiment-loop.md` + `bin/project-experiment-loop` (preflight/scaffold/canary/close/triage). MindGraph canaries write `20_live/eval-registry/last-canary-action.md`; weekly eval-schedule runs triage after harvest; session-open surfaces the card. Fresh dogfood run `2026-07-13T145406Z-experiment-loop-canary-*`.
- Portfolio eval action (2026-07-13): `bin/project-experiment-loop portfolio` triages **all** eval-profile projects into `20_live/eval-registry/last-eval-action.md`; registry harvest/check skip non-eval outputs so hygiene is actionable.
- Craft research loop (2026-07-13): `.context/workflows/craft-research-loop.md`, skill, template, `bin/craft-research-loop` (preflight/scaffold/close/triage/promote). Project-local `outputs/LAST_CRAFT_ACTION.md`. Dogfood on image-generation-lab: closed realism bake-off as keep; scaffolded `2026-07-13-sdxl-install-scorecard-verify`.
- ADR-029 (Accepted) in [DECISIONS.md](DECISIONS.md): MainFrame Epistemic Standard — 12-source epistemics canon (local `10_knowledge/knowledge-systems/epistemics/`), expanded [EPISTEMIC_STANCE.md](EPISTEMIC_STANCE.md) with GRADE certainty and promotion gate, workflow at `.context/workflows/epistemic-standard.md`, GRADE mapping in credibility-tiers, agent wiring.
- Local epistemics sub-wiki (gitignored `10_knowledge/`, 2026-06-17): 12 raw stubs (SEP, GRADE, Ioannidis, Nickerson, OSC, Cochrane, CEBM, CASP, Guba/Lincoln, Merton, CASP); synthesis notes `mainframe-epistemic-standard` and `epistemics-source-map`; source-literature run note.
- ADR-028 (Accepted) in [DECISIONS.md](DECISIONS.md): `source-literature` workflow complements ingest — credibility tiers, dedup, bibliographic capture to `00_inbox/` before `ingest-minion`. Skill at `.agents/skills/source-literature/`, workflow at `.context/workflows/source-literature.md`, subagent at `agents/source-literature-agent.md`, Claude mirror at `.claude/skills/source-literature.md`.

- Project-level local-agent delegation packets and private harness evaluation (2026-06-14): added `bin/task-packet`, `.context/templates/task-packet.md`, `.context/workflows/delegate-local-task.md`, packet-aware task manifest generation, deterministic validation tests, and ADR-024. The ignored `agent-harness-eval` project supplies disposable Git fixtures, Stub/Aider adapters, external verification, receipts, harness variants, reports, and a sanitized capability summary for the Local Agent workstation.
- `bin/aider-watcher` telemetry hardening and `tests/test_aider_watcher.py`: Local Coder runs now keep the explicit `client: local` tag, emit one start per session, capture newly created histories, record allowlisted context/edit/approval diagnostics plus observed edits and verification commands, and support isolated history replay. Added `.context/workflows/local-coder-run.md` to keep deterministic operations and external verification outside the model.
- `10_knowledge/regulated-systems/` knowledge domain (2026-06-13): GxP/pharma regulatory rules — cGMP records & document control, data integrity / ALCOA+, electronic records & audit trails (21 CFR Part 11 / EU Annex 11), quality risk management & CSV, and cosmetics/OTC GMP — with a source catalog and a rule→control crosswalk grounding the `biotech-rag-assistant` project. Registered in the tracked [10_knowledge/index.md](10_knowledge/index.md) and indexed into MindGraph; domain contents are gitignored per the processed-knowledge convention.
- ADR-022 (Accepted) in [DECISIONS.md](DECISIONS.md): shared-component reuse via pinned git submodules with automated Dependabot bump-PRs, canonical = each component's projects-root/GitHub repo. Codifies how `evidence-bundler` / `claim-audit-lab` / `apparatus-contracts` / `research-scaffold-harness` stay current across consumers (`scaffold-claims-study` today; the Biotech RAG Assistant per its own ADR-015).
- Planning Standard in [30_projects/AGENTS.md](30_projects/AGENTS.md) (2026-06-12): the four coordination entries (`README.md`, `log.md`, `decisions.md`, `plans/`) are now explicitly required per project, and phased work follows a documented phase-plan template (`Goal` / `Non-Negotiable Boundaries` / `Unit Stance` / `Unit Plan` with per-unit green-boundary checklists / `Verification` / `Tie-Off Review` / `Handoff Notes`), generalized from the format proven in two project workbenches. Completed or historical plans are never retrofitted (Agent Protocol rule 6). Missing coordination files were scaffolded in the two non-compliant private projects.
- Phase 5 dogfood completed (2026-05-28). The full v2 pipeline (`00_inbox/` → minion normalize → `01_ingest/ready/` → ingest-agent enrich → `bin/prep-ingest` → `01_ingest/queue/` → minion route → `10_knowledge/<domain>/`) was exercised end-to-end against a sandbox covering all four entry shapes (no-frontmatter clipping, partial-frontmatter draft, already-`status: extracted` note, convention-named raw PDF) and against a real captured note (`mindgraph-integration-notes.md` routed into `10_knowledge/ai-systems/`). All six acceptance criteria from [planning/mainframe-agent-ingest-plan.md](../../planning/mainframe-agent-ingest-plan.md) Phase 5 passed.
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
