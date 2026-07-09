#!/usr/bin/env python3
"""Fetch open-access full text (or best available excerpt) for source-literature stubs.

Scans type: raw stubs under 10_knowledge/, resolves DOI/PMID/PDF/HTML sources,
and appends a ## Full text extract section following the business-operations audit
pattern. Does not paste paywalled PDFs.

Usage:
  bin/fetch-source-text --dry-run
  bin/fetch-source-text --apply --subset healthcare-practice
  bin/fetch-source-text --apply --file path/to/stub.md
  bin/fetch-source-text --json --subset healthcare-practice
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "10_knowledge"
USER_AGENT = "MainFrame-fetch-source-text/1.0 (mailto:mainframe@local)"
EXCERPT_MAX = 6000
HTTP_TIMEOUT = 45


@dataclass
class FetchResult:
    path: str
    status: str  # fetched | pending | skipped | na | error
    method: str = ""
    access_url: str = ""
    message: str = ""
    excerpt_chars: int = 0
    section: str = ""


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    header = text[3:end]
    body = text[end + 5 :]
    fm: dict[str, str] = {}
    for raw_line in header.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        fm[key.strip().lower()] = val.strip().strip('"').strip("'")
    return fm, body


def parse_tags(tag_field: str) -> list[str]:
    if not tag_field:
        return []
    tag_field = tag_field.strip()
    if tag_field.startswith("["):
        tag_field = tag_field.strip("[]").strip()
    return [t.strip().strip('"').strip("'") for t in tag_field.split(",") if t.strip()]


def normalize_source_url(source: str) -> str:
    """Pick the first fetchable URL from messy source fields."""
    source = source.strip().strip('"').strip("'")
    if not source:
        return ""
    urls = re.findall(r"https?://[^\s\"'<>]+", source)
    if urls:
        return urls[0].rstrip(").,;")
    if source.startswith("/"):
        arxiv = re.search(r"/abs/([\d.]+)", source)
        if arxiv:
            return f"https://arxiv.org/abs/{arxiv.group(1)}"
    if source.startswith("arxiv:"):
        return f"https://arxiv.org/abs/{source.split(':', 1)[1].strip()}"
    if source.startswith("10."):
        return f"https://doi.org/{source}"
    return source.split(";")[0].split()[0].strip()


def extract_identifiers(fm: dict[str, str]) -> tuple[str | None, str | None]:
    doi = fm.get("doi")
    pmid = fm.get("pmid")
    source = normalize_source_url(fm.get("source", ""))
    if not doi:
        m = re.search(r"10\.\d{4,9}/[^\s\"'>]+", source)
        if m:
            doi = m.group(0).rstrip(").,;")
    if not pmid:
        m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", source, re.I)
        if m:
            pmid = m.group(1)
    return doi, pmid


def http_get(url: str, accept: str = "*/*") -> bytes:
    url = normalize_source_url(url) if " " in url or ";" in url else url
    if not url.startswith(("http://", "https://")):
        raise urllib.error.URLError(f"unsupported URL: {url!r}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept},
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def http_get_json(url: str) -> Any:
    raw = http_get(url, accept="application/json")
    return json.loads(raw.decode("utf-8", errors="replace"))


def europepmc_search(doi: str | None, pmid: str | None) -> dict[str, Any] | None:
    if pmid:
        query = f"EXT_ID:{pmid}"
    elif doi:
        query = f"DOI:{doi}"
    else:
        return None
    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
        + urllib.parse.urlencode({"query": query, "format": "json", "pageSize": 1})
    )
    try:
        data = http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None
    results = data.get("resultList", {}).get("result") or []
    return results[0] if results else None


def openalex_abstract(doi: str) -> str:
    url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}"
    try:
        data = http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return ""
    inv = data.get("abstract_inverted_index")
    if not inv:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def crossref_abstract(doi: str) -> str:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    try:
        data = http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return ""
    msg = data.get("message", {})
    abstract = msg.get("abstract") or ""
    abstract = re.sub(r"<[^>]+>", "", abstract)
    return " ".join(abstract.split())


def unpaywall_best_pdf(doi: str, email: str | None) -> str | None:
    if not email:
        return None
    url = (
        f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}"
        f"?email={urllib.parse.quote(email)}"
    )
    try:
        data = http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None
    if not data.get("is_oa"):
        return None
    loc = data.get("best_oa_location") or {}
    return loc.get("url_for_pdf") or loc.get("url")


def jats_xml_to_text(xml_bytes: bytes) -> tuple[str, str]:
    """Return (abstract, body_text) from JATS XML."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return "", ""

    def collect(tag: str) -> str:
        parts: list[str] = []
        for el in root.iter(tag):
            text = "".join(el.itertext()).strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts)

    abstract = collect("abstract")
    body = collect("body")
    if not body:
        # Fallback: all paragraphs outside front matter
        paras = []
        for el in root.iter("p"):
            text = "".join(el.itertext()).strip()
            if text:
                paras.append(text)
        body = "\n\n".join(paras)
    return abstract, body


