# Ingest Minion Workflow

Use this workflow when moving captured files from `00_inbox/` into durable knowledge storage.

## Pending changes (ADR-009)

A v2 design is proposed in [DECISIONS.md ADR-009](../../DECISIONS.md). When ratified:
- Missing/partial frontmatter is **normalized** (not rejected) and staged to `01_ingest/ready/` with `status: skimmed`.
- The minion extracts `[[wikilinks]]` from body content into a `links:` array during normalization.
- The agent-driven middle (see `agents/ingest-agent.md`) handles classification and enrichment.
- `bin/prep-ingest` validates and moves files from `ready/ → queue/` after agent enrichment.
- Strict routing from `queue/ → 10_knowledge/` (documented below) is unchanged.

The v1 behavior below remains current until ADR-009 is accepted and Phase 3 of the plan ([planning/mainframe-agent-ingest-plan.md](../../../../planning/mainframe-agent-ingest-plan.md)) ships.

## Defaults
- Script: `bin/ingest-minion`
- Mode: dry-run unless `--apply` is passed
- Input: `00_inbox/` and `01_ingest/queue/`
- Durable output: `10_knowledge/<domain>/`
- Raw evidence output: `10_knowledge/<domain>/raw/`

## Steps
1. Place Markdown notes or convention-named raw PDFs in `00_inbox/`.
2. Run `bin/ingest-minion run --dry-run`.
3. Resolve any rejected or blocked items before applying.
4. Run `bin/ingest-minion run --apply`.
5. Run `bin/mindgraph-refresh` if durable knowledge notes changed and search should be refreshed immediately.

## File Rules
- Markdown files must contain the standard metadata from `.context/primitives.md`: `title`, `domain`, `type`, `status`, `source`, and `tags`.
- V1 routes only `type: "note"` and `type: "raw"` into `10_knowledge/`.
- Existing `10_knowledge/` domain directories are the domain whitelist.
- Raw PDFs should use `YYYY-MM-DD__domain__raw__slug.pdf`.
- If a raw PDF does not follow the filename convention, pass `--domain <domain>` and review the generated stub name before applying.

## Guardrails
- Dry-run first. The script refuses destination collisions and never overwrites existing files.
- Rejected files move to `01_ingest/rejected/` only during `--apply`.
- The raw PDF is preserved as evidence; the generated Markdown stub is only the searchable MindGraph wrapper.
- Do not use this workflow for `20_live/` state or `30_projects/` records in v1.
