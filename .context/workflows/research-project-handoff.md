---
title: "Research ↔ project handoff"
domain: "knowledge-systems"
type: "workflow"
status: "active"
structural_type: workflow
lifecycle_scope: root
owner_surface: ".context/workflows/research-project-handoff.md"
authority: workflow-contract
volatility: stable
updated: "2026-07-13"
tags: ["research-lane", "handoff", "projects", "workflow"]
---

# Research ↔ project handoff

## Purpose

Move value **out of a research lane** into a **project surface** without collapsing every signal into the same `next_action` rewrite.

Handoff is **not** “more literature.” It is a typed packet that answers:

> Who should care, how hard, and what loop runs next?

## Scope and authority

- **From:** `30_projects/research-lanes-strategy/lanes/` (+ durable notes under `10_knowledge/`)
- **To:** one `30_projects/<slug>/` (or explicit multi-consumer list in the receipt)
- **Does not replace:** research-lane-loop (literature), craft-research-loop, project-experiment-loop, or `lane-intake archive`
- **Does not mean:** auto-code, auto-archive, or silent promotion of claims

Related: `.context/workflows/research-lane-loop.md` (step 7), `craft-research-loop.md`, `project-experiment-loop.md`.

## When to hand off

Use a handoff when literature (or synthesis) changes what a **project** should do, decide, try, measure, or avoid — and continuing the same literature pass would only add footnotes.

Do **not** hand off when:

- You still need 3–4 sources for the **current phase** stop condition
- The “target” is only “me someday” with no project slug
- You are dumping unprocessed inbox stubs (finish ingest/synthesis first)

## Handoff kinds (taxonomy)

Kinds are the core of this workflow. Pick **one primary kind** per handoff. Secondary tags optional in the receipt.

| Kind | Intent | Urgency | Typical destination behavior |
|------|--------|---------|------------------------------|
| **`gate`** | Literature (or stop-condition) **clears or blocks a project decision gate** — go / no-go / promotion / protocol freeze | High | Set or replace project `next_action` with the gate decision + evidence links |
| **`application`** | Planned **build/use** work that was always the lane’s application phase (checklist, wiring, product default) | High–medium | Primary `next_action` for implementation or craft scaffold |
| **`opportunity`** | Something **interesting** related to a project — try, consider, or queue when WIP allows | Low | Log + optional ideas card; **do not steal** primary `next_action` unless project is idle |
| **`constraint`** | Bound future work: don’t do X without Y; failure mode; compliance/risk | Medium | Append to project `decisions.md` or README risks; may demote a planned path |
| **`experiment`** | Ready for a **measured** decision (protocol, metric, eval_run_id) | Medium–high | Point at `project-experiment-loop scaffold` (or canary/matrix) |
| **`craft`** | Ready for product **trial-and-error** (bake-off, stack trial, prototype) | Medium | Point at `craft-research-loop scaffold` with one question |
| **`knowledge`** | Durable lesson for the vault; project is only a **consumer**, not the worker | Low | Ensure note is in `10_knowledge/`; project log cites path; no forced `next_action` |
| **`split`** | Signal is really a **new research question** | Medium | `## Research Lane Candidate` + `bin/lane-intake scan` — not a project implement task |
| **`close`** | **Lane** stop condition met; consumers notified before/alongside archive | Portfolio | Handoff block on lane README + archive micro-loop |

### How to choose (quick rules)

1. **Does a decision wait on this?** → `gate`
2. **Was this always “phase = application” on the lane card?** → `application`
3. **Must we measure before changing process/product?** → `experiment`
4. **Must we try settings/stack before claiming “what works”?** → `craft`
5. **Is it a hard bound or anti-pattern?** → `constraint`
6. **Nice to explore if capacity exists?** → `opportunity`
7. **Wrong project; needs its own literature thread?** → `split`
8. **Lane finished for real?** → `close` (+ archive when operator agrees)

If two apply, pick the **highest urgency that changes a decision**. Put the other as a secondary note in the receipt.

## Other situations (explicit)

