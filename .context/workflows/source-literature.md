# Source Literature Workflow

Use this workflow when you need peer-reviewed or well-accepted sources **before** ingest. It complements `ingest-minion` by handling discovery, credibility gating, and inbox capture.

## Defaults

- Skill: `.agents/skills/source-literature/SKILL.md`
- Subagent: `agents/source-literature-agent.md`
- Credibility reference: `.agents/skills/source-literature/references/credibility-tiers.md`
- Output: `00_inbox/` raw stubs + run note
- Downstream: `.context/workflows/ingest-minion.md` → `ingest-source` skill

## When to use

- Starting research on a new topic (e.g. data integrity, salary negotiation).
- Gap-filling an existing domain collection (check vault first).
- User asks for "peer-reviewed sources" or "well-accepted literature."

## When not to use

- File already in hand → drop in `00_inbox/` and run ingest directly.
- Fast social/article clip → `x-bookmark-web-clipper` workflow.
- Claim extraction from existing notes → epistemic audit / extraction-agent path.

## Steps

1. **Frame** — Write research question, stakes, target domain, exclusions in the run note.
2. **Dedup** — Search `10_knowledge/<domain>/`, source catalogs, and MindGraph before external search.
3. **Search** — Invoke `source-literature` skill (or source-literature-agent). Agent returns candidate table with tier labels.
4. **Confirm** — User approves candidates (required when >3 sources, any Tier C/E, or new domain proposed).
5. **Capture** — Agent writes stubs to `00_inbox/` as `YYYY-MM-DD__<domain>__raw__<slug>.md`.
6. **Run note** — Agent writes `YYYY-MM-DD__source-literature-run__<topic-slug>.md` with queries, accept/reject log, file list.
7. **Ingest handoff**:
   ```sh
   bin/ingest-minion run --dry-run
   bin/ingest-minion run --apply
   ```
8. **Agent enrich** — Invoke ingest-agent on `01_ingest/ready/` per `agents/ingest-agent.md`.
9. **Post-route enrich** — After stubs land in `10_knowledge/<domain>/`:
   ```sh
   export UNPAYWALL_EMAIL=you@example.com   # free API; optional but recommended
   bin/post-route-enrich --subset <domain>
   ```
   Fetches OA full text, appends `## Full text extract`, then runs `bin/mindgraph-refresh` so deeper body terms enter the search index.
10. **Optional audit** — `bin/audit-sweep --apply --subset <domain>` for `needs-audit` items.
11. **Capture surfaced questions as lanes** — Any side questions, gaps, or recurring uncertainties that emerged during the run should be emitted as `## Research Lane Candidate` blocks (see `.context/workflows/research-lane-intake.md`). Run `bin/lane-intake scan <run-note>` (or scaffold directly). This is the explicit step for "adding new questions to research lanes". Dual MindGraph pass and receipt are produced automatically.

## Capture filename convention

```
YYYY-MM-DD__<domain>__raw__<author-or-body>-<short-slug>-<year>.md
```

Examples:

- `2026-06-17__negotiation__raw__small-salary-negotiation-2007.md`
- `2026-06-17__regulated-systems__raw__pda-data-integrity-history-2018.md`

## Run note convention

```
YYYY-MM-DD__source-literature-run__<topic-slug>.md
```

Include: question, stakes, queries, candidate table, rejects with reason codes, captures written, ingest status.

## Guardrails

- Captures are `type: raw` — bibliographic stubs, not synthesis.
- All captures carry `needs-audit` until epistemic review.
- Institutional guidance (FDA, MHRA, WHO) is Tier D — authoritative for expectations, not compliance proof.
- Do not route directly to `10_knowledge/` — inbox → ingest pipeline only.
- New domains require user confirmation before folder creation (same rule as ingest-agent).

## Pipeline position

```
Research question
    → source-literature (this workflow)
    → 00_inbox/
    → ingest-minion
    → ingest-source
    → 10_knowledge/<domain>/
    → knowledge synthesis (required end of a research-lane pass)
    → tracker close + optional research-lane-intake for side questions
```

For a **full research-lane pass** (source-literature through synthesis, loopable by phase), use `.context/workflows/research-lane-loop.md` and `.agents/skills/research-lane-loop/SKILL.md`. This workflow remains the discovery step only.