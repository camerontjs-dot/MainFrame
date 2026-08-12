"""Tests for bin/lane-intake list filters and priority/status matching."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "bin" / "lane-intake"
LOADER = SourceFileLoader("lane_intake", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class PriorityMatchTests(unittest.TestCase):
    def test_p0_matches_immediate(self) -> None:
        self.assertTrue(mod._priority_matches("immediate", "P0"))
        self.assertTrue(mod._priority_matches("immediate", "p0"))

    def test_p0_matches_p0(self) -> None:
        self.assertTrue(mod._priority_matches("P0", "P0"))
        self.assertTrue(mod._priority_matches("P0 critical", "P0"))

    def test_p0_rejects_next(self) -> None:
        self.assertFalse(mod._priority_matches("next", "P0"))
        self.assertFalse(mod._priority_matches("P1", "P0"))

    def test_p1_matches_next_and_high(self) -> None:
        self.assertTrue(mod._priority_matches("next", "P1"))
        self.assertTrue(mod._priority_matches("high", "P1"))
        self.assertTrue(mod._priority_matches("P1", "P1"))

    def test_p4_matches_monitor_alongside(self) -> None:
        self.assertTrue(mod._priority_matches("monitor", "P4"))
        self.assertTrue(mod._priority_matches("alongside", "P4"))
        self.assertTrue(mod._priority_matches("deferred", "P4"))

    def test_empty_filter_matches_all(self) -> None:
        self.assertTrue(mod._priority_matches("immediate", ""))
        self.assertTrue(mod._priority_matches("", ""))


class StatusMatchTests(unittest.TestCase):
    def test_exact_active(self) -> None:
        self.assertTrue(mod._status_matches("active", "active"))

    def test_prefix_em_dash(self) -> None:
        self.assertTrue(
            mod._status_matches("active — specialization pass done", "active")
        )

    def test_prefix_hyphen(self) -> None:
        self.assertTrue(mod._status_matches("active - foundation", "active"))

    def test_complete_not_active(self) -> None:
        self.assertFalse(mod._status_matches("complete", "active"))
        self.assertFalse(mod._status_matches("parked", "active"))

    def test_case_insensitive(self) -> None:
        self.assertTrue(mod._status_matches("Active", "ACTIVE"))


class ListLanesFixtureTests(unittest.TestCase):
    """list_lanes against a temporary lanes tree."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.lanes = self.root / "lanes"
        self.completed = self.lanes / "completed"
        self.lanes.mkdir(parents=True)
        self.completed.mkdir(parents=True)

        self._write_lane(
            self.lanes / "alpha-lane",
            lane_id="A1",
            status="active",
            priority="immediate",
            domain="agents",
        )
        self._write_lane(
            self.lanes / "beta-lane",
            lane_id="B1",
            status="active — specialization pass done",
            priority="P0",
            domain="agents",
        )
        self._write_lane(
            self.lanes / "gamma-lane",
            lane_id="G1",
            status="active",
            priority="next",
            domain="finance",
        )
        self._write_lane(
            self.completed / "done-lane",
            lane_id="D1",
            status="complete",
            priority="P0",
            domain="agents",
        )

        self._orig_lanes = mod.LANES_DIR
        self._orig_completed = mod.COMPLETED_DIR
        mod.LANES_DIR = self.lanes
        mod.COMPLETED_DIR = self.completed

    def tearDown(self) -> None:
        mod.LANES_DIR = self._orig_lanes
        mod.COMPLETED_DIR = self._orig_completed
        self.tmp.cleanup()

    def _write_lane(
        self,
        path: Path,
        *,
        lane_id: str,
        status: str,
        priority: str,
        domain: str,
    ) -> None:
        path.mkdir(parents=True, exist_ok=True)
        (path / "README.md").write_text(
            f"""---
title: "Lane: {path.name}"
status: "{status}"
lane_id: "{lane_id}"
knowledge_domain: "{domain}"
priority: "{priority}"
---

# {path.name}
""",
            encoding="utf-8",
        )

    def test_p0_active_includes_immediate_and_p0(self) -> None:
        rows = mod.list_lanes(status_filter="active", priority_filter="P0")
        slugs = {r["slug"] for r in rows}
        self.assertIn("alpha-lane", slugs)
        self.assertIn("beta-lane", slugs)
        self.assertNotIn("gamma-lane", slugs)
        self.assertNotIn("done-lane", slugs)

    def test_status_prefix_matches_decorated_active(self) -> None:
        rows = mod.list_lanes(status_filter="active")
        slugs = {r["slug"] for r in rows}
        self.assertIn("beta-lane", slugs)
        self.assertEqual(len(rows), 3)

    def test_p1_matches_next(self) -> None:
        rows = mod.list_lanes(status_filter="active", priority_filter="P1")
        slugs = {r["slug"] for r in rows}
        self.assertEqual(slugs, {"gamma-lane"})

    def test_complete_p0(self) -> None:
        rows = mod.list_lanes(status_filter="complete", priority_filter="P0")
        slugs = {r["slug"] for r in rows}
        self.assertEqual(slugs, {"done-lane"})

    def test_format_json(self) -> None:
        rows = mod.list_lanes(status_filter="active", priority_filter="P0")
        out = mod.format_list(rows, fmt="json")
        self.assertIn("alpha-lane", out)
        self.assertTrue(out.strip().startswith("["))


class ParseFrontmatterTests(unittest.TestCase):
    def test_basic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "README.md"
            p.write_text(
                '---\nstatus: "active"\npriority: "immediate"\nlane_id: "X1"\n---\n\n# Hi\n',
                encoding="utf-8",
            )
            fm = mod.parse_frontmatter(p)
            self.assertEqual(fm.get("status"), "active")
            self.assertEqual(fm.get("priority"), "immediate")
            self.assertEqual(fm.get("lane_id"), "X1")


if __name__ == "__main__":
    unittest.main()
