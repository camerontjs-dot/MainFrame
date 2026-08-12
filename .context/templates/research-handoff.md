---
title: "Research handoff — <kind> — <lane> → <project>"
domain: "<project-domain or knowledge-systems>"
type: "project"
status: "active"
handoff_kind: "gate|application|opportunity|constraint|experiment|craft|knowledge|split|close"
from_lane: "<lane-slug>"
to_project: "<project-slug>"
urgency: "high|medium|low"
next_loop: "none|implement|craft|experiment|operator|archive|intake"
updated: "YYYY-MM-DD"
source: "bin/research-lane-loop handoff-project"
tags: ["research-handoff", "handoff"]
---

# Research handoff — <kind>

## Decision or signal (one sentence)

<What should change, be decided, tried, measured, avoided, or remembered?>

## Kind

| Field | Value |
|-------|-------|
| kind | |
| urgency | |
| next_loop | |
| from_lane | |
| to_project | |

## Evidence

- `10_knowledge/...` (synthesis or raw)
- (optional) prior craft/experiment path

## Does not mean

- <Negative boundary: e.g. not a full rewrite, not archive, not promotion>

## Project routing

- [ ] `next_action` updated (gate/application/experiment/craft only when appropriate)
- [ ] `log.md` entry
- [ ] `decisions.md` or ideas/ (constraint/opportunity)
- [ ] No steal of active WIP (opportunity)

## Lane routing

- [ ] Lane log entry
- [ ] Phase / stop-condition note if application or close
- [ ] Archive only if kind=close and operator accepts
