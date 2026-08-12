# Mainframe - Global Operating Contract

## System Purpose
This system organizes knowledge by its **information lifecycle** first, and topic second. The goal is accurate recall, low-friction capture, and safe updates.

## Architecture
- `00_inbox/`: Fast capture zone.
- `01_ingest/`: Normalization and routing.
- `10_knowledge/`: Durable, slower-moving knowledge.
- `20_live/`: Volatile personal and project state, active research.
- `30_projects/`: Active work with outcomes.
- `90_archive/`: Preserved material without cluttering active navigation.

## Agent Behavior
1. **Harness contract:** Read `HARNESS.md` for task-category harness rules, dual MindGraph indexes, and local/cloud delegation boundaries.
2. **MindGraph Planning Hook:** Always query the dual MindGraph databases (`mainframe.sqlite` and `mainframe-projects.sqlite`) when planning or starting work on any project in `30_projects/` to leverage existing workspace context. Use the MindGraph Query Station when available, or the CLI equivalent, and preserve the two result groups with trust labels instead of blending them into one answer.
3. **MindGraph MCP (shared daemon):** Operational clients connect through the loopback shared daemon (`http://127.0.0.1:8000/mcp`) via `bin/mindgraph mcp-proxy` or a streamable-HTTP URL — never by spawning `serve-mcp` per session. Every MCP `query` / `graph_neighbors` call **must** pass `scope` = `knowledge` or `projects`. Do not invent `both`. Prefer CLI `bin/mindgraph query --db …` when MCP is unavailable. See ADR-049 and `.agents/skills/mindgraph-retrieval/SKILL.md`.
4. **Centralized Skills:** Use `.context/workflows/` for operator-driven sequences and `.agents/skills/` for reusable agent skills rather than duplicating instructions.
5. **Subagents:** Named subagent definitions live in `agents/` (e.g. `agents/ingest-agent.md`). Subagents are first-class collaborators; their roles, tools, guardrails, and procedures are defined there.
6. **Local Constraints:** Respect local `AGENTS.md` files in subdirectories—they contain overriding rules for sensitive or volatile data.
7. **Immutability:** Do not silently overwrite history. If a file is in `20_live`, use snapshots or append-only timelines.
8. **Provenance:** Preserve raw sources as evidence. Extracted text is a searchable working copy, not the source of truth.


## Structural File Discipline
- Structural files include operating contracts, local `AGENTS.md` files, `HARNESS.md`, decision records, workflows, skills, subagent definitions, templates, configs, indexes, manifests, hooks, scripts, and project/workbench files that define process or verification behavior.
- Use `.context/templates/structural-file-profile.md` when creating or auditing structural files. Project-local files follow the same framework even when they are ignored or private.
- Put stable always-on rules in `AGENTS.md`; put long operator sequences in `.context/workflows/`; put repeated agent judgment in `.agents/skills/`; put specialized roles in `agents/`; put deterministic enforcement in `bin/`, scripts, hooks, config, or tests.
- Keep root and lifecycle contracts durable. Put volatile status in `STATE.md`, `20_live/`, project `README.md`, or project `log.md`.
- Record accepted architecture or workflow changes in `DECISIONS.md`; record project-only tradeoffs in the project's `decisions.md`.

## Searching this repo

`grep` here is a **ugrep wrapper that honours `.gitignore`**, and `10_knowledge/`,
`20_live/` and `30_projects/` are all ignored. A repo-root search returns zero
hits for content that demonstrably exists. Use `command grep`, an explicit path,
or MindGraph.

Recursive searches from the root also time out: `.venv` and `node_modules` trees
dominate the file count. Scope to the directory you mean.

## Metadata & Updating
- Every finalized note must contain the standard metadata schema defined in `.context/primitives.md`.
- Ensure changes to architecture or workflow are recorded in `DECISIONS.md`.
- Adhere to the epistemic stance defined in `EPISTEMIC_STANCE.md` when recording claims. For any claim-bearing output, follow `.context/workflows/epistemic-standard.md` (classify claims, check evidence tier, assign confidence, surface counterevidence).
