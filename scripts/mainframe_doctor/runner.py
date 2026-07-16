"""Doctor runner: catalogue → providers → aggregate."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from mainframe_doctor.catalogue import load_catalogue_pair
from mainframe_doctor.providers import run_provider
from mainframe_doctor.schema import (
    DoctorReport,
    aggregate_health,
    exit_code,
    summarize,
    utc_now_rfc3339,
)
from mainframe_doctor import __version__


QUICK_SUBSYSTEMS = {
    "authority",
    "session",
    "projects",
    "scheduler",
    "mindgraph",
    "telemetry",
    "structure",
    "cli",
    "security",
    "workstation",
    "evaluation",
}

# quick profile: prefer these ids if present
QUICK_IDS = {
    "AUTH-001",
    "SESSION-001",
    "SESSION-002",
    "PROJECT-002",
    "SCHED-001",
    "EVAL-002",
    "MG-001",
    "MG-003",
    "TEL-001",
    "WS-001",
    "WS-003",
    "CLI-001",
    "SEC-001",
    "STRUCT-001",
    "TASK-001",
}


def default_paths(root: Path) -> tuple[Path, Path]:
    return (
        root / ".context" / "doctor" / "catalogue.json",
        root / ".context" / "doctor" / "required-invariants.json",
    )


def load_fixture(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if path.is_dir():
        f = path / "fixture.json"
    else:
        f = path
    if not f.exists():
        raise FileNotFoundError(f"fixture not found: {f}")
    return json.loads(f.read_text(encoding="utf-8"))


def select_checks(
    checks: list[dict[str, Any]],
    *,
    profile: str,
    component: str | None,
) -> list[dict[str, Any]]:
    if component:
        return [c for c in checks if c.get("subsystem") == component]
    if profile == "quick":
        selected = [c for c in checks if c.get("id") in QUICK_IDS]
        if selected:
            return selected
        return [c for c in checks if c.get("subsystem") in QUICK_SUBSYSTEMS]
    # deep = all
    return list(checks)


def run_doctor(
    *,
    root: Path,
    profile: str = "quick",
    component: str | None = None,
    fixture_path: Path | None = None,
    catalogue_path: Path | None = None,
    invariants_path: Path | None = None,
) -> tuple[DoctorReport, int]:
    t0 = time.perf_counter()
    cat_path, inv_path = default_paths(root)
    if catalogue_path:
        cat_path = catalogue_path
    if invariants_path:
        inv_path = invariants_path

    loaded = load_catalogue_pair(cat_path, inv_path)
    if not loaded.ok:
        report = DoctorReport(
            schema_version=1,
            doctor_version=__version__,
            profile=profile,
            health="unknown",
            checked_at=utc_now_rfc3339(),
            duration_ms=int((time.perf_counter() - t0) * 1000),
            authority_revision=None,
            summary={"pass": 0, "warn": 0, "fail": 0, "stale": 0, "unknown": 0, "skip": 0},
            checks=[],
            catalogue_version=None,
            mode="fixture" if fixture_path else "live",
            internal_error="; ".join(loaded.errors)[:1000],
        )
        return report, exit_code("unknown", internal_error=True)

    try:
        fixture = load_fixture(fixture_path)
    except Exception as exc:  # noqa: BLE001
        report = DoctorReport(
            schema_version=1,
            doctor_version=__version__,
            profile=profile,
            health="unknown",
            checked_at=utc_now_rfc3339(),
            duration_ms=int((time.perf_counter() - t0) * 1000),
            authority_revision=None,
            summary={"pass": 0, "warn": 0, "fail": 0, "stale": 0, "unknown": 0, "skip": 0},
            checks=[],
            catalogue_version=str(loaded.catalogue.get("catalogue_version")),
            mode="fixture",
            internal_error=f"fixture load failed: {exc}",
        )
        return report, exit_code("unknown", internal_error=True)

    # Fixture may point at a synthetic root
    run_root = root
    if fixture.get("root"):
        run_root = Path(fixture["root"])
        if not run_root.is_absolute():
            # relative to fixture file dir
            base = fixture_path if fixture_path and fixture_path.is_dir() else (fixture_path.parent if fixture_path else root)
            run_root = (base / fixture["root"]).resolve()

    ctx: dict[str, Any] = {
        "root": run_root,
        "fixture": fixture,
        "profile": profile,
    }

    all_checks = [c for c in loaded.catalogue.get("checks", []) if isinstance(c, dict)]
    selected = select_checks(all_checks, profile=profile, component=component)

    results = []
    for check in selected:
        results.append(run_provider(check, ctx))

    health = aggregate_health(results)
    report = DoctorReport(
        schema_version=1,
        doctor_version=__version__,
        profile=profile if not component else f"component:{component}",
        health=health,
        checked_at=utc_now_rfc3339(),
        duration_ms=int((time.perf_counter() - t0) * 1000),
        authority_revision=fixture.get("authority_revision"),
        summary=summarize(results),
        checks=results,
        catalogue_version=str(loaded.catalogue.get("catalogue_version")),
        mode="fixture" if fixture_path else "live",
        internal_error=None,
    )
    return report, exit_code(health, internal_error=False)


def format_human(report: DoctorReport) -> str:
    lines = [
        f"mainframe-doctor {report.doctor_version}  profile={report.profile}  mode={report.mode}",
        f"health={report.health}  checked_at={report.checked_at}  duration_ms={report.duration_ms}",
        f"summary: {report.summary}",
    ]
    if report.internal_error:
        lines.append(f"INTERNAL ERROR: {report.internal_error}")
        return "\n".join(lines) + "\n"

    # order by severity interest: fail, unknown, stale, warn, skip, pass
    order = {"fail": 0, "unknown": 1, "stale": 2, "warn": 3, "skip": 4, "pass": 5}
    checks = sorted(report.checks, key=lambda c: (order.get(c.status, 9), c.id))
    lines.append("")
    for c in checks:
        if c.status == "pass" and report.profile.startswith("quick"):
            continue  # keep quick human output short; still in JSON
        flag = c.status.upper()
        req = "req" if c.required else "opt"
        lines.append(f"  [{flag}] {c.id} ({req}/{c.severity}) {c.message}")
        if c.status != "pass" and c.remediation:
            lines.append(f"         remediation: {c.remediation}")
    # always show non-pass count reminder
    non_pass = [c for c in report.checks if c.status != "pass"]
    lines.append("")
    lines.append(f"{len(non_pass)} non-pass / {len(report.checks)} checks shown partially; use --json for full vector")
    return "\n".join(lines) + "\n"
