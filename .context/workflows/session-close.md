# Session Close Workflow

A session-close workflow should always update state, write a concise handoff note, record meaningful changes in a log, and identify the exact next reentry point.

## Required Actions:
1. **Update `STATE.md`:** 
   - What changed?
   - What remains?
   - What is blocked?
   - What should be done first next time? (Handoff note)
2. **Log Updates:** If significant architecture or design choices were made, record them in `DECISIONS.md`.
3. **Regenerate indexes:** Run `bin/sync-project-index --write` when project metadata changed.
4. **Refresh retrieval:** Run `bin/mindgraph-refresh` when durable knowledge changed.
5. **Review telemetry:** Run `bin/workflow-report --days 1` when diagnosing process friction.
6. **Commit:** Ensure any living documents have their timestamps or logs updated.
