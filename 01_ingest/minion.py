#!/usr/bin/env python3
"""Deterministic ingest routing for Mainframe."""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import sys
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
PDF_METADATA_RE = re.compile(
    rb"/(?P<key>Title|Author|Subject|Keywords|CreationDate|ModDate)\s*"
    rb"(?P<value>\((?:\\.|[^\\)])*\)|<(?!!<)[0-9A-Fa-f\s]+>)",
    re.DOTALL,
)
PDF_METADATA_SCAN_BYTES = 1024 * 1024


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
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"', '`'}:
        value = value[1:-1].strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
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
    index = 1
    while index < end:
        line_number = index + 1
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if ":" not in stripped or stripped.startswith("-"):
            raise FrontmatterError(f"invalid frontmatter line {line_number}")
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        if key in metadata:
            raise FrontmatterError(f"duplicate frontmatter key: {key}")

        if raw_value.strip():
            if key in ("tags", "links"):
                metadata[key] = parse_list_value(raw_value, key)
            else:
                metadata[key] = strip_quotes(raw_value)
            index += 1
            continue

        list_items: list[str] = []
        lookahead = index + 1
        while lookahead < end:
            item_line = lines[lookahead]
            item_stripped = item_line.strip()
            if not item_stripped or item_stripped.startswith("#"):
                lookahead += 1
                continue
            if item_stripped.startswith("-"):
                list_items.append(strip_quotes(item_stripped[1:]))
                lookahead += 1
                continue
            if ":" in item_stripped:
                break
            raise FrontmatterError(f"invalid frontmatter line {lookahead + 1}")

        if list_items:
            metadata[key] = list_items
            index = lookahead
        else:
            metadata[key] = ""
            index += 1

    return ParsedFrontmatter(
        metadata=metadata,
        body_lines=lines[end + 1:],
        has_frontmatter=True,
        trailing_newline=trailing_newline,
    )


