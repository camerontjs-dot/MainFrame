#!/usr/bin/env python3
"""Validate agent-enriched files in 01_ingest/ready/ and gate them into 01_ingest/queue/.

Deterministic Phase-4 helper for the ADR-009 two-pass ingest pipeline. Files in
``01_ingest/ready/`` are produced by the minion's pass-1 normalization and
enriched by the ingest-agent sub-agent. This script is the explicit boundary
between agent judgment and minion pass-2: it checks that the agent finished
its job (strict-valid frontmatter, ``status: "extracted"``, filename matches
the canonical ``YYYY-MM-DD__domain__type__slug.md`` shape, domain in the
``10_knowledge/`` whitelist) before promoting the file into ``queue/``.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


_HERE = Path(__file__).resolve().parent
_MINION_PATH = _HERE / "minion.py"
_SPEC = importlib.util.spec_from_file_location("ingest_minion", _MINION_PATH)
assert _SPEC and _SPEC.loader
_minion = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault(_SPEC.name, _minion)
_SPEC.loader.exec_module(_minion)

parse_frontmatter = _minion.parse_frontmatter
FrontmatterError = _minion.FrontmatterError
RunResult = _minion.RunResult


ROOT = Path(__file__).resolve().parents[1]
ROUTING_READY_STATUS = "extracted"
FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})__(?P<domain>[^_]+)__(?P<type>[^_]+)__(?P<slug>.+)\.md$",
)


class PrepIngest:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root.resolve()
        self.ingest = self.root / "01_ingest"
        self.ready = self.ingest / "ready"
        self.queue = self.ingest / "queue"
        self.knowledge = self.root / "10_knowledge"
        self.log_path = self.ingest / "prep-ingest-log.md"

    def domains(self) -> set[str]:
        if not self.knowledge.exists():
            return set()
        return {
            path.name
            for path in self.knowledge.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        }

    def run(self, apply: bool = False) -> "RunResult":
        result = RunResult()

        if apply:
            self.queue.mkdir(parents=True, exist_ok=True)

        if not self.ready.exists():
            return result

        domains = self.domains()
        for source in sorted(self.ready.iterdir(), key=lambda item: item.name):
            if not source.is_file() or source.name.startswith("."):
                continue
            self._process_file(source, domains, result, apply)

        if apply:
            self._append_log(result)
        return result

    def _process_file(
        self,
        source: Path,
        domains: set[str],
        result: "RunResult",
        apply: bool,
    ) -> None:
        if source.suffix.lower() != ".md":
            result.add(
                "blocked",
                source,
                None,
                f"unsupported file type for prep-ingest: {source.suffix or '(none)'}",
                "error",
            )
            return

        try:
            metadata = parse_frontmatter(source)
        except (OSError, UnicodeDecodeError, FrontmatterError) as exc:
            result.add(
                "blocked",
                source,
                None,
                f"frontmatter not ready for queue: {exc}",
                "error",
            )
            return

        status = metadata.get("status", "")
        if status != ROUTING_READY_STATUS:
            result.add(
                "blocked",
                source,
                None,
                f"status must be '{ROUTING_READY_STATUS}' before prep-ingest; got '{status}'",
                "error",
            )
            return

        match = FILENAME_RE.match(source.name)
        if not match:
            result.add(
                "blocked",
                source,
                None,
                "filename must match YYYY-MM-DD__domain__type__slug.md",
                "error",
            )
            return

        fname_domain = match.group("domain")
        fname_type = match.group("type")
        domain = metadata["domain"]
        item_type = metadata["type"]

        if fname_domain != domain:
            result.add(
                "blocked",
                source,
                None,
                f"filename domain '{fname_domain}' does not match frontmatter domain '{domain}'",
                "error",
            )
            return
        if fname_type != item_type:
            result.add(
                "blocked",
                source,
                None,
                f"filename type '{fname_type}' does not match frontmatter type '{item_type}'",
                "error",
            )
            return

        if domain not in domains:
            result.add(
                "blocked",
                source,
                None,
                f"unknown knowledge domain: {domain}",
                "error",
            )
            return

        target = self.queue / source.name
        if target.exists():
            result.add(
                "blocked",
                source,
                target,
                "queue destination already exists",
                "error",
            )
            return

        result.add(
            "promote",
            source,
            target,
            "promote agent-enriched file from ready to queue",
        )
        if apply:
            shutil.move(str(source), target)

    def _append_log(self, result: "RunResult") -> None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        lines = [f"## {timestamp}", ""]
        if not result.events:
            lines.append("- no files found")
        for event in result.events:
            target = f" -> {self.rel(event.target)}" if event.target else ""
            lines.append(
                f"- {event.severity}: {event.kind}: {self.rel(event.source)}{target} "
                f"- {event.message}"
            )
        lines.append("")
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

    def rel(self, path: Path | None) -> str:
        if path is None:
            return "-"
        try:
            return str(path.resolve().relative_to(self.root))
        except ValueError:
            return str(path)


def print_result(result: "RunResult", prep: PrepIngest, apply: bool) -> None:
    mode = "apply" if apply else "dry-run"
    print(f"prep-ingest {mode}")
    if not result.events:
        print("no files found")
        return
    for event in result.events:
        prefix = "ERROR" if event.severity == "error" else "OK"
        target = f" -> {prep.rel(event.target)}" if event.target else ""
        print(f"{prefix} {event.kind}: {prep.rel(event.source)}{target}")
        print(f"  {event.message}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Promote agent-enriched files from 01_ingest/ready/ "
            "to 01_ingest/queue/ after strict validation."
        )
    )
    parser.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="process 01_ingest/ready/")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="show planned moves without writing")
    mode.add_argument("--apply", action="store_true", help="move files from ready/ to queue/")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    apply = bool(args.apply)
    prep = PrepIngest(Path(args.root))

    if args.command == "run":
        result = prep.run(apply=apply)
        print_result(result, prep, apply)
        return 0 if result.ok else 1

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
