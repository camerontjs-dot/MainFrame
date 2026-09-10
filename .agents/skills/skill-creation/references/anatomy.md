# Five Components, Five Failure Modes, and the Pre-Ship Checklist

**Authoritative synthesis:** `10_knowledge/agents/prompts/2026-06-21__agents__note__agent-instruction-design-principles.md`
Source claims below are attributed in that note with confidence labels, counterevidence, and operational examples from the Tripwire harness eval. Read the synthesis note before modifying any claim here.

---

## The five components every instruction document needs

| # | Component | In a SKILL.md | Why it matters |
|---|-----------|---------------|----------------|
| 1 | **Trigger / activation** | YAML `description` with 5–7 explicit trigger phrases + "Do NOT use for…" | Agent won't activate without the right phrases; too-broad phrases hijack unrelated tasks |
| 2 | **Overview** | One paragraph written for the agent, not the human | Sets frame and vocabulary before any rules are read |
| 3 | **Step-by-step workflow** | Numbered imperative steps | Removes ambiguity; "handle appropriately" is a Drifter waiting to happen |
| 4 | **Output format** | Exact structure, length, tone, forbidden phrases | Without it, the agent guesses — and guesses vary |
| 5 | **Examples + edge cases** | ≥ 1 happy path + ≥ 1 edge-case rule | The most commonly skipped component; the most common cause of fragile behavior |

Skip any one → unreliable output. The gap in most shipped docs is **#5**.

---

## The five failure modes

### Failure 1 — Silent (never activates)
**Symptom:** skill should govern the interaction; agent ignores it.
**Diagnosis:** activation language too weak; doesn't contain the words the user typed.
**Fix:** add more trigger phrases, synonyms, and the slightly-wrong phrasings users actually type.

### Failure 2 — Hijacker (fires on wrong requests)
**Symptom:** skill activates on unrelated tasks.
**Diagnosis:** activation language too broad, or missing negative boundaries.
**Fix:** add explicit "Do NOT use for [X, Y, Z]" clauses. Tighten generic phrases.

### Failure 3 — Drifter (right doc, inconsistent output)
**Symptom:** skill activates correctly but output varies run-to-run.
**Diagnosis:** vague, non-testable instructions. "Handle appropriately." "Format nicely."
**Fix:** replace every vague rule with a specific, testable one. Leave zero room for interpretation.

### Failure 4 — Fragile (works on clean input, breaks on edge cases)
**Symptom:** normal inputs succeed; unusual inputs collapse silently.
**Diagnosis:** edge cases not enumerated.
**Fix:** feed the doc the worst inputs imaginable. For each failure, add: `If [condition], then [specific action].`

### Failure 5 — Overachiever (adds things not asked for)
**Symptom:** output carries unsolicited commentary, extra sections, creative additions.
**Diagnosis:** doc says what TO do, but not what NOT to do.
**Fix:** add explicit scope constraints. "Output ONLY the specified format. Do NOT add [list of forbidden extras]."

---

## Three activation-language rules

1. **Be pushy.** List 5–7 explicit trigger phrases. Include synonyms. Include the slightly-wrong phrasings users actually type.
2. **Include negative boundaries.** "Do NOT use for [similar-but-different thing]." Prevents hijacking.
3. **Write in third person.** "Generates proposals" beats "I can help you with proposals." Agent instruction parsers handle third-person system-property phrasing more reliably.

---

## The five-test protocol

Run every instruction doc through these before shipping:

| Test | Input | Pass condition |
|------|-------|----------------|
| **Happy path** | Clean input, complete context | Expected output, no extra content |
| **Minimal input** | Absolute least information a user might provide | Asks for what it needs, doesn't invent |
| **Edge case** | Unusual, contradictory, typo-laden input | Handles explicitly, not silently mis-handles |
| **Negative test** | A request that should NOT trigger the skill | Agent correctly routes elsewhere |
| **Repeat test** | Same input, three runs | Output consistent across all three |

Inconsistency on the repeat test = ambiguous instructions. Find the vague phrase and replace it.

---

## Pre-ship checklist

- [ ] Activation language lists 5–7 explicit trigger phrases
- [ ] Activation language includes at least one negative boundary ("Do NOT use for X")
- [ ] Activation language is third-person / system-property phrasing
- [ ] Overview paragraph speaks to the agent, not the human reader
- [ ] Workflow steps are numbered, imperative, testable
- [ ] Every vague phrase has been replaced ("handle appropriately" → specific rule)
- [ ] Output format is explicit — structure, length, tone, forbidden phrases
- [ ] At least one happy-path example exists (or is referenced from a `references/` or `examples/` file)
- [ ] At least one edge case is enumerated ("If X, then Y")
- [ ] A "what this skill does NOT do" section exists with explicit scope exclusions
- [ ] The doc passed the five-test protocol (happy, minimal, edge, negative, repeat)

---

## Thin-router pattern

A SKILL.md should contain only:
1. YAML trigger block (5–7 explicit phrases + negative boundaries).
2. One-paragraph overview.
3. A one-line pointer: "Follow the workflow in `<path to the real prompt file>`."

When to use it: if the workflow body exceeds ~150 lines, move it to a `references/` file and point to it from SKILL.md.

**Why:** Non-Claude agents don't read `.claude/skills/`. If the workflow body lives only in the skill, portability breaks. Three places to drift (skill body + prompt body + AGENTS.md routing) = eventual contradiction.
