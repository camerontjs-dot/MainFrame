# Epistemic Stance

This document establishes the claim discipline for the Mainframe portfolio. It dictates how work is described, what counts as support, and when a claim must remain conditional.

Truth-seeking takes precedence over conviction, aesthetics, or vibes. The full operational standard — appraisal checklists, source canon, and agent obligations — lives in the local synthesis note `10_knowledge/knowledge-systems/epistemics/2026-06-17__knowledge-systems__note__mainframe-epistemic-standard.md`. Workflow: `.context/workflows/epistemic-standard.md`.

## Core Rules

1. **Separate Facts from Inferences**
   - *Observation*: "The script returned error 500 on 3 successive attempts."
   - *Source-claim*: "The author reports a 36% replication rate" (must cite source).
   - *Inference/Hypothesis*: "The API rate limit is likely being exceeded."
   - Do not state inferences, source-claims, or hypotheses as settled facts. Label them explicitly.

2. **Source-Backed Confirmation**
   - For high-risk or live-updating domains (especially finance, legal, compliance, and markets), all claims must link to their supporting raw source (the "evidence").
   - If a claim cannot be verified against a source, it must be marked with a low confidence indicator or noted as unverified.

3. **LLM Inferences are Not Truth**
   - Do not promote model-generated summaries or inferences as ground truth without human verification or explicit labeling.
   - All LLM-derived claims carry `needs-audit` until reviewed.

4. **Preserve Raw Evidence**
   - Raw source material must not be rewritten for tidiness. Summaries or extractions should be created as separate notes, preserving the original file as immutable evidence.

## Claim Types

| Type | Label required |
|------|----------------|
| Observation | No (if directly witnessed or logged) |
| Source-claim | Yes — attribute to source |
| Inference | Yes — calibrated language ("likely", "suggests") |
| Hypothesis | Yes — tag or confidence **low** / **very low** |

## Confidence Language

Synthesized claims must use GRADE-aligned certainty (see Guyatt et al. 2008, captured in epistemics canon):

| Certainty | When to use |
|-----------|-------------|
| **High** | Converging high-tier sources; further research unlikely to change conclusion |
| **Moderate** | Good evidence with limitations |
| **Low** | Single study, indirect evidence, or meaningful bias risk |
| **Very low** | Expert opinion only, exploratory sources, or significant conflict |

Credibility tiers (A–E) in `.agents/skills/source-literature/references/credibility-tiers.md` govern **what sources to retrieve**. GRADE certainty governs **what confidence to assign after appraisal**.

## Evidence Minimums

| Claim stakes | Minimum source tier (without operator override) |
|--------------|------------------------------------------------|
| High (legal, medical, compliance, compensation) | A or B |
| Medium (practice guidance, architecture) | A, B, or D |
| Exploratory / hypothesis | C or E; must stay `needs-audit` |

Institutional sources (Tier D) are authoritative for what bodies *expect* or *define*, not proof that a specific system complies.

## Disconfirmation

Any synthesis must surface the strongest available counterevidence. If sources conflict, record both positions with attribution. Do not bury dissent to preserve narrative coherence.

## Promotion Gate

| Status | Requirement |
|--------|-------------|
| `synthesized` | Claim types labeled; confidence assigned |
| `stable` | Operator-verified or audit-sweep cleared — **never** from LLM output alone |

A single published study is insufficient for `stable` (see Ioannidis 2005). Operator override requires logged rationale.

## Related

- `.context/workflows/epistemic-standard.md` — operator and agent procedure
- `.context/workflows/audit-sweep.md` — post-placement verification
- `.agents/skills/source-literature/references/credibility-tiers.md` — retrieval gates
- `10_knowledge/knowledge-systems/epistemics/` — canonical source base (local, gitignored)