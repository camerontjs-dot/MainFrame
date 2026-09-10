---
title: "MainFrame Process Evaluation"
domain: "knowledge-systems"
type: operation
status: "active"
record_type: operation
work_kind: "evaluation_program"
portfolio_role: "maintenance"
authority_mode: "local_coordination"
wip_class: "eval"
goal: "Evaluate MainFrame operating processes with repeatable baselines without publishing private evidence."
updated: "2026-09-10"
source: "public-export-transform"
tags: ["mainframe", "evaluation", "synthetic"]
---

# MainFrame Process Evaluation

This admitted operation is the portable self-evaluation engine for MainFrame.

There is no standalone GitHub owner. Generic lifecycle substrate remains
MainFrame-owned. Raw evaluation evidence is local-only. Git does not contain
complete evaluation history.

## Portable implementation

- [`src/`](src/) — evaluator CLI implementation
- [`tests/`](tests/) — portable engine tests
- [`methodology/methodology-approach.md`](methodology/methodology-approach.md)
- [`workbench/loop-eval/`](workbench/loop-eval/) — schema and scorer

`bin/process-eval` is a repository-level shim that delegates here.

## Local-only evidence

`local-only: outputs/`, `local-only: raw-materials/`, receipts, logs, and
campaign artefacts are not part of the public tree. Synthetic demos must be
labelled synthetic.

## What this public surface is not

It is not a report of any private MainFrame's quality. It does not include
private migration archaeology.
