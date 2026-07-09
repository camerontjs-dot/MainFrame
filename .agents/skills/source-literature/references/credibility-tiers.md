# Source credibility tiers

Retrieval gates for `source-literature`. Tiers label **evidence type**, not truth. Every capture stays `type: raw` until ingest and optional audit.

## Tier definitions

| Tier | Label | Accept when | Required metadata | Default tags |
|------|-------|-------------|-------------------|--------------|
| **A** | `peer-reviewed` | Indexed journal article with DOI or PubMed ID; clear methods | `doi` or `pmid`, `author`, `published`, `source_tier: peer-reviewed` | `peer-reviewed`, `needs-audit` |
| **B** | `systematic-review` | Systematic review, meta-analysis, or Cochrane/Campbell-style synthesis | same as A | `systematic-review`, `meta-analysis`, `needs-audit` |
| **C** | `preprint` | arXiv, bioRxiv, SSRN, etc. with stated methods; not yet peer-reviewed | `source_tier: preprint`, preprint URL | `preprint`, `needs-audit` |
| **D** | `institutional` | Government, standards body, regulator, WHO/ICH/PIC/S, major university report | issuing body, document ID/version, `published` or `retrieved_at` | `institutional`, `needs-audit` |
| **E** | `professional-consensus` | Major textbook chapter, citation-heavy handbook, widely cited conference proceedings (e.g. USENIX, ACM) | `author`, `published`, citation count or "canonical reference" note in capture context | `professional-consensus`, `needs-audit` |
| **Reject** | — | SEO blogs, undisclosed AI summaries, no methods, abstract-only with no full text path, duplicate of vault capture | — | log in run note only |

## Risk calibration

| Claim stakes | Minimum tier without explicit operator OK |
|--------------|-------------------------------------------|
| High (legal, medical, compliance, compensation numbers) | A or B |
| Medium (practice guidance, architecture critique) | A, B, or D |
| Exploratory / hypothesis formation | C or E allowed; must stay `needs-audit` |

Institutional guidance (D) is authoritative for **what regulators expect**, not proof that a specific system complies.

## Deduplication checks

Before capture, search:

1. `10_knowledge/<domain>/` filename and title patterns
2. `bin/mindgraph query "<author> <year> <key term>"` when operational
3. Existing source catalogs (e.g. `gxp-pharma-source-catalog` in `regulated-systems`)

If the source is already cited inside a synthesized note but has no dedicated raw capture, prefer a **raw bibliographic stub** linked to that note rather than skipping.

## Reject reasons (log in run note)

- `duplicate` — already in vault with same DOI/URL
- `no-full-text` — cannot obtain abstract + bibliographic record + stable URL
- `tier-too-low` — below stake threshold
- `weak-methods` — opinion piece without citations
- `paywall-blocked` — record only if bibliographic metadata is complete from PubMed/Crossref; flag `full-text-pending`

## Operational mapping (GRADE / MainFrame)

Credibility tiers govern **retrieval**. GRADE certainty (Guyatt et al. 2008) governs **synthesis output**. See `EPISTEMIC_STANCE.md` and `10_knowledge/knowledge-systems/epistemics/` (local).

| Tier | Starting certainty (before appraisal downgrade) | MainFrame use |
|------|--------------------------------------------------|---------------|
| A | Moderate → high (pending audit) | Primary evidence for high-stakes claims |
| B | Moderate → high (pending audit) | Preferred for synthesis and promotion |
| C | Low | Exploratory only; never sole basis for high-stakes |
| D | Moderate for institutional facts; low if generalized | Regulators, SEP, CASP, CEBM — authoritative for *expectations*, not compliance proof |
| E | Low → very low | Canonical references; hypothesis formation |

**Downgrade certainty** for: risk of bias, inconsistency across sources, indirect evidence, imprecision, publication bias, or unresolved conflict (GRADE factors).

**OCEBM alignment (informal):** Tier B ≈ Level 1; Tier A ≈ Level 2–3; Tier D institutional ≈ Level 4–5 for guidance documents.

## Relationship to ingest

Captures land in `00_inbox/` with `type: raw`. The ingest pipeline (`ingest-minion` → `ingest-source`) handles domain assignment, connections, and routing. This skill does not set `status: extracted` or write to `10_knowledge/`.