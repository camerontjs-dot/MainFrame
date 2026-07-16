# MainFrame framework decisions (public distillations)

These are **adopter-facing** rationales for how the public MainFrame shape works. They are not a diary of private projects, career strategy, or live WIP inventories.

For the full private ADR stream, see the operator monorepo (not published).

---

## Lifecycle before topic

**Decision:** Organize the tree by information lifecycle (`inbox` → `ingest` → `knowledge` / `live` / `projects` → `archive`) rather than by subject domain first.

**Why:** Capture, durable notes, volatile state, and project outcomes have different update and trust rules. Mixing them under topic folders invites silent overwrites and unclear provenance.

**Consequence:** Domain folders appear under lifecycle roots (especially `10_knowledge/`). Agents and scripts must respect local `AGENTS.md` overlays.

---

## Private monorepo vs public surface

**Decision:** Keep a full local monorepo as system of record; publish an **allowlisted clean-history** export, not a flip of private git history.

**Why:** Ignore rules do not erase history. Career, path, and project disclosures can survive in old commits.

**Consequence:** Public tips are built with export tooling and leak scans. Nested private projects stay under ignored `30_projects/*`.

---

## MindGraph as nested retrieval, nominations not answers

**Decision:** Ship MindGraph as a nested local hybrid engine (lexical + semantic + optional graph). Treat hits as context nominations with trust labels when dual indexes exist.

**Why:** Agents need retrieval without pretending search equals verification.

**Consequence:** Docs and skills must say “nominate, then verify against sources.” Private corpora never ship as the default example vault.

---

## Pixel tracker is onboarding-first (not a file dump)

**Decision:** The public control-room story is **demo fixtures + agent onboarding** (pick agent → portable telemetry/hooks → smoke), not publishing the operator’s full `workstation/` tree and handoff prose.

**Why:** Full trees are clunky and high-risk; progressive disclosure matches harness culture; telemetry must be opt-in.

**Consequence:** Stage 1b excludes the full workstation. A later stage ships security-gated demo/onboarding surfaces.

---

## Personal skills stay local; templates may be public

**Decision:** Personal methodology packs (e.g. writing style, private process routers) stay gitignored. Public MainFrame may ship **empty templates** that teach structure without a private voice pack.

**Why:** Voice and career process are not reusable OS core and often contain identity-specific guidance.

**Consequence:** Root `.agents/skills/` holds OS-wide skills; project-specific skills belong under that project’s tree.

---

## Deterministic minions vs judgment agents

**Decision:** File routing and mechanical checks prefer scripts (`bin/*`); judgment enrichment uses skills and subagents.

**Why:** Reliability for boring steps; models for ambiguous ones.

**Consequence:** Ingest minion stays dry-run by default; promotion paths remain explicit.
