---
title: "Session open"
domain: "knowledge-systems"
type: "workflow"
status: "active"
source: "AGENTS.md, HARNESS.md, and bin/session-open"
tags: ["session", "onboarding", "context-routing"]
updated: "2026-09-05"
structural_type: "workflow"
lifecycle_scope: "root"
owner_surface: "HARNESS.md"
authority: "workflow-contract"
privacy: "public-safe"
volatility: "stable"
source_of_truth: true
update_rule: "replace-with-review"
verification: ["uvx --with pytest pytest tests/test_session_open.py tests/test_focus_authority.py -q"]
related_surfaces: ["bin/session-open", ".context/workflows/session-lifecycle.md", ".context/workflows/project-resume-and-candidate-lifecycle.md"]
do_not_use_for: ["system health", "project acceptance", "authorization", "evidence verification"]
---

# Session open

**Trigger:** starting or resuming MainFrame work.
**Owner surface:** `HARNESS.md`.
**Stop state:** the request, governing sources, applicable constraints, relevant
unknowns and next useful step are established for the selected route. Missing
context is reported before dependent claims or action.

## Choose the route

```bash
bin/session-open --json
bin/session-open --project my-project --task "onboarding" --json
bin/session-open --intent resume --json
```

Without a project, the default is **arrival**: root AGENTS, the harness's Session
orientation section, narrative state, this workflow and available structured
focus. Describe the lifecycle map and recorded focus with freshness caveats,
then stop. Project-specific diagnosis or recommendations require **resume**.

A named `--project` implies resume. Explicit `--intent resume` selects structured
focus, then the STATE fallback. Resume requires the full harness, project lifecycle
and applicable local contracts, reconstruction workflow, README and existing
PROJECT metadata, methodology note, current log and latest decision. Older log
and decision entries remain available when the current task needs them.

Add `--path` with `--project` to include deeper ancestor contracts. The path must
exist inside that project; use an existing parent for a new file. Sibling trees,
raw evidence and evaluator bodies are not recursively loaded.

`--task` nominates an active plan by unique overlap with its filename/title.
This is a lexical navigation aid, not a relevance verdict. Verify the candidate.
Ties, no match or no task leave selection unresolved and list the candidates;
there is no alphabetical first-plan fallback. Use `--plan <repo-relative-path>`
with `--project` for a known plan inside its `plans/` directory.

Operation-aware selection is deferred. For an operation, read `40_operations/AGENTS.md`,
its owning README and applicable local contracts directly without reclassifying it.

## Read complete, bounded context

The JSON lists numbered `read_batches`, each at most 8,000 UTF-8 content bytes.
Read **one batch per tool response**, retaining the same routing arguments:

```bash
bin/session-open --project my-project --task "onboarding" --read-batch 1 --json
```

Continue through every required batch. Allow enough tool output for the batch
(for example, 10,000 output tokens); do not combine many batches into one response.
Use `--expect-hash <source_sha256>` from the listing to reject source changes
between calls. If a response is truncated, recover the missing content before
relying on it. A byte limit cannot guarantee another tool's output setting.
`--print-contents` prints the first batch only and identifies the continuation.

The route emits `context_status: unread` when paths are valid, or `incomplete`
when required context is missing, unreadable or invalid. It never reports that an
agent read or understood the content. The agent checks actual receipt of required
context and completes the route's `stop_when` conditions before giving its answer.

For resume, reconstruct current coordination, Git/worktrees, candidate/experiment
identity and direct evidence under the project-resume workflow. Use valid existing
receipts for status questions; rerun checks for changed source, missing evidence
or an explicit test request. After reconstruction, answer the request. Load an
action workflow when that action is authorized.

## Output meanings and fallback

- `ok`: required context files can be read and project/task/plan paths resolve.
  Exit 1 indicates an unresolved prerequisite. File presence and readability do
  not establish comprehension, project readiness, system health or authorization.
- `focused_project`: recorded attention during arrival; `project` is the project
  actually entered by resume. Selecting either route never changes focus.
- `missing_required`, `read_errors`, `intent_error`, `project_error`, `path_error`
  and `plan_error`: unresolved prerequisites. `reading_verified` is always false.
- `degraded`, `focus_errors` and `focus_warnings`: context/freshness concerns.
  Keep stale attention distinct from missing task authority.
- `eval_schedule_ok`: adjacent scheduled-evaluation health. `null` means the check
  was unavailable or timed out. This warning does not initiate unrelated repairs.

### Required context remains visible

> **Binds:** callers consuming `bin/session-open` output
> **Tier:** T2 (CLI blocks missing/unreadable required context and invalid paths; reading itself is T0)
> **Check:** `tests/test_session_open.py`, `tests/test_focus_authority.py`; live CLI exits and content batches
> **Escape:** read the named source files directly; report unresolved context before dependent claims or action

When routing is unavailable, use the same source order directly. If the arrival
section is missing, read the full harness. A missing project prerequisite keeps
resume incomplete; it never licenses skipping the relevant contract. The larger
open/work/close loop lives in `session-lifecycle.md`.
