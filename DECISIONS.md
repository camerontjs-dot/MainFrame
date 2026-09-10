# Architecture Decision Records (public subset)

This file is a **curated public extract**. It is produced by a named export
transform. It is not the complete private decision log and does not include
private project names, personal operations, or unpublished experiments.

## ADR-064: Public MainFrame Is A Fresh-Tree Product, Not A Git Mirror (2026-09-10)

**Status**: Accepted for the private→public publication boundary. This does
not authorize an unattended public push.

**Context**: Private `mainframe-live` history contains machine-path backlog.
`.gitignore` is a tracking policy, not a publication policy. The public
repository must not inherit private Git history.

**Decision**:

1. Public `camerontjs-dot/MainFrame` is a curated reference implementation.
2. Export uses a positive allowlist over a fresh tree (no `.git` copy).
3. Files that need redaction use named deterministic transforms. Transform
   failure blocks export; unsanitized private bytes are not a fallback.
4. Operation admission is not whole-tree Git admission and is not whole-tree
   public admission. MPE portable engine/methodology/tests may be public;
   MPE evidence remains local.
5. This does not generalize every future operation into the public tree.

**Verification**: the private exporter on `camerontjs-dot/mainframe-live`
(`bin/public-export`) plus candidate leak scan and clean-candidate tests.
Those exporter files stay private; they are not part of this public tree.

## ADR-063: Selectively Track Portable MPE Engine On Private mainframe-live (public summary)

Private `mainframe-live` allowlists portable MPE source under
`40_operations/mainframe-process-eval/`. Evidence stays local. There is no
standalone public MPE repository.

## ADR-062 / ADR-061 (public summary)

`40_operations/` is the lifecycle home for standing operations. MainFrame
Process Evaluation is an admitted operation. Lifecycle location does not
itself determine WIP, focus, health, or approval. Direct README authority
remains authoritative.

## ADR-056 (public summary)

Operations are distinct from projects. They share one slug namespace across
`30_projects/` and `40_operations/`. Duplicate identity fails closed.
