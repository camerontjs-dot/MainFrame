from __future__ import annotations

import importlib.util
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WATCHER_PATH = ROOT / "bin" / "aider-watcher"
LOADER = SourceFileLoader("aider_watcher", str(WATCHER_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
aider_watcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aider_watcher)


class AiderWatcherParserTests(unittest.TestCase):
    def parse(self, text: str) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        path = ROOT / "30_projects" / "example" / ".aider.chat.history.md"
        state = aider_watcher.new_state()
        aider_watcher.process_bytes(
            text.encode(),
            path,
            state,
            events.append,
            final=True,
        )
        aider_watcher.end_session(path, state, events.append, "test_eof")
        return events

    def test_one_start_per_session_and_next_session_closes_previous(self) -> None:
        events = self.parse(
            """
# aider chat started at 2026-06-13 10:00:00
> Model: ollama_chat/qwen2.5-coder:14b with diff edit format
#### Fix one warning.
# aider chat started at 2026-06-13 10:01:00
> Model: ollama_chat/qwen2.5-coder:14b with diff edit format
#### Fix the second warning.
"""
        )
        names = [event["hook_event_name"] for event in events]
        self.assertEqual(names.count("SessionStart"), 2)
        self.assertEqual(names.count("UserPromptSubmit"), 2)
        self.assertEqual(names.count("SessionEnd"), 2)
        session_ids = {
            event["session_id"]
            for event in events
            if event["hook_event_name"] == "SessionStart"
        }
        self.assertEqual(len(session_ids), 2)

    def test_records_coarse_diagnostics_without_model_output(self) -> None:
        transcript = """
# aider chat started at 2026-06-13 10:00:00
> Model: ollama_chat/qwen2.5-coder:14b with diff edit format
> Your estimated chat context of 47,226 tokens exceeds the 24,576 token limit!
> The LLM did not conform to the edit format.
> # 1 SEARCH/REPLACE block failed to match!
"""
        events = self.parse(transcript)
        diagnostics = [
            event["diagnostic"]
            for event in events
            if event["hook_event_name"] == "Diagnostic"
        ]
        self.assertEqual(
            diagnostics,
            ["context_limit_exceeded", "edit_format_failure"],
        )
        self.assertNotIn("47,226", repr(events))

    def test_denied_shell_command_is_not_recorded_as_execution(self) -> None:
        events = self.parse(
            """
# aider chat started at 2026-06-13 10:00:00
> Model: ollama_chat/qwen2.5-coder:14b with diff edit format
> git am ../private.patch
> Run shell commands? (Y)es/(N)o [Yes]: n
"""
        )
        self.assertFalse(
            any(event.get("tool_name") == "Bash" for event in events)
        )
        self.assertTrue(
            any(
                event.get("diagnostic") == "shell_command_denied"
                for event in events
            )
        )

    def test_applied_edits_and_direct_tests_are_observed(self) -> None:
        events = self.parse(
            """
# aider chat started at 2026-06-13 10:00:00
> Model: ollama_chat/qwen2.5-coder:14b with diff edit format
# The other 2 SEARCH/REPLACE blocks were applied successfully.
/run pytest -q
"""
        )
        edit = next(event for event in events if event.get("tool_name") == "Edit")
        test = next(event for event in events if event.get("tool_name") == "Bash")
        self.assertEqual(edit["observed_count"], 2)
        self.assertEqual(test["tool_purpose"], "verification")

    def test_only_verification_shaped_package_commands_are_marked(self) -> None:
        self.assertFalse(aider_watcher.is_test_command("npm install"))
        self.assertTrue(aider_watcher.is_test_command("npm test"))
        self.assertTrue(
            aider_watcher.is_test_command("python3 -m unittest discover")
        )


class AiderWatcherFileTests(unittest.TestCase):
    def test_new_history_can_be_read_from_the_beginning(self) -> None:
        events: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".aider.chat.history.md"
            path.write_text(
                "# aider chat started at 2026-06-13 10:00:00\n"
                "> Model: local/model with diff edit format\n",
                encoding="utf-8",
            )
            state = aider_watcher.new_state()
            aider_watcher.read_growth(path, state, events.append, final=True)

        self.assertEqual(
            [event["hook_event_name"] for event in events],
            ["SessionStart"],
        )

    def test_existing_history_offset_does_not_replay_old_content(self) -> None:
        events: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".aider.chat.history.md"
            path.write_text(
                "# aider chat started at 2026-06-13 10:00:00\n",
                encoding="utf-8",
            )
            state = aider_watcher.new_state(size=path.stat().st_size)
            aider_watcher.read_growth(path, state, events.append)

        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
