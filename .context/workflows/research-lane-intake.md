# Research Lane Intake Workflow

Use this workflow when a new research question surfaces that merits its own bounded lane in the portfolio tracker.

## Purpose
Turn recurring, decision-impacting, or cross-project open questions into **lane trackers** (`lanes/<slug>/README.md`) with minimal friction, while preserving all rules:
- Tracker only (no knowledge content here).
- All durable captures still route `00_inbox/` → ingest-minion → `10_knowledge/`.
- First-principles convention.
- Dual MindGraph query pass before committing a lane.
- WIP discipline and operator confirmation.

This is the **explicit "add new questions to research lanes" step**.

## When to use (the trigger step)
- During or after a source-literature run, new side questions appear that deserve tracking.
- PRP01 / project sweep identifies a gap that is not covered by an existing lane.
- Agent runs, eval outputs, or MindGraph queries (esp. repeated weak_fit or scope warnings) reveal a missing foundation or specialization area.
- Operator session surfaces a high-stakes open question.
- Synthesis notes or plans name a reusable research strand.

**Do not** create a lane for one-off curiosity or transient lookup.

## Steps
1. **Emit the candidate** (anywhere)
   Add a block like this in the source artifact (run note, project plan, synthesis, log, agent output):

   ```markdown
   ## Research Lane Candidate

   - **lane_id**: C32          # optional; script suggests next
   - **slug**: intent-graphs-rag-routing
   - **central_question**: "How can intent and goal graphs drive routing and planning across specialized retrievers?"
   - **decision**: "Decide whether and how to make intent graphs first-class in MainFrame retrieval and agent harnesses."
   - **knowledge_domain**: "graph-memory"
   - **stakes**: high
   - **priority**: next
   - **trigger**: "surfaced during multi-RAG architecture planning in mindgraph-eval + C28/C29 work"
   - **handoff**: "30_projects/mindgraph-eval, 30_projects/mindgraph"
   ```

   (Scan-friendly: any file containing one or more such blocks can be fed to `bin/lane-intake scan`.)

2. **Dual MindGraph query pass** (mandatory)
   ```bash
   bin/mindgraph query "<question keywords>" --db ~/.mindgraph/mainframe.sqlite --json --top-k 6
   bin/mindgraph query "<question keywords>" --db ~/.mindgraph/mainframe-projects.sqlite --json --top-k 6
   ```
   Record nominations + trust labels. Treat as nominations only.

3. **Run intake**
   ```bash
   # Propose / dry-run (recommended first)
   bin/lane-intake scaffold \
     --question "..." \
     --decision "..." \
     --domain "graph-memory" \
     --trigger "path or description" \
     --slug "my-topic" \
     --priority next

   # Or parse emitters from a file
   bin/lane-intake scan 30_projects/research-lanes-strategy/plans/some-plan.md

   # Apply (creates folder + README + receipt + log append)
   bin/lane-intake scaffold ... --apply
   ```

4. **Review outputs**
   - New `lanes/<slug>/README.md` (populated from template).
   - `raw-materials/YYYY-MM-DD__proposed-lane-<slug>.md` (receipt with context, MindGraph results, suggested master-plan row).
   - Append in `log.md`.

5. **Commit to master plan**
   Copy the suggested table row from the receipt into the correct tier/section of `plans/research-lanes-master-plan.md`.
   Update any "active trackers" lists if appropriate.

6. **Handoff**
   - Freeze the plan-freezing checklist on the lane card (`first-principles-research-conventions.md`).
   - Run research with `.context/workflows/research-lane-loop.md` (source-literature → synthesis → close), not capture-only.
   - Use the lane README as the brief; update the capture index only as part of loop step 6.

## Guardrails
- Script refuses to overwrite existing slugs.
- Never auto-runs source-literature or ingests.
- New domains still require confirmation per ingest rules.
- Respect WIP cap (document in receipt).
- Always preserve provenance (trigger + dual-query output) in the receipt.
- Lane creation is a **portfolio decision**, not an automatic side effect of every question.

## Integration points (where the step is called)
- Source-literature workflow (post run note): scan for candidates and propose.
- Project research pipeline (PRP01): after gap sweep, promote to intake.
- Session-close / process-evaluation: harvest open questions.
- Agent instructions: when you surface a recurring decision question, emit a candidate block and/or run `bin/lane-intake scan`.

## Related
- `30_projects/research-lanes-strategy/plans/research-lanes-master-plan.md`
- `30_projects/research-lanes-strategy/plans/project-research-pipeline.md`
- `30_projects/research-lanes-strategy/plans/knowledge-routing.md`
- `30_projects/research-lanes-strategy/lanes/_TEMPLATE.md`
- `.context/workflows/source-literature.md`
- `bin/mindgraph` (strict CLI only)
- `.agents/skills/mindgraph-retrieval/SKILL.md`

## Quick usage (operator or agent)

After any research activity surfaces a question:

1. Append a candidate block to the relevant note or plan.
2. `bin/lane-intake scan that-file.md`   # review output + receipt
3. `bin/lane-intake scan that-file.md --apply`
4. Paste the suggested row into master-plan.md under the right tier.
5. Dual-query evidence and receipt already captured for provenance.

Example command that created C32:
```
bin/lane-intake scaffold \
  --question "..." --decision "..." --domain knowledge-systems \
  --trigger "..." --slug research-lane-intake --lane-id C32 --apply
```

## Claim discipline

Lane intake produces claim-bearing output, so
[epistemic-standard.md](epistemic-standard.md) and `EPISTEMIC_STANCE.md` bind
every capture and synthesis this workflow creates.

- **No source quotas, ever.** Do not set or infer a target count of sources for a
  lane. Ask a coverage question instead: is the decision answerable with what we
  found? A documented gap is a valid, and often better, lane outcome.
- Captures route through `01_ingest/`, where `bin/capture-validate` checks
  provenance. Never write a `type: raw` file into `10_knowledge/` directly.
- **Escape:** if a lane cannot be answered from real sources, close it as
  `blocked` with the gap named. That is a complete result, not a failed one.

**Stop state.** A lane that cannot find real evidence stops and says so. It does
not fill to a batch size.

Background: a source count in `bin/research-lane-loop` produced 107 captures
citing papers that do not exist
(`20_live/security/2026-08-09__fabricated-source-captures-in-10-knowledge.md`).
