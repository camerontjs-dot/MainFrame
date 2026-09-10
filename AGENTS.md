# Mainframe - Global Operating Contract

## System Purpose
This system organizes knowledge by its **information lifecycle** first, and topic second. The goal is accurate recall, low-friction capture, and safe updates.

## Architecture
- `00_inbox/`: Fast capture zone.
- `01_ingest/`: Normalization and routing.
- `10_knowledge/`: Durable, slower-moving knowledge.
- `20_live/`: Volatile personal and project state, active research.
- `30_projects/`: Active work with outcomes.
- `40_operations/`: Standing coordination systems under the local pilot rules.
- `90_archive/`: Preserved material without cluttering active navigation.

## Session Entry

Run `bin/session-open --json` for workspace arrival. For project work, use
`--project <slug> --task "brief task description"`; use `--intent resume` to
resume the recorded focus. Add `--path <repo-relative-path>` for deeper rules.
Read every required content batch separately with `--read-batch N`, repeating
the routing arguments. Recover truncated reads before relying on them.
The command lists and serves context; it cannot verify reading or understanding.
Follow `.context/workflows/session-open.md` for the route's stopping point.

> **Binds:** agents starting or resuming MainFrame work
> **Tier:** T0 (advisory)
> **Check:** none — invocation and reading are not enforced by the command
> **Escape:** if the command is unavailable, read `HARNESS.md` and the applicable directory contracts directly; report unresolved prerequisites before dependent work

## Agent Behavior
1. **Harness contract:** For workspace arrival, read `HARNESS.md`'s **Session orientation** section. For project resume, implementation, evaluation, delegation, or other action, read the full harness and applicable directory contracts. Arrival may report the lifecycle map and recorded focus, then stops; project-specific diagnosis or recommendations require the resume route. This explicitly narrows the former unconditional full-harness reading requirement for arrival only (ADR-059).
2. **MindGraph Planning Hook:** Always query the dual MindGraph databases (`mainframe.sqlite` and `mainframe-projects.sqlite`) when planning or starting work on any project in `30_projects/` to leverage existing workspace context. Use the MindGraph Query Station when available, or the CLI equivalent, and preserve the two result groups with trust labels instead of blending them into one answer.
3. **MindGraph MCP (shared daemon):** Operational clients connect through the loopback shared daemon (`http://127.0.0.1:8000/mcp`) via `bin/mindgraph mcp-proxy` or a streamable-HTTP URL — never by spawning `serve-mcp` per session. Every MCP `query` / `graph_neighbors` call **must** pass `scope` = `knowledge` or `projects`. Do not invent `both`. Prefer CLI `bin/mindgraph query --db …` when MCP is unavailable. See ADR-049 and `.agents/skills/mindgraph-retrieval/SKILL.md`.
4. **MindGraph engine edits:** The engine has one source tree — `30_projects/mindgraph/workbench/`, which is also the tree that publishes to GitHub. Root `mindgraph/` is a **promoted artifact**; editing it directly is drift by definition, and doing so through 2026-08 left the published MindGraph without the guardrails built after the fabricated-citations incident. Change the workbench, then run `bin/mindgraph-promote`. `bin/mindgraph-promote --check` and `tests/test_mindgraph_promotion.py` fail on drift. See `mindgraph/AGENTS.md`.
5. **Centralized Skills:** Use `.context/workflows/` for operator-driven sequences and `.agents/skills/` for reusable agent skills rather than duplicating instructions.
6. **Subagents:** Named subagent definitions live in `agents/` (e.g. `agents/ingest-agent.md`). Subagents are first-class collaborators; their roles, tools, guardrails, and procedures are defined there.
7. **Local Constraints:** Respect local `AGENTS.md` files in subdirectories—they contain overriding rules for sensitive or volatile data.
8. **Immutability:** Do not silently overwrite history. If a file is in `20_live`, use snapshots or append-only timelines.
9. **Provenance:** Preserve raw sources as evidence. Extracted text is a searchable working copy, not the source of truth.
10. **Execution Honesty:** Never simulate compute or mock operational completeness. Scripts, tools, and tests must physically invoke the underlying engines, models, or databases they represent or fail closed (`status: blocked`). Do not format evaluation tables or claim-audit verdicts in Markdown without a verifiable machine trace on disk. See `.context/workflows/deterministic-tool-standard.md`.
11. **Degraded-Mode & Escape Valve Discipline:** Complex systems run as broken systems (Cook 1998). Tools, scripts, and validation gates must never assume 100% operational availability or faultless inputs. When dependencies fail, tools must fail closed or report explicit degraded status. All validation gates must provide explicit, valid intermediate escape hatches (e.g. `type: hypothesis`, `status: queued`, `needs-audit`) so agents and operators are never pressured into deceptive workarounds or fabricated metadata to pass a check. Enforced via ADR-052 and `.context/workflows/deterministic-tool-standard.md`.
12. **Project Resume Reconstruction:** Treat casual project-resume language such as “take a look,” “where are we,” “read the handoff,” or “decide what to do next” as authorization to inspect, diagnose, and recommend only. Before proposing work, reconstruct the current coordination files, every nested Git repository and registered worktree, dirty/concurrent state, candidate and experiment identity, and direct test/receipt evidence. Handoffs, READMEs, plans, generated indexes, and MindGraph results are leads; they do not override current source, Git, manifests, or execution evidence. Report the reconstructed workstate before recommendations, and follow `.context/workflows/project-resume-and-candidate-lifecycle.md`.

