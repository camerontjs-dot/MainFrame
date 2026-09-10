# MainFrame

A local-first, Markdown-centered operating environment for agent-assisted
knowledge work. It gives files explicit lifecycle boundaries, deterministic
control surfaces, retrieval nominations, project/operation identity, and a
portable self-evaluation engine.

This repository is a **reference implementation**. It is not a backup of any
one person's installed MainFrame, and it does not contain private knowledge,
live state, project evidence, or evaluation receipts.

## Why it exists

Captures, durable notes, volatile status, bounded projects, and standing
operations need different update rules. Mixing them in one pile makes recall
and safe updates harder. MainFrame organizes work by **information lifecycle
first, topic second**, with fail-closed tools around identity and publication.

## Architecture

```text
PRIVATE / USER MAINFRAME                 PUBLIC MAINFRAME
living knowledge + evidence              portable architecture
projects, operations, runtime            contracts, engines, tests
        |                                         ^
        | positive fresh-tree publication         |
        +-----------------------------------------+
```

The public tree is produced from a private working repository through a
deterministic allowlist. Private Git history does not cross that boundary.

## Lifecycle model

| Path | Purpose |
| --- | --- |
| `00_inbox/` | Fast capture |
| `01_ingest/` | Normalization and routing |
| `10_knowledge/` | Durable knowledge |
| `20_live/` | Volatile-state **interfaces and templates**, not someone else's live state |
| `30_projects/` | Bounded outcome work |
| `40_operations/` | Standing systems and recurring programs |
| `90_archive/` | Retired or preserved material |

Lifecycle zones may carry local `AGENTS.md` contracts that refine root
policy. Location does not itself decide WIP, focus, health, or approval.
Direct file authority outranks indexes and retrieval.

## Quick demo (synthetic)

The tree under `examples/demo-mainframe/` is labelled synthetic. It is not a
claim that any private MainFrame passed an evaluation.

```bash
python3 -c "from pathlib import Path; import sys; sys.path.insert(0,'scripts'); from lifecycle_identity import resolve_record, DuplicateIdentity, MissingIdentity"
python3 bin/process-eval --help
python3 bin/process-eval status --json
```

`status` resolves the portable `mainframe-process-eval` operation in this
tree. Evaluation **outputs** are local-only and are not part of Git.

## Projects vs operations

Slugs are unique across `30_projects/` and `40_operations/`. A project is a
bounded outcome. An operation is a standing loop. Duplicate slugs and missing
README authority fail closed.

See `scripts/lifecycle_identity.py` and `tests/test_lifecycle_identity.py`.

## Agent / runtime integration

Agents read contracts from `AGENTS.md`, `.context/workflows/`, and
`.agents/skills/`. `bin/session-open` lists context; it does not prove that
an agent understood it. Client-specific runtimes are optional.

## Authority and fail-closed boundaries

- Direct README / contract files are authority.
- Retrieval nominates evidence; it does not establish truth or lifecycle state.
- Deterministic tools prefer `--check` / dry-run and fail closed on missing
  identity, duplicate slugs, or broken publication inputs.
- Publication uses a positive allowlist. A newly tracked private file does
  not become public by default.

## MindGraph retrieval

MindGraph is classified as an optional public component in this vNext slice.
The operating rule, when the engine is present: returned chunks are
nominations. Inspect the underlying note before treating a result as true.

## MainFrame Process Evaluation

The portable engine lives at `40_operations/mainframe-process-eval/`. Generic
lifecycle substrate stays at the repository root. Raw evaluation evidence
stays local. Public methodology, identity, and a bounded synthetic loop-eval
scoring path are included; private migration archaeology, outputs, receipts,
and traces are not.

The installed private MainFrame uses a larger `process-eval preflight` pack
involving additional optional operational tools. That full pack is not claimed
as publicly reproducible in this vNext slice.

## What is deliberately not included

- Private knowledge bases, inboxes, and archives
- Live focus/handoff/telemetry state
- Private project contents
- Workstation UI
- Real evaluation outputs, transcripts, and baselines
- Private Git history
- The private-to-public exporter itself (it stays on the private owner)

## Demonstrated properties

These are backed by inspectable tests in this tree:

- Lifecycle zones have explicit contracts
- Project and operation types share one identity namespace
- Duplicate identity fails closed
- Missing authority fails closed
- `bin/process-eval` is a shim over operation-owned code
- Publication candidates are exact allowlisted file sets
- Synthetic examples are labelled synthetic

## Limitations

- This is not an autonomous agent framework or enterprise orchestrator.
- Full process-eval **preflight** talks to adjacent MainFrame tools; some
  steps are machine-bound and will skip or fail closed without local setup.
- MindGraph, Workstation, and many operator CLIs are not in this first vNext
  candidate.
- No claim is made that a private MainFrame is healthy or that Git contains
  evaluation history.

## How this public tree is produced

A private exporter (`bin/public-export` on `camerontjs-dot/mainframe-live`)
builds a fresh directory from an exact private SHA, a positive manifest, and
named transforms. It never copies `.git`. Publication remains a human PR
onto public `camerontjs-dot/MainFrame`.

## Setup

```bash
git clone https://github.com/camerontjs-dot/MainFrame.git
python3 bin/process-eval --help
uvx --with pytest pytest tests/test_lifecycle_identity.py tests/test_process_eval_shim.py -q
```

There is no required cloud account. Local notes you add under lifecycle
directories stay yours.
