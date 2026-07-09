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

Use this block in plans, handoffs, and task packets until the Query Station can emit it directly:

```markdown
## MindGraph Query Pass
intent:
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
1. Confirm you are using the official CLI: `bin/mindgraph query "..." --json`
2. For durable knowledge: default `~/.mindgraph/mainframe.sqlite` (or explicit `--db $HOME/.mindgraph/mainframe.sqlite`)
3. For active projects: `~/.mindgraph/mainframe-projects.sqlite`
4. Always run **both** and keep the two result groups separate with trust labels (`durable_knowledge` vs `project_status`).
5. Emit a "MindGraph Query Pass" block (template above) before diving into source files.
6. Use `--json` for agent processing.

### Known friction points (from 2026-06-23 session)
- Workspace root `mainframe*.sqlite` files are usually 4 KB stubs with no tables. The real indexes live in `~/.mindgraph/`.
- `bin/mindgraph query` reloads the embedding model on every call ("Loading embedding model (all-MiniLM-L6-v2)..."). Plan for latency on discovery passes.
- `python` may not be in PATH (use `python3`).
- Project-internal docs often live one level deeper (e.g. `workbench/docs/ENGINE_NOTES.md`).
- Early broad queries return weak or tangential hits. Use exact project slugs, phase names, and file stems once you have them from the lane tracker or prior notes.

### Recommended mitigations (process + future tooling)
- Always start research or project planning with an explicit dual query + Query Pass record.
- Record new friction in `10_knowledge/agents/` + the `mindgraph-agent-harness-discovery` research lane.
- Future: `bin/mindgraph status` or `doctor` that reports DB locations, sizes, table presence, and last refresh.
- Future: louder early failure or warnings when a DB lacks expected tables.
- Keep this section and the companion note (`10_knowledge/agents/2026-06-23__agents__note__first-time-local-agent-harness-mindgraph-discovery.md`) up to date.

See also the dedicated research lane `30_projects/research-lanes-strategy/lanes/mindgraph-agent-harness-discovery/README.md`. MindGraph is the retrieval engine of the system; making first contact reliable is high-leverage.