> **Binds:** any agent starting or resuming work in `30_projects/`
> **Tier:** T0 (advisory MainFrame-wide; a project-local contract may raise the tier)
> **Check:** none at the root; managed projects may provide candidate/experiment validators
> **Escape:** if direct authority is missing or conflicting, label the field `UNKNOWN` or the worktree `UNMANAGED`, remain read-only, and stop comparison or promotion rather than guessing

13. **Repository reconciliation:** GitHub is authoritative for registered repository state. Query `bin/repo-reconcile` for derived drift; verify the actual repository before consequential operations. `DIRTY` and `DIVERGED` are observations, not license to rebase, force-push, or pick a side. See `.context/workflows/repo-reconciliation.md` and ADR-060.

> **Binds:** agents inspecting or mutating GitHub-facing checkouts registered in `20_live/github-portfolio/registry.json`
> **Tier:** T0 (advisory) for reading the derived receipt; T2 (blocked) for unattended repair
> **Check:** `bin/repo-reconcile --check`; `tests/test_repo_reconcile.py`
> **Escape:** inspect `git -C <path> status` / `git fetch` directly; leave a checkout unregistered if it must not be classified


## Structural File Discipline
- Structural files include operating contracts, local `AGENTS.md` files, `HARNESS.md`, decision records, workflows, skills, subagent definitions, templates, configs, indexes, manifests, hooks, scripts, and project/workbench files that define process or verification behavior.
- Use `.context/templates/structural-file-profile.md` when creating or auditing structural files. Project-local files follow the same framework even when they are ignored or private.
- **Contract templates:** start new contracts from `.context/templates/contracts/`. Every normative rule declares **Binds / Tier / Check / Escape**, with tiers **T0** advisory · **T1** detected · **T2** blocked · **T3** reconciled. `T0` with `Check: none` is an honest answer; an inflated tier is not. Check the file before committing with `bin/contract-lint --file <path>`; `.githooks/pre-commit` runs `--changed` so an adopted contract cannot silently lose its enforcement to a blank line. Reference implementations: `00_inbox/AGENTS.md`, `10_knowledge/AGENTS.md`.
- Put stable always-on rules in `AGENTS.md`; put long operator sequences in `.context/workflows/`; put repeated agent judgment in `.agents/skills/`; put specialized roles in `agents/`; put deterministic enforcement in `bin/`, scripts, hooks, config, or tests.
- Keep root and lifecycle contracts durable. Put volatile status in `STATE.md`, `20_live/`, project `README.md`, or project `log.md`.
- Record accepted architecture or workflow changes in `DECISIONS.md`; record project-only tradeoffs in the project's `decisions.md`.

