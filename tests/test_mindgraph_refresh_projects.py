"""Unit 2.1 — mindgraph-refresh-projects fail-closed CLI contract."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "mindgraph-refresh-projects"


def _run(args: list[str], *, env: dict | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        env=e,
        check=False,
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class MindgraphRefreshProjectsCLITests(unittest.TestCase):
    def test_help_exits_zero_and_mentions_apply(self) -> None:
        proc = _run(["--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--apply", proc.stdout)
        self.assertIn("--dry-run", proc.stdout)
        self.assertIn("--deep", proc.stdout)
        self.assertNotIn("ingest-many", proc.stdout.split("Safety:")[0] if "Safety:" in proc.stdout else "")

    def test_dry_run_lean_excludes_outputs_include(self) -> None:
        proc = _run(["--dry-run"])
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("lean/default", proc.stdout)
        # Includes block should not list outputs globs for default
        after = proc.stdout.split("Includes:")[-1]
        self.assertNotIn("outputs/*.md", after)
        self.assertNotIn("outputs/**/*.md", after)

    def test_dry_run_deep_includes_outputs(self) -> None:
        proc = _run(["--dry-run", "--deep"])
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("(deep)", proc.stdout)
        after = proc.stdout.split("Includes:")[-1]
        self.assertIn("outputs", after)

    def test_help_flag_order_independent(self) -> None:
        # --help wins as first matched option when alone; with other flags,
        # any --help in argv should still be non-mutating if processed in loop.
        proc = _run(["--full", "--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Usage:", proc.stdout)

    def test_unknown_flag_fails_closed(self) -> None:
        proc = _run(["--not-a-real-flag"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown option", proc.stderr.lower())

    def test_positional_arg_fails_closed(self) -> None:
        proc = _run(["surprise"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unexpected argument", proc.stderr.lower())

    def test_bare_invocation_refuses_without_apply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sentinel = Path(td) / "sentinel.sqlite"
            sentinel.write_bytes(b"before")
            before = _sha256(sentinel)
            proc = _run([], env={"MINDGRAPH_DB_PATH": str(sentinel)})
            self.assertEqual(proc.returncode, 2)
            self.assertIn("refusing to mutate without --apply", proc.stderr)
            self.assertEqual(_sha256(sentinel), before)
            self.assertEqual(sentinel.read_bytes(), b"before")

    def test_dry_run_does_not_change_sentinel_db_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sentinel = Path(td) / "sentinel.sqlite"
            payload = b"x" * 4096
            sentinel.write_bytes(payload)
            before = _sha256(sentinel)
            # flag order: --full before --dry-run
            proc = _run(
                ["--full", "--dry-run"],
                env={"MINDGRAPH_DB_PATH": str(sentinel)},
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("dry-run", proc.stdout.lower())
            self.assertEqual(sentinel.read_bytes(), payload)
            self.assertEqual(_sha256(sentinel), before)

    def test_dry_run_apply_together_rejected(self) -> None:
        proc = _run(["--dry-run", "--apply"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("refuse", proc.stderr.lower())

    def test_help_does_not_require_db(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "nope.sqlite"
            proc = _run(["--help"], env={"MINDGRAPH_DB_PATH": str(missing)})
            self.assertEqual(proc.returncode, 0)
            self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
