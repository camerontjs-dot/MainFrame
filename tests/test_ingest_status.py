from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "bin" / "ingest-status"
LOADER = SourceFileLoader("ingest_status", str(SCRIPT_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC and SPEC.loader
ingest_status = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ingest_status
SPEC.loader.exec_module(ingest_status)


TODAY = date(2026, 6, 9)

MANIFEST_HEADER = (
    "batch_id,source,relative_path,size_bytes,sha256,created_at,modified_at,"
    "extension,embedded_dates,category,proposed_destination,review_status,"
    "duplicate_group\n"
)
LEDGER_HEADER = (
    "recorded_at,batch_id,relative_path,sha256,disposition,destination,"
    "evidence,notes\n"
)


def set_age(path: Path, days: int) -> None:
    stamp = datetime.combine(
        TODAY - timedelta(days=days), datetime.min.time()
    ).timestamp()
    os.utime(path, (stamp, stamp))


class IngestStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for lane in ("00_inbox", "01_ingest/ready", "01_ingest/queue",
                     "01_ingest/rejected"):
            (self.root / lane).mkdir(parents=True)
        self.batches = (
            self.root / "30_projects/second-brain-migration/raw-materials/batches"
        )
        self.batches.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_inbox(self, name: str, body: str, age_days: int) -> Path:
        path = self.root / "00_inbox" / name
        path.write_text(body, encoding="utf-8")
        set_age(path, age_days)
        return path

    def register_batch(self, batch_id: str, files: dict[str, Path],
                       ledger_rows: list[tuple[str, str]] | None = None) -> None:
        batch_dir = self.batches / batch_id
        batch_dir.mkdir()
        manifest_lines = [MANIFEST_HEADER]
        for name, path in files.items():
            digest = ingest_status.sha256_of(path)
            manifest_lines.append(
                f"{batch_id},test drop,{name},1,{digest},,,.md,,cat,dest,unreviewed,\n"
            )
        (batch_dir / "manifest.csv").write_text(
            "".join(manifest_lines), encoding="utf-8"
        )
        if ledger_rows is not None:
            ledger_lines = [LEDGER_HEADER]
            for name, disposition in ledger_rows:
                digest = (
                    ingest_status.sha256_of(files[name]) if name in files else ""
                )
                ledger_lines.append(
                    f"2026-06-06T12:00:00,{batch_id},{name},{digest},"
                    f"{disposition},,evidence,\n"
                )
            (batch_dir / "disposition-ledger.csv").write_text(
                "".join(ledger_lines), encoding="utf-8"
            )

    def test_lane_age_buckets_and_hidden_files(self) -> None:
        self.write_inbox("fresh.md", "fresh", age_days=2)
        self.write_inbox("aging.md", "aging", age_days=14)
        self.write_inbox("stale.md", "stale", age_days=90)
        hidden = self.write_inbox(".DS_Store", "junk", age_days=400)
        ready = self.root / "01_ingest/ready/note.md"
        ready.write_text("ready", encoding="utf-8")
        set_age(ready, 5)
        (self.root / "00_inbox" / "subdir").mkdir()

        status = ingest_status.build_status(self.root, today=TODAY)
        lanes = {lane["name"]: lane for lane in status["lanes"]}

        inbox = lanes["00_inbox"]
        self.assertEqual(inbox["files"], 3)  # hidden file skipped
        self.assertEqual(inbox["directories"], 1)
        self.assertEqual(inbox["age_days_0_7"], 1)
        self.assertEqual(inbox["age_days_8_30"], 1)
        self.assertEqual(inbox["age_days_31_plus"], 1)
        self.assertEqual(inbox["oldest_file_age_days"], 90)
        self.assertEqual(lanes["01_ingest/ready"]["files"], 1)
        self.assertEqual(lanes["01_ingest/queue"]["files"], 0)
        self.assertTrue(hidden.exists())

    def test_inbox_composition_splits_registered_from_organic(self) -> None:
        registered = self.write_inbox("migrated.md", "old note", age_days=60)
        self.write_inbox("organic.md", "fresh capture", age_days=1)
        self.register_batch(
            "2026-06-05-001",
            {"migrated.md": registered},
            ledger_rows=[("migrated.md", "unresolved")],
        )

        status = ingest_status.build_status(self.root, today=TODAY)
        composition = status["inbox_composition"]

        self.assertEqual(composition["batch_registered"], 1)
        self.assertEqual(composition["organic"], 1)
        self.assertEqual(composition["batches_matched"], ["2026-06-05-001"])
        self.assertEqual(
            composition["registered_by_disposition"],
            [{"name": "unresolved", "count": 1}],
        )

    def test_last_ledger_row_wins(self) -> None:
        kept = self.write_inbox("kept.md", "kept body", age_days=10)
        self.register_batch(
            "2026-06-05-001",
            {"kept.md": kept},
            ledger_rows=[
                ("kept.md", "unresolved"),
                ("kept.md", "retained"),
            ],
        )

        status = ingest_status.build_status(self.root, today=TODAY)
        composition = status["inbox_composition"]
        batch = status["batches"][0]

        self.assertEqual(
            composition["registered_by_disposition"],
            [{"name": "retained", "count": 1}],
        )
        self.assertEqual(
            batch["dispositions"], [{"name": "retained", "count": 1}]
        )
        self.assertEqual(batch["ledger_rows"], 2)

    def test_renamed_registered_file_matches_by_hash(self) -> None:
        original = self.write_inbox("original-name.md", "same bytes", age_days=30)
        self.register_batch(
            "2026-06-05-001",
            {"original-name.md": original},
            ledger_rows=[("original-name.md", "parked")],
        )
        original.rename(self.root / "00_inbox" / "renamed.md")
        set_age(self.root / "00_inbox" / "renamed.md", 30)

        status = ingest_status.build_status(self.root, today=TODAY)
        composition = status["inbox_composition"]

        self.assertEqual(composition["batch_registered"], 1)
        self.assertEqual(composition["organic"], 0)
        self.assertEqual(
            composition["registered_by_disposition"],
            [{"name": "parked", "count": 1}],
        )

    def test_batch_without_ledger_and_invalid_dir(self) -> None:
        registered = self.write_inbox("noledger.md", "body", age_days=5)
        self.register_batch("2026-06-05-001", {"noledger.md": registered})
        (self.batches / "stray-dir").mkdir()

        status = ingest_status.build_status(self.root, today=TODAY)
        composition = status["inbox_composition"]
        batch = status["batches"][0]

        self.assertFalse(batch["has_ledger"])
        self.assertEqual(batch["dispositions"], [])
        self.assertEqual(
            composition["registered_by_disposition"],
            [{"name": "unresolved", "count": 1}],
        )
        self.assertEqual(status["invalid_batch_dirs"], ["stray-dir"])

    def test_missing_batches_dir_means_all_organic(self) -> None:
        self.write_inbox("capture.md", "body", age_days=1)

        status = ingest_status.build_status(self.root, today=TODAY)
        composition = status["inbox_composition"]

        self.assertEqual(composition["batch_registered"], 0)
        self.assertEqual(composition["organic"], 1)
        self.assertEqual(status["batches"], [])


if __name__ == "__main__":
    unittest.main()
