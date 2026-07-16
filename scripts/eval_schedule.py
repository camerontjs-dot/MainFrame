#!/usr/bin/env python3
"""Run MainFrame eval suites on a fixed cadence and record schedule manifests."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "20_live" / "eval-registry"
SCHEDULE_LOG = REGISTRY_DIR / "schedule-runs.jsonl"
PROCESS_EVAL_OUTPUTS = ROOT / "30_projects" / "mainframe-process-eval" / "outputs"
MINDGRAPH_PROBE = ROOT / "30_projects" / "mindgraph-eval" / "scripts" / "retrieval_quality_probe.py"
MINDGRAPH_LIVE_ENVELOPE = (
    ROOT / "30_projects" / "mindgraph-eval" / "scripts" / "live_envelope_probe.py"
)
MINDGRAPH_GRAPH_HEALTH = (
    ROOT / "30_projects" / "mindgraph-eval" / "scripts" / "graph_health_trend.py"
)
MINDGRAPH_PROJECT = ROOT / "mindgraph"
DEFAULT_DB = Path.home() / ".mindgraph" / "mainframe.sqlite"
DEFAULT_INTENT_DB = Path.home() / ".mindgraph" / "mainframe-intent.sqlite"
LOG_DIR = REGISTRY_DIR / "logs"
DAEMON_LABEL_DAILY = "com.mainframe.eval-schedule.daily"
DAEMON_LABEL_WEEKLY = "com.mainframe.eval-schedule.weekly"
SCHEDULED_PROBE_QUERY_IDS = (
    "q04_memory_cite_forget,q07_ai_detection,q11_negative_live_state,q12_negative_inbox"
)
STEP_PROCESS_IDS = {
    "ingest_minion_dry_run": ["cli-ingest-minion", "workflow-ingest-minion"],
    "mindgraph_refresh_dry_run": ["cli-mindgraph-refresh", "workflow-mindgraph-refresh"],
    "sync_project_index_check": ["cli-sync-project-index"],
    "eval_registry_status": ["cli-eval-registry"],
    "unittest_suite": ["workflow-process-evaluation"],
    "workflow_report_7d": ["cli-workflow-report", "workflow-workflow-telemetry"],
    "mindgraph_retrieval_probe": ["workflow-mindgraph-refresh"],
    "mindgraph_live_envelope": ["workflow-mindgraph-refresh"],
    "mindgraph_graph_health": ["workflow-mindgraph-refresh"],
    "eval_registry_harvest": ["cli-eval-registry"],
}
WEEKLY_STALE_DAYS = 8
DAILY_STALE_DAYS = 2
OPERATOR_CARD = REGISTRY_DIR / "OPERATOR.md"


@dataclass
class StepResult:
    name: str
    command: list[str]
    exit_code: int
    duration_seconds: float
    process_ids: list[str] = field(default_factory=list)
    stdout_tail: str = ""
    stderr_tail: str = ""
    skipped: bool = False
    skip_reason: str | None = None


@dataclass
class ScheduleRun:
    run_id: str
    cadence: str
    started_at: str
    finished_at: str
    git_sha: str | None
    all_passed: bool
    steps: list[StepResult] = field(default_factory=list)
    # Unit 2.4: provenance for control honesty (launchd vs manual)
    trigger: str = "manual"


@dataclass
class ScheduleHealth:
    launchd_daily: bool
    launchd_weekly: bool
    last_weekly: dict[str, Any] | None
    last_daily: dict[str, Any] | None
    weekly_age_days: float | None
    daily_age_days: float | None
    problems: list[str] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems and not self.degraded

    @property
    def status_label(self) -> str:
        if self.problems:
            return "FAIL"
        if self.degraded:
            return "DEGRADED"
        return "OK"


def repo_root() -> Path:
    return ROOT


def git_short_sha(root: Path) -> str | None:
    try:
        res = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res.returncode == 0:
            return res.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None
    return None


def tail_text(text: str, max_lines: int = 12) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def run_step(name: str, command: list[str], *, cwd: Path, timeout: int | None = None) -> StepResult:
    started = time.monotonic()
    try:
        res = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.monotonic() - started
        return StepResult(
            name=name,
            command=command,
            exit_code=res.returncode,
            duration_seconds=round(duration, 3),
            process_ids=STEP_PROCESS_IDS.get(name, []),
            stdout_tail=tail_text(res.stdout),
            stderr_tail=tail_text(res.stderr),
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return StepResult(
            name=name,
            command=command,
            exit_code=124,
            duration_seconds=round(duration, 3),
            process_ids=STEP_PROCESS_IDS.get(name, []),
            stdout_tail=tail_text(stdout),
            stderr_tail=tail_text(stderr or "timeout"),
        )
    except OSError as exc:
        duration = time.monotonic() - started
        return StepResult(
            name=name,
            command=command,
            exit_code=127,
            duration_seconds=round(duration, 3),
            process_ids=STEP_PROCESS_IDS.get(name, []),
            stderr_tail=str(exc),
        )


def skipped_step(name: str, reason: str) -> StepResult:
    return StepResult(
        name=name,
        command=[],
        exit_code=0,
        duration_seconds=0.0,
        process_ids=STEP_PROCESS_IDS.get(name, []),
        skipped=True,
        skip_reason=reason,
    )


def parse_harvest_stats(stdout: str) -> dict[str, int]:
    stats = {"errors": 0, "runs_new": 0, "skipped": 0}
    match = re.search(
        r"runs_new=(\d+).*?skipped=(\d+).*?errors=(\d+)",
        stdout.replace("\n", " "),
    )
    if match:
        stats["runs_new"] = int(match.group(1))
        stats["skipped"] = int(match.group(2))
        stats["errors"] = int(match.group(3))
    return stats


def make_run_id(cadence: str) -> str:
    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    return f"{stamp}-scheduled-{cadence}"


def mindgraph_uv_python_cmd(script: Path, *script_args: str) -> list[str] | None:
    """Run a MindGraph-eval script with the mindgraph project's deps (PyYAML, etc.).

    Operator card and live_envelope_probe docs use
    ``uv run --project mindgraph python …``. Bare ``sys.executable`` lacks
    PyYAML on the MainFrame host Python and fails the weekly canary in <1s.
    """
    uv = shutil.which("uv")
    if not uv or not MINDGRAPH_PROJECT.is_dir():
        return None
    return [
        uv,
        "run",
        "--project",
        str(MINDGRAPH_PROJECT),
        "python",
        str(script),
        *script_args,
    ]


def steps_for_cadence(
    cadence: str,
    *,
    skip_tests: bool,
    skip_probe: bool,
    full_probe: bool,
    run_id: str,
) -> list[tuple[str, list[str] | None, str | None]]:
    """Return (name, command-or-None, skip_reason) tuples."""
    bin_dir = repo_root() / "bin"
    py = sys.executable
    root = repo_root()

    out: list[tuple[str, list[str] | None, str | None]] = []

    def add(name: str, cmd: list[str]) -> None:
        out.append((name, cmd, None))

    add("ingest_minion_dry_run", [str(bin_dir / "ingest-minion"), "run", "--dry-run"])
    add("mindgraph_refresh_dry_run", [str(bin_dir / "mindgraph-refresh"), "--dry-run"])
    add("sync_project_index_check", [str(bin_dir / "sync-project-index"), "--check"])
    add("eval_registry_status", [str(bin_dir / "eval-registry"), "status"])

    if cadence in {"weekly", "monthly"} and not skip_tests:
        add("unittest_suite", [py, "-m", "unittest", "discover", "-s", "tests"])

    if cadence == "monthly":
        add("workflow_report_7d", [str(bin_dir / "workflow-report"), "--days", "7", "--json"])

    if cadence in {"weekly", "monthly"} and not skip_probe:
        if MINDGRAPH_PROBE.exists() and DEFAULT_DB.exists():
            probe_run_id = f"{run_id}-probe"
            probe_cmd = [
                py,
                str(MINDGRAPH_PROBE),
                "--run-id",
                probe_run_id,
                "--registry",
            ]
            if not full_probe:
                probe_cmd.extend(
                    ["--fused-only", "--query-ids", SCHEDULED_PROBE_QUERY_IDS]
                )
            add("mindgraph_retrieval_probe", probe_cmd)
        else:
            reason = "probe script or MindGraph DB missing"
            out.append(("mindgraph_retrieval_probe", None, reason))

        # Post-install / weekly ritual: score live envelope against installed intent graph.
        # Requires mindgraph project env (PyYAML) — not bare host Python.
        if MINDGRAPH_LIVE_ENVELOPE.exists() and DEFAULT_INTENT_DB.exists():
            env_run_id = f"{run_id}-live-envelope"
            live_cmd = mindgraph_uv_python_cmd(
                MINDGRAPH_LIVE_ENVELOPE, "--run-id", env_run_id
            )
            if live_cmd is not None:
                add("mindgraph_live_envelope", live_cmd)
            else:
                out.append(
                    (
                        "mindgraph_live_envelope",
                        None,
                        "uv or mindgraph/ project missing (live envelope needs PyYAML)",
                    )
                )
        else:
            out.append(
                (
                    "mindgraph_live_envelope",
                    None,
                    "live envelope script or intent DB missing",
                )
            )

        if MINDGRAPH_GRAPH_HEALTH.exists():
            add("mindgraph_graph_health", [py, str(MINDGRAPH_GRAPH_HEALTH)])
        else:
            out.append(("mindgraph_graph_health", None, "graph health script missing"))

    return out


def resolve_trigger(explicit: str | None = None) -> str:
    """Record how a suite was started (Unit 2.4 provenance)."""
    if explicit in {"launchd", "manual", "unknown"}:
        return explicit
    env = (os.environ.get("MAINFRAME_EVAL_TRIGGER") or "").strip().lower()
    if env in {"launchd", "manual", "unknown"}:
        return env
    return "manual"


def execute_suite(
    cadence: str,
    *,
    skip_tests: bool = False,
    skip_probe: bool = False,
    full_probe: bool = False,
    trigger: str | None = None,
) -> ScheduleRun:
    root = repo_root()
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = make_run_id(cadence)
    steps: list[StepResult] = []

    for name, command, skip_reason in steps_for_cadence(
        cadence,
        skip_tests=skip_tests,
        skip_probe=skip_probe,
        full_probe=full_probe,
        run_id=run_id,
    ):
        if command is None:
            steps.append(skipped_step(name, skip_reason or "skipped"))
            continue
        if name == "unittest_suite":
            timeout = 1800
        elif name in {"mindgraph_retrieval_probe", "mindgraph_live_envelope"}:
            timeout = 1200
        else:
            timeout = 600
        steps.append(run_step(name, command, cwd=root, timeout=timeout))

    finished_at = datetime.now(timezone.utc).isoformat()
    all_passed = all(s.exit_code == 0 for s in steps if not s.skipped)
    return ScheduleRun(
        run_id=run_id,
        cadence=cadence,
        started_at=started_at,
        finished_at=finished_at,
        git_sha=git_short_sha(root),
        all_passed=all_passed,
        steps=steps,
        trigger=resolve_trigger(trigger),
    )


def append_schedule_log(run: ScheduleRun, *, dry_run: bool) -> None:
    if dry_run:
        return
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run.run_id,
        "cadence": run.cadence,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "git_sha": run.git_sha,
        "all_passed": run.all_passed,
        "trigger": run.trigger,
        "steps": [asdict(s) for s in run.steps],
    }
    with SCHEDULE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_process_eval_output(run: ScheduleRun, *, dry_run: bool) -> Path | None:
    if dry_run or run.cadence == "daily":
        return None

    PROCESS_EVAL_OUTPUTS.mkdir(parents=True, exist_ok=True)
    out_path = PROCESS_EVAL_OUTPUTS / f"{run.run_id}.md"
    failed = [s.name for s in run.steps if not s.skipped and s.exit_code != 0]
    skipped = [s.name for s in run.steps if s.skipped]
    passed_count = sum(1 for s in run.steps if not s.skipped and s.exit_code == 0)
    step_total = sum(1 for s in run.steps if not s.skipped)

    answer = (
        f"Scheduled {run.cadence} suite {'passed' if run.all_passed else 'failed'}: "
        f"{passed_count}/{step_total} steps green."
    )
    if failed:
        answer += f" Failed: {', '.join(failed)}."
    if skipped:
        answer += f" Skipped: {', '.join(skipped)}."

    metrics = [
        {
            "name": "scheduled_steps_passed",
            "slice": run.cadence,
            "value": passed_count,
            "n": step_total,
            "unit": "count",
        },
        {
            "name": "scheduled_all_passed",
            "slice": run.cadence,
            "value": 1 if run.all_passed else 0,
            "n": 1,
            "unit": "binary",
        },
    ]

    irregularities: list[dict[str, Any]] = []
    for step in run.steps:
        if step.skipped:
            irregularities.append(
                {
                    "id": f"skipped-{step.name}",
                    "severity": "info",
                    "category": "intentional_skip",
                    "observation": step.skip_reason or "step skipped",
                    "context": run.run_id,
                    "resolved": True,
                }
            )
        elif step.exit_code != 0:
            irregularities.append(
                {
                    "id": f"failed-{step.name}",
                    "severity": "medium" if run.cadence == "weekly" else "high",
                    "category": "step_failure",
                    "observation": f"{step.name} exit_code={step.exit_code}",
                    "context": step.stderr_tail or step.stdout_tail or "",
                    "resolved": False,
                }
            )
        elif step.name == "eval_registry_harvest":
            stats = parse_harvest_stats(step.stdout_tail)
            if stats["errors"]:
                irregularities.append(
                    {
                        "id": "harvest-parse-errors",
                        "severity": "low",
                        "category": "registry_hygiene",
                        "observation": f"eval-registry harvest reported errors={stats['errors']}",
                        "context": "outputs missing metric extract or non-harvestable artifacts",
                        "resolved": False,
                    }
                )

    yaml_metrics = "\n".join(
        f"  - name: {m['name']}\n    slice: {m['slice']}\n    value: {m['value']}\n    n: {m['n']}\n    unit: {m['unit']}"
        for m in metrics
    )
    if irregularities:
        yaml_irreg = "\n".join(
            "  - id: {id}\n    severity: {severity}\n    category: {category}\n    observation: \"{observation}\"\n    context: \"{context}\"\n    resolved: {resolved}".format(
                id=i["id"],
                severity=i["severity"],
                category=i["category"],
                observation=i["observation"].replace('"', "'"),
                context=(i.get("context") or "").replace('"', "'")[:200],
                resolved=str(i["resolved"]).lower(),
            )
            for i in irregularities
        )
    else:
        yaml_irreg = "  []"

    step_rows = "\n".join(
        f"| {s.name} | {'skip' if s.skipped else s.exit_code} | {s.duration_seconds} | {', '.join(s.process_ids) or 'none'} |"
        for s in run.steps
    )

    body = f"""---
