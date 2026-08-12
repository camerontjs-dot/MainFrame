---
name: rename-material
description: Rename a file to the Mainframe convention YYYY-MM-DD__domain__type__slug.md after enrichment has resolved domain and type.
status: stub
---

# rename-material

## Purpose

Rename a file in `01_ingest/ready/` to the convention `YYYY-MM-DD__domain__type__slug.md` once the agent has resolved `domain` and `type`. This is the last step before `bin/prep-ingest` validates and moves to `queue/`.

## Status

**Stub** — to be expanded. Initial guidance:
- Date comes from frontmatter `captured` or `created` field; falls back to current date if missing.
- Slug is kebab-case, derived from title.
- Domain must be in the existing whitelist (subdirectories of `10_knowledge/`).
- Type must be `raw` or `note` for files routing through ingest (per ADR-007).

## Related

- [ingest-source](ingest-source.md) — the parent skill
- [classify-note](classify-note.md) — produces the domain/type the rename consumes
