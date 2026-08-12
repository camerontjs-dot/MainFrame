---
name: craft-research-loop
description: >
  Run product/craft trial-and-error research with finishable FINDINGS, proof-index
  discipline, and project-local action cards. Use for image-lab bake-offs, stack
  trials, integration prototypes, and "what works for us" questions. Do NOT use
  for literature capture (research-lane-loop), system eval metrics
  (project-experiment-loop), or pure unit tests.
status: implemented
---

# craft-research-loop

## Purpose

Orchestrate **one craft trial** for a product/workbench project:

```text
question → scaffold → run → FINDINGS (keep|kill|iterate) → proof index → next_action
```

Operator workflow: `.context/workflows/craft-research-loop.md`.

## Inputs

- Project slug under `30_projects/`
- One primary question + decision sentence
- Optional: existing trial folder to close

## Outputs

- `outputs/YYYY-MM-DD-<slug>/TRIAL.md` (+ FINDINGS at close)
- Updated `outputs/RESEARCH_PROOF_INDEX.md` (or project proof index)
- `log.md` entry + README `next_action`
- `outputs/LAST_CRAFT_ACTION.md`

## Procedure

Follow the workflow steps **0–6**. Use CLI:

```bash
bin/craft-research-loop preflight --project <slug>
bin/craft-research-loop scaffold --project <slug> --question "..." --decision "..." --slug "..."
bin/craft-research-loop close --project <slug> --trial <id> --verdict keep|kill|iterate --findings "..."
bin/craft-research-loop triage --project <slug>
bin/craft-research-loop promote --project <slug> --trial <id> --to knowledge|experiment|lane
```

### Judgment rules

1. **One question per trial.** Split multi-axis matrices into a primary criterion + secondary notes.
2. **Criteria before beauty.** Do not set success thresholds after picking a favorite image/run.
3. **Close is mandatory.** No open-ended generate loops without FINDINGS + next_action.
4. **Proof index is the memory.** Cull ephemera; keep only paths that still prove a disposition.
5. **Do not default to eval-registry.** Promote to experiment-loop only for decision-bearing metrics.
6. **Do not trap durable knowledge** in `outputs/` — extract or lane when the lesson is domain-wide.
7. **Action is project-local** (`LAST_CRAFT_ACTION.md`), never mixed into `last-eval-action.md`.

## Guardrails

- Tracker vs knowledge: craft outputs are project evidence, not `10_knowledge/` until extract/ingest.
- Failed runs stay until explicitly culled with reason.
- Nested workbench commits are fine; MainFrame coordination still uses project README/log/decisions.

## Related

- `.context/workflows/craft-research-loop.md`
- `.context/templates/craft-trial.md`
- research-lane-loop, project-experiment-loop
- Reference implementation: `30_projects/image-generation-lab/outputs/RESEARCH_PROOF_INDEX.md`
