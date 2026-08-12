from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADER = SourceFileLoader("capture_validate", str(ROOT / "bin" / "capture-validate"))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
capture_validate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capture_validate
SPEC.loader.exec_module(capture_validate)


def write_capture(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "capture.md"
    path.write_text(
        "---\n"
        "title: \"Test capture\"\n"
        "type: raw\n"
        f"source: \"{source}\"\n"
        "---\n\nBody.\n",
        encoding="utf-8",
    )
    return path


def test_bare_domain_source_is_a_warning(tmp_path: Path) -> None:
    findings = capture_validate.validate(write_capture(tmp_path, "https://ollama.com"))

    assert any(
        finding.rule == "R7" and finding.severity == "warn" for finding in findings
    )


def test_specific_document_source_is_not_a_bare_domain(tmp_path: Path) -> None:
    findings = capture_validate.validate(
        write_capture(tmp_path, "https://ollama.com/library/llama3")
    )

    assert not any(finding.rule == "R7" for finding in findings)


def test_query_or_fragment_does_not_count_as_a_bare_domain(tmp_path: Path) -> None:
    findings = capture_validate.validate(
        write_capture(tmp_path, "https://example.org/?page=about")
    )

    assert not any(finding.rule == "R7" for finding in findings)
