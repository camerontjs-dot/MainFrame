# Activation Language Reference

Source: `10_knowledge/software-practice/2026-06-11__software-practice__raw__instruction-design.md`

---

## What activation language is

The YAML `description` field in SKILL.md is the only surface the agent reads when deciding whether to
load a skill. It is not marketing copy. It is a routing table.

The field must do three jobs simultaneously:
1. Fire when the user's words match the skill's domain.
2. Stay silent when the user's words almost-but-don't-quite match.
3. Communicate scope to both the agent and any human who reads the file.

---

## Template

```yaml
---
name: your-skill-name
description: >
  Use when [primary use case summary in one phrase]. Triggers on: "[phrase 1]", "[phrase 2]",
  "[phrase 3]", "[phrase 4]", "[phrase 5]", "[phrase 6]", "[phrase 7]".
  Do NOT use for: [adjacent thing that could false-positive 1], [adjacent thing 2], [adjacent thing 3].
---
```

---

## Rules

### Volume
- List **5–7 explicit trigger phrases**. Fewer than 5 risks Silent failure. More than 7 risks Hijacker failure.
- Include the slightly-wrong phrasings users actually type ("make a skill" alongside "create a skill").
- Include synonyms from adjacent domains ("instruction doc" alongside "SKILL.md").

### Negative boundaries
- Every skill needs at least **one explicit "Do NOT use for" clause**.
- Name the closest adjacent skill or task that could confuse the router.
- Example: a `prompt-creation` skill should exclude "SKILL.md files" if a separate `skill-creation` skill handles those.

### Grammar / person
- Use **third-person, system-property phrasing**: "Generates proposals" not "I can help you with proposals."
- Use **imperative triggers** in the trigger list: "create a skill", "write a skill" (the form the user types).
- Keep the `description` as a single YAML block scalar (use `>` for multi-line).

### Scope signal
- The description should tell a competent reader what the skill does and doesn't do in under 60 words.
- If it takes more than 60 words to define the scope, the skill probably covers too much — consider splitting.

---

## Diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Skill never loads | Trigger phrases too narrow or absent | Add phrases, especially how users actually phrase requests |
| Skill loads on unrelated requests | No negative boundary, or too-broad phrase | Add "Do NOT use for" clause; narrow the generic phrase |
| Two skills compete on same request | Overlapping trigger sets | Deduplicate phrases; make negative boundaries mirror each other |
| Skill loads correctly but wrong skill wins | Agent uses first-match or highest-score | Move the more specific phrase first; add a tiebreaker negative boundary |
