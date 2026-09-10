"""Unit tests for bin/process-eval."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
LOADER = SourceFileLoader(
    "process_eval",
    str(ROOT / "40_operations" / "mainframe-process-eval" / "src" / "process_eval.py"),
)
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
pe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pe
SPEC.loader.exec_module(pe)


class TestProcessEval(unittest.TestCase):
    def test_preflight_steps_structure(self):
        steps = pe.preflight_steps()
        self.assertTrue(len(steps) > 5)
        for name, cmd in steps:
            self.assertIsInstance(name, str)
            self.assertIsInstance(cmd, list)
            self.assertTrue(len(cmd) > 0)

    def test_cmd_status_runs(self):
        args = argparse.Namespace(json=False)
        ret = pe.cmd_status(args)
        self.assertEqual(ret, 0)

    def test_cmd_status_loop_eval_absent(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            project = root / "40_operations" / "mainframe-process-eval"
            project.mkdir(parents=True)
            args = argparse.Namespace(json=True)
            with (
                patch.object(pe, "ROOT", root),
                patch.object(pe, "WORKFLOW", root / "missing.md"),
                patch.object(pe, "live_project", lambda: project),
                patch("builtins.print") as printer,
            ):
                ret = pe.cmd_status(args)
            self.assertEqual(ret, 0)
            payload = json.loads(printer.call_args[0][0])
            self.assertIsNone(payload["loop_eval"])

    def test_cmd_status_loop_eval_present(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            project = root / "40_operations" / "mainframe-process-eval"
            index = project / "workbench" / "loop-eval" / "catalogue" / "INDEX.md"
            index.parent.mkdir(parents=True)
            index.write_text("# catalogue\n", encoding="utf-8")
            args = argparse.Namespace(json=True)
            with (
                patch.object(pe, "ROOT", root),
                patch.object(pe, "WORKFLOW", root / "missing.md"),
                patch.object(pe, "live_project", lambda: project),
                patch("builtins.print") as printer,
            ):
                ret = pe.cmd_status(args)
            self.assertEqual(ret, 0)
            payload = json.loads(printer.call_args[0][0])
            self.assertEqual(
                payload["loop_eval"],
                "40_operations/mainframe-process-eval/workbench/loop-eval/catalogue/INDEX.md",
            )

    def test_cmd_close_runs(self):
        args = argparse.Namespace(
            run_id="2026-08-18-test-run",
            question="Is the process verified?",
            decision="Accept current baseline",
            write=False,
        )
        ret = pe.cmd_close(args)
        self.assertEqual(ret, 0)

    @patch.object(pe, "run_cmd")
    def test_cmd_preflight_all_pass(self, mock_run):
        mock_proc = MagicMock(spec=subprocess.CompletedProcess)
        mock_proc.returncode = 0
        mock_proc.stdout = "OK"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        args = argparse.Namespace(
            json=False,
            fast=False,
            stop_on_failure=False,
            skip_doctor=False,
            skip_unittest=False,
            timeout=180,
        )
        ret = pe.cmd_preflight(args)
        self.assertEqual(ret, 0)

    @patch.object(pe, "run_cmd")
    def test_cmd_preflight_failure_with_stop(self, mock_run):
        mock_proc_fail = MagicMock(spec=subprocess.CompletedProcess)
        mock_proc_fail.returncode = 1
        mock_proc_fail.stdout = ""
        mock_proc_fail.stderr = "Error in step"
        mock_run.return_value = mock_proc_fail

        args = argparse.Namespace(
            json=False,
            fast=False,
            stop_on_failure=True,
            skip_doctor=False,
            skip_unittest=False,
            timeout=180,
        )
        ret = pe.cmd_preflight(args)
        self.assertEqual(ret, 1)


if __name__ == "__main__":
    unittest.main()
