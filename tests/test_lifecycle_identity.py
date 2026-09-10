from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lifecycle_identity import (  # noqa: E402
    DuplicateIdentity,
    FrontmatterError,
    InvalidIdentity,
    MissingIdentity,
    resolve_record,
    scan_lifecycle_records,
)
from work_inventory import (  # noqa: E402
    document_map_hash,
    manifest_members,
    selected_source_files,
    validate_manifest,
    verify_typed_document_map,
)


def write_record(root: Path, slug: str, *, record_type: str = "project", state: str = "active") -> Path:
    path = root / slug
    path.mkdir(parents=True, exist_ok=True)
    path.joinpath("README.md").write_text(
        "---\n"
        f"record_type: {record_type}\n"
        f"project_state: {state}\n"
        f"status: {state}\n"
        "---\n"
        f"# {slug}\n",
        encoding="utf-8",
    )
    path.joinpath("plans").mkdir()
    path.joinpath("plans", "plan.md").write_text("# plan\n", encoding="utf-8")
    path.joinpath("log.md").write_text("# log\n", encoding="utf-8")
    return path


def typed_manifest(root: Path) -> Path:
    scan = scan_lifecycle_records(root)
    assert not scan.issues, scan.issues
    members = [record.manifest_entry(root) for record in sorted(scan.records, key=lambda item: item.slug)]
    path = root / "30_projects" / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "profile": "test",
                "projects": [
                    member["id"]
                    for member in members
                    if member["path"].startswith("30_projects/")
                ],
                "members": members,
                "include": ["README.md", "plans/*.md", "log.md"],
                "exclude": ["outputs/*"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


class LifecycleIdentityTests(unittest.TestCase):
    def test_resolves_project_and_operation_across_shared_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root / "30_projects", "project-a")
            write_record(root / "40_operations", "operation-a", record_type="operation")

            project = resolve_record(root, "project-a", expected_record_type="project")
            operation = resolve_record(root, "operation-a", expected_record_type="operation")

            self.assertEqual(project.root_name, "30_projects")
            self.assertEqual(operation.root_name, "40_operations")
            self.assertEqual(operation.relative_path(root), "40_operations/operation-a")

    def test_duplicate_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root / "30_projects", "same")
            write_record(root / "40_operations", "same", record_type="operation")
            with self.assertRaises(DuplicateIdentity):
                resolve_record(root, "same")

    def test_missing_and_invalid_operation_identity_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(MissingIdentity):
                resolve_record(root, "ghost")
            write_record(root / "40_operations", "bad")
            with self.assertRaises(InvalidIdentity):
                resolve_record(root, "bad")

    def test_symlinked_root_and_child_are_not_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real-projects"
            write_record(real, "project-a")
            (root / "30_projects").symlink_to(real, target_is_directory=True)
            self.assertFalse(scan_lifecycle_records(root).records)
            self.assertTrue(scan_lifecycle_records(root).issues)

            root.unlink() if root.is_symlink() else None

    def test_readme_state_conflict_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_record(root / "30_projects", "conflict")
            readme = path / "README.md"
            readme.write_text(
                "---\nrecord_type: project\nproject_state: active\nlifecycle_state: paused\n---\n",
                encoding="utf-8",
            )
            with self.assertRaises(InvalidIdentity):
                resolve_record(root, "conflict")

    def test_explicit_invalid_record_type_does_not_fall_back_to_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_record(root / "30_projects", "bad-type")
            (path / "README.md").write_text(
                "---\nrecord_type: definitely-not-a-type\nproject_state: active\n---\n",
                encoding="utf-8",
            )
            with self.assertRaises(InvalidIdentity):
                resolve_record(root, "bad-type")

    def test_malformed_duplicate_and_nested_frontmatter_fail_closed(self) -> None:
        with self.assertRaises(FrontmatterError):
            from lifecycle_identity import parse_frontmatter
            parse_frontmatter("---\nrecord_type: project\nrecord_type: operation\n---\n")
        with self.assertRaises(FrontmatterError):
            from lifecycle_identity import parse_frontmatter
            parse_frontmatter("---\nidentity:\n  record_type: project\n---\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_record(root / "30_projects", "malformed")
            (path / "README.md").write_text("---\nrecord_type: project\n  project_state: active\n---\n", encoding="utf-8")
            with self.assertRaises(InvalidIdentity):
                resolve_record(root, "malformed")

    def test_uninspectable_sibling_root_blocks_cross_root_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root / "30_projects", "project-a")
            real_operations = root / "real-operations"
            write_record(real_operations, "operation-a", record_type="operation")
            (root / "40_operations").symlink_to(real_operations, target_is_directory=True)
            with self.assertRaises(InvalidIdentity):
                resolve_record(root, "project-a")

    def test_project_md_owns_lifecycle_state_without_copying_private_fields_to_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_record(root / "30_projects", "public-mirror")
            (path / "README.md").write_text("---\nrecord_type: project\n---\n# public mirror\n", encoding="utf-8")
            (path / "PROJECT.md").write_text(
                "---\nproject_state: paused\nwip_class: eval\nnext_action: private reentry\n---\n",
                encoding="utf-8",
            )
            record = resolve_record(root, "public-mirror")
            self.assertEqual(record.lifecycle_state, "paused")
            self.assertEqual(record.state_source, "PROJECT.md")
            self.assertEqual(record.wip_class, "eval")
            entry = record.manifest_entry(root)
            self.assertNotIn("next_action", entry)


