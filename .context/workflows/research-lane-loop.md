# Research Lane Loop

**One complete research pass.** Starts at source-literature and ends at knowledge synthesis. Designed to be easy to run and safe to loop.

## Profile

| Field | Value |
|-------|-------|
| structural_type | workflow |
| owner_surface | `30_projects/research-lanes-strategy/` + `.context/workflows/` |
| authority | workflow-contract |
| volatility | stable |
| related_surfaces | source-literature, ingest-minion, epistemic-standard, research-lane-intake |

## Purpose

Replace ad-hoc “capture then maybe synthesize later” runs with a single unit of work:

```text
select → brief → preflight → source-literature → ingest → synthesize → close → loop?
```

Tracker stays a link index. Durable claims live only in `10_knowledge/`.

## When to use

- Completing research for one lane phase (foundation, taxonomy, specialization, or application/eval).
- Weekly portfolio cadence: pick a P0/P1 lane and finish one pass end-to-end.
- Operator says “run the research loop”, “full loop”, or “source to synthesis” for a lane.

## When not to use

- **New lane only** → `.context/workflows/research-lane-intake.md` (then come back here).
- **File already in hand** → drop in `00_inbox/` and start at **Ingest** (step 4).
- **Project closeout extraction** → `.context/workflows/extract-knowledge.md`.
- **Portfolio governance only** (priority, archive, kill) → `bin/lane-intake` + master plan; no sources needed.

## Loop unit (what one iteration is)

| Field | Rule |
|-------|------|
| **Scope** | Exactly **one** lane × **one** phase |
| **Batch size** | **3–4** accepted sources (plus 1 failure/counterevidence when stakes are high) |
| **Start gate** | Lane README has decision, `knowledge_domain`, `capture_tags`, and a stop condition |
| **End gate** | Synthesis note written (or explicit skip logged) **and** tracker capture index updated |
| **Default phases** | `foundation` → `taxonomy` → `specialization` → `application` (see first-principles conventions) |

One iteration is **not** “finish the whole lane.” Multi-phase lanes re-enter this loop once per phase.

## Command card (copy/paste)

```bash
# 0) Select + classify resume (preferred entry)
bin/research-lane-loop doctor                    # top P0 active lane + class A–D
# or: bin/research-lane-loop preflight --slug <slug>
# or: bin/lane-intake list --priority P0 --status active

# 0b) Portfolio hygiene — stale capture indexes (class D)
bin/research-lane-loop audit-indexes --status active
# bin/research-lane-loop audit-indexes --status active --repair-index

# 2) Preflight MindGraph (replace QUESTION / DOMAIN)
bin/mindgraph query "QUESTION" --db ~/.mindgraph/mainframe.sqlite --json --top-k 6
bin/mindgraph query "QUESTION" --db ~/.mindgraph/mainframe-projects.sqlite --json --top-k 6

# 4) Ingest after inbox stubs exist
bin/ingest-minion run --dry-run
bin/ingest-minion run --apply
# If files landed in 01_ingest/ready/: ingest-agent → bin/prep-ingest run --apply → ingest-minion again
export UNPAYWALL_EMAIL="${UNPAYWALL_EMAIL:-you@example.com}"
bin/post-route-enrich --subset DOMAIN

# 5) Optional synthesis candidates
bin/suggest-synthesis --domain DOMAIN --dry-run

# After synthesis note written
bin/mindgraph-refresh
```

Agent judgment steps (1 brief, 3 source-literature, 5 synthesize, 6 close) use the skills listed under **Related**.
**Deterministic preflight:** `bin/research-lane-loop` (tests: `tests/test_research_lane_loop.py`, `tests/test_lane_intake.py`).

---

## Steps

### 0. Select lane + phase

```bash
bin/research-lane-loop doctor
# or explicit:
bin/research-lane-loop preflight --slug <slug>
bin/lane-intake list --priority P0 --status active
```

Record from preflight output (do not guess):

