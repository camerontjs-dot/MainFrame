---
title: "Methodology approach — read first in new session"
domain: "knowledge-systems"
type: "note"
status: "active"
source: "G43–G45 synthesis session 2026-06-20"
tags: ["methodology", "handoff", "eval-planning"]
updated: "2026-06-20"
---

# ⚠️ Methodology approach — MainFrame Process Eval

**New session:** Read this before treating eval outputs as causal proof of process changes. Playbook: `10_knowledge/knowledge-systems/methodology/2026-06-20__knowledge-systems__note__scientific-method-experiment-design-synthesis.md`. Contract: `.context/workflows/process-evaluation.md`.

## Current posture (2026-06-20 eval)

- 168 tests green; duration coverage ~75% (up from ~20%).
- `workflow-report` now separates tool failures (79) vs StopFailures (410) vs policy blocks (0).
- **Next slice:** Claude StopFailure investigation (410 events, 2 sessions) — need safe reason/kind field if hook exposes it.

## Study type: observational friction radar

This is **not** an RCT. Use language: *associated with*, *trend*, *signal* — not *caused*.

| Dimension | Use for |
|-----------|---------|
| Correctness / safety | Tests, dry runs, blockers |
| Provenance | Raw preservation, append-only |
| Throughput | Inbox/ingest counts |
| Friction | Repeated manual steps, failures |
| Observability | Tags, duration, pairing |
| Improvement readiness | Bugs, process gaps, workflow/skill candidates, parked questions |

## Cadence (keep)

1. Baseline before changes
2. ≤2 improvement slices at a time
3. Re-run after change
4. Repeat after 1 week or 5 sessions

## Promotion gate (G45)

Promote pattern only when: 3+ real tasks (or high-risk mandatory path), recognizable I/O, clear layer, success/boundary/failure cases evaluable, no duplicate workflow.

## Improvement tracking method

Use `improvement-backlog/items.md` for MainFrame process findings that might
turn into a bug fix, automation, workflow, skill, documentation update,
project-local experiment, or explicit no-action decision.

Treat every item as a nomination until triaged. Do not promote or implement
from a single attractive observation unless it is a high-risk mandatory path.

Process-eval finding classes:

| Class | Meaning |
|-------|---------|
| `code-defect` | Implementation does not match the contract. |
| `process-gap` | The contract lacks a needed step or boundary. |
| `adoption-gap` | A sound workflow exists but is not being used. |
| `telemetry-gap` | Current signals cannot support the conclusion. |
| `intentional-backlog` | Queued work is expected, not a defect. |

Practical backlog categories:

| Category | Use for |
|----------|---------|
| `bug` | A broken deterministic check, parser, script, or stale state condition. |
| `automation-candidate` | Repeated deterministic work that might belong in `bin/`. |
| `workflow-candidate` | Operator-driven sequence using existing tools. |
| `skill-candidate` | Repeated agent judgment, domain rules, or tool strategy. |
| `documentation-gap` | Missing or stale guidance, handoff, or boundary text. |
| `research-question` | Useful but not ready for implementation or promotion. |
| `declined` | Explicitly not worth promoting now; keep the rationale visible. |

Every backlog item needs source evidence: eval output, MindGraph query,
telemetry summary, command output, project log, or decision reference. If the
evidence is only a retrieval nomination, mark it as such and inspect the source
before selecting the item.

## StopFailure slice frame

1. **Observation** — concentration in `main-claude-pixel`, 2 sessions
2. **Hypothesis** — specific hook/session pattern (document, don't assume)
3. **Instrumentation** — `stop_failure_kind` enum if payload allows
4. **Re-baseline** — one change only, narrow time window

## Do not

- Claim a workflow change "improved throughput X%" without a single-variable window and before/after note.
- Copy prompts or private telemetry into tracked reports.

## Related

- Latest: `local-only: outputs/2026-06-20-evaluation.md`
- `10_knowledge/knowledge-systems/methodology/2026-06-21__knowledge-systems__note__eval-sample-size-and-significance.md` (§3.4)
- `10_knowledge/knowledge-systems/methodology/2026-06-21__knowledge-systems__note__eval-cross-project-trends-synthesis.md` (§3.1, §5 portfolio rollup)
