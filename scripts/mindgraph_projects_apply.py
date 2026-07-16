"""Staged apply for the projects MindGraph index (ADR-045).

plan  → coverage of manifest vs on-disk projects; dry-run scopes
stage → ingest into a staging DB; verify namespaces; write receipt
promote → backup installed DB; replace from a green stage receipt
status → compare installed DB namespaces to manifest

Never mutates the installed DB without --promote.
Never ingests 20_live telemetry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "30_projects" / "mindgraph-projects.json"
DEEP_MANIFEST = ROOT / "30_projects" / "mindgraph-projects-deep.json"
DEFAULT_INSTALLED = Path.home() / ".mindgraph" / "mainframe-projects.sqlite"
STAGING_DIR = Path.home() / ".mindgraph" / "staging"
RECEIPT_DIR = ROOT / "20_live" / "system-health" / "mindgraph-projects-apply"
REFRESH = ROOT / "bin" / "mindgraph-refresh-projects"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest_projects(manifest_path: Path) -> list[str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    projects = payload.get("projects")
    if not isinstance(projects, list) or not all(isinstance(p, str) for p in projects):
        raise SystemExit(f"manifest.projects must be a string list: {manifest_path}")
    return list(projects)


def real_project_dirs(projects_dir: Path) -> list[str]:
    return sorted(
        p.name
        for p in projects_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".") and (p / "README.md").exists()
    )


def coverage_report(manifest_projects: list[str], real_dirs: list[str]) -> dict[str, Any]:
    set_m, set_r = set(manifest_projects), set(real_dirs)
    return {
        "manifest_count": len(manifest_projects),
        "real_count": len(real_dirs),
        "missing_dirs": sorted(set_m - set_r),
        "omitted_dirs": sorted(set_r - set_m),
        "intersection": sorted(set_m & set_r),
        "complete": set_m <= set_r and len(set_m) == len(set_r),
    }


def namespaces_from_db(db_path: Path) -> dict[str, int]:
    if not db_path.exists():
        return {}
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT namespace, COUNT(*) FROM documents GROUP BY namespace ORDER BY 1"
        ).fetchall()
    finally:
        con.close()
    return {str(n): int(c) for n, c in rows if n}


def verify_stage(
    db_path: Path,
    expected_namespaces: list[str],
) -> dict[str, Any]:
    observed = namespaces_from_db(db_path)
    expected = set(expected_namespaces)
    present = set(observed)
    missing = sorted(expected - present)
    extra = sorted(present - expected)
    return {
        "expected_count": len(expected),
        "observed_count": len(present),
        "doc_counts": observed,
        "missing_namespaces": missing,
        "extra_namespaces": extra,
        "ok": not missing and db_path.exists() and db_path.stat().st_size > 10_000,
    }


def run_refresh_apply(
    db_path: Path,
    *,
    full: bool = False,
    deep: bool = False,
    manifest: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["MINDGRAPH_DB_PATH"] = str(db_path)
    if manifest is not None:
        env["MAINFRAME_MINDGRAPH_PROJECTS_MANIFEST"] = str(manifest)
    cmd = [str(REFRESH), "--apply"]
    if full:
        cmd.append("--full")
    if deep and manifest is None:
        cmd.append("--deep")
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def resolve_manifest(args: argparse.Namespace) -> Path:
    if getattr(args, "manifest", None) and args.manifest != str(DEFAULT_MANIFEST):
        return Path(args.manifest).expanduser()
    if getattr(args, "deep", False):
        return DEEP_MANIFEST
    return Path(args.manifest).expanduser()


def cmd_plan(args: argparse.Namespace) -> int:
    manifest = resolve_manifest(args)
    projects = load_manifest_projects(manifest)
    real = real_project_dirs(ROOT / "30_projects")
    cov = coverage_report(projects, real)
    profile = json.loads(manifest.read_text(encoding="utf-8")).get("profile", "unknown")
    print("mindgraph-projects-apply plan")
    print(f"  profile: {profile}")
    print(f"  manifest: {manifest}")
    print(f"  installed: {args.installed}")
    print(f"  coverage_complete: {cov['complete']}")
    print(f"  manifest_count: {cov['manifest_count']} real_count: {cov['real_count']}")
    includes = json.loads(manifest.read_text(encoding="utf-8")).get("include", [])
    print(f"  include: {includes}")
    if cov["missing_dirs"]:
        print(f"  missing_dirs: {cov['missing_dirs']}")
    if cov["omitted_dirs"]:
        print(f"  omitted_dirs: {cov['omitted_dirs']}")
    # dry-run wrapper for scopes
    env = os.environ.copy()
    env["MINDGRAPH_DB_PATH"] = str(Path(args.installed).expanduser())
    env["MAINFRAME_MINDGRAPH_PROJECTS_MANIFEST"] = str(manifest)
    dry_cmd = [str(REFRESH), "--dry-run"]
    if args.full:
        dry_cmd.append("--full")
    # Manifest path is forced via MAINFRAME_MINDGRAPH_PROJECTS_MANIFEST
    proc = subprocess.run(
        dry_cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    print("--- dry-run ---")
    sys.stdout.write(proc.stdout or "")
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if not cov["complete"]:
        print("plan: coverage incomplete — fix manifest before stage", file=sys.stderr)
        return 1
    if proc.returncode != 0:
        return proc.returncode
    print("plan: OK — ready to --stage")
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    manifest = resolve_manifest(args)
    projects = load_manifest_projects(manifest)
    real = real_project_dirs(ROOT / "30_projects")
    cov = coverage_report(projects, real)
    if not cov["complete"] and not args.allow_incomplete_coverage:
        print("error: manifest coverage incomplete; refuse stage", file=sys.stderr)
        print(json.dumps(cov, indent=2), file=sys.stderr)
        return 1

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    profile = json.loads(manifest.read_text(encoding="utf-8")).get("profile", "default")
    stage_db = STAGING_DIR / f"mainframe-projects-{profile}-{stamp}.sqlite"
    if stage_db.exists():
        stage_db.unlink()

    print(f"stage: profile={profile} ingest → {stage_db}")
    proc = run_refresh_apply(
        stage_db, full=args.full, deep=args.deep, manifest=manifest
    )
    sys.stdout.write(proc.stdout or "")
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print(f"error: stage ingest exit {proc.returncode}", file=sys.stderr)
        return proc.returncode

    # Expected namespaces: scopes that actually exist on disk from manifest
    expected = [p for p in projects if (ROOT / "30_projects" / p).is_dir()]
    verify = verify_stage(stage_db, expected)
    receipt = {
        "schema_version": 1,
        "kind": "mindgraph-projects-stage",
        "as_of": utc_now(),
        "stamp": stamp,
        "manifest": str(manifest),
        "manifest_profile": profile,
        "manifest_sha256": sha256_file(manifest),
        "include": json.loads(manifest.read_text(encoding="utf-8")).get("include"),
        "stage_db": str(stage_db),
        "stage_db_sha256": sha256_file(stage_db),
        "stage_db_size": stage_db.stat().st_size if stage_db.exists() else 0,
        "coverage": cov,
        "verify": verify,
        "green": bool(verify.get("ok")),
        "policy_ref": ".context/live-retention.md",
        "adr": "ADR-045",
    }
    receipt_path = RECEIPT_DIR / f"{stamp}-stage.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"stage receipt: {receipt_path.relative_to(ROOT)}")
    print(f"  namespaces: {verify['observed_count']}/{verify['expected_count']}")
    if verify["missing_namespaces"]:
        print(f"  missing: {verify['missing_namespaces']}")
    if verify["extra_namespaces"]:
        print(f"  extra: {verify['extra_namespaces']}")
    if not receipt["green"]:
        print("stage: NOT GREEN — do not promote", file=sys.stderr)
        return 1
    print("stage: GREEN — promote with:")
    print(f"  bin/mindgraph-projects-apply --promote --receipt {receipt_path}")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    receipt_path = Path(args.receipt).expanduser()
    if not receipt_path.is_absolute():
        # allow relative to ROOT
        cand = ROOT / receipt_path
        if cand.exists():
            receipt_path = cand
    if not receipt_path.exists():
        print(f"error: receipt not found: {receipt_path}", file=sys.stderr)
        return 1
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not receipt.get("green"):
        print("error: refuse promote of non-green receipt", file=sys.stderr)
        return 1
    stage_db = Path(receipt["stage_db"])
    if not stage_db.exists():
        print(f"error: stage DB missing: {stage_db}", file=sys.stderr)
        return 1
    current_hash = sha256_file(stage_db)
    if receipt.get("stage_db_sha256") and current_hash != receipt["stage_db_sha256"]:
        print("error: stage DB hash mismatch vs receipt (stage changed)", file=sys.stderr)
        return 1

    installed = Path(args.installed).expanduser()
    installed.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if installed.exists():
        stamp = receipt.get("stamp") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = installed.with_name(f"mainframe-projects.pre-promote-{stamp}.sqlite")
        shutil.copy2(installed, backup)
        print(f"promote: backed up → {backup}")

    # Atomic-ish replace: copy to temp beside target then replace
    tmp_target = installed.with_suffix(installed.suffix + ".promoting")
    shutil.copy2(stage_db, tmp_target)
    os.replace(tmp_target, installed)

    manifest_path = Path(receipt["manifest"])
    if manifest_path.exists():
        expected = [
            p
            for p in load_manifest_projects(manifest_path)
            if (ROOT / "30_projects" / p).is_dir()
        ]
    else:
        expected = list((receipt.get("verify") or {}).get("doc_counts") or {})
    post = verify_stage(installed, expected)

    promote_receipt = {
        "schema_version": 1,
        "kind": "mindgraph-projects-promote",
        "as_of": utc_now(),
        "from_stage_receipt": str(receipt_path),
        "installed": str(installed),
        "installed_sha256": sha256_file(installed),
        "backup": str(backup) if backup else None,
        "verify": post,
        "green": bool(post.get("ok")),
        "adr": "ADR-045",
    }
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    out = RECEIPT_DIR / f"{receipt.get('stamp', 'promote')}-promote.json"
    out.write_text(json.dumps(promote_receipt, indent=2) + "\n", encoding="utf-8")
    print(f"promote receipt: {out.relative_to(ROOT)}")
    if not promote_receipt["green"]:
        print("promote: installed but verify failed — inspect backup", file=sys.stderr)
        return 1
    print("promote: OK")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    manifest = resolve_manifest(args)
    installed = Path(args.installed).expanduser()
    projects = load_manifest_projects(manifest)
    real = real_project_dirs(ROOT / "30_projects")
    cov = coverage_report(projects, real)
    expected = [p for p in projects if (ROOT / "30_projects" / p).is_dir()]
    verify = verify_stage(installed, expected) if installed.exists() else {
        "ok": False,
        "missing_namespaces": expected,
        "observed_count": 0,
        "expected_count": len(expected),
        "doc_counts": {},
        "extra_namespaces": [],
    }
    profile = json.loads(manifest.read_text(encoding="utf-8")).get("profile", "unknown")
    print("mindgraph-projects-apply status")
    print(f"  profile: {profile}")
    print(f"  manifest: {manifest}")
    print(f"  manifest_coverage_complete: {cov['complete']}")
    print(f"  installed_exists: {installed.exists()} size={installed.stat().st_size if installed.exists() else 0}")
    print(f"  installed_namespaces: {verify.get('observed_count')}/{verify.get('expected_count')}")
    if verify.get("missing_namespaces"):
        print(f"  missing_in_db: {verify['missing_namespaces']}")
    if verify.get("extra_namespaces"):
        print(f"  extra_in_db: {verify['extra_namespaces']}")
    print(f"  installed_green: {verify.get('ok')}")
    return 0 if cov["complete"] and verify.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Staged projects MindGraph apply (plan → stage → promote)."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="projects manifest JSON (default: lean mindgraph-projects.json)",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="use mindgraph-projects-deep.json (includes outputs/**)",
    )
    parser.add_argument(
        "--installed",
        default=str(DEFAULT_INSTALLED),
        help="installed projects DB path",
    )
    parser.add_argument("--full", action="store_true", help="pass --full to refresh wrapper")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="coverage + dry-run only")
    mode.add_argument("--stage", action="store_true", help="ingest into staging DB + receipt")
    mode.add_argument("--promote", action="store_true", help="promote green stage to installed")
    mode.add_argument("--status", action="store_true", help="compare installed DB to manifest")
    parser.add_argument(
        "--receipt",
        help="stage receipt path (required for --promote)",
    )
    parser.add_argument(
        "--allow-incomplete-coverage",
        action="store_true",
        help="allow stage when manifest ≠ disk (not recommended)",
    )
    args = parser.parse_args(argv)
    # If user passed both --deep and explicit default path, deep wins via resolve_manifest
    if args.deep and args.manifest == str(DEFAULT_MANIFEST):
        pass  # resolve_manifest uses DEEP_MANIFEST

    if args.plan:
        return cmd_plan(args)
    if args.stage:
        return cmd_stage(args)
    if args.promote:
        if not args.receipt:
            print("error: --promote requires --receipt", file=sys.stderr)
            return 2
        return cmd_promote(args)
    if args.status:
        return cmd_status(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
