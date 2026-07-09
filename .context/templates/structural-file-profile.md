---
title: "Structural File Profile Template"
domain: "knowledge-systems"
type: "template"
status: "active"
source: "AGENTS.md, HARNESS.md, 30_projects/AGENTS.md, DECISIONS.md ADR-037, and verified agent-architecture best-practice notes"
tags: ["structural-files", "contracts", "agents", "harness", "templates"]
updated: "2026-06-24"
---

# Structural File Profile Template

Use this profile when creating, auditing, or tightening any file that controls
how MainFrame, a project, a workbench, an agent, or a repeatable workflow
behaves.

The profile can be implemented as frontmatter when the file already uses
metadata, or as an explicit "Profile" section when the file should stay plain
Markdown. Not every structural file needs to paste this whole template, but
every structural file should be answerable against it.

## Profile Fields

```yaml
structural_type: operating-contract | local-contract | harness-contract | workflow | skill | subagent | decision-record | project-entry | project-log | project-plan | template | config | manifest | deterministic-operation | verification | index
lifecycle_scope: root | lifecycle | project | workbench | live | archive | external-template
owner_surface: "path or project that owns updates"
authority: operating-policy | local-override | project-status | durable-knowledge | workflow-contract | reusable-skill | deterministic-source | generated-state | live-state | private-local
privacy: public-safe | private-local | ignored-generated | live-sensitive
volatility: stable | active | volatile | generated
source_of_truth: true | false
update_rule: append-only | replace-with-review | generated-only | local-only | promote-through-decision
verification: ["commands, checks, or review gates"]
related_surfaces: ["paths this file depends on or routes to"]
do_not_use_for: ["status, secrets, long procedures, etc."]
```

## Required Sections

Use the smallest set that fits the file:

- **Purpose** - why this file exists.
- **Scope and Authority** - where it applies and what it can override.
- **Read First / Related Surfaces** - contracts, workflows, skills, indexes, or
  project files that must be checked before acting.
- **Rules or Procedure** - durable imperatives, steps, or allowed values.
- **Inputs and Outputs** - what the file consumes or produces, when relevant.
- **Verification** - deterministic command, review gate, or owner check.
- **Update Discipline** - append-only, generated-only, or reviewed replacement.
- **Privacy and Provenance** - what must not be copied, published, or treated as
  proof.

## File-Type Guidance

| File type | Best use | Do not use for |
| --- | --- | --- |
| `AGENTS.md` | Durable always-on rules, directory purpose, required preflight, local constraints, verification/update expectations. | Volatile status, secrets, long procedures, duplicated root rules, aspirational enforcement without hooks/tests. |
| `HARNESS.md` | MainFrame harness policy: execution model, task categories, verification gates, local/cloud boundaries, client differences, promotion gates. | Project scoreboards, repo-specific build commands, raw telemetry, current eval minutiae. |
| `.context/workflows/*.md` | Operator-driven repeatable sequence using known tools and update surfaces. | Agent role identity, one-off plans, deterministic scripts, active project status. |
| `.agents/skills/**/SKILL.md` | Reusable agent judgment or tool strategy with clear triggers and negative boundaries. | Global repo policy, one-off prompts, broad architecture decisions. |
| `agents/*.md` | Specialized role, tools, guardrails, handoff shape. | Long reusable task workflow that belongs in a skill. |
| `DECISIONS.md` / `decisions.md` | Accepted tradeoffs with context, decision, rationale, and consequences. | Brainstorming, TODOs, daily status, unreconciled options. |
| `README.md` | Project or package entrypoint: goal, state, boundary, next action, layout. | Detailed procedure, hidden private data, stale duplicated status. |
| `log.md` | Append-only work history, query passes, session outcomes. | Rewriting old decisions, replacing README current state. |
| `plans/*.md` | Goal, boundaries, phases, verification, stop conditions, handoff. | Durable knowledge claims that should be extracted to `10_knowledge/`. |
| `templates/*` | Repeatable artifact contract with required fields and validation expectations. | Project-specific facts that will go stale when reused. |
| Config/manifests | Actual allowed values, routing, generated state, schema pins, or deterministic tool inputs. | Aspirational policy without a validation command. |
| Tests/verifiers | Deterministic evidence that a behavior or contract still holds. | Proof that generated prose or retrieval nominations are true. |

## Destination Test

When a structural rule is repeated or fails, place the fix by failure shape:

| Failure pattern | Destination |
| --- | --- |
| Agent forgets a stable repo or directory rule | `AGENTS.md` or local `AGENTS.md` |
| Operator repeats a sequence with known steps | `.context/workflows/` |
| Agent repeats judgment, routing, or tool strategy | `.agents/skills/` |
| A specialized role needs tools and handoff rules | `agents/` |
| Behavior must be enforced deterministically | `bin/`, scripts, config, hooks, tests, or CI |
| Direction or tradeoff changes | `DECISIONS.md` or project `decisions.md` |
| Active state changes | project `README.md`, `log.md`, or `20_live/` |
| Durable lesson learned | `10_knowledge/` after extraction/review |

## Audit Checklist

- [ ] Scope is explicit and narrower files can override broader ones.
- [ ] Authority/trust zone is labelled, especially for ignored project files.
- [ ] The file says what not to put here.
- [ ] Current status is not stored in a durable contract unless it is policy.
- [ ] Long procedures route to workflows or skills.
- [ ] Enforcement claims have a matching script, hook, config, test, or review
      gate where possible.
- [ ] Generated indexes/manifests say how to regenerate them.
- [ ] Private/local files are not treated as public-safe.
- [ ] Retrieval nominations are not presented as verification.
