"""Atomic validated JSON ledger and rebuildable native timetrace projections."""

import fcntl
import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from codex_time.accounting import segments
from codex_time.models import Ledger, QuotaObservation


class Digest(Protocol):
    def update(self, value: bytes, /) -> None: ...
    def copy(self) -> "Digest": ...
    def hexdigest(self) -> str: ...


def quota_key(q: QuotaObservation) -> tuple[object, ...]:
    return (q.at, q.limit_id, q.plan_type, q.bucket, q.window_minutes, q.resets_at,
            q.used_percent, q.provenance)


class StoreError(RuntimeError):
    pass


def key(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def atomic_json(path: Path, value: object, staging: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Stage beside the destination directory, never inside the Git data store.
    stage = staging
    stage.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="write-", dir=stage)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(value, output, indent=2, sort_keys=True, ensure_ascii=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def state_root(data_root: Path) -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    return base / "codex-time" / key(str(data_root.resolve()))


class Store:
    def __init__(self, root: Path, runtime: Path | None = None) -> None:
        self.root = root.expanduser().resolve()
        self.runtime = (runtime or state_root(self.root)).expanduser().resolve()
        if self.runtime == self.root or self.root in self.runtime.parents:
            raise StoreError("runtime directory must be outside the committable data root")
        self.staging = self.root.parent / (".codex-time-stage-" + key(str(self.root)))
        self._locked = False
        self._projection: dict[str, tuple[str, set[Path]]] = {}
        self._projects: set[str] = set()
        self._ledger_json: str | None = None
        self._disk_hash: str | None = None
        self._file_hashes: dict[Path, tuple[tuple[int, ...], Digest]] = {}
        self._quota_keys: set[tuple[object, ...]] = set()
        self._embedded_quotas: list[QuotaObservation] = []
        self._quota_source: list[QuotaObservation] | None = None
        self._quota_offset = 0

    @staticmethod
    def _stat_key(path: Path) -> tuple[int, ...]:
        stat = path.stat()
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)

    def _digest(self, path: Path) -> Digest | None:
        try:
            stamp = self._stat_key(path)
        except FileNotFoundError:
            self._file_hashes.pop(path, None)
            return None
        cached = self._file_hashes.get(path)
        if cached is not None and cached[0] == stamp:
            return cached[1]
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                digest.update(block)
        self._file_hashes[path] = (stamp, digest)
        return digest

    def _write(self, path: Path, value: object) -> None:
        staging = self.runtime / ".staging" if path.is_relative_to(self.runtime) else self.staging
        atomic_json(path, value, staging)

    def fingerprint(self) -> str | None:
        ledger = self._digest(self.root / "ledger.json")
        journal = self._digest(self.root / "quota-observations.jsonl")
        if journal is None:
            return ledger.hexdigest() if ledger is not None else None
        identity = (ledger.hexdigest() if ledger is not None else "-") + ":" + journal.hexdigest()
        return hashlib.sha256(identity.encode()).hexdigest()

    @contextmanager
    def writer(self) -> Iterator[None]:
        # All callers for one data root share the canonical lock, even with overrides.
        lock_root = Path.home() / ".local/state/codex-time/locks" / key(str(self.root))
        lock_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (lock_root / "writer.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise StoreError(
                    "another writer owns this data directory; stop the daemon first"
                ) from exc
            self._locked = True
            try:
                yield
            finally:
                self._locked = False
                fcntl.flock(lock, fcntl.LOCK_UN)

    def load(self) -> Ledger:
        path = self.root / "ledger.json"
        try:
            ledger = Ledger.model_validate_json(path.read_text()) if path.exists() else Ledger()
            if any(
                sid != s.id or any(tid != t.id for tid, t in s.turns.items())
                for sid, s in ledger.sessions.items()
            ):
                raise ValueError("identifier/key mismatch")
        except (OSError, ValueError, ValidationError) as exc:
            raise StoreError("invalid ledger.json; restore a valid backup before writing") from exc
        embedded = {quota_key(q): q for q in ledger.quota_observations}
        ledger.quota_observations = list(embedded.values())
        self._embedded_quotas = ledger.quota_observations.copy()
        journal = self.root / "quota-observations.jsonl"
        known = set(embedded)
        journal_keys: set[tuple[object, ...]] = set()
        _line_number = 0
        try:
            if journal.exists():
                with journal.open("rb") as source:
                    for _line_number, line in enumerate(source, 1):
                        if not line.endswith(b"\n"):
                            raise ValueError("partial final line")
                        q = QuotaObservation.model_validate_json(line)
                        identity = quota_key(q)
                        journal_keys.add(identity)
                        if identity not in known:
                            ledger.quota_observations.append(q)
                            known.add(identity)
        except (OSError, ValueError, ValidationError) as exc:
            raise StoreError(
                f"invalid quota-observations.jsonl at line {_line_number}; "
                "restore a valid backup before writing"
            ) from exc
        self._quota_keys = journal_keys
        self._quota_source = None
        self._quota_offset = 0
        self._disk_hash = self.fingerprint()
        return ledger

    def _append_quotas(self, observations: list[QuotaObservation]) -> None:
        """Append validated new evidence; never rewrite or truncate existing history."""
        pending: list[QuotaObservation] = []
        added: set[tuple[object, ...]] = set()
        for q in observations:
            identity = quota_key(q)
            if identity not in self._quota_keys and identity not in added:
                pending.append(q)
                added.add(identity)
        if not pending:
            return
        path = self.root / "quota-observations.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        current = self._digest(path)
        digest = current.copy() if current is not None else hashlib.sha256()
        with path.open("ab") as out:
            for q in pending:
                line = (q.model_dump_json() + "\n").encode()
                out.write(line)
                digest.update(line)
            out.flush()
            os.fsync(out.fileno())
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self._file_hashes[path] = (self._stat_key(path), digest)
        self._quota_keys.update(added)

    def save(self, ledger: Ledger) -> None:
        if not self._locked:
            raise StoreError("writer lock required")
        # Refuse to overwrite corrupt pre-existing durable data.
        current_hash = self.fingerprint()
        if self._disk_hash is None or current_hash != self._disk_hash:
            self.load()
            self._ledger_json = None
        # Migrate already durable embedded evidence before removing it from ledger.json.
        self._append_quotas(self._embedded_quotas)
        self._embedded_quotas = []
        payload = ledger.model_dump(mode="json", exclude={"quota_observations"})
        rendered = json.dumps(payload, sort_keys=True)
        if rendered != self._ledger_json:
            self._write(self.root / "ledger.json", payload)
            self._ledger_json = rendered
        # Ingestion appends to this list. Replacements/reloads get a full exact dedup pass.
        offset = self._quota_offset if self._quota_source is ledger.quota_observations else 0
        if offset > len(ledger.quota_observations):
            offset = 0
        self._append_quotas(ledger.quota_observations[offset:])
        self._quota_source = ledger.quota_observations
        self._quota_offset = len(ledger.quota_observations)
        self._disk_hash = self.fingerprint()
        self.project(ledger)

    def project(self, ledger: Ledger) -> None:
        """Recover native projection deterministically; remove only owned record names."""
        if not self._locked:
            raise StoreError("writer lock required")
        expected: set[Path] = set()
        zone = ZoneInfo("America/Toronto")
        for session in ledger.sessions.values():
            signature = session.model_dump_json(exclude={"title", "updated", "archived"})
            cached = self._projection.get(session.id)
            if cached and cached[0] == signature:
                expected.update(cached[1])
                continue
            owned: set[Path] = set()
            if not (session.is_child or session.parent_id):
                for span in segments(list(session.turns.values())):
                    project = key(span.cwd)
                    if project not in self._projects:
                        self._write(
                            self.root / "projects" / f"{project}.json",
                            {"key": project, "name": span.cwd},
                        )
                        self._projects.add(project)
                    cursor = span.start
                    while cursor < span.end:
                        local = cursor.astimezone(zone)
                        midnight = datetime.combine(local.date() + timedelta(days=1), time(), zone)
                        end = min(midnight.astimezone(UTC), span.end)
                        identity = json.dumps(
                            [
                                session.id,
                                span.turn_ids,
                                span.cwd,
                                cursor.isoformat(),
                                end.isoformat(),
                            ]
                        )
                        path = (
                            self.root
                            / "records"
                            / local.date().isoformat()
                            / (f"codex-time-{key(identity)}.json")
                        )
                        owned.add(path)
                        self._write(
                            path,
                            {
                                "start": local.isoformat(),
                                "end": end.astimezone(zone).isoformat(),
                                "project": {"key": project},
                                "is_billable": False,
                                "tags": [
                                    f"session:{session.id}",
                                    *[f"turn:{t}" for t in span.turn_ids],
                                ],
                            },
                        )
                        cursor = end
            expected.update(owned)
            self._projection[session.id] = (signature, owned)
        for path in (self.root / "records").glob("*/codex-time-*.json"):
            if path not in expected:
                path.unlink()
        for sid in set(self._projection) - set(ledger.sessions):
            del self._projection[sid]

    def runtime_read(self) -> dict[str, object]:
        path = self.runtime / "checkpoint.json"
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text())
            if not isinstance(value, dict):
                return {}
            return {str(k): v for k, v in value.items()}
        except (OSError, ValueError):
            return {}  # Cache is disposable; ledger + source history rebuild it.

    def runtime_save(self, value: dict[str, object]) -> None:
        if not self._locked:
            raise StoreError("writer lock required")
        self._write(self.runtime / "checkpoint.json", value)
