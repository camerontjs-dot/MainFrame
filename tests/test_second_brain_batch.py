import csv
import hashlib
import importlib.util
import importlib.machinery
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "second-brain-batch"


class SecondBrainBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "bin").mkdir()
        register = (
            self.root
            / "30_projects"
            / "second-brain-migration"
            / "raw-materials"
            / "batch-register.md"
        )
        register.parent.mkdir(parents=True)
        register.write_text(
            "# Batch Register\n\n"
            "| Batch | Registered | Source | Files | Status | Manifest |\n"
            "|---|---|---|---:|---|---|\n",
            encoding="utf-8",
        )
        script_text = SCRIPT.read_text(encoding="utf-8").replace(
            "ROOT = Path(__file__).resolve().parents[1]",
            f"ROOT = Path({str(self.root)!r})",
        )
        self.script = self.root / "bin" / "second-brain-batch"
        self.script.write_text(script_text, encoding="utf-8")
        self.script.chmod(0o755)
        loader = importlib.machinery.SourceFileLoader(
            f"second_brain_batch_{id(self)}", str(self.script)
        )
        spec = importlib.util.spec_from_loader(
            f"second_brain_batch_{id(self)}", loader
        )
        assert spec and spec.loader
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_script(self, *args):
        return subprocess.run(
            [str(self.script), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(path.read_bytes())
        return digest.hexdigest()

    def test_registers_every_file_copies_snapshot_and_initializes_ledger(self):
        inbox = self.root / "drop"
        (inbox / "nested").mkdir(parents=True)
        (inbox / "cc-state.md").write_text(
            "Last Updated: 2026-04-01\n", encoding="utf-8"
        )
        (inbox / "copy.md").write_text("same\n", encoding="utf-8")
        (inbox / "nested" / "copy.md").write_text("same\n", encoding="utf-8")

        result = self.run_script(
            "--batch-id",
            "2026-06-05-001",
            "--source",
            str(inbox),
            "--source-label",
            "old-vault export",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        batch = (
            self.root
            / "30_projects"
            / "second-brain-migration"
            / "raw-materials"
            / "batches"
            / "2026-06-05-001"
        )
        with (batch / "manifest.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        with (batch / "disposition-ledger.csv").open(encoding="utf-8") as handle:
            ledger_rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(ledger_rows), 3)
        duplicate_rows = [row for row in rows if row["duplicate_group"]]
        self.assertEqual(len(duplicate_rows), 2)
        self.assertEqual(
            duplicate_rows[0]["duplicate_group"],
            duplicate_rows[1]["duplicate_group"],
        )
        self.assertEqual(rows[0]["review_status"], "unreviewed")
        self.assertTrue(
            (batch / "source-files" / "cc-state.md").exists(),
            "registered batch should preserve a recoverable source snapshot",
        )
        self.assertTrue(
            (batch / "source-files" / "nested" / "copy.md").exists(),
            "nested files should keep their relative paths inside the snapshot",
        )
        self.assertTrue(
            all(row["disposition"] == "unresolved" for row in ledger_rows),
            "registration should initialize every file with an unresolved ledger row",
        )
        self.assertEqual(
            ledger_rows[0]["evidence"],
            "raw-materials/batches/2026-06-05-001/manifest.csv",
        )

    def test_snapshot_recovers_original_bytes_after_source_changes(self):
        inbox = self.root / "drop"
        inbox.mkdir()
        source = inbox / "note.md"
        source.write_text("original\n", encoding="utf-8")

        result = self.run_script(
            "--batch-id",
            "2026-06-05-001",
            "--source",
            str(inbox),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        batch = (
            self.root
            / "30_projects"
            / "second-brain-migration"
            / "raw-materials"
            / "batches"
            / "2026-06-05-001"
        )
        snapshot = batch / "source-files" / "note.md"
        with (batch / "manifest.csv").open(encoding="utf-8") as handle:
            manifest_row = next(csv.DictReader(handle))

        source.write_text("changed later\n", encoding="utf-8")

        self.assertEqual(snapshot.read_text(encoding="utf-8"), "original\n")
        self.assertEqual(self.hash_file(snapshot), manifest_row["sha256"])
        self.assertNotEqual(self.hash_file(source), manifest_row["sha256"])

    def test_registration_does_not_mutate_source_files(self):
        inbox = self.root / "drop"
        inbox.mkdir()
        source = inbox / "note.md"
        original = "unchanged body\n"
        source.write_text(original, encoding="utf-8")

        result = self.run_script(
            "--batch-id",
            "2026-06-05-001",
            "--source",
            str(inbox),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(source.read_text(encoding="utf-8"), original)

    def test_ledger_append_keeps_prior_rows(self):
        inbox = self.root / "drop"
        inbox.mkdir()
        (inbox / "note.md").write_text("note\n", encoding="utf-8")

        batch = self.module.register_batch(
            "2026-06-05-001", inbox.resolve(), str(inbox.resolve())
        )
        ledger = batch / "disposition-ledger.csv"
        self.module.append_disposition_entries(
            ledger,
            [
                {
                    "recorded_at": "2026-06-06T12:00:00-04:00",
                    "batch_id": "2026-06-05-001",
                    "relative_path": "note.md",
                    "sha256": self.hash_file(batch / "source-files" / "note.md"),
                    "disposition": "promoted",
                    "destination": "10_knowledge/finance/example.md",
                    "evidence": "manual verification",
                    "notes": "test append",
                }
            ],
        )

        with ledger.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["disposition"], "unresolved")
        self.assertEqual(rows[1]["disposition"], "promoted")

    def test_refuses_to_overwrite_existing_batch(self):
        inbox = self.root / "drop"
        inbox.mkdir()
        (inbox / "note.md").write_text("note\n", encoding="utf-8")
        args = ("--batch-id", "2026-06-05-001", "--source", str(inbox))

        self.assertEqual(self.run_script(*args).returncode, 0)
        second = self.run_script(*args)

        self.assertNotEqual(second.returncode, 0)
        self.assertIn("already registered", second.stderr)

    def test_registered_batch_is_rejected_before_creating_output(self):
        inbox = self.root / "drop"
        inbox.mkdir()
        register = (
            self.root
            / "30_projects"
            / "second-brain-migration"
            / "raw-materials"
            / "batch-register.md"
        )
        register.write_text(
            register.read_text(encoding="utf-8")
            + "| `2026-06-05-001` | 2026-06-05 | `prior` | 1 | registered | `prior.csv` |\n",
            encoding="utf-8",
        )

        result = self.run_script(
            "--batch-id",
            "2026-06-05-001",
            "--source",
            str(inbox),
        )

        batch = (
            self.root
            / "30_projects"
            / "second-brain-migration"
            / "raw-materials"
            / "batches"
            / "2026-06-05-001"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already registered", result.stderr)
        self.assertFalse(batch.exists())

    def test_rejects_preexisting_batch_directory(self):
        inbox = self.root / "drop"
        inbox.mkdir()
        (inbox / "note.md").write_text("note\n", encoding="utf-8")
        batch = (
            self.root
            / "30_projects"
            / "second-brain-migration"
            / "raw-materials"
            / "batches"
            / "2026-06-05-001"
        )
        batch.mkdir(parents=True)

        result = self.run_script(
            "--batch-id",
            "2026-06-05-001",
            "--source",
            str(inbox),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)

    def test_rejects_batch_id_that_can_escape_batch_directory(self):
        inbox = self.root / "drop"
        inbox.mkdir()

        result = self.run_script(
            "--batch-id",
            "../../outside",
            "--source",
            str(inbox),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("YYYY-MM-DD-NNN", result.stderr)
        self.assertFalse((self.root / "outside").exists())


if __name__ == "__main__":
    unittest.main()
