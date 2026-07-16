# MainFrame architecture (public overview)

MainFrame is a **lifecycle-first personal knowledge OS** implemented as a git-friendly file tree plus deterministic tools and agent contracts.

## Why lifecycle before topic

Topic folders alone mix capture chaos, durable synthesis, volatile dashboards, and multi-week projects under one update rule. MainFrame splits those modes so agents and humans know what may change, what must keep provenance, and what is merely temporary.

```text
capture → normalize → durable knowledge
                  ↘ live state
                  ↘ projects → (optional) extract back to knowledge
                  ↘ archive
```

## Public / private boundary

| Public (this tree) | Private (local only) |
| --- | --- |
| Lifecycle skeleton and templates | Inbox captures, knowledge domains, live telemetry |
| Contracts, workflows, public skills | Personal skill packs, career materials |
| Deterministic scripts and tests | Project workbenches and outcomes |
| Synthetic examples | Real corpora and indexes |

Generated indexes (`10_knowledge/index.md`, `30_projects/index.md`) stay local. Templates document shape without exposing inventory.

## Deterministic minions vs judgment

- **Minions** (`bin/*`): routing, status, index sync, telemetry append — dry-run first where possible.
- **Agents**: classification hard cases, synthesis, planning — constrained by `AGENTS.md` and skills.
- **Never**: treat retrieval or chat output as verification of claims.

## Retrieval pairing (Stage 2)

MindGraph is a separate local package that indexes markdown with lexical, semantic, and graph signals. When present:

- Durable knowledge and project context use **separate databases**
- Results carry trust labels; consumers must not merge without labeling
- Retrieval **nominates** context for inspection; it does not decide truth

Stage 1 documents the contracts and wrappers; Stage 2 ships the engine package.

## Observability pairing (Stage 3)

A pixel agent tracker projects **recorded** task/run/event state into a control-room UI. The office is not the source of truth. Stage 3 is optional demo packaging after security gates.

## Design principles

1. File tree is source of truth
2. Provenance over tidy rewrites
3. Append or snapshot volatile state
4. Allowlist what is public; clean history for publish artifacts
5. Graduate reusable lessons only through explicit extraction
