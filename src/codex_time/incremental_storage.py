"""Bounded daemon state over portable per-session JSON and evidence journals.

SQLite is a disposable exact index, never the backup source of truth. Durable
session snapshots precede rollout checkpoint commits. Migration publishes its
layout marker last, leaving the old ledger readable after an interruption.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
from collections import OrderedDict
from collections.abc import Iterator, MutableMapping
from datetime import datetime
from pathlib import Path
from time import monotonic
from types import TracebackType
from typing import TYPE_CHECKING, cast

import ijson  # type: ignore[import-untyped]

from codex_time.models import Ledger, QuotaObservation, Session, UsageObservation
from codex_time.storage import Store, StoreError, key

if TYPE_CHECKING:
    from codex_time.ingest import FileState

LAYOUT_VERSION = 1


def layout(root: Path) -> dict[str, object] | None:
    path = root / "layout.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_bytes())
        if not isinstance(value, dict) or value.get("version") != LAYOUT_VERSION:
            raise ValueError("unsupported version")
        if not isinstance(value.get("revision"), str):
            raise ValueError("missing revision")
        diagnostics = value.get("diagnostics", [])
        if not isinstance(diagnostics, list) or any(
            not isinstance(item, str) for item in diagnostics
        ):
            raise ValueError("invalid diagnostics")
        return cast(dict[str, object], value)
    except (OSError, ValueError) as exc:
        raise StoreError("invalid layout.json; restore a valid backup before writing") from exc


def session_path(root: Path, sid: str) -> Path:
    return root / "sessions" / f"{key(sid)}.json"


def read_session(path: Path, sid: str | None = None) -> Session:
    try:
        session = Session.model_validate_json(path.read_bytes())
        if (
            (sid is not None and session.id != sid)
            or any(tid != turn.id for tid, turn in session.turns.items())
            or path.name != f"{key(session.id)}.json"
        ):
            raise ValueError("identifier/key mismatch")
        return session
    except (OSError, ValueError) as exc:
        raise StoreError(f"invalid session snapshot {path.name}; restore a valid backup") from exc


def load_timing(root: Path, *, include_evidence: bool = True) -> Ledger:
    meta = layout(root)
    if meta is None:
        raise StoreError("partitioned layout missing")
    ledger = Ledger(diagnostics=meta.get("diagnostics", []))
    for path in sorted((root / "sessions").glob("*.json")):
        session = read_session(path)
        ledger.sessions[session.id] = session
    if not include_evidence:
        return ledger
    for name, model, _destination in (
        ("legacy-quota-observations.jsonl", QuotaObservation, ledger.quota_observations),
        ("legacy-usage-observations.jsonl", UsageObservation, ledger.usage_observations),
    ):
        path = root / name
        if path.exists():
            try:
                with path.open("rb") as source:
                    for raw in source:
                        if not raw.endswith(b"\n"):
                            raise ValueError("partial final line")
                        observation = model.model_validate_json(raw)
                        if isinstance(observation, QuotaObservation):
                            ledger.quota_observations.append(observation)
                        else:
                            ledger.usage_observations.append(observation)
            except ValueError as exc:
                raise StoreError(f"invalid {name}; restore a valid backup") from exc
    return ledger


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


class Sessions(MutableMapping[str, Session]):
    def __init__(self, owner: IndexedStore, capacity: int) -> None:
        self.owner = owner
        self.capacity = max(1, capacity)
        self.cache: OrderedDict[str, tuple[Session, str | None]] = OrderedDict()
        self.stamps: dict[str, tuple[int, ...] | None] = {}
        self.touched: set[str] = set()

    def __getitem__(self, sid: str) -> Session:
        if sid in self.cache:
            self.touched.add(sid)
            self.cache.move_to_end(sid)
            return self.cache[sid][0]
        if self.owner.db.execute("SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone() is None:
            raise KeyError(sid)
        session = read_session(session_path(self.owner.root, sid), sid)
        self._insert(sid, session, session.model_dump_json())
        return session

    def _insert(self, sid: str, session: Session, signature: str | None) -> None:
        if len(self.cache) >= self.capacity and sid not in self.cache:
            old = next(iter(self.cache))
            self.flush_one(old)
            del self.cache[old]
            self.stamps.pop(old, None)
        if sid not in self.cache:
            path = session_path(self.owner.root, sid)
            self.stamps[sid] = Store._stat_key(path) if path.exists() else None
        self.cache[sid] = (session, signature)
        self.touched.add(sid)

    def __setitem__(self, sid: str, value: Session) -> None:
        if sid != value.id:
            raise StoreError("session identifier/key mismatch")
        self.owner.db.execute("INSERT OR IGNORE INTO sessions(id) VALUES (?)", (sid,))
        previous = self.cache.get(sid)
        self._insert(sid, value, previous[1] if previous else None)

    def __delitem__(self, sid: str) -> None:
        raise StoreError("historical session deletion is not supported")

    def __iter__(self) -> Iterator[str]:
        for row in self.owner.db.execute("SELECT id FROM sessions ORDER BY id"):
            yield str(row[0])

    def __len__(self) -> int:
        return int(self.owner.db.execute("SELECT count(*) FROM sessions").fetchone()[0])

    def __contains__(self, sid: object) -> bool:
        return isinstance(sid, str) and (
            sid in self.cache
            or self.owner.db.execute("SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone()
            is not None
        )

    def flush_one(self, sid: str) -> None:
        if sid not in self.touched:
            return
        session, old = self.cache[sid]
        path = session_path(self.owner.root, sid)
        current = Store._stat_key(path) if path.exists() else None
        if current != self.stamps[sid]:
            raise StoreError("session changed outside this writer; restart after restore")
        signature = session.model_dump_json()
        if old != signature:
            self.owner._save_session(session, old)
            self.cache[sid] = (session, signature)
            self.stamps[sid] = Store._stat_key(path)
        self.touched.discard(sid)

    def flush(self) -> None:
        for sid in list(self.touched):
            self.flush_one(sid)


class IndexedStore:
    def __init__(self, root: Path, runtime: Path, cache_size: int = 8) -> None:
        self.store = Store(root, runtime)
        self.root, self.runtime = self.store.root, self.store.runtime
        self.cache_size = cache_size
        self.changed = False
        self.db: sqlite3.Connection
        self.ledger: Ledger
        self.sessions: Sessions
        self._progress_at = 0.0
        self._writes = 0
        self._recovered_index = False
        self.timings = {"persistence_seconds": 0.0, "projection_seconds": 0.0, "index_seconds": 0.0}

    @property
    def cached_sessions(self) -> int:
        return len(self.sessions.cache)

    def progress(self, message: str) -> None:
        now = monotonic()
        if now - self._progress_at >= 2:
            print(
                ("" if os.environ.get("CLI_PLAIN") == "1" else "⏳ ") + message,
                file=sys.stderr,
                flush=True,
            )
            self._progress_at = now

    def __enter__(self) -> IndexedStore:
        self._writer = self.store.writer()
        self._writer.__enter__()
        try:
            self.runtime.mkdir(parents=True, exist_ok=True)
            if layout(self.root) is None:
                self._migrate()
            self.db = sqlite3.connect(self.runtime / "index.sqlite")
            self.db.execute("PRAGMA cache_size=-4096")
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, stamp TEXT);
                CREATE TABLE IF NOT EXISTS quotas (id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS usage (
                    id TEXT PRIMARY KEY, sid TEXT, at TEXT, body TEXT, cumulative INTEGER);
                CREATE INDEX IF NOT EXISTS usage_session ON usage(sid,at);
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY, body TEXT, pending INTEGER);
                CREATE INDEX IF NOT EXISTS checkpoint_session
                    ON checkpoints(json_extract(body,'$.session_id'));
                CREATE TABLE IF NOT EXISTS records (sid TEXT, path TEXT PRIMARY KEY);
                CREATE INDEX IF NOT EXISTS records_session ON records(sid);
                CREATE TABLE IF NOT EXISTS rows (id TEXT PRIMARY KEY, signature TEXT);
                CREATE TABLE IF NOT EXISTS titles (id TEXT PRIMARY KEY, title TEXT);
            """)
            if "stamp" not in {row[1] for row in self.db.execute("PRAGMA table_info(sessions)")}:
                self.db.execute("ALTER TABLE sessions ADD COLUMN stamp TEXT")
                self.db.execute("DELETE FROM meta WHERE key='sources'")
            saved = self.db.execute("SELECT value FROM meta WHERE key='sources'").fetchone()
            if saved is None or saved[0] != self._stamp():
                self._rebuild()
            self.sessions = Sessions(self, self.cache_size)
            meta = layout(self.root) or {}
            # Only daemon internals see a mutable disk mapping; public/report ledgers
            # continue to be validated, materialized Pydantic models.
            self.ledger = Ledger.model_construct(
                sessions=cast(dict[str, Session], self.sessions),
                diagnostics=cast(list[str], meta.get("diagnostics", [])),
                quota_observations=[],
                usage_observations=[],
            )
            self._diagnostics = list(self.ledger.diagnostics)
            self._source_stamp = self._stamp()
            # Verify individual snapshot stat identities once at restart, including
            # isolated restores that do not change the layout revision.
            restored_snapshot = False
            for sid, stamp in self.db.execute("SELECT id,stamp FROM sessions"):
                path = session_path(self.root, str(sid))
                actual = json.dumps(Store._stat_key(path)) if path.exists() else None
                if actual != stamp:
                    session = read_session(path, str(sid))
                    self._project_session(session)
                    self.db.execute("UPDATE sessions SET stamp=? WHERE id=?", (actual, sid))
                    self.db.execute(
                        "DELETE FROM checkpoints WHERE json_extract(body,'$.session_id')=?", (sid,)
                    )
                    restored_snapshot = True
                    self.changed = True
                self.progress("Checking session snapshots after restart")
            if restored_snapshot:
                # Signatures describe previously applied evidence, not restored
                # snapshots. Replay bounded metadata pages while retaining exact
                # explicit names and their independent append cursor.
                self.db.execute("DELETE FROM rows")
                _cursors, names = self.metadata_read()
                self.metadata_put({}, names)
            for pending in (self.runtime / "pending-projections").glob("*.json"):
                sid = json.loads(pending.read_bytes())["session_id"]
                session = read_session(session_path(self.root, sid), sid)
                self.db.execute("INSERT OR IGNORE INTO sessions(id) VALUES (?)", (sid,))
                self._project_session(session)
                self.changed = True
            self.flush()
            return self
        except BaseException as exc:
            if hasattr(self, "db"):
                self.db.close()
            self._writer.__exit__(*sys.exc_info())
            if (
                isinstance(exc, sqlite3.DatabaseError)
                and not self._recovered_index
                and getattr(exc, "sqlite_errorcode", None)
                in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB)
            ):
                self._recovered_index = True
                identity = uuid.uuid4().hex
                for suffix in ("", "-wal", "-shm"):
                    original = self.runtime / ("index.sqlite" + suffix)
                    if original.exists():
                        original.rename(
                            self.runtime / ("index-corrupt-" + identity + ".sqlite" + suffix)
                        )
                self.progress(
                    "Disposable index corrupt; preserving it and rebuilding from portable evidence"
                )
                return self.__enter__()
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                self.flush()
        finally:
            self.db.close()
            self._writer.__exit__(exc_type, exc, traceback)

    def _stamp(self) -> str:
        values: list[tuple[object, ...]] = []
        for name in (
            "layout.json",
            "ledger.json",
            "quota-observations.jsonl",
            "usage-observations.jsonl",
            "legacy-quota-observations.jsonl",
            "legacy-usage-observations.jsonl",
            "sessions",
        ):
            path = self.root / name
            try:
                s = path.stat()
                values.append((name, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns))
            except FileNotFoundError:
                values.append((name, None))
        return json.dumps(values)

    def _backup(self) -> None:
        target = self.root / "migration-backup-v1"
        target.mkdir(parents=True, exist_ok=True)
        manifest: dict[str, str] = {}
        for name in ("ledger.json", "quota-observations.jsonl", "usage-observations.jsonl"):
            source = self.root / name
            if not source.exists():
                continue
            self.progress(f"Verifying pre-migration backup: {name}")
            digest = sha256(source)
            destination = target / name
            if not destination.exists():
                temporary = target / (name + ".partial")
                shutil.copyfile(source, temporary)
                with temporary.open("rb") as backup:
                    os.fsync(backup.fileno())
                os.replace(temporary, destination)
            if sha256(destination) != digest:
                raise StoreError("migration backup differs from source; preserve and inspect both")
            manifest[name] = digest
        self.store._write(target / "manifest.json", manifest)

    def verify_backup(self) -> bool:
        target = self.root / "migration-backup-v1"
        try:
            manifest = json.loads((target / "manifest.json").read_bytes())
            return isinstance(manifest, dict) and all(
                isinstance(name, str) and sha256(target / name) == digest
                for name, digest in manifest.items()
            )
        except (OSError, ValueError):
            return False

    def _migrate_session(self, session: Session) -> None:
        self.store._write(session_path(self.root, session.id), session.model_dump(mode="json"))

    def _migrate(self) -> None:
        self._backup()
        legacy = self.root / "ledger.json"
        diagnostics: list[str] = []
        if legacy.exists():
            try:
                with legacy.open("rb") as source:
                    version = next(ijson.items(source, "version"), None)
                    if version not in (1, 2, 3, 4):
                        raise ValueError("unsupported legacy version")
                with legacy.open("rb") as source:
                    for sid, raw in ijson.kvitems(source, "sessions", use_float=True):
                        session = Session.model_validate(raw)
                        if session.id != sid or any(
                            tid != t.id for tid, t in session.turns.items()
                        ):
                            raise ValueError("identifier/key mismatch")
                        self._migrate_session(session)
                        self.progress("Migrating timing sessions; original ledger retained")
                with legacy.open("rb") as source:
                    diagnostics = list(ijson.items(source, "diagnostics.item"))[-200:]
                # Publish separate legacy evidence files, leaving original journals
                # and their verified backups unchanged across interrupted retries.
                for field, model, name in (
                    ("quota_observations", QuotaObservation, "legacy-quota-observations.jsonl"),
                    ("usage_observations", UsageObservation, "legacy-usage-observations.jsonl"),
                ):
                    self.store.staging.mkdir(parents=True, exist_ok=True)
                    fd, temporary = tempfile.mkstemp(dir=self.store.staging)
                    try:
                        with os.fdopen(fd, "wb") as output, legacy.open("rb") as source:
                            for raw in ijson.items(source, field + ".item", use_float=True):
                                observation = model.model_validate(raw)
                                output.write((observation.model_dump_json() + "\n").encode())
                            output.flush()
                            os.fsync(output.fileno())
                        os.replace(temporary, self.root / name)
                    finally:
                        if os.path.exists(temporary):
                            os.unlink(temporary)
            except (ValueError, ijson.JSONError) as exc:
                raise StoreError("invalid legacy ledger; migration not published") from exc
        self.store._write(
            self.root / "layout.json",
            {
                "version": LAYOUT_VERSION,
                "revision": uuid.uuid4().hex,
                "diagnostics": diagnostics,
                "legacy_ledger": "ledger.json",
            },
        )

    def _rebuild(self) -> None:
        for table in ("sessions", "quotas", "usage", "checkpoints", "records", "rows", "titles"):
            self.db.execute(f"DELETE FROM {table}")
        self.db.execute("DELETE FROM meta WHERE key IN ('metadata','contexts_cursor')")
        for path in (self.root / "sessions").glob("*.json"):
            session = read_session(path)
            self.db.execute(
                "INSERT INTO sessions VALUES (?,?)", (session.id, json.dumps(Store._stat_key(path)))
            )
            self.progress("Rebuilding disposable session index")
        for name, model in (
            ("quota-observations.jsonl", QuotaObservation),
            ("usage-observations.jsonl", UsageObservation),
            ("legacy-quota-observations.jsonl", QuotaObservation),
            ("legacy-usage-observations.jsonl", UsageObservation),
        ):
            path = self.root / name
            if not path.exists():
                continue
            try:
                with path.open("rb") as source:
                    for number, raw in enumerate(source, 1):
                        if not raw.endswith(b"\n"):
                            raise ValueError("partial final line")
                        observation = model.model_validate_json(raw)
                        if isinstance(observation, UsageObservation):
                            self._index_usage(observation)
                        else:
                            self.db.execute(
                                "INSERT OR IGNORE INTO quotas VALUES (?)",
                                (observation.model_dump_json(),),
                            )
                        if number % 2000 == 0:
                            self.progress(f"Rebuilding {name}: {number:,} observations")
            except ValueError as exc:
                raise StoreError(f"invalid {name}; restore a valid backup before writing") from exc
        # A one-time native ownership inventory supports affected-session cleanup.
        for path in (self.root / "records").glob("*/codex-time-*.json"):
            try:
                record = json.loads(path.read_bytes())
                for tag in record.get("tags", []):
                    if isinstance(tag, str) and tag.startswith("session:"):
                        self.db.execute(
                            "INSERT OR REPLACE INTO records VALUES (?,?)",
                            (tag[8:], str(path.relative_to(self.root))),
                        )
                        break
            except (OSError, ValueError, AttributeError):
                continue  # disposable projection; affected sessions rebuild it
        for (sid,) in self.db.execute("SELECT id FROM sessions"):
            self._project_session(read_session(session_path(self.root, str(sid)), str(sid)))
            self.progress("Reconciling native projections after index rebuild")
        self.db.execute("INSERT OR REPLACE INTO meta VALUES ('sources',?)", (self._stamp(),))
        self.db.commit()

    def _index_usage(self, observation: UsageObservation) -> None:
        body = observation.model_dump_json()
        previous = self.db.execute(
            "SELECT body FROM usage WHERE id=?", (observation.id,)
        ).fetchone()
        if previous is not None:
            if previous[0] != body:
                raise StoreError("conflicting usage observation identity; refusing to overwrite")
            return
        self.db.execute(
            "INSERT INTO usage VALUES (?,?,?,?,?)",
            (
                observation.id,
                observation.session_id,
                observation.at.isoformat(),
                body,
                int(observation.cumulative is not None),
            ),
        )

    @staticmethod
    def _append_line(path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as output:
            output.write((body + "\n").encode())
            output.flush()
            os.fsync(output.fileno())
        descriptor = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def has_usage(self, identity: str) -> bool:
        return self.db.execute("SELECT 1 FROM usage WHERE id=?", (identity,)).fetchone() is not None

    def previous_usage(self, sid: str, at: datetime) -> UsageObservation | None:
        row = self.db.execute(
            "SELECT body FROM usage WHERE sid=? AND at<? AND cumulative=1 ORDER BY at DESC LIMIT 1",
            (sid, at.isoformat()),
        ).fetchone()
        return UsageObservation.model_validate_json(row[0]) if row else None

    def has_later_usage(self, sid: str, at: datetime) -> bool:
        return (
            self.db.execute(
                "SELECT 1 FROM usage WHERE sid=? AND at>? LIMIT 1", (sid, at.isoformat())
            ).fetchone()
            is not None
        )

    def append_usage(self, observation: UsageObservation) -> None:
        if self.has_usage(observation.id):
            self._index_usage(observation)  # validate conflicts, including retries
            return
        self._append_line(self.root / "usage-observations.jsonl", observation.model_dump_json())
        self._index_usage(observation)
        self.changed = True
        self._source_stamp = self._stamp()

    def append_quota(self, observation: QuotaObservation) -> None:
        body = observation.model_dump_json()
        if self.db.execute("SELECT 1 FROM quotas WHERE id=?", (body,)).fetchone():
            return
        self._append_line(self.root / "quota-observations.jsonl", body)
        self.db.execute("INSERT INTO quotas VALUES (?)", (body,))
        self.changed = True
        self._source_stamp = self._stamp()

    def checkpoint_get(self, identity: str) -> FileState | None:
        from codex_time.ingest import FileState

        row = self.db.execute("SELECT body FROM checkpoints WHERE id=?", (identity,)).fetchone()
        return FileState.model_validate_json(row[0]) if row else None

    def checkpoint_put(self, identity: str, state: FileState) -> None:
        body = state.model_dump_json()
        prior = self.db.execute("SELECT body FROM checkpoints WHERE id=?", (identity,)).fetchone()
        if prior is None or prior[0] != body:
            self.db.execute(
                "INSERT OR REPLACE INTO checkpoints VALUES (?,?,?)",
                (identity, body, int(bool(state.contexts))),
            )

    def checkpoint_keys(self) -> Iterator[str]:
        for row in self.db.execute("SELECT id FROM checkpoints"):
            yield str(row[0])

    def checkpoint_pending_keys(self) -> Iterator[str]:
        for row in self.db.execute("SELECT id FROM checkpoints WHERE pending=1"):
            yield str(row[0])

    def context_batch(self, active_ids: list[str], limit: int = 128) -> list[str]:
        saved = self.db.execute("SELECT value FROM meta WHERE key='contexts_cursor'").fetchone()
        cursor = str(saved[0]) if saved else ""
        page = [
            str(row[0])
            for row in self.db.execute(
                "SELECT id FROM checkpoints WHERE pending=1 AND id>? ORDER BY id LIMIT ?",
                (cursor, limit),
            )
        ]
        next_cursor = page[-1] if len(page) == limit else ""
        if saved is None or next_cursor != cursor:
            self.db.execute(
                "INSERT OR REPLACE INTO meta VALUES ('contexts_cursor',?)", (next_cursor,)
            )
        keys = set(page)
        for sid in active_ids:
            keys.update(
                str(row[0])
                for row in self.db.execute(
                    "SELECT id FROM checkpoints WHERE pending=1 "
                    "AND json_extract(body,'$.session_id')=? LIMIT ?",
                    (sid, limit),
                )
            )
        return sorted(keys)

    def current_sources(self, session_ids: list[str]) -> Iterator[Path]:
        for sid in session_ids:
            for row in self.db.execute(
                "SELECT json_extract(body,'$.path') FROM checkpoints "
                "WHERE json_extract(body,'$.session_id')=?",
                (sid,),
            ):
                if isinstance(row[0], str) and row[0]:
                    yield Path(row[0])

    def title_get(self, sid: str) -> str | None:
        row = self.db.execute("SELECT title FROM titles WHERE id=?", (sid,)).fetchone()
        return str(row[0]) if row else None

    def title_put(self, sid: str, title: str) -> None:
        if self.title_get(sid) != title:
            self.db.execute("INSERT OR REPLACE INTO titles VALUES (?,?)", (sid, title))

    def metadata_read(self) -> tuple[dict[str, int], dict[str, object]]:
        row = self.db.execute("SELECT value FROM meta WHERE key='metadata'").fetchone()
        try:
            raw = json.loads(row[0]) if row else {}
            cursors, index = raw.get("cursors", {}), raw.get("index", {})
            if (
                not isinstance(cursors, dict)
                or not isinstance(index, dict)
                or any(
                    not isinstance(name, str) or type(value) is not int or value < 0
                    for name, value in cursors.items()
                )
            ):
                raise ValueError("invalid metadata checkpoint")
            return cursors, index
        except (ValueError, TypeError, AttributeError):
            self.progress("Invalid metadata checkpoint; reconciling safely")
            return {}, {}

    def metadata_put(self, cursors: dict[str, int], index: dict[str, object]) -> None:
        body = json.dumps({"cursors": cursors, "index": index}, sort_keys=True)
        previous = self.db.execute("SELECT value FROM meta WHERE key='metadata'").fetchone()
        if previous is None or previous[0] != body:
            self.db.execute("INSERT OR REPLACE INTO meta VALUES ('metadata',?)", (body,))

    def row_changed(self, identity: str, signature: str) -> bool:
        row = self.db.execute("SELECT signature FROM rows WHERE id=?", (identity,)).fetchone()
        if row and row[0] == signature:
            return False
        self.db.execute("INSERT OR REPLACE INTO rows VALUES (?,?)", (identity, signature))
        return True

    def _save_session(self, session: Session, old: str | None = None) -> None:
        self.store._write(
            self.runtime / "pending-projections" / f"{key(session.id)}.json",
            {"session_id": session.id},
        )
        began = monotonic()
        self._migrate_session(session)
        self.db.execute(
            "UPDATE sessions SET stamp=? WHERE id=?",
            (json.dumps(Store._stat_key(session_path(self.root, session.id))), session.id),
        )
        self._source_stamp = self._stamp()
        self.timings["persistence_seconds"] += monotonic() - began
        signature = (
            Session.model_validate_json(old).model_dump_json(
                exclude={"title", "updated", "archived"}
            )
            if old is not None
            else ""
        )
        self._project_session(session, signature)
        self.changed = True
        self._writes += 1

    def _project_session(self, session: Session, signature: str = "") -> None:
        old_paths = {
            self.root / str(row[0])
            for row in self.db.execute("SELECT path FROM records WHERE sid=?", (session.id,))
        }
        self.store._projection[session.id] = (signature, old_paths)
        began = monotonic()
        self.store.project(Ledger(sessions={session.id: session}), sweep=False)
        self.timings["projection_seconds"] += monotonic() - began
        owned = self.store._projection.pop(session.id)[1]
        self.store._projects.clear()
        self.db.execute("DELETE FROM records WHERE sid=?", (session.id,))
        self.db.executemany(
            "INSERT OR REPLACE INTO records VALUES (?,?)",
            ((session.id, str(path.relative_to(self.root))) for path in owned),
        )

    def flush(self) -> None:
        if self._stamp() != self._source_stamp:
            raise StoreError("data changed outside this writer; stop and rebuild after restore")
        self.sessions.flush()
        if self.changed or self._diagnostics != self.ledger.diagnostics:
            self.store._write(
                self.root / "layout.json",
                {
                    "version": LAYOUT_VERSION,
                    "revision": uuid.uuid4().hex,
                    "diagnostics": self.ledger.diagnostics,
                    "legacy_ledger": "ledger.json",
                },
            )
            self._diagnostics = list(self.ledger.diagnostics)
            self.changed = False
        self._source_stamp = self._stamp()
        saved = self.db.execute("SELECT value FROM meta WHERE key='sources'").fetchone()
        if saved is None or saved[0] != self._source_stamp:
            self.db.execute(
                "INSERT OR REPLACE INTO meta VALUES ('sources',?)", (self._source_stamp,)
            )
        self.db.commit()
        for pending in (self.runtime / "pending-projections").glob("*.json"):
            pending.unlink()
