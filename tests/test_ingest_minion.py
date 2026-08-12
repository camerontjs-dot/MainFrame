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
FrontmatterError = minion_module.FrontmatterError
validate_strict = minion_module.validate_strict


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


def pdf_bytes_with_metadata(
    *,
    title: str = "Metadata Title",
    author: str = "Ada Lovelace",
    subject: str = "Metadata subject",
    keywords: str = "agentic systems, pdf metadata",
    creation_date: str = "D:20260528112233-04'00'",
) -> bytes:
    return "\n".join(
        [
            "%PDF-1.4",
            "1 0 obj",
            "<<",
            f"/Title ({title})",
            f"/Author ({author})",
            f"/Subject ({subject})",
            f"/Keywords ({keywords})",
            f"/CreationDate ({creation_date})",
            ">>",
            "endobj",
            "trailer",
            "<< /Info 1 0 R >>",
            "%%EOF",
        ]
    ).encode("utf-8")


class FrontmatterValidationTests(unittest.TestCase):
    def test_strict_validation_rejects_blank_tag_values(self) -> None:
        metadata = {
            "title": "Example Note",
            "domain": "ai-systems",
            "type": "note",
            "status": "queued",
            "source": "manual test source",
            "tags": ["test", "   "],
        }

        with self.assertRaisesRegex(FrontmatterError, "only non-empty strings"):
            validate_strict(metadata)

    def test_strip_quotes_accepts_backticks_and_trims_wrappers(self) -> None:
        self.assertEqual(minion_module.strip_quotes("` Example title `"), "Example title")
        self.assertEqual(minion_module.strip_quotes("' Example source '"), "Example source")


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

    def test_reserved_operational_files_are_not_ingested(self) -> None:
        """A contract file in 00_inbox governs the folder; it is not a capture.

        Before 2026-08-10 the scanner returned every non-dotfile, so an
        `AGENTS.md` written into `00_inbox/` to govern that folder was
        normalized and moved to `01_ingest/ready/` on the first apply. The
        contract silently migrated out of the folder it governed. The scanner
        had no concept of a non-capture file, and treated presence in a
        directory as intent to ingest.
        """
        for name in ("AGENTS.md", "README.md", "index.md", "agents.md"):
            (self.root / "00_inbox" / name).write_text(
                valid_note(), encoding="utf-8"
            )
        capture = self.root / "00_inbox" / "real-capture.md"
        capture.write_text(valid_note(), encoding="utf-8")

        found = {p.name for p in self.minion._files_in(self.root / "00_inbox")}

        self.assertEqual(found, {"real-capture.md"})
        for name in ("AGENTS.md", "README.md", "index.md", "agents.md"):
            self.assertTrue(
                (self.root / "00_inbox" / name).exists(),
                f"{name} must stay where it was written",
            )

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

    def test_inbox_empty_tags_requires_enrichment_instead_of_routing(self) -> None:
        source = self.root / "00_inbox" / "2026-05-24__ai-systems__note__untagged.md"
        source.write_text(
            valid_note().replace('tags: ["test", "ingest"]', "tags: []"),
            encoding="utf-8",
        )

        result = self.minion.run(apply=True)

        ready_target = self.root / "01_ingest" / "ready" / source.name
        durable_target = self.root / "10_knowledge" / "ai-systems" / source.name
        self.assertTrue(result.ok)
        self.assertTrue(ready_target.exists())
        self.assertFalse(durable_target.exists())
        self.assertIn("tags: []", ready_target.read_text(encoding="utf-8"))

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

    def test_inbox_block_list_frontmatter_is_normalized_to_ready(self) -> None:
        source = self.root / "00_inbox" / "clipping.md"
        source.write_text(
            "\n".join(
                [
                    "---",
                    'title: "Existing Clipping"',
                    "author:",
                    '  - "[[@source-author]]"',
                    "tags:",
                    '  - "clippings"',
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
        self.assertIn('title: "Existing Clipping"', body)
        self.assertIn('tags: ["clippings"]', body)
        self.assertIn('author: ["[[@source-author]]"]', body)
        self.assertIn('status: "skimmed"', body)
        self.assertIn("Body paragraph.", body)

    def test_inbox_malformed_frontmatter_stages_to_ready_with_warning(self) -> None:
        source = self.root / "00_inbox" / "bad-frontmatter.md"
        source.write_text(
            "\n".join(
                [
                    "---",
                    'title: "Broken Capture"',
                    "not valid yaml structure",
                    "---",
                    "",
                    "Captured body.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.minion.run(apply=True)

        ready_target = self.root / "01_ingest" / "ready" / source.name
        rejected = self.root / "01_ingest" / "rejected" / source.name
        self.assertTrue(result.ok)
        self.assertFalse(rejected.exists())
        self.assertTrue(ready_target.exists())
        self.assertEqual(result.events[0].kind, "normalize")
        self.assertEqual(result.events[0].severity, "warning")
        self.assertIn("frontmatter needs agent repair", result.events[0].message)

        body = ready_target.read_text(encoding="utf-8")
        self.assertIn('title: "Bad Frontmatter"', body)
        self.assertIn("---\ntitle: \"Broken Capture\"\nnot valid yaml structure\n---", body)
        self.assertIn("Captured body.", body)

    def test_inbox_unknown_domain_stages_to_ready_with_warning(self) -> None:
        source = self.root / "00_inbox" / "2026-05-23__new-domain__note__example.md"
        source.write_text(valid_note(domain="new-domain"), encoding="utf-8")

        result = self.minion.run(apply=True)

        ready_target = self.root / "01_ingest" / "ready" / source.name
        rejected = self.root / "01_ingest" / "rejected" / source.name
        target = self.root / "10_knowledge" / "new-domain" / source.name
        self.assertTrue(result.ok)
        self.assertFalse(rejected.exists())
        self.assertFalse(target.exists())
        self.assertTrue(ready_target.exists())
        self.assertEqual(result.events[0].kind, "normalize")
        self.assertEqual(result.events[0].severity, "warning")
        self.assertIn("not established", result.events[0].message)

        body = ready_target.read_text(encoding="utf-8")
        self.assertIn('domain: "new-domain"', body)
        self.assertIn('status: "skimmed"', body)

    def test_wikilinks_inside_code_spans_are_ignored(self) -> None:
        source = self.root / "00_inbox" / "discusses-wikilinks.md"
        source.write_text(
            "\n".join(
                [
                    "# Note that talks about wikilinks",
                    "",
                    "Body refers to [[real-target]] as a real connection.",
                    "",
                    "But `[[inline-syntax-example]]` is just talking about the syntax.",
                    "",
                    "And the fenced block below is illustrative:",
                    "",
                    "```",
                    "tags: [\"author:[[@somebody]]\"]",
                    "see also [[fenced-example]]",
                    "```",
                    "",
                    "End paragraph also has [[real-target]] again (dedup).",
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
        self.assertIn('links: ["real-target"]', body)
        # Body itself is preserved verbatim — the code spans/blocks still appear.
        self.assertIn("`[[inline-syntax-example]]`", body)
        self.assertIn("[[fenced-example]]", body)

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
        self.assertIn('source_type: "pdf"', stub_text)

    def test_pdf_metadata_enriches_raw_stub(self) -> None:
        source = self.root / "00_inbox" / "2026-05-21__ai-systems__raw__sample-paper.pdf"
        source.write_bytes(pdf_bytes_with_metadata())

        result = self.minion.run(apply=True)

        stub = (
            self.root
            / "10_knowledge"
            / "ai-systems"
            / "2026-05-21__ai-systems__raw__sample-paper.md"
        )
        self.assertTrue(result.ok)
        stub_text = stub.read_text(encoding="utf-8")
        self.assertIn('title: "Metadata Title"', stub_text)
        self.assertIn('author: ["Ada Lovelace"]', stub_text)
        self.assertIn('description: "Metadata subject"', stub_text)
        self.assertIn('keywords: ["agentic systems", "pdf metadata"]', stub_text)
        self.assertIn('created: "2026-05-28"', stub_text)

    def test_malformed_pdf_octal_metadata_does_not_abort_routing(self) -> None:
        source = self.root / "00_inbox" / "2026-05-21__ai-systems__raw__sample-paper.pdf"
        source.write_bytes(pdf_bytes_with_metadata(title=r"Broken\777Title"))

        result = self.minion.run(apply=True)

        stub = (
            self.root
            / "10_knowledge"
            / "ai-systems"
            / "2026-05-21__ai-systems__raw__sample-paper.md"
        )
        self.assertTrue(result.ok)
        self.assertTrue(stub.exists())
        stub_text = stub.read_text(encoding="utf-8")
        self.assertIn('title: "Sample Paper"', stub_text)
        self.assertIn('author: ["Ada Lovelace"]', stub_text)

    def test_inbox_unconvention_named_pdf_suggests_without_rejecting(self) -> None:
        source = self.root / "00_inbox" / "Prompting in the Wild.pdf"
        source.write_bytes(pdf_bytes_with_metadata(title="Prompting Study"))

        result = self.minion.run(apply=True)

        rejected = self.root / "01_ingest" / "rejected" / source.name
        queued = self.root / "01_ingest" / "queue" / source.name
        self.assertTrue(result.ok)
        self.assertTrue(source.exists())
        self.assertFalse(rejected.exists())
        self.assertFalse(queued.exists())
        self.assertEqual(result.events[0].kind, "suggest")
        self.assertEqual(result.events[0].severity, "warning")
        self.assertIn("__<domain>__raw__prompting-in-the-wild.pdf", result.events[0].message)
        self.assertIn("metadata found: title: Prompting Study", result.events[0].message)

    def test_inbox_pdf_unknown_domain_suggests_without_rejecting(self) -> None:
        source = self.root / "00_inbox" / "2026-05-21__new-domain__raw__sample-paper.pdf"
        source.write_bytes(b"%PDF-1.4\n")

        result = self.minion.run(apply=True)

        rejected = self.root / "01_ingest" / "rejected" / source.name
        queued = self.root / "01_ingest" / "queue" / source.name
        self.assertTrue(result.ok)
        self.assertTrue(source.exists())
        self.assertFalse(rejected.exists())
        self.assertFalse(queued.exists())
        self.assertEqual(result.events[0].kind, "suggest")
        self.assertEqual(result.events[0].severity, "warning")
        self.assertIn("no matching 10_knowledge domain exists", result.events[0].message)

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

extract_wikilinks = minion_module.extract_wikilinks
_is_plausible_wikilink = minion_module._is_plausible_wikilink


class WikilinkExtractionTests(unittest.TestCase):
    """Regression tests for extract_wikilinks — especially unfenced code."""

    def test_unfenced_python_double_bracket_indexing_is_not_a_wikilink(self) -> None:
        """Repro case: df[['Open', 'High', 'Low', 'Close', 'Volume']]"""
        body = (
            "import pandas as pd\n"
            "df = pd.read_csv('data.csv')\n"
            "ohlcv = df[['Open', 'High', 'Low', 'Close', 'Volume']]\n"
            "filtered = df[['Close']]\n"
        )
        self.assertEqual(extract_wikilinks(body), [])

    def test_multiline_bracket_expression_is_not_a_wikilink(self) -> None:
        body = "result = df[['Open',\n 'High',\n 'Low']]\n"
        self.assertEqual(extract_wikilinks(body), [])

    def test_real_wikilinks_still_extracted_alongside_unfenced_code(self) -> None:
        body = (
            "See [[strategy-hunter]] for details.\n"
            "\n"
            "ohlcv = df[['Open', 'High', 'Low', 'Close', 'Volume']]\n"
            "\n"
            "Also [[backtest-results|results]].\n"
        )
        self.assertEqual(extract_wikilinks(body), ["strategy-hunter", "backtest-results"])

    def test_fenced_code_block_still_stripped(self) -> None:
        body = (
            "Some text\n"
            "\n"
            "```python\n"
            "ohlcv = df[['Open', 'High', 'Low', 'Close', 'Volume']]\n"
            "link = [[fenced-link]]\n"
            "```\n"
            "\n"
            "End with [[real-target]].\n"
        )
        self.assertEqual(extract_wikilinks(body), ["real-target"])

    def test_inline_code_span_still_stripped(self) -> None:
        body = "Use `[[syntax-example]]` to link. Real: [[actual-link]].\n"
        self.assertEqual(extract_wikilinks(body), ["actual-link"])

    def test_target_with_quotes_is_implausible(self) -> None:
        self.assertFalse(_is_plausible_wikilink("'Open', 'High'"))

    def test_target_with_comma_is_implausible(self) -> None:
        self.assertFalse(_is_plausible_wikilink("a, b"))

    def test_target_with_newline_is_implausible(self) -> None:
        self.assertFalse(_is_plausible_wikilink("open\nhigh"))

    def test_normal_wikilink_target_is_plausible(self) -> None:
        self.assertTrue(_is_plausible_wikilink("strategy-hunter"))
        self.assertTrue(_is_plausible_wikilink("@author-name"))
        self.assertTrue(_is_plausible_wikilink("My Note Title"))

    def test_end_to_end_strategy_hunter_repro(self) -> None:
        """Full repro of the original bug: a raw Python script saved as markdown."""
        body = "\n".join([
            "# Strategy Hunter Backtest Script",
            "",
            "import pandas as pd",
            "import numpy as np",
            "",
            "df = pd.read_csv('data.csv')",
            "ohlcv = df[['Open', 'High', 'Low', 'Close', 'Volume']]",
            "signals = df[['Signal', 'Position']]",
            "",
            "def backtest(data):",
            "    returns = data[['Close']].pct_change()",
            "    return returns",
            "",
        ])
        self.assertEqual(extract_wikilinks(body), [])


class WikilinkExtractionIntegrationTests(unittest.TestCase):
    """Integration: unfenced code in inbox markdown doesn't pollute links."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for directory in (
            "00_inbox",
            "01_ingest/queue",
            "01_ingest/ready",
            "01_ingest/rejected",
            "10_knowledge/finance/raw",
        ):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        self.minion = IngestMinion(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_inbox_python_script_as_markdown_produces_empty_links(self) -> None:
        source = self.root / "00_inbox" / "Back test - strategy hunter.md"
        source.write_text(
            "\n".join([
                "import pandas as pd",
                "df = pd.read_csv('data.csv')",
                "ohlcv = df[['Open', 'High', 'Low', 'Close', 'Volume']]",
                "filtered = df[['Close']]",
                "",
            ]),
            encoding="utf-8",
        )

        result = self.minion.run(apply=True)

        ready_target = self.root / "01_ingest" / "ready" / source.name
        self.assertTrue(result.ok)
        self.assertTrue(ready_target.exists())

        body = ready_target.read_text(encoding="utf-8")
        self.assertIn("links: []", body)


if __name__ == "__main__":
    unittest.main()
