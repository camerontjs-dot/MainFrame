"""Direct lifecycle identity and cross-root record resolution.

MainFrame has two lifecycle roots whose records share one slug namespace.  This
module is deliberately small and dependency-free so command-line readers,
writers, inventory checks, and tests can use the same authority rules.

MindGraph, generated indexes, and Workstation projections may validate the
result returned here, but they are never used to choose a path.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
LIFECYCLE_ROOTS = {
    "project": "30_projects",
    "operation": "40_operations",
}
VALID_RECORD_TYPES = frozenset({"project", "operation"})


class IdentityError(RuntimeError):
    """Base class for fail-closed identity failures."""


class MissingIdentity(IdentityError):
    """No direct authority exists for the requested slug."""


class DuplicateIdentity(IdentityError):
    """The slug exists in more than one lifecycle root."""


class InvalidIdentity(IdentityError):
    """The direct authority exists but is unsafe or internally inconsistent."""


class FrontmatterError(InvalidIdentity):
    """Lifecycle frontmatter is ambiguous or malformed."""


def _coerce_value(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {"\"", "'"}:
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value.strip("\"'")
    if value.startswith(("[", "{", "(")):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", "~"}:
        return None
    return value


def parse_frontmatter(text: str, *, strict: bool = True) -> dict[str, Any]:
    """Parse the simple metadata subset used by lifecycle README files.

    MainFrame's README frontmatter is intentionally Markdown-first.  The
    resolver only needs scalar identity fields, and refusing malformed lines is
    safer than silently importing a full YAML parser into every CLI.
    """

    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if end is None:
        if strict:
            raise FrontmatterError("frontmatter opening delimiter has no closing delimiter")
        return {}
    result: dict[str, Any] = {}
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1].isspace():
            if strict:
                raise FrontmatterError("indented/nested frontmatter declarations are not supported")
            continue
        if ":" not in line:
            if strict:
                raise FrontmatterError(f"frontmatter line is not a key/value declaration: {line!r}")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            if strict:
                raise FrontmatterError("frontmatter contains an empty key")
            continue
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
            if strict:
                raise FrontmatterError(f"frontmatter key is invalid: {key!r}")
            continue
        if key in result:
            raise FrontmatterError(f"duplicate frontmatter key: {key}")
        result[key] = _coerce_value(value)
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _root_value(mainframe_root: Path, name: str, override: Path | str | None) -> Path:
    if override is not None:
        value = Path(override).expanduser()
    else:
        env_name = "MAINFRAME_PROJECTS_ROOT" if name == "projects" else "MAINFRAME_OPERATIONS_ROOT"
        env_value = os.environ.get(env_name)
        value = Path(env_value).expanduser() if env_value else mainframe_root / {
            "projects": "30_projects",
            "operations": "40_operations",
        }[name]
    if not value.is_absolute():
        value = mainframe_root / value
    # Keep the lexical path here.  Resolving before the scan would erase the
    # fact that a lifecycle root itself is symlinked, which is a direct-
    # authority violation that must fail closed.
    return value.absolute()


def lifecycle_roots(
    mainframe_root: Path | str,
    *,
    projects_root: Path | str | None = None,
    operations_root: Path | str | None = None,
) -> dict[str, Path]:
    root = Path(mainframe_root).expanduser().resolve()
    return {
        "projects": _root_value(root, "projects", projects_root),
        "operations": _root_value(root, "operations", operations_root),
    }


def display_path(mainframe_root: Path | str, path: Path | str) -> str:
    root = Path(mainframe_root).expanduser().resolve()
    candidate = Path(path).expanduser().resolve()
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError:
        return candidate.as_posix()


def _safe_child(parent: Path, child: Path) -> tuple[bool, str | None]:
    if child.is_symlink():
        return False, "symlinked lifecycle entity is not an authority"
    try:
        resolved_parent = parent.resolve()
        resolved_child = child.resolve()
    except OSError as exc:
        return False, f"cannot resolve lifecycle entity: {exc}"
    if not resolved_child.is_relative_to(resolved_parent):
        return False, "lifecycle entity escapes its root"
    if not child.is_dir():
        return False, "lifecycle entity is not a directory"
    return True, None


def _effective_record_type(metadata: dict[str, Any], root_kind: str) -> str | None:
    keys = [key for key in ("record_type", "type") if key in metadata]
    if keys:
        values: list[str | None] = []
        for key in keys:
            raw = metadata.get(key)
            if not isinstance(raw, str):
                values.append(None)
                continue
            normalized = raw.strip().strip("\"'").lower()
            if normalized == "operation":
                values.append("operation")
            elif normalized in {"project", "program", "evaluation", "lifecycle"}:
                values.append("project")
            else:
                # An explicit but unknown declaration must not silently fall
                # back to the containing folder's historical default.
                values.append(None)
        if len(values) == 2 and values[0] != values[1]:
            return None
        return values[0]
    # Existing project READMEs predate record_type.  A project-root record is
    # compatible as a project; an operation-root record must opt in explicitly.
    return "project" if root_kind == "projects" else None


def _lifecycle_state(metadata: dict[str, Any]) -> tuple[str | None, str | None]:
    project_state = metadata.get("project_state")
    lifecycle_state = metadata.get("lifecycle_state")
    if project_state is not None and lifecycle_state is not None:
        if str(project_state).strip() != str(lifecycle_state).strip():
            return None, "project_state and lifecycle_state conflict"
    value = lifecycle_state if lifecycle_state is not None else project_state
    if value is None:
        value = metadata.get("status")
    return (str(value).strip() if value is not None else None), None


@dataclass(frozen=True)
class LifecycleRecord:
    slug: str
    path: Path
    root_kind: str
    record_type: str
    metadata: dict[str, Any]
    lifecycle_state: str | None
    readme_path: Path
    readme_sha256: str
    issues: tuple[str, ...] = field(default_factory=tuple)
    coordination_path: Path | None = None
    coordination_sha256: str | None = None
    coordination_metadata: dict[str, Any] = field(default_factory=dict)
    wip_class: str | None = None
    state_source: str = "README.md"

    @property
    def root_name(self) -> str:
        return "30_projects" if self.root_kind == "projects" else "40_operations"

    def relative_path(self, mainframe_root: Path | str) -> str:
        return display_path(mainframe_root, self.path)

    def manifest_entry(self, mainframe_root: Path | str) -> dict[str, Any]:
        result = {
            "id": self.slug,
            "record_type": self.record_type,
            "path": self.relative_path(mainframe_root),
            "lifecycle_state": self.lifecycle_state,
            "readme_sha256": self.readme_sha256,
        }
        if self.wip_class is not None:
            result["wip_class"] = self.wip_class
        return result


@dataclass
class IdentityScan:
    records: list[LifecycleRecord] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    root_issues: list[str] = field(default_factory=list)

    @property
    def by_slug(self) -> dict[str, list[LifecycleRecord]]:
        result: dict[str, list[LifecycleRecord]] = {}
        for record in self.records:
            result.setdefault(record.slug, []).append(record)
        return result


def _record_for_child(child: Path, root_kind: str) -> LifecycleRecord | None:
    slug = child.name
    issues: list[str] = []
    ok, issue = _safe_child(child.parent, child)
    if not ok:
        issues.append(issue or "unsafe lifecycle entity")
    if not SLUG_RE.fullmatch(slug):
        issues.append("invalid lifecycle slug")
    readme = child / "README.md"
    if readme.is_symlink():
        issues.append("README.md is symlinked")
    if not readme.is_file():
        issues.append("README.md missing or not a regular file")
        metadata: dict[str, Any] = {}
        readme_hash = ""
    else:
        try:
            resolved_readme = readme.resolve()
            if not resolved_readme.is_relative_to(child.resolve()):
                issues.append("README.md escapes lifecycle entity")
            raw = readme.read_bytes()
            metadata = parse_frontmatter(raw.decode("utf-8"), strict=True)
            readme_hash = hashlib.sha256(raw).hexdigest()
        except FrontmatterError as exc:
            metadata = {}
            readme_hash = ""
            issues.append(str(exc))
        except (OSError, UnicodeError) as exc:
            metadata = {}
            readme_hash = ""
            issues.append(f"README.md unreadable: {type(exc).__name__}: {exc}")

    coordination_path = child / "PROJECT.md"
    coordination_metadata: dict[str, Any] = {}
    coordination_hash: str | None = None
    if coordination_path.exists() or coordination_path.is_symlink():
        if coordination_path.is_symlink():
            issues.append("PROJECT.md is symlinked")
        elif not coordination_path.is_file():
            issues.append("PROJECT.md is not a regular file")
        else:
            try:
                coordination_raw = coordination_path.read_bytes()
                coordination_hash = hashlib.sha256(coordination_raw).hexdigest()
                coordination_text = coordination_raw.decode("utf-8")
                # PROJECT.md is an optional public-mirror coordination surface.
                # A plain Markdown file is valid when it carries no frontmatter;
                # an attempted frontmatter block must still be unambiguous.
                coordination_metadata = parse_frontmatter(coordination_text, strict=True)
            except FrontmatterError as exc:
                issues.append(f"PROJECT.md: {exc}")
            except (OSError, UnicodeError) as exc:
                issues.append(f"PROJECT.md unreadable: {type(exc).__name__}: {exc}")

    record_type = _effective_record_type(metadata, root_kind)
    if record_type not in VALID_RECORD_TYPES:
        issues.append("record_type is missing or invalid")
        record_type = "invalid"
    readme_state, state_issue = _lifecycle_state(metadata)
    if state_issue:
        issues.append(state_issue)
    coordination_state, coordination_state_issue = _lifecycle_state(coordination_metadata)
    if coordination_state_issue:
        issues.append(f"PROJECT.md: {coordination_state_issue}")
    if coordination_state is not None:
        if readme_state is not None and readme_state != coordination_state:
            issues.append("README lifecycle state differs from PROJECT.md owner")
        state = coordination_state
        state_source = "PROJECT.md"
    else:
        state = readme_state
        state_source = "README.md"
    readme_wip = metadata.get("wip_class")
    coordination_wip = coordination_metadata.get("wip_class")
    if readme_wip is not None and coordination_wip is not None and str(readme_wip) != str(coordination_wip):
        issues.append("README wip_class differs from PROJECT.md owner")
    wip_raw = coordination_wip if coordination_wip is not None else readme_wip
    wip_class = str(wip_raw).strip() if wip_raw is not None else None
    if wip_class is not None and wip_class not in {"product", "eval", "anchor"}:
        issues.append(f"invalid wip_class: {wip_class}")
    project_record_type = _effective_record_type(coordination_metadata, root_kind)
    if "record_type" in coordination_metadata and project_record_type != record_type:
        issues.append("README and PROJECT.md record_type declarations differ")
    if root_kind == "operations" and metadata.get("record_type") != "operation":
        issues.append("operation-root README must declare record_type: operation")
    return LifecycleRecord(
        slug=slug,
        path=child,
        root_kind=root_kind,
        record_type=record_type,
        metadata=metadata,
        lifecycle_state=state,
        readme_path=readme,
        readme_sha256=readme_hash,
        issues=tuple(issues),
        coordination_path=coordination_path if coordination_path.is_file() else None,
        coordination_sha256=coordination_hash,
        coordination_metadata=coordination_metadata,
        wip_class=wip_class,
        state_source=state_source,
    )


def scan_lifecycle_records(
    mainframe_root: Path | str,
    *,
    projects_root: Path | str | None = None,
    operations_root: Path | str | None = None,
) -> IdentityScan:
    root = Path(mainframe_root).expanduser().resolve()
    roots = lifecycle_roots(root, projects_root=projects_root, operations_root=operations_root)
    result = IdentityScan()
    for root_kind, root_path in (("projects", roots["projects"]), ("operations", roots["operations"])):
        if root_path.is_symlink():
            issue = f"{root_kind} lifecycle root is symlinked: {root_path}"
            result.issues.append(issue)
            result.root_issues.append(issue)
            continue
        if not root_path.exists():
            continue
        if not root_path.is_dir():
            issue = f"{root_kind} lifecycle root is not a directory: {root_path}"
            result.issues.append(issue)
            result.root_issues.append(issue)
            continue
        try:
            children: Iterable[Path] = sorted(root_path.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            issue = f"cannot enumerate {root_kind} lifecycle root: {exc}"
            result.issues.append(issue)
            result.root_issues.append(issue)
            continue
        for child in children:
            if child.name.startswith("."):
                continue
            if not child.is_dir() and not child.is_symlink():
                continue
            record = _record_for_child(child, root_kind)
            if record is None:
                continue
            result.records.append(record)
            result.issues.extend(
                f"{record.root_name}/{record.slug}: {issue}" for issue in record.issues
            )
    for slug, matches in result.by_slug.items():
        if len(matches) > 1:
            result.issues.append(
                f"duplicate lifecycle identity {slug}: "
                + ", ".join(sorted(r.relative_path(root) for r in matches))
            )
    return result


def resolve_record(
    mainframe_root: Path | str,
    slug: str,
    *,
    expected_record_type: str | None = None,
    projects_root: Path | str | None = None,
    operations_root: Path | str | None = None,
) -> LifecycleRecord:
    if not SLUG_RE.fullmatch(slug):
        raise InvalidIdentity(f"invalid lifecycle slug: {slug!r}")
    root = Path(mainframe_root).expanduser().resolve()
    scan = scan_lifecycle_records(
        root,
        projects_root=projects_root,
        operations_root=operations_root,
    )
    if scan.root_issues:
        raise InvalidIdentity("cannot prove cross-root lifecycle uniqueness: " + "; ".join(scan.root_issues))
    matches = scan.by_slug.get(slug, [])
    if len(matches) == 0:
        raise MissingIdentity(f"no direct lifecycle authority for {slug!r}")
    if len(matches) > 1:
        locations = ", ".join(sorted(record.relative_path(root) for record in matches))
        raise DuplicateIdentity(f"duplicate lifecycle identity {slug!r}: {locations}")
    record = matches[0]
    if record.issues:
        raise InvalidIdentity(f"invalid lifecycle authority {record.relative_path(root)}: " + "; ".join(record.issues))
    if expected_record_type and record.record_type != expected_record_type:
        raise InvalidIdentity(
            f"{slug!r} has record_type={record.record_type!r}, expected {expected_record_type!r}"
        )
    return record


def resolve_path(
    mainframe_root: Path | str,
    slug: str,
    *,
    expected_record_type: str | None = None,
    projects_root: Path | str | None = None,
    operations_root: Path | str | None = None,
) -> Path:
    return resolve_record(
        mainframe_root,
        slug,
        expected_record_type=expected_record_type,
        projects_root=projects_root,
        operations_root=operations_root,
    ).path


def stable_identity_snapshot(mainframe_root: Path | str, slug: str) -> dict[str, Any]:
    """Return a compact direct-authority snapshot for a writer precondition."""

    record = resolve_record(mainframe_root, slug)
    return {
        "id": record.slug,
        "record_type": record.record_type,
        "path": record.relative_path(mainframe_root),
        "readme_sha256": record.readme_sha256,
        "coordination_sha256": record.coordination_sha256,
        "lifecycle_state": record.lifecycle_state,
        "state_source": record.state_source,
        "wip_class": record.wip_class,
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write a small receipt without replacing an existing receipt silently."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
