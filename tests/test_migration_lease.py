from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from migration_lease import (  # noqa: E402
    LeaseBusy,
    LeaseUnavailable,
    MigrationLease,
    exclusive_migration_lease,
    shared_writer_lease,
)


class MigrationLeaseTests(unittest.TestCase):
    def test_exclusive_lease_fences_shared_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            with exclusive_migration_lease(root, state_root=state):
                writer = shared_writer_lease(root, "old-path-writer", state_root=state)
                with self.assertRaises(LeaseBusy):
                    writer.acquire()
                self.assertFalse((root / "30_projects" / "mainframe-process-eval").exists())

    def test_stale_state_is_recovered_under_the_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (state / "lease-state.json").write_text(
                json.dumps(
                    {
                        "mode": "exclusive",
                        "owner_pid": 999999999,
                        "epoch": "stale",
                    }
                ),
                encoding="utf-8",
            )
            lease = MigrationLease(root, "shared", "recovery-test", state_root=state)
            lease.acquire()
            try:
                current = json.loads((state / "lease-state.json").read_text(encoding="utf-8"))
                self.assertTrue(current["recovered_stale_state"])
                event = lease.record_write(root / "receipt.json", action="test")
                self.assertEqual(event["holder"], "recovery-test")
            finally:
                lease.release()

    def test_writer_must_hold_lease_to_record_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lease = shared_writer_lease(root, "writer", state_root=root / "state")
            with self.assertRaises(Exception):
                lease.record_write(root / "old-path", action="write")

    def test_concurrent_shared_holders_have_distinct_audit_records(self) -> None:
        worker = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from migration_lease import shared_writer_lease
root = Path(sys.argv[1]); state = Path(sys.argv[3])
with shared_writer_lease(root, sys.argv[4], state_root=state) as lease:
    print(lease.epoch, flush=True)
    sys.stdin.read()
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "scripts")
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", worker, str(root), str(ROOT / "scripts"), str(state), f"holder-{i}"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                )
                for i in range(2)
            ]
            epochs = [process.stdout.readline().strip() for process in processes]
            self.assertEqual(len(set(epochs)), 2)
            holders = list((state / "holders").glob("*.json"))
            self.assertEqual(len(holders), 2)
            summary = json.loads((state / "lease-state.json").read_text(encoding="utf-8"))
            self.assertEqual(len(summary["active_holders"]), 2)
            for process in processes:
                process.stdin.write("release\n")
                process.stdin.close()
                process.wait(timeout=10)
            self.assertFalse(list((state / "holders").glob("*.json")))

    def test_corrupt_or_failed_audit_metadata_does_not_leak_lock_fd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (state / "lease-state.json").write_text("{not-json", encoding="utf-8")
            lease = MigrationLease(root, "shared", "corrupt", state_root=state)
            with self.assertRaises(LeaseUnavailable):
                lease.acquire()
            self.assertIsNone(lease._lock_handle)
            (state / "lease-state.json").unlink()
            with mock.patch("migration_lease._write_state", side_effect=OSError("disk full")):
                failing = MigrationLease(root, "shared", "write-failure", state_root=state)
                with self.assertRaises(LeaseUnavailable):
                    failing.acquire()
                self.assertIsNone(failing._lock_handle)
            with shared_writer_lease(root, "after-failure", state_root=state):
                self.assertTrue((state / "lease-state.json").exists())


if __name__ == "__main__":
    unittest.main()
