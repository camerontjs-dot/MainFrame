"""Read/validate structured focus authority under 20_live/focus/ (MPE-024)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class FocusLoad:
    ok: bool
    path: Path | None
    data: dict[str, Any]
    errors: list[str]
    warnings: list[str]

    @property
    def primary_project(self) -> str | None:
        primary = self.data.get("primary")
        if isinstance(primary, dict):
            p = primary.get("project")
            return str(p).strip() if p else None
        return None

    @property
    def revision(self) -> str | None:
        r = self.data.get("revision") or self.data.get("decision_id")
        return str(r) if r else None

    @property
    def review_by(self) -> str | None:
        r = self.data.get("review_by")
        return str(r) if r else None


def _parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if s in ("null", "~", ""):
        return None
    if s in ("true", "false"):
        return s == "true"
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def parse_focus_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML subset parser for the focus schema (no PyYAML dependency)."""
    lines = text.splitlines()
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        # pop stack
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            item_raw = line[2:].strip()
            if not isinstance(parent, list):
                # parent should be list; if dict, error skip
                continue
            if ":" in item_raw and not item_raw.startswith("{"):
                # map entry in list
                key, _, val = item_raw.partition(":")
                key = key.strip()
                val = val.strip()
                item: dict[str, Any] = {}
                if val:
                    item[key] = _parse_scalar(val)
                else:
                    item[key] = {}
                    stack.append((indent, item[key] if item[key] == {} else item))
                parent.append(item)
                if not val:
                    # keep stack pointing at item for nested keys under list map
                    stack.pop()  # remove empty dict mistaken
                    stack.append((indent, item))
            else:
                parent.append(_parse_scalar(item_raw))
            continue

        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if not isinstance(parent, dict):
            continue
        if val == "":
            # peek next non-empty for list vs map
            j = i
            child: Any = {}
            while j < len(lines):
                peek = lines[j]
                if peek.strip() and not peek.lstrip().startswith("#"):
                    pindent = len(peek) - len(peek.lstrip(" "))
                    if pindent > indent and peek.lstrip().startswith("- "):
                        child = []
                    break
                j += 1
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(val)
    return root


def load_focus(root: Path) -> FocusLoad:
    focus_dir = root / "20_live" / "focus"
    errors: list[str] = []
    warnings: list[str] = []
    path = focus_dir / "current.yaml"
    if not path.exists():
        path = focus_dir / "current.json"
    if not path.exists():
        return FocusLoad(False, None, {}, ["structured focus authority missing"], [])

    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            import json

            data = json.loads(text)
        else:
            data = parse_focus_yaml(text)
    except Exception as exc:  # noqa: BLE001
        return FocusLoad(False, path, {}, [f"focus parse failed: {type(exc).__name__}"], [])

    if not isinstance(data, dict):
        return FocusLoad(False, path, {}, ["focus root must be a mapping"], [])

    for req in ("schema_version", "decision_id", "as_of", "review_by", "primary"):
        if req not in data:
            errors.append(f"missing field: {req}")

    primary = data.get("primary")
    if not isinstance(primary, dict) or not primary.get("project"):
        errors.append("primary.project required")
    else:
        project = str(primary["project"]).strip()
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", project):
            errors.append(f"primary.project invalid slug: {project!r}")
        readme = root / "30_projects" / project / "README.md"
        if not readme.exists():
            errors.append(f"primary.project path missing: 30_projects/{project}/README.md")

    # review window
    review_by = data.get("review_by")
    if isinstance(review_by, str) and review_by:
        try:
            # accept Z suffix
            rb = datetime.fromisoformat(review_by.replace("Z", "+00:00"))
            if rb.tzinfo is None:
                rb = rb.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > rb:
                warnings.append("focus review_by is past; authority is stale")
        except ValueError:
            errors.append("review_by not parseable as RFC3339")

    ok = not errors
    return FocusLoad(ok, path, data, errors, warnings)
