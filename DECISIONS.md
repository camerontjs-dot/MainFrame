# Architecture Decision Records (ADRs)

> **Public copy.** Private project names are replaced with stable placeholders
> (`<private-hub>`, `<private-eval-a>`, …). The same placeholder always means the same
> project, so the reasoning still follows. Public projects (MainFrame, MindGraph,
> Claim Audit Lab, Evidence Bundler, verified-done) are named normally.


## ADR-049: Operational default is shared daemon + mcp-proxy (2026-08-03)

**Status**: Accepted

**Context**: ADR-048 shipped the shared loopback daemon as opt-in while leaving
`.mcp.json` on per-client `serve-mcp --db`. In practice Grok, Claude Code, and
other stdio clients each spawned a full MiniLM process (~1.4 GB), so multiple
agent sessions multiplied RAM while the shared daemon either sat idle or ran
*in addition* to the duplicates.

**Decision**: Make the shared daemon the operational MCP backend for MainFrame:

1. Root `.mcp.json` (and examples) launch `bin/mindgraph mcp-proxy --url http://127.0.0.1:8000/mcp`.
2. One `serve-daemon` process owns both indexes; clients are thin stdio proxies.
3. MCP tools require explicit `scope` of `knowledge` or `projects` (no blend).
4. `serve-mcp --db` remains available for single-DB debugging only, not daily clients.
5. Optional login LaunchAgent may keep the daemon up; proxy still does not auto-start it.

**Consequences**: Clients must restart MCP after config change. Agents must pass
`scope` on every shared-MCP call. Daemon must be healthy (`daemon-start` /
`daemon-health`) before proxy connections succeed. Embedder cost is paid once
per machine, not once per agent session.

**Client rollout (same day)**: Wired proxy/URL for MainFrame `.mcp.json`, Grok
`~/.grok/config.toml`, Claude Code (project `.mcp.json`), Claude Desktop,
Cursor `~/.cursor/mcp.json`, Antigravity `~/.gemini/**/mcp_config.json`, and
Codex `~/.codex/config.toml` (`url = http://127.0.0.1:8000/mcp`). Operating
contracts: `AGENTS.md` item 3, `HARNESS.md` shared-MCP bullet, skill
`mindgraph-retrieval`.

## ADR-048: Opt-in loopback shared MindGraph MCP daemon (2026-08-03)

**Status**: Superseded in part by ADR-049 (operational default); engine contract still applies

**Decision**: Promote the tested workbench Streamable HTTP slice into root
`mindgraph/` while retaining `serve-mcp --db` as the default-compatible stdio
path. The shared daemon binds only to loopback, opens the durable and project
indexes read-only, requires one explicit `knowledge` or `projects` scope per
call, exposes the corresponding trust profile, and is supervised through
explicit PID/status/health/stop commands. The stdio proxy uses the official MCP
SDK and does not auto-start the daemon.

**Consequences**: Engine remains local-first and scope-explicit. ADR-049 moves
MainFrame client config onto proxy + daemon; `serve-mcp` stays for compatibility
and isolated tests. Auto-start-from-proxy, authentication, remote exposure,
concurrency guarantees, and RAM/latency claims remain deferred or measured
elsewhere. Workbench remains the design/test source for future upgrades; root
`mindgraph/` is the promoted operational engine.

## ADR-047: Separable C-0 Filtering and Context Allocation (2026-07-27)

**Status**: Accepted
**Date**: 2026-07-27

**Context**: The dual-gate confirmatory protocol measures two apparatus independently — C-0 source eligibility and Speaker context allocation — across four conditions: baseline, C-0 only, Speaker only, both. `apply_dual_gate_governance` in `src/mindgraph/query.py` performs both jobs in one call: it requires a non-empty eligibility manifest, filters candidates against it, and only then applies seat and character budgets. Consequences:

- **Speaker-only is unavailable.** The helper refuses to run without a manifest and filters before seating, so there is no path that allocates over unfiltered candidates.
- **C-0-only is a fudge.** It can be approximated only by setting seat/char limits high enough to "effectively disable" them, which is a parameter choice rather than an absent step.

Without both arms, any measured difference cannot be attributed to a specific gate, and the protocol's per-gate decision rules (high-risk exposure, required-proposition coverage) cannot be evaluated. The evaluation project identified this dependency (W5) but explicitly declined to design it.

**Decision**:

1. **Extract two primitives** from the existing helper, preserving current behaviour exactly:
   - `_filter_by_c0_eligibility(results, manifest)` — manifest validation, identity/path/hash matching, and attachment of the consumed `eligibility_run_id`.
   - `_allocate_context_budget(results, max_seats, max_chars, quiet_keywords)` — seat shortlisting, the existing `quiet_keywords` swap heuristic, and the character budget with its truncation rule.
2. **Express all four arms as exact compositions** of those primitives, so a condition differs by the *presence or absence of a step*, never by parameter values:

   | Arm | Composition |
   | --- | --- |
   | baseline | `run_query` — neither primitive |
   | C-0 only | filter |
   | Speaker only | allocate |
   | both | filter → allocate (`apply_dual_gate_governance`, unchanged) |

3. **Expose two new public entry points**: `filter_by_c0_eligibility` and `allocate_ungoverned_context`. `apply_dual_gate_governance` keeps its name, signature, and behaviour.
4. **Constrain the ungoverned allocator** — it is an evaluation instrument, not a product capability:
   - named for the absence it carries, so `grep ungoverned` finds every call site;
   - requires keyword-only `evaluation_use_only: Literal[True]` with **no default**, so it cannot be called accidentally or positionally, and the acknowledgement is visible at the call site;
   - never sets `eligibility_run_id`, and asserts the returned rows carry `None`, so no future refactor can stamp governance identity onto ungoverned rows;
   - raises when handed an eligibility manifest — passing one signals the caller wanted the governed path;
   - stays out of `__all__`, the CLI, and the MCP surface. The evaluation harness imports it directly from the module.

**Rationale**: Allocation is **subtractive** — `allocate(results, …) ⊆ results`. It cannot admit a source that ungated `run_query` did not already return, so exposing it adds no retrieval reach beyond what the baseline path already provides. The security delta against today is zero; the genuine risk is *misinterpretation* — a caller concluding that "allocated" implies "governed" — which the naming, the explicit acknowledgement argument, and the null-provenance assertion address directly.

Extraction rather than reimplementation keeps the governed path byte-identical. The existing `tests/test_governance.py` cases must pass **unmodified**; that is the regression proof, and adapting them would void it.

**Consequences**:

- The confirmatory 2×2 becomes measurable, and the "effectively disabled limits" workaround for C-0-only is removed rather than documented.
- `apply_dual_gate_governance` gains no new behaviour; callers are unaffected.
- **This authorizes measurement only.** Promoting Speaker-only allocation to any production or default path is a separate decision requiring its own evidence; a passing 2×2 arm is not that evidence.
- Work proceeds workbench-first under a task packet, then a **separate root-promotion packet**. Root promotion requires: the five existing governance tests green and unmodified in both trees, the new allocation tests green, and no change to CLI/MCP response shape. The promotion packet is written after workbench is green rather than now, so it describes a real diff instead of a predicted one.
- ADR-035's retrieval model and ADR-033's link resolution are untouched; this is a consumer-side boundary change only.

## ADR-046: Dual-Pool WIP — Product Seats vs Eval Seats (2026-07-23)

**Status**: Accepted
**Date**: 2026-07-23
**Context**: ADR-041’s hard cap of 5 active projects forced constant pause/swap churn once MainFrame accumulated parallel evaluation suites (harness, tracker, process-eval, mindgraph-eval, claim-audit, <private-claims>, etc.) alongside product work (<private-product>, portfolio, <private-hub>, labs). Eval projects are often correctly “on” for scheduled probes and multi-week measurement programs; treating them as interchangeable product WIP seats made the cap unmaintainable without lying about state. Operator intent: <private-hub> is the strategic hub other projects serve — it should stay active without WIP-swap thrash.

**Decision**:
1. **Dual pool** for `project_state: active`:
   - **Product WIP cap = 5** — outcome/product projects (`wip_class: product`, default).
   - **Total active ceiling = 10** — product + eval combined.
   - **Eval actives do not consume product seats.**
   - **Anchor** (`wip_class: anchor`, default for `<private-hub>`): always-on strategic hub; consumes **neither** product nor total seats.
2. **`wip_class`** optional frontmatter: `product` | `eval` | `anchor`. When omitted:
   - `<private-hub>` → `anchor`
   - slug ends with `-eval` → `eval`
   - known instrument slugs → `eval` (`claim-audit-lab`, `<private-eval-e>`, `<private-claims>`, `<private-eval-c>`, `verified-done`)
   - else → `product`
3. **Enforcement** remains in `bin/sync-project-index --check` (and Focus Board total cap for product+eval). Evidence rules and vocabulary from ADR-041 are unchanged.
4. **Focus vs activation** (ADR-044) still separate — eval/anchor being active does not mean they are focus primary.

**Rationale**: Keeps a tight product focus budget while letting measurement infrastructure and the income hub stay honestly active. Total ceiling of 10 still prevents “everything active” sprawl among product+eval work.

**Consequences**: Operators pause product projects to free product seats; eval suites may remain active up to the residual total budget; <private-hub> should not be paused to free WIP. Workstation `ACTIVE_CAP` tracks the **product+eval total** ceiling (10). Explicit `wip_class` overrides heuristics when a slug is misclassified.

