---
title: "Loop promotion thresholds and testing system"
domain: "knowledge-systems"
type: "workbench"
status: "active"
updated: "2026-07-23"
---

# Loop thresholds and testing system

## Checklist (10 binary criteria)

Every catalogue entry scores **0–10**. One point each:

| # | id | Criterion |
|---|-----|-----------|
| 1 | `unit_of_work` | One pass is named and bounded |
| 2 | `entry_exit` | Clear entry and exit conditions |
| 3 | `close_or_loop_decision` | Explicit close and/or next-loop decision |
| 4 | `workflow_contract` | Workflow file under `.context/workflows/` |
| 5 | `skill_or_agent_procedure` | Skill and/or subagent procedure exists |
| 6 | `bin_cli` | Deterministic CLI under `bin/` |
| 7 | `dogfood_evidence` | ≥1 dated dogfood / eval receipt (or scheduled automation proof) |
| 8 | `promotion_destinations` | Named destinations (knowledge, project, registry, archive, …) |
| 9 | `anti_scope` | Explicit does-not-own / when-not-to-use |
| 10 | `eval_or_action_surface` | Action card, registry, proof index, or equivalent |

## Tier thresholds

| Tier | Score | Extra gates |
|------|-------|-------------|
| **A — well_defined** | **≥ 8 / 10** | Must have `unit_of_work`, `entry_exit`, `workflow_contract`, and (`bin_cli` **or** `skill_or_agent_procedure`). Must have `dogfood_evidence`. |
| **B — underspecified** | **4–7** **or** named as a loop while failing A gates | Claims loop-shaped behavior but missing contract pieces. |
| **C — promotion candidate** | **any**, usually **3–7** | Not yet a loop; repeated operator/agent process with promotion potential. Track `repeat_signal` (low/medium/high). |

Reclassify when evidence changes — score is not permanent.

## Promotion bar (C → B or A)

A candidate may be **selected for implementation** only if **all** hold:

1. **Repeat threshold:** `repeat_signal: high` **or** ≥ **3** independent real uses documented **or** high-risk mandatory path (safety/provenance).
2. **Non-duplication:** does not re-implement an existing tier-A loop’s question (route there instead).
3. **Layer fit:** destination is clear (workflow vs skill vs bin vs composition-only).
4. **Evaluable cases:** success, boundary, and failure cases can be stated in one page.
5. **Test plan:** how we will know promotion worked (CLI preflight, unittest, dogfood receipt).
6. **Owner:** a project or lifecycle surface that will maintain it.

After implementation, re-score. **Promotion to tier A** requires meeting the tier-A table above, not just “we wrote a workflow.”

## Testing system

### Automated (every change to `entries.yaml`)

| Check | Tool |
|-------|------|
| Schema: required fields, enums, checklist keys | `tests/test_loop_catalogue.py` + JSON Schema |
| Score == count of true checklist items | `score_catalogue.py` |
| Tier consistent with score + A gates | `score_catalogue.py` |
| Surface paths that are set must exist on disk | `test_loop_catalogue.py` |
| Unique `id` | tests |

```bash
python3 -m unittest tests.test_loop_catalogue -v
python3 40_operations/mainframe-process-eval/workbench/loop-eval/scripts/score_catalogue.py
```

### Semi-automated / observational

| Check | Cadence |
|-------|---------|
| Dogfood receipt still valid (path exists, not contradicted) | when reclassifying |
| Composition edges resolve to catalogue ids | when editing compositions |
| No fourth first-class loop without ADR | process-eval decision |

### Manual gate (operator)

- Approve promotion implementation (≤2 active process-eval slices).
- Accept ADR only if durable `.context/loops/` catalogue is published.

## Composition rule (bigger “loops”)

Compositions chain tier-A/B loops and workflows. They:

- **do not** need a single mega-CLI on day one
- **must** list ordered stages and terminal conditions
- **must not** blur the three-loop questions (literature / measure / craft)

See `compositions/README.md`.
