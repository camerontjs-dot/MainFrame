---
name: mindgraph-retrieval
description: Use when an agent needs to retrieve durable knowledge or active project context from MainFrame's local graph-augmented search engine (MindGraph). It provides instructions on CLI/MCP commands and prevents hallucination of non-existent search verbs. Triggers on: "query mindgraph", "search mindgraph", "mindgraph query", "retrieve knowledge", "find in knowledge base", "query knowledge", "query projects", "mindgraph-refresh", "mindgraph doctor", "mindgraph status".
status: active
---

# mindgraph-retrieval

## Purpose

This skill guides agents on using **MindGraph**—MainFrame's local, graph-augmented retrieval engine. It defines the strict CLI/MCP command vocabulary and query station conventions to ensure efficient, hallucination-free retrieval.

---

## Strict Command Vocabulary

Agents **MUST NOT** invent or guess CLI verbs (e.g. do not call `mindgraph search`, `mindgraph scan`, or `mindgraph check-status`). Only use the following officially supported commands:

### 0. First-contact diagnostics (run before planning queries)
- **CLI Command:** `bin/mindgraph doctor` (alias: `bin/mindgraph status`)
- **Options:** `--json`, `--db <path>` (single DB), `--workspace <dir>` (stub scan root)
- **Purpose:** Report dual-index paths under `~/.mindgraph/`, sizes, required tables (`documents_fts`, `vec_chunks`, …), counts, and workspace-root stub traps — **without loading the embedder**. Exit non-zero only if a checked index is unusable.
- **On failure:** do not invent alternate DB paths; refresh with `bin/mindgraph-refresh` / `bin/mindgraph-refresh-projects` after operator OK.

### 1. Database Initialization
- **CLI Command:** `bin/mindgraph init --db <path>`
- **Purpose:** Initializes a new SQLite database with schemas for documents, chunks, vector embeddings, and edges.

### 2. Document Ingestion & Indexing
- **CLI Command:** `bin/mindgraph ingest <directory_path> --db <path>`
  - *Ingest multiple roots:* `bin/mindgraph ingest-many --roots-manifest <path> --db <path>`
- **Purpose:** Ingests a directory of Markdown notes. It extracts `[[links]]`, chunks text, generates embeddings locally using `all-MiniLM-L6-v2`, and writes them to the DB.

### 3. Fused Query Execution
- **CLI Command:** `bin/mindgraph query "your query string" --db <path> [options]`
- **MCP Tool (shared daemon via proxy):** `query(question, scope, final_top_k?)`
  - **`scope` (required):** `knowledge` or `projects` — never omit, never invent `both`.
  - Response wraps `{scope, trust_profile, results}`. Do not blend scopes without trust labels.
- **CLI options (full path):**
  - **`--json`**: Structured machine-readable JSON. Prefer in automated processing.
  - **`--top-k <int>`**: Fused result count (default: 10).
  - **`--expand --depth [1-3] --expand-top-k <int>`**: Outbound BFS graph expansion.
  - **`--associate --associate-top-k <int>`**: Semantic neighbors from seed vector matches.
  - **`--envelope`**: Opt-in `{schema_version, intent_resolution, routing, results}` (CLI / single-DB MCP).
- **Fail-fast:** Query refuses incomplete/stub DBs missing required tables (use `doctor` to diagnose). Never query workspace-root `mainframe*.sqlite` stubs.

### 4. Direct Neighbor Lookup
- **CLI Command:** `bin/mindgraph neighbors <doc_id> --db <path> --json`
- **MCP Tool (shared daemon):** `graph_neighbors(doc_id, scope)` with `scope` = `knowledge` | `projects`
- **Purpose:** Retrieves direct outbound links for a document node (dangling targets may be `null`).

### 5. Shared MCP daemon + proxy (operational default)
- **Start daemon once:** `bin/mindgraph daemon-start` (or `serve-daemon` foreground)
- **Health:** `bin/mindgraph daemon-status` · `bin/mindgraph daemon-health`
- **Stop:** `bin/mindgraph daemon-stop`
- **Client config (`.mcp.json`):** `bin/mindgraph mcp-proxy --url http://127.0.0.1:8000/mcp`
- **Contract:** loopback only; one embedder process; read-only knowledge + projects;
  every MCP call selects `knowledge` or `projects`; no blend and no refresh hot
  reload. Proxy auto-start is disabled unless the operator explicitly activates
  the idle lifecycle marker; activated proxies serialize startup and hold a
  renewable lease. Direct HTTP clients still require manual start/reconnect.
  Proxy processes are thin stdio shims — do not run per-client `serve-mcp` in
  parallel.

### 6. Legacy single-DB MCP (debug only)
- **CLI Command:** `bin/mindgraph serve-mcp --db <path>`
- **Purpose:** One-process stdio server for a single index (loads its own embedder).
  Not the daily client path — prefer daemon + proxy (section 5).

---

## Query Station Conventions

When executing project-planning phases, always query both databases and respect their trust profiles:

1.  **Durable Knowledge DB:** `~/.mindgraph/mainframe.sqlite` (trust: `durable_knowledge`). Stores synthesized notes under `10_knowledge/`.
2.  **Project Context DB:** `~/.mindgraph/mainframe-projects.sqlite` (trust: `project_status`). Stores active logs, plans, and READMEs under `30_projects/`.

### Station Query Modes
-   **`knowledge`**: Queries the durable knowledge index only.
-   **`projects`**: Queries the project context index only.
-   **`federated`**: Queries both indexes, grouping results by trust profile. **Do not merge result groups without explicit trust labels.**

### Example Query Flows

#### Standard Query
```bash
# Query the Knowledge DB
bin/mindgraph query "GxP AI validation frameworks" --db ~/.mindgraph/mainframe.sqlite --json

# Query the Projects DB
bin/mindgraph query "model-validation-lab status" --db ~/.mindgraph/mainframe-projects.sqlite --json
```

#### Graph-Expanded Query
```bash
bin/mindgraph query "RAG evaluation benchmarks" --db ~/.mindgraph/mainframe.sqlite --expand --depth 1 --json
```

---

## Retrieval Guardrails

1.  **Nomination, Not Proof:** MindGraph retrieves candidates for inspection. It does not verify claims. The presence of text in retrieved chunks does not make it true.
2.  **No Direct Modification:** Never write raw text or notes directly to `10_knowledge/` without running them through the ingest pipeline (`bin/ingest-minion`).
3.  **Preserve Attribution:** When quoting retrieved context, preserve the metadata (`display_path`, `trust_profile`, `rrf_score`).

## Link-audit judgment

When a task concerns graph hygiene, use `bin/mindgraph-audit-links` for a
source-authoritative, read-only advisory report and read the source notes
before proposing any relationship. A MindGraph result or audit candidate is a
nomination, not proof. Resolve only through the parser's exact canonical-path,
full-stem, or unique trailing-slug behavior; abstain on ambiguity, lifecycle
bridges, and identity conflicts. Raw zero-outbound documents are informational
evidence-leaf findings, not health failures. Curated zero-outbound notes need a
directly supported relationship or an explicit reviewed-no-link/standalone
disposition. Never use the audit to rewrite, delete, fuzzy-select, or mutate
SQLite; follow `.context/workflows/graph-link-audit.md` for refresh and probe
receipts.