## ADR-045: Live Retention Classes and Staged Projects MindGraph Apply (2026-07-15)

**Status**: Accepted
**Date**: 2026-07-15
**Context**: After Phase 2 containment, the projects MindGraph manifest covers 28/28 real projects, but the installed projects DB still has incomplete namespaces. Operators need live-index coverage without dumping volatile `20_live/` telemetry into retrieval, and without one-shot mutation of `~/.mindgraph/mainframe-projects.sqlite` without a prove-then-promote path. Different live surfaces go stale at different rates.

**Decision**:
1. **Retention classes** for `20_live/` and related volatile state are policy authority in `.context/live-retention.md`: Authority (A), Append-only evidence (B), Derived projection (C), Reporter noise (D), High-volume ops (E). Soft caps are documented there; automation is later.
2. **Projects MindGraph stays coordination-only** — manifest-scoped Markdown under `30_projects/`. Never bulk-ingest `20_live` telemetry/events into the projects (or knowledge) index as a hygiene shortcut.
3. **Staged apply is required** for projects index mutation: `bin/mindgraph-projects-apply` supports `--plan` → `--stage` (temp/staging DB + receipt) → `--promote` (backup installed, replace only from a green receipt). Bare `mindgraph-refresh-projects --apply` remains available for experts but the recommended path is the staged packet.
4. **Staleness responses are class-specific** (rebuild projections, archive append-only, rewrite focus authority, re-stage index) — not a single “clean 20_live” cron.

**Rationale**: Separates “make retrieval cover projects” from “manage live operational volume,” keeps indexes rebuildable and trust-labeled, and makes promote an explicit operator boundary with evidence.

**Consequences**: Operators follow live-retention policy before/around index work. Stage receipts live under `20_live/system-health/mindgraph-projects-apply/`. Promoting requires a green stage. Soft retention caps are not auto-enforced yet. MG-004 namespace isolation tests remain a separate later unit.

## ADR-044: Focus Authority, Doctor Contract, and Separate Activation (2026-07-14)

**Status**: Accepted
**Date**: 2026-07-14
**Context**: July 10 system audit and scalability program left three design drafts (`plans/scalability/canonical-authority-map.md`, `mainframe-doctor-contract.md`, `p0-repair-packet.md`) unapproved while `<private-eval-b>` stayed paused. Live false-green still reproduces: `bin/session-open --json` reports `ok: true` for compound `STATE.md` focus whose derived project path does not exist. Implementation of `mainframe-doctor` and focus writers was blocked on operator decisions.

**Decision**:
1. **Focus authority location:** Canonical current focus lives under `20_live/focus/` — at minimum `current.yaml`, with append-only `decisions.jsonl` and `outcomes.jsonl` for history. Project READMEs continue to own project lifecycle state; focus only allocates discretionary attention.
2. **STATE.md role:** Human handoff **narrative** (what changed / remains / blocked / reentry). It must cite the focus revision when structured focus exists. It is **not** the parseable primary project identifier for session tooling after migration.
3. **Session open:** After implementation, reads structured focus first; validates that the primary project path and contract chain resolve. Missing/invalid focus or project is non-green. During a single migration window, `STATE.md` narrative parsing may remain a read-only fallback with an explicit degraded/unknown signal.
4. **Focus vs activation:** Selecting or changing focus does **not** change `project_state`. WIP activation/pause under ADR-041 remains a separate explicit operator action.
5. **Doctor program:** Accept the doctor contract as the health model (vector of claims; required `unknown` cannot aggregate to healthy; reporters ≠ checks). Accept the P0 repair packet as sequenced design input subordinate to the post-audit execution overlay. No repair writers or `bin/mainframe-doctor` ship under this ADR alone.
6. **Weekly human context (default, minimal):** When a focus decision is written, capture `capacity`, `fixed_commitments`, and `deliberate_deprioritizations` unless the operator supplies a fuller `operator_context`. Horizon goals may be empty without inventing them.

**Rationale**: Separates attention allocation from project lifecycle (ADR-041 WIP), kills compound-STATE false greens without making narrative the authority, and unblocks Phase 0 without authorizing mutations.

**Consequences**: Phase 0 design contracts are **accepted** with these bindings. Next executable work requires an explicit WIP swap and selection of ≤2 units (recommended first pair after activation: Unit 1.1 frozen baseline receipt, then Unit 1.3 fixture-only doctor shell). Schema and writers remain unbuilt until those units. ADR-041 WIP cap and project README authority are unchanged.

## ADR-Handoff — Typed research↔project handoffs (2026-07-13)

**Context**: After research-lane dogfood, “handoff to project” meant both gate-clearing decisions and low-urgency opportunities. One-size application handoffs either stole WIP `next_action` or buried real gates.

**Decision**: Formalize kinds (`gate`, `application`, `opportunity`, `constraint`, `experiment`, `craft`, `knowledge`, `split`, `close`) in `.context/workflows/research-project-handoff.md` with CLI routing that does **not** overwrite busy project `next_action` for `opportunity`/`knowledge`.

**Consequences**: Operators pick kind before handoff; receipts land in project `outputs/`; reverse gaps still use lane intake / research-lane-loop, not handoff-project.


This file captures meaningful project choices, especially trade-offs affecting reproducibility, scope, evidence quality, or system behavior.

Numbering note (2026-07-02): entries are newest-first; ADR-023 exists only as "ADR-023 (follow-up)" and ADR-026 was never assigned — both gaps stay unfilled so numbers keep matching external references.

## ADR-043: Research Lane Loop (Source-Literature → Synthesis)
**Status**: Accepted
**Date**: 2026-07-13
**Context**: Completing research for portfolio lanes required stitching source-literature (stops at inbox), ingest-minion, optional synthesis, and tracker updates from separate docs. Operators and agents often stopped after capture; the successful C28 full loop lived only in project log prose.
**Decision**: Define one **loopable research pass** as the completion unit for research-lanes work:
1. Workflow: `.context/workflows/research-lane-loop.md` (command card, resume map, definition of done).
2. Skill: `.agents/skills/research-lane-loop/SKILL.md` (agent orchestration).
3. Unit: one lane × one phase (foundation → taxonomy → specialization → application); default 3–4 sources; start at source-literature; end at knowledge synthesis + tracker close; then decide next phase/lane/archive.
4. Source-literature remains the discovery skill and hands off into loop steps 4–7 rather than treating inbox as done.
**Rationale**: Easy to run, easy to resume, hard to skip synthesis. Priority (which lane) stays in `bin/lane-intake`; how a run finishes is now explicit and repeatable.
**Consequences**: Weekly cadence prefers full loops over open-ended search. Project ADR-009 in `30_projects/<private-research>/decisions.md` mirrors this for the tracker. Synthesis skip requires an existing note that already meets the stop condition plus a log line.

## ADR-042: Nested Local Repos For High-Churn Private Projects
**Status**: Accepted
**Date**: 2026-07-03
**Context**: `30_projects/*` is intentionally gitignored so project contents stay private, but that makes high-churn projects invisible to every git-based activity signal — the 2026-07-01 audit misread <private-hub> (the busiest control plane) as stale for exactly this reason. quant-markets-lab already carried a nested repo as precedent without conflicts.
**Decision**: High-churn private projects may initialize a nested local git repository at the project root. <private-hub> is now one (initial commit f519bb6, 234 files). Nested repos are **local-only — no remotes**. If a remote is ever wanted it must be private and the history must pass the leak-detection grep (prior-username/local-path rule) first. Nested `git log -1` timestamps count as activity evidence for ADR-041 states and the ADR-040 checkpoint derivation.
**Rationale**: History and diffs for the places where the most decisions happen, plus an honest machine-readable activity signal, without weakening the outer repo's privacy boundary.
**Consequences**: The evidence scanners (sync-project-index, session-close) prefer nested-commit recency over raw mtimes when fresher. Operators must remember nested repos have their own working-tree hygiene; MainFrame's session-close does not yet check nested-tree dirtiness (candidate for a later phase).

## ADR-041: Evidence-Based Project Activity States With WIP Cap
**Status**: Accepted
**Date**: 2026-07-03
**Context**: The 2026-07-01 audit found 21+ of 25 projects self-reporting `project_state: active`, several with no file activity for weeks (content-engine 27d idle) and two with missing or malformed frontmatter. The `updated:` field is hand-typed and drifts. Meanwhile the operator's real problem is deciding where to put focus — a state layer where everything is "active" answers nothing.
**Decision**:
1. **State vocabulary**: `active`, `paused`, `planned`, `blocked`, `suspended`, `shipped`, `trashed` — semantics recorded in `30_projects/AGENTS.md`. Any other string is a checker error.
2. **Evidence rule**: `active` requires activity evidence within 14 days — newest of bounded file-mtime scan and nested-repo `git log -1` (same derivation as the ADR-040 checkpoint) — plus a `next_action`. `paused` requires a `next_action` reentry pointer. Self-reported `updated:` carries no authority.
3. **WIP cap (original)**: at most **5** projects `active`; the checker fails loudly on breach. Activating a sixth means pausing one first. **Superseded for pool structure by ADR-046** (product seats remain 5; total ceiling 10; eval seats separate).
4. **Enforcement**: `bin/sync-project-index --check` validates all rules and the generated index gains an `Evidence` column (last observed activity date). `--write` still writes but repeats the problems on stderr.
5. **Sweep applied 2026-07-03**: active set reduced 21 → 5 (<private-eval-a>, claim-audit-lab, <private-hub>, <private-eval-b>, <private-research>); 16 projects paused with reentry pointers; <private-eval-d> and <private-eval-e> got compliant frontmatter.
**Rationale**: Truth from evidence, not self-report (truth-layer design principle 2). The cap makes the focus decision explicit and visible instead of deferred, and gives the workstation's game layer a real mechanic (desks = WIP cap, Phase 4 Unit 7).
**Consequences**: `session-close`'s sync-project-index auto action now stays "needed" while any state lies, so drift is loud at every close and in the tracker feed. Editing a README to pause a project bumps its mtime, so freshly-swept projects show today's evidence date until they decay naturally. The audit's <private-hub> false positive is fixed by construction: nested-repo commits are first-class evidence. **See ADR-046** for dual-pool product vs eval seats.

