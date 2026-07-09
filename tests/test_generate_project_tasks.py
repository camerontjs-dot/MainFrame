from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "generate-project-tasks"
LOADER = SourceFileLoader("generate_project_tasks", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
generate_tasks = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generate_tasks
SPEC.loader.exec_module(generate_tasks)


class GenerateProjectTasksTests(unittest.TestCase):
    def test_phase_tasks_and_compiled_packets_are_both_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = projects / "demo"
            project.mkdir()
            (project / "README.md").write_text(
                "---\n"
                'title: "Demo"\n'
                'status: "active"\n'
                'project_state: "active"\n'
                'next_action: "Keep going"\n'
                "---\n",
                encoding="utf-8",
            )

            plans_dir = project / "plans"
            plans_dir.mkdir()
            (plans_dir / "phase-1-test.md").write_text(
                "# Phase 1 Test\n\n"
                "status: active\n\n"
                "## Unit Plan\n\n"
                "### Unit 1 — Foundation\n\n"
                "- [ ] Task checkbox item\n",
                encoding="utf-8",
            )

            packet_manifest = projects / "task_packets_manifest.json"
            packet_manifest.write_text(
                json.dumps(
                    {
                        "packets": [
                            {
                                "id": "packet-demo-fix",
                                "task_id": "fix",
                                "project_slug": "demo",
                                "title": "Packet task",
                                "status": "ready",
                                "task_kind": "code",
                                "agent_profile": "local",
                                "goal": "Fix it",
                                "next_action": "Delegate it",
                                "packet_path": "30_projects/demo/plans/task-packets/fix.md",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            tasks = generate_tasks.compile_tasks(projects, packet_manifest)

        self.assertEqual([task["id"] for task in tasks], ["task-demo-phase-1-test-l9", "packet-demo-fix"])

        extracted_phase_task = tasks[0]
        self.assertEqual(extracted_phase_task["status"], "active")
        self.assertEqual(extracted_phase_task["title"], "[Unit 1 — Foundation] Task checkbox item")
        self.assertEqual(extracted_phase_task["mainframe_target"], "30_projects/demo/plans/phase-1-test.md#L9")

        packet = tasks[1]
        self.assertEqual(packet["status"], "active")
        self.assertEqual(packet["mainframe_target"], packet["packet_path"])

    def test_plain_bullets_and_decision_log_lines_are_not_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = projects / "demo"
            project.mkdir()
            (project / "README.md").write_text(
                "---\n"
                'title: "Demo"\n'
                'status: "active"\n'
                "---\n",
                encoding="utf-8",
            )

            plans_dir = project / "plans"
            plans_dir.mkdir()
            adr_blob = "**Promoted 2026-05-12:** ADR-011 (four-state enum " + "x" * 2000 + ")"
            (plans_dir / "master-plan.md").write_text(
                "# Master Plan\n\n"
                "status: active\n\n"
                "## Execution order\n\n"
                f"- {adr_blob}\n"
                "- A plain status note that is not a commitment\n"
                f"- [ ] {adr_blob}\n"
                "- [ ] A real checkbox task\n",
                encoding="utf-8",
            )

            tasks = generate_tasks.compile_tasks(
                projects, projects / "task_packets_manifest.json"
            )

        titles = [task["title"] for task in tasks]
        self.assertEqual(len(tasks), 1)
        self.assertIn("A real checkbox task", titles[0])
        for title in titles:
            self.assertLessEqual(len(title), 240)
            self.assertNotIn("Promoted", title)

    def test_overlong_checkbox_titles_are_truncated_with_ellipsis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = projects / "demo"
            project.mkdir()
            (project / "README.md").write_text("---\ntitle: \"Demo\"\n---\n", encoding="utf-8")

            plans_dir = project / "plans"
            plans_dir.mkdir()
            long_line = "Implement the thing " * 30
            (plans_dir / "phase-1.md").write_text(
                "# Phase 1\n\nstatus: active\n\n## Unit plan\n\n"
                f"- [ ] {long_line}\n",
                encoding="utf-8",
            )

            tasks = generate_tasks.compile_tasks(
                projects, projects / "task_packets_manifest.json"
            )

        self.assertEqual(len(tasks), 1)
        title = tasks[0]["title"]
        self.assertTrue(title.endswith("…"), title[-20:])
        self.assertLessEqual(len(title), generate_tasks.MAX_TASK_TITLE_LENGTH + 40)


if __name__ == "__main__":
    unittest.main()
