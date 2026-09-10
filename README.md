# MainFrame

MainFrame is a local-first, Markdown-centered operating environment for agent-assisted knowledge work. It separates capture, durable knowledge, volatile state, bounded projects, standing operations, and archive so each can have different update and authority rules.

This repository is a **reference implementation**. It contains portable contracts, deterministic control surfaces, synthetic examples, and a bounded self-evaluation engine. It does not contain private knowledge, live state, project evidence, or evaluation history.

## Run the public core

```bash
git clone https://github.com/camerontjs-dot/MainFrame.git
cd MainFrame

./bin/process-eval status --json
uvx --with pytest pytest tests 40_operations/mainframe-process-eval/tests -q
```

The test surface exercises lifecycle identity, fail-closed duplicate and missing authority behavior, session routing, the process-eval shim, and the bounded public MPE profile. `process-eval status` should resolve `40_operations/mainframe-process-eval` without requiring private evaluation output.

## Why it exists

Captures, durable notes, volatile status, bounded projects, and standing operations need different update rules. Mixing them in one pile makes recall and safe updates harder. MainFrame organizes work by **information lifecycle first, topic second**, with explicit authority and fail-closed tools around identity and publication.

## Architecture

```text
PRIVATE / USER MAINFRAME                 PUBLIC MAINFRAME
living knowledge + evidence              portable architecture
projects, operations, runtime            contracts, engines, tests
        |                                         ^
        | positive fresh-tree publication         |
        +-----------------------------------------+
```

The public tree is cut from a private working tree through a positive allowlist into a fresh directory before publication. Private Git history does not cross that boundary.

## Lifecycle model

| Path | Purpose |
| --- | --- |
| `00_inbox/` | Fast capture |
| `01_ingest/` | Normalization and routing |
| `10_knowledge/` | Durable knowledge |
| `20_live/` | Volatile-state interfaces and templates, not someone else's live state |
| `30_projects/` | Bounded outcome work |
| `40_operations/` | Standing systems and recurring programs |
| `90_archive/` | Retired or preserved material |

Lifecycle zones may carry local `AGENTS.md` contracts that refine root policy. Location does not itself decide WIP, focus, health, or approval. Direct file authority outranks indexes and retrieval.

## Projects vs operations

Slugs are unique across `30_projects/` and `40_operations/`. A project is a bounded outcome. An operation is a standing loop. Duplicate slugs and missing README authority fail closed.

The implementation and tests are in `scripts/lifecycle_identity.py` and `tests/test_lifecycle_identity.py`.

## MainFrame Process Evaluation

The portable evaluation engine lives at `40_operations/mainframe-process-eval/`. Generic lifecycle substrate stays at the repository root; evaluation evidence stays local.

The public profile includes:

- operation identity and status;
- process-evaluation methodology;
- the real loop-evaluation scorer;
- labelled synthetic evaluation cases;
- a bounded `close --write` path whose output remains local-only.

Malformed synthetic catalogue input fails closed. The installed private MainFrame uses a larger `process-eval preflight` pack with additional operational tools. That full pack is not claimed as publicly reproducible here.

## Agent and runtime integration

Agents read contracts from `AGENTS.md`, `.context/workflows/`, and `.agents/skills/`. `bin/session-open` lists context; it does not establish that an agent understood it. Client-specific runtimes are optional.

## Authority boundaries

- Direct README and contract files are authority.
- Retrieval nominates evidence; it does not establish truth or lifecycle state.
- Deterministic tools prefer `--check` or dry-run behavior and fail closed on missing identity, duplicate slugs, or broken inputs.
- Publication uses a positive allowlist. A newly tracked private file does not become public by default.

## MindGraph retrieval

MindGraph is an optional public component and is not included in this first vNext core. When the retrieval engine is present, returned chunks are nominations. Inspect the underlying note before treating a result as true.

## Evidence in this tree

The public tests and synthetic fixtures are meant to be inspected, not just counted:

- `tests/test_lifecycle_identity.py` exercises project/operation identity and failure cases.
- `tests/test_public_mpe_synthetic.py` exercises the bounded public evaluation profile.
- `40_operations/mainframe-process-eval/tests/test_process_eval.py` exercises operation-owned evaluator behavior.
- `tests/test_session_open.py` and `tests/test_session_open_routes.py` exercise session context and routing behavior.
- `examples/demo-mainframe/` provides synthetic project, operation, and evaluation fixtures.

The public branch is also exercised in GitHub Actions using the same public-core test and CLI surfaces.

## What is deliberately not included

- Private knowledge bases, inbox contents, and archives
- Live focus, handoff, or telemetry state
- Private project contents
- Workstation UI
- Real evaluation outputs, transcripts, and baselines
- Private Git history
- The private-to-public exporter itself

## Limitations

- This is not an autonomous agent framework or enterprise orchestrator.
- Full process-eval `preflight` talks to adjacent MainFrame tools; some steps are machine-bound and are outside the bounded public profile.
- MindGraph, Workstation, and many operator CLIs are not in this first vNext core.
- `session-open` intentionally fails closed when local `STATE.md` authority is absent.
- No claim is made that a private MainFrame is healthy or that Git contains evaluation history.

## Publication boundary

The public repository keeps its own Git history. A private exporter builds a fresh candidate from an exact private source identity, a positive manifest, and curated public variants. Publication remains a deliberate PR into this repository rather than a mirror or history copy.
