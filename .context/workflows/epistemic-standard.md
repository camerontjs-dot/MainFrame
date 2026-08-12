# Epistemic Standard Workflow

Use this workflow whenever MainFrame work produces or evaluates factual claims — synthesis, extraction, project decisions, agent output, or promotion to `stable`.

## Defaults

- Contract: [EPISTEMIC_STANCE.md](../../EPISTEMIC_STANCE.md)
- Deep reference: `10_knowledge/knowledge-systems/epistemics/2026-06-17__knowledge-systems__note__mainframe-epistemic-standard.md` (local)
- Credibility tiers: `.agents/skills/source-literature/references/credibility-tiers.md`
- Post-placement audit: `.context/workflows/audit-sweep.md`

## When to use

- Writing or reviewing a `note` in `10_knowledge/`
- Extraction-agent or ingest-source enrichment
- Project `decisions.md` entries with factual claims
- Any output that could be mistaken for settled truth

## When not to use

- Purely procedural logs (file moved, script ran) with no factual claims
- Raw captures (`type: raw`) — bibliographic stubs only; claims stay unverified until extraction

## Steps

1. **Classify each claim** — observation, source-claim, inference, or hypothesis per EPISTEMIC_STANCE.
2. **Check evidence tier** — does the supporting source meet stakes minimum (A–E table)?
3. **Run appraisal** — answer the 10 checklist questions in the epistemic standard note (CASP-adapted).
4. **Assign confidence** — high / moderate / low / very low (GRADE-aligned).
5. **Search for counterevidence** — document strongest challenge; lower certainty or split claim if warranted.
6. **Tag appropriately** — `needs-audit` on anything below promotion gate; never set `stable` from LLM alone.
7. **Hand off** — for durable notes, run `bin/audit-sweep --apply --subset <domain>` when ready for promotion review.

## Appraisal checklist (summary)

1. Clear, falsifiable claim?
2. Right source type for the claim?
3. Selection bias avoided?
4. Methods stated and replicable?
5. Confounders considered?
6. Precision matches confidence language?
7. Independent sources consistent?
8. Evidence direct (not adjacent)?
9. Publication bias risk assessed?
10. Conflicts logged with attribution?

Full detail in the epistemics synthesis note.

## Promotion checklist

Before `status: stable`:

- [ ] Claim types labeled throughout
- [ ] Confidence assigned per claim or section
- [ ] Counterevidence section present (or documented search)
- [ ] High-stakes claims backed by Tier A/B (or operator override logged)
- [ ] Not based on single study alone
- [ ] Audit-sweep reviewed or operator explicitly verified

## Pipeline position

```
Source discovery (source-literature)
    → ingest (needs-audit on raws)
    → extraction / synthesis (this workflow)
    → audit-sweep (verification)
    → stable (operator gate)
```

## Guardrails

- Tiers label evidence type, not verified truth.
- Vibes, aesthetics, and narrative coherence are not evidence.
- "I don't know yet" is a valid output.
- Contradictions go to `20_live/epistemic-audit/contradictions/` or stay tagged `needs-audit`.
## Stop state

The one this workflow most needs, because the failure it guards is a claim that
cannot be supported and an author under pressure to ship something.

**If a claim cannot be verified against a real source, stop promoting it.** Leave
it `synthesized`, label it as inference or hypothesis per the claim-type table,
and record in the note *why* verification failed: source unreachable, source
found but does not support the claim, or no source located. All three are
complete outcomes.

**Escape.** A documented gap is a finished result and carries no penalty. There
is no target number of sources and never should be. Finding one real source and
recording the gap is a better result than three that resolve to nothing.

**Never** resolve the tension by weakening the claim's language until the weak
evidence fits. Calibrated confidence describes evidence you have; it does not
launder evidence you do not.

This is the station where the 2026-08-09 incident happened. A source count in
`bin/research-lane-loop` met a capture schema that required `url` / `authors` /
`year`, and between them there was no way to record "I looked and found nothing."
107 captures cited papers that do not exist. See
`10_knowledge/agents/2026-08-10__agents__note__every-rule-needs-an-honest-failure-path.md`.
