---
title: "Lab report — <short title>"
domain: "<project-domain>"
type: "lab-report"
status: "running"
lab_report_id: "YYYY-MM-DD-<slug>"
project: "<project-slug>"
study_type: "exploratory"
protocol_ref: "<path@rev or harness/version pin>"
decision_sentence: "<What changes if positive / negative / inconclusive?>"
hypothesis: "<Expected result before looking at outcomes>"
primary_metric: "<name>"
unit_of_analysis: "<case | run | cell | session | query | …>"
disposition: "open"
privacy: "private-local"
tags: ["lab-report", "experiment"]
updated: "YYYY-MM-DD"
source: "local"
---

# Lab report — <short title>

**ID:** `YYYY-MM-DD-<slug>`
**Project:** `<project-slug>`
**Study type:** exploratory | confirmatory | regression | observational | calibration
**Disposition:** `open` | `accept` | `reject` | `hold` | `iterate`

---

## 1. Question

One primary experimental question. Split multi-axis work into separate reports.

## 2. Decision this report supports

One sentence (mirror frontmatter `decision_sentence`).

> If ___, then we will ___. If not, we will ___. If inconclusive, we will ___.

## 3. Hypothesis

State the expected result **before** inspecting outcomes.

## 4. Background / prior art (optional)

Pointers only: prior `lab_report_id`, protocol notes, literature, capability cards.

## 5. Materials and methods

### 5.1 System under test

| Field | Value |
|-------|-------|
| Stack / models | |
| Harness / tools | |
| Code / config pin | `protocol_ref` |
| Hardware / host constraints | |

### 5.2 Design

| Field | Value |
|-------|-------|
| study_type | |
| unit_of_analysis | |
| primary metric | |
| secondary metrics | (never blended into primary) |
| n / replicates | |
| factors (independent) | **one primary factor per phase** |
| controlled / held fixed | |
| randomization / seeds | |
| blinding / sealing | sealed fixtures? public demo split? |

### 5.3 Procedure

1. Preflight (doctor, disk, memory, protocol pin).
2. Execute (commands or matrix).
3. Score (external verifier / auto scorer / human gate).
4. Write this report + link raw paths.

```bash
# Record exact commands run (copy/paste):

```

## 6. Results

Facts and tables only. No promotion language here.

| Cell / condition | n | Primary metric | Secondary | Notes |
|------------------|---:|---------------:|----------:|-------|

### Raw artifacts

| Kind | Path |
|------|------|
| receipts / logs | `raw-materials/<lab_report_id>/` or project convention |
| machine scorecards | |
| human grades | |

## 7. Irregularities and anomalies

Track everything odd even if "irrelevant" to the headline. Use `[]` only if none observed.

| id | severity | category | observation | artifact_ref | resolved |
|----|----------|----------|-------------|--------------|----------|
| | info \| warn \| high | protocol \| tooling \| data \| other | | | false |

## 8. Interpretation

Label each claim:

| Statement | Type | Confidence |
|-----------|------|------------|
| | observation / inference / hypothesis | high / moderate / low |

## 9. Limitations / what this does **not** prove

- Small n, confounds, ceiling effects, non-transfer, DEV-only, exploratory label, etc.

## 10. Disposition and next experiment

| Field | Value |
|-------|-------|
| disposition | open / accept / reject / hold / iterate |
| why | |
| next_experiment | new `lab_report_id` question, or "none" |
| registry harvest? | yes if decision-bearing eval metrics |

## 11. Metric extract (eval-registry)

Required when the run is decision-bearing for eval-profile / promotion work. Omit only for pure craft trials (then use craft FINDINGS) or pure unit-test CI.

```yaml
registry:
  project: <project-slug>
  run_id: YYYY-MM-DD-<slug>
  study_type: exploratory
  protocol_ref: <pin>
  date: YYYY-MM-DD
  decision_sentence: "<one sentence>"
  artifact_path: outputs/lab-reports/YYYY-MM-DD-<slug>.md
  raw_path: raw-materials/YYYY-MM-DD-<slug>/
  decision_use: exploratory_only
metrics:
  - name: <metric>
    slice: <slice>
    value: 0
    n: 0
    unit: count
irregularities: []
```

## 12. Provenance

| Field | Value |
|-------|-------|
| operator / agent | |
| started | |
| finished | |
| git_sha (if known) | |
| privacy | private-local \| public-safe staging |
| related reports | |
