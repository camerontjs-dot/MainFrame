---
name: research-lane-loop
description: >
  Run one complete research-lane pass from source-literature through ingest to
  knowledge synthesis and tracker close. Use when the user asks to run the
  research loop, full loop, source-to-synthesis, complete research for a lane,
  or finish a foundation/taxonomy/specialization/application pass. Do NOT use
  for lane creation only (research-lane-intake), single-source capture without
  synthesis intent, or project closeout extraction (extract-knowledge).
status: implemented
---

# research-lane-loop

## Purpose

Orchestrate **one loopable research iteration** for a portfolio lane:

```text
select → brief → preflight → source-literature → ingest → synthesize → close → loop?
```

The operator workflow (command card, resume map, definition of done) lives in
`.context/workflows/research-lane-loop.md`. This skill is the agent procedure
that drives that workflow without inventing shortcuts.

## Inputs

- A lane id/slug, or permission to pick the top P0/P1 active lane.
- Optional **phase** override: `foundation` | `taxonomy` | `specialization` | `application`.
- Optional: pre-authorized candidate count (default confirm when >3 or Tier C/E).

## Outputs

- Inbox raw stubs + source-literature run note (step 3).
- Routed files under `10_knowledge/<domain>/` (step 4).
- Phase synthesis note (or logged skip) under `10_knowledge/<domain>/` (step 5).
- Updated lane capture index, project `log.md`, and `next_action` (step 6).
- Explicit loop decision for the next iteration (step 7).

## Procedure

Follow `.context/workflows/research-lane-loop.md` steps **0–7** in order.

### Judgment rules

1. **Lane README is the brief.** Do not reframe the central question unless the operator asks. Use frontmatter `capture_tags`, `knowledge_domain`, and stakes verbatim.
2. **Classify resume before searching.** A Fresh / B Partial inbox / C Ingested no synthesis / D Stale tracker — see workflow step 0. Prefer resume over a redundant source-literature pass.
3. **Select with fallback.** `bin/lane-intake list --priority P0 --status active`; if empty, `list --status active` (legacy `immediate`≡P0 after alias fix).
4. **One phase per run.** Tag every capture with the phase. If the operator wants “whole lane,” run sequential iterations, not one mixed batch.
5. **Batch size 3–4** accepted sources. Prefer depth + counterevidence over a long low-tier dump. **Atomic ACCEPT:** every accepted row gets a real file or is deferred — no orphan accepts.
6. **Preflight before search.** Dual MindGraph (knowledge + projects) + vault greps. Log dedup rejects in the run note.
7. **Delegate discovery** to the `source-literature` skill; do not synthesize inside raw stubs.
8. **Ingest is mandatory** before synthesis. Use dry-run then apply; then `bin/post-route-enrich --subset <domain>`.
9. **Synthesis ends the loop.** Write `type: note` synthesis when ≥3 related lane raws exist or the phase stop condition is met. Include Adverse Findings & Limitations and epistemic labels (`.context/workflows/epistemic-standard.md`).
10. **Tracker is links only.** Update capture index paths to `10_knowledge/` (never leave stale `00_inbox/` rows after ingest).
11. **Always close the pass.** Even if synthesis is skipped, update log + next_action + loop decision + process metrics.
12. **Archive is a lane-close action, not a default loop step.** Only run `bin/lane-intake archive <slug> --apply` when the **lane** stop condition is met (step 7 terminal branch), after handoff is logged. Do not archive after a single foundation/taxonomy pass.

### Command vocabulary (do not invent)

```bash
bin/research-lane-loop doctor
bin/research-lane-loop doctor --all-active
bin/research-lane-loop preflight --slug <slug>
bin/research-lane-loop audit-indexes --status active
bin/research-lane-loop audit-indexes --status active --repair-index
bin/research-lane-loop handoff-project --slug <slug> --to <project> \
  --kind gate|application|opportunity|constraint|experiment|craft|knowledge|split|close \
  --note "..." [--evidence path] [--urgency high|medium|low]
bin/lane-intake list --priority P0 --status active
bin/mindgraph query "..." --db ~/.mindgraph/mainframe.sqlite --json --top-k 6
bin/mindgraph query "..." --db ~/.mindgraph/mainframe-projects.sqlite --json --top-k 6
bin/ingest-minion run --dry-run
bin/ingest-minion run --apply
bin/prep-ingest run --apply
bin/post-route-enrich --subset <domain>
bin/suggest-synthesis --domain <domain> --dry-run
bin/mindgraph-refresh
bin/lane-intake archive <slug> --apply   # only when lane stop condition met
bin/lane-intake scan <run-note>          # side-question candidates
```

**Handoff kinds** (do not treat all as application): see `.context/workflows/research-project-handoff.md`.

Always run **preflight** before source-literature. Trust its `resume_class` over ad-hoc ls of the inbox.

## Output format (end-of-run report)

Return a short report with:

| Section | Content |
|---------|---------|
| Lane / phase | id, slug, phase |
| Sources | accepted count, paths under `10_knowledge/` |
| Synthesis | path or explicit skip + existing note |
| Stop condition | met / not met / deferred |
| Tracker | capture index updated? log line? |
| Next loop | same phase / next phase / next lane / archive / blocked |

Do **not** add: research claims outside the synthesis note, new lanes without intake, or durable knowledge written only under `30_projects/`.

## Guardrails

- **Start at source-literature** (or step 4 if stubs already exist); **end at synthesis + close**.
- Tracker-only boundary: ADR-005 style — no landscapes or claim digests under `lanes/`.
- MindGraph nominations are not proof.
- Paywalled full text is not a hard stop; abstract stub + `full-text-pending` is enough to continue.
- New domains require operator confirmation before folder creation.
- High-stakes claims keep `needs-audit` until audit-sweep / operator review.

## Related components

- `.context/workflows/research-lane-loop.md` — operator sequence (source of truth for steps)
- `.agents/skills/source-literature/SKILL.md` — step 3
- `.context/workflows/ingest-minion.md` — step 4
- `.context/workflows/epistemic-standard.md` — step 5
- `.context/workflows/research-lane-intake.md` — new lanes only
- `30_projects/research-lanes-strategy/plans/knowledge-routing.md`
- `30_projects/research-lanes-strategy/plans/first-principles-research-conventions.md`

## Evaluation

Track: time select→close, % runs that end with synthesis (or justified skip), dedup reject rate, stop-condition hit rate per phase, forgotten tracker updates.
