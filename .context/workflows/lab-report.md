# Lab report convention

**Universal experiment tracking.** Every decision-bearing test, matrix cell family, or live probe that should be remembered gets one lab report — the same skeleton a careful experimentalist would keep in a lab notebook.

## Profile

| Field | Value |
|-------|-------|
| structural_type | workflow |
| owner_surface | `EVAL_METHODOLOGY.md` + project `outputs/lab-reports/` |
| related | eval-methodology, project-experiment-loop, craft-research-loop, epistemic-standard |

## Purpose

Stop losing experiments as unnamed logs, half-filled scorecards, or chat history. A lab report forces:

1. **Question and decision first** (before results)
2. **One primary factor** (or an explicit multi-factor design)
3. **Raw paths** separate from interpretation
4. **Irregularities** (even "probably nothing")
5. **Disposition + next experiment**

## Relationship to other templates

| Artifact | Use when |
|----------|----------|
| **lab-report** (this) | Default for any measured experiment / test campaign |
| `eval-output.md` | Same content shape specialized for **eval-registry** harvest (metric YAML required) |
| `craft-trial.md` | Product/craft bake-offs with keep\|kill\|iterate (still encouraged to use lab-report sections 1–10) |
| JSON receipts | Machine-checkable cell-level evidence; **not** a substitute for the report |

**Rule:** If you would write a methods section in a paper, write a lab report. If it is only `unittest` green in CI with no design question, skip.

## Where reports live

```text
30_projects/<slug>/
  outputs/
    lab-reports/
      YYYY-MM-DD-<slug>.md     # one report per experiment identity
  raw-materials/
    YYYY-MM-DD-<slug>/         # logs, receipts copies, scorecards
```

Shorthand allowed: `outputs/YYYY-MM-DD-<slug>.md` for eval-profile projects already using that path (project-experiment-loop scaffold). Prefer `outputs/lab-reports/` for new work.

## Lifecycle

```text
scaffold → (optional) design freeze → execute → fill results → disposition → harvest?
```

```bash
# Scaffold
bin/lab-report scaffold \
  --project agent-harness-eval \
  --title "coder-14b-verify-ablation" \
  --question "Does hiding run_verify increase false completions on task 07?" \
  --decision "If yes, require verify tool for multi-file coding profiles" \
  --study-type exploratory

# After run
# edit the report; move/link raw receipts into raw-materials/<id>/

# Check completeness
bin/lab-report check --project agent-harness-eval --id 2026-08-08-coder-14b-verify-ablation

# List open reports
bin/lab-report list --project agent-harness-eval --open

# Eval-profile: also harvest when metrics are final
bin/project-experiment-loop close --project agent-harness-eval
```

## Required fields (minimum bar)

A report is incomplete if any are missing:

- [ ] `lab_report_id` / `eval_run_id`
- [ ] `study_type`
- [ ] `decision_sentence`
- [ ] `hypothesis` (or explicit "descriptive only — no hypothesis")
- [ ] primary metric + unit of analysis + n
- [ ] one primary independent factor (or stated multi-factor design)
- [ ] results table or explicit "no cells completed"
- [ ] `irregularities` section (may be empty list with statement "none observed")
- [ ] limitations / does-not-prove
- [ ] `disposition` + `next_experiment`

## Study types

Same vocabulary as `EVAL_METHODOLOGY.md`:

| Type | Use |
|------|-----|
| exploratory | First look, small n, generate next protocol |
| confirmatory | Pre-registered contrast |
| regression | Frozen baseline after change |
| observational | Telemetry / before-after windows |
| calibration | Human gold / scorer agreement |

## Dispositions

| Value | Meaning |
|-------|---------|
| `open` | Running or unfilled |
| `accept` | Evidence supports the decision sentence's positive branch (still respect study_type limits) |
| `reject` | Evidence supports the negative branch or fails pre-registered gate |
| `hold` | Interesting but blocked (n, confound, tooling) |
| `iterate` | Close this id; open a new lab report with a sharper question |

Do **not** use `accept` on a single exploratory run to claim production graduation.

## One factor per phase

Default for harness and model work (agent-harness-eval rule): change **either** model/path **or** harness factor, not both, in one `lab_report_id`. Multi-factor matrices need an explicit design section and still one **primary** metric.

## Privacy

| Report content | Allowed |
|----------------|---------|
| Methods, n, metrics, disposition | yes in private project |
| Public-safe restatement | only after sanitization (no absolute paths, no fixture gold) |
| Raw agent transcripts | stay in raw-materials / gitignored live trees |

## Retrofit

Existing scorecards and sprint rollups can be **linked** from a new lab report rather than rewritten wholesale. Minimum retrofit:

1. Scaffold lab report with the real question/decision.
2. Point results section at existing paths.
3. Fill disposition + irregularities + does-not-prove.

## Related

- Template: `.context/templates/lab-report.md`
- CLI: `bin/lab-report`
- Eval contract: `EVAL_METHODOLOGY.md`
- Experiment loop: `.context/workflows/project-experiment-loop.md`
- Epistemic labels: `.context/workflows/epistemic-standard.md`
