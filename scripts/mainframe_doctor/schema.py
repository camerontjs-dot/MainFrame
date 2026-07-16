"""Result schema and aggregation for mainframe-doctor."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

CheckStatus = Literal["pass", "warn", "fail", "stale", "unknown", "skip"]
Health = Literal["healthy", "degraded", "unhealthy", "unknown"]
Severity = Literal["info", "low", "medium", "high", "critical"]

STATUS_ORDER = ("pass", "warn", "fail", "stale", "unknown", "skip")


@dataclass
class CheckResult:
    id: str
    subsystem: str
    layer: str
    status: CheckStatus
    severity: Severity
    required: bool
    expected: str
    observed: str
    observed_at: str | None
    freshness_seconds: int | None
    authority: str
    evidence_refs: list[str] = field(default_factory=list)
    message: str = ""
    remediation: str = ""
    safe_fix_available: bool = False
    duration_ms: int = 0
    proves: str = ""
    does_not_prove: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DoctorReport:
    schema_version: int
    doctor_version: str
    profile: str
    health: Health
    checked_at: str
    duration_ms: int
    authority_revision: str | None
    summary: dict[str, int]
    checks: list[CheckResult]
    catalogue_version: str | None = None
    mode: str = "live"
    internal_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def summarize(checks: list[CheckResult]) -> dict[str, int]:
    summary = {k: 0 for k in STATUS_ORDER}
    for c in checks:
        summary[c.status] = summary.get(c.status, 0) + 1
    return summary


def aggregate_health(checks: list[CheckResult]) -> Health:
    """Aggregate check statuses into overall health.

    Rules (doctor contract):
    - healthy: all required checks pass (optional may warn/skip)
    - unhealthy: any required failure or critical defect
    - unknown: a critical required check is unknown, or insufficient evidence
    - degraded: no critical failure, but required warn/stale or accepted optional fail
    """
    if not checks:
        return "unknown"

    required = [c for c in checks if c.required]
    optional = [c for c in checks if not c.required]

    # Critical severity fail on any check → unhealthy
    for c in checks:
        if c.status == "fail" and c.severity == "critical":
            return "unhealthy"

    for c in required:
        if c.status == "fail":
            return "unhealthy"

    # Required unknown / skip-policy-fail → unknown (cannot claim healthy)
    for c in required:
        if c.status == "unknown":
            return "unknown"
        if c.status == "skip":
            # skip_policy fail for required is treated as unknown, not pass
            return "unknown"

    for c in required:
        if c.status in ("warn", "stale"):
            return "degraded"

    for c in optional:
        if c.status == "fail":
            return "degraded"

    for c in required:
        if c.status != "pass":
            return "unknown"

    return "healthy"


def exit_code(health: Health, *, internal_error: bool = False) -> int:
    if internal_error:
        return 2
    if health == "healthy":
        return 0
    return 1


def redact_secret_shaped(text: str) -> str:
    """Redact long token-like substrings; never echo secret values."""
    import re

    # crude: long base64/hex-ish runs
    text = re.sub(r"(?i)(secret|token|password|api[_-]?key)\s*[:=]\s*\S+", r"\1=[REDACTED]", text)
    text = re.sub(r"\b[A-Za-z0-9_\-]{40,}\b", "[REDACTED_LONG]", text)
    return text
