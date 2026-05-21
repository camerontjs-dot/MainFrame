# 20_live - Local Rules

> [!WARNING]
> This folder contains volatile, changing information (e.g., finance, job hunt status).

## Defensive Constraints:
1. **Never Silently Overwrite History:** When updating a state dashboard, either use the gbrain "Timeline" pattern (append-only log below the line) or create explicit snapshots.
2. **Timestamp Everything:** Any claim of current state must include an `as_of` or `updated` date.
3. **Verify Before Promotion:** High-risk domain data (finance) must be verified against source documents before updating the "Compiled Truth".
