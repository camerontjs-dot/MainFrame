# Session Open Workflow

A session-open workflow should load only the minimum useful context in a fixed order. This implements progressive context disclosure and prevents the model from consuming broad ambient context that is unrelated to the immediate work.

## Script
- Command: `bin/session-open`
- Auto-detect project: reads `## Active Project` from `STATE.md`
- Override: `--project <slug>`
- Content dump: `--print-contents`
- Structured output: `--json`

## Suggested Order:
1. Load `AGENTS.md` (root control file)
2. Load `STATE.md` (workspace state file)
3. Load the selected project `README.md` (if working on a specific project; see `30_projects/AGENTS.md`)
4. Load the phase plan (if applicable)
5. Load task-local docs/code
6. Load evidence ONLY when needed.
