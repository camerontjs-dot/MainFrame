# Session Guide

What a normal MainFrame working session looks like from the operator's seat.
Scripts handle the deterministic steps; judgment stays manual. Telemetry
records itself. The per-step contracts live in the other files in this
folder — this page is the end-to-end view.

## 1. Open

```bash
bin/session-open
```

Loads context in a fixed order (root contract, state, active project README).
It picks the active project from `STATE.md` — if that is stale, override with
`--project <slug>` now and correct `STATE.md` before you close. Details:
`session-open.md`.

## 2. Work

- Capture without ceremony: drop files into `00_inbox/`. No frontmatter is
  required at capture time; pass 1 is suggestion-first (ADR-011).
- Project work happens inside `30_projects/<slug>/` workbenches, which the
  outer repo ignores.
- Live-state updates in `20_live/` get dates and append-only timelines or
  snapshots, never silent overwrites.
- Telemetry needs nothing from you: Claude Code and Codex hooks append
  redacted events (hashes, zones, durations — never prompt or file text) to
  `20_live/workflow-metrics/events/`.

## 3. Ingest pass (only when you choose to run one)

Not every session includes ingest. When one does:

```bash
bin/ingest-minion run --dry-run   # warnings are suggestions, not rejects
bin/ingest-minion run --apply
```

The ingest-agent then enriches `01_ingest/ready/` files (domain, type, tags,
connections — the judgment middle), `bin/prep-ingest` validates them into
`queue/`, and minion pass 2 applies the strict `queue/ -> 10_knowledge/`
gate. Details: `ingest-minion.md`; migration drops follow
`rolling-second-brain-migration.md`.

Migration batches and aged backlogs skip the per-file loop: batch mode
(ADR-019) classifies the lane under `.context/routing-policy.md`, you approve
one review table, and exceptions stay in `ready/` tagged `routing-exception`.
Routed clips carry `needs-audit`, which the epistemic research system sweeps
continuously (see [.context/workflows/audit-sweep.md](.context/workflows/audit-sweep.md) and `bin/audit-sweep`) — review-after instead of approve-before. Your first full-table
review is also the calibration baseline for how much autonomy each rule earns. Run the sweep regularly (integrated into session-close) and review the pending-review surface before widening Tier A usage.

To see where the backlog actually stands first:

```bash
bin/ingest-status
```

It separates batch-registered migration files (intentional backlog tracked by
an append-only disposition ledger) from organic captures going stale.

## 4. Close

```bash
bin/session-close --check
bin/session-close --apply   # index sync, MindGraph refresh, telemetry report
```

The judgment steps stay yours and are only reminded, never automated:

1. Update `STATE.md`: active project, what changed, what remains, the next
   reentry point.
2. Record architecture or workflow changes in `DECISIONS.md`.
3. Review the staged diff before committing — keep private content out of
   the tracked surface.

Details: `session-close.md`.

## Weekly, or when something feels off

```bash
bin/workflow-report --days 7
bin/ingest-status
```

Read the per-client quality block before trusting aggregates, then run the
evaluation loop in `process-evaluation.md` before changing any process.

## Known telemetry limits (as of 2026-06-09)

- Codex has no `SessionEnd`, `PostToolUseFailure`, or `PostToolBatch` hook
  events, and it silently ignores unrecognized names. Its session-close
  coverage is structurally 0%; judge close habits from the claude row, not
  the aggregate. `.codex/hooks.json` now wires its real vocabulary
  (`Stop`, `SubagentStart`/`SubagentStop`, `PermissionRequest`,
  `UserPromptSubmit`, compaction); treat those rows as unverified until the
  first events appear, and expect Codex to re-prompt once to trust the
  changed hooks.
- Codex tool failures are derived from `tool_response` exit codes inside
  `PostToolUse` (best effort); its payloads carry no durations.
- Permission and approval events (`PermissionRequest`, `Notification`)
  cannot fire while sessions run with permissions bypassed, so any state
  built on them stays unverified until a default-permission session runs.
- Tool failures are execution events, not task quality.

## What never happens automatically

- No script writes `STATE.md` narrative, `DECISIONS.md`, or knowledge
  content.
- Pass 1 never rejects a capture; strict rejects exist only at the
  `queue/ -> 10_knowledge/` gate.
- Nothing moves or deletes raw evidence; the reports (`workflow-report`,
  `ingest-status`) are read-only.