| Situation | Kind | Notes |
|-----------|------|--------|
| Eval promotion blocked on missing literature | `gate` or `experiment` | Cite protocol_ref / irregularity id |
| Canary green; optional product bake-off | `craft` or `opportunity` | Don’t inflate severity |
| Found competitor/stack pattern mid-build | `opportunity` or `constraint` | Don’t restart whole lane unless decision depends on it |
| Multi-project consumer (e.g. G43 methodology) | `knowledge` + optional multi-`to` list | One primary project still owns the receipt |
| Project discovers a knowledge gap while building | **Reverse handoff** → research-lane-loop / intake | See “Inbound” below |
| Side question during source-literature | `split` | Don’t bury in project next_action |

## Inbound (project → research)

Handoff is bidirectional in spirit:

```text
project friction / unknown
  → research-lane-loop (existing lane) or research-lane-intake (new)
  → later: outbound handoff back to project
```

Do not use `handoff-project` for inbound gaps. Use lane intake or a lane preflight resume class A/B.

## Procedure (outbound)

### 0. Preflight

```bash
bin/research-lane-loop preflight --slug <lane>
# Prefer blocker=project, or explicit stop-condition met for application/close
```

Confirm: synthesis path(s), decision sentence, target project exists, kind chosen.

### 1. Write the packet (mental or receipt)

Every handoff answers:

| Field | Required |
|-------|----------|
| `kind` | yes — one of the taxonomy |
| `from_lane` | yes — slug / lane_id |
| `to_project` | yes — one primary slug |
| `decision_or_signal` | yes — one sentence |
| `evidence` | yes — knowledge paths (not “vibes”) |
| `urgency` | yes — high / medium / low |
| `next_loop` | yes — none / craft / experiment / implement / operator / archive |
| `does_not_mean` | yes — one negative boundary |

Template: `.context/templates/research-handoff.md`.

### 2. Apply via CLI

```bash
bin/research-lane-loop handoff-project \
  --slug <lane> \
  --to <project> \
  --kind gate|application|opportunity|constraint|experiment|craft|knowledge|split|close \
  --note "one sentence decision or signal" \
  --evidence "10_knowledge/.../note.md" \
  [--urgency high|medium|low] \
  [--dry-run]
```

### 3. Kind-specific routing (CLI + operator)

| Kind | Lane side | Project side |
|------|-----------|--------------|
| `gate` | Log + phase note “gate cleared/blocked” | **Replace** `next_action` with gate sentence + evidence |
| `application` | Log; literature stop for this phase | **Set** `next_action` to concrete build/craft step |
| `opportunity` | Log only | Append **Consider** entry to `log.md` (and `ideas/` if project uses it); **do not** overwrite a busy `next_action` |
| `constraint` | Log | Append `decisions.md` or risk note; optional demote conflicting next_action |
| `experiment` | Log | Set `next_action` to experiment-loop scaffold command |
| `craft` | Log | Set `next_action` to craft scaffold command |
| `knowledge` | Log | Cite path in project log; no forced next_action |
| `split` | Emit candidate; optional intake | No project next_action change |
| `close` | Handoff block + archive checklist | Notify consumers in log only |

### 4. Close the research pass

Still complete research-lane-loop step 6–7: capture index, phase status, research-lanes-strategy `log.md`, loop decision.

### 5. Verification

- [ ] Receipt exists (CLI prints path under project `outputs/` or lane `log.md`)
- [ ] Kind matches urgency (opportunity did not hijack active WIP next_action)
- [ ] Evidence paths resolve under `10_knowledge/` or project outputs
- [ ] Next loop is named (or explicit `none`)
- [ ] Archive only if kind is `close` **and** operator accepts lane stop

## Anti-patterns

- Every interesting paper becomes a **gate** (severity inflation)
- Every handoff overwrites project `next_action` (kills real WIP)
- Handoff without evidence paths (“trust me”)
- Using handoff instead of synthesis (skipping step 5)
- Archiving the lane because one opportunity was filed
- Filing `split` as `application` on a random active project

## Relation to the three research modes

```text
literature  ──handoff──►  project surface
                │
                ├─ gate / application / constraint  →  implement or decide
                ├─ craft                             →  craft-research-loop
                ├─ experiment                        →  project-experiment-loop
                ├─ opportunity                       →  consider queue
                ├─ knowledge                         →  consume note only
                └─ split / close                     →  intake or archive
```

## Update discipline

- Workflow is stable; extend kinds only with a short DECISIONS note if taxonomy changes.
- Receipts are project/lane logs — append-only.
- CLI defaults must stay conservative for `opportunity` (no next_action steal).
