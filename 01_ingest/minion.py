#!/usr/bin/env python3
"""Deterministic ingest routing for Mainframe."""

from __future__ import annotations

import argparse
import ast
import re
import shutil
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_KEYS = ("title", "domain", "type", "status", "source", "tags")
ALLOWED_TYPES = {"raw", "note", "live", "project", "decision"}
ALLOWED_STATUSES = {
    "queued",
    "skimmed",
    "routed",
    "extracted",
    "active",
    "synthesized",
    "stable",
    "archived",
    "parked",
}
KNOWLEDGE_TYPES = {"note", "raw"}
RAW_PDF_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})__(?P<domain>[^_]+)__raw__(?P<slug>.+)\.pdf$",
    re.IGNORECASE,
)
WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")
CANONICAL_FM_ORDER = ("title", "domain", "type", "status", "source", "tags", "links")
NORMALIZED_DEFAULT_STATUS = "skimmed"
NORMALIZED_DEFAULT_TYPE = "note"


@dataclass(frozen=True)
class Event:
    kind: str
    source: Path
    target: Path | None
    message: str
    severity: str = "info"


@dataclass
class RunResult:
    events: list[Event] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(event.severity != "error" for event in self.events)

    def add(
        self,
        kind: str,
        source: Path,
        target: Path | None,
        message: str,
        severity: str = "info",
    ) -> None:
        self.events.append(Event(kind, source, target, message, severity))


class FrontmatterError(ValueError):
    """Raised when a Markdown file does not match the approved schema."""


@dataclass
class ParsedFrontmatter:
    metadata: dict[str, Any]
    body_lines: list[str]
    has_frontmatter: bool
    trailing_newline: bool


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_list_value(value: str, key: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError) as exc:
        raise FrontmatterError(f"{key} must be an inline string list") from exc
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise FrontmatterError(f"{key} must be an inline string list")
    return parsed


def parse_tags(value: str) -> list[str]:
    return parse_list_value(value, "tags")


