## ADR-<NNN>: <Title in the imperative or as a stated position> (<YYYY-MM-DD>)

**Status**: Proposed | Accepted | Superseded by ADR-<NNN>
**Date**: <YYYY-MM-DD>

**Context**: <What forced the decision. Measured state where it exists — counts,
dates, the failing command. A context section with no evidence produces a
decision nobody can later falsify.>

**Decision**: <What was decided, numbered when it has parts. Each part should be
checkable against the repo six months from now.>

**Rationale**: <Why this over the alternatives that were actually considered.
Name the rejected option; "we chose X" with no discarded Y is a description, not
a rationale.>

**Consequences**: <What becomes true, what becomes forbidden, and what is
explicitly NOT authorized by this ADR. The last clause matters most — it is what
stops an accepted design from being read as an accepted implementation.>

**Enforcement**:

> **Binds:** <who or what this decision constrains in practice>
> **Tier:** T1 (detected)
> **Check:** `bin/<tool>` / `tests/test_<name>.py` / <audit check id>
> **Escape:** <how to honestly not comply — usually "raise a superseding ADR">

<!--
TEMPLATE NOTES — delete before saving.

DECISIONS.md is newest-first. Numbers are never reused and gaps stay unfilled so
external references keep matching (see the numbering note at the file's end).

The Enforcement block is what separates a decision from an intention. On
2026-08-23 DECISIONS.md carried 60 unbound normative clauses, the largest single
block in the corpus — accepted decisions that nothing checks.

If the decision is genuinely a direction rather than a rule, say so:
  > **Tier:** T0 (advisory)
  > **Check:** none
That is honest. An inflated tier is not.

Project-only tradeoffs go in the project's decisions.md, not here.

Verify with: bin/contract-lint --file <this file>
-->
