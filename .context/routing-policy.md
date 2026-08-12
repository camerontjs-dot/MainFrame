# Ingest Routing Policy

Consumed by the ingest-agent (and, once calibrated per ADR-019, any classification
engine) when deciding where staged captures go. This file governs **placement only** —
domain, type, tags, park or route. It never decides whether content is true. Truth-work
belongs to the epistemic audit loop: routed raw clips carry `needs-audit`, which the
epistemic research system sweeps continuously after placement.

Maintenance rule: when the operator corrects a Tier B exception the same way twice, add
or amend a rule here in the same session. Policy changes are commits, so routing
behavior stays reviewable and diffable.

## Tiers (ADR-019)

- **Tier A — rule-matched, auto-apply.** A named rule below matches. Apply frontmatter,
  canonical rename, `bin/prep-ingest run --apply`, minion pass 2. Append a ledger row
  citing the rule (for example `rule:R3`). Tag routed raw clips `needs-audit`.
- **Tier B — exception.** No rule matches, the fit is weak, or the file suggests a new
  domain. Stay in `01_ingest/ready/`, add tag `routing-exception`, record a one-line
  `routing_note:` in frontmatter. Surfaced in the batch review table and `ingest-status`.
- **Tier C — always human.** Never auto-applied regardless of rule match: new top-level
  domains (ADR-011), anything destined for `20_live/`, `status: stable`, disposition
  `rejected`.

## Sensitivity overrides (checked before all other rules)

The protected class is **money-consequential state** — content where acting on a stale or
misrouted copy could cost money (operator clarification, 2026-06-10 batch pass 1).
Personally *scoped* research (e.g. region- or goal-specific analysis) is not sensitive by
itself and routes normally.

| Rule | Signal | Handling |
| --- | --- | --- |
| S1 | Personal financial state: accounts, balances, positions, allocations, deployment plans, tickers *held* (vs. analyzed) | Tier C. Propose `20_live/finance/` (after ADR-016 reconciliation) or park; never `10_knowledge/`. |
| S2 | Identity, credentials, family records | Tier C. Propose park. |
| S3 | Anything matching `20_live/AGENTS.md` defensive rules | Tier C. |

## Park rules (Tier A dispositions that do not route to knowledge)

Every parked file gets a `parked_reason:` frontmatter line stating why, in plain language
(amendment 2026-06-10). A park without a reason is not inspectable later.

| Rule | Pattern | Disposition |
| --- | --- | --- |
| P1 | Empty, untitled, or fragment notes (`Untitled*`, single-thought stubs with no source) | `parked` → `90_archive/second-brain-migration/parked/` |
| P2 | Code, scripts, configs (`.py`, `.sh`, `.bat`, `.ps1`, `.json`, `.jsx`) with no note context | `parked` (adopt into an owning project workbench manually if wanted) |
| P3 | Exact duplicate by batch-manifest or body hash | `duplicate-removed`; delete the redundant working copy — the canonical copy plus the batch `source-files/` snapshot preserve the bytes (amended 2026-06-10 per operator instruction, ADR-020) |
| P4 | Binary without a convention name (images, `.docx`, `.rtf`, `.xlsx`) | `parked`; convention-named PDFs go through the minion wrapper instead |
| P5 | Unrecoverable clipper placeholder ("Original clippings file could not be recovered") | `parked` with tags `placeholder-stub`, `re-clip-wanted`; list in the parked folder's `re-clip-list.md` so it stays findable |
| P6 | Stale generated artifacts: cron briefing emails, dated setup notes, price-data snapshots | `parked` with reason; generated output and public market data have no durable value (added 2026-06-10) |

## Adoption rule (checked after P-rules, before R-rules)

| Rule | Pattern | Handling |
| --- | --- | --- |
| B1 | Old-system operational docs: role prompts, project instructions, system audits and evals, automation guides, product references from pre-MainFrame systems | Adopt into `30_projects/second-brain-migration/raw-materials/legacy-systems/<system>/` with `status: archived` and tag `legacy-system-doc`. Everything stays in the migration project; promotion into active MainFrame projects is a later operator decision (ADR-020). |

## Routing rules (first match wins)

| Rule | Pattern (filename / content signals) | domain | type | tags |
| --- | --- | --- | --- | --- |
| R1 | X/Twitter clip (`Post by @…`, `Thread by @…`, x.com source) about AI agents, Claude/Codex, MCP | agents | raw | x-capture, needs-audit |
| R2 | AI tooling guides and listicles: Claude workflows, MCP servers, prompt packs, repo roundups — *excluding PKM/Obsidian contexts, which match R5 first* (amendment 2026-06-10, per ADR-013 intent) | agents | raw | needs-audit |
| R3 | GitHub repo clip or README about agent frameworks or automation | agents | raw | repo-clip, needs-audit |
| R4 | AI product strategy, monetization, consulting, AI-native business content | ai-business | raw | needs-audit |
| R5 | PKM, Obsidian, vault design, retrieval-first workflows | knowledge-systems | raw | needs-audit |
| R6 | Market, sector, or macro analysis; trading strategies and backtests *as research* (no personal positions) | finance | raw | needs-audit |
| R7 | LLM-conversation exports (ChatGPT/Grok/DeepSeek dumps) on market or macro topics | finance | raw | llm-output, needs-verification, needs-audit |
| R8 | AI-writing-detection and content-authenticity material | ai-detection | raw | needs-audit |
| R9 | Humour theory and humour writing | humour | raw | needs-audit |
| R10 | Reusable prompt or research templates with no personal data | agents | raw | template, needs-audit |
| R11 | Software engineering practice, code quality, research-software methodology | software-practice | raw | needs-audit |

## Defaults

- Evaluation order: S-rules, then P-rules, then B1, then R-rules (R5 before R2); first match wins; no match → Tier B.
- Cross-domain topics keep one domain and gain topic tags (e.g. an agent-framework repo about trading → `agents` + tag `finance`), rather than forcing a domain choice to carry topic signal (operator preference, 2026-06-10).
- Old-system documents that still carry durable knowledge route normally but get tag `legacy-system-doc` so provenance stays visible (operator preference, 2026-06-10).
- `type` defaults to `raw` for captures. Use `note` only for the user's own drafts.
- Never invent a new domain from a rule. New domains are ADR-011 territory (Tier C).
- A rule match is the autonomy ticket. If the match feels forced, it is not a match —
  Tier B exists so the policy stays honest.