title: "Scheduled process evaluation — {run.cadence} — {date.today().isoformat()}"
domain: "knowledge-systems"
type: "project"
status: "active"
study_type: "observational"
eval_run_id: "{run.run_id}"
protocol_ref: ".context/workflows/eval-schedule.md"
decision_sentence: "If scheduled steps fail twice in a row, fix the failing bin before changing agent workflows."
project: "mainframe-process-eval"
tags: ["evaluation", "eval-registry", "eval-profile", "scheduled"]
updated: "{date.today().isoformat()}"
source: "bin/eval-schedule"
---

# Scheduled process evaluation — {run.cadence} — {date.today().isoformat()}

## Answer

{answer}

## Checks run

| Step | Exit | Duration (s) | Process IDs |
| --- | ---: | ---: | --- |
{step_rows}

## Metric extract (eval-registry)

```yaml
registry:
  project: mainframe-process-eval
  run_id: {run.run_id}
  study_type: observational
  protocol_ref: .context/workflows/eval-schedule.md
  date: {date.today().isoformat()}
  decision_sentence: "If scheduled steps fail twice in a row, fix the failing bin before changing agent workflows."
  artifact_path: outputs/{run.run_id}.md
  raw_path: null
  environment:
    git_sha: {run.git_sha or "null"}
    cadence: {run.cadence}
  decision_use: regression_only
metrics:
{yaml_metrics}
irregularities:
{yaml_irreg}
```
"""
    out_path.write_text(body, encoding="utf-8")
    return out_path


def print_run_summary(run: ScheduleRun) -> None:
    print(
        f"eval-schedule: cadence={run.cadence} run_id={run.run_id} "
        f"all_passed={run.all_passed} trigger={run.trigger}"
    )
    for step in run.steps:
        if step.skipped:
            print(f"  - {step.name}: SKIP ({step.skip_reason})")
        else:
            print(f"  - {step.name}: exit={step.exit_code} duration={step.duration_seconds}s")


def plist_path(label: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def build_plist(label: str, cadence: str, root: Path) -> str:
    log_out = LOG_DIR / f"{cadence}.log"
    log_err = LOG_DIR / f"{cadence}.err"
    script = root / "bin" / "eval-schedule"
    if cadence == "daily":
        calendar = """
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>15</integer>
    </dict>"""
    else:
        calendar = """
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{script}</string>
        <string>run</string>
        <string>--cadence</string>
        <string>{cadence}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{root}</string>{calendar}
    <key>StandardOutPath</key>
    <string>{log_out}</string>
    <key>StandardErrorPath</key>
    <string>{log_err}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINFRAME_EVAL_TRIGGER</key>
        <string>launchd</string>
    </dict>
