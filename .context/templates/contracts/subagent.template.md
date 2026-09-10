---
name: <subagent-name>
role: "<one line — the specialized job>"
status: "active"
updated: "<YYYY-MM-DD>"
---

# <Subagent name>

<One paragraph: what this role is for, and what it deliberately does not do.>

## Tools

| Tool | Why this role needs it |
| --- | --- |
| <tool> | <reason> |

**Denied:** <tools this role must not have, and why. An unstated denial is not
a boundary.>

## Guardrails

### 1. <Rule as one imperative sentence.>

> **Binds:** this subagent
> **Tier:** T2 (blocked)
> **Check:** <tool allowlist, hook, or harness config that enforces it>
> **Escape:** <hand back to the caller with a named blocked status>

### 2. <Scope boundary — what it may read and write.>

> **Binds:** this subagent
> **Tier:** T1 (detected)
> **Check:** scope diff in the run receipt
> **Escape:** <alternative>

## Procedure

1. <Imperative step.>
2. <...>

## Handoff

**Returns:** <the distilled summary shape — fields, not raw output. Contract-audit
6.3: subagents return distilled summaries, not raw noise.>

**Blocked status:** <the exact shape of an honest "I could not do this". A role
with no way to report failure will report success.>

## Verification

<How the caller checks the work, independent of what the subagent claims.>

<!--
TEMPLATE NOTES — delete before saving.

A subagent is a ROLE (tools, guardrails, handoff shape). A repeatable procedure
belongs in a skill and is referenced from here, not restated (contract-audit 6.2).

Write-heavy parallel subagents need conflict controls (6.4): name the worktree,
lock, or disjoint path set that keeps two instances from colliding.

Verify with: bin/contract-lint --file <this file>
-->
