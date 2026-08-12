"""Tests for bin/research-lane-loop preflight classification and index audit."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "bin" / "research-lane-loop"
LOADER = SourceFileLoader("research_lane_loop", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class ClassifyResumeTests(unittest.TestCase):
    def test_class_a_fresh(self) -> None:
        c, _ = mod.classify_resume([], [], [], [])
        self.assertEqual(c, "A")

    def test_class_b_inbox(self) -> None:
        c, reason = mod.classify_resume(["00_inbox/x.md"], [], [], [])
        self.assertEqual(c, "B")
        self.assertIn("inbox", reason.lower())

    def test_class_c_raws_no_notes(self) -> None:
        raws = [f"r{i}" for i in range(3)]
        c, _ = mod.classify_resume([], raws, [], [])
        self.assertEqual(c, "C")

    def test_class_d_stale_when_knowledge_exists(self) -> None:
        stale = [
            mod.StaleRef(
                tracker_path="00_inbox/foo.md",
                basename="foo.md",
                knowledge_path="10_knowledge/agents/foo.md",
                still_in_inbox=False,
            )
        ]
        c, reason = mod.classify_resume([], ["10_knowledge/agents/foo.md"], [], stale)
        self.assertEqual(c, "D")
        self.assertIn("00_inbox", reason)

    def test_class_b_wins_over_empty_knowledge(self) -> None:
        c, _ = mod.classify_resume(["00_inbox/x.md"], ["raw1"], ["note1"], [])
        self.assertEqual(c, "B")

    def test_class_c_sparse_existing_corpus(self) -> None:
        """1 raw + 1 note is not 'fresh' — avoid re-discovering from zero."""
        c, reason = mod.classify_resume([], ["raw1"], ["note1"], [])
        self.assertEqual(c, "C")
        self.assertIn("coverage", reason.lower())

    def test_sparse_corpus_reason_carries_no_source_quota(self) -> None:
        """The resume reason must never imply a target number of sources.

        Until 2026-08-09 this path said "gap-fill" and the loop emitted
        "need ~3-4 raws" whenever a lane held fewer than three. An agent that
        searched honestly and found one source had no compliant way to say so,
        because no field meant "I looked and found nothing" — so it produced
        three that looked right. 107 captures citing papers that do not exist
        followed, across four months and fourteen domains.

        The guarantee is not a wording preference. It is that the loop asks a
        coverage question rather than naming a count, so that recording a gap
        stays an available and honest answer. Asserted on the shape of the
        reason string rather than its exact text, so a rewrite that keeps the
        guarantee does not fail and a quota that returns does.
        """
        for raws, notes in (([], []), (["r1"], []), (["r1"], ["n1"]),
                            (["r1", "r2"], ["n1"])):
            _, reason = mod.classify_resume([], raws, notes, [])
            low = reason.lower()
            self.assertNotRegex(
                low,
                r"(need|fill|at least|minimum|target|quota)\b[^.]{0,24}\b\d+",
                f"resume reason reintroduces a source quota: {reason!r}",
            )
            self.assertNotIn("gap-fill", low)


class StaleScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.knowledge = self.root / "10_knowledge" / "agents"
        self.knowledge.mkdir(parents=True)
        self.inbox = self.root / "00_inbox"
        self.inbox.mkdir()
        (self.knowledge / "2026-01-01__agents__raw__sample.md").write_text("# raw\n")

        self._orig_root = mod.ROOT
        self._orig_know = mod.KNOWLEDGE
        self._orig_inbox = mod.INBOX
        mod.ROOT = self.root
        mod.KNOWLEDGE = self.root / "10_knowledge"
        mod.INBOX = self.inbox

    def tearDown(self) -> None:
        mod.ROOT = self._orig_root
        mod.KNOWLEDGE = self._orig_know
        mod.INBOX = self._orig_inbox
        self.tmp.cleanup()

    def test_detects_fixable_stale_path(self) -> None:
        text = (
            "| 2026-01-01 | `00_inbox/2026-01-01__agents__raw__sample.md` | raw |\n"
        )
        refs = mod.scan_stale_inbox_refs(text, "agents")
        self.assertEqual(len(refs), 1)
        self.assertEqual(
            refs[0].knowledge_path,
            "10_knowledge/agents/2026-01-01__agents__raw__sample.md",
        )
        self.assertFalse(refs[0].still_in_inbox)

    def test_no_stale_when_only_knowledge_paths(self) -> None:
        text = "`10_knowledge/agents/2026-01-01__agents__raw__sample.md`"
        refs = mod.scan_stale_inbox_refs(text, "agents")
        self.assertEqual(refs, [])


class CaptureTagsTests(unittest.TestCase):
    def test_parse_yaml_list(self) -> None:
        fm = {
            "capture_tags": '["research-lane", "lane-mh01", "mindgraph"]',
        }
        tags = mod.parse_capture_tags(fm, "")
        self.assertIn("lane-mh01", tags)
        self.assertIn("research-lane", tags)

    def test_fallback_lane_tag_from_body(self) -> None:
        tags = mod.parse_capture_tags({}, "see lane-c28 work")
        self.assertIn("lane-c28", tags)

    def test_paths_from_capture_index(self) -> None:
        text = (
            "| d | `10_knowledge/loop-engineering/2026-07-10__x__raw__y.md` |\n"
            "| e | 10_knowledge/ai-business/z.md |\n"
        )
        paths = mod.paths_from_capture_index(text)
        self.assertIn(
            "10_knowledge/loop-engineering/2026-07-10__x__raw__y.md", paths
        )
        self.assertIn("10_knowledge/ai-business/z.md", paths)


class AuditRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.lanes = self.root / "30_projects" / "research-lanes-strategy" / "lanes"
        self.completed = self.lanes / "completed"
        self.lanes.mkdir(parents=True)
        self.completed.mkdir(parents=True)
        self.knowledge = self.root / "10_knowledge" / "agents"
        self.knowledge.mkdir(parents=True)
        self.inbox = self.root / "00_inbox"
        self.inbox.mkdir()

        base = "2026-01-01__agents__raw__widget.md"
        (self.knowledge / base).write_text("# raw\n")

        lane = self.lanes / "widget-lane"
        lane.mkdir()
        self.readme = lane / "README.md"
        self.readme.write_text(
            f"""---
