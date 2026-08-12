#!/usr/bin/env python3
"""Advisory, source-authoritative MainFrame wikilink audit.

Profile: deterministic-operation / root / generated-state.
Authority: Markdown source files in the requested scope and the canonical
MindGraph parser/resolver.  This command never opens or mutates SQLite and
never rewrites source notes.  It is deliberately separate from the
mindgraph-eval frozen-snapshot inventory.

The audit reports link-level classifications (resolved, dangling/unresolved,
ambiguous, external/cross-lifecycle, intentional body/frontmatter mirror,
same-channel duplicate) and document-level findings (raw evidence leaf,
curated no-outbound, reviewed curated disposition, metadata domain/type gaps).
A unique candidate is recorded as an exact-safe repair candidate for review; it
is never selected or written automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MINDGRAPH_SRC = ROOT / "mindgraph" / "src"
if str(MINDGRAPH_SRC) not in sys.path:
    sys.path.insert(0, str(MINDGRAPH_SRC))

from mindgraph.parser import (  # noqa: E402
    LINK_PATTERN,
    LinkResolver,
    extract_metadata_link_targets,
    parse_document,
)


SUPPORTED_RELATIONSHIPS = frozenset(
    {"evidence", "extends", "contrasts", "implements", "navigation"}
)
VALID_GRAPH_DISPOSITIONS = frozenset({"reviewed-no-link", "standalone"})
CANONICAL_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}__")


def normalize_target(target: str) -> str:
    target = target.strip()
    return target if target.endswith(".md") else f"{target}.md"


def lifecycle_classification(target: str) -> str | None:
    lowered = target.strip().casefold()
    if lowered.startswith(("http://", "https://", "doi:")):
        return "external/cross-lifecycle"
    if lowered.startswith(("00_inbox/", "01_ingest/", "20_live/", "30_projects/", "90_archive/")):
        return "external/cross-lifecycle"
    return None


def candidate_paths(target: str, paths: set[str]) -> tuple[str, list[str]]:
    """Return conservative candidates using the resolver's supported aliases."""
    normalized = normalize_target(target)
    name = Path(normalized).name.casefold()
    stem = Path(normalized).stem.casefold()
    same_name = sorted(path for path in paths if Path(path).name.casefold() == name)
    if same_name:
        return "same-filename", same_name
    same_stem = sorted(path for path in paths if Path(path).stem.casefold() == stem)
    if same_stem:
        return "same-stem", same_stem
    if "__" not in stem:
        same_slug = sorted(
            path
            for path in paths
            if CANONICAL_PREFIX.match(Path(path).stem)
            and Path(path).stem.rsplit("__", 1)[-1].casefold() == stem
        )
        if same_slug:
            return "same-canonical-slug", same_slug
    return "none", []


def _context(text: str, start: int, end: int) -> str:
    left = max(0, start - 160)
    right = min(len(text), end + 160)
    return " ".join(text[left:right].split())


def _display_path(scope_root: Path, root: Path, relative: str) -> str:
    return (scope_root.relative_to(root).as_posix().rstrip("/") + "/" + relative).lstrip("/")


def _source_occurrences(parsed: Any, text: str) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for target in extract_metadata_link_targets(parsed.metadata):
        occurrences.append(
            {
                "raw_link_target": target,
                "location": "frontmatter",
                "relationship": None,
                "context": f"links: {target}",
            }
        )
    for match in LINK_PATTERN.finditer(parsed.truth_text):
        relationship = match.group(2).strip() if match.group(2) else None
        occurrences.append(
            {
                "raw_link_target": match.group(1).strip(),
                "location": "body",
                "relationship": relationship,
                "context": _context(parsed.truth_text, match.start(), match.end()),
            }
        )
    return occurrences


