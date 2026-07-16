from __future__ import annotations

from datetime import datetime
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
            workflow_event.command_head("/opt/tools/run.sh --flag"),
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

    def test_bash_summary_handles_codex_cmd_field(self) -> None:
        summary = workflow_event.bash_summary({"cmd": "git status --short"})
        self.assertEqual(summary["command_head"], "git")
        self.assertIsNotNone(summary["command_hash"])

    def test_grok_terminal_tool_uses_redacted_command_summary(self) -> None:
        summary = workflow_event.input_summary(
            "run_terminal_command",
            {"command": "PRIVATE=/tmp/path npm test"},
        )
        self.assertEqual(summary["command_head"], "npm")
        self.assertNotIn("/tmp/path", json.dumps(summary))


class ProcessIdTests(unittest.TestCase):
    def test_process_ids_keep_catalogue_shaped_values(self) -> None:
        ids = workflow_event.process_ids(
            {
                "process_id": "cli-workflow-report",
                "process_ids": ["workflow-workflow-telemetry", "cli-workflow-report"],
            }
        )
        self.assertEqual(
            ids,
            ["cli-workflow-report", "workflow-workflow-telemetry"],
        )

    def test_process_ids_reject_paths_and_free_text(self) -> None:
        ids = workflow_event.process_ids(
            {
                "process_id": "/tmp/example-mainframe/bin/workflow-report",
                "catalogue_id": "ran private command",
                "catalogue_ids": ["client-name-sensitive-case"],
            }
        )
        self.assertEqual(ids, [])

    def test_process_ids_keep_only_catalogue_prefixes(self) -> None:
        ids = workflow_event.process_ids(
            {
                "process_ids": [
                    "cli-workflow-report",
                    "workflow-workflow-telemetry",
                    "skill-source-literature",
                    "agent-ingest-agent",
                    "script-eval-schedule-implementation",
                    "ingest-minion-module",
                    "private-case-slug",
                ],
            }
        )
        self.assertEqual(
            ids,
            [
                "cli-workflow-report",
                "workflow-workflow-telemetry",
                "skill-source-literature",
                "agent-ingest-agent",
                "script-eval-schedule-implementation",
                "ingest-minion-module",
            ],
        )

    def test_process_ids_can_come_from_environment(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {"MAINFRAME_PROCESS_ID": "cli-workflow-event,workflow-workflow-telemetry"},
            clear=False,
        ):
            ids = workflow_event.process_ids({})
        self.assertEqual(
            ids,
            ["cli-workflow-event", "workflow-workflow-telemetry"],
        )


class PathClassTests(unittest.TestCase):
    def test_path_inside_repo_zone(self) -> None:
        cls = workflow_event.path_class(str(ROOT / "10_knowledge" / "index.md"))
        self.assertEqual(cls["path_zone"], "10_knowledge")
        self.assertEqual(cls["extension"], ".md")

    def test_path_outside_repo_marked_external(self) -> None:
        cls = workflow_event.path_class("/etc/hosts")
        self.assertEqual(cls["path_zone"], "external")


class ResponseSuccessTests(unittest.TestCase):
    """Codex reports tool outcomes inside PostToolUse's tool_response."""

    def test_exit_code_zero_is_success(self) -> None:
        self.assertTrue(workflow_event.response_success({"exit_code": 0}))

    def test_nonzero_exit_code_is_failure(self) -> None:
        self.assertFalse(workflow_event.response_success({"exit_code": 2}))
        self.assertFalse(workflow_event.response_success({"returncode": 1}))

    def test_exit_code_nested_in_metadata(self) -> None:
        self.assertFalse(
            workflow_event.response_success({"metadata": {"exitCode": 3}})
        )

    def test_explicit_success_flag(self) -> None:
        self.assertFalse(workflow_event.response_success({"success": False}))
        self.assertTrue(workflow_event.response_success({"success": True}))

    def test_bool_exit_code_is_not_an_exit_code(self) -> None:
        # True is an int in Python; it must not be read as exit code 1.
        self.assertIsNone(workflow_event.response_success({"exit_code": True}))

    def test_unrecognized_shapes_return_none(self) -> None:
        self.assertIsNone(workflow_event.response_success("plain output"))
        self.assertIsNone(workflow_event.response_success(None))
        self.assertIsNone(workflow_event.response_success({"output": "ok"}))