def check_provenance(path: Path) -> list[str]:
    """G3 gate — reject captures carrying unearned citations.

    Delegates to `bin/capture-validate` so there is exactly one definition of
    "fabricated identifier" in the repo. Loaded lazily: the gate must never be
    the reason ingest cannot run, so if the validator is missing or broken the
    ingest proceeds and says so rather than blocking everything.
    """
    try:
        import importlib.util
        from importlib.machinery import SourceFileLoader

        loader = SourceFileLoader("_capval", str(ROOT / "bin" / "capture-validate"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        if spec is None or spec.loader is None:
            return []
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001 — never block ingest on a broken gate
        print(f"warning: provenance gate unavailable ({exc}) — routing unchecked",
              file=sys.stderr)
        return []

    return [
        f"{f.rule} {f.message}"
        for f in mod.validate(path)
        if f.severity == "error"
    ]


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

    tags = metadata["tags"]
    if not isinstance(tags, list) or not tags:
        raise FrontmatterError("tags must be a non-empty string list")
    if any(not isinstance(tag, str) or not tag.strip() for tag in tags):
        raise FrontmatterError("tags must contain only non-empty strings")

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


_IMPLAUSIBLE_LINK_RE = re.compile(r"""['",\n]""")


def _is_plausible_wikilink(target: str) -> bool:
    """Return ``False`` for targets that look like programming expressions.

    Real wikilink targets are prose identifiers (``my-note``, ``@author``).
    Python double-bracket indexing (``df[['Open', 'High']]``) and similar
    constructs produce candidates containing quotes, commas, or newlines —
    none of which appear in legitimate wikilinks.
    """
    return not _IMPLAUSIBLE_LINK_RE.search(target)


def extract_wikilinks(body: str) -> list[str]:
    """Return ``[[wikilink]]`` targets from body text, deduplicated and ordered.

    Strips alias suffix (``[[target|alias]]`` → ``target``). Wikilinks that
    appear inside fenced code blocks or inline code spans are ignored — they
    are discussion of the syntax, not real connections. Candidates whose
    targets contain quotes, commas, or newlines are rejected as implausible
    (likely programming expressions in unfenced code). Empty targets and
    repeats are dropped.
    """
    cleaned = _strip_code_spans(body)
    seen: set[str] = set()
    out: list[str] = []
    for match in WIKILINK_RE.findall(cleaned):
        target = match.split("|", 1)[0].strip()
        if not target or target in seen:
            continue
        if not _is_plausible_wikilink(target):
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


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "untitled"


def read_unparsed_markdown(path: Path) -> ParsedFrontmatter:
    """Treat an unparseable Markdown file as body-only evidence."""
    text = path.read_text(encoding="utf-8")
    return ParsedFrontmatter(
        metadata={},
        body_lines=text.splitlines(),
        has_frontmatter=False,
        trailing_newline=text.endswith("\n"),
    )


def pdf_filename_suggestion(path: Path) -> str:
    slug = slugify(path.stem)
    return f"{date.today().isoformat()}__<domain>__raw__{slug}.pdf"


def _decode_pdf_bytes(value: bytes) -> str:
    for encoding in ("utf-8", "utf-16-be", "utf-16-le", "latin-1"):
        try:
            decoded = value.decode(encoding)
        except UnicodeDecodeError:
            continue
        decoded = decoded.lstrip("\ufeff").strip()
        if decoded:
            return decoded
    return ""


def _decode_pdf_literal(raw: bytes) -> str:
    value = raw[1:-1]
    out = bytearray()
    index = 0
    while index < len(value):
        char = value[index]
        if char != 0x5C:
            out.append(char)
            index += 1
            continue

        index += 1
        if index >= len(value):
            break
        escaped = value[index]
        if escaped in b"nrtbf":
            out.append({ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}[escaped])
            index += 1
        elif escaped in b"()\\":
            out.append(escaped)
            index += 1
        elif 48 <= escaped <= 55:
            digits = bytes([escaped])
            index += 1
            for _ in range(2):
                if index < len(value) and 48 <= value[index] <= 55:
                    digits += bytes([value[index]])
                    index += 1
            octal_value = int(digits, 8)
            if octal_value > 0xFF:
                # A PDF literal represents bytes. Treat an out-of-range octal
                # escape as malformed metadata instead of aborting ingestion.
                return ""
            out.append(octal_value)
        elif escaped in b"\r\n":
            while index < len(value) and value[index] in b"\r\n":
                index += 1
        else:
            out.append(escaped)
            index += 1
    return _decode_pdf_bytes(bytes(out))


def _decode_pdf_hex(raw: bytes) -> str:
    hex_value = re.sub(rb"\s+", b"", raw[1:-1])
    if len(hex_value) % 2:
        hex_value += b"0"
    try:
        value = bytes.fromhex(hex_value.decode("ascii"))
    except ValueError:
        return ""
    return _decode_pdf_bytes(value)


def decode_pdf_value(raw: bytes) -> str:
    if raw.startswith(b"(") and raw.endswith(b")"):
        return _decode_pdf_literal(raw)
    if raw.startswith(b"<") and raw.endswith(b">"):
        return _decode_pdf_hex(raw)
    return ""


def normalize_pdf_date(value: str) -> str:
    match = re.match(r"^D?:(?P<year>\d{4})(?P<month>\d{2})?(?P<day>\d{2})?", value)
    if not match:
        match = re.match(r"^(?P<year>\d{4})(?P<month>\d{2})?(?P<day>\d{2})?", value)
    if not match:
        return value
    year = match.group("year")
    month = match.group("month") or "01"
    day = match.group("day") or "01"
    return f"{year}-{month}-{day}"


def parse_keywords(value: str) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for keyword in re.split(r"[,;]", value):
        cleaned = keyword.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        keywords.append(cleaned)
    return keywords


def pdf_metadata(path: Path) -> dict[str, Any]:
    """Best-effort PDF Info dictionary extraction for wrappers/suggestions."""
    try:
        with path.open("rb") as handle:
            start = handle.read(65536)
            try:
                handle.seek(0, 2)
                size = handle.tell()
                handle.seek(max(0, size - PDF_METADATA_SCAN_BYTES))
                tail = handle.read(PDF_METADATA_SCAN_BYTES)
            except OSError:
                tail = b""
    except OSError:
        return {}

    data = start + b"\n" + tail
    found: dict[str, Any] = {}
    key_map = {
        "Title": "title",
        "Author": "author",
        "Subject": "description",
        "Keywords": "keywords",
        "CreationDate": "created",
        "ModDate": "modified",
    }
    for match in PDF_METADATA_RE.finditer(data):
        pdf_key = match.group("key").decode("ascii")
        key = key_map[pdf_key]
        if key in found:
            continue
        value = decode_pdf_value(match.group("value"))
        if not value:
            continue
        if key == "author":
            found[key] = [value]
        elif key == "keywords":
            keywords = parse_keywords(value)
            if keywords:
                found[key] = keywords
        elif key in {"created", "modified"}:
            found[key] = normalize_pdf_date(value)
        else:
            found[key] = value
    return found


def summarize_pdf_metadata(metadata: dict[str, Any]) -> str:
    parts: list[str] = []
    title = metadata.get("title")
    author = metadata.get("author")
    created = metadata.get("created")
    if isinstance(title, str) and title:
        parts.append(f"title: {title}")
    if isinstance(author, list) and author:
        parts.append(f"author: {', '.join(author)}")
    if isinstance(created, str) and created:
        parts.append(f"created: {created}")
    return "; ".join(parts)


def raw_stub(
    domain: str,
    slug: str,
    raw_filename: str,
    source_metadata: dict[str, Any] | None = None,
) -> str:
    metadata = dict(source_metadata or {})
    title = metadata.pop("title", "") or slug_to_title(slug)
    frontmatter: dict[str, Any] = {
        "title": title,
        "domain": domain,
        "type": "raw",
        "status": "queued",
        "source": f"./raw/{raw_filename}",
        "tags": ["pdf", "evidence"],
        "links": [],
        "source_type": "pdf",
    }
    frontmatter.update(metadata)
    return "\n".join(
        [
            render_frontmatter(frontmatter),
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
        staged = self._stage_inbox(result, apply, domains)
        candidates = existing_queue + staged

        for path in sorted(candidates, key=lambda item: item.name):
            self._process_candidate(path, domains, result, apply, raw_domain)

        if apply:
            self._append_log(result)
        return result

    # Operational files are not captures. Without this, the scanner treats
    # presence in a directory as intent to ingest, so a contract file placed in
    # `00_inbox/` to govern that folder gets normalized and moved into
    # `01_ingest/ready/` — the contract migrates out of the folder it governs,
    # silently and on the first apply. Verified by dry-run on 2026-08-10:
    #
    #     OK normalize: 00_inbox/AGENTS.md -> 01_ingest/ready/AGENTS.md
    #
    # Matched case-insensitively: `core.ignorecase` is true in this workspace,
    # so `agents.md` and `AGENTS.md` are the same file to git and must be the
    # same file here.
    RESERVED_NAMES = frozenset({
        "agents.md", "readme.md", "index.md", "claude.md",
        "license", "license.md", ".gitkeep",
    })

    def _files_in(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return [
            path
            for path in sorted(directory.iterdir(), key=lambda item: item.name)
            if path.is_file()
            and not path.name.startswith(".")
            and path.name.lower() not in self.RESERVED_NAMES
        ]

    def _stage_inbox(self, result: RunResult, apply: bool, domains: set[str]) -> list[Path]:
        staged: list[Path] = []
        for source in self._files_in(self.inbox):
            if source.suffix.lower() == ".md":
                staged_path = self._stage_inbox_markdown(source, domains, result, apply)
                if staged_path is not None:
                    staged.append(staged_path)
                continue

            if source.suffix.lower() == ".pdf":
                staged_path = self._stage_inbox_pdf(source, domains, result, apply)
                if staged_path is not None:
                    staged.append(staged_path)
                continue

            # Unknown inbox file types need an explicit workflow before routing.
            result.add(
                "suggest",
                source,
                None,
                f"unsupported inbox file type; convert to Markdown or add an explicit workflow for {source.suffix or '(none)'}",
                "warning",
            )
        return staged

    def _stage_inbox_markdown(
        self,
        source: Path,
        domains: set[str],
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
            result.add(
                "suggest",
                source,
                None,
                f"unreadable Markdown; save as UTF-8 text before ingest: {exc}",
                "warning",
            )
            return None
        except FrontmatterError as exc:
            try:
                parsed = read_unparsed_markdown(source)
            except (OSError, UnicodeDecodeError) as read_exc:
                result.add(
                    "suggest",
                    source,
                    None,
                    f"malformed frontmatter and unreadable as UTF-8; repair manually before ingest: {read_exc}",
                    "warning",
                )
                return None
            frontmatter_warning = str(exc)
        else:
            frontmatter_warning = ""

        was_strict_valid = False
        if parsed.has_frontmatter:
            try:
                validate_strict(parsed.metadata)
                was_strict_valid = True
            except FrontmatterError:
                was_strict_valid = False

        body = "\n".join(parsed.body_lines)

        domain = parsed.metadata.get("domain")
        item_type = parsed.metadata.get("type")
        is_known_knowledge_target = (
            isinstance(domain, str)
            and domain in domains
            and isinstance(item_type, str)
            and item_type in KNOWLEDGE_TYPES
        )

        if was_strict_valid and is_known_knowledge_target:
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

        message = "normalize frontmatter and stage for agent enrichment"
        severity = "info"
        if frontmatter_warning:
            message = f"frontmatter needs agent repair: {frontmatter_warning}"
            severity = "warning"
        elif was_strict_valid and not is_known_knowledge_target:
            if isinstance(domain, str) and domain and domain not in domains:
                message = f"domain '{domain}' is not established; agent should confirm an existing domain or propose a new one"
            elif isinstance(item_type, str) and item_type not in KNOWLEDGE_TYPES:
                message = f"type '{item_type}' is not routable to 10_knowledge in v1; agent should route through the right lifecycle"
            else:
                message = "strict metadata needs agent review before routing"
            severity = "warning"

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
            message,
            severity,
        )
        if apply:
            source.write_text(
                render_normalized_text(md, parsed.body_lines, parsed.trailing_newline),
                encoding="utf-8",
            )
            shutil.move(str(source), target)
        return None

    def _stage_inbox_pdf(
        self,
        source: Path,
        domains: set[str],
        result: RunResult,
        apply: bool,
    ) -> Path | None:
        metadata = pdf_metadata(source)
        metadata_summary = summarize_pdf_metadata(metadata)
        metadata_message = f"; metadata found: {metadata_summary}" if metadata_summary else ""
        parsed = RAW_PDF_RE.match(source.name)
        if not parsed:
            result.add(
                "suggest",
                source,
                None,
                f"raw PDF needs a domain and convention filename; suggested shape: {pdf_filename_suggestion(source)}{metadata_message}",
                "warning",
            )
            return None

        domain = parsed.group("domain")
        if domain not in domains:
            result.add(
                "suggest",
                source,
                None,
                f"PDF names proposed domain '{domain}', but no matching 10_knowledge domain exists; agent should confirm or create it before routing{metadata_message}",
                "warning",
            )
            return None

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
            shutil.move(str(source), target)
            return target
        return source

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

        # G3 — provenance gate. A capture may not enter durable knowledge wearing
        # a citation it did not earn. See
        # 20_live/security/2026-08-09__fabricated-source-captures-in-10-knowledge.md
        # (103 captures with identifiers that do not exist, routed and indexed
        # because nothing between authoring and `10_knowledge/` ever asked).
        provenance_errors = check_provenance(source)
        if provenance_errors:
            self._reject(
                source,
                result,
                apply,
                "provenance gate: " + "; ".join(provenance_errors),
            )
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
            metadata = pdf_metadata(source)
            raw_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), raw_target)
            stub_target.write_text(
                raw_stub(domain, slug, raw_target.name, metadata),
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
        if event.severity == "error":
            prefix = "ERROR"
        elif event.severity == "warning":
            prefix = "WARN"
        else:
            prefix = "OK"
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
