# Workflow Telemetry Workflow

This workflow records local process metrics so future sessions can improve the way work is done. It does not record prompts, file contents, command output, or tool responses.

## Data Path
- Claude Code hooks live in `.claude/settings.json`.
- Codex hooks live in `.codex/hooks.json`.
- Antigravity hooks live in `.antigravity/settings.json` and `.antigravity/hooks.json`.
- Hook events call `bin/workflow-event`.
- Redacted JSONL is appended under ignored `20_live/workflow-metrics/events/`.
- Summaries are produced with `bin/workflow-report`.

## Captured Fields
- Hook event name
- Tool name
- Duration when the client provides it
- Success or failure for post-tool events
- Permission mode and effort level when present
- Redacted path zone, file extension, command head, and hashed identifiers
- Optional allowlisted `process_id` / `process_ids` values for catalogue attribution

## Guardrails
- Telemetry is append-only local state.
- Never log raw prompts, raw command text, file contents, tool output, or model responses.
- Process IDs must be stable catalogue-style identifiers with an approved prefix (`cli-`, `script-`, `ingest-`, `workflow-`, `skill-`, or `agent-`), not raw commands, paths, prompts, project names, people names, or free-text task descriptions.
- `bin/workflow-report` keeps redacted defaults; use `--by-process` when a process rollup is needed.
- Use `bin/workflow-report --input-signals` only for aggregate redacted input rollups such as safe command heads, lifecycle path zones, and file extensions; it must not expose command hashes, prompt hashes, full paths, or raw command text.
- Use reports to spot workflow friction, not to treat speed as the only measure of quality.
