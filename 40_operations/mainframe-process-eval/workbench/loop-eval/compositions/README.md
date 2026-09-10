---
title: "Loop compositions (bigger programs)"
domain: "knowledge-systems"
type: "workbench"
status: "active"
updated: "2026-07-23"
---

# Compositions — bigger “loops” without a fourth loop type

A **composition** is an ordered chain of catalogue entries (tier A/B loops + workflows).
It answers “how does X get from start to archive?” without merging literature, craft, and measurement into one god-procedure.

## Rules

1. Stages reference catalogue `id`s from `entries.json`.
2. Terminal stages are explicit (archive, stop, blocked).
3. Optional branches are labeled (craft vs experiment).
4. No new first-class loop unless tier-A gates + ADR.

## Draft compositions (baseline)

### `comp-research-lane-lifecycle`

**Intent:** Source discovery through portfolio archive for one research lane.

```text
cand-lane-intake-archive          # intake (once)
    ↓
loop-research-lane  × N           # foundation → … (includes source-literature step)
    ↓
cand-research-handoff             # when knowledge should hit a project
    ↓
  ┌─ loop-craft ────────────────┐
  ├─ loop-experiment ───────────┤  optional application branches
  └─ implement / operator ──────┘
    ↓
cand-lane-intake-archive          # archive when lane stop condition met
```

**Note:** `cand-source-literature` and `loop-ingest-pipeline` run *inside* research-lane passes, not as peer outer stages.

### `comp-weekly-control-plane`

**Intent:** Honest scheduled health → action.

```text
cand-eval-schedule-control        # launchd daily/weekly
    ↓
loop-experiment (canary/triage)   # portfolio action card
    ↓
loop-process-evaluation           # optional deeper process slice
```

### `comp-standing-operation` (example)

**Intent:** Recurring signals feed a standing operation. Admission of one
operation does not migrate other projects automatically.

```text
cand-intake
    ↓
loop-operating-cycle
    ↓
(operation next_action)
```

## Next

- Optional `compositions.yaml` with machine-checked stage ids.
- Link from durable `.context/loops/` when published.
