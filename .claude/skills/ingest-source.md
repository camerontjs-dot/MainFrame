---
name: ingest-source
description: Walk a single file from 01_ingest/ready/ through the full agent-driven enrichment loop — read, classify (domain/type/tags), find connections, discuss proposal with user, enrich frontmatter + Connections, rename canonically, and hand off to bin/prep-ingest + minion pass 2. This is the primary skill for the ingest-agent subagent on organic (non-batch) captures.
status: implemented
---

# ingest-source

## Purpose

The canonical, reusable skill for the per-file judgment pass in the two-pass ingest architecture (ADR-009, ADR-011, ADR-019). It encapsulates everything between the deterministic minion pass 1 (which produces `status: skimmed` files in `01_ingest/ready/`) and the handoff to `bin/prep-ingest` (which moves to `queue/`) + minion pass 2 routing.

The skill is invoked by the [ingest-agent](../../agents/ingest-agent.md) subagent. After this skill completes its proposal + user confirmation + enrichment, the file is ready for the strict deterministic gate.

## Inputs
- A Markdown file in `01_ingest/ready/` with at minimum the minion-normalized frontmatter (`title`, `domain` possibly empty, `type`, `status: skimmed`, `source`, `tags`, and the `links:` array extracted from body wikilinks).
- Read-only access to `10_knowledge/<existing-domains>/` (and their indexes) for calibration and connection finding.
- Optional: `bin/mindgraph query` results for graph-augmented signals (when available).

## Outputs
- Same file (or atomically renamed version) with:
  - `status: extracted`
  - Fully populated `domain`, `tags`, `source`, `type`
  - `links:` array extended with judgment-driven connections
  - Optional `## Connections` prose section appended (never mutates original body for `type: raw`)
  - Canonical filename `YYYY-MM-DD__domain__type__slug.md`
- The file remains in `01_ingest/ready/` until `bin/prep-ingest run --apply` is called by the caller.
- A clear proposal presented to the user for confirmation before any enrichment writes.

## Procedure (step-by-step — this is the implementation of the skill)

1. **List and select**
   Enumerate files in `01_ingest/ready/`. Process **one at a time** for organic captures (batch mode uses a different table flow in the ingest-agent). Skip any file already at `status: extracted` (it is awaiting `prep-ingest`).

2. **Read the full content** of the selected file.

3. **Propose classification (domain, type, tags)**
   - `domain`: Match against the inventory and rules in `10_knowledge/index.md`. Start with existing domains. If the topic is genuinely new, distinct, and likely to recur, **propose a new domain (or subdomain)** with short rationale and **wait for explicit user confirmation** before creating folders (ADR-011 / Tier C). Never force a weak fit. Leave `domain: ""` and stop if uncertain — the downstream gate will reject it anyway.
   - `type`: `raw` for unprocessed evidence/clippings/PDF wrappers; `note` for synthesized/user-authored content.
   - `tags`: Add useful retrieval tags (lowercase kebab-case). Include required signals such as `needs-audit` (or `needs-verification`) for raw or low-synthesis routed material (per routing-policy and the audit-sweep workflow). Preserve any existing good tags from the minion or prior state.

4. **Find and propose connections** (ADR-033 dual-channel graph)
   - Start with the deterministic `links:` array already populated by the ingest minion (wikilinks extracted from body, code spans stripped).
   - Extend with judgment: read nearby notes in the target `10_knowledge/<domain>/`, use `bin/mindgraph query "key terms"` when operational for nominations, cross-domain pointers.
   - Add targets to frontmatter `links:` using **unique canonical trailing slugs** (e.g. `gxp-pharma-source-catalog`) or **full filename stems** when ambiguous. MindGraph indexes `links:` and body wikilinks equally after refresh.
   - For `type: raw`, prefer frontmatter `links:` and/or an appended `## Connections` section with `[[wikilinks]]`. For notes, body wikilinks are optional when `links:` is populated. Do not wikilink `30_projects/` paths — use prose until bridge registry exists.
   - Proposed connections are nominations only — they do not assert truth.

