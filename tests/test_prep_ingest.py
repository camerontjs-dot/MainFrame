from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREP_PATH = ROOT / "01_ingest" / "prep_ingest.py"
SPEC = importlib.util.spec_from_file_location("prep_ingest", PREP_PATH)
assert SPEC and SPEC.loader
prep_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prep_module
SPEC.loader.exec_module(prep_module)

PrepIngest = prep_module.PrepIngest


def enriched_note(
    domain: str = "ai-systems",
    item_type: str = "note",
    status: str = "extracted",
    title: str = "Enriched Note",
) -> str:
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            f'domain: "{domain}"',
            f'type: "{item_type}"',
            f'status: "{status}"',
            'source: "00_inbox/raw-clipping.md"',
            'tags: ["draft", "ai"]',
            'links: ["related-note"]',
            "---",
            "",
            "# Enriched Note",
            "",
            "Body content.",
            "",
        ]
    )


class PrepIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for directory in (
            "01_ingest/queue",
            "01_ingest/ready",
            "10_knowledge/ai-systems",
            "10_knowledge/productivity-systems",
            "10_knowledge/robotics",
        ):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        self.prep = PrepIngest(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_ready(self, name: str, content: str) -> Path:
        path = self.root / "01_ingest" / "ready" / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_promotes_valid_extracted_file_to_queue(self) -> None:
        source = self._write_ready(
            "2026-05-27__ai-systems__note__enriched-clipping.md",
            enriched_note(),
        )

        result = self.prep.run(apply=True)

        target = self.root / "01_ingest" / "queue" / source.name
        self.assertTrue(result.ok)
        self.assertFalse(source.exists())
        self.assertTrue(target.exists())
        self.assertIn("promote", [event.kind for event in result.events])

    def test_dry_run_does_not_move_files(self) -> None:
        source = self._write_ready(
            "2026-05-27__ai-systems__note__enriched-clipping.md",
            enriched_note(),
        )

        result = self.prep.run(apply=False)

        target = self.root / "01_ingest" / "queue" / source.name
        self.assertTrue(result.ok)
        self.assertTrue(source.exists())
        self.assertFalse(target.exists())
        self.assertIn("promote", [event.kind for event in result.events])

    def test_blocks_partial_frontmatter(self) -> None:
        source = self._write_ready(
            "2026-05-27__ai-systems__note__partial.md",
            "\n".join(
                [
                    "---",
                    'title: "Partial"',
                    'domain: "ai-systems"',
                    'type: "note"',
                    'status: "extracted"',
                    "---",
                    "",
                ]
            ),
        )

        result = self.prep.run(apply=True)

        target = self.root / "01_ingest" / "queue" / source.name
        self.assertFalse(result.ok)
        self.assertTrue(source.exists())
        self.assertFalse(target.exists())
        self.assertEqual(result.events[0].kind, "blocked")
        self.assertIn("frontmatter not ready", result.events[0].message)

    def test_blocks_non_extracted_status(self) -> None:
        source = self._write_ready(
            "2026-05-27__ai-systems__note__premature.md",
            enriched_note(status="skimmed"),
        )

        result = self.prep.run(apply=True)

        self.assertFalse(result.ok)
        self.assertTrue(source.exists())
        self.assertEqual(result.events[0].kind, "blocked")
        self.assertIn("status must be 'extracted'", result.events[0].message)

    def test_blocks_malformed_filename(self) -> None:
        source = self._write_ready(
            "just-a-slug.md",
            enriched_note(),
        )

        result = self.prep.run(apply=True)

        self.assertFalse(result.ok)
        self.assertTrue(source.exists())
        self.assertEqual(result.events[0].kind, "blocked")
        self.assertIn("filename must match", result.events[0].message)

    def test_blocks_filename_domain_mismatch(self) -> None:
        source = self._write_ready(
            "2026-05-27__robotics__note__wrong-domain.md",
            enriched_note(domain="ai-systems"),
        )

        result = self.prep.run(apply=True)

        self.assertFalse(result.ok)
        self.assertTrue(source.exists())
        self.assertIn("filename domain", result.events[0].message)

    def test_blocks_unknown_domain(self) -> None:
        source = self._write_ready(
            "2026-05-27__mythics__note__unknown.md",
            enriched_note(domain="mythics"),
        )

        result = self.prep.run(apply=True)

        self.assertFalse(result.ok)
        self.assertTrue(source.exists())
        self.assertIn("unknown knowledge domain", result.events[0].message)

    def test_blocks_destination_collision(self) -> None:
        source = self._write_ready(
            "2026-05-27__ai-systems__note__enriched-clipping.md",
            enriched_note(),
        )
        target = self.root / "01_ingest" / "queue" / source.name
        target.write_text("preexisting\n", encoding="utf-8")

        result = self.prep.run(apply=True)

        self.assertFalse(result.ok)
        self.assertTrue(source.exists())
        self.assertEqual(target.read_text(encoding="utf-8"), "preexisting\n")
        self.assertEqual(result.events[0].kind, "blocked")
        self.assertIn("queue destination already exists", result.events[0].message)

    def test_empty_ready_directory_is_ok(self) -> None:
        result = self.prep.run(apply=True)

        self.assertTrue(result.ok)
        self.assertEqual(result.events, [])


if __name__ == "__main__":
    unittest.main()
