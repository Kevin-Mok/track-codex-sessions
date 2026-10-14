"""Schema-detected, strictly read-only adapters for Codex metadata databases."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import datetime
from pathlib import Path

from codex_time.ingest import ancestry, diagnostic, timestamp
from codex_time.models import Ledger, Session, Turn


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    # Table identifiers are fixed internal constants, never user input.
    return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _time(row: sqlite3.Row, name: str) -> datetime:
    ms = f"{name}_ms"
    if ms in row.keys() and isinstance(row[ms], (int, float)) and row[ms] > 0:
        return timestamp(row[ms] / 1000)
    return timestamp(row[name])


def refresh_metadata(
    home: Path,
    ledger: Ledger,
    *,
    row_changed: Callable[[str, str], bool] | None = None,
    active_ids: list[str] | None = None,
    cursors: dict[str, int] | None = None,
    batch_size: int = 128,
    index_state: dict[str, object] | None = None,
    title_get: Callable[[str], str | None] | None = None,
    title_put: Callable[[str, str], None] | None = None,
) -> bool:
    """Read active IDs and bounded historical pages; return whether pages remain.

    Omitting cursors/index_state preserves full import behavior. Incremental index
    names require exact external storage so unknown-session titles survive backfill.
    Only explicit names become titles; no conversation/title heuristics are used.
    """
    if batch_size < 1:
        raise ValueError("metadata batch size must be positive")
    if index_state is not None and (title_get is None or title_put is None):
        raise ValueError("incremental session index requires exact title_get/title_put callbacks")
    pending = False
    for path in sorted(home.glob("state_*.sqlite")):
        pending = (
            _read_database(
                path,
                ledger,
                history=False,
                row_changed=row_changed,
                active_ids=active_ids,
                cursors=cursors,
                batch_size=batch_size,
                title_get=title_get,
            )
            or pending
        )
    for path in sorted(home.glob("thread_history_*.sqlite")):
        pending = (
            _read_database(
                path,
                ledger,
                history=True,
                row_changed=row_changed,
                active_ids=active_ids,
                cursors=cursors,
                batch_size=batch_size,
                title_get=title_get,
            )
            or pending
        )
    path = home / "session_index.jsonl"
    if not path.exists():
        return pending
    return (
        _session_index(
            path,
            ledger,
            index_state=index_state,
            batch_size=batch_size,
            title_get=title_get,
            title_put=title_put,
        )
        or pending
    )


def _session_index(
    path: Path,
    ledger: Ledger,
    *,
    index_state: dict[str, object] | None,
    batch_size: int,
    title_get: Callable[[str], str | None] | None,
    title_put: Callable[[str, str], None] | None,
) -> bool:
    try:
        stat = path.stat()
        offset = 0
        if index_state is not None:
            raw_offset = index_state.get("offset", 0)
            offset = raw_offset if type(raw_offset) is int and raw_offset >= 0 else 0
            unchanged = all(
                index_state.get(key) == value
                for key, value in {
                    "dev": stat.st_dev,
                    "ino": stat.st_ino,
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "ctime_ns": stat.st_ctime_ns,
                }.items()
            )
            if unchanged and (offset == stat.st_size or index_state.get("pending") is False):
                return False
        with path.open("rb") as stream:
            if index_state is not None:
                prefix_size = index_state.get("prefix_size", 0)
                prefix_size = prefix_size if type(prefix_size) is int and prefix_size >= 0 else 0
                prefix = hashlib.sha256(stream.read(min(256, prefix_size))).hexdigest()
                tail_size = min(256, offset)
                stream.seek(offset - tail_size)
                tail = hashlib.sha256(stream.read(tail_size)).hexdigest()
                replaced = (
                    index_state.get("dev") != stat.st_dev
                    or index_state.get("ino") != stat.st_ino
                    or stat.st_size < offset
                    or (offset > 0 and index_state.get("prefix") != prefix)
                    or (offset > 0 and index_state.get("tail") != tail)
                    or (stat.st_size == index_state.get("size") and not unchanged)
                )
                if replaced:
                    offset = 0
            stream.seek(offset)
            lines = 0
            partial = False
            while index_state is None or lines < batch_size:
                raw = stream.readline()
                if not raw:
                    break
                if not raw.endswith(b"\n"):
                    partial = True
                    break
                offset = stream.tell()
                lines += 1
                try:
                    value = json.loads(raw)
                    if not isinstance(value, dict):
                        raise ValueError("expected object")
                    sid = value.get("id")
                    session = ledger.sessions.get(sid) if isinstance(sid, str) else None
                    title = value.get("thread_name")
                    if isinstance(sid, str) and isinstance(title, str) and title.strip():
                        if title_put is not None:
                            title_put(sid, title.strip())
                        if session is not None:
                            session.title = title.strip()
                except (ValueError, TypeError):
                    diagnostic(ledger, "malformed session index record skipped")
            if index_state is not None:
                prefix_size = min(256, stat.st_size)
                stream.seek(0)
                prefix = hashlib.sha256(stream.read(prefix_size)).hexdigest()
                stream.seek(offset - min(256, offset))
                tail = hashlib.sha256(stream.read(min(256, offset))).hexdigest()
                index_state.update(
                    {
                        "dev": stat.st_dev,
                        "ino": stat.st_ino,
                        "offset": offset,
                        "size": stat.st_size,
                        "mtime_ns": stat.st_mtime_ns,
                        "ctime_ns": stat.st_ctime_ns,
                        "prefix_size": prefix_size,
                        "prefix": prefix,
                        "tail": tail,
                        "pending": offset < stat.st_size and not partial,
                    }
                )
                return offset < stat.st_size and not partial
    except OSError:
        diagnostic(ledger, "session index unavailable; will retry")
    return False


def _rows(
    connection: sqlite3.Connection,
    selected: str,
    table: str,
    *,
    cursor_key: str,
    active_columns: tuple[str, ...],
    active_ids: list[str] | None,
    cursors: dict[str, int] | None,
    batch_size: int,
    related_ids: dict[str, list[str]] | None = None,
) -> tuple[Iterator[sqlite3.Row], bool]:
    """Union exact active matches with a rowid page without materializing history."""
    if cursors is None:
        return iter(connection.execute(f"SELECT {selected} FROM {table}")), False
    position = cursors.get(cursor_key, 0)
    if type(position) is not int or position < 0:
        position = 0
    page = connection.execute(
        f"SELECT rowid FROM {table} WHERE rowid>? ORDER BY rowid LIMIT ?",
        (position, batch_size + 1),
    ).fetchall()
    pending = len(page) > batch_size
    identities = [row[0] for row in page[:batch_size]]
    cursors[cursor_key] = identities[-1] if identities and pending else 0
    predicates = []
    parameters: list[object] = []
    if identities:
        predicates.append("rowid IN (" + ",".join("?" for _ in identities) + ")")
        parameters.extend(identities)
    for column in active_columns:
        ids = list(dict.fromkeys([*(active_ids or []), *(related_ids or {}).get(column, [])]))
        if ids:
            predicates.append(f'"{column}" IN (' + ",".join("?" for _ in ids) + ")")
            parameters.extend(ids)
    predicate = " OR ".join(predicates) or "0"
    rows = connection.execute(
        f"SELECT {selected} FROM {table} WHERE {predicate} ORDER BY rowid", parameters
    )
    return iter(rows), pending


def _read_database(
    path: Path,
    ledger: Ledger,
    *,
    history: bool,
    row_changed: Callable[[str, str], bool] | None = None,
    active_ids: list[str] | None = None,
    cursors: dict[str, int] | None = None,
    batch_size: int = 128,
    title_get: Callable[[str], str | None] | None = None,
) -> bool:
    try:
        # mode=ro guarantees that observing never creates or changes a database.
        with closing(
            sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.2)
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            if history:
                return _turns(
                    connection,
                    ledger,
                    row_changed=row_changed,
                    active_ids=active_ids,
                    cursors=cursors,
                    batch_size=batch_size,
                    cursor_prefix=str(path.resolve()),
                )
            else:
                return _threads(
                    connection,
                    ledger,
                    row_changed=row_changed,
                    active_ids=active_ids,
                    cursors=cursors,
                    batch_size=batch_size,
                    cursor_prefix=str(path.resolve()),
                    title_get=title_get,
                )
    except (sqlite3.Error, OSError):
        diagnostic(ledger, "Codex metadata database unreadable; will retry")
    return False


def _threads(
    connection: sqlite3.Connection,
    ledger: Ledger,
    *,
    row_changed: Callable[[str, str], bool] | None = None,
    active_ids: list[str] | None = None,
    cursors: dict[str, int] | None = None,
    batch_size: int = 128,
    cursor_prefix: str = "",
    title_get: Callable[[str], str | None] | None = None,
) -> bool:
    columns = _columns(connection, "threads")
    required = {"id", "cwd", "created_at", "updated_at"}
    if not required <= columns:
        diagnostic(ledger, "unsupported Codex threads schema; rollout data retained")
        return False
    allowed = required | {
        "created_at_ms",
        "updated_at_ms",
        "name",
        "archived",
        "source",
        "parent_thread_id",
        "thread_source",
    }
    selected = ",".join(f'"{column}"' for column in sorted(allowed & columns))
    rows, pending = _rows(
        connection,
        selected,
        "threads",
        cursor_key=cursor_prefix + ":threads",
        active_columns=("id",),
        active_ids=active_ids,
        cursors=cursors,
        batch_size=batch_size,
    )
    seen_ids: list[str] = []
    for row in rows:
        try:
            sid, cwd = row["id"], row["cwd"]
            if not isinstance(sid, str) or not isinstance(cwd, str):
                raise ValueError("invalid metadata ID or directory")
            seen_ids.append(sid)
            if (
                row_changed is not None
                and not row_changed("thread:" + sid, json.dumps(dict(row), sort_keys=True))
                and sid in ledger.sessions
            ):
                explicit = title_get(sid) if title_get is not None else None
                if explicit is not None:
                    ledger.sessions[sid].title = explicit
                continue
            created, updated = _time(row, "created_at"), _time(row, "updated_at")
            fields = {key: row[key] for key in row.keys()}
            parent, child = ancestry(fields)
            session = ledger.sessions.setdefault(
                sid,
                Session(
                    id=sid,
                    cwd=cwd,
                    created=created,
                    updated=updated,
                    parent_id=parent,
                    is_child=child,
                ),
            )
            session.cwd = cwd
            session.created = min(session.created, created)
            session.updated = max(session.updated, updated)
            session.is_child = session.is_child or child
            if parent:
                session.parent_id = parent
            if "archived" in row.keys():
                session.archived = bool(row["archived"])
            if "name" in row.keys() and isinstance(row["name"], str) and row["name"].strip():
                session.title = row["name"].strip()
            explicit = title_get(sid) if title_get is not None else None
            if explicit is not None:
                session.title = explicit
        except (ValueError, TypeError, OverflowError):
            diagnostic(ledger, "invalid Codex thread metadata skipped")
    if {"parent_thread_id", "child_thread_id"} <= _columns(connection, "thread_spawn_edges"):
        rows, edge_pending = _rows(
            connection,
            "parent_thread_id,child_thread_id",
            "thread_spawn_edges",
            cursor_key=cursor_prefix + ":thread_spawn_edges",
            active_columns=("parent_thread_id", "child_thread_id"),
            active_ids=active_ids,
            cursors=cursors,
            batch_size=batch_size,
            related_ids={"child_thread_id": seen_ids},
        )
        pending = pending or edge_pending
        for row in rows:
            child_session = ledger.sessions.get(row["child_thread_id"])
            if child_session is None:
                continue
            if row_changed is not None and not row_changed(
                "edge:" + str(row["child_thread_id"]), json.dumps(dict(row), sort_keys=True)
            ):
                continue
            if child_session is not None and isinstance(row["parent_thread_id"], str):
                child_session.parent_id = row["parent_thread_id"]
                child_session.is_child = True
    return pending


def _turns(
    connection: sqlite3.Connection,
    ledger: Ledger,
    *,
    row_changed: Callable[[str, str], bool] | None = None,
    active_ids: list[str] | None = None,
    cursors: dict[str, int] | None = None,
    batch_size: int = 128,
    cursor_prefix: str = "",
) -> bool:
    columns = _columns(connection, "thread_turns")
    required = {"thread_id", "turn_id", "status", "started_at", "completed_at"}
    if not required <= columns:
        diagnostic(ledger, "unsupported Codex turns schema; rollout data retained")
        return False
    selected = ",".join(f'"{column}"' for column in sorted(required))
    rows, pending = _rows(
        connection,
        selected,
        "thread_turns",
        cursor_key=cursor_prefix + ":thread_turns",
        active_columns=("thread_id",),
        active_ids=active_ids,
        cursors=cursors,
        batch_size=batch_size,
    )
    for row in rows:
        session = ledger.sessions.get(row["thread_id"])
        if session is None:
            continue
        if row_changed is not None and not row_changed(
            "turn:" + str(row["thread_id"]) + ":" + str(row["turn_id"]),
            json.dumps(dict(row), sort_keys=True),
        ):
            continue
        try:
            tid = row["turn_id"]
            if not isinstance(tid, str) or row["started_at"] is None:
                continue
            start = timestamp(row["started_at"])
            turn = session.turns.get(tid)
            if turn is None:
                turn = Turn(
                    id=tid,
                    cwd=session.cwd,
                    start=start,
                    provenance=["sqlite"],
                    quality=[
                        "historical_upper_bound",
                        "metadata_cwd_estimate",
                        "metadata_start_estimate",
                    ],
                )
                session.turns[tid] = turn
            if "no_lifecycle_events" in session.quality:
                session.quality.remove("no_lifecycle_events")
            end = timestamp(row["completed_at"]) if row["completed_at"] is not None else None
            if end is not None and end >= turn.start and turn.end is None:
                turn.end = end
                if "sqlite" not in turn.provenance:
                    turn.provenance.append("sqlite")
                turn.outcome = str(row["status"])
                if "metadata_reconciled" not in turn.quality:
                    turn.quality.append("metadata_reconciled")
                if "metadata_end_estimate" not in turn.quality:
                    turn.quality.append("metadata_end_estimate")
        except (ValueError, TypeError, OverflowError):
            diagnostic(ledger, "invalid Codex turn metadata skipped")
    return pending


def current_rollouts(home: Path, session_ids: list[str]) -> list[Path]:
    """Resolve live source paths through a bounded, strictly read-only ID query."""
    found: set[Path] = set()
    if not session_ids:
        return []
    for path in home.glob("state_*.sqlite"):
        try:
            with closing(
                sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.2)
            ) as connection:
                connection.execute("PRAGMA query_only=ON")
                if not {"id", "rollout_path"} <= _columns(connection, "threads"):
                    continue
                for offset in range(0, len(session_ids), 128):
                    chunk = session_ids[offset : offset + 128]
                    placeholders = ",".join("?" for _ in chunk)
                    for row in connection.execute(
                        f"SELECT rollout_path FROM threads WHERE id IN ({placeholders})", chunk
                    ):
                        if isinstance(row[0], str):
                            candidate = Path(row[0]).resolve()
                            if any(
                                candidate.is_relative_to(home / name)
                                for name in ("sessions", "archived_sessions")
                            ):
                                found.add(candidate)
        except (sqlite3.Error, OSError):
            continue
    return sorted(found)