5. **Present the full proposal to the user as a single confirm-or-correct surface** (critical judgment gate)
   Show:
   - Proposed full frontmatter block (`domain`, `type`, `tags` (with `needs-audit` if applicable), `source`, updated `links`).
   - Proposed new canonical filename.
   - Draft `## Connections` section (if any) with prose explanation of relationships.
   - Open questions: new vs. known? Does this affect existing understanding? Split or keep together? Domain justification if proposing new.
   - Any warnings from minion pass 1.

   **Wait for explicit user confirmation or specific corrections** before proceeding to step 6. Do not auto-apply enrichment.

6. **Enrich after confirmation**
   - If a new top-level domain was confirmed by the user: create `10_knowledge/<domain>/`, `10_knowledge/<domain>/raw/`, and a minimal `index.md` (see 10_knowledge/index.md rules).
   - Update the file's frontmatter with the confirmed values and set `status: routed` then `status: extracted`.
   - Append `## Connections` section at the bottom when useful (for raw items: frontmatter `links:` is sufficient for the graph; Connections adds human-readable context. Body is immutable evidence. For user notes/drafts: inline wikilinks are optional when `links:` is complete).
   - If a raw item would benefit from a synthesized companion, prefer calling the sibling `create-source-summary` skill to produce a separate `note` rather than editing the raw.

7. **Rename atomically** to the canonical `YYYY-MM-DD__domain__type__slug.md` (use captured date from frontmatter or today). Write the new path first, verify, then remove the old if using separate operations.

8. **Handoff to deterministic pipeline**
   - Run `bin/prep-ingest run --dry-run` (validates strict frontmatter, `status: extracted`, canonical name, known domain whitelist, no collisions).
   - On clean result: `bin/prep-ingest run --apply` (moves ready/ → queue/).
   - Then `bin/ingest-minion run --apply` (routes queue/ → 10_knowledge/<domain>/).
   - Optionally `bin/mindgraph-refresh`.
   - For batch flows the caller coordinates the single review table instead of per-file discussion.

## Guardrails (enforced by this skill and its caller)
- **Body immutability for raw**: Never rewrite the original content of `type: raw` items. All enrichment lives in frontmatter and appended sections.
- **Read-only on durable knowledge**: Only read `10_knowledge/` to find connections and calibrate proposals. All writes stay inside `01_ingest/`.
- **New domains are human**: Always Tier C. Propose with evidence from `10_knowledge/index.md`; create folders only after user OK.
- **needs-audit tagging**: For material that will be routed under Tier A or batch rules, ensure the tag is present so `bin/audit-sweep` + the epistemic auditor can verify post-placement (see `.context/workflows/audit-sweep.md`).
- **Epistemic stance**: Follow `.context/workflows/epistemic-standard.md` and `EPISTEMIC_STANCE.md`. Label claim types. Assign confidence. Preserve raw sources. MindGraph results are retrieval nominations, not verified relationships. Record provenance.
- **One file at a time for organic**: Batch mode (ADR-019) uses the table flow instead.

## Error & Edge Handling
- Malformed or missing required frontmatter after minion: surface warning; repair in proposal if recoverable.
- Unknown domain in proposal: force user confirmation or park as exception.
- Collision on rename or prep-ingest: abort and report; do not overwrite.
- User rejects proposal: leave file as-is (or with minimal `routing_note`) and move to next or ask for guidance.

## Related Skills & Components
- `classify-note` — focused sub-skill for domain/type/tags proposal (can be called internally).
- `extract-metadata` — optional source metadata enrichment (PDF info etc.).
- `rename-material` — the atomic rename step.
- `create-source-summary` — for turning a raw into a synthesized note sibling.
- `agents/ingest-agent.md` — the subagent that orchestrates this skill (and the batch table path).
- `bin/prep-ingest`, `bin/ingest-minion`, `.context/workflows/audit-sweep.md`, `10_knowledge/index.md`, `.context/routing-policy.md`, `01_ingest/AGENTS.md`.

## Evaluation
This skill should be exercised and measured during process evaluations (see `30_projects/mainframe-process-eval/`). Track: proposal acceptance rate, time-to-extracted, downstream routing success rate, number of needs-audit tags correctly applied, and any Tier B exceptions that later graduate to rules.

## Status Note
This skill was promoted from stub (2026-06-13) as part of closing the gap between the detailed agent procedure and reusable skill contracts. The long-form procedure now lives here; the ingest-agent definition should remain focused on role, guardrails, batch vs. per-file mode, and orchestration.