"""MPE-024 — structured focus authority loader and session-open preference."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from focus_authority import load_focus, parse_focus_yaml  # noqa: E402

SCRIPT_PATH = ROOT / "bin" / "session-open"
LOADER = SourceFileLoader("session_open_focus", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)
build_context = mod.build_context


SAMPLE = """\
schema_version: 1
decision_id: focus-test-01
revision: abcd1234
as_of: 2026-07-15T00:00:00Z
review_by: 2099-01-01T00:00:00Z
selected_by: operator
primary:
  project: demo-proj
  desired_outcome: ship
  success_boundary: done
  why_now: now
  confidence: high
  evidence_refs:
    - a.md
supporting_slots: []
snoozed: []
candidate_snapshot: null
"""


class FocusParseTests(unittest.TestCase):
    def test_parse_primary_project(self) -> None:
        data = parse_focus_yaml(SAMPLE)
        self.assertEqual(data["decision_id"], "focus-test-01")
        self.assertEqual(data["primary"]["project"], "demo-proj")
        self.assertEqual(data["primary"]["evidence_refs"], ["a.md"])

    def test_parse_list_mapping_preserves_sibling_fields(self) -> None:
        data = parse_focus_yaml(
            """\
supporting_slots:
  - project: support-one
    desired_outcome: unblock primary
    evidence_refs:
      - evidence-a.md
      - evidence-b.md
  - project: support-two
    desired_outcome: preserve follow-up
"""
        )

        self.assertEqual(
            data["supporting_slots"],
            [
                {
                    "project": "support-one",
                    "desired_outcome": "unblock primary",
                    "evidence_refs": ["evidence-a.md", "evidence-b.md"],
                },
                {
                    "project": "support-two",
                    "desired_outcome": "preserve follow-up",
                },
            ],
        )

    def test_load_focus_requires_project_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            focus = root / "20_live" / "focus"
            focus.mkdir(parents=True)
            (focus / "current.yaml").write_text(SAMPLE, encoding="utf-8")
            loaded = load_focus(root)
            self.assertFalse(loaded.ok)
            self.assertTrue(any("missing" in e for e in loaded.errors))

            proj = root / "30_projects" / "demo-proj"
            proj.mkdir(parents=True)
            (proj / "README.md").write_text("# Demo\n", encoding="utf-8")
            loaded2 = load_focus(root)
            self.assertTrue(loaded2.ok, loaded2.errors)
            self.assertEqual(loaded2.primary_project, "demo-proj")


class SessionOpenFocusTests(unittest.TestCase):
    def test_prefers_focus_over_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# a\n", encoding="utf-8")
            (root / "STATE.md").write_text(
                "# S\n\n## Active Project\n\nother-project\n",
                encoding="utf-8",
            )
            focus = root / "20_live" / "focus"
            focus.mkdir(parents=True)
            (focus / "current.yaml").write_text(SAMPLE, encoding="utf-8")
            for slug in ("demo-proj", "other-project"):
                d = root / "30_projects" / slug
                d.mkdir(parents=True)
                (d / "README.md").write_text(f"# {slug}\n", encoding="utf-8")

            result = build_context(root)
            self.assertEqual(result.project, "demo-proj")
            self.assertEqual(result.project_source, "focus")
            self.assertTrue(result.ok)
            self.assertEqual(result.focus_revision, "abcd1234")


if __name__ == "__main__":
    unittest.main()
