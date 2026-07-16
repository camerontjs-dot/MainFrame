# MindGraph Refresh Workflow

MindGraph is a complementary retrieval layer for Mainframe, not the source of truth.

## Defaults
- Knowledge database: `~/.mindgraph/mainframe.sqlite`
- Knowledge ingest scope: `10_knowledge/`
- Projects database: `~/.mindgraph/mainframe-projects.sqlite`
- Projects ingest scope: optional ignored local manifest at `30_projects/mindgraph-projects.json`; if absent, `bin/mindgraph-refresh-projects` uses its built-in curated list. `--full` discovers all project coordination surfaces and `MAINFRAME_MINDGRAPH_PROJECTS="slug-a slug-b"` overrides the manifest for a focused pass
- Wrapper: `bin/mindgraph`
- Refresh commands: `bin/mindgraph-refresh` (knowledge), `bin/mindgraph-refresh-projects` (projects)
- Query station: workstation interpreter over both DBs for `knowledge`, `projects`, and grouped `federated`; use explicit CLI queries for any station mode that has not shipped yet
- Operating contract: `HARNESS.md` (dual-index routing)
- MCP example config: `.mcp.json.example`
- Binary resolution: install `mindgraph` on `PATH`, set `MINDGRAPH_BIN=/path/to/mindgraph`, or set local repo config `git config mainframe.mindgraphBin /path/to/mindgraph`

## Steps
1. Add or update durable Markdown notes in `10_knowledge/`.
2. Run `bin/mindgraph-refresh`.
3. Add or update project-layer notes (README, `outputs/`, `plans/`, `decisions.md`) in `30_projects/`.
4. Run `bin/mindgraph-refresh-projects`; it generates one temporary manifest and calls `mindgraph ingest-many` so repeated filenames across projects do not collide.
5. Query with the workstation Query Station when available, or with `bin/mindgraph query "<question>"` for the knowledge DB and `MINDGRAPH_DB_PATH="$HOME/.mindgraph/mainframe-projects.sqlite" bin/mindgraph query "<question>"` for the projects DB. Preserve both result groups with trust labels. Connect an MCP-aware client using `.mcp.json.example` (defaults to knowledge DB unless configured otherwise).

## Query Pass Template

**Canonical copy-paste:** [`.context/templates/mindgraph-query-pass.md`](../templates/mindgraph-query-pass.md)
Also embedded in [`.context/templates/task-packet.md`](../templates/task-packet.md) as an optional section.

Minimal YAML-style block for plans and handoffs:

```markdown
## MindGraph Query Pass
intent:
doctor:   # overall line from `bin/mindgraph doctor`
knowledge_query:
projects_query:
knowledge_nominations:
- title: ...
  path: ...
  reason: ...
project_nominations:
- title: ...
  path: ...
  reason: ...
weak_or_excluded:
- ...
source_inspection_required:
- ...
```

## Guardrails
- Do not ingest the full vault by default; operating contracts and empty indexes add retrieval noise.
- Do not merge `mainframe.sqlite` and `mainframe-projects.sqlite` into one blended ranking. The station/interpreter may group, annotate, and bridge nominations, but the DBs stay physically and epistemically separate.
- Project DB refresh uses multi-root namespaced ingest; still inspect source files before treating station output as complete project context.
- MindGraph nominations are not verification. Treat returned chunks as candidates to inspect.
- Keep the SQLite database outside the repo so Git history stays clean.

## First-Time Agent / Troubleshooting (added 2026-06-23)

When an agent or operator is starting fresh or after a long gap, the mandatory dual MindGraph planning hook can become an environment archaeology exercise. The following checklist and known issues reduce that friction.

### Quick first-run checklist
1. `bin/mindgraph doctor` — confirm dual `~/.mindgraph` indexes (not workspace stubs)
2. Official CLI: `bin/mindgraph query "..." --json --db ~/.mindgraph/mainframe.sqlite`
3. Projects: `bin/mindgraph query "..." --json --db ~/.mindgraph/mainframe-projects.sqlite`
4. Always run **both** and keep groups labeled (`durable_knowledge` vs `project_status`)
5. Emit a MindGraph Query Pass (template above / `.context/templates/mindgraph-query-pass.md`)
6. Use `--json` for agent processing

### Known friction points (from 2026-06-23 session)
- Workspace root `mainframe*.sqlite` files are usually 4 KB stubs with no tables. The real indexes live in `~/.mindgraph/`. Doctor warns; query fail-fasts if you hit a stub.
- `bin/mindgraph query` reloads the embedding model on every cold process. Plan for latency on discovery passes (or use MCP warm path when available).
- `python` may not be in PATH (use `python3`).
- Project-internal docs often live one level deeper (e.g. `workbench/docs/ENGINE_NOTES.md`).
- Early broad queries return weak or tangential hits. Use exact project slugs, phase names, and file stems once you have them from the lane tracker or prior notes.

### Recommended mitigations
- Start research or project planning with doctor + dual query + Query Pass record.
- Record new friction in `10_knowledge/agents/` + MH01 lane (`mindgraph-agent-harness-discovery`).
- **Shipped (2026-07-13):** `bin/mindgraph doctor|status`; query fail-fast on missing tables.
- Still open: warm MCP dual-index path for the 60s budget.
- Keep this section and the companion friction note up to date.

See also the dedicated research lane `30_projects/research-lanes-strategy/lanes/mindgraph-agent-harness-discovery/README.md`. MindGraph is the retrieval engine of the system; making first contact reliable is high-leverage.
