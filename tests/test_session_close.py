from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "bin" / "session-close"
LOADER = SourceFileLoader("session_close", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

check_session = mod.check_session


def make_runner(changed_files: list[str] | None = None,
                fail_commands: set[str] | None = None):
    changed = changed_files or []
    failures = fail_commands or set()

    def run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        cmd_str = " ".join(cmd)
        if any(f in cmd_str for f in failures):
            return subprocess.CompletedProcess(cmd, 1, "", "error")

        if "git" in cmd and "diff" in cmd and "--name-only" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "\n".join(changed), "")
        if "git" in cmd and "status" in cmd:
            porcelain = "\n".join(f" M {f}" for f in changed)
            return subprocess.CompletedProcess(cmd, 0, porcelain, "")

        return subprocess.CompletedProcess(cmd, 0, "", "")

    return run_command


STATE_MD = """\
# STATE

**Status**: Active

## Active Project
test-project

## Next Actions
- things
"""


class SessionCloseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "STATE.md").write_text(STATE_MD, encoding="utf-8")
        (self.root / "bin").mkdir()
        for script in ("sync-project-index", "mindgraph-refresh", "workflow-report"):
            (self.root / "bin" / script).write_text("#!/bin/sh\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_clean_state_no_changes(self) -> None:
        runner = make_runner([])
        result = check_session(self.root, run_command=runner)
        self.assertTrue(result.ok)
        auto_needed = [a for a in result.actions
                       if a.kind == "auto" and a.needed]
        self.assertEqual(len(auto_needed), 0)

    def test_detects_project_metadata_change(self) -> None:
        runner = make_runner(["30_projects/foo/README.md"])
        result = check_session(self.root, run_command=runner)
        sync = [a for a in result.actions if a.name == "sync-project-index"][0]
        self.assertTrue(sync.needed)
        self.assertEqual(sync.kind, "auto")

    def test_detects_knowledge_change(self) -> None:
        runner = make_runner(["10_knowledge/ai-systems/note.md"])
        result = check_session(self.root, run_command=runner)
        refresh = [a for a in result.actions if a.name == "mindgraph-refresh"][0]
        self.assertTrue(refresh.needed)
        self.assertEqual(refresh.kind, "auto")

    def test_no_knowledge_change_not_needed(self) -> None:
        runner = make_runner(["AGENTS.md"])
        result = check_session(self.root, run_command=runner)
        refresh = [a for a in result.actions if a.name == "mindgraph-refresh"][0]
        self.assertFalse(refresh.needed)

    def test_missing_state_md(self) -> None:
        (self.root / "STATE.md").unlink()
        runner = make_runner([])
        result = check_session(self.root, run_command=runner)
        warn = [a for a in result.actions if a.name == "state-md"][0]
        self.assertEqual(warn.kind, "warn")
        self.assertTrue(warn.needed)

    def test_telemetry_available(self) -> None:
        events_dir = self.root / "20_live" / "workflow-metrics" / "events"
        events_dir.mkdir(parents=True)
        today = date.today().isoformat()
        (events_dir / f"{today}.jsonl").write_text("{}\n", encoding="utf-8")

        runner = make_runner([])
        result = check_session(self.root, run_command=runner)
        report = [a for a in result.actions if a.name == "workflow-report"][0]
        self.assertTrue(report.needed)
        self.assertEqual(report.kind, "auto")

    def test_no_telemetry(self) -> None:
        runner = make_runner([])
        result = check_session(self.root, run_command=runner)
        report = [a for a in result.actions if a.name == "workflow-report"][0]
        self.assertFalse(report.needed)

    def test_apply_runs_sync_project_index(self) -> None:
        runner = make_runner(["30_projects/foo/README.md"])
        result = check_session(self.root, run_command=runner, apply=True)
        sync = [a for a in result.actions if a.name == "sync-project-index"][0]
        self.assertTrue(sync.ran)
        self.assertTrue(sync.success)

    def test_apply_runs_mindgraph_refresh(self) -> None:
        runner = make_runner(["10_knowledge/ai-systems/note.md"])
        result = check_session(self.root, run_command=runner, apply=True)
        refresh = [a for a in result.actions if a.name == "mindgraph-refresh"][0]
        self.assertTrue(refresh.ran)
        self.assertTrue(refresh.success)

    def test_apply_reports_failure(self) -> None:
        runner = make_runner(
            ["30_projects/foo/README.md"],
            fail_commands={"sync-project-index"},
        )
        result = check_session(self.root, run_command=runner, apply=True)
        sync = [a for a in result.actions if a.name == "sync-project-index"][0]
        self.assertTrue(sync.ran)
        self.assertFalse(sync.success)
        self.assertFalse(result.ok)

    def test_manual_reminders_always_present(self) -> None:
        runner = make_runner([])
        result = check_session(self.root, run_command=runner)
        manual = [a for a in result.actions if a.kind == "manual"]
        names = {a.name for a in manual}
        self.assertIn("state-md-narrative", names)
        self.assertIn("decisions-review", names)

    def test_dirty_tree_warning(self) -> None:
        runner = make_runner(["AGENTS.md", "STATE.md", "README.md"])
        result = check_session(self.root, run_command=runner)
        warn = [a for a in result.actions if a.name == "working-tree"][0]
        self.assertEqual(warn.kind, "warn")
        self.assertIn("changed file(s)", warn.reason)

    def test_check_not_needed_returns_ok(self) -> None:
        runner = make_runner([])
        result = check_session(self.root, run_command=runner)
        self.assertTrue(result.ok)
        auto_pending = [a for a in result.actions
                        if a.kind == "auto" and a.needed and not a.ran]
        self.assertEqual(len(auto_pending), 0)


if __name__ == "__main__":
    unittest.main()
