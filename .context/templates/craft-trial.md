---
title: "Craft trial — <slug>"
domain: "<project-domain>"
type: "project"
status: "running"
craft_trial_id: "YYYY-MM-DD-<slug>"
project: "<project-slug>"
verdict: "open"
decision_sentence: "<What changes if keep / kill / iterate?>"
tags: ["craft-research", "trial"]
updated: "YYYY-MM-DD"
source: "local"
---

# Craft trial — <slug>

## Question

One primary question only.

## Decision this trial supports

One sentence (also in frontmatter `decision_sentence`).

## Hypothesis

State expected result **before** ranking outputs.

## Success criteria

Measurable / comparable thresholds set in advance.

## Fixed inputs

- assets:
- models / stack:
- hardware:
- software versions:

## Variables

- independent:
- controlled:
- observed:

## Procedure

1.
2.
3.

## Run table

| Run | Config | Result | Notes |
|-----|--------|--------|-------|

## Observations

Facts only.

## Interpretation

What observations may mean (labeled inference).

## Limitations

What this trial cannot establish.

## Verdict

`open` | `keep` | `kill` | `iterate`

### If keep
What default / decision is adopted?

### If kill
What anti-pattern is recorded?

### If iterate
What is the **next trial** question (new slug)?

## Promotion

- [ ] none (local product only)
- [ ] `decisions.md`
- [ ] extract-knowledge / research-lane-loop
- [ ] project-experiment-loop (single eval_run_id)
