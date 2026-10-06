import json
import sqlite3
from pathlib import Path

from codex_time.models import Ledger


def make_db(home: Path) -> None:
    with sqlite3.connect(home / "state_5.sqlite") as c:
        c.execute(
            "CREATE TABLE threads (id TEXT, cwd TEXT, created_at INTEGER, updated_at INTEGER, "
            "title TEXT, first_user_message TEXT, name TEXT, archived INTEGER, source TEXT)"
        )
        c.execute(
            "INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "s1",
                "/a",
                1700000000,
                1700000060,
                "SECRET first prompt",
                "SECRET first prompt",
                None,
                1,
                "cli",
            ),
        )
        c.execute("CREATE TABLE thread_spawn_edges (parent_thread_id TEXT, child_thread_id TEXT)")
        c.execute("INSERT INTO thread_spawn_edges VALUES (?,?)", ("parent", "s1"))


def test_metadata_read_only_explicit_name_and_ancestry(tmp_path: Path) -> None:
    from codex_time.metadata import refresh_metadata

    make_db(tmp_path)
    ledger = Ledger()
    before = (tmp_path / "state_5.sqlite").read_bytes()
    refresh_metadata(tmp_path, ledger)
    assert (tmp_path / "state_5.sqlite").read_bytes() == before
    assert ledger.sessions["s1"].title == ""
    assert ledger.sessions["s1"].archived
    assert ledger.sessions["s1"].parent_id == "parent"
    assert ledger.sessions["s1"].is_child
    (tmp_path / "session_index.jsonl").write_text(
        json.dumps(
            {"id": "s1", "thread_name": "Explicit name", "updated_at": "2026-10-06T12:00:00Z"}
        )
        + "\n"
    )
    refresh_metadata(tmp_path, ledger)
    assert ledger.sessions["s1"].title == "Explicit name"
    assert "SECRET" not in ledger.model_dump_json()


def test_sqlite_turn_reconciliation_is_idempotent(tmp_path: Path) -> None:
    from codex_time.metadata import refresh_metadata

    make_db(tmp_path)
    with sqlite3.connect(tmp_path / "thread_history_1.sqlite") as c:
        c.execute(
            "CREATE TABLE thread_turns (thread_id TEXT, turn_id TEXT, "
            "status TEXT, started_at INTEGER, completed_at INTEGER, duration_ms INTEGER)"
        )
        c.execute(
            "INSERT INTO thread_turns VALUES (?,?,?,?,?,?)",
            ("s1", "t1", "completed", 1700000000, 1700000060, 60000),
        )
    ledger = Ledger()
    refresh_metadata(tmp_path, ledger)
    refresh_metadata(tmp_path, ledger)
    assert len(ledger.sessions["s1"].turns) == 1
    turn = ledger.sessions["s1"].turns["t1"]
    assert turn.end is not None
    assert (turn.end - turn.start).total_seconds() == 60
    assert "historical_upper_bound" in turn.quality


def test_unsupported_and_corrupt_schemas_are_content_free_diagnostics(tmp_path: Path) -> None:
    from codex_time.metadata import refresh_metadata

    with sqlite3.connect(tmp_path / "state_9.sqlite") as c:
        c.execute("CREATE TABLE threads (secret TEXT)")
    (tmp_path / "state_10.sqlite").write_text("SECRET corruption")
    ledger = Ledger()
    refresh_metadata(tmp_path, ledger)
    assert ledger.diagnostics
    assert "SECRET" not in ledger.model_dump_json()


