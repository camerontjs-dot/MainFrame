"""Pytest conftest hook for MainFrame Brain sensory afference."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def pytest_sessionfinish(session, exitstatus):
    """Notify MainFrame Brain of test completion.
    Executes in <1ms directly in Python; completely fails open so it never breaks tests.
    """
    if os.environ.get("MAINFRAME_BRAIN_NO_HOOK") == "1":
        return

    try:
        root = Path(__file__).resolve().parents[1]
        brain_path = str(root / "30_projects/mainframe-brain")
        if brain_path not in sys.path:
            sys.path.insert(0, brain_path)
        from engine import storage
        total = getattr(session, "testscollected", 0)
        status_label = "passed" if exitstatus == 0 else f"failed (exit code {exitstatus})"
        summary = f"Test suite {status_label}: {total} tests collected"
        storage.add_event(source="test", summary=summary)
    except Exception:
        pass