- `lane_id`, slug, path to `lanes/<slug>/README.md`
- **Phase** for this pass: `foundation` | `taxonomy` | `specialization` | `application`
- Whether the lane’s **stop condition** can be met this pass
- **Resume class** A–D and **recommended step** from `bin/research-lane-loop`

| Resume class | Signal | Enter loop at |
|--------------|--------|---------------|
| **A Fresh** | No inbox stubs; few/no knowledge raws | Step 1 → 2 → 3 |
| **B Partial batch** | Matching stubs in `00_inbox/` | Step 4 (ingest) then 5 |
| **C Ingested** | Lane-tagged raws/notes in `10_knowledge/` | Step 5 (or next phase if stop met) |
| **D Stale tracker** | Capture index lists `00_inbox/` for files already in knowledge | `audit-indexes --repair-index`, then re-preflight |

**Dogfood note (2026-07-13):** P0 list was empty until priority aliases (`immediate`≡P0). Class D false WIP showed on C28 until `audit-indexes --repair-index`. Prefer `bin/research-lane-loop doctor` over hand-classifying.

If the plan-freezing checklist on the card is empty, fill it first (first-principles conventions). Do not search externally until step 2 is complete (unless class B/C/D).

### 1. Brief (read-only)

From the lane README, copy as the run brief (do not re-invent):

| Field | Source |
|-------|--------|
| Central question / decision | README body |
| `knowledge_domain` | frontmatter |
| `capture_tags` | frontmatter |
| Stakes | frontmatter |
| Stop condition | first-principles section |
| Phase tag | chosen in step 0 |

Every capture in this pass must include:

```yaml
tags: ["research-lane", "lane-<id>", "<phase>", "needs-audit", "<topic>"]
```

Example: `["research-lane", "lane-c28", "application", "needs-audit", "agent-memory"]`.

### 2. Preflight dedup

Before any external search:

1. Dual MindGraph query (knowledge + projects) with the lane question keywords.
2. Grep / list `10_knowledge/<knowledge_domain>/` for existing raws and notes.
3. Check domain source catalogs if present.
4. Note gaps and **reuse hits** (do not re-capture).

Write gap notes into the eventual source-literature run note. Treat MindGraph rows as **nominations only**.

### 3. Source-literature (**loop start** — skip if resume class B/C)

Follow `.context/workflows/source-literature.md` and `.agents/skills/source-literature/SKILL.md`:

1. Frame PICO from the lane brief (step 1).
2. Search, tier, and filter (credibility tiers).
3. Confirm candidates when >3 sources, any Tier C/E, or new domain.
4. Write **3–4** `type: raw` stubs to `00_inbox/`.
5. Write run note: `00_inbox/YYYY-MM-DD__source-literature-run__<lane-or-topic-slug>.md`.
6. **Atomic batch rule:** every row marked ACCEPT in the run note must have a real file on disk before handoff. If a stub fails to materialize, either write it now or demote to REJECT/`deferred-captures-backlog` — never leave “accepted” orphans (MH01 Li survey was orphaned 19 days).

**Batch shape (default):**

| Slot | Count | Purpose |
|------|-------|---------|
| Foundation / phase-primary | 2–3 | Definitions, mechanisms, or phase-specific core |
| Taxonomy or standard | 0–1 | Map the domain (taxonomy phase; optional otherwise) |
| Counterevidence / failure | 0–1 | Required when stakes = high |
| Official/current docs | as needed | Tools, regulators, APIs (date-stamped) |

Do **not** synthesize in stubs. Stop at inbox + run note.

### 4. Ingest pipeline

```bash
bin/ingest-minion run --dry-run
bin/ingest-minion run --apply
```

If anything is in `01_ingest/ready/`:

1. Run ingest-agent enrichment (`agents/ingest-agent.md`).
2. `bin/prep-ingest run --apply`
3. `bin/ingest-minion run --apply` again

Then enrich full text and refresh search:

```bash
bin/post-route-enrich --subset <knowledge_domain>
```

