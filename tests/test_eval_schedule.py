"""Tests for scripts/eval_schedule.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import scripts.eval_schedule as es


class EvalScheduleTests(unittest.TestCase):
    def test_steps_for_daily_excludes_tests_and_probe(self) -> None:
        steps = es.steps_for_cadence(
            "daily", skip_tests=False, skip_probe=False, full_probe=False, run_id="test-run"
        )
        names = [s[0] for s in steps]
        self.assertIn("ingest_minion_dry_run", names)
        self.assertNotIn("unittest_suite", names)
        self.assertNotIn("eval_registry_harvest", names)

    def test_steps_for_weekly_includes_tests_not_mid_harvest(self) -> None:
        steps = es.steps_for_cadence(
            "weekly", skip_tests=False, skip_probe=True, full_probe=False, run_id="test-run"
        )
        names = [s[0] for s in steps]
        self.assertIn("unittest_suite", names)
        self.assertNotIn("eval_registry_harvest", names)
        self.assertNotIn("mindgraph_retrieval_probe", names)

    def test_scheduled_probe_uses_fused_subset(self) -> None:
        steps = es.steps_for_cadence(
            "weekly", skip_tests=True, skip_probe=False, full_probe=False, run_id="2026-06-22T120000-scheduled-weekly"
        )
        probe = next(s for s in steps if s[0] == "mindgraph_retrieval_probe")
        cmd = probe[1] or []
        self.assertIn("--fused-only", cmd)
        self.assertIn("--query-ids", cmd)
        self.assertIn("--registry", cmd)

    def test_live_envelope_uses_mindgraph_uv_env(self) -> None:
        """Live envelope imports PyYAML; bare host python fails (weekly 2026-07-12)."""
        steps = es.steps_for_cadence(
            "weekly",
            skip_tests=True,
            skip_probe=False,
            full_probe=False,
            run_id="2026-07-12T235432-scheduled-weekly",
        )
        step = next(s for s in steps if s[0] == "mindgraph_live_envelope")
        cmd = step[1]
        if cmd is None:
            # uv or mindgraph/ absent in this environment — skip is allowed.
            self.assertIsNotNone(step[2])
            return
        self.assertEqual(cmd[0:4], [cmd[0], "run", "--project", str(es.MINDGRAPH_PROJECT)])
        self.assertIn("uv", Path(cmd[0]).name)
        self.assertEqual(cmd[4], "python")
        self.assertEqual(cmd[5], str(es.MINDGRAPH_LIVE_ENVELOPE))
        self.assertIn("--run-id", cmd)
        self.assertIn("2026-07-12T235432-scheduled-weekly-live-envelope", cmd)

    def test_live_envelope_missing_frozen_snapshot_is_operator_gate(self) -> None:
        with mock.patch.object(
            es, "missing_eval_snapshots", return_value=[Path("/tmp/frozen-mainframe-intent.sqlite")]
        ):
            steps = es.steps_for_cadence(
                "weekly", skip_tests=True, skip_probe=False, full_probe=False, run_id="test-run"
            )
        step = next(s for s in steps if s[0] == "mindgraph_live_envelope")
        self.assertIsNone(step[1])
        self.assertTrue((step[2] or "").startswith("OPERATOR GATE:"))

    def test_failed_step_summary_names_failed_and_operator_gated_steps(self) -> None:
        summary = es.failed_step_summary(
            {"steps": [
                {"name": "ok", "exit_code": 0},
                {"name": "probe", "exit_code": 2},
                {"name": "snapshot", "operator_gated": True, "skipped": True},
            ]}
        )
        self.assertEqual(summary, "probe (exit 2), snapshot (operator gate)")

    def test_mindgraph_uv_python_cmd_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            with mock.patch.object(es.shutil, "which", return_value="/usr/bin/uv"):
                with mock.patch.object(es, "MINDGRAPH_PROJECT", project):
                    cmd = es.mindgraph_uv_python_cmd(
                        Path("/tmp/probe.py"), "--run-id", "rid-1"
                    )
        self.assertEqual(
            cmd,
            [
                "/usr/bin/uv",
                "run",
                "--project",
                str(project),
                "python",
                "/tmp/probe.py",
                "--run-id",
                "rid-1",
            ],
        )

    def test_mindgraph_uv_python_cmd_missing_uv(self) -> None:
        with mock.patch.object(es.shutil, "which", return_value=None):
            self.assertIsNone(
                es.mindgraph_uv_python_cmd(Path("/tmp/probe.py"), "--run-id", "x")
            )

    def test_parse_harvest_stats(self) -> None:
        stats = es.parse_harvest_stats(
            "harvest: projects=5 files_scanned=42 runs_new=1 metrics=4 irregularities=0 skipped=37 errors=2"
        )
        self.assertEqual(stats["errors"], 2)
        self.assertEqual(stats["runs_new"], 1)

    def test_run_step_attaches_process_ids(self) -> None:
        completed = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(es.subprocess, "run", return_value=completed):
            step = es.run_step(
                "workflow_report_7d",
                ["bin/workflow-report", "--days", "7", "--json"],
                cwd=Path("/tmp"),
            )

        self.assertEqual(
            step.process_ids,
            ["cli-workflow-report", "workflow-workflow-telemetry"],
        )

    def test_write_process_eval_output_skips_daily(self) -> None:
        run = es.ScheduleRun(
            run_id="2026-06-22-scheduled-daily",
            cadence="daily",
            started_at="t0",
            finished_at="t1",
            git_sha="abc",
            all_passed=True,
            steps=[es.StepResult("ingest_minion_dry_run", ["bin"], 0, 1.0)],
        )
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(es, "PROCESS_EVAL_OUTPUTS", Path(tmp)):
                out = es.write_process_eval_output(run, dry_run=False)
        self.assertIsNone(out)

    def test_write_process_eval_output_weekly(self) -> None:
        run = es.ScheduleRun(
            run_id="2026-06-22-scheduled-weekly",
            cadence="weekly",
            started_at="t0",
            finished_at="t1",
            git_sha="abc",
            all_passed=True,
            steps=[
                es.StepResult("unittest_suite", ["py"], 0, 2.0),
                es.StepResult("eval_registry_harvest", ["bin"], 0, 0.5),
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(es, "PROCESS_EVAL_OUTPUTS", Path(tmp)):
                out = es.write_process_eval_output(run, dry_run=False)
                self.assertIsNotNone(out)
                text = out.read_text(encoding="utf-8")
                self.assertIn("## Metric extract (eval-registry)", text)
                self.assertIn("scheduled_steps_passed", text)

    def test_append_schedule_log(self) -> None:
        run = es.ScheduleRun(
            run_id="2026-06-22-scheduled-daily",
            cadence="daily",
            started_at="t0",
            finished_at="t1",
            git_sha=None,
            all_passed=True,
            steps=[],
        )
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "schedule-runs.jsonl"
            with mock.patch.object(es, "SCHEDULE_LOG", log), mock.patch.object(es, "REGISTRY_DIR", Path(tmp)):
                es.append_schedule_log(run, dry_run=False)
            lines = log.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["run_id"], run.run_id)

    def test_build_plist_contains_cadence(self) -> None:
        plist = es.build_plist(es.DAEMON_LABEL_WEEKLY, "weekly", Path("/tmp/MainFrame"))
        self.assertIn(es.DAEMON_LABEL_WEEKLY, plist)
        self.assertIn("weekly", plist)
        self.assertIn("StartCalendarInterval", plist)
        self.assertIn("MAINFRAME_EVAL_TRIGGER", plist)
        self.assertIn("launchd", plist)
        self.assertIn("scripts/eval_schedule.py", plist)
        self.assertIn("MAINFRAME_ROOT", plist)
        # WorkingDirectory should not force Desktop chdir
        self.assertIn(str(Path.home()), plist)

    def test_detect_launchd_tcc_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            err = log_dir / "weekly.err"
            err.write_text(
                "bash: /path/to/MainFrame/bin/eval-schedule: Operation not permitted\n",
                encoding="utf-8",
            )
            hits = es.detect_launchd_tcc_blocks(log_dirs=[log_dir])
            self.assertEqual(hits, [str(err)])

    def test_root_needs_full_disk_access(self) -> None:
        self.assertTrue(es.root_needs_full_disk_access(Path("/Users/x/Desktop/MainFrame")))
        self.assertFalse(es.root_needs_full_disk_access(Path("/Users/x/src/MainFrame")))

    def test_assess_schedule_health_stale_weekly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "schedule-runs.jsonl"
            old = {
                "run_id": "old-weekly",
                "cadence": "weekly",
                "finished_at": "2020-01-01T00:00:00+00:00",
                "all_passed": True,
                "trigger": "launchd",
            }
            log.write_text(json.dumps(old) + "\n", encoding="utf-8")
            with mock.patch.object(es, "SCHEDULE_LOG", log):
                with mock.patch.object(es, "plist_path", return_value=Path(tmp) / "missing.plist"):
                    with mock.patch.object(es, "detect_launchd_tcc_blocks", return_value=[]):
                        with mock.patch.object(
                            es, "root_needs_full_disk_access", return_value=False
                        ):
                            health = es.assess_schedule_health(
                                now=datetime(2026, 6, 22, tzinfo=timezone.utc)
                            )
            self.assertFalse(health.ok)
            self.assertTrue(any("stale" in p for p in health.problems))

    def test_assess_schedule_health_ok_when_recent_launchd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "schedule-runs.jsonl"
            recent = {
                "run_id": "new-weekly",
                "cadence": "weekly",
                "finished_at": "2026-06-22T10:00:00+00:00",
                "all_passed": True,
                "trigger": "launchd",
            }
            log.write_text(json.dumps(recent) + "\n", encoding="utf-8")
            weekly_plist = Path(tmp) / "weekly.plist"
            daily_plist = Path(tmp) / "daily.plist"
            weekly_plist.write_text("plist", encoding="utf-8")
            daily_plist.write_text("plist", encoding="utf-8")

            def fake_plist(label: str) -> Path:
                if label == es.DAEMON_LABEL_WEEKLY:
                    return weekly_plist
                return daily_plist

            with mock.patch.object(es, "SCHEDULE_LOG", log):
                with mock.patch.object(es, "plist_path", side_effect=fake_plist):
                    with mock.patch.object(es, "detect_launchd_tcc_blocks", return_value=[]):
                        with mock.patch.object(
                            es, "root_needs_full_disk_access", return_value=False
                        ):
                            health = es.assess_schedule_health(
                                now=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
                            )
            self.assertTrue(health.ok)
            self.assertEqual(health.status_label, "OK")

    def test_assess_schedule_health_degraded_without_launchd_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "schedule-runs.jsonl"
            recent = {
                "run_id": "manual-weekly",
                "cadence": "weekly",
                "finished_at": "2026-06-22T10:00:00+00:00",
                "all_passed": True,
                # no trigger field → treated as missing launchd provenance
            }
            log.write_text(json.dumps(recent) + "\n", encoding="utf-8")
            weekly_plist = Path(tmp) / "weekly.plist"
            daily_plist = Path(tmp) / "daily.plist"
            weekly_plist.write_text("plist", encoding="utf-8")
            daily_plist.write_text("plist", encoding="utf-8")

            def fake_plist(label: str) -> Path:
                if label == es.DAEMON_LABEL_WEEKLY:
                    return weekly_plist
                return daily_plist

            with mock.patch.object(es, "SCHEDULE_LOG", log):
                with mock.patch.object(es, "plist_path", side_effect=fake_plist):
                    with mock.patch.object(es, "detect_launchd_tcc_blocks", return_value=[]):
                        with mock.patch.object(
                            es, "root_needs_full_disk_access", return_value=False
                        ):
                            health = es.assess_schedule_health(
                                now=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
                            )
            self.assertFalse(health.ok)
            self.assertEqual(health.status_label, "DEGRADED")
            self.assertTrue(any("provenance" in d for d in health.degraded))

    def test_assess_schedule_health_tcc_denial_is_problem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "schedule-runs.jsonl"
            recent = {
                "run_id": "new-weekly",
                "cadence": "weekly",
                "finished_at": "2026-06-22T10:00:00+00:00",
                "all_passed": True,
                "trigger": "launchd",
            }
            log.write_text(json.dumps(recent) + "\n", encoding="utf-8")
            weekly_plist = Path(tmp) / "weekly.plist"
            daily_plist = Path(tmp) / "daily.plist"
            weekly_plist.write_text("plist", encoding="utf-8")
            daily_plist.write_text("plist", encoding="utf-8")

            def fake_plist(label: str) -> Path:
                if label == es.DAEMON_LABEL_WEEKLY:
                    return weekly_plist
                return daily_plist

            with mock.patch.object(es, "SCHEDULE_LOG", log):
                with mock.patch.object(es, "plist_path", side_effect=fake_plist):
                    with mock.patch.object(
                        es,
                        "detect_launchd_tcc_blocks",
                        return_value=["/tmp/weekly.err"],
                    ):
                        health = es.assess_schedule_health(
                            now=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
                        )
            self.assertFalse(health.ok)
            self.assertTrue(any("TCC" in p for p in health.problems))


if __name__ == "__main__":
    unittest.main()