class HookPayloadNormalizationTests(unittest.TestCase):
    def test_grok_camel_case_payload_is_normalized(self) -> None:
        normalized = workflow_event.normalize_hook_payload(
            {
                "hookEventName": "pre_tool_use",
                "sessionId": "grok-session",
                "workspaceRoot": str(ROOT),
                "toolName": "run_terminal_command",
                "toolInput": {"command": "python3 -m unittest"},
                "toolUseId": "tool-1",
                "modelId": "grok-build",
            }
        )

        self.assertEqual(normalized["hook_event_name"], "PreToolUse")
        self.assertEqual(normalized["session_id"], "grok-session")
        self.assertEqual(normalized["cwd"], str(ROOT))
        self.assertEqual(normalized["tool_name"], "run_terminal_command")
        self.assertEqual(normalized["tool_input"]["command"], "python3 -m unittest")
        self.assertEqual(normalized["tool_use_id"], "tool-1")
        self.assertEqual(normalized["model"], "grok-build")

    def test_grok_event_aliases_cover_session_and_failure_events(self) -> None:
        self.assertEqual(
            workflow_event.normalize_hook_payload(
                {"hookEventName": "session_start"}
            )["hook_event_name"],
            "SessionStart",
        )
        self.assertEqual(
            workflow_event.normalize_hook_payload(
                {"hookEventName": "post_tool_use_failure"}
            )["hook_event_name"],
            "PostToolUseFailure",
        )
        self.assertEqual(
            workflow_event.normalize_hook_payload(
                {"hookEventName": "session_end"}
            )["hook_event_name"],
            "SessionEnd",
        )


