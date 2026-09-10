"""Generic lease-aware lifecycle writers.

Readers resolve a slug from direct lifecycle authority at use time. Writers
acquire the shared migration lease before resolving and hold it until the
filesystem write is complete. This module is MainFrame-owned substrate: it
must not import process-evaluation internals.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from lifecycle_identity import LifecycleRecord, resolve_record
from migration_lease import MigrationLease, shared_writer_lease


def resolve_lifecycle(
    root: Path | str,
    slug: str,
    *,
    expected_record_type: str | None = None,
) -> LifecycleRecord:
    return resolve_record(root, slug, expected_record_type=expected_record_type)


@contextmanager
def lifecycle_writer(
    root: Path | str,
    slug: str,
    holder: str,
    *,
    expected_record_type: str | None = None,
    pause_token: str | None = None,
    state_root: Path | str | None = None,
) -> Iterator[tuple[LifecycleRecord, MigrationLease]]:
    """Acquire the writer fence before resolving a lifecycle path."""

    root_path = Path(root).expanduser().resolve()
    with shared_writer_lease(
        root_path,
        holder,
        state_root=state_root,
        pause_token=pause_token,
        pause_scope=slug,
    ) as lease:
        record = resolve_lifecycle(
            root_path,
            slug,
            expected_record_type=expected_record_type,
        )
        yield record, lease
