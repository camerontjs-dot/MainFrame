# MainFrame — Global Operating Contract

## System purpose

MainFrame organizes knowledge by **information lifecycle** first, and topic second. Goals: accurate recall, low-friction capture, and safe updates.

## Architecture

- `00_inbox/` — Fast capture zone
- `01_ingest/` — Normalization and routing
- `10_knowledge/` — Durable, slower-moving knowledge
- `20_live/` — Volatile operational state (dashboards, research in progress)
- `30_projects/` — Active work with outcomes
- `90_archive/` — Preserved material off the active path

## Agent behavior

1. **Harness contract.** Read `HARNESS.md` for execution environment rules, verification, and local vs cloud boundaries.
2. **Retrieval (when installed).** If MindGraph is present, query durable knowledge and project context as **separate** result groups with trust labels. Do not blend them into one unlabelled answer. MindGraph nominates context; it does not verify claims.
3. **Centralized skills and workflows.** Use `.context/workflows/` for operator sequences and `.agents/skills/` for reusable agent judgment.
4. **Subagents.** Named roles live in `agents/` (for example `agents/ingest-agent.md`).
5. **Local constraints.** Respect local `AGENTS.md` files in lifecycle folders — they override for sensitive or volatile data.
6. **Immutability.** Do not silently overwrite history. Live state uses snapshots or append-only timelines.
7. **Provenance.** Raw sources are evidence. Extracted text is a searchable working copy, not the source of truth.

## Structural file discipline

- Put stable always-on rules in `AGENTS.md`.
- Put long operator sequences in `.context/workflows/`.
- Put repeated agent judgment in `.agents/skills/`.
- Put specialized roles in `agents/`.
- Put deterministic enforcement in `bin/`, scripts, hooks, config, or tests.
- Keep volatile status in local `STATE.md`, `20_live/`, or project `README.md` / `log.md` (usually gitignored).
- Record framework architecture changes in public architecture notes; project-only tradeoffs stay in the project.

## Metadata and claims

- Finalized notes use the schema in `.context/primitives.md`.
- Follow `EPISTEMIC_STANCE.md` and `.context/workflows/epistemic-standard.md` for claim-bearing work: classify claims, check evidence tier, assign confidence, surface counterevidence.
