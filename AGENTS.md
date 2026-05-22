# Mainframe - Global Operating Contract

## System Purpose
This system organizes knowledge by its **information lifecycle** first, and topic second. The goal is accurate recall, low-friction capture, and safe updates.

## Architecture
- `00_inbox/`: Fast capture zone.
- `01_ingest/`: Normalization and routing.
- `10_knowledge/`: Durable, slower-moving knowledge.
- `20_live/`: Volatile state (finance, job hunt, active research).
- `30_projects/`: Active work with outcomes.
- `90_archive/`: Preserved material without cluttering active navigation.

## Agent Behavior
1. **Centralized Skills:** Use `.context/workflows` or `/skills` for repeatable tasks rather than duplicating instructions.
2. **Local Constraints:** Respect local `AGENTS.md` files in subdirectories—they contain overriding rules for sensitive or volatile data.
3. **Immutability:** Do not silently overwrite history. If a file is in `20_live`, use snapshots or append-only timelines.
4. **Provenance:** Preserve raw sources as evidence. Extracted text is a searchable working copy, not the source of truth.

## Metadata & Updating
- Every finalized note must contain the standard metadata schema defined in `.context/primitives.md`.
- Ensure changes to architecture or workflow are recorded in `DECISIONS.md`.
- Adhere to the epistemic stance defined in `EPISTEMIC_STANCE.md` when recording claims.