Optional for high-stakes: `bin/audit-sweep --apply --subset <knowledge_domain>`.

### 5. Knowledge synthesis (**loop end**)

**Write a synthesis note** in the knowledge domain when **any** of these is true:

| Trigger | Action |
|---------|--------|
| ≥3 related raws share this `lane-*` tag (this pass or cumulative for the phase) | Write / update phase synthesis note |
| Phase stop condition is met with current evidence | Write synthesis that answers the decision |
| `bin/suggest-synthesis --domain <domain>` flags this cluster | Prefer writing now over parking |

**Skip synthesis only if** sources were pure gap-fill under an existing current note **and** the stop condition is already satisfied. Log the skip in `log.md` with a link to the existing note.

**Note path:**

```text
10_knowledge/<domain>/YYYY-MM-DD__<domain>__note__<lane-or-phase-slug>.md
```

**Required note shape:**

1. Decision this note supports (one sentence from lane card).
2. Claims labeled per `.context/workflows/epistemic-standard.md` (observation / source-claim / inference / hypothesis + confidence).
3. Links to the raw stubs consumed (`links:` + body citations).
4. **Adverse Findings & Limitations** (boundary conditions, literature gaps, compensating controls) — required by first-principles conventions.
5. Same `lane-*` + phase tags as captures.
6. Explicit **stop-condition check**: met / not met / deferred (with reason).

Then:

```bash
bin/mindgraph-refresh
```

### 6. Tracker close (mandatory)

Do not leave the loop mid-air:

1. **Lane README** — append rows to **Captured knowledge** (paths + type + status only; no claim copy).
2. **Phase status** — mark phase done / in progress / blocked.
3. **Project `log.md`** — one entry: lane, phase, N sources, synthesis path, stop-condition result.
4. **Project `README.md` `next_action`** — what the next loop should be.
5. **Side questions** — emit `## Research Lane Candidate` blocks; `bin/lane-intake scan <run-note>` if any deserve new lanes.
6. **Deferred sources** — append to `plans/deferred-captures-backlog.md` (do not stall the loop).

### 7. Loop decision (close the *pass*, not necessarily the *lane*)

| Outcome | Next |
|---------|------|
| Phase stop condition **met**; more phases remain | Same lane, **next phase** → restart at step 0 |
| Phase incomplete (need more sources) | Same lane + phase → step 2/3 |
| Blocked | Log + deferred backlog; pick another P0 lane |
| New high-priority gap | `research-lane-intake`, then loop that lane |
| **Lane** stop condition **met** | Enter **lane close** (below) — do **not** auto-archive mid-pass |

#### Lane close (separate closing micro-loop — optional after step 7)

Archiving is **not** part of every research pass. It is a portfolio decision once the **lane** stop condition is met:

```text
stop check → handoff block on lane README → bin/lane-intake archive <slug>   # dry-run
         → bin/lane-intake archive <slug> --apply → portfolio README/log
```

**Dogfood (2026-07-13):** C28 closed this way → `lanes/completed/cognitive-agent-memory-architectures/`.

| Keep archive separate because | If you fold archive into every loop |
|-------------------------------|-------------------------------------|
| Most passes only finish a *phase* | Agents will archive too early |
| Archive moves cards to `lanes/completed/` | Loses WIP signal mid-research |
| Needs operator confirmation for portfolio | Silent archive is hard to reverse |

**Rule of thumb:** research-lane-loop ends at **synthesis + tracker close + decision**. Archive is the **closing loop** for a finished lane (step 7 terminal branch), not a default step 0–6 action.

**Looping is intentional.** Prefer many short end-to-end passes over one open-ended search that never synthesizes.

---

## Resume map (if interrupted)

