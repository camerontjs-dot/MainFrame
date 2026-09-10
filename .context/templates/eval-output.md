---
title: "<Eval report title>"
domain: "<project-domain>"
type: "lab-report"
status: "active"
study_type: "exploratory"
lab_report_id: "YYYY-MM-DD-<slug>"
eval_run_id: "YYYY-MM-DD-<slug>"
protocol_ref: "plans/<file>.yaml@<git-short-sha>"
decision_sentence: "<What changes if positive / negative / inconclusive?>"
hypothesis: "<Expected before outcomes, or descriptive-only>"
disposition: "open"
project: "<project-slug>"
tags: ["evaluation", "eval-registry", "lab-report"]
updated: "YYYY-MM-DD"
source: "local"
---

<!--
  This file is the eval-registry specialization of the universal lab-report
  convention (.context/templates/lab-report.md). Prefer bin/lab-report scaffold
  for new work; keep the metric extract block for harvest.
-->

# <Title> — YYYY-MM-DD

## Boundary

- Scope, DB/path, what this run does **not** claim.

## Decision sentence

<Repeat from frontmatter for human scan.>

## Hypothesis

<Expected before outcomes.>

## Inputs

| Field | Value |
|-------|-------|
| study_type | exploratory |
| protocol_ref | … |
| unit_of_analysis | |
| primary metric | |
| raw artifacts | `raw-materials/<run-id>/` |

## Results

<Tables and findings. Label claim types if interpretive.>

## Irregularities

<Table or "None observed." Also mirrored under metric extract.>

## Counterevidence and limits

<What would falsify the read; known confounds.>

## Disposition

`open` | `accept` | `reject` | `hold` | `iterate` — and next experiment id if iterate.

## Metric extract (eval-registry)

```yaml
registry:
  project: <project-slug>
  run_id: YYYY-MM-DD-<slug>
  study_type: exploratory
  protocol_ref: plans/queries.yaml@HEAD
  date: YYYY-MM-DD
  decision_sentence: "<one sentence>"
  artifact_path: outputs/YYYY-MM-DD-<slug>.md
  raw_path: raw-materials/YYYY-MM-DD-<slug>/
  environment:
    git_sha: null
    harness_version: null
  decision_use: regression_only
  prior_baseline_ref: outputs/YYYY-MM-DD-prior.md
metrics:
  - name: <metric_name>
    slice: <slice_id>
    value: 0.0
    n: 0
    unit: ratio
    ci_lower: null
    ci_upper: null
irregularities:
  - id: <slug>
    severity: info
    category: other
    observation: "<what was odd>"
    context: "<why it might matter or not>"
    artifact_ref: "<path or null>"
    resolved: false
```

## Claims (epistemic pass)

| Statement | Type | Confidence |
|-----------|------|------------|
| … | observation / inference / hypothesis | high / moderate / low |