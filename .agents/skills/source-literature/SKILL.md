---
name: source-literature
description: Find, vet, deduplicate, and capture peer-reviewed or well-accepted literature into 00_inbox/ as raw evidence stubs for the ingest pipeline. Use when the user needs research sources, literature search, academic references, DOI/PubMed sourcing, or asks to complement ingest with upstream discovery. Triggers on "source literature", "find papers", "peer-reviewed sources", "research this topic".
status: implemented
---

# source-literature

## Purpose

Upstream complement to `ingest-source`. This skill handles **discovery and credibility gating** before files enter the ingest minion. It finds sources, assigns credibility tiers, deduplicates against the vault, and writes bibliographic raw stubs to `00_inbox/`.

The operator workflow lives in `.context/workflows/source-literature.md`. Credibility criteria live in [references/credibility-tiers.md](references/credibility-tiers.md).

## Inputs

- A research question or topic brief from the user (scope, stakes, target domain if known).
- Read-only access to `10_knowledge/<domain>/` and domain indexes.
- Optional: `bin/mindgraph query` for dedup nominations.
- Web search and bibliographic databases (PubMed, Crossref, Google Scholar, regulator sites).

## Outputs

- One or more Markdown stubs in `00_inbox/` with canonical naming `YYYY-MM-DD__<domain>__raw__<slug>.md`.
- A run note `00_inbox/YYYY-MM-DD__source-literature-run__<slug>.md` listing queries, candidates, accept/reject decisions, and handoff status.
- A short proposal table for user confirmation before bulk capture (when >3 sources).

## Procedure

### 1. Frame the search

Extract from the user request and map using a modified PICO framework (Richardson et al., 1995):

- **Problem/Entity (P)**: The core subject, obstacle, or system under review.
- **Intervention/Method (I)**: The specific protocol, software, tool, or strategy being introduced.
- **Comparison (C)**: The baseline, alternative method, or current state.
- **Outcome/Decision (O)**: The target decision or action this search supports.
- **Stakes** (high / medium / exploratory) per [credibility-tiers.md](references/credibility-tiers.md).
- **Target domain** — start from `10_knowledge/index.md` inventory; propose new seed domain only when distinct and recurring (Tier C, user confirmation before folder creation).
- **Exclusions** — what is out of scope.

### 2. Dedup against existing vault

Before searching externally:

- Glob `10_knowledge/<candidate-domain>/` for related filenames and titles.
- Grep for author surnames, DOIs, regulator doc IDs.
- Run `bin/mindgraph query "<topic keywords>"` when available; treat results as nominations only.
- Check domain source catalogs (e.g. `gxp-pharma-source-catalog`) — cite gaps, do not re-capture catalog entries unless a dedicated raw stub is missing.

### 3. Search and nominate

Use multiple channels and search methods:

| Channel | Best for |
|---------|----------|
| PubMed / Google Scholar | Peer-reviewed A/B tier |
| Crossref / DOI resolver | Bibliographic verification |
| Regulator and standards sites | Tier D institutional |
| arXiv / SSRN | Tier C preprints |

**Search Strategy (Cochrane Method):**
*   Build structured queries using Boolean logic (`AND` to connect concepts, `OR` to combine synonyms/free text, `NOT` to exclude).
*   Search grey literature (trials registers, white papers, government reports) to prevent publication bias, especially for high-stakes topics.

