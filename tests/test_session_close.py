from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
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

        if "sync-project-index" in cmd_str and "--check" in cmd_str:
            project_meta_changed = any(
                f.startswith("30_projects/") and f.endswith("/README.md")
                for f in changed
            )
            return subprocess.CompletedProcess(cmd, 1 if project_meta_changed else 0, "", "")

        if "eval-schedule" in cmd_str and "check" in cmd_str:
            return subprocess.CompletedProcess(cmd, 0, "eval-schedule check: OK\n", "")

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
                       if a.kind == "auto" and a.needed and a.name != "handoff-digest"]
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

    def test_eval_schedule_check_always_considered(self) -> None:
        runner = make_runner([])
        result = check_session(self.root, run_command=runner)
        names = [a.name for a in result.actions]
        self.assertIn("eval-schedule", names)
        ev = [a for a in result.actions if a.name == "eval-schedule"][0]
        self.assertEqual(ev.kind, "warn")

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
                        if a.kind == "auto" and a.needed and not a.ran and a.name != "handoff-digest"]
        self.assertEqual(len(auto_pending), 0)


class CheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "STATE.md").write_text(STATE_MD, encoding="utf-8")
        (self.root / "20_live").mkdir()
        projects = self.root / "30_projects"
        (projects / "foo").mkdir(parents=True)
        (projects / "foo" / "notes.md").write_text("recent\n", encoding="utf-8")
        (projects / "old-proj").mkdir()
        old_file = projects / "old-proj" / "stale.md"
        old_file.write_text("old\n", encoding="utf-8")
        old_ts = (datetime.now() - timedelta(days=30)).timestamp()
        os.utime(old_file, (old_ts, old_ts))
        os.utime(projects / "old-proj", (old_ts, old_ts))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def draft_path(self) -> Path:
        return self.root / "20_live" / "last-handoff-draft.md"

    def feed_path(self) -> Path:
        return self.root / "20_live" / "workstation" / "session-close-feed.jsonl"

    def test_checkpoint_creates_draft_and_feed(self) -> None:
        hook = {"session_hash": "abc123", "hook_event_name": "PreCompact",
                "trigger": "auto"}
        record, draft = mod.run_checkpoint(
            self.root, run_command=make_runner([]), hook=hook)
        text = draft.read_text(encoding="utf-8")
        self.assertIn(mod.CHECKPOINT_HEADING, text)
        self.assertIn("foo (files", text)
        self.assertIn("PreCompact (auto)", text)
        self.assertEqual(record["kind"], "checkpoint")
        lines = self.feed_path().read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        feed_record = json.loads(lines[0])
        self.assertEqual(feed_record["kind"], "checkpoint")
        self.assertEqual(feed_record["session_hash"], "abc123")
        self.assertEqual(feed_record["source"], "PreCompact")

    def test_derive_orders_and_windows(self) -> None:
        derived = mod.derive_active_projects(self.root, make_runner([]))
        self.assertEqual([d["project"] for d in derived], ["foo"])

    def test_drift_flag(self) -> None:
        record = mod.build_checkpoint(self.root, make_runner([]))
        self.assertTrue(record["drift"])
        match_dir = self.root / "30_projects" / "test-project"
        match_dir.mkdir()
        (match_dir / "work.md").write_text("hot\n", encoding="utf-8")
        record = mod.build_checkpoint(self.root, make_runner([]))
        self.assertFalse(record["drift"])

    def test_snapshot_cap(self) -> None:
        for _ in range(mod.SNAPSHOT_CAP + 2):
            mod.run_checkpoint(self.root, run_command=make_runner([]))
        text = self.draft_path().read_text(encoding="utf-8")
        self.assertEqual(text.count("\n### "), mod.SNAPSHOT_CAP)
        self.assertEqual(text.count("\nDerived active: "), 1)

    def test_checkpoint_preserves_digest_scaffold(self) -> None:
        self.draft_path().write_text(
            "# Session Handoff Draft (auto-generated)\n\n"
            "Ingest status: XYZ-sentinel\n",
            encoding="utf-8",
        )
        mod.run_checkpoint(self.root, run_command=make_runner([]))
        text = self.draft_path().read_text(encoding="utf-8")
        self.assertIn("Ingest status: XYZ-sentinel", text)
        self.assertLess(text.index("XYZ-sentinel"),
                        text.index(mod.CHECKPOINT_HEADING))

    def test_digest_rewrite_preserves_checkpoints(self) -> None:
        (self.root / "bin").mkdir()
        mod.run_checkpoint(self.root, run_command=make_runner([]))
        result = check_session(self.root, run_command=make_runner([]), apply=True)
        digest = [a for a in result.actions if a.name == "handoff-digest"][0]
        self.assertTrue(digest.success)
        text = self.draft_path().read_text(encoding="utf-8")
        self.assertIn(mod.CHECKPOINT_HEADING, text)
        self.assertEqual(text.count("\n### "), 1)
        self.assertIn("## What changed / remains / blockers / next", text)

    def test_check_feed_record_shape(self) -> None:
        result = check_session(self.root, run_command=make_runner(["AGENTS.md"]))
        hook = {"session_hash": "xyz", "hook_event_name": "SessionEnd",
                "reason": "logout"}
        record = mod.check_feed_record(result, hook, "close-check")
        self.assertEqual(record["kind"], "close-check")
        self.assertEqual(record["source"], "SessionEnd")
        self.assertEqual(record["reason"], "logout")
        self.assertIn("working-tree", record["warnings"])
        self.assertIn("handoff-digest", record["pending_auto"])
        self.assertFalse(record["ok"])
        names = [a["name"] for a in record["actions"]]
        self.assertIn("state-md-narrative", names)
        feed = mod.append_feed(self.root, record)
        parsed = json.loads(feed.read_text(encoding="utf-8").strip())
        self.assertEqual(parsed["kind"], "close-check")

    def test_parse_hook_stdin(self) -> None:
        payload = json.dumps({
            "session_id": "abc",
            "hook_event_name": "PreCompact",
            "trigger": "auto",
            "prompt": "verbatim content must never be copied",
        })
        hook = mod.parse_hook_stdin(payload)
        expected = hashlib.sha256(b"abc").hexdigest()[:16]
        self.assertEqual(hook["session_hash"], expected)
        self.assertEqual(hook["hook_event_name"], "PreCompact")
        self.assertEqual(hook["trigger"], "auto")
        self.assertNotIn("prompt", hook)
        self.assertNotIn("session_id", hook)
        self.assertEqual(mod.parse_hook_stdin("not json"), {})
        self.assertEqual(mod.parse_hook_stdin(""), {})

    def test_eval_weekly_status_staleness(self) -> None:
        runs_path = self.root / "20_live" / "eval-registry" / "schedule-runs.jsonl"
        runs_path.parent.mkdir(parents=True)
        stale_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        runs_path.write_text(json.dumps({
            "run_id": "old-weekly", "cadence": "weekly",
            "finished_at": stale_ts, "all_passed": True,
        }) + "\n", encoding="utf-8")
        status = mod.eval_weekly_status(self.root)
        self.assertTrue(status["stale"])
        fresh_ts = datetime.now(timezone.utc).isoformat()
        with runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "run_id": "fresh-weekly", "cadence": "weekly",
                "finished_at": fresh_ts, "all_passed": True,
            }) + "\n")
        status = mod.eval_weekly_status(self.root)
        self.assertFalse(status["stale"])
        self.assertEqual(status["run_id"], "fresh-weekly")


if __name__ == "__main__":
    unittest.main()
