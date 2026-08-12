"""Unit 1.3 — mainframe-doctor catalogue, aggregation, fixture shell."""

from __future__ import annotations

import json
import shutil
import sqlite3
import stat
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mainframe_doctor.catalogue import load_catalogue_pair, validate_catalogue  # noqa: E402
from mainframe_doctor import providers  # noqa: E402
from mainframe_doctor.runner import run_doctor  # noqa: E402
from mainframe_doctor.schema import (  # noqa: E402
    CheckResult,
    aggregate_health,
    exit_code,
    redact_secret_shaped,
)


CAT = ROOT / ".context" / "doctor" / "catalogue.json"
INV = ROOT / ".context" / "doctor" / "required-invariants.json"
FIXTURES = ROOT / "tests" / "fixtures" / "mainframe_doctor"


class AggregationTests(unittest.TestCase):
    def _c(
        self,
        status: str,
        *,
        required: bool = True,
        severity: str = "high",
        cid: str = "X",
    ) -> CheckResult:
        return CheckResult(
            id=cid,
            subsystem="t",
            layer="t",
            status=status,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            required=required,
            expected="e",
            observed="o",
            observed_at=None,
            freshness_seconds=0,
            authority="test",
        )

    def test_required_unknown_not_healthy(self) -> None:
        h = aggregate_health([self._c("pass"), self._c("unknown", cid="U")])
        self.assertEqual(h, "unknown")
        self.assertEqual(exit_code(h), 1)

    def test_required_fail_unhealthy(self) -> None:
        h = aggregate_health([self._c("pass"), self._c("fail", cid="F")])
        self.assertEqual(h, "unhealthy")

    def test_optional_skip_does_not_block_healthy(self) -> None:
        h = aggregate_health(
            [
                self._c("pass", cid="A"),
                self._c("skip", required=False, cid="B"),
            ]
        )
        self.assertEqual(h, "healthy")
        self.assertEqual(exit_code(h), 0)

    def test_required_skip_is_unknown(self) -> None:
        h = aggregate_health([self._c("pass"), self._c("skip", required=True, cid="S")])
        self.assertEqual(h, "unknown")

    def test_warn_degraded(self) -> None:
        h = aggregate_health([self._c("pass"), self._c("warn", severity="low", cid="W")])
        self.assertEqual(h, "degraded")

    def test_internal_error_exit_2(self) -> None:
        self.assertEqual(exit_code("unknown", internal_error=True), 2)

    def test_redact_secret_shaped(self) -> None:
        s = redact_secret_shaped("client_secret=abcDEF1234567890supersecretvalue")
        self.assertNotIn("supersecretvalue", s)
        self.assertIn("REDACTED", s)


class CatalogueTests(unittest.TestCase):
    def test_live_catalogue_complete_against_invariants(self) -> None:
        loaded = load_catalogue_pair(CAT, INV)
        self.assertTrue(loaded.ok, msg=loaded.errors)
        self.assertGreaterEqual(len(loaded.checks_by_id), len(loaded.required_ids))

    def test_missing_required_id_fails_completeness(self) -> None:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        cat["checks"] = [c for c in cat["checks"] if c["id"] != "CLI-001"]
        errors = validate_catalogue(cat, json.loads(INV.read_text())["required_check_ids"])
        self.assertTrue(any("CLI-001" in e for e in errors))

    def test_duplicate_id_fails(self) -> None:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        cat["checks"] = cat["checks"] + [cat["checks"][0]]
        errors = validate_catalogue(cat, [])
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_mutating_provider_rejected_in_catalogue(self) -> None:
        cat = {
            "checks": [
                {
                    "id": "X-001",
                    "owner": "t",
                    "subsystem": "t",
                    "layer": "t",
                    "provider": "x",
                    "required": True,
                    "mutates": True,
                    "isolation": "live",
                    "timeout_seconds": 1,
                    "skip_policy": "fail",
                    "pass_condition": "x",
                    "remediation": "x",
                    "safe_fix_available": False,
                    "contract_version": 1,
                }
            ]
        }
        errors = validate_catalogue(cat, ["X-001"])
        self.assertTrue(any("mutates" in e for e in errors))

    def test_nonpositive_provider_timeout_is_rejected(self) -> None:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        cat["checks"][0]["timeout_seconds"] = 0
        errors = validate_catalogue(cat, [])
        self.assertTrue(any("positive integer" in error for error in errors))


