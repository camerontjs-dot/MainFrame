---
name: skill-creation
description: >
  Use when designing, writing, auditing, or improving a SKILL.md file or any agent instruction
  document in this workspace. Triggers on: "create a skill", "write a skill", "add a skill",
  "audit this skill", "audit a skill", "make a new skill", "design an instruction doc".
  Do NOT use for one-off task prompts or system prompts for LLMs (use prompt-creation), for
  AGENTS.md or HARNESS.md system contracts, or for workflow files in .context/workflows/.
---

# Skill Creation

## Purpose

Produce a well-structured, reliable SKILL.md (or any agent instruction document) that activates at
the right time, produces consistent output, and fails gracefully at its edges.

A skill is a training manual for an agent-employee. The failure modes are identical across SKILL.md,
AGENTS.md, CLAUDE.md, and `prompts/*.md`. Learn to diagnose by mode; the fix becomes obvious.

## Load Order

Always read `references/anatomy.md` first — it contains the five-component checklist, five failure
modes, the pre-ship testing protocol, and the thin-router pattern.

Then load only the references needed:

- `references/anatomy.md`: required for every skill-creation task
- `references/activation-language.md`: load when writing or auditing the YAML `description` block

## Workflow

### Writing a new skill

1. **Name the job** — Write one sentence: "This skill owns [single task category]." If it covers more than one independently-triggerable category, split into two skills before drafting.
2. **Load references** — Load `references/anatomy.md` and `references/activation-language.md`.
3. **Draft the YAML block** — `name` (kebab-case), `description` using the template in `references/activation-language.md`: 5–7 explicit trigger phrases + at least one "Do NOT use for" clause, third-person phrasing, description text under 60 words.
4. **Write the body** — Five components in order: (1) Purpose — one paragraph written for the agent; (2) Load Order — only if external references exist, otherwise omit the section entirely; (3) Workflow — numbered imperative steps, no vague verbs; (4) Output Format — structure + explicit "Do NOT add" list; (5) Examples and edge cases — at least one happy path, at least one `If [condition], then [action]` rule.
5. **Apply the thin-router test** — If the body exceeds ~150 lines, move workflow content to `references/workflow.md` and replace with a single pointer line.
6. **Run the five-test protocol** from `references/anatomy.md`: happy path, minimal input, edge case, negative test, repeat test.
7. **Check every item** on the pre-ship checklist in `references/anatomy.md`.

### Auditing an existing skill

1. **Read the skill in full** before writing anything.
2. **Score each of the five components** as present / weak / missing.
3. **Run the five failure-mode diagnosis** — for each failure mode, state whether the skill has symptoms and what the fix is.
4. **Run the five-test protocol** mentally against the skill's current text.
5. **List findings** as: component, failure mode, specific line, replacement text.
6. **Apply fixes** one at a time. Re-check the affected component after each fix.

## Output Format

Deliver:
1. The complete SKILL.md as a ready-to-copy file block (for new skills), or the changed lines with exact replacement text (for audits).
2. A checklist showing each pre-ship item as pass / fail / note.
3. For any fail item: the specific line and the exact replacement text.

Do NOT add: preamble explaining skill design theory, hedging disclaimers, sections not in the five-component structure, or alternative versions unless asked.

## Examples and Edge Cases

**Happy path:** See `examples/happy-path.md` for a complete worked example of writing a new skill from a user request through to a shipped SKILL.md with checklist.

**If the user provides only a skill name with no description:** ask for (1) the single task category in one sentence, (2) three example user phrasings that should trigger it, (3) one request that should NOT trigger it. Do not draft until all three are answered.

**If the user asks to audit a skill but no task context is given:** follow the Auditing workflow above. Do not ask for the intended output — diagnose from the existing text using the five-component and five-failure-mode frameworks.

**If the requested skill overlaps with an existing skill:** name the overlapping trigger phrases, state which "Do NOT use for" clause would prevent collision, and confirm with the user before writing.

**If the skill body grows past ~150 lines during drafting:** stop. Move workflow content to `references/workflow.md`. Replace with: "Follow the workflow in `references/workflow.md`." Note this in your checklist output.

**If the skill needs no external references:** omit the Load Order section entirely. Do not include it with an empty list.

## Boundaries

This skill governs SKILL.md files and agent instruction documents only.

Do NOT use it for:
- One-off task prompts or system prompts for LLMs → use `prompt-creation`
- Editing `AGENTS.md`, `HARNESS.md`, or `.context/workflows/` files
- Auditing or editing code files