title: "Lane: Widget"
status: "active"
lane_id: "W1"
knowledge_domain: "agents"
priority: "immediate"
capture_tags: ["research-lane", "lane-w1"]
---

# Widget

| Date | Path |
|------|------|
| 2026-01-01 | `00_inbox/{base}` |
""",
            encoding="utf-8",
        )

        # Point module paths + lane_intake dirs at fixture
        self._paths = {
            "ROOT": mod.ROOT,
            "KNOWLEDGE": mod.KNOWLEDGE,
            "INBOX": mod.INBOX,
            "LANES_DIR": mod.LANES_DIR,
            "COMPLETED_DIR": mod.COMPLETED_DIR,
            "li_LANES": mod.lane_intake.LANES_DIR,
            "li_COMPLETED": mod.lane_intake.COMPLETED_DIR,
        }
        mod.ROOT = self.root
        mod.KNOWLEDGE = self.root / "10_knowledge"
        mod.INBOX = self.inbox
        mod.LANES_DIR = self.lanes
        mod.COMPLETED_DIR = self.completed
        mod.lane_intake.LANES_DIR = self.lanes
        mod.lane_intake.COMPLETED_DIR = self.completed

    def tearDown(self) -> None:
        mod.ROOT = self._paths["ROOT"]
        mod.KNOWLEDGE = self._paths["KNOWLEDGE"]
        mod.INBOX = self._paths["INBOX"]
        mod.LANES_DIR = self._paths["LANES_DIR"]
        mod.COMPLETED_DIR = self._paths["COMPLETED_DIR"]
        mod.lane_intake.LANES_DIR = self._paths["li_LANES"]
        mod.lane_intake.COMPLETED_DIR = self._paths["li_COMPLETED"]
        self.tmp.cleanup()

    def test_audit_dry_run_finds_stale(self) -> None:
        result = mod.audit_indexes("active", repair=False)
        self.assertEqual(result["lanes_with_stale_refs"], 1)
        self.assertEqual(result["repaired"], [])
        self.assertIn("00_inbox/", self.readme.read_text())

    def test_preflight_does_not_rewrite_stale_path(self) -> None:
        mod.preflight_slug("widget-lane")

        self.assertIn("00_inbox/", self.readme.read_text())

    def test_audit_repair_rewrites_path(self) -> None:
        result = mod.audit_indexes("active", repair=True)
        self.assertEqual(result["repaired"], ["widget-lane"])
        text = self.readme.read_text()
        self.assertIn("10_knowledge/agents/2026-01-01__agents__raw__widget.md", text)
        self.assertNotIn("00_inbox/2026-01-01__agents__raw__widget.md", text)


if __name__ == "__main__":
    unittest.main()


class PhaseAndBlockerTests(unittest.TestCase):
    def test_parse_phase_status_ignores_capture_index(self) -> None:
        text = """
## Captured knowledge

| Date | Path | Type |
|------|------|------|
| 2026-07-13 | `foo.md` | raw |

## Phase status

| Phase | Status | Notes |
|-------|--------|-------|
| Foundation | ✅ done | x |
| Taxonomy | ✅ done | y |
| Application | next | z |
"""
        ps = mod.parse_phase_status(text)
        self.assertEqual(ps.get("Foundation"), "done")
        self.assertEqual(ps.get("Taxonomy"), "done")
        self.assertEqual(ps.get("Application"), "next")
        self.assertNotIn("Date", ps)

    def test_infer_next_phase_and_blocker(self) -> None:
        ps = {"Foundation": "done", "Taxonomy": "done", "Application": "next"}
        nxt = mod.infer_next_phase(ps)
        self.assertEqual(nxt, "Application")
        blocker = mod.infer_blocker(
            "C", nxt, "10_knowledge/x/, 30_projects/local-agent/", raw_count=5, note_count=2
        )
        self.assertEqual(blocker, "project")
