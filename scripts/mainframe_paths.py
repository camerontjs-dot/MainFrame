"""Path display helpers shared by bin/ tools.

## Why this module exists

`Path.relative_to` raises `ValueError` on any path outside the repo. Three tools
have now shipped that crash independently:

    2026-08-11  bin/capture-validate   crashed on any path outside the tree, and
                                       exited 1 — which was also its "found
                                       errors" code, so a crash was
                                       indistinguishable from a result
    2026-08-23  bin/contract-lint      same crash, linting a file by absolute
                                       path from outside the repo
    2026-08-23  bin/doctor-remediate   same crash, writing a receipt whose
                                       snapshot directory was a temp dir

`bin/papercut harvest`'s rule is that one papercut is noise and the same
papercut three times is a defect with an address. This is the address. A fourth
private `try/except ValueError` would have been the wrong fix.

Import from a bin/ script the way the repo already does it::

    sys.path.insert(0, str(ROOT))
    from scripts.mainframe_paths import rel_to_root
"""

from __future__ import annotations

from pathlib import Path


def rel_to_root(path: Path | str, root: Path) -> str:
    """Repo-relative when possible, absolute otherwise. Never raises.

    Display only. Do not use the result to reopen the file — an absolute return
    value means the path was outside `root`, and re-joining it to `root` would
    silently point somewhere else.
    """
    p = Path(path)
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except (ValueError, OSError):
        return str(p)
