---
name: print-ready-pdf-generation
description: Create, repair, and verify polished print-ready PDFs from Markdown or HTML for agent-generated deliverables. Use when Codex needs to regenerate an attachment, fix Chrome/Puppeteer/Playwright PDF layout issues, handle md-to-pdf hangs, prevent header/footer overlap, stop clipped tables or overflowing text, or leave a reusable PDF generation path for future agents.
---

# Print-Ready PDF Generation

## Overview

Use this skill to turn Markdown or HTML into a visually checked PDF that is safe to send as an attachment. Prefer a deterministic render script plus PNG inspection over one-off browser printing.

## Workflow

1. Find the source file. Do not edit the generated PDF directly unless the user specifically asks for binary PDF manipulation.
2. Inspect any existing generator notes, CSS, config, and prior PDF output.
3. Render the current PDF to PNG with Poppler and inspect at least the first page, every page with a table, and the last page.
4. Fix the source, CSS, or config. Common fixes:
   - Remove CSS `@page margin: 0` when Chrome header/footer templates are enabled; let the PDF margin options reserve header/footer space.
   - Keep body padding small when PDF margins are already set.
   - Use `table-layout: fixed`, `overflow-wrap: anywhere`, and normal white-space for narrative table cells.
   - Avoid global `td:nth-child(...) { white-space: nowrap; }` rules unless the table really contains short numeric values.
   - Increase top/bottom PDF margins when header or footer content overlaps body text.
5. Regenerate the PDF with `scripts/render-markdown-pdf.mjs`.
6. Render the new PDF to PNG and inspect visually before delivery. Text extraction is useful for smoke checks, but it is not layout verification.

## Script

Run from the workspace root or the source file directory:

```bash
node .agents/skills/print-ready-pdf-generation/scripts/render-markdown-pdf.mjs \
  path/to/source.md \
  path/to/output.pdf \
  --config path/to/pdf-config.js
```

The script:

- strips YAML frontmatter from Markdown;
- converts Markdown with `marked`;
- inlines CSS from `pdf-config.js` and optional `--css` flags;
- renders with Playwright/Chromium, preferring system Chrome when bundled Playwright browsers are absent;
- supports `--keep-html` for debugging and `--fail-on-overflow` for obvious screen-layout overflow checks.

## Verification Commands

```bash
pdfinfo path/to/output.pdf
pdftoppm -png -r 150 path/to/output.pdf /tmp/pdf-check/page
pdftotext -layout path/to/output.pdf -
```

Use `view_image` on the rendered PNGs when available. Check for:

- header/body and footer/body overlap;
- clipped tables or text running outside margins;
- awkward page starts where a heading is separated from its first paragraph;
- unreadable fonts, broken glyphs, or placeholder/source tokens;
- correct page count and intended output path.

## Output Discipline

Keep final artifacts where the project rules say they belong: source notes and generation assets stay with the project, while generated phone-uploadable PDFs go to the configured output vault.
