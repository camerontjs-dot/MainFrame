from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "bin" / "extract-knowledge"
LOADER = SourceFileLoader("extract_knowledge", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

run_extract = mod.run_extract
slugify = mod.slugify


def make_project(root: Path, slug: str = "test-proj",
                 log: bool = True, decisions: bool = True) -> None:
    proj = root / "30_projects" / slug
    proj.mkdir(parents=True)
    (proj / "README.md").write_text("# Test Project\n", encoding="utf-8")
    if log:
        (proj / "log.md").write_text("# Log\n", encoding="utf-8")
    if decisions:
        (proj / "decisions.md").write_text("# Decisions\n", encoding="utf-8")


def make_domain(root: Path, domain: str = "ai-systems") -> None:
    (root / "10_knowledge" / domain).mkdir(parents=True)


class SlugifyTests(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(slugify("My Great Insight"), "my-great-insight")

    def test_special_chars(self) -> None:
        self.assertEqual(slugify("Test: A (thing)!"), "test-a-thing")

    def test_leading_trailing(self) -> None:
        self.assertEqual(slugify("  --hello-- "), "hello")


class ExtractKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_all_prerequisites_met(self) -> None:
        make_project(self.root)
        make_domain(self.root)
        result = run_extract(self.root, "test-proj", "ai-systems",
                             "Test Note", ["extracted"])
        self.assertTrue(result.ok)
        self.assertFalse(result.written)
        self.assertIn("ai-systems", result.target_path)

    def test_missing_project_dir(self) -> None:
        make_domain(self.root)
        result = run_extract(self.root, "nonexistent", "ai-systems",
                             "Test Note", ["extracted"])
        self.assertFalse(result.ok)
        failed = [p for p in result.prerequisites if not p.exists and p.required]
        self.assertTrue(len(failed) >= 1)

    def test_missing_readme(self) -> None:
        proj = self.root / "30_projects" / "test-proj"
        proj.mkdir(parents=True)
        make_domain(self.root)
        result = run_extract(self.root, "test-proj", "ai-systems",
                             "Test Note", ["extracted"])
        self.assertFalse(result.ok)
        readme_prereq = [p for p in result.prerequisites
                         if p.name == "project README"][0]
        self.assertFalse(readme_prereq.exists)
        self.assertTrue(readme_prereq.required)

    def test_missing_log_warns_but_ok(self) -> None:
        make_project(self.root, log=False)
        make_domain(self.root)
        result = run_extract(self.root, "test-proj", "ai-systems",
                             "Test Note", ["extracted"])
        self.assertTrue(result.ok)
        log_prereq = [p for p in result.prerequisites
                      if p.name == "project log"][0]
        self.assertFalse(log_prereq.exists)
        self.assertFalse(log_prereq.required)

    def test_missing_decisions_warns_but_ok(self) -> None:
        make_project(self.root, decisions=False)
        make_domain(self.root)
        result = run_extract(self.root, "test-proj", "ai-systems",
                             "Test Note", ["extracted"])
        self.assertTrue(result.ok)
        dec_prereq = [p for p in result.prerequisites
                      if p.name == "project decisions"][0]
        self.assertFalse(dec_prereq.exists)
        self.assertFalse(dec_prereq.required)

    def test_unknown_domain(self) -> None:
        make_project(self.root)
        result = run_extract(self.root, "test-proj", "unknown-domain",
                             "Test Note", ["extracted"])
        self.assertFalse(result.ok)
        domain_prereq = [p for p in result.prerequisites
                         if p.name == "knowledge domain"][0]
        self.assertFalse(domain_prereq.exists)

    def test_write_creates_scaffold(self) -> None:
        make_project(self.root)
        make_domain(self.root)
        result = run_extract(self.root, "test-proj", "ai-systems",
                             "Test Note", ["extracted"], write=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.written)
        target = self.root / result.target_path
        self.assertTrue(target.exists())
        content = target.read_text(encoding="utf-8")
        self.assertIn('title: "Test Note"', content)
        self.assertIn('domain: "ai-systems"', content)
        self.assertIn('type: "note"', content)
        self.assertIn('status: "queued"', content)
        self.assertIn('source: "30_projects/test-proj/README.md"', content)
        self.assertIn("# Test Note", content)

    def test_collision_blocks_write(self) -> None:
        make_project(self.root)
        make_domain(self.root)
        result1 = run_extract(self.root, "test-proj", "ai-systems",
                              "Test Note", ["extracted"], write=True)
        self.assertTrue(result1.written)

        result2 = run_extract(self.root, "test-proj", "ai-systems",
                              "Test Note", ["extracted"], write=True)
        self.assertFalse(result2.ok)
        self.assertTrue(result2.collision)
        self.assertFalse(result2.written)

    def test_title_slugification_in_filename(self) -> None:
        make_project(self.root)
        make_domain(self.root)
        result = run_extract(self.root, "test-proj", "ai-systems",
                             "My Great Insight", ["extracted"])
        self.assertIn("my-great-insight", result.target_path)

    def test_custom_tags(self) -> None:
        make_project(self.root)
        make_domain(self.root)
        result = run_extract(self.root, "test-proj", "ai-systems",
                             "Test Note", ["foo", "bar"], write=True)
        target = self.root / result.target_path
        content = target.read_text(encoding="utf-8")
        self.assertIn('["foo", "bar"]', content)

    def test_check_mode_does_not_write(self) -> None:
        make_project(self.root)
        make_domain(self.root)
        result = run_extract(self.root, "test-proj", "ai-systems",
                             "Test Note", ["extracted"], write=False)
        self.assertTrue(result.ok)
        self.assertFalse(result.written)
        target = self.root / result.target_path
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
