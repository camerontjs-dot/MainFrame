---
name: classify-note
description: Assign domain, type, and tags to a file based on its content. Propose to user for confirmation before applying.
status: stub
---

# classify-note

## Purpose

Read a file in `01_ingest/ready/` and propose:
- **`domain`** — one of the existing `10_knowledge/<domain>/` subdirectories.
- **`type`** — `raw` (unprocessed evidence) or `note` (synthesized content).
- **`tags`** — free-form, lowercase, kebab-case topic markers.

## Status

Implemented (2026-06-13) as a focused sub-skill of ingest-source. Use it when the parent skill (or ingest-agent in batch mode) needs a clean classification proposal.

## Procedure (as callable sub-skill)
1. Read the full target file (and its current frontmatter + minion-extracted `links:`).
2. Read `10_knowledge/index.md` and sample 3-5 recent/representative notes from each plausible target domain for calibration.
3. Propose exactly one `domain` (existing preferred; propose new only with strong distinctness + recurrence justification + explicit user confirmation later).
4. Propose `type`: default to `raw` for captures/clippings/PDF-derived; use `note` for the operator's own synthesized thinking.
5. Propose 3-8 `tags` (kebab-case, lowercase). Always include provenance/retrieval signals (`x-capture`, `repo-clip`, `pdf`, `llm-output`, etc.) and the audit signal `needs-audit` (or `needs-verification`) when the item will be routed under Tier A/batch rules or is raw evidence.
6. Return a structured proposal object (domain, type, tags list, short rationale, any warnings). Do not mutate the file.

## Rules
- Never invent a domain from thin air for a single file. New top-level domains are Tier C (user confirmation required; see 10_knowledge/index.md seed-domain rule and ADR-011/020).
- Tags are for retrieval and routing policy, not exhaustive keywords.
- Surface "routing-exception" signals clearly when fit is weak.
- Respect sensitivity overrides from `.context/routing-policy.md` (finance state etc. → Tier C, propose 20_live or park).

## Related
- [ingest-source](ingest-source.md) — calls this (or equivalent logic) as step 3.
- [extract-metadata](extract-metadata.md) — sibling for other frontmatter fields.
- `.context/routing-policy.md` and `10_knowledge/index.md` — the source of truth for rules and domain inventory.

## Related

- [ingest-source](ingest-source.md) — the parent skill
- [extract-metadata](extract-metadata.md) — fills in the rest of frontmatter
