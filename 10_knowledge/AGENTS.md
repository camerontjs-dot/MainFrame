# 10_knowledge - Local Rules

> [!WARNING]
> This folder is durable knowledge. Everything here is citable by default, which
> means anything wrong here is wrong everywhere downstream.

Every rule below declares four things. **Escape** is not a loophole: it is the
named, cheap, non-penalized way to comply when you cannot meet the letter of the
rule. A rule without one manufactures violations, because an agent that cannot
comply and cannot honestly fail will produce something that *looks* like
compliance. See
[every-rule-needs-an-honest-failure-path](agents/2026-08-10__agents__note__every-rule-needs-an-honest-failure-path.md).

Tiers: **T0** advisory · **T1** detected · **T2** blocked · **T3** reconciled.

---

## 1. Raw captures enter through ingest. Never by direct write.

> **Binds:** any client writing a `type: raw` file under `10_knowledge/`
> **Tier:** T2 (blocked)
> **Check:** `bin/knowledge-write-guard` (PreToolUse hook on Write), plus
> `bin/knowledge-reconcile` as the T3 backstop for clients with no hook
> **Escape:** write the capture to `00_inbox/` and run `bin/ingest-minion run
> --dry-run` then `--apply`. If it is a synthesis rather than a retrieval, set
> `type: note` and write it here directly, that is expected and always allowed.

A raw is by definition something retrieved from outside. Ingest is where that
retrieval gets checked. Measured 2026-08-10: 449 raws had skipped it, 395 in ten
days, because `Write` was one step and the pipeline was three.

## 2. A capture may not wear a citation it did not earn.

> **Binds:** any file carrying `url`, `doi`, `authors`, or `year`
> **Tier:** T2 (blocked) at the ingest gate
> **Check:** `bin/capture-validate` R1–R3, wired into `01_ingest/minion.py`
> **Escape:** drop the citation fields and set `type: hypothesis`. A documented
> gap is a **better** result than an invented source, and is recorded as such.

`retrieved_at` is self-asserted and worth nothing; captures claiming it were
citing hard 404s. A real receipt is status plus timestamp plus content hash.
Verify identifiers, not bylines: the shape check found all 107 fabrications, the
non-human-author heuristic caught 6 and missed 76.

## 3. `status: stable` and `status: audited` must be earned.

> **Binds:** any file claiming a verified status
> **Tier:** T2 (blocked)
> **Check:** `bin/capture-validate` R6
> **Escape:** use `status: synthesized`. That is the honest default for anything
> an LLM produced, carries no penalty, and is what most of this folder should be.

Per `EPISTEMIC_STANCE.md` these statuses may never come from LLM output alone.
Measured 2026-08-10 before the gate: 29 files claimed `stable`, none carried
evidence, and 14 simultaneously carried `needs-audit`.

## 4. Quarantined and fabricated material is not citable.

> **Binds:** anything reading this folder, including MindGraph
> **Tier:** T1 (detected)
> **Check:** `mindgraph` attaches `provenance_warning` to every chunk of a
> quarantined document, not only the first
> **Escape:** re-source the claim against real literature and write a new note.
> The quarantined body may well be correct; it simply has no source behind it.

## 5. Raw bodies are immutable. Frontmatter may change.

> **Binds:** any edit to a `type: raw` file
> **Tier:** **T0 (advisory). Nothing checks this.**
> **Check:** none
> **Escape:** n/a

Stated honestly rather than dressed up. Status changes, tags, links and appended
`## Connections` sections are fine; the original body is evidence. If this rule
starts mattering, it needs a check, and until then it should not be quoted as
though it were enforced.

---

## Reading this folder

`grep` in this workspace is a ugrep wrapper that honours `.gitignore`, and this
whole tree is ignored. A repo-root search returns zero hits for content that
exists. Use `command grep`, an explicit path, or MindGraph.
