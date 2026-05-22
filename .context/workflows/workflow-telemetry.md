# Workflow Telemetry Workflow

This workflow records local process metrics so future sessions can improve the way work is done. It does not record prompts, file contents, command output, or tool responses.

## Data Path
- Claude Code hooks live in `.claude/settings.json`.
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

## Guardrails
- Telemetry is append-only local state.
- Never log raw prompts, raw command text, file contents, tool output, or model responses.
- Use reports to spot workflow friction, not to treat speed as the only measure of quality.
