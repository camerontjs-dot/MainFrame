# MainFrame Harness Operating Contract

This file defines how MainFrame treats **agent harnesses** across lifecycle folders. It complements `AGENTS.md` (global agent behavior) and `STATE.md` (current focus). Agents and operators should read this when preparing delegation, evaluating capability, or choosing local vs cloud execution.

## Definition

A **harness** is the environment around a model: instructions, state, verification, scope, and session lifecycle. It is not the model and not the framework brand. The harness makes output **reliable**; the model makes output **possible**.

## File role

`HARNESS.md` is MainFrame's harness policy contract. The filename is local to
this workspace; the common practice is the role: describe the execution
environment around agents, including instructions, state, scope, verification,
session lifecycle, client differences, task categories, and promotion gates.

This file owns durable harness policy. It should not absorb project status,
repo-specific build commands, raw telemetry, or current scoreboards. Current
evaluation results live in `30_projects/agent-harness-eval/`; durable patterns
live in `10_knowledge/agents/`; structural-file updates should be checked
against `.context/templates/structural-file-profile.md`.

## Three documentation layers

Harness knowledge is split on purpose — different lifecycle, different MindGraph index, different trust:

| Layer | Location | MindGraph DB | Trust | Contents |
|-------|----------|--------------|-------|----------|
| **Patterns** | `10_knowledge/agents/` — e.g. `harness-engineering-by-task-category` | `mainframe.sqlite` (default) | Durable, synthesized | Task categories, five subsystems, local/cloud integration patterns, skill routing heuristics |
| **Program** | `30_projects/agent-harness-eval/outputs/` — e.g. `harness-evaluation-program` | `mainframe-projects.sqlite` | Project status, dated | H0/H1/H2/H3 variants, sealed cases, graduation matrix, next gate |
| **Contract** | `HARNESS.md` (this file) | Not indexed | Operating policy | Rules that do not change every eval run |

Volatile telemetry (`20_live/workflow-metrics/`) is intentionally **outside** default MindGraph scope. It shows activity, not graduated capability.

## Clients in this workspace

| Client | Typical use | Harness surface | Capability evidence |
|--------|-------------|-----------------|---------------------|
| **Local Coder** (Aider + Ollama) | Bounded code edits | Task packets, file allowlists, post-hoc verification | `agent-harness-eval` receipts + graduation gate |
| **Claude Code** | Planning, multi-file judgment | AGENTS.md, skills, hooks | Redacted telemetry; no auto-graduation |
| **Codex** | Implementation slices | Hooks, permissions | Redacted telemetry; vocabulary TBD |
| **Grok Build** | Cloud agent sessions | Native project hooks, skills | Redacted telemetry (`client: grok`) |

Do not infer delegation authority from live telemetry or workstation display alone.

## Planning, execution, verification

1. **Planning authority** — Frontier/cloud agents and the operator produce reviewed task packets. Unresolved design stays out of execution.
2. **Execution** — Local or cloud agent runs inside scope. Run state goes to receipts, not packet mutation.
3. **Verification** — External deterministic checks (tests, linters, scope diff, claim-accuracy). MindGraph supplies **context nominations only**, never verification.

### Focus and system health (ADR-044)

- **Focus authority (accepted, not yet implemented):** operator-approved primary attention will live under `20_live/focus/` (`current.yaml` + decision/outcome history). Project READMEs keep lifecycle state; focus does not activate projects (WIP remains ADR-041).
- **STATE.md:** human handoff narrative; after migration it cites focus revision rather than acting as the parseable project id.
- **Doctor:** health is a **vector** of claims (`bin/mainframe-doctor` contract accepted; binary ships with Unit 1.3 after WIP activation). Required `unknown` must not aggregate to healthy. Until the doctor exists, treat `session-open ok: true` with a missing project path as a known false-green (reproduced 2026-07-14).
- Design surfaces: `30_projects/mainframe-process-eval/plans/scalability/`.

Workflows:

- `.context/workflows/delegate-local-task.md` — packet prep and isolated execution
- `.context/workflows/local-coder-run.md` — live local coder discipline
- `.context/workflows/source-literature.md` — peer-reviewed / institutional source discovery before ingest (ADR-028)
- `.context/workflows/research-lane-loop.md` — one lane-phase pass: source-literature → ingest → synthesis → tracker close (loopable)
- `bin/research-lane-loop` — preflight resume class A–D, capture-index audit/repair (`doctor`, `preflight`, `audit-indexes`)
- `.context/workflows/epistemic-standard.md` — claim classification, evidence appraisal, confidence language, promotion gate (ADR-029)
- `.context/workflows/ingest-minion.md` — deterministic inbox → `10_knowledge/` routing
- `.context/workflows/eval-schedule.md` — scheduled eval suites, launchd, weekly review ritual (ADR-036)
- `.context/workflows/project-experiment-loop.md` — measured experiment pass (design → run → harvest → **triage/action**); `bin/project-experiment-loop`
- `.context/workflows/lab-report.md` — universal researcher lab-report notebook for every decision-bearing test; `bin/lab-report scaffold|check|list`
- `20_live/eval-registry/last-eval-action.md` — portfolio triage for **all** MainFrame evals (action layer); `last-canary-action.md` is a pointer
- `.context/workflows/craft-research-loop.md` — product/craft trial-and-error (FINDINGS keep|kill|iterate + proof index); `bin/craft-research-loop`; action card is **project-local** `outputs/LAST_CRAFT_ACTION.md`

