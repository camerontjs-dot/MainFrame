---
title: "Live surface retention and index hygiene"
domain: "knowledge-systems"
type: "note"
status: "active"
updated: "2026-07-15"
source: "ADR-045; process-eval program after Phase 2"
tags: ["20_live", "retention", "mindgraph", "hygiene"]
---

# Live surface retention and index hygiene

Policy for volatile MainFrame state. Complements `20_live/AGENTS.md` (no silent
overwrite) and ADR-045. **Does not** authorize bulk deletion of history.

## Goals

1. Keep **MindGraph projects index** useful: coordination Markdown only, full
   intended coverage, rebuildable, no telemetry firehose.
2. Keep **`20_live/`** honest: different classes age differently; derived
   projections may be wiped; append-only evidence is capped/archived, not
   silently rewritten.
3. Never treat “clean” as “delete until green.”

## Retention classes

| Class | Examples | Default rule | MindGraph? |
|-------|----------|--------------|------------|
| **A — Authority** | `20_live/focus/current.yaml`, SEC dispositions, operator cards | Keep; revise with review; cite revision | No (focus is session/doctor authority, not corpus) |
| **B — Append-only evidence** | `eval-registry/*.jsonl`, focus `decisions.jsonl` / `outcomes.jsonl`, workflow-metrics event days | Append only; **archive or compress** after soft age (see caps); never rewrite lines | No |
| **C — Derived projection** | `workstation.sqlite`, session-close feeds, staged MindGraph DBs under `~/.mindgraph/staging/` | Rebuildable; wipe/replace OK when receipt exists | No (DB is the projection) |
| **D — Reporter / schedule noise** | Many `*-scheduled-weekly.md` under process-eval, large trend dumps | Keep last **N** hot; older stay on disk or move to project archive; optional exclude from index globs later | Optional: only if under `outputs/**` and still useful for status |
| **E — High-volume ops** | `workflow-metrics/events/`, markets DBs | Size/age caps; cold days off hot path; not knowledge | **Never** into projects or knowledge index |

## Soft caps (operator defaults — not auto-enforced yet)

| Surface | Soft cap | Action when exceeded |
|---------|----------|----------------------|
| Eval schedule jsonl | 24 months hot | Archive older segments to `90_archive/` or compress beside file |
| Workflow event day files | 90 days hot detail | Compress or move cold days; keep chain receipts if any |
| Workstation projection DB | rebuild anytime | Prefer refuse bad seed (Unit 2.3/2.4) over partial edit |
| Process-eval scheduled outputs | last 12 weeklies hot | Older remain files but need not drive attention |
| MindGraph staging DBs | 3 newest under `~/.mindgraph/staging/` | Delete older stage DBs after promote or abandon |

Automation of caps is a later unit. This file is the **policy authority**.

## Projects MindGraph (separate from 20_live cleanup)

| Rule | Detail |
|------|--------|
| Default (lean) | `30_projects/mindgraph-projects.json` — README, log, decisions, methodology, plans; **excludes outputs/** |
| Deep | `30_projects/mindgraph-projects-deep.json` or `--deep` — adds `outputs/**` for archaeology |
| Out of scope | `20_live/**` telemetry, workbenches, raw-materials, secrets |
| Mutation | Explicit staged apply: **plan → stage (temp DB) → promote** |
| Command | `bin/mindgraph-projects-apply` [ `--deep` ] |
| Success | Manifest namespaces ⊆ staged DB; no missing intended project dirs; receipt written |
| Re-stage | See HARNESS.md “When to re-stage the projects index” |

Installed path remains `~/.mindgraph/mainframe-projects.sqlite`. Promote always
backs up the previous file first. Prefer lean for daily agent context; deep only
when hunting old eval receipts or FINDINGS.

## What “manage staleness” means here

| Stale kind | Response |
|------------|----------|
| Project README/plan changed | Re-stage/promote projects index (or accept lag until next apply) |
| Focus review_by past | Doctor AUTH stale/warn; rewrite focus authority |
| Eval schedule without launchd provenance | SCHED degraded (Unit 2.4) |
| Telemetry volume | Cap class E; do not index |
| Workstation shows old seeded tasks | Rebuild class C projection; do not “fix” by editing jsonl |

## Related

- ADR-045
- `HARNESS.md` dual MindGraph trust profiles
- `bin/mindgraph-projects-apply`
- `20_live/AGENTS.md`
