#!/usr/bin/env python3
"""
Stub for unifying client hook configs (Claude, Codex, Antigravity, Aider watcher).

Part of Fix 5 (client config fragmentation).

In a full impl, this would read a single source (e.g. .context/client-hooks.json or yaml)
and emit the per-client files:
  .claude/settings.json (or hooks section)
  .codex/hooks.json
  .antigravity/hooks.json
  etc.

For now: a thin generator stub that documents the pattern and can be expanded.
Run with --dry-run to preview; --apply to write (respecting local overrides).

This keeps the public surface clean while reducing duplication of hook wiring
(bin/workflow-event calls remain the single backend).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_source() -> dict:
    # Placeholder: in real version load from .context/client-hooks-source.json
    # or derive from the existing settings we maintain in .claude/ etc.
    # For demo, hardcode a minimal unified view. Use a shell-safe template that
    # the real hook files expand with their ${VAR} prefixes.
    return {
        "events": [
            "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
            "PostToolUseFailure", "Stop", "SubagentStart", "SubagentStop",
            "PermissionRequest", "PreCompact", "PostCompact"
        ],
        # MAINFRAME_ROOT / client project-dir env only — never hard-code a personal Desktop path.
        "command_template": "${MAINFRAME_ROOT:-${CLAUDE_PROJECT_DIR}}/bin/workflow-event --client {client}",
        "timeout": 5,
    }


def generate_for_client(client: str, source: dict) -> dict:
    # Very simplified emitter. Real version would match the exact layout of
    # .claude/settings.json hooks, .codex/hooks.json, etc.
    cmd = source["command_template"].format(client=client)
    hooks = {}
    for ev in source["events"]:
        hooks[ev] = [{"type": "command", "command": cmd, "timeout": source["timeout"]}]
    return {"hooks": hooks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--client", choices=["claude", "codex", "antigravity"], default="claude")
    parser.add_argument("--pixel", default=None, help="Unique pixel/agent ID for trackable hooks in the local agents pixel agent tracker (e.g. main-claude-pixel)")
    args = parser.parse_args()

    source = load_source()
    cfg = generate_for_client(args.client, source)

    # Inject pixel into all hook commands for unique tracking (like web_panel/human clients)
    if args.pixel:
        pixel_arg = f" --pixel {args.pixel}"
        for event_hooks in cfg.get("hooks", {}).values():
            for h in event_hooks:
                for hook in h.get("hooks", []):
                    if "command" in hook:
                        hook["command"] += pixel_arg

    if args.dry_run:
        print(json.dumps(cfg, indent=2))
        return 0

    if args.apply:
        # In real: write to the correct dotfile location for the client.
        # e.g. for claude: (ROOT / ".claude" / "settings.json") but preserve other keys.
        print(f"Would write generated hooks for {args.client} with pixel={args.pixel} (stub).")
        print("Expand this script to do real merge/write while keeping manual local overrides.")
        return 0

    print("Use --dry-run or --apply --pixel ID. This is a stub for centralizing unique/trackable hook definitions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
