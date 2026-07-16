"""Non-mutating check providers for mainframe-doctor."""

from __future__ import annotations

import json
import re
import sqlite3
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from mainframe_doctor.schema import CheckResult, CheckStatus, Severity, redact_secret_shaped, utc_now_rfc3339


ProviderFn = Callable[[dict[str, Any], dict[str, Any]], CheckResult]


def _result(
    check: dict[str, Any],
    status: CheckStatus,
    *,
    observed: str,
    message: str,
    severity: Severity | None = None,
    evidence_refs: list[str] | None = None,
    duration_ms: int = 0,
) -> CheckResult:
    sev: Severity
    if severity is not None:
        sev = severity
    elif status == "fail":
        sev = "high"
    elif status in ("unknown", "stale"):
        sev = "medium"
    elif status == "warn":
        sev = "low"
    else:
        sev = "info"
    return CheckResult(
        id=check["id"],
        subsystem=check.get("subsystem", "unknown"),
        layer=check.get("layer", "unknown"),
        status=status,
        severity=sev,
        required=bool(check.get("required", True)),
        expected=str(check.get("pass_condition", "")),
        observed=redact_secret_shaped(observed)[:500],
        observed_at=utc_now_rfc3339(),
        freshness_seconds=check.get("freshness_seconds"),
        authority=str(check.get("owner", "")),
        evidence_refs=evidence_refs or [],
        message=redact_secret_shaped(message)[:500],
        remediation=str(check.get("remediation", "")),
        safe_fix_available=bool(check.get("safe_fix_available", False)),
        duration_ms=duration_ms,
        proves=str(check.get("pass_condition", "")),
        does_not_prove="Outcome value, income benefit, or unreproduced live claims",
    )


