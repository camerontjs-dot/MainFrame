---
title: "Loop Eval Workstation"
domain: "knowledge-systems"
type: "workbench"
status: "active"
project: "mainframe-process-eval"
updated: "2026-07-23"
tags: ["loop-eval", "catalogue", "process-eval"]
---

# Loop Eval Workstation

Mini evaluation workbench inside **mainframe-process-eval** for cataloguing
MainFrame loops, underspecified “loop-shaped” processes, and promotion
candidates — plus thresholds and automated checks.

## Layout

```text
workbench/loop-eval/
  README.md                 ← you are here
  THRESHOLDS.md             ← promotion bar + testing system
  schema/loop-entry.schema.json
  catalogue/
    entries.json            ← machine authority (tests read this)
    entries.yaml            ← twin for editors
    INDEX.md                ← human summary
    01-well-defined.md
    02-underspecified.md
    03-promotion-candidates.md
  compositions/
    README.md               ← bigger programs that chain loops
  scripts/
    score_catalogue.py      ← score + tier consistency (also used by tests)
```

## Three catalogue tiers

| Tier | File | Meaning |
|------|------|---------|
| **A — well-defined** | `01-well-defined.md` | First-class loops meeting the threshold |
| **B — underspecified** | `02-underspecified.md` | Named or used as loops but missing contract pieces |
| **C — promotion candidates** | `03-promotion-candidates.md` | Repeated workflows/processes that *could* become loops |

Compositions (e.g. source → archive) are **not** a fourth loop type; see
`compositions/`.

## Operator commands

```bash
# Score + tier consistency (exit 1 on violations)
python3 40_operations/mainframe-process-eval/workbench/loop-eval/scripts/score_catalogue.py

# Same checks via unittest (repo root)
python3 -m unittest tests.test_loop_catalogue -v
```

## How to add or reclassify an entry

1. Edit `catalogue/entries.json` (source of truth for tests).
2. Optionally sync `entries.yaml` via PyYAML for readability.
3. Fill checklist booleans honestly; do not invent surfaces.
4. Run `score_catalogue.py` — checks score/tier/surface/edge rules.
5. Update tier markdown + INDEX when classifications change.
6. Log a one-line note in project `log.md` when tier changes.

## Relationship to durable docs

| Surface | Role |
|---------|------|
| This workbench | Lab: inventory, scores, promotion experiments |
| `.context/loops/` (later) | Promoted durable catalogue for all agents |
| `improvement-backlog/items.md` | MPE/LOOP backlog items when action is selected |

## Non-goals

- Do not invent a fourth first-class “meta-loop” (see three-loop gaps 2026-07-13).
- Do not promote from a single attractive observation (methodology G45).
- Do not copy prompts or private telemetry into catalogue files.
