"""Root shim for bin/process-eval delegates to the operation-owned engine."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProcessEvalShimTests(unittest.TestCase):
    def test_help_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "bin" / "process-eval"), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("process-evaluation", result.stdout.lower() + result.stderr.lower())

    def test_status_resolves_tracked_operation_authority(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "bin" / "process-eval"), "status", "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("40_operations/mainframe-process-eval", result.stdout)
