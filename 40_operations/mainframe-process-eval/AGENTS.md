# MainFrame Process Evaluation — Local Rules

> [!WARNING]
> This operation evaluates MainFrame processes. A path here is not proof that
> a process is healthy, that an evaluation passed, or that Git contains the
> evaluation history.

Rules declare **Binds / Tier / Check / Escape**. Tiers: **T0** advisory ·
**T1** detected · **T2** blocked · **T3** reconciled.

---

## 1. Keep portable engine and local evidence distinct.

> **Binds:** any agent adding files under `40_operations/mainframe-process-eval/`
> **Tier:** T2 (blocked from tracking evidence)
> **Check:** `tests/test_operations_git_boundary.py`; `.gitignore` default-deny allowlist
> **Escape:** leave evidence, receipts, outputs, raw-materials, logs, and
> transcripts untracked; do not force-add them to private Git

Private `mainframe-live` tracks only the allowlisted portable surfaces
(README, AGENTS, `src/`, `tests/`, `methodology/`, loop-eval workbench).
Git is not the evaluation archive.

## 2. Depend downward on MainFrame lifecycle substrate.

> **Binds:** MPE portable source under `src/`
> **Tier:** T1 (detected)
> **Check:** `tests/test_lifecycle_substrate_isolation.py`
> **Escape:** call `lifecycle_identity` / `lifecycle_runtime` / `migration_lease`;
> do not make those modules import this operation

## 3. Fail closed when direct operation authority is missing.

> **Binds:** `bin/process-eval` and MPE writers
> **Tier:** T2 (blocked)
> **Check:** `40_operations/mainframe-process-eval/tests/test_process_eval.py`
> **Escape:** report `status: blocked` / missing identity; do not guess a path

## 4. Do not treat this operation as a standalone GitHub owner.

> **Binds:** agents proposing a `mainframe-process-eval` repository
> **Tier:** T0 (advisory)
> **Check:** none
> **Escape:** keep the operation inside private `mainframe-live`; evidence stays local

## Verification

```bash
uvx --with pytest pytest tests/test_operations_git_boundary.py tests/test_lifecycle_substrate_isolation.py 40_operations/mainframe-process-eval/tests -q
bin/contract-lint --file 40_operations/mainframe-process-eval/AGENTS.md
```
