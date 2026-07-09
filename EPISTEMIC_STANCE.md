# Epistemic Stance

This document establishes claim discipline for MainFrame. It dictates how work is described, what counts as support, and when a claim must remain conditional.

Truth-seeking takes precedence over conviction, aesthetics, or vibes. Operational procedure: `.context/workflows/epistemic-standard.md`.

## Core rules

1. **Separate facts from inferences**
   - *Observation*: "The script returned error 500 on three successive attempts."
   - *Source-claim*: "The author reports a 36% replication rate" (must cite source).
   - *Inference / hypothesis*: "The API rate limit is likely being exceeded."
   - Do not state inferences or hypotheses as settled facts. Label them explicitly.

2. **Source-backed confirmation**
   - For high-risk or live-updating domains (especially finance, legal, compliance, and markets), claims must link to supporting raw evidence.
   - If a claim cannot be verified against a source, mark low confidence or unverified.

3. **Model outputs are not ground truth**
   - Do not promote model-generated summaries as fact without human verification or explicit labeling.
   - LLM-derived claims carry `needs-audit` until reviewed.

4. **Preserve raw evidence**
   - Do not rewrite raw sources for tidiness. Summaries and extractions are separate notes; originals stay immutable evidence.

## Claim types

| Type | Label required |
| --- | --- |
| Observation | No (if directly witnessed or logged) |
| Source-claim | Yes — attribute to source |
| Inference | Yes — calibrated language ("likely", "suggests") |
| Hypothesis | Yes — confidence **low** / **very low** |

## Confidence language

Synthesized claims should use calibrated certainty language. Prefer:

- **High** — multiple independent sources or direct measurement
- **Moderate** — single strong source or consistent indirect evidence
- **Low** — sparse evidence, contested literature, or model-only support

Surface counterevidence when it exists. Prefer under-claiming over over-claiming.
