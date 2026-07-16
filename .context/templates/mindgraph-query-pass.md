---
title: "MindGraph Query Pass template"
domain: "knowledge-systems"
type: "template"
status: "active"
source: "ADR-030, ADR-032, MH01 first-contact protocol"
tags: ["mindgraph", "query-pass", "template", "planning"]
updated: "2026-07-13"
---

# MindGraph Query Pass template

Copy into **task packets**, **project plans**, **session handoffs**, and **create-project** logs.
Do **not** blend knowledge and project nominations. Nominations are not verification.

## Preflight (10 seconds)

```bash
bin/mindgraph doctor          # dual ~/.mindgraph indexes + stub warnings
# then dual query:
bin/mindgraph query "KNOWLEDGE QUESTION" --db ~/.mindgraph/mainframe.sqlite --json --top-k 6
bin/mindgraph query "PROJECTS QUESTION" --db ~/.mindgraph/mainframe-projects.sqlite --json --top-k 6
```

## Block (paste as `## MindGraph Query Pass`)

```markdown
## MindGraph Query Pass

- **intent:** <one sentence decision this retrieval supports>
- **doctor:** ok | fail (paste overall line from `bin/mindgraph doctor`)
- **knowledge_query:** `<exact string used against mainframe.sqlite>`
- **projects_query:** `<exact string used against mainframe-projects.sqlite>`

### knowledge (trust: durable_knowledge)

| path | why nominated | weak_fit? |
|------|---------------|-----------|
| `10_knowledge/…` | … | no |

### projects (trust: project_status)

| path | why nominated | weak_fit? |
|------|---------------|-----------|
| `30_projects/…` | … | no |

### weak_or_excluded

- …

### source_inspection_required

- …

### do_not_merge_without_trust_labels: true
```

## Minimal YAML-style variant (plans / logs)

```markdown
## MindGraph Query Pass
intent:
doctor:
knowledge_query:
projects_query:
knowledge_nominations:
- title: ...
  path: ...
  reason: ...
project_nominations:
- title: ...
  path: ...
  reason: ...
weak_or_excluded:
- ...
source_inspection_required:
- ...
```

## Rules

1. Authoritative DBs are under `~/.mindgraph/` — never workspace-root stub `mainframe*.sqlite`.
2. Keep the two result groups labeled; never one blended ranking.
3. If doctor fails, stop and refresh (`bin/mindgraph-refresh` / `bin/mindgraph-refresh-projects`) before planning.
4. For task packets: set `mindgraph_mode: "curated"` and list `knowledge_queries` when the packet depends on vault context; fill this section after the dual query.