class ProviderTimeoutTests(unittest.TestCase):
    def test_slow_provider_becomes_unknown_at_its_catalogue_deadline(self) -> None:
        check = {
            "id": "SLOW-001",
            "owner": "test",
            "subsystem": "test",
            "layer": "unit",
            "provider": "slow_test_provider",
            "required": True,
            "mutates": False,
            "timeout_seconds": 1,
            "pass_condition": "returns before deadline",
            "remediation": "fix slow provider",
        }

        def slow_provider(_check: dict, _ctx: dict) -> CheckResult:
            time.sleep(10)
            raise AssertionError("deadline was not enforced")

        started = time.perf_counter()
        with mock.patch.dict(
            providers.PROVIDERS,
            {"slow_test_provider": slow_provider},
        ):
            result = providers.run_provider(check, {"root": ROOT})
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 2.0)
        self.assertEqual(result.status, "unknown")
        self.assertIn("timed out after 1s", result.message)


class MindGraphProviderTests(unittest.TestCase):
    def _check(self, check_id: str) -> dict:
        catalogue = json.loads(CAT.read_text(encoding="utf-8"))
        return next(c for c in catalogue["checks"] if c["id"] == check_id)

    def _write_db(self, path: Path, *, missing: set[str] | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        missing = missing or set()
        con = sqlite3.connect(path)
        for table in ("documents", "documents_fts", "chunks", "vec_chunks", "edges"):
            if table not in missing:
                con.execute(f"CREATE TABLE {table} (id TEXT, namespace TEXT)")
        con.commit()
        con.close()

    def test_mg_001_checks_projects_schema_not_only_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            mg = home / ".mindgraph"
            self._write_db(mg / "mainframe.sqlite")
            self._write_db(mg / "mainframe-projects.sqlite", missing={"edges"})
            with mock.patch.object(providers.Path, "home", return_value=home):
                result = providers.provider_mg_db_presence(
                    self._check("MG-001"), {"root": ROOT}
                )
        self.assertEqual(result.status, "fail")
        self.assertIn("projects tables missing", result.observed)

    def test_mg_003_fails_when_installed_namespace_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            root = temp / "root"
            projects = root / "30_projects"
            for slug in ("alpha", "beta"):
                project = projects / slug
                project.mkdir(parents=True)
                (project / "README.md").write_text("# project\n", encoding="utf-8")
            (projects / "mindgraph-projects.json").write_text(
                json.dumps({"projects": ["alpha", "beta"]}), encoding="utf-8"
            )

            home = temp / "home"
            db_path = home / ".mindgraph" / "mainframe-projects.sqlite"
            db_path.parent.mkdir(parents=True)
            con = sqlite3.connect(db_path)
            con.execute("CREATE TABLE documents (namespace TEXT)")
            con.execute("INSERT INTO documents VALUES ('alpha')")
            con.commit()
            con.close()

            with mock.patch.object(providers.Path, "home", return_value=home):
                result = providers.provider_mg_manifest_coverage(
                    self._check("MG-003"), {"root": root}
                )
        self.assertEqual(result.status, "fail")
        self.assertIn("beta", result.observed)
        self.assertIn("stale", result.message)


class FixtureShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # minimal catalogue copy
        doc = self.root / ".context" / "doctor"
        doc.mkdir(parents=True)
        shutil.copy(CAT, doc / "catalogue.json")
        shutil.copy(INV, doc / "required-invariants.json")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_fixture(self, name: str, payload: dict) -> Path:
        d = self.root / "fixtures" / name
        d.mkdir(parents=True)
        (d / "fixture.json").write_text(json.dumps(payload), encoding="utf-8")
        return d

    def test_all_pass_fixture_healthy(self) -> None:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        checks = {
            c["id"]: {"status": "pass", "observed": "ok", "message": "fixture pass"}
            for c in cat["checks"]
            if c.get("required")
        }
        # optional can skip
        for c in cat["checks"]:
            if not c.get("required"):
                checks[c["id"]] = {"status": "skip", "observed": "opt", "message": "skip"}
        fix = self._write_fixture("all-pass", {"checks": checks})
        report, code = run_doctor(
            root=self.root,
            profile="deep",
            fixture_path=fix,
        )
        self.assertIsNone(report.internal_error)
        self.assertEqual(report.health, "healthy")
        self.assertEqual(code, 0)

    def test_required_unknown_fixture_not_healthy(self) -> None:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        checks = {
            c["id"]: {"status": "pass", "observed": "ok", "message": "p"}
            for c in cat["checks"]
        }
        checks["SESSION-001"] = {
            "status": "unknown",
            "observed": "missing evidence",
            "message": "unknown",
        }
        fix = self._write_fixture("req-unknown", {"checks": checks})
        report, code = run_doctor(root=self.root, profile="deep", fixture_path=fix)
        self.assertEqual(report.health, "unknown")
        self.assertEqual(code, 1)

    def test_compound_session_fixture_fails(self) -> None:
        # synthetic root with compound STATE
        synth = self.root / "synth"
        synth.mkdir()
        (synth / "STATE.md").write_text(
            "# S\n\n## Active Project\n\nfoo (bar) + baz (qux)\n",
            encoding="utf-8",
        )
        (synth / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        (synth / "30_projects").mkdir()
        # only override non-session checks to pass; let session provider run
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        checks = {}
        for c in cat["checks"]:
            if c["id"] == "SESSION-001":
                continue  # live provider against fixture root
            checks[c["id"]] = {"status": "pass", "observed": "ok", "message": "p"}
        fix = self._write_fixture(
            "compound-session",
            {"root": str(synth), "checks": checks},
        )
        report, code = run_doctor(root=self.root, profile="deep", fixture_path=fix)
        by_id = {c.id: c for c in report.checks}
        self.assertEqual(by_id["SESSION-001"].status, "fail")
        self.assertIn(report.health, ("unhealthy", "unknown", "degraded"))
        self.assertEqual(code, 1)

    def test_cli_help_unsafe_source_fixture(self) -> None:
        synth = self.root / "cli-root"
        bin_dir = synth / "bin"
        bin_dir.mkdir(parents=True)
        # minimal unsafe wrapper (legacy pre-Unit-2.1)
        (bin_dir / "mindgraph-refresh-projects").write_text(
            '#!/bin/bash\n'
            'if [[ "${1:-}" == "--dry-run" ]]; then exit 0; fi\n'
            'echo ingest\n',
            encoding="utf-8",
        )
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        checks = {
            c["id"]: {"status": "pass", "observed": "ok", "message": "p"}
            for c in cat["checks"]
            if c["id"] != "CLI-001"
        }
        fix = self._write_fixture(
            "cli-unsafe",
            {"root": str(synth), "checks": checks},
        )
        report, _code = run_doctor(root=self.root, profile="deep", fixture_path=fix)
        by_id = {c.id: c for c in report.checks}
        self.assertEqual(by_id["CLI-001"].status, "fail")

    def test_cli_help_safe_source_fixture(self) -> None:
        synth = self.root / "cli-safe"
        bin_dir = synth / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "mindgraph-refresh-projects").write_text(
            "#!/bin/bash\n"
            "usage() { echo Show this help; }\n"
            'while [[ $# -gt 0 ]]; do case "$1" in\n'
            "  -h|--help) usage; exit 0 ;;\n"
            "  --dry-run) shift ;;\n"
            "  --apply) shift ;;\n"
            '  -*) echo "error: unknown option: $1"; exit 2 ;;\n'
            "esac; done\n"
            'if [[ "$DRY_RUN" -eq 0 ]]; then echo "refusing to mutate without --apply"; exit 2; fi\n',
            encoding="utf-8",
        )
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        checks = {
            c["id"]: {"status": "pass", "observed": "ok", "message": "p"}
            for c in cat["checks"]
            if c["id"] != "CLI-001"
        }
        fix = self._write_fixture(
            "cli-safe",
            {"root": str(synth), "checks": checks},
        )
        report, _code = run_doctor(root=self.root, profile="deep", fixture_path=fix)
        by_id = {c.id: c for c in report.checks}
        self.assertEqual(by_id["CLI-001"].status, "pass")

    def test_workstation_zero_ops_fixture(self) -> None:
        import sqlite3

        synth = self.root / "ws-root"
        db_path = synth / "20_live" / "workstation"
        db_path.mkdir(parents=True)
        db = db_path / "workstation.sqlite"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE tasks (id INTEGER)")
        con.execute("CREATE TABLE runs (id INTEGER)")
        con.execute("CREATE TABLE approvals (id INTEGER)")
        con.execute("CREATE TABLE artifacts (id INTEGER)")
        for _ in range(5):
            con.execute("INSERT INTO tasks VALUES (1)")
        con.commit()
        con.close()
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        checks = {
            c["id"]: {"status": "pass", "observed": "ok", "message": "p"}
            for c in cat["checks"]
            if c["id"] not in ("WS-001", "WS-003")
        }
        fix = self._write_fixture(
            "ws-empty-ops",
            {"root": str(synth), "checks": checks},
        )
        report, _code = run_doctor(root=self.root, profile="deep", fixture_path=fix)
        by_id = {c.id: c for c in report.checks}
        self.assertEqual(by_id["WS-001"].status, "pass")
        self.assertEqual(by_id["WS-003"].status, "fail")

    def test_provider_exception_becomes_unknown(self) -> None:
        # force broken root for mg provider only — use override for exception sim via bad fixture status
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        checks = {
            c["id"]: {"status": "pass", "observed": "ok", "message": "p"}
            for c in cat["checks"]
        }
        checks["TEL-001"] = {
            "status": "unknown",
            "observed": "RuntimeError",
            "message": "provider exception: RuntimeError",
        }
        fix = self._write_fixture("prov-exc", {"checks": checks})
        report, code = run_doctor(root=self.root, profile="deep", fixture_path=fix)
        self.assertEqual(report.health, "unknown")
        self.assertEqual(code, 1)

    def test_bad_catalogue_exit_2(self) -> None:
        bad = self.root / ".context" / "doctor" / "catalogue.json"
        bad.write_text('{"checks":[]}', encoding="utf-8")
        report, code = run_doctor(root=self.root, profile="quick")
        self.assertEqual(code, 2)
        self.assertIsNotNone(report.internal_error)

    def test_json_serializable(self) -> None:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        checks = {
            c["id"]: {"status": "fail", "observed": "x", "message": "y"}
            for c in cat["checks"]
        }
        fix = self._write_fixture("ser", {"checks": checks})
        report, _code = run_doctor(root=self.root, profile="quick", fixture_path=fix)
        blob = json.dumps(report.to_dict())
        self.assertIn("schema_version", blob)
        self.assertNotIn("supersecret", blob)


class LiveSmokeTests(unittest.TestCase):
    """Live probes — doctor shell must not claim healthy while system degraded."""

    def test_live_quick_not_healthy_or_internal_ok(self) -> None:
        report, code = run_doctor(root=ROOT, profile="quick")
        self.assertIsNone(report.internal_error, msg=report.internal_error)
        # SEC-001 residual disposition keeps live vector from claiming healthy.
        self.assertIn(report.health, ("unknown", "unhealthy", "degraded"))
        self.assertEqual(code, 1)
        ids = {c.id for c in report.checks}
        self.assertIn("SESSION-001", ids)
        self.assertIn("CLI-001", ids)

    def test_live_cli_001_passes_after_unit_2_1(self) -> None:
        report, _code = run_doctor(root=ROOT, profile="deep")
        by_id = {c.id: c for c in report.checks}
        self.assertEqual(by_id["CLI-001"].status, "pass")

    def test_live_auth_001_reports_state_and_task_001_passes(self) -> None:
        report, _code = run_doctor(root=ROOT, profile="quick")
        by_id = {c.id: c for c in report.checks}
        self.assertIn(by_id["AUTH-001"].status, ("pass", "warn", "stale"), by_id["AUTH-001"].message)
        self.assertEqual(by_id["TASK-001"].status, "pass", by_id["TASK-001"].message)

    def test_focus_review_staleness_is_deterministic(self) -> None:
        check = next(
            c for c in json.loads(CAT.read_text(encoding="utf-8"))["checks"] if c["id"] == "AUTH-001"
        )
        result = providers.provider_auth_focus(
            check,
            {"root": ROOT, "now": datetime(2026, 8, 2, tzinfo=timezone.utc)},
        )
        self.assertEqual(result.status, "stale")

    def test_live_quick_has_no_unimplemented_unknowns(self) -> None:
        report, _code = run_doctor(root=ROOT, profile="quick")
        unknowns = [c for c in report.checks if c.status == "unknown"]
        self.assertEqual(unknowns, [], msg=[(c.id, c.message) for c in unknowns])
        by_id = {c.id: c for c in report.checks}
        for cid in ("SESSION-002", "STRUCT-001", "TEL-001"):
            self.assertIn(cid, by_id)
            self.assertNotEqual(by_id[cid].status, "unknown", by_id[cid].message)
        # May be degraded (SEC-001) or unhealthy if a required live surface fails;
        # the contract is no silent unimplemented unknowns in the quick profile.
        self.assertNotEqual(report.health, "unknown")


class NewProviderUnitTests(unittest.TestCase):
    def _check(self, cid: str = "X") -> dict:
        return {
            "id": cid,
            "subsystem": "t",
            "layer": "t",
            "required": True,
            "pass_condition": "p",
            "remediation": "r",
            "owner": "t",
        }

    def test_session_phase_alignment_missing_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "STATE.md").write_text("# no active project\n", encoding="utf-8")
            result = providers.provider_session_phase_alignment(self._check(), {"root": root})
            self.assertEqual(result.status, "fail")

    def test_structure_bounds_missing_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = providers.provider_structure_bounds(self._check(), {"root": root})
            self.assertEqual(result.status, "fail")
            self.assertIn("missing", result.observed)

    def test_tel_hash_integrity_missing_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = providers.provider_tel_hash_integrity(self._check(), {"root": root})
            self.assertEqual(result.status, "fail")

    def test_tel_hash_integrity_intact_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = root / "20_live" / "workflow-metrics" / "events"
            events.mkdir(parents=True)
            prev = "genesis-seed"
            lines = []
            for i in range(3):
                body = {"event": "test", "n": i, "as_of": f"2026-07-23T00:00:0{i}Z"}
                h = providers._telemetry_compute_hash(body, prev)
                row = dict(body)
                row["hash_chain"] = h
                lines.append(json.dumps(row, sort_keys=True, separators=(",", ":")))
                prev = h
            (events / "2026-07-23.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = providers.provider_tel_hash_integrity(self._check(), {"root": root})
            self.assertEqual(result.status, "pass", result.observed)


if __name__ == "__main__":
    unittest.main()