## Task-category rule

Optimize and graduate harnesses **per task category × model profile × harness version**. Categories include mechanical edit, multi-file coordination, failure recovery, scope enforcement, research/synthesis, environment setup, and long-horizon build. See the durable note in `10_knowledge/agents/` for pattern detail.

## Graduation (local delegation)

Real delegation requires a tuple that passes the strict gate in `agent-harness-eval`:

- ≥ 8/10 held-out verified passes
- Zero scope violations
- Zero false completion claims
- Zero human repair on passing runs

### Evaluation layers for coding (2026-07-22)

Local Coder evaluation is **three layers**. Do not collapse them into one score.

| Layer | Question | Owner / artifacts |
|-------|----------|-------------------|
| **Public standards** | Is the model coding-agent-shaped? | Calibration only: Aider Polyglot; optional SWE-bench Verified lite. Plan: `30_projects/agent-harness-eval/plans/coding-standard-benchmark-calibration.md` |
| **Sealed H1 suite** | Does *our* stack pass *our* edit jobs under packet + external verify? | `agent-harness-eval` coding-backend hard screen / multi-path scorecards |
| **Live receipts** | May it touch real trees under this contract? | This section + verified-done live path |

HumanEval/MBPP-style completion benches are **not** sufficient for promotion. Public leaderboards do **not** override sealed false-completion or scope gates. Sealed matrices do **not** replace live receipts for graduation.

### Live receipts are the standard (2026-07-19)

Offline grading of a pre-produced workspace is allowed for fixture authoring and verifier selftest. **Promotion and capability claims for Local Coder (and any coding profile under this contract) must cite live-agent receipts**: the agent ran under an adapter, emitted a completion claim through the claim channel, and was scored by an external deterministic verifier.

Minimum live receipt fields:

- task / case id, profile, harness version, adapter id
- `claimed_complete` (or finish status) recorded independently of the verifier
- `verified_pass`, `false_completion`, `scope_violation`
- unified ledger label when available (`verified-supported` | `honestly-abstained` | `unsupported-assertion` | `out-of-scope`)
- trajectory summary when the adapter supports tools: commit-class tags (`lookup` / `verify` / `commit` / `finish`) and `commit_fired`

Public demo instrumentation: `30_projects/verified-done` (`runner/run.py live`, `LEDGER.md`). Private lab matrices remain in `agent-harness-eval`.

The Local Agent workstation may display only **sanitized aggregates** from the evaluator. Raw prompts, transcripts, diffs, and verifier output stay in the private eval project.

Current matrix status and next gates live in `30_projects/agent-harness-eval/README.md`, `methodology-approach.md`, and dated outputs. This file records the graduation rule, not the live scoreboard.

## MindGraph: two indexes

- **Knowledge** — `bin/mindgraph-refresh` → `~/.mindgraph/mainframe.sqlite` over `10_knowledge/`
- **Projects** — `bin/mindgraph-refresh-projects` → `~/.mindgraph/mainframe-projects.sqlite` over an optional ignored local manifest.
  - **Default (lean):** `30_projects/mindgraph-projects.json` — `README.md`, `AGENTS.md`, `log.md`, `decisions.md`, `methodology-approach.md`, `plans/**` only. **No bulk `outputs/`** (higher precision for agent context).
  - **Deep (archaeology):** `30_projects/mindgraph-projects-deep.json` or `--deep` — adds `outputs/**`. Use for audits, not default daily query.
  - Excludes workbenches/raw materials. `--full` expands the *project list* to every directory; include globs still come from the chosen manifest.
  - **Mutation requires explicit `--apply`** (Unit 2.1); preview with `--dry-run`; `--help` is non-mutating.
  - **Recommended path (ADR-045):** `bin/mindgraph-projects-apply --plan` → `--stage` → `--promote --receipt …`. Add `--deep` on those flags for the archaeology profile. Never bulk-ingest `20_live` telemetry. Live retention: `.context/live-retention.md`.

#### When to re-stage the projects index