def read_frontmatter(path: Path) -> ParsedFrontmatter:
    """Parse a Markdown file's frontmatter permissively.

    Returns the parsed metadata, body lines (verbatim), and whether the file
    had a frontmatter block at all. Does not raise on missing required keys or
    unknown values — only on truly malformed YAML structure (no closing ``---``,
    duplicate keys, bad ``tags``/``links`` list syntax, etc.).
    """
    text = path.read_text(encoding="utf-8")
    trailing_newline = text.endswith("\n")
    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        return ParsedFrontmatter(
            metadata={},
            body_lines=lines,
            has_frontmatter=False,
            trailing_newline=trailing_newline,
        )

    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise FrontmatterError("unterminated YAML frontmatter") from exc

    metadata: dict[str, Any] = {}
    for line_number, line in enumerate(lines[1:end], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise FrontmatterError(f"invalid frontmatter line {line_number}")
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        if key in metadata:
            raise FrontmatterError(f"duplicate frontmatter key: {key}")
        if key in ("tags", "links"):
            metadata[key] = parse_list_value(raw_value, key)
        else:
            metadata[key] = strip_quotes(raw_value)

    return ParsedFrontmatter(
        metadata=metadata,
        body_lines=lines[end + 1:],
        has_frontmatter=True,
        trailing_newline=trailing_newline,
    )


def validate_strict(metadata: dict[str, Any]) -> None:
    """Raise ``FrontmatterError`` if metadata fails the strict v1 schema check."""
    missing = [key for key in REQUIRED_KEYS if key not in metadata]
    if missing:
        raise FrontmatterError(f"missing required metadata: {', '.join(missing)}")

    for key in REQUIRED_KEYS:
        value = metadata[key]
        if key == "tags":
            continue
        if not isinstance(value, str) or not value.strip():
            raise FrontmatterError(f"{key} must be a non-empty string")

    if metadata["type"] not in ALLOWED_TYPES:
        raise FrontmatterError(f"unsupported type: {metadata['type']}")
    if metadata["status"] not in ALLOWED_STATUSES:
        raise FrontmatterError(f"unsupported status: {metadata['status']}")


def parse_frontmatter(path: Path) -> dict[str, Any]:
    """Read + strict-validate a Markdown file's frontmatter.

    Backward-compatible entry point used by the strict ``queue/ → 10_knowledge/``
    routing gate. Raises ``FrontmatterError`` on any schema deviation.
    """
    parsed = read_frontmatter(path)
    if not parsed.has_frontmatter:
        raise FrontmatterError("missing YAML frontmatter")
    validate_strict(parsed.metadata)
    return parsed.metadata


_FENCED_CODE_RE = re.compile(r"^([`~]{3,})[^\n]*\n.*?\n\1[ \t]*$", re.DOTALL | re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_code_spans(text: str) -> str:
    """Remove fenced code blocks and inline code spans.

    Wikilinks inside code (e.g. notes that discuss the ``[[target]]`` syntax)
    are not real connections — they should not appear in the ``links:`` array.
    """
    text = _FENCED_CODE_RE.sub("", text)
    text = _INLINE_CODE_RE.sub("", text)
    return text


def extract_wikilinks(body: str) -> list[str]:
    """Return ``[[wikilink]]`` targets from body text, deduplicated and ordered.

    Strips alias suffix (``[[target|alias]]`` → ``target``). Wikilinks that
    appear inside fenced code blocks or inline code spans are ignored — they
    are discussion of the syntax, not real connections. Empty targets and
    repeats are dropped.
    """
    cleaned = _strip_code_spans(body)
    seen: set[str] = set()
    out: list[str] = []
    for match in WIKILINK_RE.findall(cleaned):
        target = match.split("|", 1)[0].strip()
        if not target or target in seen:
            continue
        seen.add(target)
        out.append(target)
    return out


def _format_string_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_list_value(value: list[str]) -> str:
    if not value:
        return "[]"
    items = ", ".join(_format_string_value(item) for item in value)
    return f"[{items}]"


def render_frontmatter(metadata: dict[str, Any]) -> str:
    """Render a metadata dict as a canonical YAML frontmatter block."""
    lines = ["---"]
    seen: set[str] = set()

    def emit(key: str, value: Any) -> None:
        if isinstance(value, list):
            lines.append(f"{key}: {_format_list_value(value)}")
        else:
            lines.append(f"{key}: {_format_string_value(str(value))}")

    for key in CANONICAL_FM_ORDER:
        if key in metadata:
            emit(key, metadata[key])
            seen.add(key)
    for key, value in metadata.items():
        if key not in seen:
            emit(key, value)
    lines.append("---")
    return "\n".join(lines)


def _infer_title(body_lines: list[str], path: Path) -> str:
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            inferred = stripped[2:].strip()
            if inferred:
                return inferred
    return slug_to_title(path.stem)


def normalize_metadata(
    metadata: dict[str, Any],
    body: str,
    body_lines: list[str],
    original_filename: str,
    *,
    force_skimmed: bool,
) -> dict[str, Any]:
    """Fill missing required keys with defaults and merge ``links`` from body."""
    md = dict(metadata)

    if not md.get("title"):
        md["title"] = _infer_title(body_lines, Path(original_filename))
    if "domain" not in md:
        md["domain"] = ""
    if not md.get("type"):
        md["type"] = NORMALIZED_DEFAULT_TYPE
    if force_skimmed or not md.get("status"):
        md["status"] = NORMALIZED_DEFAULT_STATUS
    if not md.get("source"):
        md["source"] = f"00_inbox/{original_filename}"
    if not isinstance(md.get("tags"), list):
        md["tags"] = []

    body_links = extract_wikilinks(body)
    existing_links = md.get("links") if isinstance(md.get("links"), list) else []
    seen: set[str] = set()
    merged: list[str] = []
    for link in list(existing_links) + body_links:
        if not isinstance(link, str):
            continue
        target = link.strip()
        if not target or target in seen:
            continue
        seen.add(target)
        merged.append(target)
    md["links"] = merged

    return md


def render_normalized_text(metadata: dict[str, Any], body_lines: list[str], trailing_newline: bool) -> str:
    """Combine a metadata dict and body lines into a normalized Markdown file."""
    fm_block = render_frontmatter(metadata)
    if not body_lines:
        body_text = ""
    else:
        body_text = "\n".join(body_lines)
    if body_text:
        text = fm_block + "\n" + body_text
    else:
        text = fm_block
    if trailing_newline and not text.endswith("\n"):
        text += "\n"
    return text


def slug_to_title(slug: str) -> str:
    words = re.sub(r"[-_]+", " ", slug).strip()
    words = re.sub(r"\s+", " ", words)
    return words.title() if words else "Untitled Raw Evidence"


def raw_stub(domain: str, slug: str, raw_filename: str) -> str:
    title = slug_to_title(slug)
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            f'domain: "{domain}"',
            'type: "raw"',
            'status: "queued"',
            f'source: "./raw/{raw_filename}"',
            'tags: ["pdf", "evidence"]',
            "---",
            "",
            f"Raw evidence file located at `raw/{raw_filename}`.",
            "",
        ]
    )


