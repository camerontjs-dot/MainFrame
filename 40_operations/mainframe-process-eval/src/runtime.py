"""MPE-owned convenience wrappers over MainFrame lifecycle substrate."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from lifecycle_identity import LifecycleRecord
from lifecycle_runtime import lifecycle_writer, resolve_lifecycle
from migration_lease import MigrationLease

SLUG = "mainframe-process-eval"


def resolve_mpe(root: Path | str) -> LifecycleRecord:
    return resolve_lifecycle(root, SLUG, expected_record_type=None)


def mpe_path(root: Path | str, *parts: str) -> Path:
    return resolve_mpe(root).path.joinpath(*parts)


@contextmanager
def mpe_writer(
    root: Path | str,
    holder: str,
    *,
    pause_token: str | None = None,
    state_root: Path | str | None = None,
) -> Iterator[tuple[LifecycleRecord, MigrationLease]]:
    with lifecycle_writer(
        root,
        SLUG,
        holder,
        pause_token=pause_token,
        state_root=state_root,
    ) as result:
        yield result
