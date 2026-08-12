from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "bin" / "sync-project-index"
LOADER = SourceFileLoader("sync_project_index", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


README_TEMPLATE = """\
---
title: "{title}"
project_state: "{state}"
goal: "Do the thing"
next_action: "{next_action}"
updated: "2026-06-01"
{wip_class_line}---

# {title}
"""


class ValidateProjectsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = Path(self.tmp.name) / "30_projects"
        self.projects.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def add_project(
        self,
        name: str,
        state: str = "active",
        next_action: str = "Do the next step",
        age_days: float = 0.0,
        frontmatter: bool = True,
        wip_class: str | None = None,
    ) -> Path:
        project = self.projects / name
        project.mkdir()
        readme = project / "README.md"
        if frontmatter:
            wip_line = f'wip_class: "{wip_class}"\n' if wip_class else ""
            readme.write_text(
                README_TEMPLATE.format(
                    title=name,
                    state=state,
                    next_action=next_action,
                    wip_class_line=wip_line,
                ),
                encoding="utf-8",
            )
        else:
            readme.write_text(f"# {name}\n\nNo frontmatter here.\n",
                              encoding="utf-8")
        if age_days:
            old_ts = (datetime.now() - timedelta(days=age_days)).timestamp()
            os.utime(readme, (old_ts, old_ts))
            os.utime(project, (old_ts, old_ts))
        return project

    def problems(self, **kwargs) -> list[str]:
        return mod.validate_projects(self.projects, **kwargs)

    def test_fresh_active_passes(self) -> None:
        self.add_project("hot-project")
        self.assertEqual(self.problems(), [])

    def test_idle_active_fails_loudly(self) -> None:
        self.add_project("stale-project", age_days=20)
        problems = self.problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("stale-project: active but idle", problems[0])
        self.assertIn("pause it", problems[0])

    def test_nested_repo_commit_counts_as_evidence(self) -> None:
        project = self.add_project("repo-project", age_days=20)
        subprocess.run(["git", "-C", str(project), "init", "-q", "-b", "main"],
                       check=True)
        subprocess.run(["git", "-C", str(project), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(project), "-c", "user.email=t@t", "-c",
             "user.name=t", "commit", "-q", "-m", "fresh work"],
            check=True)
        # File mtimes are 20d old, but the commit is from just now.
        self.assertEqual(self.problems(), [])

    def test_missing_frontmatter_flagged(self) -> None:
        self.add_project("bare-project", frontmatter=False)
        problems = self.problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("bare-project: missing project_state", problems[0])

    def test_missing_readme_flagged(self) -> None:
        (self.projects / "empty-project").mkdir()
        problems = self.problems()
        self.assertIn("empty-project: missing README.md", problems)

    def test_unknown_state_flagged(self) -> None:
        self.add_project("weird-project", state="wip")
        problems = self.problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("unknown project_state 'wip'", problems[0])

    def test_paused_requires_reentry_pointer(self) -> None:
        self.add_project("shelved-ok", state="paused",
                         next_action="Reread plans/reentry.md")
        self.add_project("shelved-bare", state="paused", next_action="")
        problems = self.problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("shelved-bare: paused without next_action", problems[0])

    def test_active_requires_next_action(self) -> None:
        self.add_project("aimless", next_action="")
        problems = self.problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("aimless: active without next_action", problems[0])

    def test_product_wip_cap_breach(self) -> None:
        for i in range(6):
            self.add_project(f"proj-{i}", wip_class="product")
        problems = self.problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("product WIP cap breach: 6 active product projects (cap 5)", problems[0])
        for i in range(6):
            self.assertIn(f"proj-{i}", problems[0])

    def test_product_wip_cap_boundary_passes(self) -> None:
        for i in range(5):
            self.add_project(f"proj-{i}", wip_class="product")
        self.assertEqual(self.problems(), [])

    def test_eval_actives_do_not_consume_product_seats(self) -> None:
        for i in range(5):
            self.add_project(f"product-{i}", wip_class="product")
        for i in range(5):
            self.add_project(f"metric-{i}-eval")  # suffix heuristic → eval
        self.assertEqual(self.problems(), [])

    def test_total_active_cap_breach(self) -> None:
        for i in range(5):
            self.add_project(f"product-{i}", wip_class="product")
        for i in range(6):
            self.add_project(f"suite-{i}-eval")
        problems = self.problems()
        self.assertTrue(any("total active cap breach: 11" in p for p in problems), problems)

    def test_default_eval_slug_set(self) -> None:
        for i in range(5):
            self.add_project(f"product-{i}", wip_class="product")
        # claim-audit-lab is in DEFAULT_EVAL_SLUGS (no -eval suffix)
        self.add_project("claim-audit-lab")
        self.assertEqual(self.problems(), [])

    def test_explicit_wip_class_overrides_suffix(self) -> None:
        # Force a *-eval slug into product pool — counts toward product cap.
        for i in range(5):
            self.add_project(f"other-{i}", wip_class="product")
        self.add_project("forced-eval", wip_class="product")
        problems = self.problems()
        self.assertTrue(any("product WIP cap breach" in p for p in problems), problems)

    def test_anchor_does_not_consume_product_or_total_seats(self) -> None:
        for i in range(5):
            self.add_project(f"product-{i}", wip_class="product")
        for i in range(5):
            self.add_project(f"suite-{i}-eval")
        self.add_project("income-engine")  # default anchor
        self.assertEqual(self.problems(), [])

    def test_non_active_states_have_no_evidence_rule(self) -> None:
        self.add_project("old-shipped", state="shipped", age_days=90)
        self.add_project("old-planned", state="planned", age_days=90)
        self.add_project("old-suspended", state="suspended", age_days=90)
        self.assertEqual(self.problems(), [])

    def test_only_scopes_to_single_project(self) -> None:
        self.add_project("healthy", state="shipped")
        self.add_project("broken", frontmatter=False)
        self.assertEqual(self.problems(only="healthy"), [])
        problems = self.problems(only="broken")
        self.assertEqual(len(problems), 1)
        self.assertIn("broken: missing project_state frontmatter", problems[0])

    def test_only_missing_directory_is_a_problem(self) -> None:
        problems = self.problems(only="no-such-project")
        self.assertEqual(
            problems, ["no-such-project: project directory does not exist"])

    def test_only_skips_wip_cap(self) -> None:
        for i in range(6):
            self.add_project(f"proj-{i}")
        self.assertEqual(self.problems(only="proj-0"), [])


class RenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = Path(self.tmp.name) / "30_projects"
        self.projects.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_render_includes_evidence_column(self) -> None:
        project = self.projects / "alpha"
        project.mkdir()
        (project / "README.md").write_text(
            README_TEMPLATE.format(
                title="Alpha",
                state="active",
                next_action="Next",
                wip_class_line="",
            ),
            encoding="utf-8",
        )
        output = mod.render(self.projects)
        self.assertIn("| Project | State | Goal | Next action | Updated | Evidence |",
                      output)
        today = datetime.now().date().isoformat()
        self.assertIn(f"| {today} |", output)


if __name__ == "__main__":
    unittest.main()
