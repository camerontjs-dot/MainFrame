"""Generic lifecycle substrate must not import MPE internals."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
GENERIC = (
    "lifecycle_identity.py",
    "lifecycle_runtime.py",
    "migration_lease.py",
    "work_inventory.py",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


class LifecycleSubstrateIsolationTests(unittest.TestCase):
    def test_generic_modules_do_not_import_mpe_engine(self) -> None:
        banned = {
            "runtime",
            "process_eval",
            "migration",
            "writer_smoke",
            "mpe_runtime",
            "mpe_migration",
        }
        for name in GENERIC:
            imported = _imports(SCRIPTS / name)
            overlap = imported & banned
            self.assertFalse(overlap, f"{name} imports {overlap}")

    def test_generic_modules_do_not_hardcode_operation_src(self) -> None:
        needle = "40_operations/mainframe-process-eval/src"
        for name in GENERIC:
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertNotIn(needle, text, name)

    def test_lifecycle_identity_has_no_mpe_helper(self) -> None:
        text = (SCRIPTS / "lifecycle_identity.py").read_text(encoding="utf-8")
        self.assertNotIn("def resolve_mpe", text)
