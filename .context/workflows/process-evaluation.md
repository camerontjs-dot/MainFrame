# MainFrame Process Evaluation Workflow

Use this workflow to evaluate a MainFrame process before changing it. The goal
is to measure current behavior, identify the smallest useful improvement, and
rerun the same evaluation after the change.

Eval-profile binding: [EVAL_METHODOLOGY.md](../../EVAL_METHODOLOGY.md). The
longer eval-methodology workflow is an optional/deferred component and is
not required for this public-core slice. Process evals use `study_type:
observational`. Every `outputs/YYYY-MM-DD-evaluation.md` requires metric extract,
`irregularities`, and `bin/eval-registry harvest`.

## CLI

```bash
bin/process-eval preflight          # standard non-mutating check pack
bin/process-eval status             # project + latest output pointers
bin/process-eval close [--write]    # loop-decision scaffold
```

Owner operation: `40_operations/mainframe-process-eval/`.
Loop catalogue: `40_operations/mainframe-process-eval/workbench/loop-eval/`.
Root command: `bin/process-eval` (shim; implementation is operation-owned).

## Loop unit

| Field | Rule |
|-------|------|
| Unit | One observational pass: question → baseline → checks → samples → ≤2 slices → rerun → output |
| Entry | Cadence (≈1 week / 5 sessions), post-change verification, or operator request |
| Exit | Dated output harvested; loop decision recorded (`bin/process-eval close`) |

## Evaluation Loop

1. Write one evaluation question.
   - Good: "Does the ingest path move supported captures forward without
     losing provenance or creating avoidable manual work?"
   - Avoid: "Is MainFrame good?"
2. Capture a baseline before editing files.
3. Run the relevant deterministic checks:

   ```bash
   python3 -m unittest discover -s tests
   bin/ingest-minion run --dry-run
   bin/mindgraph-refresh --dry-run
   bin/sync-project-index --check
   bin/session-open --json
   bin/session-close --check
   bin/eval-schedule check
   bin/workflow-report --days 7 --json
   ```

Scheduled regression (ADR-036): `bin/eval-schedule run --cadence weekly` and
`20_live/eval-registry/OPERATOR.md` for the standing review ritual.

4. Sample real outcomes. For each evaluated workflow, inspect at least three
   representative cases when available:
   - a normal case;
   - a boundary or ambiguous case;
   - a known failure or high-friction case.
5. Score the process on:
   - correctness and safety;
   - provenance and reversibility;
   - throughput and backlog;
   - operator friction;
   - observability;
   - handoff and reentry quality.
6. Classify each finding:
   - `code-defect`: implementation does not match the contract;
   - `process-gap`: the contract lacks a needed step or boundary;
   - `adoption-gap`: a sound workflow exists but is not being used;
   - `telemetry-gap`: current signals cannot support the conclusion;
   - `intentional-backlog`: queued work is expected and should not be treated
     as a defect.
7. Select one or two improvement slices. Prefer changes that make future
   evaluation easier or remove repeated friction without weakening safety.
8. Apply the change, then rerun the same checks and samples
   (`bin/process-eval preflight`).
9. Save the baseline, change, rerun result, and next action in a dated project
   output. Record accepted architecture or workflow changes in `DECISIONS.md`.
10. **Close the pass** with an explicit loop decision:
    ```bash
    bin/process-eval close --run-id YYYY-MM-DD-… --question "…" --write
    ```
    Choices: `same_slice` | `new_question` | `promote_pattern` | `park` | `handoff`.
11. Harvest: `bin/eval-registry harvest` (project mainframe-process-eval).

## Action surface

- Dated files under `local-only: 40_operations/mainframe-process-eval/outputs/`
- `improvement-backlog/items.md` for nominations
- Optional loop-eval catalogue re-score when process taxonomy changes
- `bin/mainframe-doctor` and `bin/eval-schedule check` remain adjacent health tools

## Promotion Test

When a repeated pattern appears during evaluation, place it at the right layer:

| Pattern | Destination |
| --- | --- |
| Fixed, deterministic operation | `bin/` script with tests |
| Operator-driven sequence using existing tools | `.context/workflows/` |
| Repeated agent judgment, domain rules, or tool strategy | `.agents/skills/` |
| Role with its own tools, guardrails, and procedure | `agents/` subagent |
| One-project experiment or uncertain practice | `30_projects/<slug>/` |

Prefer improving an existing workflow or skill over creating a near-duplicate.
Promote a new skill only when there are concrete trigger examples, repeated
judgment that general models would otherwise rediscover, and a way to evaluate
the skill against representative outputs.

## Guardrails

- Tool-call success is not task success.
- Speed is not the only quality measure.
- Do not treat inbox or queue size alone as a failure; separate expected
  migration backlog from stuck work.
- Keep telemetry metadata-only. Do not add prompts, file contents, command
  output, or model responses to workflow logs.
- Preserve raw evidence and baseline artifacts before changing the process.
- Do not tune against one convenient example. Keep boundary and failure cases.
