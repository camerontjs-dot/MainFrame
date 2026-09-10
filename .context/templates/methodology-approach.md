---
title: "Methodology approach — read first in new session"
domain: "<project-domain>"
type: "note"
status: "active"
source: "EVAL_METHODOLOGY.md eval-profile template"
tags: ["methodology", "handoff", "eval-profile", "eval-planning"]
study_type: null
eval_run_id: null
updated: "YYYY-MM-DD"
---

# ⚠️ Methodology approach — <Project Name>

**New session:** Read this before any eval run, output write, or promotion claim.

**Contracts:** [EVAL_METHODOLOGY.md](../../EVAL_METHODOLOGY.md). Optional/deferred: a longer eval-methodology workflow if installed locally.

## Eval profile

| Field | Value |
|-------|-------|
| **Strict profile** | yes |
| **Study types used** | exploratory / regression / confirmatory / observational / calibration |
| **Primary decision** | <what promotion or change this eval supports> |
| **Current blocker** | <calibration / hold-out / H2 / none> |

## Do in order

1. <project-specific sequence>
2. Write `outputs/` with [.context/templates/eval-output.md](../../.context/templates/eval-output.md)
3. `bin/eval-registry harvest` then `bin/eval-registry check --strict`

## Do not

- Run unlabeled study_type
- Omit metric extract or `irregularities` (use `[]` only after explicit scan)
- Promote from exploratory alone
- State confirmatory conclusions before blockers clear

## Knowledge

- `10_knowledge/knowledge-systems/methodology/` — design, sample size, trends, irregularities
- Project `methodology-approach.md` sections below — living posture

## Living posture

(Update after each eval cycle.)

| Date | eval_run_id | study_type | Headline | Open irregularities |
|------|-------------|------------|----------|---------------------|
| — | — | — | — | — |