class IngestMinion:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root.resolve()
        self.inbox = self.root / "00_inbox"
        self.ingest = self.root / "01_ingest"
        self.queue = self.ingest / "queue"
        self.ready = self.ingest / "ready"
        self.rejected = self.ingest / "rejected"
        self.knowledge = self.root / "10_knowledge"
        self.log_path = self.ingest / "ingest-log.md"

    def domains(self) -> set[str]:
        if not self.knowledge.exists():
            return set()
        return {
            path.name
            for path in self.knowledge.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        }

    def run(self, apply: bool = False, raw_domain: str | None = None) -> RunResult:
        result = RunResult()
        domains = self.domains()

        if raw_domain and raw_domain not in domains:
            result.add(
                "blocked",
                self.knowledge,
                None,
                f"raw domain override is not a known knowledge domain: {raw_domain}",
                "error",
            )
            return result

        if apply:
            self.queue.mkdir(parents=True, exist_ok=True)
            self.ready.mkdir(parents=True, exist_ok=True)
            self.rejected.mkdir(parents=True, exist_ok=True)

        existing_queue = self._files_in(self.queue)
        staged = self._stage_inbox(result, apply)
        candidates = existing_queue + staged

        for path in sorted(candidates, key=lambda item: item.name):
            self._process_candidate(path, domains, result, apply, raw_domain)

        if apply:
            self._append_log(result)
        return result

    def _files_in(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return [
            path
            for path in sorted(directory.iterdir(), key=lambda item: item.name)
            if path.is_file() and not path.name.startswith(".")
        ]

    def _stage_inbox(self, result: RunResult, apply: bool) -> list[Path]:
        staged: list[Path] = []
        for source in self._files_in(self.inbox):
            if source.suffix.lower() == ".md":
                staged_path = self._stage_inbox_markdown(source, result, apply)
                if staged_path is not None:
                    staged.append(staged_path)
                continue

            # Non-markdown files (PDFs and others) stage straight to queue/.
            target = self.queue / source.name
            if target.exists() or target in staged:
                result.add(
                    "blocked",
                    source,
                    target,
                    "queue destination already exists",
                    "error",
                )
                continue
            result.add("stage", source, target, "stage inbox file in ingest queue")
            if apply:
                shutil.move(str(source), target)
                staged.append(target)
            else:
                staged.append(source)
        return staged

    def _stage_inbox_markdown(
        self,
        source: Path,
        result: RunResult,
        apply: bool,
    ) -> Path | None:
        """Read frontmatter, normalize, and route to queue/ or ready/.

        Returns the queue-bound path for further routing on the same run, or
        ``None`` when the file lands in ``ready/`` (awaiting agent enrichment)
        or is blocked/rejected.
        """
        try:
            parsed = read_frontmatter(source)
        except (OSError, UnicodeDecodeError) as exc:
            self._reject(source, result, apply, f"unreadable file: {exc}")
            return None
        except FrontmatterError as exc:
            self._reject(source, result, apply, f"malformed frontmatter: {exc}")
            return None

        was_strict_valid = False
        if parsed.has_frontmatter:
            try:
                validate_strict(parsed.metadata)
                was_strict_valid = True
            except FrontmatterError:
                was_strict_valid = False

        body = "\n".join(parsed.body_lines)

        if was_strict_valid:
            md = normalize_metadata(
                parsed.metadata,
                body,
                parsed.body_lines,
                source.name,
                force_skimmed=False,
            )
            target = self.queue / source.name
            if target.exists():
                result.add(
                    "blocked",
                    source,
                    target,
                    "queue destination already exists",
                    "error",
                )
                return None
            result.add("stage", source, target, "stage inbox file in ingest queue")
            if apply:
                source.write_text(
                    render_normalized_text(md, parsed.body_lines, parsed.trailing_newline),
                    encoding="utf-8",
                )
                shutil.move(str(source), target)
                return target
            return source

        md = normalize_metadata(
            parsed.metadata,
            body,
            parsed.body_lines,
            source.name,
            force_skimmed=True,
        )
        target = self.ready / source.name
        if target.exists():
            result.add(
                "blocked",
                source,
                target,
                "ready destination already exists",
                "error",
            )
            return None
        result.add(
            "normalize",
            source,
            target,
            "normalize frontmatter and stage for agent enrichment",
        )
        if apply:
            source.write_text(
                render_normalized_text(md, parsed.body_lines, parsed.trailing_newline),
                encoding="utf-8",
            )
            shutil.move(str(source), target)
        return None

    def _process_candidate(
        self,
        source: Path,
        domains: set[str],
        result: RunResult,
        apply: bool,
        raw_domain: str | None,
    ) -> None:
        suffix = source.suffix.lower()
        if suffix == ".md":
            self._route_markdown(source, domains, result, apply)
            return
        if suffix == ".pdf":
            self._route_pdf(source, domains, result, apply, raw_domain)
            return
        self._reject(source, result, apply, f"unsupported file type: {source.suffix or '(none)'}")

    def _route_markdown(
        self,
        source: Path,
        domains: set[str],
        result: RunResult,
        apply: bool,
    ) -> None:
        try:
            metadata = parse_frontmatter(source)
        except (OSError, UnicodeDecodeError, FrontmatterError) as exc:
            self._reject(source, result, apply, f"invalid frontmatter: {exc}")
            return

        domain = metadata["domain"]
        item_type = metadata["type"]
        if domain not in domains:
            self._reject(source, result, apply, f"unknown knowledge domain: {domain}")
            return
        if item_type not in KNOWLEDGE_TYPES:
            self._reject(source, result, apply, f"unsupported lifecycle type for v1: {item_type}")
            return

        target = self.knowledge / domain / source.name
        if target.exists():
            result.add("blocked", source, target, "knowledge destination already exists", "error")
            return

        result.add("route", source, target, f"route {item_type} markdown to {domain}")
        if apply:
            shutil.move(str(source), target)

    def _route_pdf(
        self,
        source: Path,
        domains: set[str],
        result: RunResult,
        apply: bool,
        raw_domain: str | None,
    ) -> None:
        parsed = RAW_PDF_RE.match(source.name)
        if parsed:
            date_prefix = parsed.group("date")
            domain = raw_domain or parsed.group("domain")
            slug = parsed.group("slug")
        elif raw_domain:
            date_prefix = date.today().isoformat()
            domain = raw_domain
            slug = source.stem
        else:
            self._reject(
                source,
                result,
                apply,
                "raw PDF filename must match YYYY-MM-DD__domain__raw__slug.pdf",
            )
            return

        if domain not in domains:
            self._reject(source, result, apply, f"unknown knowledge domain: {domain}")
            return

        raw_dir = self.knowledge / domain / "raw"
        raw_target = raw_dir / source.name
        stub_target = self.knowledge / domain / f"{date_prefix}__{domain}__raw__{slug}.md"
        collisions = [path for path in (raw_target, stub_target) if path.exists()]
        if collisions:
            result.add(
                "blocked",
                source,
                collisions[0],
                "raw routing destination already exists",
                "error",
            )
            return

        result.add("route-raw", source, raw_target, f"route raw PDF to {domain}/raw")
        result.add("stub", source, stub_target, "create MindGraph Markdown stub")
        if apply:
            raw_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), raw_target)
            stub_target.write_text(
                raw_stub(domain, slug, raw_target.name),
                encoding="utf-8",
            )

    def _reject(self, source: Path, result: RunResult, apply: bool, reason: str) -> None:
        target = self.rejected / source.name
        if target.exists():
            result.add("blocked", source, target, f"cannot reject file: {reason}", "error")
            return
        result.add("reject", source, target, reason, "error")
        if apply:
            shutil.move(str(source), target)

    def _append_log(self, result: RunResult) -> None:
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


def print_result(result: RunResult, minion: IngestMinion, apply: bool) -> None:
    mode = "apply" if apply else "dry-run"
    print(f"ingest-minion {mode}")
    if not result.events:
        print("no files found")
        return
    for event in result.events:
        prefix = "ERROR" if event.severity == "error" else "OK"
        target = f" -> {minion.rel(event.target)}" if event.target else ""
        print(f"{prefix} {event.kind}: {minion.rel(event.source)}{target}")
        print(f"  {event.message}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route Mainframe inbox files through 01_ingest.")
    parser.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="process 00_inbox and 01_ingest/queue")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="show planned moves without writing")
    mode.add_argument("--apply", action="store_true", help="move files and write raw stubs")
    run.add_argument(
        "--domain",
        help="domain override for raw PDFs that do not follow the filename convention",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    apply = bool(args.apply)
    minion = IngestMinion(Path(args.root))

    if args.command == "run":
        result = minion.run(apply=apply, raw_domain=args.domain)
        print_result(result, minion, apply)
        return 0 if result.ok else 1

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