def fetch_europepmc_fulltext(pmcid: str) -> tuple[str, str, str]:
    """Returns method, access_url, combined_text."""
    access = f"https://europepmc.org/article/PMC/{pmcid.replace('PMC', '')}"
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    try:
        xml_bytes = http_get(url, accept="application/xml")
    except (urllib.error.URLError, urllib.error.HTTPError):
        return "europepmc-blocked", access, ""
    abstract, body = jats_xml_to_text(xml_bytes)
    chunks = []
    if abstract:
        chunks.append(abstract)
    if body:
        chunks.append(body)
    return "europepmc-xml", access, "\n\n".join(chunks)


def pdf_to_text(pdf_bytes: bytes) -> str:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return ""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as pdf_tmp:
        pdf_tmp.write(pdf_bytes)
        pdf_tmp.flush()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=True) as txt_tmp:
            proc = subprocess.run(
                [pdftotext, "-layout", pdf_tmp.name, txt_tmp.name],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                return ""
            return Path(txt_tmp.name).read_text(encoding="utf-8", errors="replace")


def fetch_direct_pdf(url: str) -> tuple[str, str, str]:
    try:
        data = http_get(url)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        return "direct-pdf-blocked", url, f"HTTP error: {exc}"
    if not data.startswith(b"%PDF"):
        return "direct-pdf-blocked", url, "Response was not a PDF"
    text = pdf_to_text(data)
    if not text.strip():
        return "direct-pdf-empty", url, "PDF downloaded; text extraction failed or empty"
    return "direct-pdf", url, text


def strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p>", "\n\n", html)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"[ \t]+\n", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    html = re.sub(r" +", " ", html)
    return html.strip()


def fetch_html(url: str) -> tuple[str, str, str]:
    try:
        raw = http_get(url, accept="text/html")
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        return "direct-html-blocked", url, f"HTTP error: {exc}"
    text = strip_html(raw.decode("utf-8", errors="replace"))
    if len(text) < 200:
        return "direct-html-empty", url, text
    return "direct-html", url, text


def truncate_excerpt(text: str, limit: int = EXCERPT_MAX) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n\n[… truncated at {limit} chars — full text available at Access URL]"


def has_fulltext_section(body: str) -> bool:
    return bool(re.search(r"^##\s+Full text extract\b", body, re.M))


def remove_fulltext_section(body: str) -> str:
    return re.sub(r"\n?## Full text extract\b[\s\S]*\Z", "", body.rstrip()) + "\n"


def channel_source_na(source: str) -> bool:
    host = urllib.parse.urlparse(source).netloc.lower()
    return any(
        x in host
        for x in (
            "youtube.com",
            "youtu.be",
            "reddit.com",
            "twitter.com",
            "x.com",
        )
    )


def build_section(
    *,
    today: str,
    method: str,
    access_url: str,
    abstract: str,
    body_text: str,
    verdict: str,
) -> str:
    lines = [f"## Full text extract (fetch {today})", ""]
    if access_url:
        lines.append(f"**Access:** {access_url}")
    lines.append(f"**Fetch method:** {method}")
    lines.append("")
    if abstract:
        lines.append("**Abstract (fetched):**")
        lines.append("")
        lines.append(truncate_excerpt(abstract, 2500))
        lines.append("")
    if body_text:
        lines.append("**Body excerpt:**")
        lines.append("")
        lines.append(truncate_excerpt(body_text))
        lines.append("")
    lines.append(f"**Audit verdict:** {verdict}")
    lines.append("")
    return "\n".join(lines)


def update_fulltext_assessment(body: str, assessment: str) -> str:
    if re.search(r"^\-\s+\*\*Full text:\*\*", body, re.M):
        return re.sub(
            r"^\-\s+\*\*Full text:\*\*.*$",
            f"- **Full text:** {assessment}",
            body,
            count=1,
            flags=re.M,
        )
    # Insert before Dedup note inside Source assessment if present
    m = re.search(
        r"(## Source assessment\s*\n)(.*?)(^\-\s+\*\*Dedup note:\*\*)",
        body,
        re.M | re.S,
    )
    if m:
        prefix, middle, dedup = m.group(1), m.group(2), m.group(3)
        if "**Full text:**" not in middle:
            insert = f"- **Full text:** {assessment}\n"
            return body.replace(
                m.group(0),
                prefix + middle + insert + dedup,
                1,
            )
    return body


def update_tags_in_frontmatter(header: str, add: list[str], remove_prefixes: tuple[str, ...]) -> str:
    # Non-greedy: header may contain other bracketed YAML values (e.g. author arrays).
    m = re.search(r"^tags:\s*\[(.*?)\]\s*$", header, re.M)
    if not m:
        return header
    tags = parse_tags(m.group(1))
    tags = [t for t in tags if not any(t.startswith(p) for p in remove_prefixes)]
    for t in add:
        if t not in tags:
            tags.append(t)
    new_inner = ", ".join(f'"{t}"' for t in tags)
    return header[: m.start()] + f"tags: [{new_inner}]" + header[m.end() :]


def fetch_for_stub(path: Path, *, today: str, unpaywall_email: str | None, force: bool) -> FetchResult:
    rel = str(path.relative_to(ROOT))
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return FetchResult(rel, "error", message=str(exc))

    fm, body = parse_frontmatter(text)
    if fm.get("type", "").lower() != "raw":
        return FetchResult(rel, "skipped", message="not type: raw")

    if has_fulltext_section(body) and not force:
        return FetchResult(rel, "skipped", message="already has Full text extract")

    source = normalize_source_url(fm.get("source", ""))
    doi, pmid = extract_identifiers(fm)
    abstract = ""
    body_text = ""
    method = ""
    access_url = source
    verdict = ""
    status = "pending"

    if channel_source_na(source):
        section = build_section(
            today=today,
            method="channel-source",
            access_url=source,
            abstract="",
            body_text="",
            verdict="Full text **not applicable** — channel/community source; use manual monitor notes.",
        )
        return FetchResult(rel, "na", method="channel-source", access_url=source, section=section)

    # Europe PMC for scholarly IDs
    epmc = europepmc_search(doi, pmid) if (doi or pmid) else None
    if epmc:
        abstract = (epmc.get("abstractText") or "").strip()
        pmcid = epmc.get("pmcid")
        is_oa = (epmc.get("isOpenAccess") or "").upper() == "Y"
        if pmcid and is_oa:
            method, access_url, full = fetch_europepmc_fulltext(pmcid)
            if full:
                body_text = full
                status = "fetched"
                verdict = "Full text **fetch verified** (Europe PMC OA XML). Claims still need human appraisal."
            else:
                status = "pending"
                verdict = "**full-text-pending** — indexed in Europe PMC but XML fetch blocked."
        elif abstract:
            status = "pending"
            method = "europepmc-abstract"
            access_url = f"https://doi.org/{doi}" if doi else source
            verdict = "**full-text-pending** — abstract only (not open access in Europe PMC)."
        if not abstract and doi:
            abstract = openalex_abstract(doi) or crossref_abstract(doi)

    # Unpaywall PDF fallback for DOI
    if status != "fetched" and doi:
        pdf_url = unpaywall_best_pdf(doi, unpaywall_email)
        if pdf_url:
            m, u, txt = fetch_direct_pdf(pdf_url)
            if txt and not txt.startswith("HTTP") and not txt.startswith("Response"):
                method, access_url, body_text = m, u, txt
                status = "fetched"
                verdict = "Full text **fetch verified** (Unpaywall OA PDF). Claims still need human appraisal."

    # Direct PDF URL in source field
    if status != "fetched" and source.lower().endswith(".pdf"):
        m, u, txt = fetch_direct_pdf(source)
        if m == "direct-pdf":
            method, access_url, body_text = m, u, txt
            status = "fetched"
            verdict = "Full text **fetch verified** (direct PDF). Claims still need human appraisal."
        elif not verdict:
            method, access_url = m, u
            status = "pending"
            verdict = f"**full-text-pending** — {txt}"

    # HTML institutional / guidance pages
    if status != "fetched" and source.startswith("http") and not source.lower().endswith(".pdf"):
        if not method or method in ("europepmc-abstract", ""):
            m, u, txt = fetch_html(source)
            if m == "direct-html" and len(txt) > 400:
                method, access_url, body_text = m, u, txt
                status = "fetched"
                verdict = "Full text **fetch verified** (HTML page). Claims still need human appraisal."
            elif not verdict and txt:
                method, access_url = m, u
                abstract = abstract or truncate_excerpt(txt, 1500)
                status = "pending"
                verdict = "**full-text-pending** — partial HTML only."

    if not verdict:
        if abstract:
            status = "pending"
            method = method or "abstract-only"
            verdict = "**full-text-pending** — abstract/metadata only; no OA full text found."
        else:
            status = "pending"
            method = method or "none"
            verdict = "**full-text-pending** — no automated full text or abstract found."

    if not abstract and doi:
        abstract = openalex_abstract(doi) or crossref_abstract(doi)

    section = build_section(
        today=today,
        method=method or "none",
        access_url=access_url,
        abstract=abstract,
        body_text=body_text,
        verdict=verdict,
    )
    return FetchResult(
        rel,
        status,
        method=method,
        access_url=access_url,
        excerpt_chars=len(body_text),
        section=section,
    )


def apply_result(path: Path, original: str, result: FetchResult, today: str) -> str:
    fm, body = parse_frontmatter(original)
    header_end = original.find("\n---", 3)
    header = original[3:header_end]

    body = remove_fulltext_section(body)
    body = update_fulltext_assessment(
        body,
        "verified (automated fetch)" if result.status == "fetched" else (
            "not applicable" if result.status == "na" else "pending (automated fetch)"
        ),
    )
    body = body.rstrip() + "\n\n" + result.section

    tag_add: list[str] = []
    if result.status == "fetched":
        tag_add.append(f"full-text-fetched-{today}")
    elif result.status == "na":
        tag_add.append("full-text-na")
    else:
        tag_add.append("full-text-pending")

    header = update_tags_in_frontmatter(
        header,
        tag_add,
        ("full-text-fetched-", "full-text-pending", "full-text-na"),
    )
    return f"---\n{header}\n---\n{body}"


def find_stubs(subset: str | None, file_arg: str | None) -> list[Path]:
    if file_arg:
        p = Path(file_arg)
        if not p.is_absolute():
            p = ROOT / p
        return [p] if p.is_file() else []
    base = KNOWLEDGE / subset if subset else KNOWLEDGE
    if not base.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(base.rglob("*.md")):
        if p.name.lower() == "index.md":
            continue
        if "__raw__" in p.name or p.parent.name == "raw":
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch full text for source-literature stubs.")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not write files")
    parser.add_argument("--apply", action="store_true", help="Append extracts to stub files")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable report")
    parser.add_argument("--subset", metavar="DOMAIN", help="Limit to 10_knowledge/<domain>/")
    parser.add_argument("--file", metavar="PATH", help="Single stub file")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if extract exists")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.apply and not args.json:
        args.dry_run = True

    today = date.today().isoformat()
    unpaywall_email = (
        __import__("os").environ.get("UNPAYWALL_EMAIL")
        or __import__("os").environ.get("MAINFRAME_UNPAYWALL_EMAIL")
    )

    stubs = find_stubs(args.subset, args.file)
    results: list[FetchResult] = []
    for path in stubs:
        try:
            result = fetch_for_stub(
                path, today=today, unpaywall_email=unpaywall_email, force=args.force
            )
        except Exception as exc:  # noqa: BLE001 — batch must survive one bad stub
            result = FetchResult(
                str(path.relative_to(ROOT)),
                "error",
                message=str(exc),
            )
        results.append(result)
        if args.apply and result.section and result.status in ("fetched", "pending", "na"):
            original = path.read_text(encoding="utf-8")
            updated = apply_result(path, original, result, today)
            path.write_text(updated, encoding="utf-8")

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            flag = r.status.upper()
            extra = f" ({r.method}, {r.excerpt_chars} chars)" if r.method else ""
            print(f"[{flag}] {r.path}{extra}")
            if r.message:
                print(f"       {r.message}")

    fetched = sum(1 for r in results if r.status == "fetched")
    pending = sum(1 for r in results if r.status == "pending")
    print(
        f"\nSummary: {len(results)} scanned, {fetched} fetched, {pending} pending, "
        f"{sum(1 for r in results if r.status == 'skipped')} skipped",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())