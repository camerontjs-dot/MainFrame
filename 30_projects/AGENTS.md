# Projects — Local Rules

`30_projects/` holds bounded outcome work. Project slugs share one namespace
with `40_operations/`. Duplicate slugs fail closed.

Each project README is direct authority for identity and lifecycle state.
Generated indexes and retrieval results do not replace it.

> **Binds:** agents creating or resuming a project
> **Tier:** T0 (advisory in the public reference implementation)
> **Check:** `tests/test_lifecycle_identity.py`
> **Escape:** if authority is missing, label the field unknown and stop rather than guessing

Do not copy another operator's project contents into this directory. Use
`30_projects/index.template.md` as the navigation template.
