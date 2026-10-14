import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from codex_time.incremental_storage import IndexedStore
from codex_time.metadata import refresh_metadata
from codex_time.models import Ledger, Session, TokenCounts, Turn, UsageObservation
from codex_time.storage import Store, StoreError

AT = datetime(2026, 10, 14, tzinfo=UTC)


def fixture(root: Path, state: Path, count: int = 20) -> Ledger:
    ledger = Ledger(
        sessions={
            str(i): Session(
                id=str(i),
                cwd="/fixture",
                title=f"Session {i}",
                created=AT,
                updated=AT,
                turns={"t": Turn(id="t", cwd="/fixture", start=AT, end=AT + timedelta(seconds=10))},
            )
            for i in range(count)
        }
    )
    store = Store(root, state)
    with store.writer():
        store.save(ledger)
    return ledger


def stamps(root: Path) -> dict[str, tuple[int, int]]:
    return {
        str(p.relative_to(root)): (p.stat().st_mtime_ns, p.stat().st_size)
        for p in root.rglob("*")
        if p.is_file()
    }


def test_migration_parity_backup_and_bounded_cache(tmp_path: Path) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    before = fixture(root, state)
    with IndexedStore(root, state, cache_size=3) as store:
        ledger = store.ledger
        assert len(ledger.sessions) == 20
        for sid in ledger.sessions:
            assert ledger.sessions[sid] == before.sessions[sid]
        store.flush()
        assert store.cached_sessions <= 3
        assert store.verify_backup()
    assert Store(root, state).load() == before


def test_idle_no_historical_writes_and_only_changed_session(tmp_path: Path) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    fixture(root, state)
    with IndexedStore(root, state) as store:
        before = stamps(root)
        store.flush()
        assert stamps(root) == before
        store.ledger.sessions["0"].title = "Renamed"
        store.flush()
        after = stamps(root)
        changed = [name for name in before if before[name] != after[name]]
        assert len(changed) == 2  # one session + layout revision, no full ledger or projections
        assert all(name == "layout.json" or name.startswith("sessions/") for name in changed)
    assert Store(root, state).load().sessions["0"].title == "Renamed"


def test_isolated_snapshot_restore_replays_metadata_turns_and_names(tmp_path: Path) -> None:
    root, state, home = tmp_path / "data", tmp_path / "state", tmp_path / "home"
    home.mkdir()
    fixture(root, state, 1)
    with sqlite3.connect(home / "state_1.sqlite") as db:
        db.execute("CREATE TABLE threads(id TEXT PRIMARY KEY,cwd,created_at,updated_at,name)")
        db.execute("INSERT INTO threads VALUES ('0','/fixture',1700000000,1700000005,'New name')")
    with sqlite3.connect(home / "thread_history_1.sqlite") as db:
        db.execute("CREATE TABLE thread_turns(thread_id,turn_id,status,started_at,completed_at)")
        db.execute(
            "INSERT INTO thread_turns VALUES "
            "('0','metadata-turn','completed',1700000000,1700000005)"
        )
    with IndexedStore(root, state) as index:
        path = next((root / "sessions").glob("*.json"))
        before = path.read_bytes()
        cursors, names = index.metadata_read()
        refresh_metadata(
            home,
            index.ledger,
            row_changed=index.row_changed,
            active_ids=["0"],
            cursors=cursors,
            index_state=names,
            title_get=index.title_get,
            title_put=index.title_put,
        )
        index.metadata_put(cursors, names)
    assert Store(root, state).load().sessions["0"].title == "New name"
    path.write_bytes(before)  # In-place restore preserves layout revision and directory mtime.
    with IndexedStore(root, state) as index:
        cursors, names = index.metadata_read()
        refresh_metadata(
            home,
            index.ledger,
            row_changed=index.row_changed,
            active_ids=["0"],
            cursors=cursors,
            index_state=names,
            title_get=index.title_get,
            title_put=index.title_put,
        )
    restored = Store(root, state).load().sessions["0"]
    assert "metadata-turn" in restored.turns
    assert restored.title == "New name"


def test_usage_exact_dedup_and_conflict_rejection(tmp_path: Path) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    fixture(root, state, 1)
    observation = UsageObservation(
        id="u", session_id="0", at=AT, cumulative=TokenCounts(input_tokens=7)
    )
    with IndexedStore(root, state) as store:
        store.append_usage(observation)
        store.append_usage(observation)
        assert store.has_usage("u")
        assert store.previous_usage("0", AT + timedelta(seconds=1)) == observation
        assert store.has_later_usage("0", AT - timedelta(seconds=1))
        with pytest.raises(StoreError, match="conflicting"):
            store.append_usage(observation.model_copy(update={"cwd": "/other"}))
        store.flush()
    assert Store(root, state).load().usage_observations == [observation]


def test_interrupted_migration_keeps_old_ledger_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    before = fixture(root, state)
    real = IndexedStore._migrate_session
    calls = 0

    def fail(self: IndexedStore, session: Session) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("injected interruption")
        real(self, session)

    monkeypatch.setattr(IndexedStore, "_migrate_session", fail)
    with pytest.raises(OSError, match="injected"):
        with IndexedStore(root, state):
            pass
    assert not (root / "layout.json").exists()
    assert Store(root, state).load() == before
    monkeypatch.setattr(IndexedStore, "_migrate_session", real)
    with IndexedStore(root, state) as store:
        assert store.verify_backup()
    assert Store(root, state).load() == before