def audit(root: Path, scope: Path, run_id: str) -> dict[str, Any]:
    files = sorted(path for path in scope.rglob("*.md") if path.is_file())
    parsed_docs: list[tuple[Path, Any, str]] = []
    parse_errors: list[dict[str, str]] = []
    digest = hashlib.sha256()
    for source in files:
        relative = source.relative_to(scope).as_posix()
        digest.update(relative.encode("utf-8"))
        try:
            body = source.read_bytes()
            digest.update(body)
            display = _display_path(scope, root, relative)
            parsed = parse_document(relative, body).model_copy(
                update={"path": display, "display_path": display, "source_path": relative}
            )
            parsed_docs.append((source, parsed, display))
        except Exception as exc:  # keep the audit advisory and complete the queue
            parse_errors.append({"source_path": str(source.relative_to(root)), "error": str(exc)})

    resolver = LinkResolver.from_documents(parsed for _, parsed, _ in parsed_docs)
    paths = {display for _, _, display in parsed_docs}
    link_rows: list[dict[str, Any]] = []
    document_rows: list[dict[str, Any]] = []
    metadata_gap_rows: list[dict[str, Any]] = []

    for source, parsed, display in parsed_docs:
        text = source.read_text(encoding="utf-8")
        occurrences = _source_occurrences(parsed, text)
        resolved_targets: set[str] = set()
        occurrence_keys: Counter[str] = Counter()
        source_link_rows: list[dict[str, Any]] = []
        for occurrence in occurrences:
            target = occurrence["raw_link_target"]
            lifecycle = lifecycle_classification(target)
            resolved_path = resolver.resolve(target, display) if lifecycle is None else None
            kind, candidates = candidate_paths(target, paths) if resolved_path is None else ("resolved", [resolved_path])
            if resolved_path:
                classification = "resolved"
                resolved_targets.add(resolved_path)
                occurrence_key = resolved_path.casefold()
            elif lifecycle:
                classification = lifecycle
                occurrence_key = target.casefold()
            elif len(candidates) > 1:
                classification = "ambiguous"
                occurrence_key = target.casefold()
            else:
                classification = "dangling/unresolved"
                occurrence_key = target.casefold()
            occurrence_keys[occurrence_key] += 1
            row = {
                "source_path": display,
                "source_domain": parsed.metadata.get("domain") or "unset",
                "source_type": parsed.metadata.get("type") or "unset",
                "source_title": parsed.title,
                "raw_link_target": target,
                "location": occurrence["location"],
                "relationship": occurrence["relationship"],
                "relationship_supported": occurrence["relationship"] in SUPPORTED_RELATIONSHIPS
                if occurrence["relationship"]
                else None,
                "target_resolution_status": classification,
                "resolved_target_path": resolved_path,
                "candidate_kind": kind,
                "candidate_paths": candidates,
                "repair_candidate": (
                    "exact-safe-repair-candidate" if len(candidates) == 1 and not lifecycle and not resolved_path else None
                ),
                "context": occurrence["context"],
            }
            source_link_rows.append(row)
        rows_by_key: dict[str, list[dict[str, Any]]] = {}
        for row in source_link_rows:
            key = row["resolved_target_path"] or row["raw_link_target"].casefold()
            rows_by_key.setdefault(key, []).append(row)
        for rows in rows_by_key.values():
            body_rows = [row for row in rows if row["location"] == "body"]
            frontmatter_rows = [row for row in rows if row["location"] == "frontmatter"]
            mirror_pairs = 0
            if rows[0]["target_resolution_status"] == "resolved":
                mirror_pairs = min(len(body_rows), len(frontmatter_rows))
                for row in body_rows[:mirror_pairs] + frontmatter_rows[:mirror_pairs]:
                    row["mirror"] = True
                    row["duplicate"] = False
                    row["classifications"] = [row["target_resolution_status"], "mirror"]
            for channel_rows, channel_total in (
                (body_rows[mirror_pairs:], len(body_rows)),
                (frontmatter_rows[mirror_pairs:], len(frontmatter_rows)),
            ):
                is_duplicate = channel_total > 1
                for row in channel_rows:
                    row["mirror"] = False
                    row["duplicate"] = is_duplicate
                    row["classifications"] = [row["target_resolution_status"]]
                    if is_duplicate:
                        row["classifications"].append("duplicate")
            if mirror_pairs == 0:
                for row in rows:
                    row.setdefault("mirror", False)
                    row.setdefault("duplicate", len(rows) > 1)
                    row.setdefault("classifications", [row["target_resolution_status"]])
        link_rows.extend(source_link_rows)

        metadata = parsed.metadata
        missing = [field for field in ("domain", "type") if not metadata.get(field)]
        if missing:
            gap = {
                "source_path": display,
                "classification": "metadata domain/type gaps",
                "missing_fields": missing,
                "context": "frontmatter metadata",
            }
            metadata_gap_rows.append(gap)

        item_type = str(metadata.get("type") or "unset").casefold()
        if item_type == "raw" and not resolved_targets:
            document_rows.append(
                {
                    "source_path": display,
                    "source_domain": metadata.get("domain") or "unset",
                    "source_type": "raw",
                    "title": parsed.title,
                    "classification": "raw evidence leaf",
                    "resolved_outbound_count": 0,
                    "raw_link_count": len(occurrences),
                    "context": "raw document with zero resolved authored outbound links",
                }
            )
        if item_type == "note" and not resolved_targets:
            disposition = str(metadata.get("graph_disposition") or "").strip().casefold()
            disposition_valid = disposition in VALID_GRAPH_DISPOSITIONS
            document_rows.append(
                {
                    "source_path": display,
                    "source_domain": metadata.get("domain") or "unset",
                    "source_type": "note",
                    "title": parsed.title,
                    "classification": (
                        "curated no-outbound reviewed"
                        if disposition_valid
                        else "curated no-outbound"
                    ),
                    "actionable": not disposition_valid,
                    "resolved_outbound_count": 0,
                    "raw_link_count": len(occurrences),
                    "graph_disposition": disposition or "missing-review-disposition",
                    "disposition_valid": disposition_valid,
                    "context": "curated note with zero resolved authored outbound links",
                }
            )

    link_counts = Counter()
    for row in link_rows:
        link_counts.update(row["classifications"])
    duplicate_count = link_counts.get("duplicate", 0)
    mirror_count = link_counts.get("mirror", 0)
    disposition_counts = Counter(
        row["graph_disposition"]
        for row in document_rows
        if row["classification"] == "curated no-outbound reviewed"
    )
    doc_counts = Counter(row["classification"] for row in document_rows)
    if metadata_gap_rows:
        doc_counts["metadata domain/type gaps"] = len(metadata_gap_rows)
    summary = {
        "run_id": run_id,
        "root": str(root),
        "scope": str(scope),
        "source_digest": digest.hexdigest(),
        "source_file_count": len(files),
        "parsed_file_count": len(parsed_docs),
        "parse_error_count": len(parse_errors),
        "link_count": len(link_rows),
        "link_classification_counts": dict(sorted(link_counts.items())),
        "duplicate_link_count": duplicate_count,
        "mirror_occurrence_count": mirror_count,
        "mirror_pair_count": mirror_count // 2,
        "document_finding_counts": dict(sorted(doc_counts.items())),
        "metadata_gap_count": len(metadata_gap_rows),
        "curated_reviewed_disposition_counts": dict(sorted(disposition_counts.items())),
        "supported_relationship_vocabulary": sorted(SUPPORTED_RELATIONSHIPS),
    }
    action_queue = {
        "auto_detectable": [
            "review dangling/unresolved targets and exact-safe candidates",
            "review ambiguous targets without fuzzy selection",
            "review same-channel duplicate authored occurrences or duplicate edge semantics",
            "review metadata domain/type gaps",
            "review curated no-outbound notes with missing or invalid graph_disposition",
        ],
        "informational": [
            "body/frontmatter mirror pairs are intentional ingest mirrors and are not duplicate findings",
            "raw evidence leaves (informational): raw documents with zero resolved authored outbound links",
            "curated no-outbound notes with graph_disposition reviewed-no-link or standalone are reviewed/informational",
            "external/cross-lifecycle references remain intentional unless a bridge policy is approved",
        ],
        "human_decision_required": [
            "source renames, identity conflicts, and any source rewrite or link repair",
        ],
    }
    return {
        "status": "advisory",
        "mutating": False,
        "snapshot_mode": False,
        "summary": summary,
        "action_queue": action_queue,
        "links": link_rows,
        "documents": document_rows,
        "metadata_gaps": metadata_gap_rows,
        "parse_errors": parse_errors,
    }