def test_precise_rollout_replaces_metadata_estimates_without_later_downgrade(
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime

    from codex_time.ingest import RolloutReader
    from codex_time.metadata import refresh_metadata

    make_db(tmp_path)
    with sqlite3.connect(tmp_path / "thread_history_1.sqlite") as c:
        c.execute(
            "CREATE TABLE thread_turns (thread_id TEXT, turn_id TEXT, status TEXT, "
            "started_at INTEGER, completed_at INTEGER)"
        )
        c.execute(
            "INSERT INTO thread_turns VALUES (?,?,?,?,?)",
            ("s1", "t1", "completed", 1700000000, 1700000060),
        )
    ledger = Ledger()
    refresh_metadata(tmp_path, ledger)
    assert ledger.sessions["s1"].turns["t1"].provenance == ["sqlite"]
    precise_start = datetime.fromtimestamp(1700000000.25, UTC)
    precise_end = datetime.fromtimestamp(1700000060.75, UTC)
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    events = [
        ("session_meta", precise_start, {"id": "s1", "cwd": "/old", "source": "cli"}),
        ("event_msg", precise_start, {"type": "task_started", "turn_id": "t1"}),
        ("turn_context", precise_start, {"turn_id": "t1", "cwd": "/precise"}),
        ("event_msg", precise_end, {"type": "task_complete", "turn_id": "t1"}),
    ]
    (sessions / "one.jsonl").write_text(
        "".join(
            json.dumps({"timestamp": at.isoformat(), "type": kind, "payload": payload}) + "\n"
            for kind, at, payload in events
        )
    )
    RolloutReader(tmp_path).scan(ledger)
    turn = ledger.sessions["s1"].turns["t1"]
    assert set(turn.provenance) == {"sqlite", "rollout"}
    assert turn.start == precise_start
    assert turn.end == precise_end
    assert turn.cwd == "/precise"
    assert "metadata_cwd_estimate" not in turn.quality
    assert "metadata_reconciled" not in turn.quality
    assert "historical_upper_bound" in turn.quality
    refresh_metadata(tmp_path, ledger)
    assert ledger.sessions["s1"].turns["t1"] == turn


def test_precise_zero_second_turn_replaces_rounded_metadata_atomically(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from codex_time.ingest import RolloutReader
    from codex_time.metadata import refresh_metadata

    make_db(tmp_path)
    with sqlite3.connect(tmp_path / "thread_history_1.sqlite") as c:
        c.execute(
            "CREATE TABLE thread_turns (thread_id TEXT, turn_id TEXT, status TEXT, "
            "started_at INTEGER, completed_at INTEGER)"
        )
        c.execute(
            "INSERT INTO thread_turns VALUES (?,?,?,?,?)",
            ("s1", "t1", "completed", 1700000000, 1700000000),
        )
    ledger = Ledger()
    refresh_metadata(tmp_path, ledger)
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    start = datetime.fromtimestamp(1700000000.25, UTC)
    end = datetime.fromtimestamp(1700000000.75, UTC)
    (sessions / "one.jsonl").write_text(
        "".join(
            json.dumps({"timestamp": at.isoformat(), "type": kind, "payload": payload}) + "\n"
            for kind, at, payload in [
                ("session_meta", start, {"id": "s1", "cwd": "/a", "source": "cli"}),
                ("event_msg", start, {"type": "task_started", "turn_id": "t1"}),
                ("event_msg", end, {"type": "task_complete", "turn_id": "t1"}),
            ]
        )
    )
    RolloutReader(tmp_path).scan(ledger)
    turn = ledger.sessions["s1"].turns["t1"]
    assert turn.start == start and turn.end == end
    assert not ledger.diagnostics


def test_duplicate_lifecycle_preserves_precise_start_when_cwd_remains_estimated(
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime

    from codex_time.ingest import RolloutReader
    from codex_time.metadata import refresh_metadata

    make_db(tmp_path)
    with sqlite3.connect(tmp_path / "thread_history_1.sqlite") as c:
        c.execute(
            "CREATE TABLE thread_turns (thread_id TEXT, turn_id TEXT, status TEXT, "
            "started_at INTEGER, completed_at INTEGER)"
        )
        c.execute(
            "INSERT INTO thread_turns VALUES (?,?,?,?,?)", ("s1", "t1", "running", 1700000000, None)
        )
    ledger = Ledger()
    refresh_metadata(tmp_path, ledger)
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    precise_start = datetime.fromtimestamp(1700000000.25, UTC)
    records = [
        (precise_start, "session_meta", {"id": "s1", "cwd": "/a", "source": "cli"}),
        (precise_start, "event_msg", {"type": "task_started", "turn_id": "t1"}),
        (
            datetime.fromtimestamp(1700000000.5, UTC),
            "event_msg",
            {"type": "task_started", "turn_id": "t1"},
        ),
    ]
    (sessions / "one.jsonl").write_text(
        "".join(
            json.dumps({"timestamp": at.isoformat(), "type": kind, "payload": payload}) + "\n"
            for at, kind, payload in records
        )
    )
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.sessions["s1"].turns["t1"].start == precise_start
