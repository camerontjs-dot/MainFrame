from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MAINFRAME_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = MAINFRAME_ROOT / "scripts" / "mindgraph_link_audit.py"
SPEC = importlib.util.spec_from_file_location("mindgraph_link_audit", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class LinkAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "10_knowledge" / "alpha").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, relative: str, body: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def test_resolves_supported_typed_link_and_flags_raw_leaf(self) -> None:
        self.write(
            "10_knowledge/alpha/2026-01-01__alpha__raw__source.md",
            "---\ntitle: Source\ndomain: alpha\ntype: raw\nstatus: queued\nsource: manual\ntags: []\n---\n# Source\n",
        )
        self.write(
            "10_knowledge/alpha/2026-01-02__alpha__note__synthesis.md",
            "---\ntitle: Synthesis\ndomain: alpha\ntype: note\nstatus: stable\nsource: manual\ntags: []\n---\n# Synthesis\nEvidence: [[source]] (evidence)\n",
        )
        result = module.audit(self.root, self.root / "10_knowledge", "test")
        self.assertEqual(result["summary"]["link_classification_counts"], {"resolved": 1})
        self.assertEqual(result["summary"]["document_finding_counts"], {"raw evidence leaf": 1})
        self.assertTrue(result["links"][0]["relationship_supported"])
        self.assertIn("raw evidence leaf", module.markdown_report(result))
        self.assertFalse(result["mutating"])

    def test_ambiguous_and_external_are_abstentions(self) -> None:
        note = "---\ntitle: Note\ndomain: alpha\ntype: note\nstatus: stable\nsource: manual\ntags: []\n---\n# Note\nSee [[same]] and [[30_projects/demo/README.md]].\n"
        self.write("10_knowledge/alpha/2026-01-01__alpha__note__one.md", note)
        self.write("10_knowledge/alpha/2026-01-02__alpha__note__same.md", "---\ntitle: A\ndomain: alpha\ntype: note\n---\n")
        self.write("10_knowledge/beta/2026-01-03__beta__raw__same.md", "---\ntitle: B\ndomain: beta\ntype: raw\n---\n")
        result = module.audit(self.root, self.root / "10_knowledge", "test")
        counts = result["summary"]["link_classification_counts"]
        self.assertEqual(counts["ambiguous"], 1)
        self.assertEqual(counts["external/cross-lifecycle"], 1)

    def test_unique_alias_is_resolved_without_rewrite(self) -> None:
        self.write(
            "10_knowledge/alpha/2026-01-01__alpha__note__one.md",
            "---\ntitle: One\ndomain: alpha\ntype: note\n---\n# One\nSee [[renamed-target]].\n",
        )
        self.write(
            "10_knowledge/alpha/2026-01-02__alpha__note__renamed-target.md",
            "---\ntitle: Renamed\ndomain: alpha\ntype: note\n---\n# Renamed\n",
        )
        result = module.audit(self.root, self.root / "10_knowledge", "test")
        row = next(row for row in result["links"] if row["raw_link_target"] == "renamed-target")
        self.assertEqual(row["target_resolution_status"], "resolved")
        self.assertIsNone(row["repair_candidate"])
        kind, candidates = module.candidate_paths(
            "renamed-target",
            {"10_knowledge/alpha/2026-01-02__alpha__note__renamed-target.md"},
        )
        self.assertEqual(kind, "same-canonical-slug")
        self.assertEqual(len(candidates), 1)

    def test_same_channel_duplicates_and_metadata_gap_are_reported_without_rewrite(self) -> None:
        self.write(
            "10_knowledge/alpha/2026-01-01__alpha__note__one.md",
            "---\ntitle: One\ntype: note\n---\n# One\nAgain [[target]]. Again [[target]].\n",
        )
        self.write(
            "10_knowledge/alpha/2026-01-02__alpha__note__target.md",
            "---\ntitle: Target\ndomain: alpha\ntype: note\n---\n# Target\n",
        )
        before = (self.root / "10_knowledge/alpha/2026-01-01__alpha__note__one.md").read_bytes()
        result = module.audit(self.root, self.root / "10_knowledge", "test")
        after = (self.root / "10_knowledge/alpha/2026-01-01__alpha__note__one.md").read_bytes()
        self.assertEqual(result["summary"]["duplicate_link_count"], 2)
        self.assertEqual(result["summary"]["metadata_gap_count"], 1)
        self.assertEqual(before, after)

    def test_body_frontmatter_mirror_is_informational_not_duplicate(self) -> None:
        self.write(
            "10_knowledge/alpha/2026-01-01__alpha__note__one.md",
            "---\ntitle: One\ndomain: alpha\ntype: note\nlinks: [target]\n---\n# One\nSee [[target]].\n",
        )
        self.write(
            "10_knowledge/alpha/2026-01-02__alpha__note__target.md",
            "---\ntitle: Target\ndomain: alpha\ntype: note\n---\n# Target\n",
        )
        result = module.audit(self.root, self.root / "10_knowledge", "test")
        self.assertEqual(result["summary"]["mirror_pair_count"], 1)
        self.assertEqual(result["summary"]["duplicate_link_count"], 0)
        self.assertTrue(all(row["mirror"] for row in result["links"]))

    def test_valid_curated_dispositions_are_reviewed_not_actionable(self) -> None:
        for disposition in ("reviewed-no-link", "standalone"):
            self.write(
                f"10_knowledge/alpha/2026-01-{len(disposition)}__alpha__note__{disposition}.md",
                f"---\ntitle: {disposition}\ndomain: alpha\ntype: note\ngraph_disposition: {disposition}\n---\n# {disposition}\n",
            )
        self.write(
            "10_knowledge/alpha/2026-01-20__alpha__note__needs-review.md",
            "---\ntitle: Needs review\ndomain: alpha\ntype: note\n---\n# Needs review\n",
        )
        result = module.audit(self.root, self.root / "10_knowledge", "test")
        findings = result["summary"]["document_finding_counts"]
        self.assertEqual(findings["curated no-outbound reviewed"], 2)
        self.assertEqual(findings["curated no-outbound"], 1)
        reviewed = [row for row in result["documents"] if not row["actionable"]]
        actionable = [row for row in result["documents"] if row["actionable"]]
        self.assertEqual({row["graph_disposition"] for row in reviewed}, {"reviewed-no-link", "standalone"})
        self.assertEqual(len(actionable), 1)
