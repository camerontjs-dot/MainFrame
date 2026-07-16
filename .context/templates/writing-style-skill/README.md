# Template: personal writing-style skill

**Status:** scaffold only (Phase 1b) — fill when you build your own voice pack
**Public intent:** ship this template with MainFrame; never ship a filled personal pack as the default skill.

## What this is

A copy-local recipe for a **router skill** plus genre reference pages. Operators clone the structure into a local-only skill path and fill it with their own standards.

## Install (local only)

```bash
# From MainFrame root — creates an ignored personal skill (do not commit)
mkdir -p .agents/skills/writing-style/references
cp .context/templates/writing-style-skill/SKILL.template.md \
  .agents/skills/writing-style/SKILL.md
cp .context/templates/writing-style-skill/references/*.template.md \
  .agents/skills/writing-style/references/
# Rename *.template.md → short names matching SKILL.md load order
```

Ensure `.agents/skills/writing-style/` stays in `.gitignore` (MainFrame default).

## Structure

| File | Role |
| --- | --- |
| `SKILL.template.md` | Frontmatter + load order + workflow (no personal voice) |
| `references/shared-natural-voice.template.md` | Always-on craft principles |
| `references/portfolio.template.md` | Public technical / portfolio prose |
| `references/content.template.md` | Posts, newsletters, comments |
| `references/career.template.md` | Applications, outreach (name the lane you use) |
| `references/technical-professional.template.md` | Internal / professional docs |
| `references/persuasive-craft.template.md` | Asks, proposals, decisions |
| `references/humour-rhythm.template.md` | Optional rhythm / tone pass |

Add or drop reference pages to match your surfaces. Keep the router thin; put length in references.

## Design rules

1. **Positive craft first** — anti-patterns only as a final lint.
2. **Truth before style** — no invented metrics, status, or credentials.
3. **Load the smallest set** of references per task.
4. **Project-specific voice packs** for one client or one private project belong under that project (e.g. `30_projects/<slug>/skills/`), not in root `.agents/skills/`.

## Deferred

- Example filled pages (synthetic, not a real person's voice)
- Optional eval harness hooks (`eval_writing_style`-style) as a separate template
