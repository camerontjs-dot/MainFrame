# Create Project Workflow

Use this workflow when starting a new outcome-bearing project in `30_projects/`.

## Steps
1. Create `30_projects/<slug>/`.
2. Add `README.md` with the metadata required by `30_projects/AGENTS.md`.
3. **MindGraph Scan:** Query MindGraph through the Query Station when available, or run the CLI equivalent against both databases. Record a grouped `MindGraph Query Pass` with query strings, durable-knowledge nominations, project-context nominations, weak/excluded hits, and source files that still require inspection.
4. **Full coordination (default):** Add `log.md`, `decisions.md`, and the folders `plans/`, `raw-materials/`, `outputs/`, and `workbench/`.
   **Light/experiment mode (Fix 3 ceremony reduction):** For small exploratory work you may start with only README + (optional) log.md. Graduate to full coordination when it becomes a tracked outcome (add the required files then). Use `bin/extract-knowledge` early to push reusable lessons to `10_knowledge/`.
5. Set `project_state: "active"`, `updated: "YYYY-MM-DD"`, and a concrete `next_action`.
6. Run `bin/sync-project-index --write` to refresh the local ignored project index.
7. If the project introduces an architecture or workflow choice, record it in `DECISIONS.md`.

## Guardrails
- Keep raw source material in `raw-materials/` or the lifecycle folder where it originated.
- Keep the project workbench inside `workbench/` when colocating the active source tree inside MainFrame.
- Do not promote model-generated summaries as facts unless the source evidence is preserved.
- If the project belongs in `20_live`, follow `20_live/AGENTS.md` instead.
