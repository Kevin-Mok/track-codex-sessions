"""Model evidence is historical, content-free and idempotent across upgrades."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from codex_time.ingest import RolloutReader
from codex_time.models import Ledger, Session, Span, Turn
from codex_time.storage import Store

BASE = datetime(2026, 10, 6, 16, tzinfo=UTC)


def record(kind: str, seconds: int, **payload: object) -> str:
    return (
        json.dumps(
            {
                "type": kind,
                "timestamp": (BASE + timedelta(seconds=seconds)).isoformat(),
                "payload": payload,
            }
        )
        + "\n"
    )


def source(home: Path, tail: list[str]) -> Path:
    path = home / "sessions" / "fixture.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        record("session_meta", 0, id="root", cwd="/work", source="cli")
        + record("event_msg", 0, type="task_started", turn_id="one")
        + "".join(tail)
    )
    return path


def test_contexts_capture_exact_fields_deduplicate_and_survive_restart_archive(
    tmp_path: Path,
) -> None:
    path = source(
        tmp_path,
        [
            record(
                "turn_context", 2, turn_id="one", model="exact-A", effort="high", prompt="SECRET"
            ),
            record("turn_context", 3, turn_id="one", model="exact-A", effort="high"),
            record("turn_context", 20, turn_id="one", model="exact-A", effort="max"),
        ],
    )
    ledger = Ledger()
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)
    turn = ledger.sessions["root"].turns["one"]
    assert [(c.model_id, c.reasoning_level, c.at) for c in turn.model_contexts] == [
        ("exact-A", "high", BASE + timedelta(seconds=2)),
        ("exact-A", "high", BASE + timedelta(seconds=3)),
        ("exact-A", "max", BASE + timedelta(seconds=20)),
    ]
    with path.open("a") as stream:
        stream.write(record("turn_context", 30, turn_id="one", model="exact-B", effort="low"))
        stream.write(record("event_msg", 60, type="task_complete", turn_id="one"))
    archive = tmp_path / "archived_sessions"
    archive.mkdir()
    path.rename(archive / path.name)
    reader = RolloutReader(tmp_path, reader.checkpoints)
    reader.scan(ledger)
    assert ledger.sessions["root"].archived
    before = ledger.model_dump_json()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.model_dump_json() == before
    assert "SECRET" not in before + json.dumps(reader.checkpoints)
    assert len(turn.model_contexts) == 4


def test_legacy_ledger_backfill_invalidates_old_offsets_preserves_timing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    path = source(
        home,
        [
            record("turn_context", 2, turn_id="one", model="A", effort="high"),
            record("event_msg", 60, type="task_complete", turn_id="one"),
        ],
    )
    turn = Turn(
        id="one",
        cwd="/work",
        start=BASE,
        end=BASE + timedelta(seconds=60),
        waits=[Span(start=BASE + timedelta(seconds=10), end=BASE + timedelta(seconds=30))],
        coverage=[Span(start=BASE, end=BASE + timedelta(seconds=5))],
    )
    original = Ledger(
        sessions={
            "root": Session(
                id="root",
                cwd="/work",
                created=BASE,
                updated=BASE + timedelta(seconds=60),
                turns={"one": turn},
            )
        }
    ).model_dump(mode="json")
    original["version"] = 1
    for t in original["sessions"]["root"]["turns"].values():
        t.pop("model_contexts", None)
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    (store.root / "ledger.json").write_text(json.dumps(original))
    ledger = store.load()
    assert ledger.version == 3
    stat = path.stat()
    old = {
        "version": 1,
        "files": {
            f"{stat.st_dev}:{stat.st_ino}": {
                "offset": path.stat().st_size,
                "session_id": "root",
                "cwd": "/work",
            }
        },
    }
    reader = RolloutReader(home, old)
    reader.scan(ledger)
    recovered = ledger.sessions["root"].turns["one"]
    assert recovered.waits == turn.waits and recovered.coverage == turn.coverage
    assert recovered.start == turn.start and recovered.end == turn.end
    assert recovered.model_contexts[0].model_id == "A"
    assert reader.checkpoints["version"] == 3
    before = ledger.model_dump_json()
    RolloutReader(home, reader.checkpoints).scan(ledger)
    assert ledger.model_dump_json() == before
    path.unlink()
    RolloutReader(home).scan(ledger)
    assert ledger.model_dump_json() == before
    with store.writer():
        store.save(ledger)
    assert Store(store.root, store.runtime).load() == ledger


def test_missing_fields_conflicts_and_context_before_start(tmp_path: Path) -> None:
    source(
        tmp_path,
        [
            record("turn_context", 1, turn_id="one", model="A"),
            record("turn_context", 20, turn_id="one", model="B", effort="high"),
            record("turn_context", 20, turn_id="one", model="C", effort="high"),
            record("turn_context", 50, turn_id="two", model="D", effort="medium"),
            record("event_msg", 60, type="task_started", turn_id="two"),
            record("event_msg", 90, type="task_complete", turn_id="two"),
        ],
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.sessions["root"].turns["one"].model_contexts[0].reasoning_level is None
    assert "model_context_conflict" in ledger.sessions["root"].turns["one"].quality
    assert "conflicting model context; attribution unknown" in ledger.diagnostics
    assert ledger.sessions["root"].turns["two"].model_contexts[0].model_id == "D"


def test_available_context_attaches_to_sqlite_only_turn_after_metadata(tmp_path: Path) -> None:
    import sqlite3

    from codex_time.daemon import import_history

    home = tmp_path / "home"
    path = source(home, [record("turn_context", 2, turn_id="one", model="A", effort="high")])
    # Deliberately omit lifecycle start: SQLite provides timing, never models.
    path.write_text(
        record("session_meta", 0, id="root", cwd="/work", source="cli")
        + record("turn_context", 2, turn_id="one", model="A", effort="high")
    )
    db = home / "thread_history_1.sqlite"
    with sqlite3.connect(db) as connection:
        connection.execute(
            "CREATE TABLE thread_turns (thread_id TEXT, turn_id TEXT, status TEXT, "
            "started_at INTEGER, completed_at INTEGER)"
        )
        connection.execute(
            "INSERT INTO thread_turns VALUES (?,?,?,?,?)",
            (
                "root",
                "one",
                "completed",
                BASE.timestamp(),
                (BASE + timedelta(seconds=60)).timestamp(),
            ),
        )
    before = db.read_bytes()
    store = Store(tmp_path / "data", tmp_path / "runtime")
    data = import_history(store, home)
    assert data.sessions["root"].turns["one"].model_contexts[0].model_id == "A"
    assert import_history(store, home) == data
    assert db.read_bytes() == before


def test_model_backfill_does_not_change_native_record_identity(tmp_path: Path) -> None:
    data = Ledger(
        sessions={
            "root": Session(
                id="root",
                cwd="/work",
                created=BASE,
                updated=BASE,
                turns={
                    "one": Turn(id="one", cwd="/work", start=BASE, end=BASE + timedelta(seconds=60))
                },
            )
        }
    )
    store = Store(tmp_path / "data", tmp_path / "runtime")
    with store.writer():
        store.save(data)
        before = {
            path.relative_to(store.root): path.read_bytes()
            for path in store.root.rglob("*.json")
            if path.name != "ledger.json"
        }
        home = tmp_path / "home"
        source(
            home,
            [
                record("turn_context", 2, turn_id="one", model="A", effort="high"),
                record("turn_context", 30, turn_id="one", model="B", effort="max"),
                record("event_msg", 60, type="task_complete", turn_id="one"),
            ],
        )
        reader = RolloutReader(home)
        reader.scan(data)
        store.save(data)
        after = {
            path.relative_to(store.root): path.read_bytes()
            for path in store.root.rglob("*.json")
            if path.name != "ledger.json"
        }
    assert before == after
    assert len(data.sessions["root"].turns["one"].model_contexts) == 2
