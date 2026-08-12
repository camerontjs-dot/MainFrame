"""Loop-eval catalogue schema, scores, tier gates, surface paths."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "30_projects" / "mainframe-process-eval" / "workbench" / "loop-eval"
SCRIPT = WB / "scripts" / "score_catalogue.py"
CATALOGUE = WB / "catalogue" / "entries.json"
SCHEMA = WB / "schema" / "loop-entry.schema.json"


def _load_score_mod():
    spec = importlib.util.spec_from_file_location("score_catalogue", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class LoopCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_score_mod()
        cls.data = cls.mod.load_catalogue(CATALOGUE)

    def test_workbench_files_exist(self) -> None:
        for rel in (
            "README.md",
            "THRESHOLDS.md",
            "catalogue/entries.json",
            "catalogue/entries.yaml",
            "catalogue/INDEX.md",
            "catalogue/01-well-defined.md",
            "catalogue/02-underspecified.md",
            "catalogue/03-promotion-candidates.md",
            "compositions/README.md",
            "schema/loop-entry.schema.json",
            "scripts/score_catalogue.py",
        ):
            path = WB / rel
            self.assertTrue(path.is_file(), msg=f"missing {rel}")

    def test_catalogue_validates_clean(self) -> None:
        problems = self.mod.validate_catalogue(self.data, root=ROOT)
        self.assertEqual(problems, [], msg="\n".join(problems))

    def test_unique_ids(self) -> None:
        ids = [e["id"] for e in self.data["entries"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_scores_match_checklist(self) -> None:
        for e in self.data["entries"]:
            computed = self.mod.score_entry(e)
            self.assertEqual(
                computed,
                sum(1 for v in e["checklist"].values() if v is True),
                msg=e["id"],
            )
            self.assertGreaterEqual(computed, 0)
            self.assertLessEqual(computed, 10)

    def test_tier_a_entries_meet_gates(self) -> None:
        for e in self.data["entries"]:
            if e.get("tier") != "well_defined":
                continue
            self.assertTrue(
                self.mod.tier_a_gates_ok(e),
                msg=f"{e['id']} fails tier A gates (score={self.mod.score_entry(e)})",
            )

    def test_at_least_three_well_defined(self) -> None:
        n = sum(1 for e in self.data["entries"] if e.get("tier") == "well_defined")
        self.assertGreaterEqual(n, 3)

    def test_solidified_loops_are_well_defined(self) -> None:
        """Former tier-B loops must stay A after 2026-07-23 solidification."""
        required = {
            "loop-process-evaluation",
            "loop-income-wave1",
            "loop-repo-radar-harvest",
            "loop-session-lifecycle",
        }
        by_id = {e["id"]: e for e in self.data["entries"]}
        for eid in required:
            self.assertIn(eid, by_id)
            self.assertEqual(by_id[eid]["tier"], "well_defined", msg=eid)
            self.assertTrue(self.mod.tier_a_gates_ok(by_id[eid]), msg=eid)

    def test_process_eval_bin_help(self) -> None:
        import subprocess

        proc = subprocess.run(
            [str(ROOT / "bin" / "process-eval"), "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("preflight", proc.stdout)

    def test_required_tiers_present(self) -> None:
        """A and C must exist; B may be empty after solidification sweeps."""
        tiers = {e.get("tier") for e in self.data["entries"]}
        self.assertIn("well_defined", tiers)
        self.assertIn("candidate", tiers)
        # underspecified optional
        for t in tiers:
            self.assertIn(t, {"well_defined", "underspecified", "candidate"})

    def test_schema_file_lists_checklist_keys(self) -> None:
        text = SCHEMA.read_text(encoding="utf-8")
        for key in self.mod.CHECKLIST_KEYS:
            self.assertIn(key, text)

    def test_cli_score_script_exits_zero(self) -> None:
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