class SafeEventNewSignalsTests(unittest.TestCase):
    def test_permission_request_sets_permission_kind(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "PermissionRequest",
                "tool_name": "Bash",
                "tool_input": {"command": "rm -rf build"},
                "session_id": "s1",
            },
            client="codex",
        )
        self.assertEqual(event["notification_kind"], "permission")
        self.assertNotIn("rm -rf", json.dumps(event))

    def test_post_tool_use_derives_failure_from_response(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "make test"},
                "tool_response": {"exit_code": 1},
                "session_id": "s1",
            },
            client="codex",
        )
        self.assertFalse(event["success"])

    def test_post_tool_use_without_outcome_stays_success(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "README.md"},
                "tool_response": "text",
                "session_id": "s1",
            },
            client="claude",
        )
        self.assertTrue(event["success"])

    def test_post_tool_use_failure_event_stays_failure(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "PostToolUseFailure",
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
                "tool_response": {"exit_code": 0},
                "session_id": "s1",
            },
            client="claude",
        )
        self.assertFalse(event["success"])

    def test_grok_permission_denied_is_blocked(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "PermissionDenied",
                "tool_name": "run_terminal_command",
                "tool_input": {"command": "git push"},
                "session_id": "s1",
            },
            client="grok",
        )
        self.assertFalse(event["success"])

    def test_compact_events_record_trigger_only(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "PreCompact",
                "trigger": "auto",
                "custom_instructions": "keep the secret plan",
                "session_id": "s1",
            },
            client="claude",
        )
        self.assertEqual(event["trigger"], "auto")
        self.assertNotIn("secret plan", json.dumps(event))

    def test_aider_diagnostic_uses_allowlisted_code(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "Diagnostic",
                "diagnostic": "context_limit_exceeded",
                "detail": "private model output",
                "session_id": "s1",
            },
            client="local",
        )
        self.assertEqual(event["diagnostic"], "context_limit_exceeded")
        self.assertNotIn("private model output", json.dumps(event))

    def test_verification_purpose_and_observed_count_are_preserved(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "pytest -q"},
                "tool_purpose": "verification",
                "observed_count": 2,
                "session_id": "s1",
            },
            client="local",
        )
        self.assertEqual(event["tool_purpose"], "verification")
        self.assertEqual(event["observed_count"], 2)

    def test_aider_source_is_preserved_on_tool_events(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "PostToolUse",
                "source": "aider",
                "tool_name": "Edit",
                "session_id": "s1",
            },
            client="local",
        )
        self.assertEqual(event["source"], "aider")

    def test_safe_event_preserves_valid_process_ids_only(self) -> None:
        event = workflow_event.safe_event(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "bin/workflow-report --days 1"},
                "process_ids": [
                    "cli-workflow-report",
                    "/tmp/example-mainframe/bin/workflow-report",
                    "workflow-workflow-telemetry",
                ],
                "session_id": "s1",
            },
            client="codex",
        )
        self.assertEqual(event["process_id"], "cli-workflow-report")
        self.assertEqual(
            event["process_ids"],
            ["cli-workflow-report", "workflow-workflow-telemetry"],
        )
        self.assertNotIn("/tmp/example-user", json.dumps(event))


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

    def test_writes_codex_exec_command_summary(self) -> None:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "functions.exec_command",
            "tool_input": {"cmd": "python3 -m unittest"},
            "tool_use_id": "abc123",
            "session_id": "session-xyz",
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
        self.assertEqual(record["tool_name"], "functions.exec_command")
        self.assertEqual(record["input_summary"]["command_head"], "python3")
        self.assertIsNotNone(record["input_summary"]["command_hash"])

    def test_antigravity_agent_env_override(self) -> None:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "README.md"},
            "session_id": "session-xyz",
            "cwd": str(ROOT),
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = {"WORKFLOW_METRICS_DIR": tmp, "ANTIGRAVITY_AGENT": "1"}
            with mock.patch.dict("os.environ", env, clear=True):
                with mock.patch.object(sys, "stdin", StringIO(json.dumps(payload))):
                    rc = workflow_event.main()
            self.assertEqual(rc, 0)
            files = list(Path(tmp).glob("*.jsonl"))
            self.assertEqual(len(files), 1)
            line = files[0].read_text(encoding="utf-8").strip()
            record = json.loads(line)
        self.assertEqual(record["client"], "antigravity")

    def test_explicit_client_wins_over_parent_inference(self) -> None:
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": "session-xyz",
            "cwd": str(ROOT),
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = {"WORKFLOW_METRICS_DIR": tmp, "ANTIGRAVITY_AGENT": "1"}
            with mock.patch.dict("os.environ", env, clear=True):
                with mock.patch.object(
                    workflow_event,
                    "get_client_override",
                    return_value="antigravity",
                ):
                    with mock.patch.object(
                        sys,
                        "argv",
                        ["workflow-event", "--client", "local"],
                    ):
                        with mock.patch.object(
                            sys, "stdin", StringIO(json.dumps(payload))
                        ):
                            rc = workflow_event.main()
            self.assertEqual(rc, 0)
            record = json.loads(
                next(Path(tmp).glob("*.jsonl")).read_text(encoding="utf-8")
            )
        self.assertEqual(record["client"], "local")

    def test_writes_redacted_grok_hook_event(self) -> None:
        payload = {
            "hookEventName": "pre_tool_use",
            "sessionId": "grok-session",
            "workspaceRoot": str(ROOT),
            "toolName": "run_terminal_command",
            "toolInput": {
                "command": "SECRET=/tmp/private python3 -m unittest",
            },
            "toolUseId": "tool-1",
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = {"WORKFLOW_METRICS_DIR": tmp}
            with mock.patch.dict("os.environ", env, clear=False):
                with mock.patch.object(
                    sys,
                    "argv",
                    ["workflow-event", "--client", "grok"],
                ):
                    with mock.patch.object(
                        sys,
                        "stdin",
                        StringIO(json.dumps(payload)),
                    ):
                        rc = workflow_event.main()

            record = json.loads(
                next(Path(tmp).glob("*.jsonl")).read_text(encoding="utf-8")
            )

        self.assertEqual(rc, 0)
        self.assertEqual(record["client"], "grok")
        self.assertEqual(record["event"], "PreToolUse")
        self.assertEqual(record["input_summary"]["command_head"], "python3")
        self.assertNotIn("/tmp/private", json.dumps(record))


class HooksConfigurationTests(unittest.TestCase):
    def test_grok_hooks_valid_json(self) -> None:
        hooks_path = ROOT / ".grok" / "hooks" / "mainframe-telemetry.json"
        self.assertTrue(hooks_path.exists())
        with hooks_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertIn("SessionStart", data["hooks"])
        self.assertIn("SessionEnd", data["hooks"])
        commands = [
            hook.get("command", "")
            for groups in data["hooks"].values()
            for group in groups
            for hook in group.get("hooks", [])
        ]
        self.assertTrue(
            all("--client grok --pixel main-grok-build" in command for command in commands)
        )

    def test_antigravity_hooks_valid_json(self) -> None:
        hooks_path = ROOT / ".antigravity" / "hooks.json"
        self.assertTrue(hooks_path.exists())
        with hooks_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("hooks", data)
        self.assertIn("SessionEnd", data["hooks"])
        # Verify at least one hook is configured to run workflow-event with --client antigravity
        found = False
        for hook_name, hook_list in data["hooks"].items():
            for group in hook_list:
                for hook in group.get("hooks", []):
                    if "--client antigravity" in hook.get("command", ""):
                        found = True
        self.assertTrue(found, "Did not find '--client antigravity' in any hook command")

    def test_codex_hooks_valid_json(self) -> None:
        hooks_path = ROOT / ".codex" / "hooks.json"
        self.assertTrue(hooks_path.exists())
        with hooks_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("hooks", data)
        self.assertIn("SessionEnd", data["hooks"])
        found = False
        for hook_name, hook_list in data["hooks"].items():
            for group in hook_list:
                for hook in group.get("hooks", []):
                    if "--client codex" in hook.get("command", ""):
                        found = True
        self.assertTrue(found, "Did not find '--client codex' in any hook command")

    def test_antigravity_settings_valid_json(self) -> None:
        settings_path = ROOT / ".antigravity" / "settings.json"
        self.assertTrue(settings_path.exists())
        with settings_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("hooks", data)


class DetectLoopTests(unittest.TestCase):
    def test_detect_loop_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "nonexistent.jsonl"
            res = workflow_event.detect_loop(p, "session-1")
            self.assertEqual(res, {"is_loop": False, "loop_count": 0})

    def test_detect_loop_no_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "telemetry.jsonl"
            events = [
                {"session_hash": "session-1", "success": True, "event": "PostToolUse"},
                {"session_hash": "session-1", "success": True, "event": "PostToolUse"},
            ]
            with p.open("w", encoding="utf-8") as f:
                for ev in events:
                    f.write(json.dumps(ev) + "\n")
            res = workflow_event.detect_loop(p, "session-1")
            self.assertEqual(res, {"is_loop": False, "loop_count": 0})

    def test_detect_loop_with_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "telemetry.jsonl"
            events = [
                {"session_hash": "session-1", "success": True, "event": "PostToolUse"},
                {"session_hash": "session-1", "success": False, "event": "PostToolUse"},
                {"session_hash": "session-1", "success": False, "event": "PostToolUseFailure"},
            ]
            with p.open("w", encoding="utf-8") as f:
                for ev in events:
                    f.write(json.dumps(ev) + "\n")
            res = workflow_event.detect_loop(p, "session-1")
            self.assertEqual(res, {"is_loop": True, "loop_count": 2})


class CalculateDurationTests(unittest.TestCase):
    def test_calculate_duration_no_file(self) -> None:
        p = Path("/nonexistent/file.jsonl")
        res = workflow_event.calculate_duration_from_pre_tool(
            p, "session-1", "tool-1", datetime.now()
        )
        self.assertIsNone(res)

    def test_calculate_duration_no_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "telemetry.jsonl"
            events = [
                {
                    "session_hash": "session-1",
                    "tool_use_hash": "tool-2",
                    "event": "PreToolUse",
                    "logged_at": "2026-06-18T00:00:00-04:00",
                }
            ]
            with p.open("w", encoding="utf-8") as f:
                for ev in events:
                    f.write(json.dumps(ev) + "\n")
            res = workflow_event.calculate_duration_from_pre_tool(
                p,
                "session-1",
                "tool-1",
                datetime.fromisoformat("2026-06-18T00:00:05-04:00"),
            )
            self.assertIsNone(res)

    def test_calculate_duration_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "telemetry.jsonl"
            events = [
                {
                    "session_hash": "session-1",
                    "tool_use_hash": "tool-1",
                    "event": "PreToolUse",
                    "logged_at": "2026-06-18T00:00:00-04:00",
                }
            ]
            with p.open("w", encoding="utf-8") as f:
                for ev in events:
                    f.write(json.dumps(ev) + "\n")
            res = workflow_event.calculate_duration_from_pre_tool(
                p,
                "session-1",
                "tool-1",
                datetime.fromisoformat("2026-06-18T00:00:05-04:00"),
            )
            self.assertEqual(res, 5000)


if __name__ == "__main__":
    unittest.main()
