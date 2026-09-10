---
title: "MainFrame Operations"
domain: "knowledge-systems"
type: "lifecycle"
status: "active"
source: "public-export-transform"
tags: ["mainframe", "operations", "lifecycle"]
structural_type: "project-entry"
lifecycle_scope: "lifecycle"
owner_surface: "40_operations/"
authority: "operating-policy"
privacy: "public-safe"
volatility: "stable"
source_of_truth: true
update_rule: "replace-with-review"
verification:
  - "bin/contract-lint --file 40_operations/AGENTS.md"
related_surfaces:
  - "AGENTS.md"
  - "30_projects/AGENTS.md"
  - "DECISIONS.md"
do_not_use_for:
  - "automatic project migration or lifecycle classification"
  - "focus, health, approval, or completion authority"
---

# MainFrame Operations

`40_operations/` is the lifecycle home for standing control planes, recurring
programs, and management systems.

This public tree includes the operations-layer contracts and the portable
MainFrame Process Evaluation engine. Other admitted operation trees, raw
evidence, and local receipts remain local-only unless explicitly allowlisted.

The folder separates a continuing loop from a bounded project outcome; it
does not make any operation healthier, focused, approved, or exempt from
WIP limits.

## Scope and authority

This folder owns the coordination entrypoint for an admitted operation. Each
operation's own `README.md` is its direct authority for identity, lifecycle
state, goal, next action, classification, and WIP class. Existing ledgers,
receipts, schedules, external systems, and nested repositories remain their
own authorities. Local focus authority, when present, lives under
`local-only: 20_live/focus/`.

MindGraph is retrieval only: a result may nominate a coordination surface but
cannot establish lifecycle, WIP, focus, health, approval, or completion.

## Admission and identity

Admission of one operation does not migrate other projects automatically.
A recurring loop is not an operation merely because it repeats. Further
admission requires an explicitly reviewed decision.

An admitted operation uses a stable slug and direct `README.md`, with at
least these classification fields in addition to its lifecycle fields:

```yaml
record_type: operation
work_kind: control_plane | relationship_pipeline | research_program | evaluation_program | product_asset | experiment | external_coordinator
portfolio_role: primary | support | maintenance | waiting | parked
authority_mode: local_coordination | nested_repo | external_workspace
wip_class: product | eval | anchor
```

The slug is a cross-lifecycle identity. It must be unique across
`30_projects/` and `40_operations/`; two live copies, aliases, or symlinked
copies do not constitute a migration. Folder location never determines WIP,
focus, health, approval, or lifecycle state.

## Lifecycle semantics

Operations use explicit lifecycle states rather than the fact that a recurring
cycle exists. `active` requires an explicit next action and current evidence;
`paused`, `blocked`, and `suspended` state the different ways a loop is not
running; `planned` names its activation gate. An operation is not `shipped`
because one cycle finished.

`wip_class` remains orthogonal to folder location.

## Update discipline

Keep durable local rules in [AGENTS.md](AGENTS.md). Put status and cycle
history in admitted operation records or their append-only ledgers, and record
accepted architecture changes in root [DECISIONS.md](../DECISIONS.md). Do not
place secrets, unrelated raw evidence, mailbox content, or generated
projections here.