</dict>
</plist>
"""


def launchctl_load(plist: Path) -> tuple[int, str]:
    subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
    res = subprocess.run(["launchctl", "load", "-w", str(plist)], capture_output=True, text=True)
    return res.returncode, (res.stderr or res.stdout or "").strip()


def cmd_run(args: argparse.Namespace) -> int:
    run = execute_suite(
        args.cadence,
        skip_tests=args.skip_tests,
        skip_probe=args.skip_probe,
        full_probe=args.full_probe,
        trigger=getattr(args, "trigger", None),
    )
    out = write_process_eval_output(run, dry_run=args.dry_run)
    if out:
        print(f"process_eval_output: {out.relative_to(ROOT)}")

    if not args.dry_run and args.cadence in {"weekly", "monthly"}:
        harvest = run_step(
            "eval_registry_harvest",
            [str(ROOT / "bin" / "eval-registry"), "harvest"],
            cwd=ROOT,
        )
        run.steps.append(harvest)
        stats = parse_harvest_stats(harvest.stdout_tail)
        if harvest.exit_code != 0:
            run.all_passed = False
        elif stats["errors"]:
            print(
                f"  - harvest warning: errors={stats['errors']} "
                f"(non-fatal — fix outputs missing metric extract)"
            )

        # Action layer: suite already ran + harvested; portfolio triage so all
        # MainFrame evals are actionable (project-experiment-loop).
        triage_bin = ROOT / "bin" / "project-experiment-loop"
        if triage_bin.exists():
            triage = run_step(
                "eval_portfolio_triage",
                [str(triage_bin), "triage", "--scope", "portfolio"],
                cwd=ROOT,
                timeout=180,
            )
            run.steps.append(triage)
            if triage.exit_code not in (0, 2):
                print(f"  - triage warning: exit={triage.exit_code}")
            else:
                print(
                    "  - eval action card: "
                    f"{(REGISTRY_DIR / 'last-eval-action.md').relative_to(ROOT)}"
                )

    if out and not args.dry_run and run.cadence in {"weekly", "monthly"}:
        out = write_process_eval_output(run, dry_run=False)

    print_run_summary(run)
    append_schedule_log(run, dry_run=args.dry_run)
    return 0 if run.all_passed else 1


def cmd_install(args: argparse.Namespace) -> int:
    root = repo_root()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    ensure_operator_card()
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True, exist_ok=True)

    targets: list[tuple[str, str]] = []
    if args.cadence in {"daily", "both"}:
        targets.append((DAEMON_LABEL_DAILY, "daily"))
    if args.cadence in {"weekly", "both"}:
        targets.append((DAEMON_LABEL_WEEKLY, "weekly"))

    for label, cadence in targets:
        path = plist_path(label)
        path.write_text(build_plist(label, cadence, root), encoding="utf-8")
        code, msg = launchctl_load(path)
        if code == 0:
            print(f"installed: {label} -> {path}")
        else:
            print(f"install warning ({label}): {msg}", file=sys.stderr)
            return 1
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    labels: list[str] = []
    if args.cadence in {"daily", "both"}:
        labels.append(DAEMON_LABEL_DAILY)
    if args.cadence in {"weekly", "both"}:
        labels.append(DAEMON_LABEL_WEEKLY)

    for label in labels:
        path = plist_path(label)
        if path.exists():
            subprocess.run(["launchctl", "unload", str(path)], capture_output=True)
            path.unlink()
            print(f"uninstalled: {label}")
        else:
            print(f"not installed: {label}")
    return 0


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_schedule_runs() -> list[dict[str, Any]]:
    if not SCHEDULE_LOG.exists():
        return []
    runs: list[dict[str, Any]] = []
    for line in SCHEDULE_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            runs.append(json.loads(line))
    return runs


def last_run_for_cadence(runs: list[dict[str, Any]], cadence: str) -> dict[str, Any] | None:
    matches = [r for r in runs if r.get("cadence") == cadence]
    if not matches:
        return None
    return max(matches, key=lambda r: r.get("finished_at") or r.get("started_at") or "")


def assess_schedule_health(*, now: datetime | None = None) -> ScheduleHealth:
    now = now or datetime.now(timezone.utc)
    runs = load_schedule_runs()
    last_weekly = last_run_for_cadence(runs, "weekly")
    last_daily = last_run_for_cadence(runs, "daily")

    weekly_finished = _parse_iso(last_weekly.get("finished_at") if last_weekly else None)
    daily_finished = _parse_iso(last_daily.get("finished_at") if last_daily else None)
    weekly_age = (
        (now - weekly_finished).total_seconds() / 86400 if weekly_finished else None
    )
    daily_age = (now - daily_finished).total_seconds() / 86400 if daily_finished else None

    launchd_daily = plist_path(DAEMON_LABEL_DAILY).exists()
    launchd_weekly = plist_path(DAEMON_LABEL_WEEKLY).exists()
    problems: list[str] = []
    degraded: list[str] = []

    if not launchd_weekly:
        problems.append("launchd weekly agent not installed — run: bin/eval-schedule install --cadence both")
    if not launchd_daily:
        problems.append("launchd daily agent not installed — run: bin/eval-schedule install --cadence both")
    if last_weekly is None:
        problems.append("no weekly eval run logged — run: bin/eval-schedule run --cadence weekly")
    elif weekly_age is not None and weekly_age > WEEKLY_STALE_DAYS:
        problems.append(
            f"weekly eval stale ({weekly_age:.1f}d) — run: bin/eval-schedule run --cadence weekly"
        )
    elif last_weekly and not last_weekly.get("all_passed"):
        problems.append(
            f"last weekly eval failed ({last_weekly.get('run_id')}) — inspect 20_live/eval-registry/logs/"
        )
    if daily_age is not None and daily_age > DAILY_STALE_DAYS:
        problems.append(f"daily eval stale ({daily_age:.1f}d) — check launchd logs")

    # Unit 2.4: recency alone is insufficient — require launchd provenance
    if last_weekly and last_weekly.get("all_passed") and (
        weekly_age is None or weekly_age <= WEEKLY_STALE_DAYS
    ):
        trigger = last_weekly.get("trigger")
        if trigger != "launchd":
            degraded.append(
                "last successful weekly run lacks launchd provenance "
                f"(trigger={trigger!r}); manual/unknown runs cannot prove the service "
                "(Unit 2.4 control-honesty)"
            )

    return ScheduleHealth(
        launchd_daily=launchd_daily,
        launchd_weekly=launchd_weekly,
        last_weekly=last_weekly,
        last_daily=last_daily,
        weekly_age_days=weekly_age,
        daily_age_days=daily_age,
        problems=problems,
        degraded=degraded,
    )


def ensure_operator_card() -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    if OPERATOR_CARD.exists():
        return
    OPERATOR_CARD.write_text(
        """# Eval registry — operator card

