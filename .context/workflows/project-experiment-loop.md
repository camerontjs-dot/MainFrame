# Project Experiment Loop

**One measured experiment pass.** Complements the research-lane-loop (literature → knowledge).
This loop owns **testing and results**: design → run → output → registry → **action**.

## Profile

| Field | Value |
|-------|-------|
| structural_type | workflow |
| owner_surface | `EVAL_METHODOLOGY.md` + eval-profile projects |
| related | eval-methodology, eval-schedule, eval-registry, research-lane-loop |

## Purpose

Make every decision-bearing test:

1. **Identifiable** (`eval_run_id`)
2. **Protocol-pinned** (`protocol_ref`)
3. **Harvested** into `20_live/eval-registry/`
4. **Actionable** (triage card with one next step — not a silent green log)

```text
preflight → design gate → execute → write output → harvest → triage/action → loop?
```

## When to use

- Eval-profile projects (`*-eval`, `scaffold-claims-study`, `eval-profile` tag)
- MindGraph canaries, harness matrices, process baselines
- Any measurement that should change a promotion, architecture, or process decision

## When not to use

- Pure literature capture → `research-lane-loop`
- Single unit test green with no report (keep as CI)
- One-off task-packet verification (local gate only)

## Separation

| Need | Loop |
|------|------|
| External knowledge | research-lane-loop → `10_knowledge/` |
| Measured result | **this loop** → `outputs/` + registry |
| Project gap routing | PRP01 project-research-pipeline |

## Command card

```bash
# 0) Health
bin/mindgraph doctor
bin/eval-schedule check
bin/project-experiment-loop preflight --project mindgraph-eval

# 1) Fresh MindGraph regression canary (probe + envelope + doctor + harvest + triage)
bin/project-experiment-loop canary --fresh

# 2) Or scaffold a custom experiment output, run manually, then close
bin/project-experiment-loop scaffold \
  --project mindgraph-eval \
  --study-type exploratory \
  --title "my-slice" \
  --decision "If X, do Y"
# ... run experiment, fill outputs/ ...
bin/project-experiment-loop close --project mindgraph-eval

# 3) Action ALL MainFrame evals (default triage = portfolio)
bin/project-experiment-loop portfolio
# same as: bin/project-experiment-loop triage --scope portfolio
cat 20_live/eval-registry/last-eval-action.md

# MindGraph-only action card (optional)
bin/project-experiment-loop triage --scope canary
```

## Steps

### 0. Preflight

- Read `30_projects/<slug>/methodology-approach.md`
- `bin/mindgraph doctor` when retrieval is in scope
- `bin/eval-registry status` / `bin/eval-schedule check`

### 1. Design gate

- [ ] `decision_sentence`
- [ ] `study_type`
- [ ] `eval_run_id` (`YYYY-MM-DD-<slug>` or timestamped)
- [ ] `protocol_ref` pinned
- [ ] Primary metric + unit of analysis
- [ ] Irregularity watch list

### 2. Execute

- Raw under `raw-materials/<eval_run_id>/` when applicable
- Do not change protocol mid-run without a new `eval_run_id`

### 3. Write output

Use the **lab report** convention (`.context/templates/lab-report.md`, workflow `lab-report.md`) so every experiment has researcher-grade tracking.

- Prefer: `bin/lab-report scaffold …` → `outputs/lab-reports/<id>.md`
- Eval-registry specialization: `.context/templates/eval-output.md` (also emitted by `project-experiment-loop scaffold`)
- Minimum bar: `bin/lab-report check --project <slug> --id <id>`

### 4. Harvest

```bash
bin/eval-registry harvest
bin/eval-registry check --strict   # eval-profile
```

### 5. Triage / action (non-optional for canaries)

Running is not enough. After harvest:

1. Compare to prior run (pass/fail, metric deltas)
2. Write `20_live/eval-registry/last-canary-action.md`
3. Set **one** next action (investigate / no-op keep cadence / open improvement slice)
4. Optional: update project `next_action` when severity ≥ medium

`bin/project-experiment-loop triage` and `canary --fresh` do this automatically.

### 6. Loop decision

| Outcome | Next |
|---------|------|
| Regression green, no high irregularities | Keep cadence; no product change |
| Regression red or unprotected scope rise | Investigate before ingest/harness changes |
| Exploratory interesting | Design confirmatory follow-up with new `eval_run_id` |
| Knowledge gap | Emit research-lane candidate → research-lane-loop |

## Automation model (all MainFrame evals)

| Layer | What runs | What was missing |
|-------|-----------|------------------|
| **Schedule** | weekly: process suite + MindGraph canaries + harvest | Already automated |
| **Registry** | `runs.jsonl` / `metrics.jsonl` / `irregularities.jsonl` | Already automated |
| **Action** | Human reads OPERATOR.md | **Often skipped** |

**Right idea:** keep execution scheduled; automate **portfolio triage**, not more silent metrics.

| Card | Path | Scope |
|------|------|--------|
| **Portfolio (primary)** | `20_live/eval-registry/last-eval-action.md` | MindGraph + process suite + every eval-profile project |
| Canary pointer | `last-canary-action.md` | Points at portfolio card |

- After weekly suite: `triage --scope portfolio`
- On session-open: surface `last-eval-action.md`
- `canary --fresh` for MindGraph package; `portfolio` anytime for action refresh

Eval-profile projects covered: `mindgraph-eval`, `mainframe-process-eval`, `agent-harness-eval`, `agent-tracker-eval`, `scaffold-claims-study`, `skill-eval-workshop`, plus any `tags: [eval-profile]`.

## Related

- `EVAL_METHODOLOGY.md`, `.context/workflows/eval-methodology.md`
- `.context/workflows/eval-schedule.md`, `process-evaluation.md`
- `.context/workflows/research-lane-loop.md`
- `bin/project-experiment-loop`, `bin/eval-registry`, `bin/eval-schedule`
- Operator card: `20_live/eval-registry/OPERATOR.md`

## Dogfood — batch20 process gaps (2026-07-13)

### What worked
- `canary --fresh` end-to-end green (probe failures 0)
- Portfolio triage gives a single operator card for all eval-profile projects
- Harvest + check --strict stay green when outputs are registry-shaped

### Friction → improve
| Issue | Fix direction |
|-------|----------------|
| Scaffold harvested with placeholder metrics | Close must re-harvest or gate placeholders |
| High irregularities stay open after product disposition | Irregularity lifecycle: waived / accepted_risk / superseded |
| Operator-gated studies inflate severity | `operator_gated` flag in registry / triage sections |
| Canary log buffering when backgrounded | Unbuffered progress / JSONL |

Full note: `30_projects/mainframe-process-eval/outputs/2026-07-13-three-loop-process-gaps.md`.

## Irregularity lifecycle (G1)

```bash
# Accept historical risk so portfolio severity tracks actionable work only
bin/eval-registry dispose \
  --project agent-harness-eval \
  --run-id <run> \
  --id <irregularity_id> \
  --status accepted_risk|waived|superseded \
  --reason "..."

bin/eval-registry list-open-high
bin/project-experiment-loop portfolio
```

Statuses: `open` | `accepted_risk` | `waived` | `superseded` | `resolved`.
Store: `20_live/eval-registry/irregularity-dispositions.jsonl`.
