---
title: "Session lifecycle loop"
domain: "knowledge-systems"
type: "workflow"
status: "active"
structural_type: "workflow"
lifecycle_scope: "system"
owner_surface: "HARNESS.md"
authority: "workflow-contract"
privacy: "public-safe"
volatility: "stable"
source_of_truth: true
update_rule: "replace-with-review"
related_surfaces:
  - ".context/workflows/session-open.md"
  - ".context/workflows/session-close.md"
  - "bin/session-open"
  - "bin/session-close"
  - "20_live/focus/current.yaml"
do_not_use_for:
  - "project outcome work itself"
  - "replacing eval-schedule or mainframe-doctor"
updated: "2026-07-23"
---

# Session lifecycle loop

One **agent session** as a closed control unit: open with honest context → work →
close with reentry truth. Implements progressive disclosure (open) and
ADR-040 checkpoints (close hooks).

## Purpose

```text
open (focus/STATE → contract chain) → work → close (check|checkpoint|apply*)
  → loop decision (continue / handoff / stop)
```

\* `session-close --apply` remains gated (`--acknowledge-unverified` or env ack).

## When to use

- Starting or ending a coding-agent session on MainFrame
- Compaction / SessionEnd hooks (automated half of the loop)
- Diagnosing false-green open or stale close state

## When not to use

- Replacing project-specific loops (research / craft / experiment)
- Full system health (use `bin/mainframe-doctor`, `bin/eval-schedule check`)

## Loop unit

| Field | Rule |
|-------|------|
| Unit | One client session (or one checkpoint slice mid-session) |
| Entry | SessionStart / operator `bin/session-open` |
| Exit | SessionEnd check/feed, or operator close check/apply; handoff next_action known |

## Steps

### Open

1. Prefer structured focus: `20_live/focus/current.yaml` (ADR-044 / MPE-024).
2. Run `bin/session-open` (or `--json` / `--project <slug>`).
3. Load only the progressive chain the script prints (AGENTS → STATE → project → plan → …).
4. Fail closed if project path does not resolve (Unit 2.2).

Detail: `.context/workflows/session-open.md`.

### Work

- Stay inside selected project / focus success boundary.
- Do not treat tool success as task success.

### Close

1. `bin/session-close --check` — pending autos / warnings (exit 1 if work remains).
2. Hooks: PreCompact `--checkpoint`; SessionEnd `--check --feed`.
3. Operator true close: edit STATE from draft; optional `--apply` only with ack.
4. Note reentry on project `next_action` when project work changed.

Detail: `.context/workflows/session-close.md`.

## Loop decision

| Decision | Meaning |
|----------|---------|
| **continue** | Same session / same focus after compaction |
| **handoff** | Stop; STATE + project next_action sufficient for next session |
| **switch_focus** | Change focus authority (separate from project_state) then re-open |
| **stop** | No further agent work; leave checks green or explicitly degraded |

## Action / eval surface

- `20_live/workstation/session-close-feed.jsonl` (machine feed)
- `20_live/last-handoff-draft.md` (checkpoint + digest draft)
- `bin/session-open --json` ok/path fields
- Doctor: SESSION-001 / SESSION-002

## CLI

```bash
bin/session-open --json
bin/session-close --check
bin/session-close --checkpoint   # hooks / fast snapshot
# bin/session-close --apply --acknowledge-unverified   # rare; gated
```

## Guardrails

- Focus selection ≠ project activation (ADR-044).
- Never copy prompts/transcripts into feed (hash-only hook fields).
- Close apply is not default; prefer check + human STATE edit.
