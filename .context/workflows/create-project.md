# Create Project Workflow

Use this workflow when starting a new outcome-bearing project in `30_projects/`.

## Steps
1. Create `30_projects/<slug>/`.
2. Add `README.md` with the metadata required by `30_projects/AGENTS.md`.
3. Add `log.md`, `decisions.md`, and the folders `plans/`, `raw-materials/`, and `outputs/`.
4. Set `project_state: "active"`, `updated: "YYYY-MM-DD"`, and a concrete `next_action`.
5. Run `bin/sync-project-index --write`.
6. If the project introduces an architecture or workflow choice, record it in `DECISIONS.md`.

## Guardrails
- Keep raw source material in `raw-materials/` or the lifecycle folder where it originated.
- Do not promote model-generated summaries as facts unless the source evidence is preserved.
- If the project belongs in `20_live`, follow `20_live/AGENTS.md` instead.
