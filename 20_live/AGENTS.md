# 20_live - Local Rules

> [!WARNING]
> This folder contains volatile, changing information (e.g., finance, income engine / opportunity pipeline status).

## Defensive Constraints:
1. **Never Silently Overwrite History:** When updating a state dashboard, either use an append-only Timeline pattern (new entry below the line, oldest preserved) or create explicit dated snapshots.
2. **Timestamp Everything:** Any claim of current state must include an `as_of` or `updated` date.
3. **Verify Before Promotion:** High-risk domain data (finance) must be verified against source documents before updating the "Compiled Truth".
4. **Retention classes (ADR-045):** Follow `.context/live-retention.md`. Do not bulk-index this folder into MindGraph. Treat derived projections as rebuildable; append-only evidence as archive-capable; high-volume ops as capped, never knowledge.
5. **Projects index apply:** Use `bin/mindgraph-projects-apply` (plan → stage → promote). Do not “clean” live state by wiping evidence to make an index look healthy.
