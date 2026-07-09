from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "task-packet"
LOADER = SourceFileLoader("task_packet", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
task_packet = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = task_packet
SPEC.loader.exec_module(task_packet)


def packet_text(**overrides: object) -> str:
    metadata: dict[str, object] = {
        "packet_version": 1,
        "task_id": "fix-one",
        "project_slug": "demo",
        "title": "Fix one thing",
        "status": "ready",
        "task_kind": "code",
        "agent_profile": "local-test",
        "workdir": "workbench",
        "timeout_seconds": 60,
        "editable_files": ["src/app.py"],
        "create_files": [],
        "read_only_files": ["AGENTS.md"],
        "verification_commands": ["python3 -m unittest -q"],
        "mindgraph_mode": "off",
        "knowledge_queries": [],
    }
    metadata.update(overrides)
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list):
            rendered = json.dumps(value)
        elif isinstance(value, int):
            rendered = str(value)
        else:
            rendered = json.dumps(value)
        lines.append(f"{key}: {rendered}")
    lines.extend(["---", "", "# Task Packet", ""])
    for section in task_packet.REQUIRED_SECTIONS:
        lines.extend([f"## {section}", "", f"{section} content.", ""])
    return "\n".join(lines)


class TaskPacketTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        project = root / "demo"
        packet_dir = project / "plans" / "task-packets"
        (project / "workbench" / "src").mkdir(parents=True)
        (project / "workbench" / "AGENTS.md").write_text("", encoding="utf-8")
        packet_dir.mkdir(parents=True)
        return project

    def test_valid_ready_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            path.write_text(packet_text(), encoding="utf-8")
            packet = task_packet.load_packet(path)

            errors = task_packet.validate_packet(
                packet,
                projects_dir=projects,
                require_ready=True,
            )

        self.assertEqual(errors, [])

    def test_rejects_unsafe_paths_overlap_and_shell_operators(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            path.write_text(
                packet_text(
                    editable_files=["../secret", "AGENTS.md"],
                    read_only_files=["AGENTS.md"],
                    verification_commands=["pytest && rm -rf /"],
                ),
                encoding="utf-8",
            )
            packet = task_packet.load_packet(path)
            errors = task_packet.validate_packet(packet, projects_dir=projects)

        self.assertTrue(any("unsafe path" in error for error in errors))
        self.assertTrue(any("overlap" in error for error in errors))
        self.assertTrue(any("shell operator" in error for error in errors))

    def test_rejects_missing_section_and_nonexistent_workdir(self) -> None:
        text = packet_text().replace(
            "## Stop conditions\n\nStop conditions content.\n",
            "",
        )
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            path.write_text(
                text.replace('workdir: "workbench"', 'workdir: "missing"'),
                encoding="utf-8",
            )
            packet = task_packet.load_packet(path)
            errors = task_packet.validate_packet(packet, projects_dir=projects)

        self.assertTrue(any("Stop conditions" in error for error in errors))
        self.assertTrue(any("workdir does not exist" in error for error in errors))

    def test_rejects_absolute_paths_missing_verification_and_draft_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            path.write_text(
                packet_text(
                    status="draft",
                    editable_files=["/tmp/escape.py"],
                    verification_commands=[],
                ),
                encoding="utf-8",
            )
            packet = task_packet.load_packet(path)
            errors = task_packet.validate_packet(
                packet,
                projects_dir=projects,
                require_ready=True,
            )

        self.assertTrue(any("relative paths" in error for error in errors))
        self.assertTrue(any("verification command" in error for error in errors))
        self.assertTrue(any("status ready" in error for error in errors))

    def test_accepts_optional_routing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            path.write_text(
                packet_text(
                    task_category="mechanical-edit",
                    executor="local",
                    harness_recommendation="H1-packet",
                    allow_fusion_plan=False,
                    needs_deliberation=False,
                ),
                encoding="utf-8",
            )
            packet = task_packet.load_packet(path)
            errors = task_packet.validate_packet(packet, projects_dir=projects)

        self.assertEqual(errors, [])
        summary = task_packet.packet_summary(packet, root=projects.parent)
        self.assertEqual(summary["task_category"], "mechanical-edit")
        self.assertEqual(summary["harness_recommendation"], "H1-packet")

    def test_rejects_invalid_routing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            path.write_text(
                packet_text(
                    task_category="not-a-category",
                    executor="hybrid",
                    harness_recommendation="H9-fusion",
                ),
                encoding="utf-8",
            )
            packet = task_packet.load_packet(path)
            errors = task_packet.validate_packet(packet, projects_dir=projects)

        self.assertTrue(any("task_category" in error for error in errors))
        self.assertTrue(any("executor" in error for error in errors))
        self.assertTrue(any("harness_recommendation" in error for error in errors))

    def test_infer_routing_hints_for_multi_file_code(self) -> None:
        hints = task_packet.infer_routing_hints(
            {
                "task_kind": "code",
                "editable_files": ["a.py", "b.py"],
                "create_files": [],
            }
        )
        self.assertEqual(hints["task_category"], "multi-file-coordination")
        self.assertEqual(hints["harness_recommendation"], "H2-repair")
        self.assertEqual(hints["agent_profile"], "local-qwen25-coder-14b")

    def test_rejects_unknown_metadata_and_duplicate_paths(self) -> None:
        text = packet_text(
            editable_files=["src/app.py", "src/app.py"],
        ).replace(
            'title: "Fix one thing"',
            'title: "Fix one thing"\nmisspelled_timeout: 99',
        )
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            path.write_text(text, encoding="utf-8")
            packet = task_packet.load_packet(path)
            errors = task_packet.validate_packet(packet, projects_dir=projects)

        self.assertTrue(any("unknown frontmatter key" in error for error in errors))
        self.assertTrue(any("duplicate paths" in error for error in errors))

    def test_rejects_unknown_and_duplicate_sections(self) -> None:
        unknown = packet_text() + "\n## Surprise\n\nNot part of the contract.\n"
        duplicate = packet_text() + "\n## Goal\n\nA second goal.\n"
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            path.write_text(unknown, encoding="utf-8")
            errors = task_packet.validate_packet(
                task_packet.load_packet(path),
                projects_dir=projects,
            )
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaises(task_packet.PacketError):
                task_packet.load_packet(path)

        self.assertTrue(any("unknown packet section" in error for error in errors))

    def test_compile_writes_deterministic_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projects = root / "30_projects"
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            path.write_text(packet_text(), encoding="utf-8")
            output = projects / "task_packets_manifest.json"

            first = task_packet.compile_packets(
                projects_dir=projects,
                output=output,
            )
            first_bytes = output.read_bytes()
            second = task_packet.compile_packets(
                projects_dir=projects,
                output=output,
            )

        self.assertEqual(first, second)
        self.assertEqual(first_bytes, json.dumps(second, indent=2, sort_keys=True).encode() + b"\n")
        self.assertEqual(first["packets"][0]["task_id"], "fix-one")
        self.assertEqual(
            first["packets"][0]["packet_path"],
            "30_projects/demo/plans/task-packets/fix-one.md",
        )

    def test_invalid_compile_preserves_last_good_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projects = root / "30_projects"
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            output = projects / "task_packets_manifest.json"
            output.write_text('{"last_good": true}\n', encoding="utf-8")
            path.write_text(
                packet_text(verification_commands=[]),
                encoding="utf-8",
            )

            payload = task_packet.compile_packets(
                projects_dir=projects,
                output=output,
            )
            output_text = output.read_text(encoding="utf-8")

        self.assertTrue(payload["invalid"])
        self.assertEqual(output_text, '{"last_good": true}\n')

    def test_compiled_ready_contract_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projects = root / "30_projects"
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            output = projects / "task_packets_manifest.json"
            path.write_text(packet_text(), encoding="utf-8")
            task_packet.compile_packets(projects_dir=projects, output=output)
            last_good = output.read_bytes()

            path.write_text(
                packet_text(title="Silently changed contract"),
                encoding="utf-8",
            )
            payload = task_packet.compile_packets(
                projects_dir=projects,
                output=output,
            )

            preserved = output.read_bytes()

        self.assertTrue(payload["invalid"])
        self.assertIn("immutable", payload["invalid"][0]["errors"][0])
        self.assertEqual(preserved, last_good)

    def test_compiled_ready_contract_may_not_be_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projects = root / "30_projects"
            project = self.make_project(projects)
            path = project / "plans" / "task-packets" / "fix-one.md"
            output = projects / "task_packets_manifest.json"
            path.write_text(packet_text(), encoding="utf-8")
            task_packet.compile_packets(projects_dir=projects, output=output)
            last_good = output.read_bytes()

            path.unlink()
            payload = task_packet.compile_packets(
                projects_dir=projects,
                output=output,
            )
            preserved = output.read_bytes()

        self.assertTrue(payload["invalid"])
        self.assertIn("may not be deleted", payload["invalid"][0]["errors"][0])
        self.assertEqual(preserved, last_good)


if __name__ == "__main__":
    unittest.main()
