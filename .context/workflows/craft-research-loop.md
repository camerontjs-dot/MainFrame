# Craft Research Loop

**Product / craft trial-and-error research.** Separate from literature and system evals.

| Loop | Question | Ends with |
|------|----------|-----------|
| research-lane-loop | What do sources say? | Synthesis in `10_knowledge/` |
| project-experiment-loop | What does a protocol measure? | Registry + `last-eval-action.md` |
| **craft-research-loop** | What works for *this* product/stack? | Trial FINDINGS + proof index + project `next_action` |

## Profile

| Field | Value |
|-------|-------|
| structural_type | workflow |
| owner_surface | `30_projects/<slug>/` craft labs |
| skill | `.agents/skills/craft-research-loop/SKILL.md` |
| CLI | `bin/craft-research-loop` |

## Purpose

Make trial-and-error **finishable and citable** without dumping every smoke run into eval-registry or research lanes.

```text
question → scaffold trial → run → FINDINGS (keep|kill|iterate)
  → proof index / cull → log + next_action → promote? → loop
```

## When to use

- Image/video generation bake-offs, runtime stack trials
- Integration prototypes (phone bridge, dashboard UX)
- “Does this setting/workflow/tool path work for us?”
- Any project with many intermediate artifacts and a need to **keep only proof**

## When not to use

- Peer-reviewed / institutional literature → research-lane-loop
- Harness/MindGraph/process metrics that change promotion gates → project-experiment-loop
- Pure unit-test green/red → CI

## Loop unit

| Field | Rule |
|-------|------|
| **Scope** | One project × **one primary question** |
| **Artifact** | `outputs/<YYYY-MM-DD>-<slug>/` (+ optional `FINDINGS.md`) |
| **Start** | Written question + success criteria *before* reviewing winners |
| **End** | Verdict recorded + proof index updated + `next_action` set |
| **Promotion** | Optional: knowledge extract, research lane, or single eval_run_id |

## Command card

```bash
# 0) Select project + see open trials
bin/craft-research-loop preflight --project image-generation-lab
bin/craft-research-loop triage --project image-generation-lab

# 1) Open a trial (before running)
bin/craft-research-loop scaffold \
  --project image-generation-lab \
  --question "Does SDXL light refine beat prep-only Lanczos on green-lizard micro-detail?" \
  --decision "If no, keep prep-first defaults; if yes, change default refine path." \
  --slug "sdxl-light-vs-prep"

# 2) Run the trial in the workbench (project-specific tools)
# ... generate, measure, save artifacts into the trial folder ...

# 3) Close (mandatory)
bin/craft-research-loop close \
  --project image-generation-lab \
  --trial 2026-07-13-sdxl-light-vs-prep \
  --verdict keep|kill|iterate \
  --findings "One-paragraph observation + recommendation"

# 4) Optional promotion
bin/craft-research-loop promote --project image-generation-lab --trial … --to knowledge
bin/craft-research-loop promote --project image-generation-lab --trial … --to experiment
bin/craft-research-loop promote --project image-generation-lab --trial … --to lane
```

## Steps

### 0. Preflight

- Read project README `goal` / `next_action`
- Confirm proof index path (default `outputs/RESEARCH_PROOF_INDEX.md`)
- List open trials (folders without FINDINGS or status: running)
- Dual MindGraph only if the trial depends on prior domain knowledge (optional)

### 1. Frame the trial

Write **one** primary question and the decision it supports. No multi-question bake-offs without a primary.

Template: `.context/templates/craft-trial.md` (also written by `scaffold`).

### 2. Scaffold

Create:

```text
30_projects/<slug>/outputs/YYYY-MM-DD-<trial-slug>/
  TRIAL.md      # question, criteria, procedure (pre-results)
  FINDINGS.md   # filled at close (or during)
  # media / logs / json as needed
```

Register row in proof index as **open** (or omit until close — prefer open for WIP visibility).

### 3. Execute

- Record exact models, params, hardware, manual interventions
- Separate **observation** from **interpretation**
- Keep failed runs (do not delete only because ugly)
- Do not change the primary question mid-trial; open a new trial instead

### 4. Close (definition of done)

