---
title: "Create Thread Workflow"
domain: "agents"
type: "workflow"
status: "active"
source: "ADR-038 and existing prompt/session contracts"
tags: ["threads", "handoff", "prompting"]
updated: "2026-06-28"
structural_type: "workflow"
lifecycle_scope: "root"
owner_surface: ".context/workflows/"
authority: "workflow-contract"
privacy: "public-safe"
volatility: "stable"
source_of_truth: true
update_rule: "replace-with-review"
verification: ["confirm referenced skill and workflows exist"]
related_surfaces: [".agents/skills/prompt-creation/SKILL.md", ".context/workflows/session-open.md", ".context/workflows/session-close.md"]
do_not_use_for: ["project status", "one-off implementation plans", "prompt-engineering guidance"]
---

# Create Thread Workflow

Use this workflow only when the user explicitly asks for a separate thread.

1. Load the minimum current context using `session-open` conventions and the
   task's authoritative project files. For `30_projects/` planning, preserve
   the required dual MindGraph query groups.
2. Use [prompt-creation](../../.agents/skills/prompt-creation/SKILL.md) to design
   the seed prompt. Point to source files instead of copying large documents.
3. Include the task objective, mode when requested (for example `/plan`),
   boundaries, expected first response, and completion or approval gate.
4. Create the thread in the correct project with the available thread tool,
   then give it a clear title and return the created-thread reference.

Do not copy secrets, raw transcripts, or unverified status into the prompt. A
plan-shaped handoff is context, not implementation approval.

Related workflows: [session-open](session-open.md) and
[session-close](session-close.md).