def test_corrupt_session_refuses_write(tmp_path: Path) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    fixture(root, state, 1)
    with IndexedStore(root, state):
        pass
    session_path = next((root / "sessions").glob("*.json"))
    session_path.write_text('{"id":')
    with pytest.raises(StoreError, match="session"):
        with IndexedStore(root, state) as store:
            store.ledger.sessions["0"].title = "unsafe"


def test_unknown_layout_fails_closed(tmp_path: Path) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    fixture(root, state, 1)
    (root / "layout.json").write_text(json.dumps({"version": 99}))
    with pytest.raises(StoreError, match="layout"):
        with IndexedStore(root, state):
            pass


def test_embedded_migration_retry_does_not_modify_original_journals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    root.mkdir()
    observation = UsageObservation(id="embedded", session_id="0", at=AT)
    legacy = Ledger(usage_observations=[observation])
    (root / "ledger.json").write_text(legacy.model_dump_json())
    (root / "usage-observations.jsonl").write_text("")
    original = (root / "usage-observations.jsonl").read_bytes()
    real = Store._write

    def interrupt(self: Store, path: Path, value: object) -> None:
        if path.name == "layout.json":
            raise OSError("injected publish interruption")
        real(self, path, value)

    monkeypatch.setattr(Store, "_write", interrupt)
    with pytest.raises(OSError, match="injected"):
        with IndexedStore(root, state):
            pass
    assert (root / "usage-observations.jsonl").read_bytes() == original
    monkeypatch.setattr(Store, "_write", real)
    with IndexedStore(root, state) as store:
        assert store.has_usage("embedded")
        assert store.verify_backup()
    assert Store(root, state).load().usage_observations == [observation]


def test_projection_interruption_repairs_on_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    fixture(root, state, 1)
    with IndexedStore(root, state):
        pass
    real = Store.project

    def interrupt(self: Store, ledger: Ledger, *, sweep: bool = True) -> None:
        for path in (root / "records").glob("*/*.json"):
            path.unlink()
        raise OSError("injected projection interruption")

    monkeypatch.setattr(Store, "project", interrupt)
    with pytest.raises(OSError, match="injected"):
        with IndexedStore(root, state) as store:
            store.ledger.sessions["0"].turns["t"].end = AT + timedelta(seconds=20)
            store.flush()
    monkeypatch.setattr(Store, "project", real)
    with IndexedStore(root, state):
        pass
    assert len(list((root / "records").glob("*/*.json"))) == 1


def test_unsupported_legacy_version_does_not_publish(tmp_path: Path) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    root.mkdir()
    (root / "ledger.json").write_text('{"version":99,"sessions":{}}')
    with pytest.raises(StoreError, match="legacy"):
        with IndexedStore(root, state):
            pass
    assert not (root / "layout.json").exists()


def test_cached_session_external_restore_is_not_overwritten(tmp_path: Path) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    fixture(root, state, 1)
    with pytest.raises(RuntimeError, match="expected cleanup"), IndexedStore(root, state) as store:
        cached = store.ledger.sessions["0"]
        path = next((root / "sessions").glob("*.json"))
        restored = Session.model_validate_json(path.read_bytes())
        restored.title = "External restore"
        path.write_text(restored.model_dump_json())
        cached.title = "Stale cache edit"
        with pytest.raises(StoreError, match="outside"):
            store.flush()
        cached.title = "Session 0"  # leave context exception handling deterministic
        with pytest.raises(StoreError, match="outside"):
            store.sessions.flush()
        # Context manager also refuses, so close manually through exceptional exit.
        raise RuntimeError("expected cleanup")


def test_summary_and_picker_do_not_load_evidence_history(tmp_path: Path) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    fixture(root, state, 1)
    with IndexedStore(root, state) as store:
        store.append_usage(UsageObservation(id="summary", session_id="0", at=AT))
    public = Store(root, state)
    assert public.summary()["sessions"] == 1
    assert public.load(include_evidence=False).usage_observations == []
    assert len(public.load().usage_observations) == 1


def test_corrupt_disposable_index_rebuilds_without_losing_history(tmp_path: Path) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    expected = fixture(root, state, 1)
    with IndexedStore(root, state):
        pass
    (state / "index.sqlite").write_bytes(b"corrupt disposable cache")
    with IndexedStore(root, state) as store:
        assert store.ledger.sessions["0"] == expected.sessions["0"]
        assert store.verify_backup()
    assert Store(root, state).load() == expected
    assert list(state.glob("index-corrupt-*.sqlite"))


def test_pending_context_reconciliation_rotates_bounded_pages(tmp_path: Path) -> None:
    from codex_time.ingest import FileState
    from codex_time.models import ModelContext

    root, state = tmp_path / "data", tmp_path / "runtime"
    fixture(root, state, 1)
    with IndexedStore(root, state) as store:
        for i in range(300):
            store.checkpoint_put(
                f"file-{i:03}",
                FileState(
                    session_id="0", contexts={"t": [ModelContext(at=AT, model_id="fixture")]}
                ),
            )
        first = store.context_batch([])
        second = store.context_batch([])
        third = store.context_batch([])
        assert len(first) == 128 and len(second) == 128 and len(third) == 44
        assert len(set(first + second + third)) == 300


def test_unchanged_wakeup_does_not_serialize_cached_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "runtime"
    fixture(root, state, 1)
    with IndexedStore(root, state) as store:
        store.ledger.sessions["0"]
        store.flush()

        def refuse(*args, **kwargs):
            raise AssertionError("untouched sessions must not be serialized")

        monkeypatch.setattr(Session, "model_dump_json", refuse)
        store.flush()
