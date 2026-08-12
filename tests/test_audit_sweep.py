"""Focused tests for bin/audit-sweep candidate discovery and CLI validation."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SWEEP_PATH = ROOT / "bin" / "audit-sweep"
LOADER = SourceFileLoader("audit_sweep", str(SWEEP_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
audit_sweep = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit_sweep
SPEC.loader.exec_module(audit_sweep)


class AuditSweepTests(unittest.TestCase):
    def test_parse_frontmatter_tags_supports_inline_and_block_lists(self) -> None:
        inline = """---
tags: ["x-capture", "needs-audit", "clippings"]
---
"""
        block = """---
tags:
- needs-audit
- raw
- pdf
---
"""

        self.assertEqual(
            audit_sweep.parse_simple_frontmatter_tags(inline),
            ["x-capture", "needs-audit", "clippings"],
        )
        self.assertEqual(
            audit_sweep.parse_simple_frontmatter_tags(block),
            ["needs-audit", "raw", "pdf"],
        )
        self.assertEqual(
            audit_sweep.parse_simple_frontmatter_tags("just body"),
            [],
        )

    def test_max_days_limits_samples_but_not_explicit_audit_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            knowledge = root / "10_knowledge"
            domain = knowledge / "example"
            domain.mkdir(parents=True)

            at_boundary = domain / "2026-01-01__example__raw__boundary.md"
            too_old = domain / "2026-01-01__example__raw__old.md"
            explicit = domain / "2026-01-01__example__note__audit.md"
            at_boundary.write_text("---\ntags: [raw]\n---\n", encoding="utf-8")
            too_old.write_text("---\ntags: [raw]\n---\n", encoding="utf-8")
            explicit.write_text(
                "---\ntags: [needs-audit]\n---\n",
                encoding="utf-8",
            )

            self._set_age(at_boundary, 7)
            self._set_age(too_old, 8)
            self._set_age(explicit, 30)

            with (
                patch.object(audit_sweep, "ROOT", root),
                patch.object(audit_sweep, "KNOWLEDGE", knowledge),
            ):
                candidates = audit_sweep.collect_candidates("example", max_days=7)

        by_name = {candidate["name"]: candidate for candidate in candidates}
        self.assertEqual(set(by_name), {at_boundary.name, explicit.name})
        self.assertFalse(by_name[at_boundary.name]["has_needs_audit"])
        self.assertTrue(by_name[explicit.name]["has_needs_audit"])

    def test_cli_rejects_negative_max_days(self) -> None:
        result = subprocess.run(
            [str(SWEEP_PATH), "--dry-run", "--json", "--max-days", "-1"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("must be zero or greater", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_dry_run_json_reports_subset_and_counts(self) -> None:
        result = subprocess.run(
            [
                str(SWEEP_PATH),
                "--dry-run",
                "--json",
                "--subset",
                "regulated-systems",
                "--max-days",
                "7",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        data = json.loads(result.stdout)
        self.assertEqual(data["subset"], "regulated-systems")
        self.assertGreaterEqual(data["candidate_count"], 0)
        self.assertGreaterEqual(data["explicit_needs_audit"], 0)

    @staticmethod
    def _set_age(path: Path, days: int) -> None:
        modified = datetime.combine(
            date.today() - timedelta(days=days),
            time(hour=12),
        ).timestamp()
        os.utime(path, (modified, modified))


if __name__ == "__main__":
    unittest.main()