def markdown_report(data: dict[str, Any]) -> str:
    summary = data["summary"]
    lines = [
        f"# MindGraph advisory link audit — {summary['run_id']}",
        "",
        "Source-authoritative, read-only preflight. No SQLite or source-note writes are performed; findings do not fail ingest.",
        "",
        f"- Scope: `{summary['scope']}`",
        f"- Source digest: `{summary['source_digest']}`",
        f"- Files / authored link occurrences: **{summary['source_file_count']} / {summary['link_count']}**",
        f"- Status: **{data['status']}**; mutating: **{data['mutating']}**",
        "",
        "## Link classifications",
        "",
        "| Classification | Count |",
        "| --- | ---: |",
    ]
    for key, value in summary["link_classification_counts"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            f"| `mirror` (body/frontmatter ingest pairs) | {summary['mirror_occurrence_count']} occurrences / {summary['mirror_pair_count']} pairs |",
            f"| `duplicate` (same-channel authored occurrences) | {summary['duplicate_link_count']} |",
            "",
            "## Document findings",
            "",
            "| Finding | Count |",
            "| --- | ---: |",
        ]
    )
    for key, value in summary["document_finding_counts"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Action queue", ""])
    for bucket, entries in data["action_queue"].items():
        lines.append(f"### {bucket.replace('_', ' ').title()}")
        lines.append("")
        lines.extend(f"- {entry}" for entry in entries)
        lines.append("")
    if data["documents"]:
        lines.extend(["## Document queue", "", "| Source | Type | Finding | Actionable | Disposition | Context |", "| --- | --- | --- | --- | --- | --- |"])
        for row in data["documents"]:
            disposition = row.get("graph_disposition", "-")
            lines.append(
                f"| `{row['source_path']}` | `{row['source_type']}` | `{row['classification']}` | `{row.get('actionable', False)}` | `{disposition}` | {row['context']} |"
            )
    if data["metadata_gaps"]:
        lines.extend(["", "## Metadata gaps", ""])
        for row in data["metadata_gaps"]:
            lines.append(f"- `{row['source_path']}` — missing `{', '.join(row['missing_fields'])}`")
    unresolved = [row for row in data["links"] if row["target_resolution_status"] != "resolved"]
    if unresolved:
        lines.extend(["", "## Unresolved and candidate links", "", "| Source | Raw target | Status | Candidates | Context |", "| --- | --- | --- | --- | --- |"])
        for row in unresolved:
            candidates = ", ".join(row["candidate_paths"]) or "-"
            context = row["context"].replace("|", "\\|")
            lines.append(f"| `{row['source_path']}` | `{row['raw_link_target']}` | `{row['target_resolution_status']}` | `{candidates}` | {context} |")
    lines.extend(["", "## Non-mutating contract", "", "This audit only reads source Markdown, uses the canonical parser/resolver semantics, and emits advisory JSON/Markdown. It does not rewrite notes, delete links, mutate SQLite, fuzzy-select targets, or act as a blocking gate.", ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bin/mindgraph-audit-links",
        description="Run the advisory, read-only MainFrame wikilink audit.",
        epilog=(
            "Recommended sequence: pre-refresh audit -> source review/edit -> "
            "durable refresh -> post-refresh audit/probe. Findings are advisory "
            "and never a blocking gate."
        ),
    )
    parser.add_argument("--root", default=str(ROOT), help="MainFrame root")
    parser.add_argument("--scope", default="10_knowledge", help="scope directory, relative to --root")
    parser.add_argument("--run-id", default=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--output-dir", help="optional directory for JSON and Markdown reports")
    parser.add_argument("--json", action="store_true", help="print the complete JSON report")
    parser.add_argument("--dry-run", action="store_true", help="explicitly document read-only mode")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    scope_arg = Path(args.scope)
    scope = (root / scope_arg if not scope_arg.is_absolute() else scope_arg).resolve()
    if not scope.is_dir():
        print(f"audit scope does not exist: {scope}", file=sys.stderr)
        return 2
    data = audit(root, scope, args.run_id)
    human = markdown_report(data)
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{args.run_id}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output_dir / f"{args.run_id}.md").write_text(human, encoding="utf-8")
        print(f"json: {output_dir / f'{args.run_id}.json'}", file=sys.stderr)
        print(f"report: {output_dir / f'{args.run_id}.md'}", file=sys.stderr)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(human)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
