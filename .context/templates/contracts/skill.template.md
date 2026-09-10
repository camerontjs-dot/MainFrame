---
name: <kebab-case-name>
description: "Use when <task keywords front-loaded>. Covers <X, Y, Z>. Not for <negative boundary>."
---

# <Skill name>

<One paragraph: the judgement this skill encodes, and why an agent would get it
wrong without the skill. If the answer is "it would just be slower", this is a
workflow, not a skill.>

## When this applies

- <trigger phrasing an agent will actually encounter>
- <...>

## When it does not

- <the nearest neighbouring skill, and why this is not it>
- <...>

## Procedure

1. <Imperative step.>
2. <...>

## Rules

### 1. <Rule as one imperative sentence.>

> **Binds:** any agent applying this skill
> **Tier:** T1 (detected)
> **Check:** `bin/skill-eval` <case or lint rule>
> **Escape:** <the compliant alternative — say plainly it carries no penalty>

## Happy path

<One worked example, end to end. Required by contract-audit 5.6.>

## Edge case

<One case that looks like the happy path and is not, with the correct handling.
Required by contract-audit 5.6.>

## Verification

<How a reviewer checks the skill was applied correctly, as a command or a
falsifiable observation.>

<!--
TEMPLATE NOTES — delete before saving.

DESCRIPTION FIELD (contract-audit 5.3): front-load task keywords, then state a
negative boundary. This string is the whole trigger mechanism — an agent that
never loads the skill gets none of its judgement.

LENGTH (5.4): long content goes in references/, not in SKILL.md. If this file
grows past roughly 200 lines, split it:
  <skill>/SKILL.md
  <skill>/references/<topic>.md

SCRIPTS (5.5): skill scripts do deterministic helper work only. A script that
makes the judgement has replaced the skill.

Verify with: bin/contract-lint --file <this file>
-->
