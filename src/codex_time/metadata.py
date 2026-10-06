"""Schema-detected, strictly read-only adapters for Codex metadata databases."""

from __future__ import annotations

import json
import sqlite3
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


def refresh_metadata(home: Path, ledger: Ledger) -> None:
    """No conversation/title heuristics: only explicit names become display titles."""
    for path in sorted(home.glob("state_*.sqlite")):
        _read_database(path, ledger, history=False)
    for path in sorted(home.glob("thread_history_*.sqlite")):
        _read_database(path, ledger, history=True)
    path = home / "session_index.jsonl"
    if not path.exists():
        return
    try:
        with path.open("rb") as stream:
            for raw in stream:
                if not raw.endswith(b"\n"):
                    break
                try:
                    value = json.loads(raw)
                    if not isinstance(value, dict):
                        raise ValueError("expected object")
                    sid = value.get("id")
                    session = ledger.sessions.get(sid) if isinstance(sid, str) else None
                    title = value.get("thread_name")
                    if session is not None and isinstance(title, str) and title.strip():
                        session.title = title.strip()
                except (ValueError, TypeError):
                    diagnostic(ledger, "malformed session index record skipped")
    except OSError:
        diagnostic(ledger, "session index unavailable; will retry")


def _read_database(path: Path, ledger: Ledger, *, history: bool) -> None:
    try:
        # mode=ro guarantees that observing never creates or changes a database.
        with sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.2
        ) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            if history:
                _turns(connection, ledger)
            else:
                _threads(connection, ledger)
    except (sqlite3.Error, OSError):
        diagnostic(ledger, "Codex metadata database unreadable; will retry")


def _threads(connection: sqlite3.Connection, ledger: Ledger) -> None:
    columns = _columns(connection, "threads")
    required = {"id", "cwd", "created_at", "updated_at"}
    if not required <= columns:
        diagnostic(ledger, "unsupported Codex threads schema; rollout data retained")
        return
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
    for row in connection.execute(f"SELECT {selected} FROM threads"):
        try:
            sid, cwd = row["id"], row["cwd"]
            if not isinstance(sid, str) or not isinstance(cwd, str):
                raise ValueError("invalid metadata ID or directory")
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
        except (ValueError, TypeError, OverflowError):
            diagnostic(ledger, "invalid Codex thread metadata skipped")
    if {"parent_thread_id", "child_thread_id"} <= _columns(connection, "thread_spawn_edges"):
        for row in connection.execute(
            "SELECT parent_thread_id,child_thread_id FROM thread_spawn_edges"
        ):
            child_session = ledger.sessions.get(row["child_thread_id"])
            if child_session is not None and isinstance(row["parent_thread_id"], str):
                child_session.parent_id = row["parent_thread_id"]
                child_session.is_child = True


def _turns(connection: sqlite3.Connection, ledger: Ledger) -> None:
    columns = _columns(connection, "thread_turns")
    required = {"thread_id", "turn_id", "status", "started_at", "completed_at"}
    if not required <= columns:
        diagnostic(ledger, "unsupported Codex turns schema; rollout data retained")
        return
    selected = ",".join(f'"{column}"' for column in sorted(required))
    for row in connection.execute(f"SELECT {selected} FROM thread_turns"):
        session = ledger.sessions.get(row["thread_id"])
        if session is None:
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
