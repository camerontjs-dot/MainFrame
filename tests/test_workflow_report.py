from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "bin" / "workflow-report"
LOADER = SourceFileLoader("workflow_report", str(REPORT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
workflow_report = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = workflow_report
SPEC.loader.exec_module(workflow_report)


class WorkflowReportTests(unittest.TestCase):
    def test_build_summary_reports_coverage_and_pairing(self) -> None:
        events = [
            {
                "event": "SessionStart",
                "session_hash": "a",
                "client": "codex",
            },
            {
                "event": "PreToolUse",
                "session_hash": "a",
                "client": "codex",
                "tool_name": "Bash",
            },
            {
                "event": "PostToolUse",
                "session_hash": "a",
                "client": "codex",
                "tool_name": "Bash",
                "success": True,
                "duration_ms": 20,
            },
            {
                "event": "SessionEnd",
                "session_hash": "a",
                "client": "codex",
            },
            {
                "event": "Diagnostic",
                "session_hash": "a",
                "client": "codex",
                "diagnostic": "context_limit_exceeded",
            },
            {
                "event": "SessionStart",
                "session_hash": "b",
                "client": None,
            },
            {
                "event": "PreToolUse",
                "session_hash": "b",
                "client": None,
                "tool_name": "Read",
            },
        ]

        summary = workflow_report.build_summary(events, days=7)
        quality = summary["telemetry_quality"]

        self.assertEqual(summary["events"], 7)
        self.assertEqual(summary["sessions"], 2)
        self.assertEqual(summary["tool_failures"], 0)
        self.assertEqual(quality["client_tagged_events"], 5)
        self.assertEqual(quality["duration_coverage_pct"], 100.0)
        self.assertEqual(quality["session_close_coverage_pct"], 50.0)
        self.assertEqual(quality["unbalanced_tool_sessions"], 1)
        self.assertEqual(quality["unmatched_pre_tool_events"], 1)
        self.assertEqual(
            summary["diagnostics"],
            [{"name": "context_limit_exceeded", "count": 1}],
        )

    def test_build_summary_segments_quality_by_client(self) -> None:
        events = [
            {"event": "SessionStart", "session_hash": "a", "client": "codex"},
            {
                "event": "PreToolUse",
                "session_hash": "a",
                "client": "codex",
                "tool_name": "Bash",
            },
            {
                "event": "PostToolUse",
                "session_hash": "a",
                "client": "codex",
                "tool_name": "Bash",
                "success": False,
                "duration_ms": 12,
            },
            {"event": "SessionStart", "session_hash": "b", "client": "claude"},
            {
                "event": "PostToolUse",
                "session_hash": "b",
                "client": "claude",
                "tool_name": "Read",
                "success": True,
            },
            {"event": "SessionEnd", "session_hash": "b", "client": "claude"},
        ]

        summary = workflow_report.build_summary(events, days=7)
        by_client = {
            item["name"]: item
            for item in summary["telemetry_quality"]["by_client"]
        }

        self.assertEqual(set(by_client), {"codex", "claude"})

        codex = by_client["codex"]
        self.assertEqual(codex["events"], 3)
        self.assertEqual(codex["sessions"], 1)
        self.assertEqual(codex["sessions_with_start"], 1)
        self.assertEqual(codex["sessions_with_end"], 0)
        self.assertEqual(codex["session_close_coverage_pct"], 0.0)
        self.assertEqual(codex["duration_coverage_pct"], 100.0)
        self.assertEqual(codex["tool_failures"], 1)
        self.assertEqual(
            codex["event_types"],
            ["PostToolUse", "PreToolUse", "SessionStart"],
        )

        claude = by_client["claude"]
        self.assertEqual(claude["session_close_coverage_pct"], 100.0)
        self.assertEqual(claude["duration_coverage_pct"], 0.0)
        self.assertEqual(claude["tool_failures"], 0)

        # Per-client list is sorted by event volume, descending.
        names = [
            item["name"]
            for item in summary["telemetry_quality"]["by_client"]
        ]
        self.assertEqual(names, ["codex", "claude"])

    def test_load_events_skips_malformed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            path = log_dir / "2099-01-01.jsonl"
            path.write_text(
                json.dumps({"event": "SessionStart"}) + "\nnot-json\n",
                encoding="utf-8",
            )
            events = workflow_report.load_events(log_dir, days=30000)

        self.assertEqual(events, [{"event": "SessionStart"}])

    def test_empty_summary_has_no_division_errors(self) -> None:
        summary = workflow_report.build_summary([], days=1)
        quality = summary["telemetry_quality"]

        self.assertEqual(summary["events"], 0)
        self.assertIsNone(quality["client_tag_coverage_pct"])
        self.assertIsNone(quality["duration_coverage_pct"])
        self.assertIsNone(quality["session_close_coverage_pct"])
        self.assertEqual(quality["by_client"], [])

    def test_aider_outcomes_do_not_count_as_pairing_defects(self) -> None:
        summary = workflow_report.build_summary(
            [
                {
                    "event": "PostToolUse",
                    "session_hash": "a",
                    "client": "local",
                    "source": "aider",
                    "tool_name": "Edit",
                    "success": True,
                }
            ],
            days=1,
        )
        quality = summary["telemetry_quality"]
        self.assertEqual(quality["unmatched_outcome_events"], 0)
        self.assertEqual(quality["outcome_only_source_events"], 1)

    def test_process_rollup_is_opt_in(self) -> None:
        events = [
            {
                "event": "PostToolUse",
                "session_hash": "a",
                "client": "codex",
                "tool_name": "Bash",
                "success": True,
                "process_id": "cli-workflow-report",
            }
        ]

        default_summary = workflow_report.build_summary(events, days=1)
        self.assertNotIn("processes", default_summary)
        self.assertEqual(
            default_summary["telemetry_quality"]["process_tag_coverage_pct"],
            100.0,
        )

        process_summary = workflow_report.build_summary(
            events,
            days=1,
            by_process=True,
        )
        self.assertEqual(
            process_summary["processes"],
            [
                {
                    "process_id": "cli-workflow-report",
                    "events": 1,
                    "sessions": 1,
                    "tool_failures": 0,
                    "event_types": ["PostToolUse"],
                    "clients": [{"name": "codex", "count": 1}],
                }
            ],
        )

    def test_process_rollup_counts_multi_process_events_once_per_process(self) -> None:
        summary = workflow_report.build_summary(
            [
                {
                    "event": "PostToolUse",
                    "session_hash": "a",
                    "client": "codex",
                    "success": False,
                    "process_ids": [
                        "cli-workflow-event",
                        "workflow-workflow-telemetry",
                    ],
                }
            ],
            days=1,
            by_process=True,
        )
        by_process = {
            item["process_id"]: item
            for item in summary["processes"]
        }

        self.assertEqual(
            set(by_process),
            {"cli-workflow-event", "workflow-workflow-telemetry"},
        )
        self.assertEqual(by_process["cli-workflow-event"]["tool_failures"], 1)
        self.assertEqual(by_process["workflow-workflow-telemetry"]["events"], 1)

    def test_process_rollup_ignores_unsafe_process_ids(self) -> None:
        summary = workflow_report.build_summary(
            [
                {
                    "event": "PostToolUse",
                    "session_hash": "a",
                    "client": "codex",
                    "process_ids": [
                        "cli-workflow-report",
                        "/tmp/example-mainframe/bin/workflow-report",
                        "ran private command",
                        "client-name-sensitive-case",
                    ],
                }
            ],
            days=1,
            by_process=True,
        )

        self.assertEqual(
            summary["processes"],
            [
                {
                    "process_id": "cli-workflow-report",
                    "events": 1,
                    "sessions": 1,
                    "tool_failures": 0,
                    "event_types": ["PostToolUse"],
                    "clients": [{"name": "codex", "count": 1}],
                }
            ],
        )

    def test_input_signals_are_opt_in_aggregate_counts(self) -> None:
        events = [
            {
                "event": "PreToolUse",
                "tool_name": "Bash",
                "input_summary": {
                    "command_head": "git",
                    "command_hash": "not-reported",
                },
            },
            {
                "event": "PreToolUse",
                "tool_name": "Read",
                "input_summary": {
                    "path_zone": "30_projects",
                    "extension": ".md",
                },
            },
            {
                "event": "PreToolUse",
                "tool_name": "Read",
                "input_summary": {
                    "path_zone": "30_projects",
                    "extension": ".py",
                },
            },
            {
                "event": "PreToolUse",
                "tool_name": "Other",
                "input_summary": {
                    "input_hash": "not-reported",
                },
            },
        ]

        default_summary = workflow_report.build_summary(events, days=1)
        self.assertNotIn("input_signals", default_summary)

        summary = workflow_report.build_summary(
            events,
            days=1,
            input_signals=True,
        )

        self.assertEqual(
            summary["input_signals"],
            {
                "redacted_input_events": 4,
                "command_heads": [{"name": "git", "count": 1}],
                "path_zones": [{"name": "30_projects", "count": 2}],
                "file_extensions": [
                    {"name": ".md", "count": 1},
                    {"name": ".py", "count": 1},
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
