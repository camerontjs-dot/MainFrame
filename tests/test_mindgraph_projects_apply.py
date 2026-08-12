"""Tests for staged projects MindGraph apply (ADR-045)."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import mindgraph_projects_apply as mpa  # noqa: E402


class CoverageTests(unittest.TestCase):
    def test_coverage_complete(self) -> None:
        cov = mpa.coverage_report(["a", "b"], ["a", "b"])
        self.assertTrue(cov["complete"])
        self.assertEqual(cov["missing_dirs"], [])
        self.assertEqual(cov["omitted_dirs"], [])

    def test_coverage_missing_and_omitted(self) -> None:
        cov = mpa.coverage_report(["a", "ghost"], ["a", "extra"])
        self.assertFalse(cov["complete"])
        self.assertEqual(cov["missing_dirs"], ["ghost"])
        self.assertEqual(cov["omitted_dirs"], ["extra"])


class NamespaceVerifyTests(unittest.TestCase):
    def test_verify_stage_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.sqlite"
            con = sqlite3.connect(db)
            con.execute(
                "CREATE TABLE documents (id TEXT, namespace TEXT, title TEXT)"
            )
            for ns in ("alpha", "beta"):
                con.execute(
                    "INSERT INTO documents VALUES (?, ?, ?)",
                    (f"id-{ns}", ns, "t"),
                )
            con.commit()
            con.close()
            # pad size > 10k for ok check
            with db.open("ab") as f:
                f.write(b"x" * 12_000)
            v = mpa.verify_stage(db, ["alpha", "beta"])
            self.assertTrue(v["ok"], v)
            self.assertEqual(v["missing_namespaces"], [])

    def test_verify_stage_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.sqlite"
            con = sqlite3.connect(db)
            con.execute(
                "CREATE TABLE documents (id TEXT, namespace TEXT, title TEXT)"
            )
            con.execute("INSERT INTO documents VALUES ('1', 'alpha', 't')")
            con.commit()
            con.close()
            with db.open("ab") as f:
                f.write(b"x" * 12_000)
            v = mpa.verify_stage(db, ["alpha", "beta"])
            self.assertFalse(v["ok"])
            self.assertEqual(v["missing_namespaces"], ["beta"])


class ManifestLoadTests(unittest.TestCase):
    def test_live_manifest_loads(self) -> None:
        projects = mpa.load_manifest_projects(mpa.DEFAULT_MANIFEST)
        self.assertGreaterEqual(len(projects), 20)
        real = mpa.real_project_dirs(ROOT / "30_projects")
        cov = mpa.coverage_report(projects, real)
        self.assertTrue(cov["complete"], cov)

    def test_default_manifest_excludes_outputs(self) -> None:
        payload = json.loads(mpa.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(payload.get("profile"), "default")
        includes = payload.get("include") or []
        self.assertFalse(any("outputs" in p for p in includes))
        excludes = payload.get("exclude") or []
        self.assertTrue(any(p.startswith("outputs") for p in excludes))

    def test_deep_manifest_includes_outputs(self) -> None:
        payload = json.loads(mpa.DEEP_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(payload.get("profile"), "deep")
        includes = payload.get("include") or []
        self.assertTrue(any("outputs" in p for p in includes))

    def test_resolve_manifest_deep(self) -> None:
        from types import SimpleNamespace

        args = SimpleNamespace(manifest=str(mpa.DEFAULT_MANIFEST), deep=True)
        self.assertEqual(mpa.resolve_manifest(args), mpa.DEEP_MANIFEST)
        args2 = SimpleNamespace(manifest=str(mpa.DEFAULT_MANIFEST), deep=False)
        self.assertEqual(mpa.resolve_manifest(args2), mpa.DEFAULT_MANIFEST)


class CliHelpTests(unittest.TestCase):
    def test_bin_help(self) -> None:
        import subprocess

        proc = subprocess.run(
            [str(ROOT / "bin" / "mindgraph-projects-apply"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--plan", proc.stdout)
        self.assertIn("--stage", proc.stdout)
        self.assertIn("--promote", proc.stdout)


if __name__ == "__main__":
    unittest.main()