**Do not let scheduled evals fade.** This surface is the live reminder.

## Weekly ritual (~15–20 min, after Sunday 07:30 run)

1. `bin/eval-schedule check` — must exit 0
2. `bin/eval-schedule status` — last weekly green?
3. Read latest `30_projects/mainframe-process-eval/outputs/*-scheduled-weekly.md`
4. Read MindGraph canaries: retrieval probe, live-envelope, graph-health-trend under `30_projects/mindgraph-eval/outputs/`
5. `bin/eval-registry status` — new metrics or irregularities?
6. Pick **one** improvement slice; rerun `bin/eval-schedule run --cadence weekly` after the fix

### MindGraph canaries (weekly)

- `mindgraph_retrieval_probe` — q04/q07/q11/q12 fused
- `mindgraph_live_envelope` — installed intent graph (also **required after every intent install**)
- `mindgraph_graph_health` — density trend

Post-intent-install: run `live_envelope_probe.py` until exit 0 before calling the install done.

## Commands

```bash
bin/eval-schedule check
bin/eval-schedule status
bin/eval-schedule run --cadence weekly
bin/eval-schedule run --cadence weekly --full-probe
bin/eval-schedule install --cadence both   # macOS launchd
```

## Surfaces that nag you

- `bin/session-close --check` — warns when eval schedule is unhealthy
- `bin/session-open` — prints eval health on session start
- Lane **EV01** — `30_projects/research-lanes-strategy/lanes/scheduled-process-evaluation/`
- Workflow — `.context/workflows/eval-schedule.md`

