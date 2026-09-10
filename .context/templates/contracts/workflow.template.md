---
title: "<Workflow name>"
domain: "<domain>"
type: "workflow"
status: "active"
updated: "<YYYY-MM-DD>"
tags: ["workflow"]
---

# <Workflow name>

**Trigger:** <the one condition that starts this. A workflow with no trigger is
a document nobody knows when to open — 18 of 42 workflows failed this on
2026-08-23.>

**Stop state:** <what "done" looks like, and what to do when it goes wrong.
Name the blocked state explicitly: "if X, stop and record Y".>

**Owner surface:** <path or project that owns updates to this file>

## When not to use this

<Negative boundary. The nearest neighbouring workflow and why this is not it.>

## Preflight

1. <Numbered, imperative, testable. Name the command.>
2. <...>

## Procedure

1. <Step. One action per step, with the exact command.>
2. <...>

## Rules

Rules that constrain how this workflow runs, rather than steps within it.
Omit this section if the procedure carries no normative weight.

### 1. <Rule as one imperative sentence.>

> **Binds:** anyone running this workflow
> **Tier:** T1 (detected)
> **Check:** `bin/<tool> --check`
> **Escape:** <the compliant alternative>

## Verification

<The deterministic command that proves the workflow ran and produced what it
claims. Not "review the output" — a command with an exit code.>

## Outputs

| Artifact | Path | Update rule |
| --- | --- | --- |
| <name> | `<path>` | append-only / replace-with-review / generated-only |

## Escape

<What to do when the workflow cannot complete. This is the workflow-level
honest-failure path: where to record the blocked state so a stall is visible
instead of silent.>

<!--
TEMPLATE NOTES — delete before saving.

Workflows are OPERATOR SEQUENCES. If the content is reusable agent judgement it
belongs in .agents/skills/; if it is a role it belongs in agents/; if it is
deterministic it belongs in bin/.

Do not duplicate skill bodies or project status here (contract-audit 4.5).

Every workflow needs a trigger (4.1) and a stop state. Verify with:
  bin/contract-lint --file <this file>
-->
