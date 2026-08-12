# Session Close Workflow

Part of the **session lifecycle loop**: `.context/workflows/session-lifecycle.md`
(open → work → close → loop decision).

A session-close workflow should always update state, write a concise handoff note, record meaningful changes in a log, and identify the exact next reentry point.

## Script
- Command: `bin/session-close`
- Check mode: `bin/session-close --check` (report what needs doing, exit 1 if auto actions pending)
- Apply mode: `bin/session-close --apply` (run auto actions: local project-index sync, mindgraph-refresh, workflow-report)
- Checkpoint mode: `bin/session-close --checkpoint` (fast, prompt-free evidence snapshot — see hooks below)
- Feed mode: `--feed` with `--check`/`--apply` appends the machine-readable result to `20_live/workstation/session-close-feed.jsonl` and exits 0 (the outcome lives in the record)
- Auto-detect project: reads `## Active Project` from `STATE.md`
- Manual actions (STATE.md narrative, DECISIONS.md review) are always reminded but never automated

## Automated lifecycle hooks (ADR-040)
- **PreCompact** runs `session-close --checkpoint --hook-stdin`: every mid-session compaction appends a dated snapshot (derived active projects from `30_projects/*` mtimes + nested-repo commits, telemetry zones, weekly-eval staleness, derived-vs-declared drift) to `20_live/last-handoff-draft.md` and a record to the tracker feed.
- **SessionEnd** runs `session-close --check --feed --hook-stdin`: the close-check result lands in the tracker feed without operator action.
- The `## Session Checkpoints (auto)` section of the draft is machine-owned (newest five snapshots); the digest scaffold above it is preserved, and `--apply` preserves the section in return.
- STATE.md flow: checkpoints draft continuously → the operator approves/edits the narrative at true session close. Target: STATE.md never more than one session stale.

## Required Actions:
1. **Update `STATE.md`:**
   - What changed?
   - What remains?
   - What is blocked?
   - What should be done first next time? (Handoff note)
2. **Log Updates:** If significant architecture or design choices were made, record them in `DECISIONS.md`.
3. **Regenerate indexes:** Run `bin/sync-project-index --write` when project metadata changed. The generated `30_projects/index.md` is local and ignored by Git.
4. **Refresh retrieval:** Run `bin/mindgraph-refresh` when durable knowledge changed.
5. **Review telemetry:** Run `bin/workflow-report --days 1` when diagnosing process friction.
6. **Audit surface (post-ingest verification):** When durable knowledge was changed or a batch/tiered route occurred, run `bin/audit-sweep --dry-run` (or `--apply` after review). See [.context/workflows/audit-sweep.md](.context/workflows/audit-sweep.md). This is the compensating control for review-after (ADR-019).
7. **Handoff digest (operator load reduction):** `bin/session-close --apply` now writes `20_live/last-handoff-draft.md` with recent signals from ingest-status, audit-sweep, etc. + a template for STATE.md narrative. Review/edit it into STATE.md to lower manual transcription.
8. **Commit:** Ensure any living documents have their timestamps or logs updated.