Re-run `bin/mindgraph-projects-apply --plan` → `--stage` → `--promote` (lean default unless you need `--deep`) when:

1. **Coordination truth moved** — active project README / `next_action`, plans, or log entries that agents must find by search.
2. **WIP set or primary focus changed** — new active project, major pause/activate, or focus primary project swap.
3. **Manifest membership changed** — project added/removed from `mindgraph-projects.json` (or deep twin).
4. **Doctor / status says lag** — `bin/mindgraph-projects-apply --status` not green, or query results miss a file you know is on disk.
5. **After a bulk plan cut** — multi-file plan rewrite in one session (one stage at end is enough).

Do **not** re-stage for pure `20_live` telemetry, workstation UI, or knowledge-only notes (wrong DB). Prefer **one stage at session end** over promote-on-every-edit. Stage can sit green until you promote; promote always backs up the previous installed DB.
- **Doctor** — `bin/mindgraph doctor` (alias `status`): dual-index path/size/table/count health without loading the embedder. Workspace-root `mainframe*.sqlite` stubs are warnings only; authoritative DBs are under `~/.mindgraph/`. Query fail-fasts if required tables are missing.
- **Shared MCP daemon (ADR-049)** — one loopback process owns both indexes; clients must not spawn per-session `serve-mcp` (each loads MiniLM ~1.4 GB).
  - **Health / lifecycle:** `bin/mindgraph daemon-health` · `daemon-start` · `daemon-stop` (LaunchAgent `com.user.mindgraph-daemon` may KeepAlive).
  - **Idle opt-in:** persistent behavior remains default. `bin/mindgraph-idle-lifecycle activate --confirm-no-active-clients N` is the only approved switch: in a verified idle window it disables the incompatible KeepAlive job and enables locked proxy auto-start plus renewable leases. Direct HTTP remains manual-start/reconnect; implementation work must not run activation.
  - **Client wiring (all agents):** stdio → `bin/mindgraph mcp-proxy --url http://127.0.0.1:8000/mcp` (root `.mcp.json`, Antigravity `~/.gemini/**/mcp_config.json`, Grok, Claude Code, Cursor). Streamable HTTP clients (e.g. Codex) may use `url = "http://127.0.0.1:8000/mcp"` directly.
  - **Tool contract:** MCP `query(question, scope, …)` and `graph_neighbors(doc_id, scope)` require `scope` ∈ {`knowledge`, `projects`}. Response includes `trust_profile`. No blended scope.
  - **Debug only:** `serve-mcp --db <path>` for single-DB isolation; never the daily default.

MindGraph's active engine source lives in `mindgraph/`. That source project is not automatically folded into the durable knowledge index. Keep sandbox/upgrade work in `30_projects/mindgraph/` and retrieval-quality measurements in `30_projects/mindgraph-eval/`.

Query intent routing:

- "What do we know about harness patterns?" → knowledge DB
- "What is the current eval result / next gate?" → projects DB
- "Search everything" → run both; **do not merge without trust labels**

MindGraph Query Station convention:

- The Query Station is the interpreter over separate stores, not a third merged source of truth.
- Human and agent-facing station modes should include `knowledge`, `projects`, `federated`, `apply`, `extract`, and `trace`; v1 workstation support covers `knowledge`, `projects`, and grouped `federated`.
- Federated output must group results by lifecycle/trust zone and surface `index_id`, `trust_profile`, namespace/project, source root, path, query string, fit/scope warnings, and why a connection was nominated when that mechanism is available.
- Planning output should be copyable as a `MindGraph Query Pass` block listing query strings, durable-knowledge nominations, project-context nominations, weak/excluded hits, and source files that still require inspection.
- For station modes not yet implemented, agents satisfy the same convention with explicit CLI queries against both SQLite files.

Do not ingest the full vault into one graph. Operating contracts, empty indexes, and raw workbench trees add noise and false confidence (ADR-005, lifecycle DB experiment).

## Deterministic work stays out of the harness

Patch application, index generation, exact scripted rewrites, and `bin/*` minion passes run **without** a model unless a conflict requires judgment. This mirrors ADR-009 minion vs subagent routing.

## Promotion path

Reusable harness lessons discovered in projects move to `10_knowledge/` only through explicit extraction (`bin/extract-knowledge`, audit-sweep synthesis, or a reviewed note with full metadata). Eval scores stay in `30_projects/` until synthesized patterns justify a durable note.

## Related decisions

- ADR-024 — Reviewed task packets and isolated local-agent evaluation
- ADR-025 — MindGraph active source lives in a MainFrame project workbench
- ADR-005 — MindGraph default scope is `10_knowledge/` only
- ADR-015 — Project-layer MindGraph uses separate DB + trust labels
