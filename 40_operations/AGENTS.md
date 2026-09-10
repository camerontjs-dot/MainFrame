# 40_operations - Local Rules

> [!WARNING]
> This folder holds standing coordination systems. A path here is not
> evidence that a system is active, healthy, focused, approved, or safe to
> automate.

Rules declare **Binds / Tier / Check / Escape**. The Escape is the named, cheap,
non-penalized way to comply when the required authority or evidence is absent.

Tiers: **T0** advisory · **T1** detected · **T2** blocked · **T3** reconciled.

---

## 1. Keep physical admission bounded.

> **Binds:** any agent proposing to create or move another record under `40_operations/`
> **Tier:** T1 (detected)
> **Check:** `bin/work-inventory --check`
> **Escape:** leave the prospective entity in its current canonical location and record the unmet review gate instead of expanding the admitted set.

Admission of one operation does not migrate other projects automatically.
MainFrame Process Evaluation is the portable public example. No further move
is implicit in an operation classification, a completed cycle, or a successful
check.

## 2. Admit operations only with explicit identity and direct authority.

> **Binds:** any agent or operator proposing an operation under this directory
> **Tier:** T2 (blocked on duplicate or invalid typed identity)
> **Check:** `bin/work-inventory --check` and `tests/test_lifecycle_identity.py`
> **Escape:** retain the existing record unchanged, or label the proposed identity `UNKNOWN`; do not create a duplicate or infer classification from recurrence or path.

An admitted operation needs a stable slug, its own authority `README.md`, an
explicit `record_type: operation`, and the classification fields in this
directory's README. A slug must be unique across `30_projects/` and
`40_operations/`; a copy, alias, or symlink cannot act as a migration.

## 3. Preserve authority and keep projections non-authoritative.

> **Binds:** any reader or writer of an operation coordination record
> **Tier:** T0 (advisory)
> **Check:** none
> **Escape:** report the field as `UNKNOWN` and consult the direct authority; do not fill it from retrieval, a generated index, a schedule, or a past handoff.

Each operation README owns its coordination fields. Local focus authority,
when present, remains `local-only: 20_live/focus/`. Ledgers, receipts, and
nested repositories retain their own authority. Retrieval results are
nominations, never proof.

## 4. Keep WIP and lifecycle semantics orthogonal to location.

> **Binds:** any agent or operator assessing an operation's lifecycle or WIP effect
> **Tier:** T1 (detected)
> **Check:** `bin/work-inventory --check`
> **Escape:** leave the assessment unresolved and preserve the current WIP/focus decision rather than granting an exemption because the record is an operation.

`wip_class`, not `record_type` or folder location, determines seat treatment.
Finishing one recurring cycle is not closure; pause, decommission, and archive
actions require their own explicit authority.

## Verification

Run `bin/contract-lint --file 40_operations/AGENTS.md` after changing these
local rules. The linter verifies contract structure; it does not establish
operation health.
