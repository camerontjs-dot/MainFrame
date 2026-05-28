# Ingest Minion Workflow

Use this workflow when moving captured files from `00_inbox/` into durable knowledge storage. The minion makes two deterministic passes around the agent-driven middle defined in [agents/ingest-agent.md](../../agents/ingest-agent.md) (ADR-009).

## Defaults
- Script: `bin/ingest-minion`
- Mode: dry-run unless `--apply` is passed
- Input: `00_inbox/` and `01_ingest/queue/`
- Agent-pending output: `01_ingest/ready/`
- Durable output: `10_knowledge/<domain>/`
- Raw evidence output: `10_knowledge/<domain>/raw/`

## Pass 1 — staging from `00_inbox/`

Markdown files in the inbox are read permissively:
- **Strict-valid frontmatter** (all 6 required keys present, valid type + status) → staged to `01_ingest/queue/` for routing in pass 2.
- **Missing or partial frontmatter, or any invalid value** → normalized in place (defaults filled, `status: "skimmed"`, body `[[wikilinks]]` extracted into `links:`), then moved to `01_ingest/ready/` for the [ingest-agent](../../agents/ingest-agent.md) to enrich.
- **Unreadable as text or malformed YAML structure** → routed to `01_ingest/rejected/` as a dead letter.

PDFs continue to follow the existing raw-evidence path and stage to `01_ingest/queue/` for pass 2.

## Pass 2 — routing from `01_ingest/queue/`

Files in `queue/` go through the strict v1 quality gate, unchanged from ADR-007:
- Markdown must have all required keys, a known domain (the existing `10_knowledge/<domain>/` whitelist), and `type` in `{note, raw}`.
- PDFs must match `YYYY-MM-DD__domain__raw__slug.pdf` (or be passed with `--domain <domain>`).
- Files that fail the strict gate move to `01_ingest/rejected/`.

## Steps
1. Place Markdown notes or convention-named raw PDFs in `00_inbox/`.
2. Run `bin/ingest-minion run --dry-run`.
3. Resolve any rejected or blocked items before applying.
4. Run `bin/ingest-minion run --apply`.
5. Review `01_ingest/ready/` and invoke the [ingest-agent](../../agents/ingest-agent.md) on anything there.
6. After the agent finishes a file, run `bin/prep-ingest run --apply` (ADR-009 Phase 4) to move it from `ready/ → queue/`.
7. Run `bin/ingest-minion run --apply` again to route the now-ready file into `10_knowledge/<domain>/`.
8. Run `bin/mindgraph-refresh` if durable knowledge notes changed and search should be refreshed immediately.

## File Rules
- Markdown files must contain the standard metadata from `.context/primitives.md`: `title`, `domain`, `type`, `status`, `source`, and `tags`. The minion fills missing keys during pass-1 normalization; pass-2 routing requires all keys filled with valid values.
- The `links:` array is populated by the minion's deterministic wikilink extraction; the agent can extend it with additional connections.
- Routing into `10_knowledge/<domain>/` is limited to `type: "note"` and `type: "raw"`.
- Existing `10_knowledge/` domain directories are the domain whitelist; new domains are created manually.
- Raw PDFs should use `YYYY-MM-DD__domain__raw__slug.pdf`. If a raw PDF does not follow the filename convention, pass `--domain <domain>` and review the generated stub name before applying.

## Guardrails
- Dry-run first. The script refuses destination collisions and never overwrites existing files.
- Files routed to `01_ingest/ready/` are normalized in place (the file is rewritten with canonical frontmatter); the body content is preserved verbatim.
- Rejected files move to `01_ingest/rejected/` only during `--apply`, and only when the file is unreadable as text or has truly malformed YAML structure.
- The raw PDF is preserved as evidence; the generated Markdown stub is only the searchable MindGraph wrapper.
- Do not use this workflow for `20_live/` state or `30_projects/` records.
