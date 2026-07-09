"""Tests for scripts/fetch_source_text.py pure helpers."""

from __future__ import annotations

import unittest

from scripts.fetch_source_text import (
    build_section,
    extract_identifiers,
    has_fulltext_section,
    jats_xml_to_text,
    parse_frontmatter,
    strip_html,
    truncate_excerpt,
)


class TestFetchSourceTextHelpers(unittest.TestCase):
    def test_parse_frontmatter(self) -> None:
        text = """---
title: "Example"
doi: "10.1000/xyz"
type: raw
---
# Body
"""
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm.get("doi"), "10.1000/xyz")
        self.assertIn("# Body", body)

    def test_extract_identifiers_from_source(self) -> None:
        fm = {"source": "https://doi.org/10.1177/10870547231161533"}
        doi, pmid = extract_identifiers(fm)
        self.assertEqual(doi, "10.1177/10870547231161533")
        self.assertIsNone(pmid)

    def test_has_fulltext_section(self) -> None:
        self.assertTrue(has_fulltext_section("## Full text extract (fetch 2026-06-21)\n"))
        self.assertFalse(has_fulltext_section("## Bibliographic record\n"))

    def test_jats_xml_to_text_minimal(self) -> None:
        xml = b"""<article><body><p>First paragraph.</p><p>Second.</p></body></article>"""
        abstract, body = jats_xml_to_text(xml)
        self.assertIn("First paragraph", body)
        self.assertIn("Second", body)

    def test_strip_html(self) -> None:
        html = "<html><body><p>Hello <b>world</b></p></body></html>"
        self.assertIn("Hello world", strip_html(html))

    def test_truncate_excerpt(self) -> None:
        long = "a" * 100
        out = truncate_excerpt(long, limit=50)
        self.assertIn("truncated", out)
        self.assertLess(len(out), 120)

    def test_build_section_contains_verdict(self) -> None:
        section = build_section(
            today="2026-06-21",
            method="europepmc-xml",
            access_url="https://example.com",
            abstract="Short abstract.",
            body_text="Body here.",
            verdict="Full text **fetch verified**.",
        )
        self.assertIn("## Full text extract", section)
        self.assertIn("**Audit verdict:**", section)


if __name__ == "__main__":
    unittest.main()