class TypedInventoryTests(unittest.TestCase):
    def test_manifest_exactly_covers_both_lifecycle_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root / "30_projects", "project-a")
            write_record(root / "40_operations", "operation-a", record_type="operation")
            manifest = typed_manifest(root)
            report = validate_manifest(root, manifest)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["manifest_count"], 2)

            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["projects"], ["project-a"])
            self.assertEqual(
                [member["id"] for member in payload["members"]],
                ["operation-a", "project-a"],
            )

    def test_explicit_exclusion_closes_coverage_without_ingesting_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root / "30_projects", "project-a")
            write_record(root / "30_projects", "excluded-project")
            manifest = typed_manifest(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["members"] = [
                member for member in payload["members"] if member["id"] == "project-a"
            ]
            payload["projects"] = ["project-a"]
            payload["exclusions"] = [
                {
                    "id": "excluded-project",
                    "record_type": "project",
                    "path": "30_projects/excluded-project",
                    "reason": "independent repository is outside this profile",
                }
            ]
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            report = validate_manifest(root, manifest)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["omitted_records"], [])
            self.assertEqual(report["excluded_records"], ["excluded-project"])
            self.assertEqual(report["excluded_count"], 1)
            members, issues = manifest_members(payload)
            self.assertEqual(issues, [])
            rows = selected_source_files(root, payload, members)
            self.assertEqual({row["namespace"] for row in rows}, {"project-a"})

    def test_manifest_omission_and_type_mismatch_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root / "30_projects", "project-a")
            write_record(root / "40_operations", "operation-a", record_type="operation")
            manifest = typed_manifest(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["members"] = [
                member for member in payload["members"] if member["id"] == "project-a"
            ]
            payload["projects"] = ["project-a"]
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            report = validate_manifest(root, manifest)
            self.assertFalse(report["ok"])
            self.assertEqual(report["omitted_records"], ["operation-a"])

            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["members"][0]["record_type"] = "operation"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            report = validate_manifest(root, manifest)
            self.assertIn("project-a: manifest=operation direct=project", report["type_conflicts"])

    def test_exact_database_document_map_detects_stale_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root / "30_projects", "project-a")
            manifest = typed_manifest(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            members, issues = manifest_members(payload)
            self.assertEqual(issues, [])
            expected = selected_source_files(root, payload, members)
            self.assertTrue(expected)

            db = root / "projection.sqlite"
            con = sqlite3.connect(db)
            con.execute(
                "CREATE TABLE documents (id TEXT, namespace TEXT, index_id TEXT, trust_profile TEXT, "
                "source_root TEXT, source_path TEXT, display_path TEXT, content_hash TEXT, record_type TEXT)"
            )
            for row in expected:
                con.execute(
                    "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    tuple(row[key] for key in (
                        "id", "namespace", "index_id", "trust_profile", "source_root",
                        "source_path", "display_path", "content_hash", "record_type",
                    )),
                )
            con.commit()
            con.close()

            green = verify_typed_document_map(db, root, manifest)
            self.assertTrue(green["ok"], green)
            self.assertEqual(green["expected_typed_document_map_hash"], document_map_hash(expected))
            self.assertEqual(green["expected_document_map_hash"], document_map_hash(expected, include_record_type=False))

            (root / "30_projects" / "project-a" / "plans" / "plan.md").write_text(
                "# changed\n", encoding="utf-8"
            )
            stale = verify_typed_document_map(db, root, manifest)
            self.assertFalse(stale["ok"])
            self.assertTrue(stale["content_mismatches"])

            untyped_db = root / "untyped.sqlite"
            con = sqlite3.connect(untyped_db)
            con.execute(
                "CREATE TABLE documents (id TEXT, namespace TEXT, index_id TEXT, trust_profile TEXT, "
                "source_root TEXT, source_path TEXT, display_path TEXT, content_hash TEXT)"
            )
            current_expected = selected_source_files(root, payload, members)
            for row in current_expected:
                con.execute(
                    "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    tuple(row[key] for key in (
                        "id", "namespace", "index_id", "trust_profile", "source_root",
                        "source_path", "display_path", "content_hash",
                    )),
                )
            con.commit()
            con.close()
            untyped = verify_typed_document_map(untyped_db, root, manifest)
            self.assertTrue(untyped["document_map_ok"], untyped)
            self.assertFalse(untyped["record_type_direct_check"])
            self.assertTrue(untyped["record_type_derived_check"])
            self.assertEqual(untyped["record_type_source"], "derived_from_manifest")
            self.assertEqual(untyped["record_type_unknown_documents"], [])
            self.assertTrue(untyped["ok"])

    def test_legacy_manifest_is_diagnostic_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_record(root / "30_projects", "project-a")
            manifest = root / "legacy.json"
            manifest.write_text(json.dumps({"projects": ["project-a"]}), encoding="utf-8")
            report = validate_manifest(root, manifest)
            self.assertFalse(report["ok"])
            self.assertIn("manifest.members is missing", report["issues"][0])


if __name__ == "__main__":
    unittest.main()
