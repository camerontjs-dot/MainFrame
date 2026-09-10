from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "bin" / "session-open"
LOADER = SourceFileLoader("session_open", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

build_context = mod.build_context
detect_project_from_state = mod.detect_project_from_state
print_result = mod.print_result
is_valid_project_slug = mod.is_valid_project_slug


STATE_WITH_PROJECT = """\
# STATE

**Status**: Active

## Active Project
test-project

## Next Actions
- do things
"""

STATE_WITHOUT_PROJECT = """\
# STATE

**Status**: Active

## Next Actions
- do things
"""


class DetectProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_detects_project_from_state(self) -> None:
        state = self.root / "STATE.md"
        state.write_text(STATE_WITH_PROJECT, encoding="utf-8")
        self.assertEqual(detect_project_from_state(state), "test-project")

    def test_returns_none_when_no_heading(self) -> None:
        state = self.root / "STATE.md"
        state.write_text(STATE_WITHOUT_PROJECT, encoding="utf-8")
        self.assertIsNone(detect_project_from_state(state))

    def test_returns_none_when_file_missing(self) -> None:
        self.assertIsNone(detect_project_from_state(self.root / "STATE.md"))


class SessionOpenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (self.root / "HARNESS.md").write_text("# Harness\n", encoding="utf-8")
        (self.root / "STATE.md").write_text(STATE_WITHOUT_PROJECT, encoding="utf-8")
        (self.root / "30_projects").mkdir()
        (self.root / "30_projects/AGENTS.md").write_text("# Projects\n", encoding="utf-8")
        workflow = self.root / ".context/workflows/project-resume-and-candidate-lifecycle.md"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("# Project reconstruction\n", encoding="utf-8")
        (workflow.parent / "session-open.md").write_text("# Session route\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_minimal_open_no_project(self) -> None:
        result = build_context(self.root)
        self.assertTrue(result.ok)
        self.assertIsNone(result.project)
        real_entries = [e for e in result.entries if not e.path.startswith("(")]
        self.assertEqual(len(real_entries), 4)
        self.assertEqual(real_entries[0].path, "AGENTS.md")
        self.assertEqual(real_entries[1].path, "HARNESS.md")
        self.assertEqual(real_entries[2].path, "STATE.md")

    def test_open_with_project_flag(self) -> None:
        proj_dir = self.root / "30_projects" / "foo"
        proj_dir.mkdir(parents=True)
        (proj_dir / "README.md").write_text("# Foo\n", encoding="utf-8")

        result = build_context(self.root, project="foo")
        self.assertTrue(result.ok)
        self.assertEqual(result.project, "foo")
        self.assertEqual(result.project_source, "flag")
        paths = [e.path for e in result.entries]
        self.assertIn("30_projects/foo/README.md", paths)

    def test_auto_detect_project_from_state(self) -> None:
        (self.root / "STATE.md").write_text(STATE_WITH_PROJECT, encoding="utf-8")
        proj_dir = self.root / "30_projects" / "test-project"
        proj_dir.mkdir(parents=True)
        (proj_dir / "README.md").write_text("# Test\n", encoding="utf-8")

        result = build_context(self.root, intent="resume")
        self.assertEqual(result.project, "test-project")
        self.assertEqual(result.project_source, "state")
        paths = [e.path for e in result.entries]
        self.assertIn("30_projects/test-project/README.md", paths)

    def test_flag_overrides_state(self) -> None:
        (self.root / "STATE.md").write_text(STATE_WITH_PROJECT, encoding="utf-8")
        proj_dir = self.root / "30_projects" / "override"
        proj_dir.mkdir(parents=True)
        (proj_dir / "README.md").write_text("# Override\n", encoding="utf-8")

        result = build_context(self.root, project="override")
        self.assertEqual(result.project, "override")
        self.assertEqual(result.project_source, "flag")

    def test_missing_agents_is_not_ok(self) -> None:
        (self.root / "AGENTS.md").unlink()
        result = build_context(self.root)
        self.assertFalse(result.ok)

    def test_missing_state_is_not_ok(self) -> None:
        (self.root / "STATE.md").unlink()
        result = build_context(self.root)
        self.assertFalse(result.ok)

    def test_missing_harness_cannot_report_valid_context(self) -> None:
        (self.root / "HARNESS.md").unlink()
        result = build_context(self.root)
        self.assertFalse(result.ok)
        self.assertTrue(result.degraded)
        self.assertEqual(result.missing_required, ["HARNESS.md"])

    def test_missing_project_contracts_cannot_report_valid_context(self) -> None:
        project = self.root / "30_projects/foo"
        project.mkdir()
        (project / "README.md").write_text("# Foo\n", encoding="utf-8")
        (self.root / "30_projects/AGENTS.md").unlink()
        (self.root / ".context/workflows/project-resume-and-candidate-lifecycle.md").unlink()
        result = build_context(self.root, project="foo")
        self.assertFalse(result.ok)
        self.assertIn("30_projects/AGENTS.md", result.missing_required)
        self.assertIn(".context/workflows/project-resume-and-candidate-lifecycle.md",
                      result.missing_required)

    def test_task_path_loads_only_its_ancestor_contracts_before_project_content(self) -> None:
        project = self.root / "30_projects/foo"
        target = project / "workbench/src/module.py"
        target.parent.mkdir(parents=True)
        target.write_text("pass\n", encoding="utf-8")
        (project / "README.md").write_text("# Public readme\n", encoding="utf-8")
        (project / "PROJECT.md").write_text("project_state: paused\n", encoding="utf-8")
        for directory in (project, project / "workbench", project / "raw-materials",
                          self.root / "30_projects/unrelated"):
            directory.mkdir(exist_ok=True)
            (directory / "AGENTS.md").write_text("# Local rule\n", encoding="utf-8")

        result = build_context(self.root, project="foo", task_path=str(target.relative_to(self.root)))
        self.assertTrue(result.ok)
        paths = [e.path for e in result.entries]
        expected = ["AGENTS.md", "HARNESS.md", "30_projects/AGENTS.md",
                    "30_projects/foo/AGENTS.md", "30_projects/foo/workbench/AGENTS.md",
                    "30_projects/foo/README.md", "30_projects/foo/PROJECT.md"]
        self.assertEqual([p for p in paths if p in expected], expected)
        self.assertNotIn("30_projects/foo/raw-materials/AGENTS.md", paths)
        self.assertNotIn("30_projects/unrelated/AGENTS.md", paths)

        project_only = build_context(self.root, project="foo")
        self.assertNotIn("30_projects/foo/workbench/AGENTS.md",
                         [e.path for e in project_only.entries])

    def test_invalid_task_paths_fail_without_loading_other_contracts(self) -> None:
        project = self.root / "30_projects/foo"
        project.mkdir()
        (project / "README.md").write_text("# Foo\n", encoding="utf-8")
        outside = self.root / "private-other"
        outside.mkdir()
        (outside / "AGENTS.md").write_text("# Other contract\n", encoding="utf-8")
        (project / "outside-link").symlink_to(outside, target_is_directory=True)
        for path in ("private-other", "30_projects/foo/missing", "30_projects/foo/outside-link"):
            with self.subTest(path=path):
                result = build_context(self.root, project="foo", task_path=path)
                self.assertFalse(result.ok)
                self.assertTrue(result.path_error)
                self.assertNotIn("private-other/AGENTS.md", [e.path for e in result.entries])

    def test_task_path_requires_explicit_project(self) -> None:
        result = build_context(self.root, task_path=".")
        self.assertFalse(result.ok)
        self.assertIn("explicit --project", result.path_error)

    def test_directory_named_contract_is_a_missing_required_file(self) -> None:
        project = self.root / "30_projects/foo"
        project.mkdir()
        (project / "README.md").write_text("# Foo\n", encoding="utf-8")
        (project / "AGENTS.md").mkdir()
        result = build_context(self.root, project="foo")
        self.assertFalse(result.ok)
        self.assertIn("30_projects/foo/AGENTS.md", result.missing_required)

    def test_phase_plan_discovery(self) -> None:
        (self.root / "STATE.md").write_text(STATE_WITH_PROJECT, encoding="utf-8")
        proj_dir = self.root / "30_projects" / "test-project"
        plans_dir = proj_dir / "plans"
        plans_dir.mkdir(parents=True)
        (proj_dir / "README.md").write_text("# Test\n", encoding="utf-8")
        (plans_dir / "01-first.md").write_text(
            '---\ntitle: "Phase 1"\nstatus: "active"\n---\n# Phase 1\n',
            encoding="utf-8",
        )

        result = build_context(self.root, intent="resume", task="first")
        paths = [e.path for e in result.entries]
        self.assertTrue(any("01-first.md" in p for p in paths))
        plan_entry = [e for e in result.entries if "01-first.md" in e.path][0]
        self.assertIn("candidate", plan_entry.note)

    def test_skips_non_active_phase_plan(self) -> None:
        (self.root / "STATE.md").write_text(STATE_WITH_PROJECT, encoding="utf-8")
        proj_dir = self.root / "30_projects" / "test-project"
        plans_dir = proj_dir / "plans"
        plans_dir.mkdir(parents=True)
        (proj_dir / "README.md").write_text("# Test\n", encoding="utf-8")
        (plans_dir / "01-done.md").write_text(
            '---\ntitle: "Phase 1"\nstatus: "shipped"\n---\n# Phase 1\n',
            encoding="utf-8",
        )

        result = build_context(self.root, intent="resume")
        paths = [e.path for e in result.entries]
        self.assertFalse(any("01-done.md" in p for p in paths))

    def test_print_contents_mode(self) -> None:
        result = build_context(self.root)
        buf = StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            print_result(result, self.root, print_contents=True)
        finally:
            sys.stdout = old_stdout
        output = buf.getvalue()
        self.assertIn("--- BEGIN AGENTS.md ---", output)
        self.assertIn("--- END AGENTS.md ---", output)
        self.assertIn("# Agents", output)

    def test_deferred_entries_present(self) -> None:
        result = build_context(self.root)
        paths = [e.path for e in result.entries]
        self.assertIn("(task-local)", paths)
        self.assertIn("(evidence)", paths)

    def test_json_output(self) -> None:
        result = build_context(self.root)
        data = {
            "ok": result.ok,
            "project": result.project,
            "project_source": result.project_source,
            "entries": [
                {"order": e.order, "path": e.path, "exists": e.exists,
                 "size": e.size, "note": e.note}
                for e in result.entries
            ],
        }
        parsed = json.loads(json.dumps(data))
        self.assertTrue(parsed["ok"])
        self.assertIsNone(parsed["project"])
        self.assertIsInstance(parsed["entries"], list)

    def test_compound_state_label_not_ok(self) -> None:
        """July 10 false-green: compound narrative must not report ok:true."""
        (self.root / "STATE.md").write_text(
            "# S\n\n## Active Project\n\n"
            "agent-tracker-eval (Focus Board) + mainframe-process-eval (canaries)\n",
            encoding="utf-8",
        )
        result = build_context(self.root, intent="resume")
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.project_error)
        self.assertTrue(result.degraded)
        self.assertFalse(result.project_exists)
        paths = [e.path for e in result.entries]
        # no mangled invented path treated as the project entry
        self.assertIn("(invalid-project-label)", paths)
        self.assertFalse(any("agent-tracker-eval-(" in p for p in paths))

    def test_missing_project_readme_not_ok(self) -> None:
        (self.root / "STATE.md").write_text(
            "# S\n\n## Active Project\n\nmissing-slug\n",
            encoding="utf-8",
        )
        result = build_context(self.root, intent="resume")
        self.assertFalse(result.ok)
        self.assertEqual(result.project, "missing-slug")
        self.assertFalse(result.project_exists)
        self.assertIn("missing", (result.project_error or "").lower())

    def test_flag_missing_project_not_ok(self) -> None:
        result = build_context(self.root, project="no-such-project")
        self.assertFalse(result.ok)
        self.assertFalse(result.project_exists)

    def test_valid_slug_helpers(self) -> None:
        self.assertTrue(is_valid_project_slug("mainframe-process-eval"))
        self.assertFalse(is_valid_project_slug("a + b"))
        self.assertFalse(is_valid_project_slug("foo (bar)"))
        self.assertFalse(is_valid_project_slug("has space"))


if __name__ == "__main__":
    unittest.main()
