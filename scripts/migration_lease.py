"""External migration epoch/lease used by lifecycle writers.

The lock and state live under ``20_live/system-health`` (or an injected shadow
root), never under either lifecycle root.  Supported writers acquire a shared
lease immediately before resolving a path and hold it until their write is
complete.  The migration runner acquires an exclusive lease, so a writer that
resolved the old path earlier cannot recreate it after the rename.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LeaseError(RuntimeError):
    """Base class for lease failures."""


class LeaseBusy(LeaseError):
    """A compatible writer or migration lease is currently held."""


class LeaseUnavailable(LeaseError):
    """The lease could not be established safely."""


PAUSE_STATE_FILENAME = "writer-pause.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_state_root(mainframe_root: Path | str) -> Path:
    override = os.environ.get("MAINFRAME_MIGRATION_STATE_ROOT")
    if override:
        candidate = Path(override).expanduser()
        if not candidate.is_absolute():
            candidate = Path(mainframe_root).expanduser().resolve() / candidate
        return candidate.resolve()
    return Path(mainframe_root).expanduser().resolve() / "20_live" / "system-health" / "mpe-migration"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise LeaseUnavailable(f"lease state unreadable: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LeaseUnavailable("lease state must be a JSON object")
    return payload


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _remove_durable(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    _fsync_directory(path.parent)


@contextmanager
def _audit_guard(state_root: Path):
    """Serialize the audit projection without weakening the migration lock."""

    path = state_root / "audit.lock"
    handle = path.open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


@dataclass
class MigrationLease:
    mainframe_root: Path
    mode: str
    holder: str
    state_root: Path | None = None
    nonblocking: bool = True
    pause_token: str | None = None
    pause_scope: str | None = None
    _lock_handle: Any = None
    _epoch: str | None = None
    _state_path: Path | None = None
    _holder_path: Path | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"shared", "exclusive"}:
            raise ValueError("lease mode must be shared or exclusive")
        self.mainframe_root = Path(self.mainframe_root).expanduser().resolve()
        self.state_root = (self.state_root or default_state_root(self.mainframe_root)).expanduser().resolve()

    @property
    def epoch(self) -> str:
        if not self._epoch:
            raise LeaseError("lease has not been acquired")
        return self._epoch

    @property
    def lock_path(self) -> Path:
        assert self.state_root is not None
        return self.state_root / "migration.lock"

    @property
    def state_path(self) -> Path:
        assert self.state_root is not None
        return self.state_root / "lease-state.json"

    @property
    def holders_dir(self) -> Path:
        assert self.state_root is not None
        return self.state_root / "holders"

    @property
    def audit_lock_path(self) -> Path:
        assert self.state_root is not None
        return self.state_root / "audit.lock"

    @property
    def writes_path(self) -> Path:
        assert self.state_root is not None
        return self.state_root / "write-events.jsonl"

    @property
    def pause_state_path(self) -> Path:
        assert self.state_root is not None
        return self.state_root / PAUSE_STATE_FILENAME

    def _check_writer_pause(self) -> None:
        """Fail closed while a migration has paused normal writers.

        The migration runner uses an exclusive lease and is therefore allowed
        to create or advance the pause state.  Shared lifecycle writers must
        present the exact one-shot token while the state is paused; a missing,
        malformed, or unknown state never becomes an accidental allow.
        """

        if self.mode != "shared":
            return
        pause = read_writer_pause_state(self.state_root)
        if not pause:
            return
        status = pause.get("status")
        scope = pause.get("slug")
        if self.pause_scope and scope and scope != self.pause_scope:
            return
        if status == "resume-permitted":
            return
        if status != "paused":
            raise LeaseUnavailable(f"writer pause state has unsupported status: {status!r}")
        expected = pause.get("pause_token")
        if not isinstance(expected, str) or not expected:
            raise LeaseUnavailable("paused writer state has no valid pause token")
        if self.pause_token != expected:
            raise LeaseBusy("normal lifecycle writers are persistently paused by an active migration")

    def acquire(self) -> "MigrationLease":
        assert self.state_root is not None
        self.state_root.mkdir(parents=True, exist_ok=True)
        self._state_path = self.state_path
        self._lock_handle = self.lock_path.open("a+")
        operation = fcntl.LOCK_SH if self.mode == "shared" else fcntl.LOCK_EX
        if self.nonblocking:
            operation |= fcntl.LOCK_NB
        try:
            fcntl.flock(self._lock_handle.fileno(), operation)
        except BlockingIOError as exc:
            self._lock_handle.close()
            self._lock_handle = None
            raise LeaseBusy(f"migration lease busy: {self.mode}") from exc
        except OSError as exc:
            self._lock_handle.close()
            self._lock_handle = None
            raise LeaseUnavailable(f"cannot acquire migration lease: {exc}") from exc

        try:
            self._check_writer_pause()
            self._epoch = str(uuid.uuid4())
            self.holders_dir.mkdir(parents=True, exist_ok=True)
            with _audit_guard(self.state_root):
                prior = _read_json(self.state_path)
                stale_state = bool(prior and not _pid_alive(prior.get("owner_pid")))
                # Holder files are the concurrent truth.  The summary JSON is
                # an auditable projection, never the lock authority.
                active: list[dict[str, Any]] = []
                for holder_path in sorted(self.holders_dir.glob("*.json")):
                    holder_payload = _read_json(holder_path)
                    if not _pid_alive(holder_payload.get("owner_pid")):
                        _remove_durable(holder_path)
                        continue
                    active.append(holder_payload)
                self._holder_path = self.holders_dir / f"{self._epoch}.json"
                holder = {
                    "schema_version": 2,
                    "mode": self.mode,
                    "holder": self.holder,
                    "owner_pid": os.getpid(),
                    "epoch": self._epoch,
                    "started_at": utc_now(),
                }
                _write_state(self._holder_path, holder)
                active.append(holder)
                summary = {
                    "schema_version": 2,
                    "mode": self.mode,
                    "holder": self.holder,
                    "owner_pid": os.getpid(),
                    "epoch": self._epoch,
                    "started_at": holder["started_at"],
                    "recovered_stale_state": stale_state,
                    "active_holders": sorted(active, key=lambda item: str(item.get("epoch"))),
                }
                _write_state(self.state_path, summary)
        except LeaseError:
            self._release_fd_only()
            raise
        except Exception as exc:  # noqa: BLE001
            # Metadata failures must never leak an acquired migration fd.
            self._cleanup_holder_best_effort()
            self._release_fd_only()
            raise LeaseUnavailable(f"cannot record migration lease safely: {type(exc).__name__}: {exc}") from exc
        return self

    def _cleanup_holder_best_effort(self) -> None:
        if self._holder_path is None:
            return
        try:
            with _audit_guard(self.state_root):
                _remove_durable(self._holder_path)
        except Exception:
            pass
        self._holder_path = None

    def _release_fd_only(self) -> None:
        if self._lock_handle is None:
            return
        try:
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._lock_handle.close()
            self._lock_handle = None
            self._state_path = None
            self._epoch = None

    def release(self) -> None:
        if self._lock_handle is None:
            return
        audit_error: Exception | None = None
        try:
            try:
                with _audit_guard(self.state_root):
                    _remove_durable(self._holder_path) if self._holder_path else None
                    state = _read_json(self.state_path)
                    active = [
                        item for item in state.get("active_holders", [])
                        if item.get("epoch") != self._epoch
                    ]
                    state.update({
                        "mode": "released" if not active else "shared",
                        "released_at": utc_now(),
                        "active_holders": active,
                    })
                    _write_state(self.state_path, state)
            except Exception as exc:  # noqa: BLE001
                audit_error = exc
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._lock_handle.close()
            self._lock_handle = None
            self._state_path = None
            self._holder_path = None
            self._epoch = None
        if audit_error is not None:
            raise LeaseUnavailable(f"cannot finalize migration lease audit: {type(audit_error).__name__}: {audit_error}") from audit_error

    def record_write(self, path: Path | str, *, action: str) -> dict[str, Any]:
        if self._lock_handle is None:
            raise LeaseError("cannot record a write without an acquired lease")
        target = Path(path).expanduser()
        try:
            relative = target.resolve().relative_to(self.mainframe_root)
            displayed = relative.as_posix()
        except ValueError:
            displayed = str(target)
        event = {
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "epoch": self.epoch,
            "holder": self.holder,
            "pid": os.getpid(),
            "at": utc_now(),
            "action": action,
            "path": displayed,
            "lease_mode": self.mode,
        }
        self.writes_path.parent.mkdir(parents=True, exist_ok=True)
        with self.writes_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def __enter__(self) -> "MigrationLease":
        return self.acquire()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.release()


def shared_writer_lease(
    mainframe_root: Path | str,
    holder: str,
    *,
    state_root: Path | str | None = None,
    pause_token: str | None = None,
    pause_scope: str | None = None,
) -> MigrationLease:
    return MigrationLease(
        Path(mainframe_root),
        "shared",
        holder,
        Path(state_root) if state_root is not None else None,
        pause_token=pause_token,
        pause_scope=pause_scope,
    )


def exclusive_migration_lease(
    mainframe_root: Path | str,
    holder: str = "mpe-migration-runner",
    *,
    state_root: Path | str | None = None,
) -> MigrationLease:
    return MigrationLease(
        Path(mainframe_root),
        "exclusive",
        holder,
        Path(state_root) if state_root is not None else None,
    )


def state_hash(state_root: Path | str) -> str | None:
    path = Path(state_root).expanduser().resolve() / "lease-state.json"
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_writer_pause_state(state_root: Path | str) -> dict[str, Any]:
    """Read the durable writer pause projection.

    A missing file means no migration pause is active.  Any other read or JSON
    failure raises ``LeaseUnavailable`` so consumers cannot silently resume
    during an unreadable intermediate state.
    """

    path = Path(state_root).expanduser().resolve() / PAUSE_STATE_FILENAME
    return _read_json(path)


def pause_state_hash(state_root: Path | str) -> str | None:
    path = Path(state_root).expanduser().resolve() / PAUSE_STATE_FILENAME
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()
