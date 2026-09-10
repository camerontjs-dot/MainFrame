"""Synthetic MainFrame fixture: MPE/identity without private evidence."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_record(path: Path, record_type: str, slug: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                f'title: "{slug}"',
                f"type: {record_type}",
                'status: "active"',
                "project_state: active",
                f"record_type: {record_type}",
                'updated: "2026-09-10"',
                'source: "synthetic"',
                "---",
                "",
                f"# {slug}",
                "",
                "Synthetic fixture. Not a private MainFrame record.",
                "",
            ]
        ),
        encoding="utf-8",
    )


class SyntheticMpeFeasibility(unittest.TestCase):
    def _assert_output_not_exported(self, path: Path) -> None:
        manifest_path = ROOT / ".context" / "public-export" / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            exported = set(manifest.get("includes", []))
            exported.update(item["dest"] for item in manifest.get("transforms", []))
            self.assertNotIn(path.as_posix(), exported)
            self.assertFalse(any("/outputs/" in item for item in exported))
            return
        self.assertIn("outputs", path.parts)
        shipped = ROOT / "40_operations" / "mainframe-process-eval" / "outputs"
        self.assertFalse(shipped.exists())
    def test_identity_project_vs_operation_and_failures(self) -> None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from lifecycle_identity import (
            DuplicateIdentity,
            MissingIdentity,
            resolve_record,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_record(
                root / "30_projects" / "example-project" / "README.md",
                "project",
                "example-project",
            )
            _write_record(
                root / "40_operations" / "example-operation" / "README.md",
                "operation",
                "example-operation",
            )
            project = resolve_record(root, "example-project")
            operation = resolve_record(root, "example-operation")
            self.assertEqual(project.record_type, "project")
            self.assertEqual(operation.record_type, "operation")
            with self.assertRaises(MissingIdentity):
                resolve_record(root, "missing-slug")
            _write_record(
                root / "30_projects" / "example-operation" / "README.md",
                "project",
                "example-operation",
            )
            with self.assertRaises(DuplicateIdentity):
                resolve_record(root, "example-operation")

    def test_process_eval_status_on_synthetic_public_layout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "40_operations" / "mainframe-process-eval" / "src"
            src.mkdir(parents=True)
            for name in ("process_eval.py", "runtime.py", "__init__.py"):
                shutil.copy2(
                    ROOT / "40_operations" / "mainframe-process-eval" / "src" / name,
                    src / name,
                )
            (root / "bin").mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "bin" / "process-eval", root / "bin" / "process-eval")
            (root / "scripts").mkdir()
            for name in (
                "lifecycle_identity.py",
                "lifecycle_runtime.py",
                "migration_lease.py",
            ):
                shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
            _write_record(
                root / "40_operations" / "mainframe-process-eval" / "README.md",
                "operation",
                "mainframe-process-eval",
            )
            workflow = root / ".context" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "process-evaluation.md").write_text(
                "# synthetic process evaluation\n", encoding="utf-8"
            )
            proc = subprocess.run(
                [sys.executable, str(root / "bin" / "process-eval"), "status", "--json"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(
                payload["project"], "40_operations/mainframe-process-eval"
            )
            self.assertIsNone(payload["latest_output"])
            self.assertIsNone(payload["loop_eval"])

    def test_real_loop_eval_scorer_on_synthetic_catalogue(self) -> None:
        scorer = (
            ROOT
            / "40_operations"
            / "mainframe-process-eval"
            / "workbench"
            / "loop-eval"
            / "scripts"
            / "score_catalogue.py"
        )
        catalogue = (
            ROOT
            / "examples"
            / "demo-mainframe"
            / "40_operations"
            / "demo-eval"
            / "catalogue"
            / "entries.json"
        )
        self.assertTrue(catalogue.exists())
        self.assertIn("SYNTHETIC", catalogue.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "outputs" / "synthetic-loop-eval.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(scorer),
                    "--catalogue",
                    str(catalogue),
                    "--json",
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"], payload)
            scores = {row["id"]: row["score"] for row in payload["summary"]["scores"]}
            self.assertEqual(scores["loop-synthetic-capture"], 8)
            self.assertEqual(scores["loop-synthetic-thin"], 4)
            self.assertEqual(payload["summary"]["n"], 2)
            self.assertFalse(
                payload["summary"]["by_tier_counts"]["well_defined"] == 0
            )

            self._assert_output_not_exported(out)

    def test_loop_eval_scorer_is_not_a_noop(self) -> None:
        scorer = (
            ROOT
            / "40_operations"
            / "mainframe-process-eval"
            / "workbench"
            / "loop-eval"
            / "scripts"
            / "score_catalogue.py"
        )
        with tempfile.TemporaryDirectory() as td:
            broken = Path(td) / "broken.json"
            broken.write_text(
                json.dumps(
                    {
                        "synthetic": True,
                        "entries": [
                            {
                                "id": "loop-broken",
                                "title": "Broken",
                                "tier": "well_defined",
                                "kind": "loop",
                                "question": "x",
                                "unit_of_work": "x",
                                "status": "active",
                                "last_reviewed": "2026-09-10",
                                "checklist": {"unit_of_work": True},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [sys.executable, str(scorer), "--catalogue", str(broken), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertFalse(payload["ok"])
            self.assertTrue(payload["problems"])

    def test_close_writes_local_only_synthetic_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "40_operations" / "mainframe-process-eval" / "src"
            src.mkdir(parents=True)
            for name in ("process_eval.py", "runtime.py", "__init__.py"):
                shutil.copy2(
                    ROOT / "40_operations" / "mainframe-process-eval" / "src" / name,
                    src / name,
                )
            (root / "bin").mkdir()
            shutil.copy2(ROOT / "bin" / "process-eval", root / "bin" / "process-eval")
            (root / "scripts").mkdir()
            for name in (
                "lifecycle_identity.py",
                "lifecycle_runtime.py",
                "migration_lease.py",
            ):
                shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
            _write_record(
                root / "40_operations" / "mainframe-process-eval" / "README.md",
                "operation",
                "mainframe-process-eval",
            )
            wf = root / ".context" / "workflows"
            wf.mkdir(parents=True)
            (wf / "process-evaluation.md").write_text("# synthetic\n", encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(root / "bin" / "process-eval"),
                    "close",
                    "--run-id",
                    "2026-09-10-synthetic",
                    "--question",
                    "SYNTHETIC: does close write a local-only artifact?",
                    "--write",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            written = (
                root
                / "40_operations"
                / "mainframe-process-eval"
                / "outputs"
                / "2026-09-10-synthetic-process-eval-close.md"
            )
            self.assertTrue(written.is_file(), proc.stdout)
            text = written.read_text(encoding="utf-8")
            self.assertIn("SYNTHETIC", text)
            self.assertIn("same_slice", text)
            self._assert_output_not_exported(written)


if __name__ == "__main__":
    unittest.main()
