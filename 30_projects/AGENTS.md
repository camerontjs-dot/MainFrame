# 30_projects - Project Lifecycle Rules

This directory contains active work with concrete outcomes. Keep project status machine-readable so agents can update navigation without hand-editing index files.

## Project States
- `active`: Work is moving and has a next action.
- `blocked`: Work is paused on an external dependency or unresolved decision.
- `shipped`: The outcome is complete enough to preserve, but may still receive maintenance.
- `trashed`: The project should leave active navigation and move to `90_archive/`.

## Required README Metadata
Each project folder must have a `README.md` with YAML frontmatter:

```yaml
---
title: "Project name"
domain: "Broad area"
type: "project"
status: "active"
project_state: "active"
goal: "Outcome this project is meant to produce"
next_action: "Single next step"
updated: "YYYY-MM-DD"
source: "local"
tags: []
---
```

## Agent Protocol
1. Create projects with the `create-project` workflow.
2. Update a project's `README.md`, `log.md`, and `decisions.md` rather than copying status into multiple places.
3. Regenerate `30_projects/index.md` with `bin/sync-project-index --write`; do not hand-edit it.
4. When archiving, use the `archive-project` workflow so knowledge extraction and status cleanup happen first.
5. Preserve project history. Move or append; do not silently overwrite logs or decisions.
