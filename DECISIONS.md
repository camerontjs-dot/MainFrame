# Architecture Decision Records (ADRs)

This file captures meaningful project choices, especially trade-offs affecting reproducibility, scope, evidence quality, or system behavior.

## ADR-001: Centralized vs Local Agent Instructions
**Status**: Accepted
**Date**: 2026-05-20
**Context**: Should each lifecycle folder contain its own `AGENTS.md` file, or should all instructions be centralized?
**Decision**: We will enforce a global `AGENTS.md` at the root, and keep repeatable workflows in `skills/`. We will ONLY place local `AGENTS.md` files in subdirectories that have special defensive rules or processes (e.g. `20_live`).
**Rationale**: Prevents agent context bloat and repetitive instructions while still allowing for localized safety rules.

## ADR-002: MindGraph Integration Strategy
**Status**: Accepted
**Date**: 2026-05-20
**Context**: Should the MindGraph GraphRAG system be deeply coupled into the Second Brain ingest pipeline?
**Decision**: MindGraph will remain a separate project and will be wired in as a complementary RAG feature. The Second Brain will have its own ingest pipeline, but will use the same tracking/metadata schema so MindGraph can index it effectively.
**Rationale**: Keeps the Second Brain ingestion simple and markdown-first, separating the graph database concerns from the file organization concerns.

## ADR-003: Automation Tooling for Ingest
**Status**: Accepted (Deferred)
**Date**: 2026-05-20
**Context**: The `01_ingest` pipeline requires metadata validation and graph extraction. Relying entirely on LLMs for this is token-heavy.
**Decision**: We will plan to create lightweight CLI/bash scripts ("Minions") in a future session to handle deterministic routing.
**Rationale**: Saves tokens and increases reliability for repetitive, rule-based operations.
