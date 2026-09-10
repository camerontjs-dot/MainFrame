"""Exercise real context files, bounded delivery and disconnected CLI behavior."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("session_open_routes", str(ROOT / "bin/session-open"))
spec = importlib.util.spec_from_loader(loader.name, loader)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


@pytest.fixture
def workspace(tmp_path):
    files = {
        "AGENTS.md": "# Rules\nPreserve local work.\n",
        "HARNESS.md": "# Harness\n\n## Session orientation\nArrival rules.\n\n## Execution\nFull action rules.\n",
        "STATE.md": "# State\n\n## Active Project\nexample\n",
        ".context/workflows/session-open.md": "# Read the routed context completely.\n",
        ".context/workflows/project-resume-and-candidate-lifecycle.md": "# Reconstruct source and Git.\n",
        "30_projects/AGENTS.md": "# Project lifecycle rules\n",
        "30_projects/example/README.md": "# Example\n",
        "30_projects/example/plans/01-older.md": '---\ntitle: "Brainstorming"\nstatus: active\n---\nOld unrelated plan.\n',
        "30_projects/example/plans/99-onboarding.md": '---\ntitle: "Onboarding"\nstatus: active\n---\nCurrent relevant plan.\n',
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return tmp_path


def content_for(result, root, path):
    return "".join(mod.read_batch(result, root, b["id"])["content"]
                   for b in result.read_batches if b["path"] == path)


def test_arrival_does_not_enter_recorded_project_or_require_its_contracts(workspace):
    (workspace / "30_projects/AGENTS.md").unlink()
    result = mod.build_context(workspace)
    assert result.ok
    assert result.intent == "arrival"
    assert result.project is None
    assert not any(e.path.startswith("30_projects/") for e in result.entries)
    assert "Arrival rules." in content_for(result, workspace, "HARNESS.md")
    assert "Full action rules." not in content_for(result, workspace, "HARNESS.md")
    assert result.context_status == "unread"


def test_named_resume_retains_full_contracts_and_nominates_task_plan(workspace):
    result = mod.build_context(workspace, project="example", task="pick up onboarding work")
    assert result.ok
    assert result.intent == "resume"
    assert "Full action rules." in content_for(result, workspace, "HARNESS.md")
    assert result.plan.endswith("99-onboarding.md")
    assert result.plan_status == "task_match_candidate"
    assert any(e.path == "30_projects/AGENTS.md" and e.required for e in result.entries)


def test_tied_or_missing_task_match_does_not_choose_alphabetical_plan(workspace):
    plans = workspace / "30_projects/example/plans"
    (plans / "98-onboarding.md").write_text('---\ntitle: "Onboarding two"\nstatus: active\n---\n')
    for task in (None, "onboarding", "unmatched request"):
        result = mod.build_context(workspace, project="example", task=task)
        assert result.ok
        assert result.plan is None
        assert len(result.plan_candidates) == 3
    explicit = mod.build_context(workspace, project="example", plan="30_projects/example/plans/98-onboarding.md")
    assert explicit.plan_status == "explicit"
    assert next(e for e in explicit.entries if e.path == explicit.plan).required


def test_invalid_and_escaping_plan_paths_remain_incomplete(workspace, tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("Outside plan\n")
    link = workspace / "30_projects/example/plans/link.md"
    link.symlink_to(outside)
    for plan in ("outside.md", "30_projects/example/plans/missing.md", str(link)):
        result = mod.build_context(workspace, project="example", plan=plan)
        assert not result.ok
        assert result.context_status == "incomplete"
        assert result.plan_error


def test_arrival_rejects_project_arguments_and_resume_needs_a_project(workspace):
    result = mod.build_context(workspace, project="example", intent="arrival")
    assert not result.ok and result.intent_error
    (workspace / "STATE.md").write_text("# No focus\n")
    result = mod.build_context(workspace, intent="resume")
    assert not result.ok and result.project_error


def test_plan_directory_cannot_redirect_to_another_project(workspace):
    plans = workspace / "30_projects/example/plans"
    other = workspace / "30_projects/other/plans"
    other.parent.mkdir()
    plans.rename(other)
    plans.symlink_to(other, target_is_directory=True)
    result = mod.build_context(workspace, project="example", task="onboarding")
    assert not result.ok
    assert result.plan_error
    assert result.plan_candidates == []


def test_missing_workflow_and_binary_contract_are_explicit(workspace):
    (workspace / ".context/workflows/session-open.md").unlink()
    (workspace / "AGENTS.md").write_bytes(b"\xff\xfe")
    result = mod.build_context(workspace)
    assert not result.ok
    assert result.context_status == "incomplete"
    assert ".context/workflows/session-open.md" in result.missing_required
    assert any("AGENTS.md" in error for error in result.read_errors)


@pytest.mark.parametrize("content", ["Read this complete rule.\n" * 1500, "\U0001f331\u754c" * 5000])
def test_content_batches_are_lossless_bounded_and_utf8_safe(workspace, content):
    (workspace / "AGENTS.md").write_text(content)
    result = mod.build_context(workspace)
    assert result.ok
    assert content_for(result, workspace, "AGENTS.md") == content
    assert all(0 < b["bytes"] <= mod.BATCH_BYTES for b in result.read_batches)
    assert len([b for b in result.read_batches if b["path"] == "AGENTS.md"]) > 1


def test_changed_source_is_rejected_after_a_batch_manifest(workspace):
    result = mod.build_context(workspace)
    (workspace / "AGENTS.md").write_text("Changed rules\n")
    with pytest.raises(ValueError, match="source changed"):
        mod.read_batch(result, workspace, 1)


def test_latest_coordination_is_bounded_without_losing_current_entry(workspace):
    log = workspace / "30_projects/example/log.md"
    log.write_text("# Log\n\n## Today\nCurrent authority.\n" + "A long current entry.\n" * 900 + "\n## Yesterday\nHistorical detail.\n")
    result = mod.build_context(workspace, project="example")
    delivered = content_for(result, workspace, "30_projects/example/log.md")
    assert "Current authority." in delivered
    assert delivered.count("A long current entry.") == 900
    assert "Historical detail." not in delivered


def test_real_cli_survives_missing_scheduler_and_serves_one_batch(workspace):
    for relative in (
        "bin/session-open",
        "scripts/focus_authority.py",
        "scripts/lifecycle_identity.py",
    ):
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    (workspace / "AGENTS.md").write_text("Long rule.\n" * 2000)
    command = [sys.executable, str(workspace / "bin/session-open")]
    listing = subprocess.run(command + ["--json"], cwd=workspace, capture_output=True, text=True)
    assert listing.returncode == 0, listing.stderr
    payload = json.loads(listing.stdout)
    assert payload["eval_schedule_ok"] is None
    assert "unavailable" in payload["eval_schedule_summary"]
    assert payload["reading_verified"] is False
    assert payload["context_status"] == "unread"
    batch = subprocess.run(command + ["--read-batch", "1", "--json"], cwd=workspace, capture_output=True, text=True)
    assert batch.returncode == 0, batch.stderr
    delivered = json.loads(batch.stdout)
    assert len(delivered["batch"]["content"].encode()) <= mod.BATCH_BYTES
    assert "read_batches" not in delivered
    wrong_hash = subprocess.run(command + ["--read-batch", "1", "--expect-hash", "wrong", "--json"], cwd=workspace, capture_output=True, text=True)
    assert wrong_hash.returncode == 1
    assert json.loads(wrong_hash.stdout)["context_status"] == "incomplete"
    invalid = subprocess.run(command + ["--read-batch", "0", "--json"], cwd=workspace, capture_output=True, text=True)
    assert invalid.returncode == 1
    printed = subprocess.run(command + ["--print-contents"], cwd=workspace, capture_output=True, text=True)
    assert printed.returncode == 0
    assert "Only batch 1 printed" in printed.stdout
    assert printed.stdout.count("Long rule.") < 2000
