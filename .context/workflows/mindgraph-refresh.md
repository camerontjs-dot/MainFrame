# MindGraph Refresh Workflow

MindGraph is a complementary retrieval layer for Mainframe, not the source of truth.

## Defaults
- Database: `~/.mindgraph/mainframe.sqlite`
- Ingest scope: `10_knowledge/`
- Wrapper: `bin/mindgraph`
- Refresh command: `bin/mindgraph-refresh`
- MCP example config: `.mcp.json.example`
- Binary resolution: install `mindgraph` on `PATH`, set `MINDGRAPH_BIN=/path/to/mindgraph`, or set local repo config `git config mainframe.mindgraphBin /path/to/mindgraph`

## Steps
1. Add or update durable Markdown notes in `10_knowledge/`.
2. Run `bin/mindgraph-refresh`.
3. Query with `bin/mindgraph query "<question>"` or connect an MCP-aware client using `.mcp.json.example`.

## Guardrails
- Do not ingest the full vault by default; operating contracts and empty indexes add retrieval noise.
- MindGraph nominations are not verification. Treat returned chunks as candidates to inspect.
- Keep the SQLite database outside the repo so Git history stays clean.
