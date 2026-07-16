# Ingest Minion Workflow

Use this workflow when moving captured files from `00_inbox/` into durable knowledge storage. The minion makes two deterministic passes around the agent-driven middle defined in [agents/ingest-agent.md](../../agents/ingest-agent.md) (ADR-009).

## Defaults
- Script: `bin/ingest-minion`
- Mode: dry-run unless `--apply` is passed
- Input: `00_inbox/` and `01_ingest/queue/`
- Agent-pending output: `01_ingest/ready/`
- Durable output: `10_knowledge/<domain>/`
- Raw evidence output: `10_knowledge/<domain>/raw/`
- Suggestion output: warning lines in the dry-run/apply report; these do not mutate the source file.

## Pass 1 — staging from `00_inbox/`

Markdown files in the inbox are read permissively:
- **Strict-valid frontmatter** (all 6 required keys present, valid type + status) → staged to `01_ingest/queue/` for routing in pass 2.
- **Missing or partial frontmatter, or any invalid value** → normalized in place (defaults filled, `status: "skimmed"`, body `[[wikilinks]]` extracted into `links:`), then moved to `01_ingest/ready/` for the [ingest-agent](../../agents/ingest-agent.md) to enrich.
- **Malformed frontmatter** → normalized to `01_ingest/ready/` with a warning so the agent can repair metadata without losing the capture.
- **Unreadable Markdown, unsupported inbox files, unconvention-named PDFs, or PDFs naming unknown domains** → left in `00_inbox/` with a concrete suggestion. Pass 1 should not dead-letter these files.

PDFs continue to follow the existing raw-evidence path only after they have a convention filename and known destination domain.

When PDF document metadata is available, the minion may add optional fields such as `author`, `created`, `modified`, `description`, `keywords`, and `source_type: "pdf"` to suggestions or generated raw stubs. This is best-effort provenance metadata, not a verified source claim.

## Pass 2 — routing from `01_ingest/queue/`

Files in `queue/` go through the strict v1 quality gate, unchanged from ADR-007:
- Markdown must have all required keys, a known domain (the existing `10_knowledge/<domain>/` whitelist), and `type` in `{note, raw}`.
- PDFs must match `YYYY-MM-DD__domain__raw__slug.pdf` (or be passed with `--domain <domain>`).
- Files that fail the strict gate move to `01_ingest/rejected/`.

## Steps
1. Place Markdown notes or convention-named raw PDFs in `00_inbox/`.
2. Run `bin/ingest-minion run --dry-run`.
3. Review suggestions and blockers. Warnings can be handled by the ingest-agent; errors should be resolved before applying.
4. Run `bin/ingest-minion run --apply`.
5. Review `01_ingest/ready/` and invoke the [ingest-agent](../../agents/ingest-agent.md) on anything there.
6. After the agent finishes a file, run `bin/prep-ingest run --apply` (ADR-009 Phase 4) to move it from `ready/ → queue/`.
7. Run `bin/ingest-minion run --apply` again to route the now-ready file into `10_knowledge/<domain>/`.
8. **Post-route enrich (raw stubs)** — pull OA full text and refresh search index:
   ```sh
   bin/post-route-enrich --subset <domain>
   ```
   Runs `bin/fetch-source-text --apply` (Europe PMC, direct PDF/HTML, Unpaywall when `UNPAYWALL_EMAIL` is set), then `bin/mindgraph-refresh`. Use `--dry-run` to preview; `--file` for a single stub.
9. Run `bin/mindgraph-refresh` alone if only notes changed (no new raw stubs) and search should be refreshed immediately.

## File Rules
- Markdown files must contain the standard metadata from `.context/primitives.md`: `title`, `domain`, `type`, `status`, `source`, and `tags`. The minion fills missing keys during pass-1 normalization; pass-2 routing requires all keys filled with valid values.
- The `links:` array is populated by the minion's deterministic wikilink extraction; the agent can extend it with additional connections.
- Routing into `10_knowledge/<domain>/` is limited to `type: "note"` and `type: "raw"`.
- Existing `10_knowledge/` domain directories are the strict pass-2 whitelist. New domains are proposed by the ingest-agent, justified against the local `10_knowledge/index.md` (public shape: `10_knowledge/index.template.md`), and created only after user confirmation.
- Topics should begin as notes or index entries. Promote a topic to a domain or subdomain only when it is broad, recurring, and has enough material to need its own navigation.
- Raw PDFs should use `YYYY-MM-DD__domain__raw__slug.pdf`. If a raw PDF does not follow the filename convention, pass `--domain <domain>` and review the generated stub name before applying.
- Generated raw stubs may include optional source metadata extracted from the file. The raw file remains the source of truth.

## Guardrails
- Dry-run first. The script refuses destination collisions and never overwrites existing files.
- Files routed to `01_ingest/ready/` are normalized in place (the file is rewritten with canonical frontmatter); the body content is preserved verbatim.
- First-pass inbox problems produce suggestions instead of rejects. Rejected files move to `01_ingest/rejected/` only during strict pass-2 apply from `01_ingest/queue/`.
- The raw PDF is preserved as evidence; the generated Markdown stub is only the searchable MindGraph wrapper.
- Do not use this workflow for `20_live/` state or `30_projects/` records.