**Search Expansion (Bates' Berrypicking Model):**
If direct keyword searches yield insufficient results, meander iteratively using:
*   *Footnote Chasing*: Scan reference lists of key papers for foundational sources.
*   *Citation Searching*: Look up forward citations of key papers in citation databases.
*   *Author/Journal Runs*: Query prominent investigators and primary journals in the target domain.
*   *Area Scanning*: Check adjacent folders or topical index categories in the vault.

Prefer sources with stable identifiers (DOI, PMID, document version). Collect: title, authors, year, venue, URL, abstract snippet.

### 4. Tier and filter

For each candidate, assign a tier per [credibility-tiers.md](references/credibility-tiers.md). Reject below stake threshold. Log rejects in the run note with reason codes (`duplicate`, `tier-too-low`, etc.).

Present a **candidate table** to the user when:

- More than 3 sources would be captured, or
- Any source is Tier C/E, or
- A new domain is proposed.

Wait for explicit confirmation before writing captures.

### 5. Write capture stubs

Each accepted source becomes one `type: raw` file in `00_inbox/`:

```yaml
---
title: "<Full title>"
domain: "<proposed-domain>"
type: raw
status: queued
source: "<DOI URL or canonical regulator URL>"
source_tier: peer-reviewed | systematic-review | preprint | institutional | professional-consensus
tags: ["<domain-topic>", "needs-audit", "<tier-tag>"]
links: []
author: ["Surname, Initial.", "..."]
published: "YYYY"
retrieved_at: "YYYY-MM-DD"
source_type: web-clip
doi: "10.xxxx/..."   # when available
pmid: "12345678"     # when available
keywords: ["..."]
---
```

Body sections (evidence stub — not synthesis):

```markdown
## Bibliographic record

<Full citation. APA or Vancouver. Include DOI/PMID.>

## Abstract or summary

<Abstract text or, for Tier D, document scope summary from official page. Label if paraphrased.>

## Source assessment

- **Tier:** <tier label>
- **Why captured:** <one sentence tied to research question>
- **Full text:** <available | paywalled | guidance-pdf>
- **Dedup note:** <new | supplements existing [[wikilink]]>

## Capture context

<Optional: how this connects to active work. Inference labeled as inference.>
```

Do not paste full paywalled PDF text. Bibliographic record + abstract is sufficient for a stub.

### 6. Write run note

Following PRISMA flow standards (Page et al., 2021), log the search history and flow results. Create or append to the run note with:

- Research question (formatted under PICO primitives) and stakes.
- Exact queries executed (including database name, query syntax/terms, and yield counts).
- **PRISMA Flow Summary**: Records identified, records screened, accepted, and rejected.
- Candidate table (accepted + rejected with reason codes).
- Files written to `00_inbox/`.
- Proposed next step: `bin/ingest-minion run --dry-run` then ingest-agent.

### 7. Handoff

Tell the user:

1. Review captures in `00_inbox/`.
2. Run ingest pipeline per `.context/workflows/ingest-minion.md`.
3. After routing, run `bin/post-route-enrich --subset <domain>` (fetch OA full text + `bin/mindgraph-refresh`). Set `UNPAYWALL_EMAIL` in your shell for free Unpaywall PDF coverage.
4. For Tier C/E or high-stakes claims, schedule `bin/audit-sweep` after routing.

This skill **stops at inbox**. It does not invoke `prep-ingest`, rename to final canonical form in `10_knowledge/`, or synthesize notes.

## Guardrails

- **No synthesis in captures.** Stubs are bibliographic evidence, not extracted knowledge. Use `create-source-summary` / extraction-agent after ingest.
- **Calibrated claims.** Tier labels are retrieval gates, not verification. Keep `needs-audit` on all captures.
- **Provenance.** `source` field must be the canonical URL (DOI resolver preferred).
- **Immutability prep.** Write stubs as new files; never overwrite existing inbox captures.
- **Regulated domains.** For GxP/compliance topics, never imply compliance certification in capture context.
- **Epistemic stance.** Follow `EPISTEMIC_STANCE.md` — label inferences in Capture context.

## Related components

- `.context/workflows/source-literature.md` — operator sequence
- `agents/source-literature-agent.md` — subagent shell
- `.agents/skills/ingest-source.md` — downstream enrichment
- `.context/workflows/ingest-minion.md` — deterministic routing
- `EPISTEMIC_STANCE.md`, `.context/primitives.md`

## Evaluation

Track in process eval: dedup hit rate, tier distribution, downstream ingest success, user rejection rate on candidate tables.