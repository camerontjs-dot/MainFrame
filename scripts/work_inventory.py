"""Typed cross-lifecycle inventory and projects-index coverage checks.

The inventory is a derived projection.  It validates direct lifecycle
authority from :mod:`lifecycle_identity`; it never resolves a record for a
reader or writer.  The same typed member map is used by the MindGraph stage,
promotion, and status paths so a namespace count cannot masquerade as green
coverage.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

from lifecycle_identity import (
    IdentityScan,
    LifecycleRecord,
    display_path,
    scan_lifecycle_records,
)


INDEX_ID = "mainframe-projects"
TRUST_PROFILE = "project_status"
DEFAULT_INCLUDE = (
    "README.md",
    "AGENTS.md",
    "log.md",
    "decisions.md",
    "methodology-approach.md",
    "plans/*.md",
    "plans/**/*.md",
)
DEFAULT_EXCLUDE = (
    ".git/*",
    ".git/**/*",
    ".venv/*",
    ".venv/**/*",
    "__pycache__/*",
    "__pycache__/**/*",
    ".pytest_cache/*",
    ".pytest_cache/**/*",
    "workbench/*",
    "workbench/**/*",
    "raw-materials/*",
    "raw-materials/**/*",
    "outputs/*",
    "outputs/**/*",
    "*sealed*",
    "*blind-sheet-*",
    "*items-blind*",
)


@dataclass(frozen=True)
class ManifestMember:
    slug: str
    record_type: str
    path: str
    lifecycle_state: str | None = None
    readme_sha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.slug,
            "record_type": self.record_type,
            "path": self.path,
        }
        if self.lifecycle_state is not None:
            result["lifecycle_state"] = self.lifecycle_state
        if self.readme_sha256 is not None:
            result["readme_sha256"] = self.readme_sha256
        return result


@dataclass(frozen=True)
class ManifestExclusion:
    """A direct lifecycle record intentionally outside an index profile."""

    slug: str
    record_type: str
    path: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.slug,
            "record_type": self.record_type,
            "path": self.path,
            "reason": self.reason,
        }


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest must be an object: {path}")
    return payload


def _member_from_payload(item: Any, index: int) -> ManifestMember:
    if not isinstance(item, dict):
        raise ValueError(f"manifest member #{index} must be an object")
    slug = item.get("id") or item.get("slug")
    record_type = item.get("record_type")
    path = item.get("path")
    if not isinstance(slug, str) or not slug:
        raise ValueError(f"manifest member #{index} has no id")
    if not isinstance(record_type, str) or record_type not in {"project", "operation"}:
        raise ValueError(f"manifest member {slug!r} has invalid record_type")
    if not isinstance(path, str) or not path:
        raise ValueError(f"manifest member {slug!r} has no path")
    return ManifestMember(
        slug=slug,
        record_type=record_type,
        path=path.rstrip("/"),
        lifecycle_state=(str(item["lifecycle_state"]) if item.get("lifecycle_state") is not None else None),
        readme_sha256=(str(item["readme_sha256"]) if item.get("readme_sha256") is not None else None),
    )


def _exclusion_from_payload(item: Any, index: int) -> ManifestExclusion:
    if not isinstance(item, dict):
        raise ValueError(f"manifest exclusion #{index} must be an object")
    slug = item.get("id") or item.get("slug")
    record_type = item.get("record_type")
    path = item.get("path")
    reason = item.get("reason")
    if not isinstance(slug, str) or not slug:
        raise ValueError(f"manifest exclusion #{index} has no id")
    if not isinstance(record_type, str) or record_type not in {"project", "operation"}:
        raise ValueError(f"manifest exclusion {slug!r} has invalid record_type")
    if not isinstance(path, str) or not path:
        raise ValueError(f"manifest exclusion {slug!r} has no path")
    path = path.rstrip("/")
    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or not (path.startswith("30_projects/") or path.startswith("40_operations/"))
    ):
        raise ValueError(f"manifest exclusion {slug!r} path is outside lifecycle roots: {path}")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(f"manifest exclusion {slug!r} has no reason")
    return ManifestExclusion(
        slug=slug,
        record_type=record_type,
        path=path,
        reason=reason.strip(),
    )


def manifest_exclusions(payload: dict[str, Any]) -> tuple[list[ManifestExclusion], list[str]]:
    """Parse explicit profile exclusions without treating them as members."""

    issues: list[str] = []
    raw_exclusions = payload.get("exclusions", [])
    if raw_exclusions is None:
        raw_exclusions = []
    if not isinstance(raw_exclusions, list):
        return [], ["manifest.exclusions must be a list"]
    exclusions: list[ManifestExclusion] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, item in enumerate(raw_exclusions, start=1):
        try:
            exclusion = _exclusion_from_payload(item, index)
        except ValueError as exc:
            issues.append(str(exc))
            continue
        if exclusion.slug in seen_ids:
            issues.append(f"duplicate manifest exclusion identity: {exclusion.slug}")
        if exclusion.path in seen_paths:
            issues.append(f"duplicate manifest exclusion path: {exclusion.path}")
        seen_ids.add(exclusion.slug)
        seen_paths.add(exclusion.path)
        exclusions.append(exclusion)
    return exclusions, issues


def manifest_members(payload: dict[str, Any]) -> tuple[list[ManifestMember], list[str]]:
    """Return typed members plus structural manifest issues."""

    issues: list[str] = []
    raw_members = payload.get("members")
    if not isinstance(raw_members, list):
        issues.append("manifest.members is missing; exact typed coverage is unavailable")
        # Legacy manifests can still be read for a diagnostic, but they are not
        # eligible for a green migration stage.
        raw_projects = payload.get("projects")
        if isinstance(raw_projects, list):
            raw_members = [
                {
                    "id": slug,
                    "record_type": "project",
                    "path": f"30_projects/{slug}",
                }
                for slug in raw_projects
                if isinstance(slug, str)
            ]
        else:
            raw_members = []
    members: list[ManifestMember] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, item in enumerate(raw_members, start=1):
        try:
            member = _member_from_payload(item, index)
        except ValueError as exc:
            issues.append(str(exc))
            continue
        if member.slug in seen_ids:
            issues.append(f"duplicate manifest identity: {member.slug}")
        if member.path in seen_paths:
            issues.append(f"duplicate manifest path: {member.path}")
        seen_ids.add(member.slug)
        seen_paths.add(member.path)
        if not (member.path.startswith("30_projects/") or member.path.startswith("40_operations/")):
            issues.append(f"manifest member {member.slug} path is outside lifecycle roots: {member.path}")
        members.append(member)
    projects = payload.get("projects")
    if isinstance(projects, list):
        project_ids = [str(value) for value in projects]
        # The legacy list is physically rooted in 30_projects.  Typed
        # operation members under 40_operations remain in `members` but are
        # intentionally absent from this compatibility projection.
        member_ids = [
            member.slug for member in members if member.path.startswith("30_projects/")
        ]
        if project_ids != member_ids:
            issues.append(
                "manifest.projects does not exactly preserve 30_projects member order/identity"
            )
    return members, issues


def _record_map(scan: IdentityScan) -> dict[str, LifecycleRecord]:
    result: dict[str, LifecycleRecord] = {}
    for record in scan.records:
        result.setdefault(record.slug, record)
    return result


def validate_manifest(
    mainframe_root: Path | str,
    manifest_path: Path | str,
    *,
    projects_root: Path | str | None = None,
    operations_root: Path | str | None = None,
) -> dict[str, Any]:
    root = Path(mainframe_root).expanduser().resolve()
    manifest = Path(manifest_path).expanduser().resolve()
    issues: list[str] = []
    try:
        payload = load_manifest(manifest)
        members, manifest_issues = manifest_members(payload)
        issues.extend(manifest_issues)
        exclusions, exclusion_issues = manifest_exclusions(payload)
        issues.extend(exclusion_issues)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "manifest": str(manifest),
            "manifest_sha256": sha256_file(manifest),
            "issues": [f"manifest unreadable: {type(exc).__name__}: {exc}"],
            "members": [],
            "exclusions": [],
            "records": [],
        }
    scan = scan_lifecycle_records(
        root,
        projects_root=projects_root,
        operations_root=operations_root,
    )
    issues.extend(scan.issues)
    observed = _record_map(scan)
    expected = {member.slug: member for member in members}
    excluded = {exclusion.slug: exclusion for exclusion in exclusions}
    member_paths = {member.path: member.slug for member in members}
    for exclusion in exclusions:
        if exclusion.slug in expected:
            issues.append(f"manifest exclusion overlaps member identity: {exclusion.slug}")
        if exclusion.path in member_paths:
            issues.append(
                f"manifest exclusion overlaps member path: {exclusion.path}"
            )
    missing = sorted(set(expected) - set(observed))
    excluded_missing = sorted(set(excluded) - set(observed))
    omitted = sorted(set(observed) - set(expected) - set(excluded))
    path_conflicts: list[str] = []
    type_conflicts: list[str] = []
    excluded_path_conflicts: list[str] = []
    excluded_type_conflicts: list[str] = []
    state_conflicts: list[str] = []
    readme_conflicts: list[str] = []
    for slug in sorted(set(expected) & set(observed)):
        member = expected[slug]
        record = observed[slug]
        observed_path = record.relative_path(root)
        if observed_path != member.path:
            path_conflicts.append(f"{slug}: manifest={member.path} direct={observed_path}")
        if record.record_type != member.record_type:
            type_conflicts.append(f"{slug}: manifest={member.record_type} direct={record.record_type}")
        if member.lifecycle_state is not None and record.lifecycle_state != member.lifecycle_state:
            state_conflicts.append(
                f"{slug}: manifest={member.lifecycle_state} direct={record.lifecycle_state}"
            )
        if member.readme_sha256 and record.readme_sha256 != member.readme_sha256:
            readme_conflicts.append(slug)
    for slug in sorted(set(excluded) & set(observed)):
        exclusion = excluded[slug]
        record = observed[slug]
        observed_path = record.relative_path(root)
        if observed_path != exclusion.path:
            excluded_path_conflicts.append(
                f"{slug}: exclusion={exclusion.path} direct={observed_path}"
            )
        if record.record_type != exclusion.record_type:
            excluded_type_conflicts.append(
                f"{slug}: exclusion={exclusion.record_type} direct={record.record_type}"
            )
    if missing:
        issues.append(f"manifest members missing from direct roots: {missing}")
    if excluded_missing:
        issues.append(f"manifest exclusions missing from direct roots: {excluded_missing}")
    if omitted:
        issues.append(f"direct records omitted from manifest: {omitted}")
    if path_conflicts:
        issues.extend(path_conflicts)
    if type_conflicts:
        issues.extend(type_conflicts)
    if excluded_path_conflicts:
        issues.extend(excluded_path_conflicts)
    if excluded_type_conflicts:
        issues.extend(excluded_type_conflicts)
    if state_conflicts:
        issues.extend(state_conflicts)
    if readme_conflicts:
        issues.append(f"manifest README hashes changed: {readme_conflicts}")
    return {
        "ok": not issues,
        "manifest": str(manifest),
        "manifest_sha256": sha256_file(manifest),
        "schema_version": payload.get("schema_version"),
        "profile": payload.get("profile"),
        "members": [member.as_dict() for member in members],
        "exclusions": [exclusion.as_dict() for exclusion in exclusions],
        "records": [record.manifest_entry(root) for record in sorted(scan.records, key=lambda r: r.slug)],
        "manifest_count": len(members),
        "real_count": len(scan.records),
        "missing_members": missing,
        "excluded_records": sorted(set(excluded) & set(observed)),
        "excluded_missing": excluded_missing,
        "excluded_count": len(exclusions),
        "omitted_records": omitted,
        "path_conflicts": path_conflicts,
        "type_conflicts": type_conflicts,
        "excluded_path_conflicts": excluded_path_conflicts,
        "excluded_type_conflicts": excluded_type_conflicts,
        "state_conflicts": state_conflicts,
        "readme_conflicts": readme_conflicts,
        "issues": issues,
    }


def coverage_report(manifest_projects: list[str], real_dirs: list[str]) -> dict[str, Any]:
    """Compatibility report for callers that only have old slug lists."""

    expected = list(manifest_projects)
    real = list(real_dirs)
    set_m, set_r = set(expected), set(real)
    return {
        "manifest_count": len(expected),
        "real_count": len(real),
        "missing_dirs": sorted(set_m - set_r),
        "omitted_dirs": sorted(set_r - set_m),
        "intersection": sorted(set_m & set_r),
        "complete": set_m == set_r and len(expected) == len(real),
    }


def real_record_slugs(mainframe_root: Path | str) -> list[str]:
    scan = scan_lifecycle_records(mainframe_root)
    return sorted(record.slug for record in scan.records if not record.issues)


def _matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def selected_source_files(
    mainframe_root: Path | str,
    payload: dict[str, Any],
    members: Iterable[ManifestMember] | None = None,
) -> list[dict[str, Any]]:
    """Build the exact Markdown file set the projects ingester should see."""

    root = Path(mainframe_root).expanduser().resolve()
    members = list(members if members is not None else manifest_members(payload)[0])
    include = tuple(payload.get("include") or DEFAULT_INCLUDE)
    exclude = tuple(payload.get("exclude") or DEFAULT_EXCLUDE)
    rows: list[dict[str, Any]] = []
    for member in sorted(members, key=lambda item: item.slug):
        record_root = (root / member.path).resolve()
        if not record_root.is_dir() or not record_root.is_relative_to(root):
            continue
        for path in sorted(record_root.rglob("*.md")):
            if path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(record_root).as_posix()
            if include and not _matches(rel, include):
                continue
            if exclude and _matches(rel, exclude):
                continue
            source_path = rel
            scoped = f"{INDEX_ID}\0{member.slug}\0{source_path}"
            doc_id = hashlib.sha256(scoped.encode("utf-8")).hexdigest()[:16]
            rows.append(
                {
                    "id": doc_id,
                    "namespace": member.slug,
                    "index_id": INDEX_ID,
                    "trust_profile": TRUST_PROFILE,
                    "source_root": str(record_root),
                    "source_path": source_path,
                    "display_path": f"{member.path}/{source_path}",
                    "content_hash": sha256_file(path),
                    "path": str(path),
                    "record_type": member.record_type,
                }
            )
    return rows


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    resolved = db_path.expanduser().resolve()
    # `immutable=1` is only truthful for a separately frozen copy.  The live
    # MindGraph database may have a WAL or a concurrent writer, so use a real
    # read-only transaction snapshot instead.
    uri = f"file:{quote(str(resolved), safe='/')}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    con.execute("BEGIN")
    return con


def document_map_hash(rows: Iterable[dict[str, Any]], *, include_record_type: bool = True) -> str:
    keys = (
        "id",
        "namespace",
        "index_id",
        "trust_profile",
        "source_root",
        "source_path",
        "display_path",
        "content_hash",
    )
    if include_record_type:
        keys = (*keys, "record_type")
    canonical = [
        {
            key: row.get(key)
            for key in keys
        }
        for row in sorted(rows, key=lambda item: (str(item.get("namespace")), str(item.get("source_path"))))
    ]
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_typed_document_map(
    db_path: Path | str,
    mainframe_root: Path | str,
    manifest_path: Path | str,
    *,
    projects_root: Path | str | None = None,
    operations_root: Path | str | None = None,
) -> dict[str, Any]:
    """Verify exact typed rows, paths, IDs, and content hashes in a DB."""

    root = Path(mainframe_root).expanduser().resolve()
    manifest = Path(manifest_path).expanduser().resolve()
    coverage = validate_manifest(
        root,
        manifest,
        projects_root=projects_root,
        operations_root=operations_root,
    )
    result: dict[str, Any] = {
        "ok": False,
        "db": str(Path(db_path).expanduser().resolve()),
        "manifest": str(manifest),
        "coverage_ok": coverage.get("ok", False),
        "coverage": coverage,
        "expected_count": 0,
        "observed_count": 0,
        "missing_documents": [],
        "extra_documents": [],
        "identity_mismatches": [],
        "path_mismatches": [],
        "content_mismatches": [],
        "provenance_mismatches": [],
        "duplicate_database_ids": [],
        "record_type_source": "unknown",
        "record_type_direct_check": False,
        "record_type_derived_check": False,
        "record_type_mismatches": [],
        "record_type_unknown_documents": [],
        "document_map_ok": False,
        "read_snapshot": None,
        "expected_document_map_hash": None,
        "observed_document_map_hash": None,
        "expected_typed_document_map_hash": None,
        "observed_typed_document_map_hash": None,
    }
    if not coverage.get("ok"):
        return result
    payload = load_manifest(manifest)
    members, _ = manifest_members(payload)
    expected_rows = selected_source_files(root, payload, members)
    result["expected_count"] = len(expected_rows)
    result["expected_document_map_hash"] = document_map_hash(expected_rows, include_record_type=False)
    result["expected_typed_document_map_hash"] = document_map_hash(expected_rows, include_record_type=True)
    db = Path(db_path).expanduser().resolve()
    if not db.is_file():
        result["extra_documents"] = ["<database missing>"]
        return result
    try:
        con = _open_readonly(db)
        try:
            table = {row["name"] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"documents"}
            missing_tables = sorted(required - table)
            if missing_tables:
                result["extra_documents"] = [f"missing tables: {missing_tables}"]
                return result
            columns = {row[1] for row in con.execute("PRAGMA table_info(documents)")}
            has_record_type = "record_type" in columns
            result["record_type_source"] = "documents.record_type" if has_record_type else "derived_from_manifest"
            selected = "id, namespace, index_id, trust_profile, source_root, source_path, display_path, content_hash"
            if has_record_type:
                selected += ", record_type"
            rows = [dict(row) for row in con.execute(f"SELECT {selected} FROM documents")]
            result["read_snapshot"] = {
                "mode": "read_only_transaction",
                "journal_mode": str(con.execute("PRAGMA journal_mode").fetchone()[0]),
                "query_only": True,
            }
        finally:
            con.close()
    except (OSError, sqlite3.Error) as exc:
        result["extra_documents"] = [f"database unreadable: {type(exc).__name__}: {exc}"]
        return result
    result["observed_count"] = len(rows)
    expected_by_id = {row["id"]: row for row in expected_rows}
    observed_by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for row in rows:
        doc_id = str(row.get("id"))
        if doc_id in observed_by_id:
            duplicate_ids.append(doc_id)
        observed_by_id[doc_id] = row
    result["duplicate_database_ids"] = sorted(set(duplicate_ids))
    result["missing_documents"] = sorted(set(expected_by_id) - set(observed_by_id))
    result["extra_documents"] = sorted(set(observed_by_id) - set(expected_by_id))
    for doc_id in sorted(set(expected_by_id) & set(observed_by_id)):
        expected = expected_by_id[doc_id]
        observed = observed_by_id[doc_id]
        if observed.get("namespace") != expected["namespace"]:
            result["identity_mismatches"].append(doc_id)
        for key in ("index_id", "trust_profile", "source_root", "source_path", "display_path"):
            if observed.get(key) != expected[key]:
                result["path_mismatches" if key in {"source_root", "source_path", "display_path"} else "provenance_mismatches"].append(
                    {"id": doc_id, "field": key, "expected": expected[key], "observed": observed.get(key)}
                )
        if observed.get("content_hash") != expected["content_hash"]:
            result["content_mismatches"].append(
                {"id": doc_id, "expected": expected["content_hash"], "observed": observed.get("content_hash")}
            )
    result["document_map_ok"] = bool(
        not result["missing_documents"]
        and not result["extra_documents"]
        and not result["identity_mismatches"]
        and not result["path_mismatches"]
        and not result["content_mismatches"]
        and not result["provenance_mismatches"]
        and not result["duplicate_database_ids"]
    )
    if result["record_type_source"] == "documents.record_type":
        result["record_type_direct_check"] = True
        for row in rows:
            doc_id = str(row.get("id"))
            expected = expected_by_id.get(doc_id)
            observed_type = row.get("record_type")
            if expected is None:
                continue
            if observed_type is None or observed_type == "":
                result["record_type_unknown_documents"].append(doc_id)
            elif observed_type != expected.get("record_type"):
                result["record_type_mismatches"].append(
                    {"id": doc_id, "expected": expected.get("record_type"), "observed": observed_type}
                )
    else:
        # The current schema has no typed lifecycle column.  Do not inject the
        # manifest's expected type into observed rows or into the observed DB
        # hash and call that a DB check.  The manifest's classification is
        # still authoritative because validate_manifest proved its typed
        # members against the direct lifecycle README authorities.
        result["record_type_direct_check"] = False
        result["record_type_derived_check"] = bool(result["coverage_ok"])
    result["record_type_unknown_documents"] = sorted(set(result["record_type_unknown_documents"]))
    result["record_type_mismatches"] = sorted(result["record_type_mismatches"], key=lambda item: str(item.get("id")))
    observed_rows = [{**row} for row in rows]
    result["observed_document_map_hash"] = document_map_hash(observed_rows, include_record_type=False)
    if result["record_type_source"] == "documents.record_type":
        result["observed_typed_document_map_hash"] = document_map_hash(observed_rows, include_record_type=True)
    result["ok"] = bool(
        result["coverage_ok"]
        and result["document_map_ok"]
        and (
            result["record_type_direct_check"]
            or result["record_type_derived_check"]
        )
        and not result["record_type_mismatches"]
        and not result["record_type_unknown_documents"]
    )
    return result


def inventory_payload(mainframe_root: Path | str) -> dict[str, Any]:
    root = Path(mainframe_root).expanduser().resolve()
    scan = scan_lifecycle_records(root)
    records = [record.manifest_entry(root) for record in sorted(scan.records, key=lambda r: r.slug)]
    return {
        "schema_version": 1,
        "kind": "mainframe-work-inventory",
        "root": str(root),
        "records": records,
        "count": len(records),
        "issues": scan.issues,
        "ok": not scan.issues,
    }