## Searching this repo

`grep` here is a **ugrep wrapper that honours `.gitignore`**, and `10_knowledge/`,
`20_live/` and `30_projects/` are all ignored. A repo-root search returns zero
hits for content that demonstrably exists. This is the trap that makes an agent
confidently answer "that doesn't exist" about something that does.

### Never run a bare recursive `grep` from the repo root

> **Binds:** any client issuing a Bash command in this repo
> **Tier:** T2 (blocked)
> **Check:** `bin/bash-discipline-guard` (PreToolUse hook on Bash), with
> `tests/test_bash_discipline_guard.py` as the regression
> **Escape:** `bin/vault-grep`, `command grep`, `git grep`, or `grep -r` with an
> explicit path. All four are allowed and none carries a penalty.

**Use `bin/vault-grep` first.** It is the purpose-built fix: `rg --no-ignore`
scoped to the repo with the cache and dependency trees already excluded.

```bash
bin/vault-grep -l "Idle Capacity Engine"                 # whole-vault file search
bin/vault-grep -n "def parse_frontmatter" scripts/       # only this directory
```

It passes arguments to `rg` from the MainFrame root. Explicit paths limit the
search; without paths, ripgrep searches MainFrame or piped stdin using its normal
rules. It requires `rg` on PATH and fails loudly when unavailable.

Alternatives when `vault-grep` does not fit: `command grep`, an explicit path, or
MindGraph. Never a bare repo-root `grep`.

Recursive searches from the root also time out: `.venv` and `node_modules` trees
dominate the file count. Scope to the directory you mean.

## Command Execution & Path Discipline

**Workspace Root Execution:** Always execute commands from the MainFrame repository root using repo-relative paths (e.g. `bin/sync-project-index`).

**Running the tests:** `uvx --with pytest pytest tests/`. There is no project virtualenv and no pytest on any system python, so a bare `pytest tests/` fails with `No module named pytest`. This line read `pytest tests/` until 2026-08-26, which is a rule that could not be followed as written — recorded as a papercut against this file.

### Do not prefix commands with `cd <dir> && ...`

> **Binds:** any client issuing a Bash command in this repo
> **Tier:** T2 (blocked) for a relative target; T1 (detected) otherwise
> **Check:** `bin/bash-discipline-guard` (PreToolUse hook on Bash), with
> `tests/test_bash_discipline_guard.py` as the regression. Allowed-but-noted
> usages are counted in `20_live/workflow-metrics/bash-discipline.jsonl`
> **Escape:** run from the root with a repo-relative path, use the tool's own
> `--root` flag, use `git -C <dir>`, or make the target absolute
> (`cd "$(git rev-parse --show-toplevel)/dir" && ...`). Setting
> `MAINFRAME_BASH_DISCIPLINE=0` disables the guard for a deliberate exception.

Compound subshell directory changes create brittle relative path assumptions and fail across tool harnesses. The guard denies only a relative target, because telemetry records command *heads* and cannot distinguish a legitimate `cd` from a broken one — the counter exists to make that promotable on evidence rather than opinion.

## Metadata & Updating
- Every finalized note must contain the standard metadata schema defined in `.context/primitives.md`.
- Ensure changes to architecture or workflow are recorded in `DECISIONS.md`.
- Adhere to the epistemic stance defined in `EPISTEMIC_STANCE.md` when recording claims. For any claim-bearing output, follow `.context/workflows/epistemic-standard.md` (classify claims, check evidence tier, assign confidence, surface counterevidence).
