from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from io import StringIO
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
EVENT_PATH = ROOT / "bin" / "workflow-event"
# workflow-event has no .py suffix, so spec_from_file_location refuses to
# infer a loader. Use SourceFileLoader explicitly.
LOADER = SourceFileLoader("workflow_event", str(EVENT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
workflow_event = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = workflow_event
SPEC.loader.exec_module(workflow_event)


class CommandHeadRedactionTests(unittest.TestCase):
    """The command_head field must never carry a filesystem basename.

    A leak surfaced during the initial publish-readiness review: when a
    Bash invocation began with an env assignment like ``SANDBOX=/tmp/foo``
    the old logic took ``Path(...).name`` of that token and wrote ``foo``
    into telemetry. These tests pin the post-fix behaviour.
    """

    def test_plain_command_keeps_bare_name(self) -> None:
        self.assertEqual(workflow_event.command_head("git status"), "git")
        self.assertEqual(workflow_event.command_head("python3 -m unittest"), "python3")
        self.assertEqual(workflow_event.command_head("ls"), "ls")

    def test_env_assignment_prefix_is_skipped(self) -> None:
        self.assertEqual(
            workflow_event.command_head("SANDBOX=/tmp/secret-project python3 run.py"),
            "python3",
        )
        self.assertEqual(
            workflow_event.command_head("FOO=bar BAZ=qux make build"),
            "make",
        )

    def test_path_shaped_head_collapses(self) -> None:
        self.assertEqual(
            workflow_event.command_head("/Users/admin/secret/run.sh --flag"),
            "<path>",
        )
        self.assertEqual(workflow_event.command_head("./bin/private-helper"), "<path>")

    def test_only_env_assignments_returns_none(self) -> None:
        self.assertIsNone(workflow_event.command_head("FOO=bar"))

    def test_empty_command_returns_none(self) -> None:
        self.assertIsNone(workflow_event.command_head(""))

    def test_safe_head_punctuation_is_preserved(self) -> None:
        self.assertEqual(workflow_event.command_head("python3.14 -V"), "python3.14")
        self.assertEqual(workflow_event.command_head("npm install"), "npm")


class BashSummaryTests(unittest.TestCase):
    def test_bash_summary_hashes_full_command(self) -> None:
        summary = workflow_event.bash_summary(
            {"command": "SANDBOX=/tmp/x python3 run.py", "timeout": 60}
        )
        self.assertEqual(summary["command_head"], "python3")
        self.assertEqual(summary["timeout"], 60)
        self.assertIsNotNone(summary["command_hash"])
        # The hash is deterministic for the same input.
        again = workflow_event.bash_summary(
            {"command": "SANDBOX=/tmp/x python3 run.py", "timeout": 60}
        )
        self.assertEqual(summary["command_hash"], again["command_hash"])

    def test_bash_summary_handles_empty_command(self) -> None:
        summary = workflow_event.bash_summary({})
        self.assertIsNone(summary["command_head"])
        self.assertIsNone(summary["command_hash"])


class PathClassTests(unittest.TestCase):
    def test_path_inside_repo_zone(self) -> None:
        cls = workflow_event.path_class(str(ROOT / "10_knowledge" / "index.md"))
        self.assertEqual(cls["path_zone"], "10_knowledge")
        self.assertEqual(cls["extension"], ".md")

    def test_path_outside_repo_marked_external(self) -> None:
        cls = workflow_event.path_class("/etc/hosts")
        self.assertEqual(cls["path_zone"], "external")


class WriteEventTests(unittest.TestCase):
    """End-to-end: stdin JSON -> redacted JSONL on disk."""

    def test_writes_redacted_event(self) -> None:
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "SANDBOX=/tmp/fixture python3 minion.py --root /tmp/fixture",
            },
            "tool_use_id": "abc123",
            "session_id": "session-xyz",
            "duration_ms": 42,
            "cwd": str(ROOT),
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = {"WORKFLOW_METRICS_DIR": tmp}
            with mock.patch.dict("os.environ", env, clear=False):
                with mock.patch.object(sys, "stdin", StringIO(json.dumps(payload))):
                    rc = workflow_event.main()
            self.assertEqual(rc, 0)
            files = list(Path(tmp).glob("*.jsonl"))
            self.assertEqual(len(files), 1)
            line = files[0].read_text(encoding="utf-8").strip()
            record = json.loads(line)
        self.assertEqual(record["tool_name"], "Bash")
        self.assertEqual(record["input_summary"]["command_head"], "python3")
        self.assertNotIn("fixture", line, "basename leaked into telemetry line")
        self.assertNotIn("/tmp/fixture", line, "raw path leaked into telemetry line")
        self.assertTrue(record["success"])


if __name__ == "__main__":
    unittest.main()