- [ ] `FINDINGS.md` has: observations, interpretation, limitations, **verdict**
- [ ] Verdict is exactly one of: `keep` | `kill` | `iterate`
- [ ] Proof index updated (KEEP / remove / supersede)
- [ ] Ephemeral intermediates culled **or** explicitly kept with reason
- [ ] Project `log.md` one entry
- [ ] Project `next_action` updated
- [ ] Action card: `30_projects/<slug>/outputs/LAST_CRAFT_ACTION.md`

### 5. Promote (optional, explicit)

| Verdict path | Promotion |
|--------------|-----------|
| Durable domain lesson | `bin/extract-knowledge` or research-lane-loop capture |
| Decision-bearing metric for promotion gates | One `eval_run_id` via project-experiment-loop scaffold |
| Recurring cross-project question | research-lane-intake candidate |
| Local product default only | `decisions.md` + proof index is enough |

### 6. Loop decision

| Outcome | Next |
|---------|------|
| `iterate` | New trial slug; link prior FINDINGS |
| `keep` | Adopt default; optional decisions.md ADR |
| `kill` | Record anti-pattern; don’t re-run without new hypothesis |
| Knowledge gap | research-lane-loop |
| Need formal metric | project-experiment-loop |

## Proof index contract

Every craft lab should maintain `outputs/RESEARCH_PROOF_INDEX.md` (or path in README):

| Section | Content |
|---------|---------|
| **Keep** | Paths that still prove a disposition |
| **Removed** | Culled ephemera + why |
| **Open** | Running trials (optional) |
| **How to re-run** | Commands / plan pointers |

## Project-local action card

Unlike eval portfolio triage, craft action is **per project**:

```text
30_projects/<slug>/outputs/LAST_CRAFT_ACTION.md
```

Written by `close` and `triage`. Not mixed into `last-eval-action.md`.

## Anti-patterns

- Endless generates with no FINDINGS
- Promoting a single pretty image to a product default
- Leaving durable knowledge only in `outputs/` forever
- Stuffing bake-offs into eval-registry by default
- Multi-question “matrix” without a primary success criterion

## Related

- research-lane-loop, project-experiment-loop
- `30_projects/AGENTS.md` extract-knowledge rule
- Image lab reference: `outputs/RESEARCH_PROOF_INDEX.md`
- Workbench EXP template (project-local) can feed TRIAL.md

## Dogfood reference

| Date | Project | What ran | Smooth? |
|------|---------|----------|---------|
| 2026-07-13 | image-generation-lab | Close realism bake-off **keep**; pixel SDXL smoke **kill**; stack upgrades **keep**; scorecard **iterate** (weights); scaffold post-install | Yes — close works on legacy folders; triage prefers formal `running` |
| 2026-07-13 | integration-lab | Scaffold E01 G1; **iterate** (ttyd/tmux/tailscale missing); scaffold after-install follow-up | Yes — first trial creates proof index; blocked-on-tools is valid iterate |

### Friction observed

| Issue | Mitigation |
|-------|------------|
| Many legacy `outputs/` dirs look “open” | Triage prioritizes formal `TRIAL.md` running; artifact-only is low priority |
| `iterate` needs immediate scaffold | CLI tip after close; operator should scaffold next question same session |
| Close without prior TRIAL.md | Allowed; still writes FINDINGS + proof index |
| Blocked on install/operator | Use **iterate**, not hang forever on `running` |

### Smooth path (confirmed)

```text
preflight → close legacy keep|kill → scaffold next → (blocked?) close iterate → scaffold tighter
```

## Dogfood — batch20 / multi-loop (2026-07-13)

### What worked
- Close-all legacy artifact folders with explicit keep + findings
- Multi-project preflight/triage (13 projects total across two sets) exit 0
- Project-local LAST_CRAFT_ACTION stays out of eval portfolio

### Friction → improve
| Issue | Fix direction |
|-------|----------------|
| Proof index append creates duplicate section headers | Structured rewrite on close |
| Iterate-for-operator-install still reads as “open work” | `blocked_on: operator` tone on action card |
| skill-eval lint red on craft skill | Schema alignment; not a close blocker |

Cross-loop gaps: `30_projects/mainframe-process-eval/outputs/2026-07-13-three-loop-process-gaps.md`.
