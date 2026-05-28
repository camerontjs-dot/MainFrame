from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MINION_PATH = ROOT / "01_ingest" / "minion.py"
SPEC = importlib.util.spec_from_file_location("ingest_minion", MINION_PATH)
assert SPEC and SPEC.loader
minion_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = minion_module
SPEC.loader.exec_module(minion_module)

IngestMinion = minion_module.IngestMinion


def valid_note(domain: str = "ai-systems", item_type: str = "note", status: str = "queued") -> str:
    return "\n".join(
        [
            "---",
            'title: "Example Note"',
            f'domain: "{domain}"',
            f'type: "{item_type}"',
            f'status: "{status}"',
            'source: "manual test source"',
            'tags: ["test", "ingest"]',
            "links: []",
            "---",
            "",
            "# Example Note",
            "",
        ]
    )


class IngestMinionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for directory in (
            "00_inbox",
            "01_ingest/queue",
            "01_ingest/ready",
            "01_ingest/rejected",
            "10_knowledge/ai-systems/raw",
            "10_knowledge/productivity-systems/raw",
            "10_knowledge/robotics/raw",
        ):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        self.minion = IngestMinion(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_routes_valid_markdown_from_inbox_through_queue(self) -> None:
        source = self.root / "00_inbox" / "2026-05-23__ai-systems__note__example.md"
        source.write_text(valid_note(), encoding="utf-8")

        result = self.minion.run(apply=True)

        target = self.root / "10_knowledge" / "ai-systems" / source.name
        self.assertTrue(result.ok)
        self.assertFalse(source.exists())
        self.assertFalse((self.root / "01_ingest" / "queue" / source.name).exists())
        self.assertTrue(target.exists())
        self.assertEqual(target.read_text(encoding="utf-8"), valid_note())
        self.assertIn("stage", [event.kind for event in result.events])
        self.assertIn("route", [event.kind for event in result.events])

    def test_dry_run_does_not_move_files(self) -> None:
        source = self.root / "00_inbox" / "2026-05-23__ai-systems__note__example.md"
        source.write_text(valid_note(), encoding="utf-8")

        result = self.minion.run(apply=False)

        target = self.root / "10_knowledge" / "ai-systems" / source.name
        self.assertTrue(result.ok)
        self.assertTrue(source.exists())
        self.assertFalse(target.exists())
        self.assertIn("stage", [event.kind for event in result.events])
        self.assertIn("route", [event.kind for event in result.events])

    def test_extracted_status_routes_directly_to_queue(self) -> None:
        source = self.root / "00_inbox" / "2026-05-24__ai-systems__note__agent-enriched.md"
        source.write_text(valid_note(status="extracted"), encoding="utf-8")

        result = self.minion.run(apply=True)

        target = self.root / "10_knowledge" / "ai-systems" / source.name
        self.assertTrue(result.ok)
        self.assertTrue(target.exists())
        self.assertNotIn("normalize", [event.kind for event in result.events])
        self.assertIn("stage", [event.kind for event in result.events])
        self.assertIn("route", [event.kind for event in result.events])

    def test_inbox_no_frontmatter_is_normalized_to_ready(self) -> None:
        source = self.root / "00_inbox" / "raw-clipping.md"
        source.write_text("# Loose Thought\n\nA half-formed idea.\n", encoding="utf-8")

        result = self.minion.run(apply=True)

        ready_target = self.root / "01_ingest" / "ready" / source.name
        rejected = self.root / "01_ingest" / "rejected" / source.name
        self.assertTrue(result.ok)
        self.assertFalse(source.exists())
        self.assertFalse(rejected.exists())
        self.assertTrue(ready_target.exists())

        body = ready_target.read_text(encoding="utf-8")
        self.assertIn('title: "Loose Thought"', body)
        self.assertIn('type: "note"', body)
        self.assertIn('status: "skimmed"', body)
        self.assertIn('domain: ""', body)
        self.assertIn(f'source: "00_inbox/{source.name}"', body)
        self.assertIn("tags: []", body)
        self.assertIn("links: []", body)
        self.assertIn("# Loose Thought", body)
        self.assertIn("normalize", [event.kind for event in result.events])

    def test_inbox_partial_frontmatter_is_normalized_to_ready(self) -> None:
        source = self.root / "00_inbox" / "partial.md"
        source.write_text(
            "\n".join(
                [
                    "---",
                    'title: "Existing Title"',
                    'tags: ["draft"]',
                    "---",
                    "",
                    "Body paragraph.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.minion.run(apply=True)

        ready_target = self.root / "01_ingest" / "ready" / source.name
        self.assertTrue(result.ok)
        self.assertTrue(ready_target.exists())

        body = ready_target.read_text(encoding="utf-8")
        # Preserves what the author wrote
        self.assertIn('title: "Existing Title"', body)
        self.assertIn('tags: ["draft"]', body)
        # Fills missing required keys with defaults
        self.assertIn('type: "note"', body)
        self.assertIn('status: "skimmed"', body)
        self.assertIn('domain: ""', body)
        self.assertIn(f'source: "00_inbox/{source.name}"', body)
        self.assertIn("links: []", body)
        self.assertIn("normalize", [event.kind for event in result.events])

    def test_inbox_wikilinks_extracted_to_links_field(self) -> None:
        source = self.root / "00_inbox" / "with-links.md"
        source.write_text(
            "\n".join(
                [
                    "# Note With Links",
                    "",
                    "Refers to [[mindgraph-design]] and [[robot-cell|the new cell]].",
                    "",
                    "Also [[mindgraph-design]] again to test dedup.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.minion.run(apply=True)

        ready_target = self.root / "01_ingest" / "ready" / source.name
        self.assertTrue(result.ok)
        self.assertTrue(ready_target.exists())

        body = ready_target.read_text(encoding="utf-8")
        self.assertIn('links: ["mindgraph-design", "robot-cell"]', body)
        # The body itself is preserved verbatim (still contains the raw wikilinks).
        self.assertIn("[[mindgraph-design]]", body)
        self.assertIn("[[robot-cell|the new cell]]", body)

    def test_queue_missing_frontmatter_is_rejected(self) -> None:
        source = self.root / "01_ingest" / "queue" / "missing-frontmatter.md"
        source.write_text("# Missing frontmatter\n", encoding="utf-8")

        result = self.minion.run(apply=True)

        rejected = self.root / "01_ingest" / "rejected" / source.name
        self.assertFalse(result.ok)
        self.assertFalse(source.exists())
        self.assertTrue(rejected.exists())
        self.assertEqual(result.events[0].kind, "reject")

    def test_unknown_domain_is_rejected(self) -> None:
        source = self.root / "01_ingest" / "queue" / "2026-05-23__unknown__note__example.md"
        source.write_text(valid_note(domain="unknown"), encoding="utf-8")

        result = self.minion.run(apply=True)

        rejected = self.root / "01_ingest" / "rejected" / source.name
        self.assertFalse(result.ok)
        self.assertFalse(source.exists())
        self.assertTrue(rejected.exists())
        self.assertIn("unknown knowledge domain", result.events[0].message)

    def test_convention_named_pdf_creates_raw_file_and_stub(self) -> None:
        source = self.root / "00_inbox" / "2026-05-21__ai-systems__raw__sample-paper.pdf"
        source.write_bytes(b"%PDF-1.4\n")

        result = self.minion.run(apply=True)

        raw = self.root / "10_knowledge" / "ai-systems" / "raw" / source.name
        stub = (
            self.root
            / "10_knowledge"
            / "ai-systems"
            / "2026-05-21__ai-systems__raw__sample-paper.md"
        )
        self.assertTrue(result.ok)
        self.assertFalse(source.exists())
        self.assertTrue(raw.exists())
        self.assertTrue(stub.exists())
        stub_text = stub.read_text(encoding="utf-8")
        self.assertIn('title: "Sample Paper"', stub_text)
        self.assertIn('domain: "ai-systems"', stub_text)
        self.assertIn('source: "./raw/2026-05-21__ai-systems__raw__sample-paper.pdf"', stub_text)
        self.assertIn('tags: ["pdf", "evidence"]', stub_text)

    def test_destination_collision_blocks_without_overwrite(self) -> None:
        source = self.root / "01_ingest" / "queue" / "2026-05-23__ai-systems__note__example.md"
        target = self.root / "10_knowledge" / "ai-systems" / source.name
        source.write_text(valid_note(), encoding="utf-8")
        target.write_text("existing content\n", encoding="utf-8")

        result = self.minion.run(apply=True)

        self.assertFalse(result.ok)
        self.assertTrue(source.exists())
        self.assertEqual(target.read_text(encoding="utf-8"), "existing content\n")
        self.assertEqual(result.events[0].kind, "blocked")


if __name__ == "__main__":
    unittest.main()
