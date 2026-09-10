# Eval Methodology Contract

This document defines how MainFrame designs, runs, records, and interprets **evaluations** — distinct from claim discipline in [EPISTEMIC_STANCE.md](EPISTEMIC_STANCE.md).

## Separation of duties

| Question | Contract | Workflow |
|----------|----------|----------|
| Was the run designed and analyzed honestly? | **This file** | optional/deferred eval-methodology workflow |
| Are the written conclusions supported? | EPISTEMIC_STANCE | [.context/workflows/epistemic-standard.md](.context/workflows/epistemic-standard.md) |
| Is MainFrame process healthy? | process-eval plan | [.context/workflows/process-evaluation.md](.context/workflows/process-evaluation.md) |

Eval results are **observations or hypotheses** until replication, calibration, or hold-out confirms them. Never promote from a single exploratory run.

## Lab report convention (universal)

Every decision-bearing test or experiment is tracked as a **lab report** — the same skeleton a careful experimentalist would keep (question, design, results, irregularities, limits, disposition, next experiment).

| Piece | Path |
|-------|------|
| Template | [`.context/templates/lab-report.md`](.context/templates/lab-report.md) |
| Workflow | optional/deferred lab-report workflow (`bin/lab-report` when installed) |
| CLI | `bin/lab-report scaffold \| check \| list` |
| Default location | `30_projects/<slug>/outputs/lab-reports/<lab_report_id>.md` |
| Raw | `30_projects/<slug>/raw-materials/<lab_report_id>/` |

Eval-registry outputs (`.context/templates/eval-output.md`) **implement** this convention and add the mandatory metric YAML harvest block. Craft trials may use `craft-trial.md` but should still answer the lab-report minimum bar when the trial is measurement-like.

```bash
bin/lab-report scaffold --project example-project \
  --title "my-experiment" \
  --question "..." --decision "..." --study-type exploratory
bin/lab-report check --project example-project --id YYYY-MM-DD-my-experiment
```

## Core rules

1. **Decision sentence first** — Every eval slice states what will change if the result is positive, negative, or inconclusive.
2. **Study type required** — `confirmatory`, `exploratory`, `regression`, `observational`, or `calibration`. No unlabeled runs.
3. **Protocol pin** — `protocol_ref` (frozen query set, harness version, rubric version, script hash) before peeking at results.
4. **Unit of analysis fixed** — Per query, per claim, per case, per session window — declared before analysis.
5. **Raw before summary** — Artifacts in `raw-materials/` or redacted telemetry paths; summaries in `outputs/` never replace raw.
6. **Lab report required** — Decision-bearing runs write a lab report (or eval-output specialization); unnamed log dumps are not enough.
7. **Metric extract mandatory** — Every eval-profile / promotion-relevant output ends with a `## Metric extract (eval-registry)` YAML block.
8. **Irregularities explicit** — Every extract includes `irregularities:` — use `[]` only when none were observed; omitting the field is a protocol violation.
9. **Track everything odd** — Timing glitches, parse warnings, hash mismatches, off-by-one counts, flaky reruns, scope warnings, tool exit 127, YAML scalar quirks — log as irregularities even if "irrelevant" to the headline metric.
10. **No significance theater** — Effect sizes, CIs, and raw counts over binary p-value promotion. See methodology synthesis on sample size.
11. **Registry harvest** — Run `bin/eval-registry harvest` after writing or updating eval outputs; `bin/eval-registry check --strict` before session close when eval work occurred.

## Eval-profile projects (strict)

Applies to projects matching `*-eval`, `scaffold-claims-study`, and any project with `tags: [eval-profile]` in README:

- `methodology-approach.md` — read-first in new session
- `outputs/*.md` — frontmatter `study_type`, `protocol_ref`, `eval_run_id`
- Metric extract + irregularities on every report
- `decisions.md` conclusions that depend on evals cite `eval_run_id` + study_type

Project rules: [30_projects/AGENTS.md](30_projects/AGENTS.md) § Eval profile.

## Knowledge base

Canonical playbooks (local, `10_knowledge/knowledge-systems/methodology/`):

- Scientific method & experiment design synthesis
- Eval sample size and significance
- Cross-eval trends and registry
- Irregularity and anomaly tracking

Lane trackers, when present, live under the local research-program operation.

## Registry

Append-only eval state: `20_live/eval-registry/`

- `runs.jsonl` — one row per harvested run
- `metrics.jsonl` — long-format metric rows
- `irregularities.jsonl` — every logged irregularity

Harvest: `bin/eval-registry harvest`. Status: `bin/eval-registry status`.

## Skill & Agent-as-Evaluator Standards

For validating portable agent skills (e.g., prompt-creation, skill-creation) without external API costs, the following standards apply:

1. **Agent-as-Evaluator Separation**:
   - The workbench/runner is restricted to deterministic, zero-cost operations (static structure linting, trigger phrase density validation, receipt log checks, gate math).
   - The active agent session serves as the reasoning evaluator, executing the mock runs, judging correctness, and writing JSON receipts.
2. **Pesticide Paradox Mitigation**:
   - **Trigger Density Control**: Centralized skill triggers are strictly capped at 5 to 7 trigger phrases/keywords to prevent trigger bloat and false-activation noise.
   - **Dynamic Case Expansion**: Whenever an agent fails a skill constraint in production, a representative test case must be immediately transcribed and added to the workbench cases.
3. **The 5-Case Protocol**: All evaluated skills must be measured against 5 distinct case classes to prevent overfitting:
   - *Silent Negative* (activates only on target domain, stays silent on adjacent tasks).
   - *Happy Path* (performs correctly when complete information is present).
   - *Minimal Input* (seeks clarification instead of making assumptions).
   - *Edge Cases* (resilient to contradictory or vague goals).
   - *Overachiever / Constraints* (adheres to strict length limits and forbidden phrases).
4. **Graduation Gates**:
   - Skills cannot be promoted to global production without passing their designated gate thresholds (typically $\ge 80\%$ overall pass rate, with $100\%$ success on critical paths like Happy Path and Silent Negative).
   - **Cross-Model Calibration**: Must compare performance (using the `compare` command) between models (e.g., Claude Code vs. Codex) to record formatting consistency and token efficiency.

## Related

- [HARNESS.md](HARNESS.md) — harness eval program layer
- [DECISIONS.md](DECISIONS.md) ADR-040
- `.context/templates/eval-output.md`
- `.context/templates/methodology-approach.md`
