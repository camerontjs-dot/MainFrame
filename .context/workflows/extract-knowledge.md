# Extract Knowledge Workflow

Use this workflow at project closeout or after a repeated pattern becomes clear.

## Script
- Command: `bin/extract-knowledge`
- Check mode: `bin/extract-knowledge --project <slug> --domain <domain> --title <title> --check`
- Write mode: `bin/extract-knowledge --project <slug> --domain <domain> --title <title> --write`
- Scaffolds a note with correct metadata; knowledge content stays manual
- Run `bin/mindgraph-refresh` after filling in the note

## Steps
1. Review the project `README.md`, `log.md`, `decisions.md`, and final outputs.
2. Identify reusable practices, failure modes, command patterns, and standards.
3. Create or update a note in `10_knowledge/` with the standard metadata schema from `.context/primitives.md`.
4. Link the note's `source` to the project path or preserved raw evidence.
5. Keep claims calibrated: separate observed facts from inferences.
6. Run `bin/mindgraph-refresh` after durable knowledge notes change.

## Guardrails
- Extract only reusable knowledge. Do not turn every project detail into a durable note.
- Preserve source material; extracted text is a working copy, not the source of truth.
- If the note touches finance, legal, health, or other high-risk live data, verify against source documents before promotion.
