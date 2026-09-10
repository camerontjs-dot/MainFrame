# Happy Path Example — Prompt Creation

This file satisfies Component #5 (examples) for the `skill-creation` skill's own pre-ship checklist.

---

## Scenario

User says: "Write a prompt that gets Claude to review a pull request and flag any security issues."

---

## Step 1 — Name the job

> "This skill owns: designing a code-review prompt that targets security issues specifically."

One task category. No split needed.

---

## Step 2 — Map the six elements

| Element | Content |
|---------|---------|
| **Role** | A senior application security engineer with experience in OWASP Top 10 and secure code review |
| **Context** | A pull request diff will be provided. The reviewer is a developer, not a security specialist. |
| **Task** | Review the diff for security vulnerabilities; categorise each by OWASP Top 10 category if applicable |
| **Format** | Bulleted list of findings; each finding: file + line range, category, description, recommended fix |
| **Constraints** | Do NOT flag style or performance issues. Do NOT praise the code. Do NOT include findings with no concrete fix. |
| **Quality standard** | Every finding must be actionable: a developer should be able to implement the fix without follow-up questions |

---

## Step 3 — Draft (XML-tagged, ≥ 3 separable components)

```xml
<role>
You are a senior application security engineer. You specialise in secure code review and OWASP Top 10 vulnerabilities.
</role>

<context>
The reader is a developer, not a security specialist. Write findings so they are understandable without prior security training.
</context>

<task>
Review the pull request diff below for security vulnerabilities only. For each finding, identify the OWASP Top 10 category if applicable.
</task>

<constraints>
- Do NOT flag style or performance issues.
- Do NOT include praise or commentary on code quality.
- Do NOT include a finding unless you can state a concrete fix.
</constraints>

<output_format>
For each finding, output:
- File and line range
- OWASP category (or "Other" if none applies)
- Description: what the vulnerability is and why it matters
- Fix: the specific change to make

If no security issues are found, output: "No security vulnerabilities found in this diff."
</output_format>

[PASTE DIFF HERE]
```

---

## Step 4 — Element annotation

- **Role:** Named expertise area + specific knowledge domain (OWASP Top 10). Not "a helpful assistant."
- **Context:** States the reader's background so the model calibrates explanation depth.
- **Task:** "Security vulnerabilities only" scopes the task. "OWASP Top 10 category" gives a classification target.
- **Format:** Each finding's structure is explicit; no guessing required. The "no findings" fallback prevents empty output.
- **Constraints:** Three negative rules covering the most common Overachiever failures for code review prompts (style comments, praise, vague warnings).
- **Quality standard:** Embedded in output_format ("concrete fix") and constraints ("a developer should be able to implement without follow-up").

---

## Step 5 — Watch for

Most likely failure: the model includes style or complexity comments alongside security findings. If that happens, the constraint list needs to be more specific: name the specific non-security categories to exclude.

---

## Edge case

**If the diff is too long:** the prompt needs a `<scope>` block specifying which files to prioritise. Add: `<scope>Focus on authentication, authorization, and data handling code first. If the diff exceeds 500 lines, review in sections and note any sections skipped.</scope>`
