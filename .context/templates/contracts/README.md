---
title: "Contract templates"
domain: "knowledge-systems"
type: "template"
status: "active"
source: "bin/contract-audit checks 1.5/1.6/1.7/10.5; 00_inbox/AGENTS.md and 10_knowledge/AGENTS.md as reference implementations"
tags: ["contracts", "templates", "enforcement", "tiers"]
updated: "2026-08-23"
---

# Contract templates

Starter files for anything that constrains agent behaviour. They exist so a new
contract is **born enforceable** instead of being retrofitted after an incident.

`structural-file-profile.md` (one level up) answers *what kind of file is this
and where does it belong*. These templates answer *how does a rule in it get
enforced*. Use both: the profile to place the file, a template to write it.

## Why these exist

Measured 2026-08-23 by `bin/contract-audit --layer document`:

| Check | Result |
| --- | --- |
| 10.5 contracts declare a tier | **2 / 135 files** |
| 1.6 hard promises bound at clause level | 138 clauses, **124 unbound (10% bound)** |
| 1.5 normative clauses name a mechanism | 680 clauses, **39 bound (6%)** |
| 1.7 T1+ rules name an Escape | 7 rules, **0 missing** |

1.7 is the tell. **Where the format is used it works.** The gap is propagation,
not design — so the fix is a template plus a checker, not a better argument.

Behavioural corroboration, independent of the document layer: `AGENTS.md` says
"Avoid Subshell `cd`" and telemetry shows **5,215 `cd` command heads**, with
`cd` the **#1 repeated auto-papercut**. A rule nothing checks is a wish.

## The clause format

Every normative rule declares four things, as a blockquote directly under an
`##` heading:

```markdown
## 1. The rule, stated as one sentence in the imperative.

> **Binds:** who or what this constrains
> **Tier:** T2 (blocked)
> **Check:** `bin/some-tool --check`, a named hook, or `tests/test_x.py`
> **Escape:** the named, cheap, non-penalized way to comply when you cannot
> meet the letter of the rule

Optional prose: the measurement or incident that made this rule necessary.
```

**Syntax is load-bearing.** `bin/contract-audit` parses these with real regexes
and a malformed block reads as zero adoption:

- The block must **start** with `**Binds:**`.
- **No blank line inside the block** — a blank line ends it. Wrap continuation
  lines with a leading `>`.
- `Tier:` must be literally `T0`, `T1`, `T2`, or `T3`.
- `Check:` should name something runnable: a `bin/` tool, a hook event, a
  `pytest` path, `.gitignore`, or a `--check` / `--apply` / `--dry-run` flag.
  Those are the tokens the audit's `MECHANISM` regex recognises.

Verify before committing: `bin/contract-lint --file <path>`.

## The tier ladder

| Tier | Means | What must be true |
| --- | --- | --- |
| **T0** advisory | Judgement. No mechanism, and none is promised. | Nothing. `Check: none` is honest and correct here. |
| **T1** detected | A violation is found **after** the fact. | A named tool or sweep reports it. |
| **T2** blocked | A violation cannot land. | A hook, gate, or guard refuses it. |
| **T3** reconciled | Drift is detected **and** repaired against a source of truth. | A reconciler runs on a schedule. |

**T0 is a legitimate answer, and picking it honestly is the point.** "Do not
tidy this folder" carries `Check: none` in `00_inbox/AGENTS.md` and that is
correct. The defect this format fixes is not the absence of mechanisms — it is
that **nothing distinguished an advisory rule from a load-bearing one**, so a
rule that silently lost its enforcement looked exactly like one that never
needed any.

Do not inflate tiers. A declared tier is self-asserted; claiming T2 without a
gate is the same worthless self-report as a capture writing its own
`retrieved_at`.

## Escape is mandatory at T1 and above

> A rule with no compliant way to fail **manufactures** violations. An agent
> that cannot comply and cannot honestly fail will produce something that
> *resembles* compliance.

That is not theory. A source-count quota made honesty unrepresentable — no field
meant "I looked and found nothing" — and 107 fabricated citations followed. See
`10_knowledge/agents/2026-08-10__agents__note__every-rule-needs-an-honest-failure-path.md`.

Three exits must be namable for every T1+ rule:

1. **The agent's** — named, cheap, and non-penalized. An escape that reads as
   failure is not an escape.
2. **The check's** — fail-open or fail-closed, decided and written down.
3. **The reader's** — "ran, found nothing" must be distinguishable from "did not
   run".

Diagnostic for every MUST you write: *what does an agent do when it cannot?*

## Files here

| Template | For |
| --- | --- |
| `agents-md.template.md` | Any `AGENTS.md` — root, lifecycle folder, project, or workbench |
| `workflow.template.md` | `.context/workflows/*.md` operator sequences |
| `skill.template.md` | `.agents/skills/**/SKILL.md` reusable agent judgement |
| `subagent.template.md` | `agents/*.md` specialized roles |
| `decision-record.template.md` | `DECISIONS.md` / project `decisions.md` entries |

## Reference implementations

Read these before writing a new contract — they are the format working on real
rules, not illustrations:

- `00_inbox/AGENTS.md` — four rules spanning T0 through T2
- `10_knowledge/AGENTS.md` — the post-incident rules, all with earned Escapes

## Adoption is measured, not assumed

- `bin/contract-lint --file <path>` — one file, before you commit it.
- `bin/contract-lint --all` — corpus adoption and the worst offenders.
- `bin/contract-audit --layer document` — checks 1.5 / 1.6 / 1.7 / 10.5 as part
  of the full audit program.

A template with no consumption path is this system's documented failure mode. If
these files stop being linted, they have already failed.
