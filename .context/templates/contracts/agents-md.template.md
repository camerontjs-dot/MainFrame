# <folder or scope> - Local Rules

> [!WARNING]
> One or two lines on what this scope *is*, and the consequence of getting it
> wrong. Readers who skim one line should learn the blast radius from it.
> Delete this callout if the scope carries no standing hazard.

Rules declare **Binds / Tier / Check / Escape**. The Escape is the named, cheap,
non-penalized way to comply when you cannot meet the letter of the rule.

Tiers: **T0** advisory · **T1** detected · **T2** blocked · **T3** reconciled.

---

## 1. <Rule as one imperative sentence.>

> **Binds:** <who or what this constrains — a tool, a client, any agent writing here>
> **Tier:** T2 (blocked)
> **Check:** `bin/<tool>` (<hook event, or where it runs>), plus
> `tests/test_<name>.py` as the regression
> **Escape:** <the compliant alternative. Name the command. State plainly that
> it carries no penalty.>

<Optional: the measurement or incident that made this rule necessary. Dates and
counts, not adjectives. This paragraph is why the rule survives review.>

## 2. <Second rule.>

> **Binds:** <scope>
> **Tier:** T1 (detected)
> **Check:** `bin/<sweep-tool>` — reports violations after the fact
> **Escape:** <alternative>

## 3. <A rule that is genuinely advisory.>

> **Binds:** <scope>
> **Tier:** T0 (advisory)
> **Check:** none
> **Escape:** n/a

<T0 is a real answer. Use it when the rule needs judgement and no mechanism
should pretend otherwise — but say why the judgement matters.>

<!--
TEMPLATE NOTES — delete this block before saving.

SYNTAX (bin/contract-audit parses these; malformed reads as zero adoption):
  - the block must START with `**Binds:**`
  - NO blank line inside a block — a blank line ends it; prefix
    continuation lines with `>`
  - Tier must be literally T0 / T1 / T2 / T3
  - Check should name something runnable: bin/<tool>, PreToolUse/PostToolUse,
    a hook, pytest / test_<x> / selftest, --check / --apply / --dry-run,
    .claude/settings, or .gitignore

BEFORE COMMITTING:
  bin/contract-lint --file <this file>

SCOPE DISCIPLINE (AGENTS.md, Structural File Discipline):
  - stable always-on rules -> here
  - long operator sequences -> .context/workflows/
  - repeated agent judgement -> .agents/skills/
  - deterministic enforcement -> bin/, scripts, hooks, config, tests
  - volatile status -> STATE.md, 20_live/, project README or log
  A local AGENTS.md adds scoped constraints. It does not restate root rules.

TIER HONESTY:
  A declared tier is self-asserted. Claiming T2 without a gate is the same
  worthless self-report as a capture writing its own retrieved_at. If you
  cannot name the thing that blocks it, it is not T2.
-->
