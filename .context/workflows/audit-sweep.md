# Audit Sweep Workflow

Use this workflow to ensure that material routed under the tiered ingest policy (ADR-019) receives post-placement verification. The goal is to make the compensating control for review-after (needs-audit tags + epistemic auditor) visible and routine before relying on Tier A auto-apply at scale.

## Philosophy
- Placement can be cheap and reversible (byte snapshots + append-only ledgers + no overwrites).
- Truth and claim quality are verified after the fact by the epistemic research system, not blocked at every file.
- The operator sees a clear pending-review surface in `20_live/epistemic-audit/` rather than having to hunt through 10_knowledge/.
- Deterministic discovery of candidates + LLM judgment for claim extraction/auditing.

## Prerequisites
- Files routed via Tier A or batch mode should carry `needs-audit` (or `needs-verification`) in their `tags:` list (enforced in ingest-agent batch mode and per-file enrichment).
- The epistemic-research-system workbench is functional (`bin/epistemic` wrapper).
- `20_live/epistemic-audit/pending-review/` and `contradictions/` directories exist (created by mainframe_bridge).

## Script / Entry Points
- Primary: `bin/epistemic sweep --mainframe` (orchestrator subcommand targeting MainFrame durable knowledge).
- Helper: `bin/audit-sweep` (thin deterministic wrapper; see below).
- Dry / check: `bin/audit-sweep --dry-run` or `bin/epistemic sweep --mainframe --dry-run`.
- Integration: Called from `bin/session-close --apply` (or reminded in `--check`).

## Steps
1. **Discover candidates deterministically**
   - Scan `10_knowledge/` (or a `--subset` per ADR-021) for Markdown files whose frontmatter `tags` list contains `needs-audit`.
   - Also surface recent (last N days) routed raw items even without the tag for coverage sampling.
   - Record the manifest: file path, date, domain, rule (if in ledger), current audit status.

2. **Surface the worklist**
   - Write or update `20_live/epistemic-audit/pending-review/sweep-YYYY-MM-DD.md` (or per-run).
   - For each candidate, include:
     - Link to the canonical file in 10_knowledge.
     - Extracted frontmatter (title, source, tags).
     - Brief context from the first section or Connections if present.
     - Placeholder for auditor output (claim list + verdicts).

3. **Run the auditor (judgment layer)**
   - Delegate to the epistemic harness (Researcher/Auditor agents via `bin/epistemic`).
   - Use existing `harness/auditor*.py`, `evaluator.py`, and belief_db.
   - Focus on claim extraction, support/contradiction detection, confidence.
   - For raw items: treat the document as source; generate or validate claims (respecting that raw body is evidence).
   - Publish full audit reports via the existing `mainframe_bridge.publish_audit_report` mechanism.

4. **Promote or park results**
   - High-confidence supported claims: the auditor (or operator review) can propose promotion to `status: stable` or synthesis into a companion `note`.
   - Contradictions or low-confidence: move to `contradictions/` or leave tagged `needs-audit` with notes.
   - Update the source file's tags (remove `needs-audit`, add `audited-YYYY-MM-DD` or `verified` / `disputed`) **only after operator review** for Tier C items or the first calibration runs.
   - Append to the relevant batch disposition-ledger where applicable (cross-reference by path or hash).

5. **Report and close the loop**
   - Emit counts: candidates found, audited, supported, contradicted, still pending.
   - Include in the next `bin/workflow-report`.
   - Update `20_live/epistemic-audit/` index or manifest if one exists.
   - Refresh MindGraph if new synthesized notes were created.

## Guardrails
- Never mutate raw evidence bodies. Only frontmatter tags/status and separate audit artifacts.
- The first several full sweeps after enabling Tier A are treated as calibration data (measure agreement with operator on a sample, per ADR-018/019).
- `needs-audit` is a signal for the system, not a permanent label. It should age off after verified handling.
- High-risk domains (finance sensitivity per routing-policy) remain Tier C regardless of auditor readiness.
- All automated writes to 20_live/ follow the volatility rules (dated, append or explicit snapshots).

## Related
- [.context/routing-policy.md](../routing-policy.md) — when `needs-audit` must be applied.
- [agents/ingest-agent.md](../../agents/ingest-agent.md) — batch and per-file tagging responsibility.
- [30_projects/epistemic-research-system/](../../30_projects/epistemic-research-system/) — the auditor implementation and mainframe_bridge.
- [.context/workflows/process-evaluation.md](../process-evaluation.md) — evaluate this sweep before widening Tier A autonomy.
- [DECISIONS.md](../../DECISIONS.md) — ADR-019 and follow-ups.
- `bin/session-close` and `bin/workflow-report` for integration points.

## Implementation Notes (Current State — 2026-06-18)

**Done:**
- `bin/audit-sweep` — discovery, manifest to `20_live/epistemic-audit/pending-review/sweep-*.md`, `--json`, `--subset`
- `mainframe_bridge.sweep_knowledge_for_audit_tags()` — calls audit-sweep dry-run JSON

**Not done (see `30_projects/epistemic-research-system/plans/remediation-backlog.md` Tier 1):**
- `bin/epistemic sweep --mainframe` — documented here but **not implemented**
- `audit-sweep --apply` does not invoke auditor; handoff is manual: `bin/epistemic run --source <file>` per manifest row
- Planned: `bin/epistemic audit-manifest --file <sweep.md> [--limit N]`

**ERS paths to avoid (ADR-011):** `watch`/`daemon`, `sweep-knowledge` auto-ingest, `audit-corpus` paragraph indexing — disabled by default.

**Still desired:**
- Hook session-close (remind in `--check`; optional `--apply`)
- workflow-report coverage metric ("X needs-audit, Y swept, Z audited")

**Canonical workflow:** `30_projects/epistemic-research-system/plans/epistemic-workflow.md`