def provider_unimplemented(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    # Optional checks with skip_policy=skip may skip rather than force unknown
    if not check.get("required", True) and str(check.get("skip_policy", "")).lower() == "skip":
        return _result(
            check,
            "skip",
            observed="provider not implemented; optional skip_policy=skip",
            message=f"{check['id']}: skipped (unimplemented optional)",
            severity="info",
        )
    return _result(
        check,
        "unknown",
        observed="provider not implemented in Unit 1.3 shell",
        message=f"{check['id']}: explicit unknown/unimplemented",
        severity="medium",
    )


def provider_fixture_override(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult | None:
    """If fixture defines this check id, return that result."""
    fixture = ctx.get("fixture") or {}
    overrides = fixture.get("checks") or {}
    if check["id"] not in overrides:
        return None
    o = overrides[check["id"]]
    status = o.get("status", "unknown")
    if status not in ("pass", "warn", "fail", "stale", "unknown", "skip"):
        status = "unknown"
    return _result(
        check,
        status,
        observed=str(o.get("observed", "fixture override")),
        message=str(o.get("message", "from fixture")),
        severity=o.get("severity"),
        evidence_refs=list(o.get("evidence_refs") or ["fixture"]),
    )


def provider_auth_focus(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    root: Path = ctx["root"]
    try:
        from focus_authority import load_focus

        loaded = load_focus(root)
    except Exception as exc:  # noqa: BLE001
        return _result(
            check,
            "unknown",
            observed=type(exc).__name__,
            message="focus loader failed",
        )
    if loaded.path is None:
        return _result(
            check,
            "fail",
            observed="20_live/focus/current.{yaml,json} absent",
            message="structured focus authority not present (ADR-044 / MPE-024)",
            severity="high",
            evidence_refs=["20_live/focus/"],
        )
    if not loaded.ok:
        return _result(
            check,
            "fail",
            observed="; ".join(loaded.errors)[:300],
            message="focus authority failed validation",
            severity="high",
            evidence_refs=[str(loaded.path.name)],
        )
    if loaded.warnings:
        return _result(
            check,
            "stale" if any("stale" in w or "past" in w for w in loaded.warnings) else "warn",
            observed=f"project={loaded.primary_project}; " + "; ".join(loaded.warnings),
            message="focus present with warnings",
            severity="low",
            evidence_refs=[str(loaded.path.name)],
        )
    return _result(
        check,
        "pass",
        observed=f"project={loaded.primary_project} revision={loaded.revision}",
        message="structured focus authority parses within review window",
        evidence_refs=[str(loaded.path.name)],
    )


def provider_sched_service(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    """SCHED-001: launchd present + last run healthy with provenance preference."""
    root: Path = ctx["root"]
    try:
        sys.path.insert(0, str(root / "scripts"))
        import eval_schedule as es  # type: ignore

        health = es.assess_schedule_health()
    except Exception as exc:  # noqa: BLE001
        return _result(check, "unknown", observed=type(exc).__name__, message="schedule assess failed")
    if health.problems:
        return _result(
            check,
            "fail",
            observed="; ".join(health.problems)[:300],
            message="scheduler hard problems present",
            severity="high",
        )
    if health.degraded:
        return _result(
            check,
            "fail",
            observed="; ".join(health.degraded)[:300],
            message="scheduler degraded (no launchd-proven run)",
            severity="high",
        )
    return _result(
        check,
        "pass",
        observed=(
            f"weekly={health.last_weekly and health.last_weekly.get('run_id')} "
            f"trigger={health.last_weekly and health.last_weekly.get('trigger')}"
        ),
        message="scheduler service + provenance ok",
    )


def provider_sched_provenance(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    """SCHED-002: latest scheduled success came from launchd, not manual substitute."""
    root: Path = ctx["root"]
    try:
        sys.path.insert(0, str(root / "scripts"))
        import eval_schedule as es  # type: ignore

        health = es.assess_schedule_health()
    except Exception as exc:  # noqa: BLE001
        return _result(check, "unknown", observed=type(exc).__name__, message="schedule assess failed")
    last = health.last_weekly
    if not last:
        return _result(check, "fail", observed="no weekly run", message="no scheduled weekly run")
    trigger = last.get("trigger")
    if trigger == "launchd" and last.get("all_passed"):
        return _result(
            check,
            "pass",
            observed=f"run_id={last.get('run_id')} trigger=launchd",
            message="latest weekly success has launchd provenance",
        )
    return _result(
        check,
        "fail",
        observed=f"run_id={last.get('run_id')} trigger={trigger!r} all_passed={last.get('all_passed')}",
        message="latest weekly is not a launchd-proven success",
        severity="high",
    )


def provider_task_manifest_quarantine(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    root: Path = ctx["root"]
    path = root / "30_projects" / "tasks_manifest.json"
    if not path.exists():
        return _result(check, "fail", observed="tasks_manifest.json missing", message="no task projection")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return _result(check, "fail", observed=type(exc).__name__, message="manifest unreadable")
    q = payload.get("quarantine") if isinstance(payload, dict) else None
    if not isinstance(q, dict) or q.get("status") != "quarantined":
        return _result(
            check,
            "fail",
            observed="quarantine.status missing or not quarantined",
            message="task projection not quarantined — may be mistaken for executable work",
            severity="critical",
            evidence_refs=["30_projects/tasks_manifest.json"],
        )
    tasks = payload.get("tasks") or []
    executable_true = sum(1 for t in tasks if isinstance(t, dict) and t.get("executable") is True)
    if executable_true:
        return _result(
            check,
            "fail",
            observed=f"executable=true count={executable_true}",
            message="quarantined manifest still marks rows executable",
            severity="high",
        )
    return _result(
        check,
        "pass",
        observed=f"quarantined n={len(tasks)} baseline={str(q.get('baseline_sha256') or '')[:12]}…",
        message="task projection quarantined; not executable authority",
        evidence_refs=["30_projects/tasks_manifest.json"],
    )


def _detect_project_from_state(state_path: Path) -> str | None:
    if not state_path.exists():
        return None
    found = False
    for line in state_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().lower() == "## active project":
            found = True
            continue
        if found:
            value = line.strip()
            if value and not value.startswith("#"):
                return value
            if value.startswith("#"):
                break
    return None


def provider_session_project_path(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    root: Path = ctx["root"]
    state = root / "STATE.md"
    project = _detect_project_from_state(state)
    if not project:
        return _result(
            check,
            "fail",
            observed="no Active Project in STATE.md",
            message="session selected project missing",
            severity="high",
        )
    # slug path: first token if simple, else whole line as slug folder attempt
    slug = project.strip()
    # compound narrative → almost certainly invalid as single path segment
    if " + " in slug or "(" in slug:
        bad = root / "30_projects" / re.sub(r"[^\w.\-]+", "-", slug.lower()).strip("-") / "README.md"
        return _result(
            check,
            "fail",
            observed=f"compound STATE project label; path would be missing ({bad.name}…)",
            message="session-open false-green class: compound focus cannot resolve project path",
            severity="critical",
            evidence_refs=["STATE.md"],
        )
    readme = root / "30_projects" / slug / "README.md"
    if readme.exists():
        return _result(
            check,
            "pass",
            observed=f"30_projects/{slug}/README.md exists",
            message="selected project path resolves",
            evidence_refs=[f"30_projects/{slug}/README.md"],
        )
    return _result(
        check,
        "fail",
        observed=f"30_projects/{slug}/README.md missing",
        message="selected project path does not exist",
        severity="critical",
        evidence_refs=["STATE.md"],
    )


def provider_project_index_check(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    root: Path = ctx["root"]
    script = root / "bin" / "sync-project-index"
    if not script.exists():
        return _result(check, "unknown", observed="bin/sync-project-index missing", message="tool absent")
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(script), "--check"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=min(int(check.get("timeout_seconds") or 10), 30),
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(check, "unknown", observed=str(type(exc).__name__), message="index check failed to run")
    ms = int((time.perf_counter() - t0) * 1000)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0 and "current" in out.lower():
        return _result(
            check,
            "pass",
            observed="sync-project-index --check current",
            message="generated index matches authorities (parser rules)",
            duration_ms=ms,
        )
    return _result(
        check,
        "fail",
        observed=f"exit={proc.returncode}; {(out.strip().splitlines() or [''])[0][:200]}",
        message="project index stale or invalid",
        severity="high",
        duration_ms=ms,
    )


def provider_eval_registry_strict(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    root: Path = ctx["root"]
    script = root / "bin" / "eval-registry"
    if not script.exists():
        return _result(check, "unknown", observed="bin/eval-registry missing", message="tool absent")
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(script), "check", "--strict"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=min(int(check.get("timeout_seconds") or 15), 60),
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(check, "unknown", observed=str(type(exc).__name__), message="registry check failed to run")
    ms = int((time.perf_counter() - t0) * 1000)
    out = (proc.stdout or "") + (proc.stderr or "")
    # count problems without dumping paths that might be sensitive — keep count only
    m = re.search(r"(\d+)\s+problem", out)
    n = int(m.group(1)) if m else (0 if proc.returncode == 0 else -1)
    if proc.returncode == 0:
        return _result(
            check,
            "pass",
            observed="0 strict problems",
            message="eval-registry strict clean",
            duration_ms=ms,
        )
    return _result(
        check,
        "fail",
        observed=f"strict problems={n if n >= 0 else 'unknown'}; exit={proc.returncode}",
        message="eval-registry strict failures remain",
        severity="medium",
        duration_ms=ms,
    )


def provider_mg_db_presence(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    home = Path.home() / ".mindgraph"
    knowledge = home / "mainframe.sqlite"
    projects = home / "mainframe-projects.sqlite"
    missing = [p.name for p in (knowledge, projects) if not p.exists() or p.stat().st_size < 10_000]
    if missing:
        return _result(
            check,
            "fail",
            observed=f"missing or stub-like: {', '.join(missing)}",
            message="installed MindGraph DBs not healthy by size/presence",
            severity="high",
        )
    # schema sniff read-only
    try:
        con = sqlite3.connect(f"file:{knowledge}?mode=ro", uri=True)
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
        need = {"documents", "chunks"}
        if not need.issubset(tables):
            return _result(
                check,
                "fail",
                observed=f"knowledge tables missing {sorted(need - tables)}",
                message="schema incomplete",
                severity="high",
            )
    except Exception as exc:  # noqa: BLE001
        return _result(check, "unknown", observed=type(exc).__name__, message="could not open knowledge DB")
    return _result(
        check,
        "pass",
        observed="~/.mindgraph mainframe + projects DBs present with basic tables",
        message="DB presence/schema sniff ok (not freshness/coverage)",
    )


def provider_mg_manifest_coverage(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    root: Path = ctx["root"]
    man_path = root / "30_projects" / "mindgraph-projects.json"
    projects_dir = root / "30_projects"
    if not man_path.exists():
        return _result(check, "fail", observed="mindgraph-projects.json missing", message="no coverage policy file")
    try:
        man = json.loads(man_path.read_text(encoding="utf-8"))
        names = man.get("projects") or []
    except Exception as exc:  # noqa: BLE001
        return _result(check, "fail", observed=type(exc).__name__, message="manifest unreadable")
    real = sorted(
        p.name
        for p in projects_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".") and (p / "README.md").exists()
    )
    set_m, set_r = set(names), set(real)
    missing_dirs = sorted(set_m - set_r)
    omitted = sorted(set_r - set_m)
    # active omitted is worse
    active_omitted = []
    for slug in omitted:
        text = (projects_dir / slug / "README.md").read_text(encoding="utf-8", errors="replace")[:1500]
        if re.search(r'^project_state:\s*["\']?active', text, re.M):
            active_omitted.append(slug)
    if missing_dirs or active_omitted or omitted:
        return _result(
            check,
            "fail",
            observed=(
                f"manifest={len(names)} real={len(real)} "
                f"missing_dirs={len(missing_dirs)} omitted={len(omitted)} "
                f"active_omitted={active_omitted}"
            ),
            message="project MindGraph coverage incomplete or stale",
            severity="high",
            evidence_refs=["30_projects/mindgraph-projects.json"],
        )
    return _result(check, "pass", observed=f"manifest covers all {len(real)} projects", message="coverage ok")


def provider_cli_mutation_help_safety(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    """Source inspection only — never invoke --help on unsafe wrappers."""
    root: Path = ctx["root"]
    path = root / "bin" / "mindgraph-refresh-projects"
    if not path.exists():
        return _result(check, "unknown", observed="wrapper missing", message="cannot assess")
    src = path.read_text(encoding="utf-8", errors="replace")
    has_help = bool(
        re.search(r"--help\|-h|-h\|--help", src)
        or re.search(r"usage\(\)|Show this help", src)
        or ("--help)" in src and "case" in src)
    )
    has_unknown_fail = bool(
        re.search(r"unknown option|unknown flag", src, re.I)
        or ('-*)' in src and "exit 2" in src)
    )
    requires_apply = "--apply" in src and "refusing to mutate without --apply" in src
    # Legacy unsafe: only leading --dry-run accepted, no help, falls through to ingest
    legacy_unsafe = (
        re.search(r'\$\{1:-\}.*"--dry-run"', src) is not None
        and not has_help
        and "--apply" not in src
    )
    if legacy_unsafe:
        return _result(
            check,
            "fail",
            observed="no --help handler; non-dry-run first args fall through to ingest",
            message="bin/mindgraph-refresh-projects violates help/unknown fail-closed (static proof)",
            severity="critical",
            evidence_refs=["bin/mindgraph-refresh-projects"],
        )
    if has_help and has_unknown_fail and requires_apply:
        return _result(
            check,
            "pass",
            observed="help + unknown fail-closed + --apply mutation boundary present",
            message="CLI help safety contract present (static Unit 2.1)",
            evidence_refs=["bin/mindgraph-refresh-projects"],
        )
    if has_help and has_unknown_fail:
        return _result(
            check,
            "warn",
            observed="help/unknown present; --apply boundary unclear",
            message="partial CLI safety",
            severity="low",
        )
    return _result(
        check,
        "fail",
        observed=f"has_help={has_help} unknown_fail={has_unknown_fail} apply={requires_apply}",
        message="CLI help/unknown/apply contract incomplete",
        severity="high",
        evidence_refs=["bin/mindgraph-refresh-projects"],
    )


def provider_ws_db_presence(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    root: Path = ctx["root"]
    db = root / "20_live" / "workstation" / "workstation.sqlite"
    if not db.exists():
        return _result(check, "fail", observed="workstation.sqlite missing", message="storage preflight fail")
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
    except Exception as exc:  # noqa: BLE001
        return _result(check, "fail", observed=type(exc).__name__, message="cannot open workstation db")
    if "tasks" not in tables and "runs" not in tables:
        return _result(check, "fail", observed=f"tables={sorted(tables)[:12]}", message="unexpected schema")
    return _result(
        check,
        "pass",
        observed=f"db size={db.stat().st_size} tables={len(tables)}",
        message="workstation storage present (not operational fullness)",
    )


def provider_ws_operational_rows(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    root: Path = ctx["root"]
    db = root / "20_live" / "workstation" / "workstation.sqlite"
    if not db.exists():
        return _result(check, "unknown", observed="db missing", message="skip operational row probe")
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        runs = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0] if _has_table(con, "runs") else 0
        approvals = (
            con.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] if _has_table(con, "approvals") else 0
        )
        artifacts = (
            con.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] if _has_table(con, "artifacts") else 0
        )
        tasks = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] if _has_table(con, "tasks") else 0
        con.close()
    except Exception as exc:  # noqa: BLE001
        return _result(check, "unknown", observed=type(exc).__name__, message="row probe failed")
    if runs == 0 and approvals == 0 and artifacts == 0 and tasks > 0:
        return _result(
            check,
            "fail",
            observed=f"tasks={tasks} runs={runs} approvals={approvals} artifacts={artifacts}",
            message="projection full of tasks but zero operational runs/approvals/artifacts",
            severity="high",
        )
    if runs == 0 and tasks == 0:
        return _result(
            check,
            "warn",
            observed="empty operational and task tables",
            message="workstation empty",
        )
    return _result(
        check,
        "pass",
        observed=f"tasks={tasks} runs={runs} approvals={approvals} artifacts={artifacts}",
        message="operational rows present or explicitly empty with no false-full tasks",
    )


def _has_table(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def provider_sec_secret_store(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    """Presence/mode only — never print secret values."""
    root: Path = ctx["root"]
    # operator disposition can force pass via fixture or marker file
    disposition = root / "20_live" / "security" / "SEC-001-disposition.md"
    mcp = root / ".mcp.json"
    issues: list[str] = []
    if mcp.exists():
        mode = mcp.stat().st_mode
        if mode & stat.S_IROTH:
            issues.append("mcp_world_readable")
        if mode & stat.S_IRGRP:
            issues.append("mcp_group_readable")
        try:
            data = json.loads(mcp.read_text(encoding="utf-8"))
            blob = json.dumps(data)
            # detect secret-shaped keys without values
            if re.search(r"(?i)client_secret|api_key|refresh_token", blob):
                # check if values look like placeholders
                def walk(o: Any, path: str = "") -> list[str]:
                    hits: list[str] = []
                    if isinstance(o, dict):
                        for k, v in o.items():
                            p = f"{path}.{k}" if path else k
                            if re.search(r"(?i)secret|token|password|api_key", k) and isinstance(v, str):
                                if v and not v.startswith("${") and "REDACTED" not in v and len(v) > 8:
                                    hits.append(p)
                            hits.extend(walk(v, p))
                    elif isinstance(o, list):
                        for i, v in enumerate(o[:20]):
                            hits.extend(walk(v, f"{path}[{i}]"))
                    return hits

                embedded = walk(data)
                if embedded:
                    issues.append(f"embedded_secret_fields={len(embedded)}")
        except Exception:
            issues.append("mcp_unreadable")
    else:
        issues.append("mcp_absent")

    # disposition file can record accepted residual risk
    accepted = False
    if disposition.exists():
        text = disposition.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?i)status:\s*accepted|disposition:\s*accepted|residual.?risk.?accepted", text):
            accepted = True

    if not issues:
        return _result(check, "pass", observed="no world-readable secret-shaped stores found", message="SEC-001 clean")
    if accepted:
        return _result(
            check,
            "warn",
            observed=f"issues={issues}; operator disposition accepted",
            message="SEC-001 residual risk accepted by operator disposition",
            severity="low",
            evidence_refs=["20_live/security/SEC-001-disposition.md"],
        )
    return _result(
        check,
        "fail",
        observed=f"issues={issues}",
        message="secret store mode or embedding not approved",
        severity="high",
        evidence_refs=[".mcp.json"],
    )


PROVIDERS: dict[str, ProviderFn] = {
    "unimplemented": provider_unimplemented,
    "auth_focus": provider_auth_focus,
    "session_project_path": provider_session_project_path,
    "project_index_check": provider_project_index_check,
    "eval_registry_strict": provider_eval_registry_strict,
    "mg_db_presence": provider_mg_db_presence,
    "mg_manifest_coverage": provider_mg_manifest_coverage,
    "cli_mutation_help_safety": provider_cli_mutation_help_safety,
    "ws_db_presence": provider_ws_db_presence,
    "ws_operational_rows": provider_ws_operational_rows,
    "sec_secret_store": provider_sec_secret_store,
    "task_manifest_quarantine": provider_task_manifest_quarantine,
    "sched_service": provider_sched_service,
    "sched_provenance": provider_sched_provenance,
}


def run_provider(check: dict[str, Any], ctx: dict[str, Any]) -> CheckResult:
    # Fixture overrides always win when present
    overridden = provider_fixture_override(check, ctx)
    if overridden is not None:
        return overridden

    name = check.get("provider") or "unimplemented"
    fn = PROVIDERS.get(str(name), provider_unimplemented)
    if check.get("mutates") is True:
        return _result(
            check,
            "fail",
            observed="mutates=true",
            message="doctor refused mutating provider",
            severity="critical",
        )
    t0 = time.perf_counter()
    try:
        result = fn(check, ctx)
    except Exception as exc:  # noqa: BLE001 — provider fault → unknown/fail
        result = _result(
            check,
            "unknown",
            observed=type(exc).__name__,
            message=f"provider exception: {type(exc).__name__}",
            severity="high",
        )
    if result.duration_ms == 0:
        result.duration_ms = int((time.perf_counter() - t0) * 1000)
    return result