## ADR-040: Session Checkpoints Attach To Compaction Events
**Status**: Accepted
**Date**: 2026-07-02
**Context**: The 2026-07-01 bird's-eye audit found the state layer drifting out of truth because manual rituals (STATE.md narrative, session-close) run slower than the work rate. `bin/session-close` is operator-run; nothing fires it automatically. Compaction cannot be triggered *from* a shell script (it is a context operation inside the agent client), so the integration is inverted: the ritual hooks onto compaction and session-end events that already carry telemetry hooks.
**Decision**:
1. **`bin/session-close --checkpoint`** — a fast (<1s), prompt-free evidence snapshot. It derives active projects from `30_projects/*` file mtimes plus nested-repo `git log -1` (bounded scan, no self-reported `updated:` fields), summarizes today's telemetry zones, and reads weekly-eval staleness directly from `schedule-runs.jsonl` (no subprocess chain). It appends a dated snapshot block to `20_live/last-handoff-draft.md` and a machine record to `20_live/workstation/session-close-feed.jsonl`.
2. **PreCompact hook** runs `session-close --checkpoint --hook-stdin` after the existing `workflow-event` telemetry hook: every mid-session compaction becomes a state checkpoint taken before context is summarized. `--hook-stdin` keeps only derived fields (sha256[:16] session hash — same scheme as `bin/workflow-event` — event name, trigger); prompt or transcript content is never copied.
3. **SessionEnd hook** runs `session-close --check --feed --hook-stdin`: the full check result (pending autos, warnings, eval staleness) is appended to the same feed. Feed mode exits 0 once the record is written — the outcome lives in the record, so a session end never reports a hook failure for pending rituals.
4. **Draft file ownership**: the digest (`--apply`) owns the scaffold above the `## Session Checkpoints (auto)` heading; the checkpoint owns everything below it (derived-active line rebuilt each run, newest five snapshots kept). Each writer preserves the other's region. STATE.md narrative remains human-approved — checkpoints draft, the operator promotes at true session close.
**Rationale**: Design principle 1 of the truth-layer plan — make rituals cheaper than skipping them by automating the draft and keeping the human on the approve step. Attaching to compaction converts the operator's existing habit (compacting long sessions) into automatic state capture, and the JSONL feed gives the workstation tracker (Phase 4 Unit 6 Focus Board) one evidence surface for close-list and attention signals.
**Consequences**: `20_live/last-handoff-draft.md` gains a machine-owned tail section; both files stay gitignored under `20_live/*`. The feed grows one line per compaction/session-end. Derived-vs-declared drift is now measured on every checkpoint — the first live run immediately flagged `<private-hub>` as hotter than the declared active project, confirming the audit's activity-blindness finding. Phase 2 (evidence-based activity states, WIP cap) consumes the same derivation. Hook timeouts stay at 5s; measured checkpoint cost is ~0.6s.