## Logs

- Manifest: `20_live/eval-registry/schedule-runs.jsonl`
- launchd: `20_live/eval-registry/logs/{daily,weekly}.{log,err}`
""",
        encoding="utf-8",
    )


def cmd_status(args: argparse.Namespace) -> int:
    ensure_operator_card()
    health = assess_schedule_health()
    runs = load_schedule_runs()
    print(f"schedule_log: {SCHEDULE_LOG}")
    print(f"log_dir: {LOG_DIR}")
    print(f"operator_card: {OPERATOR_CARD}")
    print(f"schedule_runs: {len(runs)}")
    if health.last_weekly:
        weekly_age = (
            f"{health.weekly_age_days:.1f}"
            if health.weekly_age_days is not None
            else "n/a"
        )
        print(
            f"last_weekly: {health.last_weekly.get('run_id')} "
            f"all_passed={health.last_weekly.get('all_passed')} age_days={weekly_age}"
        )
    else:
        print("last_weekly: none")
    if health.last_daily:
        daily_age = (
            f"{health.daily_age_days:.1f}" if health.daily_age_days is not None else "n/a"
        )
        print(
            f"last_daily: {health.last_daily.get('run_id')} "
            f"all_passed={health.last_daily.get('all_passed')} age_days={daily_age}"
        )
    else:
        print("last_daily: none")
    for label in (DAEMON_LABEL_DAILY, DAEMON_LABEL_WEEKLY):
        path = plist_path(label)
        print(f"launchd {label}: {'installed' if path.exists() else 'not installed'} ({path})")
    if health.problems:
        print("problems:")
        for problem in health.problems:
            print(f"  - {problem}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    ensure_operator_card()
    health = assess_schedule_health()
    if health.ok:
        print("eval-schedule check: OK")
        if health.last_weekly and health.weekly_age_days is not None:
            trigger = health.last_weekly.get("trigger") or "unknown"
            print(
                f"  weekly: {health.last_weekly.get('run_id')} "
                f"({health.weekly_age_days:.1f}d ago) trigger={trigger}"
            )
        return 0
    label = health.status_label
    n = len(health.problems) + len(health.degraded)
    print(f"eval-schedule check: {label} ({n} issue(s))")
    for problem in health.problems:
        print(f"  - [problem] {problem}")
    for item in health.degraded:
        print(f"  - [degraded] {item}")
    print(f"operator_card: {OPERATOR_CARD}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="MainFrame scheduled evaluation runner")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Execute a scheduled eval suite")
    run.add_argument("--cadence", choices=["daily", "weekly", "monthly"], default="weekly")
    run.add_argument("--dry-run", action="store_true", help="Run suite but do not write logs/outputs")
    run.add_argument("--skip-tests", action="store_true")
    run.add_argument("--skip-probe", action="store_true")
    run.add_argument(
        "--full-probe",
        action="store_true",
        help="Run full 12-query fused+expanded probe instead of scheduled 4-query fused regression",
    )
    run.add_argument(
        "--trigger",
        choices=["launchd", "manual", "unknown"],
        default=None,
        help="Provenance label for this run (default: MAINFRAME_EVAL_TRIGGER or manual)",
    )
    run.set_defaults(func=cmd_run)

    inst = sub.add_parser("install", help="Install launchd LaunchAgents (macOS)")
    inst.add_argument("--cadence", choices=["daily", "weekly", "both"], default="both")
    inst.set_defaults(func=cmd_install)

    uninst = sub.add_parser("uninstall", help="Remove launchd LaunchAgents")
    uninst.add_argument("--cadence", choices=["daily", "weekly", "both"], default="both")
    uninst.set_defaults(func=cmd_uninstall)

    stat = sub.add_parser("status", help="Show schedule log and launchd state")
    stat.set_defaults(func=cmd_status)

    chk = sub.add_parser("check", help="Exit 1 if launchd missing or eval runs are stale/failed")
    chk.set_defaults(func=cmd_check)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
