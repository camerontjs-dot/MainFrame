# Archive Project Workflow

Use this workflow when a project is `shipped` or `trashed`.

## Steps
1. Confirm the current project state in the project `README.md`.
2. Run the `extract-knowledge` workflow and write durable lessons to `10_knowledge/` only when they are reusable outside the project.
3. Append a final entry to the project `log.md` with the archive reason and date.
4. For `shipped`, keep the project in `30_projects/` and move scratch material into project-local `archive/`.
5. For `trashed`, move the whole project folder to `90_archive/`.
6. Run `bin/sync-project-index --write`.
7. Run `bin/mindgraph-refresh` if durable notes changed.

## Guardrails
- Do not delete raw evidence while archiving.
- Do not rewrite history to make a project look cleaner.
- Record architecture or workflow changes in `DECISIONS.md`.