## ADR-039: System Integrity Audit Workflow and Generalized R1–R8 Reconstruction Rules
**Status**: Accepted
**Date**: 2026-06-29
**Context**: Modern software workflow and AI pipeline audits (such as reviews for Eldorado Node and Agent Trust Gate) were previously written using domain-specific terms (like pharma QC's LIMS, OOS, and SOP versioning). We need a generalized, system-agnostic procedure and template to standardise data-integrity audits and allow agents and operators to audit technical architectures consistently. (Originally misnumbered ADR-025 and appended at the file bottom; renumbered and moved 2026-07-02 — ADR-025 is "MindGraph Source Lives In A MainFrame Project Workbench".)
**Decision**:
1. Created `.context/workflows/system-integrity-audit.md` to serve as the canonical procedure and template for system integrity audits.
2. Generalised the R1–R8 pharma-inspired checklists into eight system-agnostic data-integrity principles (Raw Source Capture, Logic/Rule Versioning, Run Initialization Log, Sequenced Execution Path, Outcome-to-Source Traceability, Controlled System Overrides, Attributable Approval Gates, and Exportable Evidence Package).
3. Integrated the new workflow into existing discovery and engagement files (`.context/workflows/<private-workflow>.md` and `30_projects/<private-hub>/<private-subarea>/meeting-audit-protocol.md`) for high visibility during client and peer engagements.
**Rationale**: Standardising the data-integrity rules into a reusable system-agnostic format makes it easy to run audits on diverse client architectures while keeping the successful "authoritative vs. derived" and "verification trace" structures from previous reviews.
**Consequences**: Future workflow audits will reference this standard protocol and template. Subagents can consume `.context/workflows/system-integrity-audit.md` directly to perform initial data-integrity evaluations.

## ADR-038: Thread Creation Uses Existing Prompt And Session Contracts
**Status**: Accepted
**Date**: 2026-06-28
**Context**: New-thread prompts were being assembled from live project context, but MainFrame had no short workflow connecting thread creation to the existing prompt-design and session lifecycle contracts.
**Decision**: Add `.context/workflows/create-thread.md` as a lightweight pointer. Prompt-design judgment remains in `.agents/skills/prompt-creation/`; context loading and handoff state remain in `session-open` and `session-close`; a separate thread is created only when the user explicitly requests one.
**Rationale**: A pointer makes thread handoffs consistent without duplicating prompt-engineering guidance or creating another large procedure.
**Consequences**: New thread prompts should name the objective, relevant authority, boundaries, expected first response, and completion or approval gate. Plan-shaped handoffs remain context rather than implementation approval.

## ADR-037: Structural Files Use Shared Profile Schema
**Status**: Accepted
**Date**: 2026-06-24
**Context**: MainFrame has a growing set of structural files: root/lifecycle contracts, project-local `AGENTS.md` files, `HARNESS.md`, workflows, skills, subagents, templates, manifests, configs, workbench contracts, and eval-methodology files. The 2026-06-23 structural catalog showed that many are intentionally ignored/private, but still architecturally meaningful.
**Decision**:
1. Add `.context/templates/structural-file-profile.md` as the shared schema for creating, auditing, and tightening structural files.
2. Treat project-local structural files as part of the same framework even when they are private or ignored by the outer repo.
3. Keep `AGENTS.md` as the compact always-on contract and `HARNESS.md` as the MainFrame harness-policy contract; route long procedures to workflows, repeated agent judgment to skills, specialized roles to `agents/`, and deterministic enforcement to scripts/config/tests/hooks.
4. Catalogue project structural files with tracked/ignored status and authority/trust labels before promoting or tightening them.
**Rationale**: A shared profile reduces drift without turning every contract into a long manual. It also prevents ignored project files from disappearing from architecture reviews while preserving the public/private boundary.
**Consequences**: Future structural-file audits should include the profile fields or explain why a file type intentionally omits them. Root contracts now point to the schema. Tightening local `AGENTS.md`, workbench contracts, methodology files, and templates should start from the profile rather than ad hoc rewriting.

## ADR-034: Query-Time Semantic Association
**Status**: Accepted (shipped 2026-06-19)
**Date**: 2026-06-19
**Context**: MindGraph uses semantic search for query→chunk ranking and explicit edges for document→document traversal (`--expand`). Cross-domain material often co-ranks on well-formed queries but has no wikilink path — so `--expand` cannot surface it and `graph_neighbors` from a single note cannot either. The operator wants deeper connection discovery without adding a parallel trust taxonomy (MainFrame lifecycle trust already lives in index scope, result metadata, and Query Station grouping).
**Decision**:
1. Add a fourth retrieval signal **`associated`**: from fused seed documents, embed a per-doc association text (title + primary chunk), run vec kNN, promote to doc level, append results with `signal="associated"`, `semantic_distance`, and `weak_fit` — same `QueryResult` shape as fused/expanded rows.
2. **Append-only semantics:** Association does not enter RRF fusion math (mirrors Phase 3 `--expand`). CLI flag `--associate`; MCP `query` parameter parity.
3. **Per-index execution:** Association runs inside one SQLite scope at a time; federated grouping remains Query Station responsibility (ADR-032).
4. **Phase record:** `30_projects/mindgraph/plans/phases/phase-9-semantic-association.md`.
**Rationale**: Reuses existing chunk embeddings and semantic ranking primitives — no offline semantic edge table, no LLM entity extraction. Closes the doc-to-doc discovery gap while keeping signals inspectable.
**Consequences**: `Signal` type gains `"associated"`. mindgraph-eval gains cross-domain probes with no wikilink path. Latency budget must be measured on full corpus before defaulting `--associate` in agent workflows. Offline precomputed semantic edges remain deferred.

## ADR-036: Scheduled MainFrame Eval Suites With launchd And Session Visibility
**Status**: Accepted
**Date**: 2026-06-22
**Context**: ADR-018 established the process-evaluation loop, and G46 added `bin/eval-registry`, but eval runs still depended on operator memory. A one-off weekly script would silently rot without launchd, staleness checks, or session hooks.
**Decision**:
1. **`bin/eval-schedule`** runs daily/weekly suites, writes `20_live/eval-registry/schedule-runs.jsonl`, and installs macOS launchd agents (`com.mainframe.eval-schedule.{daily,weekly}`).
2. **`bin/eval-schedule check`** exits non-zero when launchd is missing, the weekly run is stale (>8 days), or the last weekly run failed.
3. **Session hooks** surface health: `bin/session-open` prints eval status; `bin/session-close --check` warns when unhealthy; handoff digest includes `eval-schedule status`.
4. **Operator card** at `20_live/eval-registry/OPERATOR.md` documents the weekly review ritual and commands.
5. Weekly MindGraph probe defaults to a **four-query fused regression** (~25s); `--full-probe` retains the full matrix.
**Rationale**: Measurement only improves the system when it runs on cadence and surfaces failures before they become folklore. Wiring eval health into session open/close makes neglect visible without blocking unrelated work.
**Consequences**: EV01 lane owns the ritual; `<private-eval-b>` receives dated `scheduled-weekly` outputs; harvest hygiene excludes `evaluation-feedback.md`. Promotions from scheduled runs still require human review per ADR-018.

## ADR-035: MindGraph Retrieval Model — Hybrid Explicit Graph + Chunk RAG
**Status**: Accepted
**Date**: 2026-06-19
**Context**: After ADR-033 link fixes and federation/graph-RAG literature review, the operator asked whether MainFrame should adopt a different retrieval architecture (GraphRAG, LightRAG, vector-only, HippoRAG PPR, newer embedders) instead of the current MindGraph model.
**Decision**: **Keep the hybrid model** as the MainFrame default:
1. **Per-scope SQLite** with FTS5 + chunk embeddings + explicit operator-authored edges (plus ADR-033 frontmatter links).
2. **RRF fusion** for query→chunk ranking; graph BFS for explicit expansion; **semantic association** (ADR-034) for implicit doc neighborhoods — four inspectable signals, not one merged score.
3. **Do not** replace dual lifecycle indexes with a single LLM entity graph or GraphRAG community vault.
4. **Empirical upgrades only** for embedding model and optional cross-encoder rerank — gated by `mindgraph-eval` A/B on a frozen query set, not ad hoc swaps.
5. **Planning reference:** `30_projects/mindgraph/plans/retrieval-model-review.md` for landscape comparison and evolution order.
**Rationale**: MainFrame's job is lifecycle-aware **nomination**, not answer generation. The current shape matches hybrid-memory "narrow then expand" and ADR-032 federated Query Station. GraphRAG-style systems optimize global private-corpus QA with LLM-extracted graphs — different trust and cost profile. Gaps (sparse cross-domain links, no doc-to-doc semantic hop) are addressable incrementally without architectural replacement.
**Consequences**: Phase 9 ships association before embedder migration or GraphRAG community experiments. Optional overview/community layers stay opt-in and low-promotion. mindgraph-eval owns comparative measurements; README/portfolio claims remain "design intent" until probes pass.

## ADR-033: Dual-Channel Graph Links and Canonical Slug Resolution
**Status**: Accepted
**Date**: 2026-06-19
**Context**: MainFrame notes commonly declare relationships in frontmatter `links:` (especially syntheses written directly into `10_knowledge/`) while MindGraph only indexed body `[[wikilinks]]`. Authors also link using Obsidian-style trailing slugs (`gxp-pharma-source-catalog`) while files use the canonical `YYYY-MM-DD__domain__type__slug` stem. The mismatch produced rich metadata graphs with sparse traversable edges and widespread phantom links.
**Decision**:
1. **Dual-channel graph ingest:** `extract_document_graph_edges` indexes both frontmatter `links:` and body wikilinks, deduplicating on `target_id` (one edge per target; body `relationship_type` wins when frontmatter had none).
2. **Canonical slug resolution:** `LinkResolver` resolves unique trailing slugs from canonical filename stems (`…__slug` after the type segment) in addition to full stem, sibling path, and unique title matches. Ambiguous slugs remain dangling.
3. **Authoring contract** (documented in `.context/primitives.md` § Link Convention): either channel is sufficient; prefer unique trailing slugs or full stems; do not wikilink `30_projects/` from knowledge notes until bridge registry exists.
**Rationale**: Fixes the convention mismatch without requiring a corpus-wide rewrite first. Frontmatter-only syntheses immediately contribute to `--expand`; trailing-slug links match how operators already write `links:` arrays.
**Consequences**: `bin/mindgraph-refresh` may change edge counts on unchanged file bodies when frontmatter `links:` resolve newly. mindgraph-eval baselines that measure graph degree should be re-run after refresh. Project cross-references stay prose or future bridges — not auto-indexed wikilinks.

## ADR-031: MindGraph First-Class Workspace Integration
**Status**: Accepted
**Date**: 2026-06-19
**Context**: MindGraph active source code lived inside the private project layer at `30_projects/mindgraph/workbench/`. This created stale paths, made wrapper and workstation configurations complex, and mixed workspace retrieval infrastructure with a development/upgrade sandbox.
**Decision**:
1. Copy the active engine source directories (`src/`, `tests/`, `pyproject.toml`, `README.md`, `LICENSE`, `.gitignore`) into a new, first-class root directory `mindgraph/`.
2. Initialize a dedicated virtual environment in `mindgraph/.venv/` and install the package locally.
3. Update `bin/mindgraph` wrapper to check `mindgraph/.venv/bin/mindgraph` first, falling back to the project workbench version if needed.
4. Modify all references in global/project documentation, workflows, and conventions to point to the root-level `mindgraph/` engine.
5. Extend the local workstation dashboard API (`workstation/server.mjs`) and UI panel (`workstation/components/mindgraph-panel.mjs`) to support direct index refreshing and semantic graph neighbor navigation.
**Rationale**: Moving the active engine to the root establishes MindGraph as standard MainFrame retrieval infrastructure, separating it from the sandbox upgrade workbench.
**Consequences**: Future engine features or upgrades are developed/tested in the `30_projects/mindgraph/` sandbox, then promoted to the root `mindgraph/` directory. All daily execution and workstation interfaces target the root engine.

## ADR-032: MindGraph Query Station Interpreter
**Status**: Accepted for planning
**Date**: 2026-06-19
**Context**: ADR-030 made dual MindGraph querying mandatory for project planning, but the current user-facing workstation and MCP examples still behave mostly like single-DB clients. A review of local reality also found that `mainframe-projects.sqlite` can be incomplete because the current projects refresh ingests one project root at a time and prunes against each root separately. The operator wants a structural query station for agents and humans while preserving strong separation between durable knowledge and active project state.
**Decision**: Create a planned MindGraph Query Station as a MainFrame interpreter over separate stores, not as a merged database. The station should expose modes such as `knowledge`, `projects`, `federated`, `apply`, `extract`, and `trace`; group results by lifecycle/trust zone; emit copyable `MindGraph Query Pass` blocks for plans and task packets; and preserve per-index rank, source root, namespace/project, trust profile, path, query string, and fit/scope warnings. Engine prerequisites and response contracts are planned in `30_projects/mindgraph/`; the human/agent UI belongs in `workstation/` and is coordinated by `30_projects/<private-eval-a>/`.
**Rationale**: MainFrame's useful boundary is that `10_knowledge/` answers durable learning questions while `30_projects/` answers active work/status questions. A station should make that boundary easier to use, not dissolve it. Fixing multi-root project ingest and explicit provenance first prevents the UI from confidently presenting incomplete or mislabelled project context.
**Consequences**: Agents should use the station when available, or a CLI-equivalent dual query pass for station modes that have not shipped yet. The first implementation slice ships namespaced `ingest-many`, provenance-rich query rows, manifest-backed project refresh, and workstation `knowledge`/`projects`/`federated` modes with copyable Query Pass output. Workstation implementations must not compare raw semantic distances across indexes as if they were calibrated together, infer trust from path strings, or treat retrieval nominations as verification. Cross-index hard bridges require explicit approval; soft bridges remain provisional suggestions.

## ADR-030: MindGraph Querying Integrated into Project Planning
**Status**: Accepted
**Date**: 2026-06-18
**Context**: While MainFrame has dual MindGraph indexes (`mainframe.sqlite` for durable knowledge and `mainframe-projects.sqlite` for active projects), querying them was not structured as an obligatory step during project creation, master planning, phase planning, or task packet preparation. This created a risk of agents or operators duplicating work, missing historical lessons, or violating existing patterns.
**Decision**: Make querying both MindGraph databases an explicit, required step in the planning and project setup workflows:
1. **Global Contract**: Add a MindGraph sourcing rule to `AGENTS.md` (global).
2. **Project Contract**: Update `30_projects/AGENTS.md` to require querying before initializing new plans, task packets, or project phases, and updating the planning rules.
3. **Setup Workflow**: Update `.context/workflows/create-project.md` to incorporate a mandatory MindGraph scan step.
**Rationale**: By structuring MindGraph retrieval as a pre-requisite for planning, we guarantee that all active work leverages the synthesized lessons in `10_knowledge/` and active project context in `30_projects/` from the outset.
**Consequences**: Planning documents must document the query strings used and their key findings. Agents must run these query sweeps before suggesting architectures or writing task packets.

## ADR-029: MainFrame Epistemic Standard
**Status**: Accepted
**Date**: 2026-06-17
**Context**: `EPISTEMIC_STANCE.md` had four core rules but no canonical methodology sources, no operational confidence language, and no structured appraisal workflow. The operator required truth-seeking to rank above vibes across all MainFrame work. Existing machinery (`needs-audit`, audit-sweep, credibility tiers) lacked an evidence base in established epistemology and research methodology.
**Decision**: (1) Capture a 12-source epistemics canon via source-literature into `10_knowledge/knowledge-systems/epistemics/` (local). (2) Write synthesis notes `note__mainframe-epistemic-standard` and `note__epistemics-source-map`. (3) Expand `EPISTEMIC_STANCE.md` with claim types, GRADE certainty language, evidence minimums, disconfirmation duty, and promotion gate. (4) Add `.context/workflows/epistemic-standard.md`. (5) Extend credibility-tiers with GRADE operational mapping. (6) Wire agents (`extraction-agent`, `ingest-agent`, `source-literature-agent`, `ingest-source`, `AGENTS.md`).
**Rationale**: Grounds existing post-placement audit model (ADR-019) in peer-reviewed and institutional sources. GRADE certainty gives shared vocabulary for synthesized claims. CASP-adapted checklist makes "truth over vibes" procedurally enforceable for operators and agents.
**Consequences**: All claim-bearing work uses confidence language. `stable` promotion requires operator verification or audit clearance — never LLM alone. Epistemics sub-wiki is the local evidence base; tracked repo carries the contract. Retrofitting existing domain notes with confidence labels is operator backlog. Epistemic research system (suspended) may later consume GRADE scores in auditor scoring.

## ADR-028: Source-Literature Workflow Complements Ingest
**Status**: Accepted
**Date**: 2026-06-17
**Context**: Ingest (`ingest-minion` + `ingest-source`) assumes files already exist. Peer-reviewed and institutional source discovery — credibility tiers, deduplication against `10_knowledge/`, bibliographic capture — had no operator workflow or agent skill. Negotiation gap-fill and data-integrity research exposed the gap directly.
**Decision**: Add upstream source acquisition as a paired workflow + skill: `.context/workflows/source-literature.md`, `.agents/skills/source-literature/` (with `references/credibility-tiers.md`), and `agents/source-literature-agent.md`. Captures land in `00_inbox/` as `type: raw` stubs; handoff to existing ingest pipeline unchanged.
**Rationale**: Discovery and enrichment are different lifecycles (ADR-009 minion vs subagent split). Credibility gating requires judgment; routing stays deterministic. Tiers label evidence type, not verified truth — consistent with `EPISTEMIC_STANCE.md`.
**Consequences**: Agents invoke `source-literature` before ingest when the user needs literature search. Run notes document queries, accept/reject decisions, and dedup hits. `.claude/skills/source-literature.md` mirrors the canonical skill. First exercised on negotiation compensation/initiation gap-fill and data-integrity strands (PDA 2018, Schneier & Kelsey 1999).

## ADR-027: Knowledge Index Is Local, Template Is Public
**Status**: Accepted
**Date**: 2026-06-17
**Context**: `10_knowledge/index.md` lists the live durable-knowledge domain inventory. Like the project index, it can expose private or still-forming areas before they are ready for the public repo.
**Decision**: Ignore the live `10_knowledge/index.md` and track `10_knowledge/index.template.md` instead. The template preserves the domain-inventory shape, promotion rules, seed-domain rule, and navigation aids without publishing the current inventory.
**Rationale**: The public repo should document the operating pattern without leaking private knowledge architecture or forcing every local domain change into Git history.
**Consequences**: Operators maintain `10_knowledge/index.md` locally. Public docs and fresh checkouts use `10_knowledge/index.template.md` as the scaffold. Any tool or workflow that mentions the live index should treat it as local state.


## ADR-025: MindGraph Source Lives In A MainFrame Project Workbench
**Status**: Accepted
**Date**: 2026-06-17
**Context**: MindGraph started as a portfolio live asset, but MainFrame now uses it as operational retrieval infrastructure and evaluates it through `30_projects/mindgraph-eval/`. Keeping the engine source under `projects/portfolio/live-asset/mindgraph/` created stale path references, split planning surfaces, and made MainFrame wrapper configuration depend on a different workspace.
**Decision**: Move MindGraph's active source into `30_projects/mindgraph/workbench/` as a nested project workbench with fresh post-migration Git history. Keep `30_projects/mindgraph/` as the coordination surface (`README.md`, `AGENTS.md`, `decisions.md`, `log.md`, `plans/`) and keep `30_projects/mindgraph-eval/` as the separate evaluation harness for retrieval-quality probes and raw run artifacts. The root `bin/mindgraph` wrapper now prefers the local workbench venv before falling back to `mainframe.mindgraphBin` or `PATH`.
**Rationale**: The project-workbench pattern keeps active source close to the system that exercises it while preserving MainFrame's public/private boundary. Separating source from eval avoids mixing implementation decisions with measured retrieval evidence. A fresh workbench history matches the existing MainFrame migration convention and keeps pre-migration history in the portfolio repo.
**Consequences**: Portfolio registry files point to MainFrame instead of carrying an active source copy. Active MindGraph plans and path references now resolve under `30_projects/mindgraph/`. Historical eval reports may still mention the old portfolio path because they record the environment that produced those runs.

## ADR-020: Seed Domains, Legacy-System Consolidation, And Duplicate Deletion
**Status**: Accepted
**Date**: 2026-06-10
**Context**: Batch pass 2 (ADR-019 batch mode) surfaced three gaps. The domain-creation criteria (5+ meaningful files, recurring use) blocks legitimately new research areas at the moment exploration starts — the first two captures of a distinct topic had no honest destination. Old-system operational docs were being adopted into multiple active projects, scattering pre-MainFrame material the operator has not yet decided to promote. And exact-duplicate working copies were being parked even though batch `source-files/` snapshots already preserve the bytes and the canonical copy is routed.
**Decision**: (1) **Seed domains**: a new top-level `10_knowledge/` domain may be created from one or two strong captures when the topic is clearly distinct from existing domains and active research is expected to bring more — operator confirmation still required (ADR-011 unchanged). Seed domains that stay small without recurring use merge back into an index entry or park. First instance: `software-practice`. (2) **Legacy consolidation**: all old-system documents adopt into `30_projects/<private-migration>/raw-materials/legacy-systems/<system>/` (rule B1); nothing legacy lands in active projects until the operator explicitly promotes it. The pass-1 adoptions into content-engine relocate accordingly. (3) **Duplicate deletion**: exact-duplicate working copies (batch-manifest or body-hash matches) are deleted rather than parked; the ledger records `duplicate-removed` with the canonical path.
**Rationale**: Seed domains keep the knowledge architecture honest about new research instead of forcing weak fits into old domains or stranding captures in exception queues. A single legacy section preserves everything ("don't lose my old stuff") while deferring promotion judgment to the operator. Deleting exact duplicates is safe because provenance lives in the snapshots and the canonical copy; parking them would re-create the clutter the migration exists to remove.
**Consequences**: `10_knowledge/index.md` documents the seed-domain rule and the new domain. `routing-policy.md` gains R11 and B1, P6 (stale generated artifacts), and an amended P3. Relocations of previously adopted legacy docs are recorded as append-only ledger rows, not edits to prior rows.

## ADR-019: Tiered Ingest Autonomy With Review-After And Epistemic Audit Integration
**Status**: Accepted
**Date**: 2026-06-10
**Context**: The two-pass ingest design (ADR-009, ADR-011) gates every file on per-file operator confirmation. At organic capture volume that is fine; against the registered migration backlog (ADR-016/017) it stalls — lanes age while the operator owes synchronous attention on every file. The safety case for confirm-before-apply is weaker than it looks: raw bytes are batch-snapshotted and hash-registered, routing never overwrites, and the disposition ledger is append-only, so a misplaced clip is cheap to detect and reverse. Separately, the epistemic research system project now runs a continuous local-LLM audit loop — claim extraction, confidence scoring, `needs-audit` tag sweeps of `10_knowledge/`, and a pending-review surface in `20_live/epistemic-audit/` — that can verify routed material after placement.
**Decision**: Ingest classification moves from approve-before to review-after, governed by the rules in `.context/routing-policy.md` and three tiers:
- **Tier A (rule-matched, auto-apply)**: files matching a named policy rule get frontmatter, canonical rename, `bin/prep-ingest`, and pass-2 routing without per-file confirmation. Routed raw clips are tagged `needs-audit` so the epistemic audit sweep verifies them after placement. Ledger rows cite the rule that fired.
- **Tier B (exception)**: no rule match, weak fit, or a proposed new domain. The file stays in `01_ingest/ready/` with a `routing-exception` tag and a one-line `routing_note:`; the operator clears these from a single review table.
- **Tier C (always human)**: new top-level domains (ADR-011 unchanged), anything destined for `20_live/`, promotion to `stable`, and `rejected` dispositions.
For registered migration batches, the ingest-agent classifies the whole lane in one pass and emits one review table. The operator's first full-table review doubles as the ADR-018 baseline: agreement is measured from their corrections, and auto-apply at scale is enabled per rule only where agreement is high. Rules below threshold stay Tier B until refined.
**Rationale**: Confirmation-before-action duplicates protections the system already provides after the fact, and it prices operator attention into every file instead of every rule. Named rules amortize judgment; the epistemic audit loop restores verification where confirmation was removed, so placement becomes cheap and reversible while truth-claims still get audited continuously. Machine-routed and machine-audited material stays labeled (`needs-audit`, audit statuses), preserving the epistemic stance rather than bypassing it.
**Consequences**: `routing-policy.md` becomes a maintained contract — repeated Tier B corrections should graduate into named rules by commit. Ledger rows and frontmatter must keep machine placement distinguishable from human-verified knowledge; `status: stable` remains exclusively human. The epistemic research system's write surface into `10_knowledge/` stays limited to labeled claim and audit artifacts governed by its own project ADRs; classification itself is not delegated to its local models until an ADR-018 evaluation shows rule-level agreement with operator choices. The operator's role shifts from pipeline operation to exception clearing and policy maintenance.

## ADR-018: Process Evaluation Uses Baseline, Outcome Samples, And Reruns
**Status**: Accepted
**Date**: 2026-06-07
**Context**: MainFrame has deterministic tests, dry-run checks, workflow telemetry, and focused evaluations for MindGraph and writing style, but no shared system-level loop for deciding whether an operating process is effective. Tool telemetry measures activity and some failures, but it does not establish task quality, workflow adoption, or outcome correctness.
**Decision**: MainFrame process evaluation will use a baseline -> focused change -> rerun loop documented in `.context/workflows/process-evaluation.md`. Each evaluation starts with a specific question, combines deterministic checks with representative outcome samples, classifies findings by cause, and limits implementation to one or two improvement slices before rerunning the same checks. Repeated patterns are promoted according to their nature: deterministic operations to `bin/`, operator sequences to `.context/workflows/`, repeated agent judgment to `.agents/skills/`, and uncertain experiments to private project workbenches.
**Rationale**: This preserves the value of telemetry without mistaking activity for quality. A shared evaluation loop also makes improvements comparable over time and reduces the chance that one-off fixes become untested process changes.
**Consequences**: Evaluation reports should state telemetry coverage limits, preserve baseline evidence, distinguish intentional backlog from defects, and record accepted workflow changes in `DECISIONS.md`.

## ADR-017: Migration Batches Preserve Source Bytes And Use Append-Only File Ledgers
**Status**: Accepted
**Date**: 2026-06-06
**Context**: ADR-016 established immutable, hash-backed batch registration for repeated second-brain imports. The June 6 migration sweep showed that a manifest alone can detect later file replacement but cannot restore the replaced bytes. It also showed that lifecycle handling drifted because the immutable manifest could not record later per-file decisions without becoming stale.
**Decision**: Each second-brain migration batch stores a batch-local `source-files/` snapshot under `30_projects/<private-migration>/raw-materials/batches/<batch-id>/` and initializes an append-only `disposition-ledger.csv` with one `unresolved` row per registered file. The manifest remains immutable classification evidence. Later decisions such as `retained`, `promoted`, `archived`, `duplicate-removed`, `parked`, `unverified`, `superseded`, or `rejected` append new ledger rows rather than mutating the manifest.
**Rationale**: Recoverable source bytes preserve provenance and make later audits or rollback possible even if the flat inbox changes. A separate ledger keeps lifecycle handling inspectable without rewriting historical registration evidence.
**Consequences**: Registration remains non-destructive to `00_inbox/` and still refuses overwrites. Existing pre-correction batches may need ledger backfills from already-recorded project evidence, and ambiguous rows should stay unresolved instead of being inferred. Source snapshot backfills are only safe when the current source still hash-matches the registered manifest.

## ADR-016: Rolling Second-Brain Migration Uses Immutable Batch Registration
**Status**: Accepted
**Date**: 2026-06-05
**Context**: Repeated imports from the previous second brain mix current state, historical snapshots, durable knowledge, project records, templates, and generated artifacts.
**Decision**: Register each drop as an immutable, hash-backed batch before routing or cleanup. Each batch receives a unique ID, complete file manifest, exact-duplicate groups, and reconciliation record. Reconcile live state claim by claim and require dated evidence before promotion.
**Rationale**: Bulk ingest or whole-file source-of-truth selection would create competing state records and could silently discard useful history.
**Consequences**: `00_inbox/` remains the safe arrival boundary. Registration does not move or edit source files. Content Engine state remains anchored to its external production workspace. Durable knowledge follows confirmation-gated ingest, while volatile state uses dated snapshots or append-only timelines.

## ADR-001: Centralized vs Local Agent Instructions
**Status**: Accepted
**Date**: 2026-05-20
**Context**: Should each lifecycle folder contain its own `AGENTS.md` file, or should all instructions be centralized?
**Decision**: We will enforce a global `AGENTS.md` at the root, and keep repeatable workflows in `skills/`. We will ONLY place local `AGENTS.md` files in subdirectories that have special defensive rules or processes (e.g. `20_live`).
**Rationale**: Prevents agent context bloat and repetitive instructions while still allowing for localized safety rules.

## ADR-002: MindGraph Integration Strategy
**Status**: Accepted
**Date**: 2026-05-20
**Context**: Should the MindGraph GraphRAG system be deeply coupled into the Mainframe ingest pipeline?
**Decision**: MindGraph will remain a separate project and will be wired in as a complementary RAG feature. The Mainframe will have its own ingest pipeline, but will use the same tracking/metadata schema so MindGraph can index it effectively.
**Rationale**: Keeps the Mainframe ingestion simple and markdown-first, separating the graph database concerns from the file organization concerns.

## ADR-003: Automation Tooling for Ingest
**Status**: Superseded by ADR-007
**Date**: 2026-05-20
**Context**: The `01_ingest` pipeline requires metadata validation and graph extraction. Relying entirely on LLMs for this is token-heavy.
**Decision**: We will plan to create lightweight CLI/bash scripts ("Minions") in a future session to handle deterministic routing.
**Rationale**: Saves tokens and increases reliability for repetitive, rule-based operations.

## ADR-004: Project Lifecycle Automation
**Status**: Accepted; tracked-index portion superseded by ADR-015
**Date**: 2026-05-22
**Context**: The `30_projects` area needs low-friction status recall without requiring agents to copy the same status into multiple files by hand.
**Decision**: Project folders will use `README.md` frontmatter as the single machine-readable status source. The project README extends the standard metadata schema with `project_state`, `goal`, `next_action`, and `updated`. The `bin/sync-project-index` script generates `30_projects/index.md` from those fields. ADR-015 changes the generated index from tracked public state to ignored local state.
**Rationale**: Keeps navigation accurate while preserving one editable project status surface. The generated index prevents manual drift.

## ADR-005: Mainframe MindGraph Operating Boundary
**Status**: Accepted
**Date**: 2026-05-22
**Context**: The MindGraph MCP wrapper is now complete in the portfolio asset, but Mainframe still needs a local integration policy.
**Decision**: Mainframe will use MindGraph as an external complementary retrieval layer through `bin/mindgraph`, `bin/mindgraph-refresh`, and the optional `.mcp.json.example`. The default database is `~/.mindgraph/mainframe.sqlite`. The default ingest scope is `10_knowledge/`, not the vault root.
**Rationale**: `10_knowledge/` keeps search focused on durable notes and avoids adding operating contracts, workflow files, and empty index stubs to retrieval results. The database stays outside the repo so Git history stays clean.

## ADR-006: Workflow Telemetry Split
**Status**: Accepted; project-index hook portion superseded by ADR-015
**Date**: 2026-05-22
**Context**: We want to improve workflow efficiency over time, including tool-call patterns, without confusing Git hooks with AI-client hooks or leaking sensitive content into logs.
**Decision**: Git hooks enforce deterministic repository hygiene through staged diff checks before commit and nonblocking MindGraph refresh after commit. Tool-call telemetry lives in agent-client hook configuration (`.claude/settings.json` and `.codex/hooks.json`), which calls `bin/workflow-event` for session and tool lifecycle events. Telemetry is metadata-only, append-only, local, and ignored under `20_live/workflow-metrics/`.
**Rationale**: Git hooks can see repository transitions but not AI tool-call intent or duration. Agent-client hooks can see tool lifecycle metadata, including post-tool timing, so they are the right layer for workflow measurement. Keeping logs redacted and ignored respects the volatility constraints of `20_live`.
**Amendment 2026-06-04**: ADR-015 removes project-index freshness from the Git pre-commit hook because the generated project index is private local state.
**Amendment 2026-06-11**: Added Antigravity configuration files (`.antigravity/settings.json` and `.antigravity/hooks.json`) with hook telemetry targeting `--client antigravity` to match the Claude and Codex configuration layouts.
**Amendment 2026-06-13**: Added the Aider history watcher as a metadata-only `client: local` source. An explicit `--client` tag is authoritative over parent-process inference. The watcher records only allowlisted run diagnostics, observed edit counts, and command hashes/heads; it does not store model output, command output, file contents, or raw commands. Existing histories are skipped at watcher startup, newly created histories are read from their beginning, and reviewed histories may be replayed into an isolated telemetry directory for evaluation.


## ADR-007: Deterministic Ingest Minion V1
**Status**: Accepted
**Date**: 2026-05-23
**Context**: Files captured in `00_inbox/` need deterministic staging, metadata validation, routing, and raw-evidence stub generation without spending LLM tokens on repeatable work.
**Decision**: Mainframe will use `bin/ingest-minion` as a manual, dry-run-first CLI for the v1 ingest path. The script stages files through `01_ingest/queue/`, validates Markdown against the approved metadata schema, routes `note` and `raw` Markdown into existing `10_knowledge/<domain>/` directories, and converts convention-named PDFs into immutable raw files plus MindGraph-compatible Markdown stubs.
**Rationale**: A manual CLI keeps ingest behavior inspectable and low-risk while preserving provenance. Existing knowledge-domain directories act as the whitelist, and MindGraph refresh remains a separate workflow.

## ADR-008: Session Lifecycle Scripts
**Status**: Accepted
**Date**: 2026-05-27
**Context**: The session-open, session-close, and extract-knowledge workflows are manual checklists in `.context/workflows/`. Their deterministic steps (file existence checks, downstream script invocation, context ordering, scaffold generation) can be scripted without removing judgment from the agent.
**Decision**: Add `bin/session-open`, `bin/session-close`, and `bin/extract-knowledge` as self-contained Python scripts following the existing conventions (check/apply modes, structured result objects, no shared library). The scripts automate only deterministic operations. Narrative judgment (STATE.md writing, DECISIONS.md review, knowledge content) remains explicitly manual.
**Rationale**: Consistent with ADR-007's approach of scripting deterministic work while keeping judgment manual. Session boundaries are the highest-frequency workflows and the most prone to step omission.

## ADR-009: Two-Pass Ingest with Agent-Driven Middle
**Status**: Accepted
**Date**: 2026-05-27
**Context**: The v1 ingest minion (ADR-007) is a strict file sorter — files in `00_inbox/` without complete YAML frontmatter are rejected to `01_ingest/rejected/`. This defeats `00_inbox/` as a fast capture zone. The original second-brain planning (`second-brain-redesign/raw-processing.md`, local notes) defined a `new → skimmed → routed → extracted → synthesized` lifecycle with judgment-driven enrichment between deterministic passes; only the deterministic pass exists today.
**Decision**: Extend the ingest pipeline to a two-pass architecture:
1. **Minion pass 1 (deterministic):** Normalize frontmatter (instead of rejecting), extract `[[wikilinks]]` from body into a `links:` array, stage to `01_ingest/ready/` with `status: skimmed`.
2. **Ingest-agent (subagent, judgment):** Reads files in `ready/`, classifies (domain/type/tags), proposes connections (using `links:` + MindGraph when operational), discusses with user, enriches, renames to convention, sets `status: extracted`.
3. **`bin/prep-ingest` (deterministic):** Validates extracted files and moves to `01_ingest/queue/`.
4. **Minion pass 2 (deterministic):** Existing strict routing from `queue/ → 10_knowledge/<domain>/`. Unchanged from ADR-007.

Extends the status enum in `.context/primitives.md` with: `skimmed`, `routed`, `extracted`, `synthesized`, `parked`.
**Rationale**: Applies the "Minions vs Sub-agents" routing rule from `second-brain-redesign/gbrain-adaptations.md` (local notes) — deterministic work in scripts, judgment work in sub-agents. Preserves the v1 quality gate at `queue/ → 10_knowledge/` (the strict ADR-007 routing is unchanged) while loosening the entry point so `00_inbox/` can be a real capture zone. Deterministic link extraction (also from gbrain-adaptations §2) means connection-finding doesn't depend on MindGraph being operational.

## ADR-010: Cross-Tool Agent Layout (`.agents/` and `agents/`)
**Status**: Accepted
**Date**: 2026-05-27
**Context**: The empty `live-asset/Mainframe/skills/` folder doesn't follow a clear convention. Mainframe is used across multiple agent tools (Claude, Codex, occasionally Google), so a Claude-Code-native layout (`.claude/agents/`, `.claude/skills/`) would not be portable. We need a layout that's recognized across agent tooling.
**Decision**: Adopt the cross-tool convention:
- **`.agents/skills/`** — reusable skill definitions (dotfile because skills are agent configuration, not user-facing content).
- **`agents/`** — top-level named subagent definitions (visible at root because subagents are first-class collaborators).

Claude-Code-specific settings continue to live in `.claude/`. The empty `skills/` folder is deleted and replaced by `.agents/skills/`. Root `AGENTS.md` is updated to reference the new layout.
**Rationale**: `.agents/` and `agents/` are recognized across Claude, Codex, and other agent runtimes. Keeping multi-tool config under `.agents/` and Claude-specific config under `.claude/` cleanly separates portable agent contracts from tool-specific settings. The `agents/` folder being visible signals that subagents are part of the system's public contract, not internal config.

## ADR-011: Suggestion-First Ingest Intake and Agent-Led Domain Promotion
**Status**: Accepted
**Date**: 2026-05-29
**Context**: The first real inbox run showed that pass-1 rejects are too harsh for a capture zone. Recoverable Markdown frontmatter issues and raw PDFs without convention names should guide the agent instead of moving evidence to `01_ingest/rejected/`. The same run also exposed a fresh-vault problem: with no `10_knowledge/<domain>/` folders, strict routing cannot complete, but automatic domain creation would guess at the knowledge architecture.
**Decision**: Pass 1 of `bin/ingest-minion` is suggestion-first. Recoverable Markdown problems stage to `01_ingest/ready/` with warnings, while unsupported files and PDFs needing domain or filename decisions stay in `00_inbox/` with concrete suggestions. Strict rejects remain reserved for pass 2 from `01_ingest/queue/`. Domain and subdomain creation belongs to the ingest-agent: it may propose a new domain when a topic is distinct and likely to recur, but it must justify the proposal against `10_knowledge/index.md` and wait for user confirmation before creating folders or setting `status: extracted`.
**Rationale**: The minion should stay deterministic and nonjudgmental, while the agent handles taxonomy judgment. This keeps fast capture low-friction, preserves raw evidence, avoids weak domain guesses, and still protects durable knowledge with the strict queue gate.

## ADR-012: Optional Source Metadata on Raw Evidence Wrappers
**Status**: Accepted
**Date**: 2026-05-29
**Context**: Web clippings and binary documents often carry useful provenance fields beyond the required Mainframe routing schema. For PDFs, common document metadata can provide titles, authors, subjects, keywords, and creation/modification dates, but those fields may be absent, stale, or tool-generated.
**Decision**: Keep the required metadata schema small, but allow optional source metadata fields such as `author`, `published`, `created`, `modified`, `retrieved_at`, `source_type`, `description`, and `keywords`. The ingest minion may extract common PDF Info dictionary fields with stdlib-only best-effort parsing and add them to suggestions or generated raw stubs. These fields are advisory and must not replace the raw evidence file or be treated as verified publication facts without review.
**Rationale**: Optional metadata improves search and triage without making the ingest gate brittle. Keeping extraction best-effort and stdlib-only preserves the deterministic, dependency-light minion boundary while maintaining provenance discipline.

## ADR-013: AI Business and Knowledge Systems Domains
**Status**: Accepted
**Date**: 2026-05-31
**Context**: The ready ingest queue contains recurring captures that do not fit cleanly into the existing `agents`, `ai-detection`, `finance`, or `humour` domains. Several notes concern AI product/business strategy rather than agent implementation, while another cluster concerns vault design, retrieval, and personal knowledge systems.
**Decision**: Add two top-level knowledge domains: `ai-business` for AI product strategy, app-layer defensibility, monetization, consulting, and AI-native business models; and `knowledge-systems` for personal knowledge management, Obsidian/vault design, retrieval-first organization, and AI-assisted knowledge workflows.
**Rationale**: Keeping these as separate domains avoids overloading `agents` with business and PKM material, improves retrieval, and follows ADR-011 by making domain promotion agent-led and user-confirmed before deterministic routing.

## ADR-014: Bundled Writing Style Skill
**Status**: Accepted
**Date**: 2026-05-31
**Context**: Writing guidance was split across portfolio, content-engine, career, and natural-voice contexts. The recurring need is to apply shared prose principles while still respecting genre-specific constraints without loading every reference into the skill body.
**Decision**: Add `.agents/skills/writing-style/` as a bundled skill with a compact router in `SKILL.md` and separate reference pages for shared natural voice, portfolio writing, content-engine writing, career writing, technical/professional writing, and humour/rhythm. The skill explicitly optimizes for authentic voice, specificity, calibrated judgment, and readable prose rather than AI-detector evasion.
**Rationale**: Keeping `SKILL.md` small follows the centralized skill pattern from ADR-010 while allowing task-specific references to be loaded only when needed. A positive craft-first rule prevents the guidance from collapsing into brittle anti-pattern chasing.

## ADR-015: Private Project Workbenches and Public Index Template
**Status**: Accepted
**Date**: 2026-06-04
**Context**: MainFrame is easier to use when the active project workbench can live inside the project layer itself. At the same time, the generated project index can expose private project names and next actions if tracked in the public repository.
**Decision**: Project folders under `30_projects/<slug>/` may contain the full local workbench for that outcome, including nested Git repositories, source trees, drafts, artifacts, and project-local plans. The outer MainFrame repo continues to ignore `30_projects/*`. The generated `30_projects/index.md` is local/private and ignored by Git. The public repo tracks `30_projects/index.template.md` to document the index shape without exposing the live project inventory. If project-layer MindGraph indexing is added, it should use a separate project-scoped database or scope from the default durable-knowledge index and surface project-context trust labels.
**Rationale**: This keeps MainFrame useful as the organizing root for real work while preserving the public/private boundary. Durable, reusable knowledge still moves into `10_knowledge/` only through an explicit extraction step, so active project context does not collapse into verified knowledge.

## ADR-021: Focus Query Sourcing, Subset Corpus Auditing, launchd Daemonisation, sqlite3 Online Backups, and Evaluation Benchmarking
**Status**: Accepted
**Date**: 2026-06-11
**Context**: In Phase 6 of the Epistemic Research System development, we need to allow directed web research via focus queries, target specific directories for corpus auditing, schedule a background watcher daemon robustly on macOS, secure SQLite database data with nightly backups in WAL mode, and measure system accuracy on claim extraction and audit verdicts.
**Decision**:
1. **Focus Sourcing**: Added `--focus` option to the CLI `run` and `research-topic` subcommands to interpolate focus instructions into the prompt template.
2. **Corpus Subsets**: Added `--subset` option to `audit-corpus` to limit indexing to a specific subdirectory of `10_knowledge/`.
3. **launchd Daemonisation**: Added `daemon` subcommand to orchestrator CLI with `install`, `uninstall`, `start`, and `stop` actions, managing a plist dynamically referenced to the active virtual environment's Python executable and script paths.
4. **Online Backups**: Implemented a daily backup hook using `sqlite3.Connection.backup()` inside the watcher loop, writing WAL-checkpointed database copies under `90_archive/epistemic/backups/`.
5. **Evaluation Framework**: Created `harness/evaluator.py` to calculate claim extraction Precision/Recall/F1 and support verdict accuracy against manual ground truth lists, with automated fallback logic for offline/stub mode.
**Rationale**: These features ensure high-fidelity directed research, resource-conscious local corpus indexing, zero-configuration background operation, robust transactional database backups, and measurable system iteration quality.
**Consequences**: The database backups will run automatically on the first watch loop run of a calendar day. When testing offline, the evaluator will automatically mock the LLM output with corresponding ground truth claims for end-to-end integration validation.

## ADR-022: Shared-component reuse via pinned git submodules with automated bump PRs
**Status**: Accepted
**Date**: 2026-06-13
**Context**: Several projects reuse the same building blocks — `evidence-bundler`, `claim-audit-lab`, `apparatus-contracts`, `research-scaffold-harness`. Each is an independent project under `30_projects/<name>/workbench/` whose working copy is the clone of a per-component GitHub repo (`github.com/camerontjs-dot/<name>`). `<private-claims>` already consumes them as git submodules under `workbench/components/`. As more projects reuse them (the Biotech RAG Assistant intends to vendor `evidence-bundler` and `claim-audit-lab`), we need one rule for keeping every copy current.
**Decision**:
1. **Canonical = the projects-root working copy of each component, which is the clone of its own GitHub repo.** Fixes happen there and are pushed to that component's GitHub repo; one source of truth per component. Consumers never edit a vendored copy.
2. **Consumers vendor via git submodules** under `workbench/components/<name>`, mirroring `<private-claims>`. No copy-paste, no path symlinks, no package publishing.
3. **Pin submodules to release tags** (e.g. `claim-audit-lab v0.2.0`), not a moving `main`, so a consumer takes shared-code changes as deliberate, reviewable bumps. (Today `<private-claims>` pins CAL/apparatus to tags but EB to `main`; tags are the target state.)
4. **Automate "keep current" with Dependabot** in each consumer repo (`package-ecosystem: "gitsubmodule"`): it opens a PR when a tracked submodule's upstream advances; a human reviews and merges. A scheduled GitHub Action running `git submodule update --remote` + opening a PR is an acceptable equivalent. Manual fallback: `git submodule update --remote <path>` then commit the gitlink bump.
5. **Prerequisite**: a consumer must be a GitHub repo for the automation to run; components moving from `main`-tracking to tags need release tags cut on their GitHub repos.
**Rationale**: Submodules keep one source of truth with explicit, pinned, reviewable version references — the same evidence discipline the components themselves embody. Tag pinning plus Dependabot gives controlled propagation (fix once in canonical → push → auto-PR into every consumer) without a consumer silently drifting onto an unreviewed shared-code change.
**Rejected alternatives**: copy-paste vendoring (drifts, no provenance); path symlinks (not portable, break on clone/CI); publishing each component to a package index (heavier release process than warranted while the components are pre-1.0 and co-evolving); a single monorepo (loses the independent per-component repos and their histories/tags); tracking `main` everywhere (consumers take unreviewed changes the moment upstream moves).
**Consequences**: `<private-claims>` should gain a Dependabot config and move EB from `main` to a tag. The Biotech RAG Assistant adds `evidence-bundler` and `claim-audit-lab` submodules under `workbench/components/` once it is on GitHub and those components are stable/tagged (its own ADR-015 records the application and its by-reference predecessor, ADR-001/006). Component repos should cut release tags so consumers can pin. This ADR governs how shared code propagates; it does not itself wire any new submodule.

## ADR-023 (follow-up): Audit Sweep Tooling and Skill Promotion for Ingest (Stabilization of ADR-019)
**Status**: Accepted
**Date**: 2026-06-13
**Context**: After landing the tiered ingest + review-after model (ADR-019) and discovering real `needs-audit` tags already present on hundreds of routed raws (but no routine surfacing or processing), plus the epistemic research system still completing "final audit integration", the compensating control for batch/Tier A routing was not yet operational. At the same time the detailed per-file judgment procedure remained embedded in a long subagent definition instead of being promoted to reusable skills per the process-evaluation promotion test and ADR-010.
**Decision**:
1. Created `.context/workflows/audit-sweep.md` and `bin/audit-sweep` (dry-run/apply/JSON/--subset support) for deterministic discovery of `needs-audit` + recent routed items, manifest generation into `20_live/epistemic-audit/pending-review/`, and handoff to the auditor.
2. Extended `30_projects/<private-harness>/workbench/mainframe_bridge/` with `sweep_knowledge_for_audit_tags()` to allow the harness to drive or be driven by the sweep.
3. Integrated the sweep into `session-close`, `session-guide`, README, and reinforced tagging obligations in the ingest-agent.
4. Promoted the core per-file enrichment loop into a first-class implemented skill at `.agents/skills/ingest-source.md` (with sub-skill `classify-note` also expanded). The `agents/ingest-agent.md` per-file procedure was thinned to delegation + guardrails/mode selection only. Batch mode remains in the agent definition for now.
5. Verified the scanner immediately surfaces real backlog (226+ explicit needs-audit items).
**Rationale**: Makes the post-placement audit safety net (the key assumption of ADR-019) actually usable and routine today. Moves repeated judgment out of the subagent contract into the skill layer exactly as the system's own promotion rules prescribe. Keeps the new tool lightweight and deterministic while delegating LLM claim work to the existing epistemic harness.
**Consequences**:
- Before any further widening of Tier A or heavy batch usage, run `bin/audit-sweep` (and drive auditor passes on the manifests) on the existing backlog, especially high-volume domains. Treat early sweeps as calibration data.
- Future ingest-agent definitions and workflows should reference the skills rather than re-describing the steps.
- Add coverage metrics and sweep calls to workflow-report / process evaluations.
- The epistemic orchestrator can grow a dedicated `sweep --mainframe` / audit-focused mode that consumes the manifests or directly queries tags.
- Record ongoing audit adoption and any rule refinements in `<private-eval-b>/` outputs and future DECISIONS entries. No change to the core routing-policy or primitives schema.

## ADR-024: Reviewed Task Packets and Isolated Local-Agent Evaluation
**Status**: Accepted
**Date**: 2026-06-14
**Context**: Local Coder telemetry can reveal execution and capture failures, but it does not establish which task categories are safe to delegate or whether a harness change improves outcomes. Project plans also need a stable implementation boundary that can be handed to a local agent without delegating unresolved design choices.
**Decision**:
1. Prepared local-agent work is expressed as a reviewed Markdown task packet under `30_projects/<slug>/plans/task-packets/`. Only packets marked `ready` may execute; run state belongs in receipts rather than mutating the packet.
2. `bin/task-packet` validates paths, scope separation, required sections, workdirs, and argv-safe verification commands, then compiles packet summaries into ignored local state for the task board.
3. Local-agent evaluation runs in disposable Git copies with hidden external verification, exact scope scoring, no agent commits, private raw artifacts, and versioned receipts.
4. Harness changes are evaluated one at a time against a fixed baseline. Capability graduation is specific to task category, model profile, and harness version.
5. The Local Agent workstation may read only a sanitized aggregate capability file. It must not expose prompts, transcripts, receipt paths, diffs, or private verifier output.
6. MindGraph retrieval is curated outside the executing agent and remains a context nomination, never verification.
**Rationale**: This separates planning authority, execution, verification, and promotion. It makes delegation reusable across projects while preventing synthetic success, model self-report, or a polished workstation display from becoming unsupported evidence of capability.
**Consequences**: Projects gain a stricter preparation step before local delegation. The private `<private-harness-eval>` project owns experimental adapters, fixtures, receipts, and harness variants; only proven reusable validators and workflows are promoted into MainFrame.