| Last completed step | Resume at |
|---------------------|-----------|
| Stubs in `00_inbox/` only | Step 4 (ingest) |
| Ingested, no synthesis | Step 5 |
| Synthesis written, tracker stale | Step 6 |
| Tracker closed, stop not met | Step 7 → new iteration step 2 or 3 |
| Run note ACCEPT list longer than files on disk | Write missing stubs or demote to deferred; then step 4 |
| Capture index shows `00_inbox/` but files live in `10_knowledge/` | Step 6 repair only (class D) |

Do not re-run source-literature for the same DOIs/titles already in the vault.

## Process metrics (log after each run)

Record in project `log.md` one line each:

- **select_friction:** did P0 list work, or need fallback?
- **resume_class:** A/B/C/D
- **sources_accepted / sources_ingested**
- **synthesis:** path or skip
- **minutes_approx:** rough wall time (optional)
- **process_fix:** one sentence if workflow/tooling should change

## Definition of done (one iteration)

- [ ] 3–4 raws (or justified smaller batch) routed to `10_knowledge/<domain>/`
- [ ] Run note preserved (inbox or routed with stubs)
- [ ] Synthesis note written **or** explicit skip logged with existing note path
- [ ] `bin/mindgraph-refresh` after durable note change
- [ ] Lane capture index + phase status updated
- [ ] `log.md` line + `next_action` set
- [ ] Loop decision recorded (next phase / next lane / archive / blocked)

## Anti-patterns

- Stopping after inbox capture (“we’ll synthesize later”) without a dated next_action
- Synthesizing inside `lanes/` or `plans/`
- Re-capturing catalog or vault hits
- Skipping dual MindGraph preflight
- Mixing two phases in one batch without tagging
- Treating MindGraph hits as verified claims
- Leaving paywalled full-text as a hard stop (stub + abstract is enough to continue; flag `full-text-pending`)

## Related

| Piece | Role |
|-------|------|
| `.context/workflows/source-literature.md` | Step 3 detail |
| `.agents/skills/source-literature/SKILL.md` | Discovery judgment |
| `.context/workflows/ingest-minion.md` | Step 4 detail |
| `.context/workflows/epistemic-standard.md` | Step 5 claim discipline |
| `.context/workflows/research-lane-intake.md` | New lanes from side questions |
| `30_projects/research-lanes-strategy/plans/knowledge-routing.md` | Tracker vs knowledge boundary |
| `30_projects/research-lanes-strategy/plans/first-principles-research-conventions.md` | Phase model + adverse findings |
| `30_projects/research-lanes-strategy/plans/lane-ingest-process-notes.md` | Retrospectives / friction |
| `.agents/skills/research-lane-loop/SKILL.md` | Agent orchestration of this loop |
| `bin/lane-intake` | Select, priority, archive |
| `bin/suggest-synthesis` | Synthesis candidate surfacing |

## Worked pattern

C28 application/eval pass (2026-07-12) is the reference full loop: preflight → 6 sources → ingest + enrich → synthesis design note → stop condition met → handoff to `mindgraph-eval`. See project `log.md` that day.

## Portfolio doctor + handoff (G2/G4/G8)

```bash
bin/research-lane-loop doctor --all-active
bin/research-lane-loop preflight --slug <slug>   # shows next_phase, blocker, suggested_command
```

**Typed handoffs** (gate vs opportunity vs application, etc.) are defined in:

→ **`.context/workflows/research-project-handoff.md`**
→ template: `.context/templates/research-handoff.md`

```bash
# Gate: clears/blocks a project decision
bin/research-lane-loop handoff-project --slug <lane> --to <project> \
  --kind gate --note "..." --evidence "10_knowledge/..."

# Application: planned build phase
bin/research-lane-loop handoff-project --slug <lane> --to <project> \
  --kind application --note "..."

# Opportunity: consider later — does NOT steal busy next_action
bin/research-lane-loop handoff-project --slug <lane> --to <project> \
  --kind opportunity --note "..."

# Constraint / experiment / craft / knowledge / split / close — see workflow
```

**Rule:** research-lane-loop ends at synthesis + tracker close + decision.
Handoff is how that decision becomes project work **without** treating every signal as “do this next.”
