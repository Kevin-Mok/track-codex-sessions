import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from codex_time.models import Ledger, Session, Turn
from codex_time.storage import Store, StoreError


def fixture_ledger() -> Ledger:
    now = datetime(2026, 10, 6, 16, tzinfo=UTC)
    sessions = {}
    for key in ("root-a", "root-b", "child"):
        sessions[key] = Session(
            id=key,
            cwd="/work",
            created=now,
            updated=now,
            is_child=key == "child",
            turns={
                "one": Turn(id="one", cwd="/work", start=now, end=now + timedelta(seconds=10)),
                "two": Turn(
                    id="two",
                    cwd="/work",
                    start=now + timedelta(seconds=20),
                    end=now + timedelta(seconds=30),
                ),
            },
        )
    return Ledger(sessions=sessions)


def test_unique_native_records_idempotent_and_no_runtime_data(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    with store.writer():
        store.save(fixture_ledger())
        store.save(fixture_ledger())
    records = sorted((tmp_path / "data" / "records").rglob("*.json"))
    assert len(records) == 4
    assert {json.loads(p.read_text())["project"]["key"] for p in records} == {
        p.stem for p in (tmp_path / "data" / "projects").glob("*.json")
    }
    assert all(
        set(json.loads(p.read_text())) == {"start", "end", "project", "is_billable", "tags"}
        for p in records
    )
    assert {p.name for p in (tmp_path / "data").iterdir()} == {"ledger.json", "projects", "records"}
    assert Store(tmp_path / "data", tmp_path / "runtime").load() == fixture_ledger()


def test_corruption_stops_writes(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    (store.root / "ledger.json").write_text('{"version":999}')
    with pytest.raises(StoreError, match="ledger"):
        store.load()
    assert (store.root / "ledger.json").read_text() == '{"version":999}'


def test_single_writer_lock(tmp_path: Path) -> None:
    one = Store(tmp_path / "data", tmp_path / "runtime")
    two = Store(tmp_path / "data", tmp_path / "different-runtime")
    with one.writer():
        with pytest.raises(StoreError, match="writer"):
            with two.writer():
                pass


def test_stale_record_recovery_and_unrelated_json_preservation(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    ledger = fixture_ledger()
    with store.writer():
        store.save(ledger)
        foreign = store.root / "records" / "2026-10-06" / "foreign.json"
        foreign.write_text("{}")
        del ledger.sessions["root-a"]
        store.save(ledger)
    assert len(list((store.root / "records").rglob("codex-time-*.json"))) == 2
    assert foreign.read_text() == "{}"


def test_native_records_split_at_local_midnight(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    start = datetime.fromisoformat("2026-11-01T03:30:00+00:00")
    end = datetime.fromisoformat("2026-11-01T07:30:00+00:00")
    data = Ledger(
        sessions={
            "night": Session(
                id="night",
                cwd="/work",
                created=start,
                updated=end,
                turns={"one": Turn(id="one", cwd="/work", start=start, end=end)},
            )
        }
    )
    with store.writer():
        store.save(data)
    assert {p.parent.name for p in (store.root / "records").rglob("*.json")} == {
        "2026-10-31",
        "2026-11-01",
    }
    values = [json.loads(p.read_text()) for p in (store.root / "records").rglob("*.json")]
    assert sorted(
        (datetime.fromisoformat(v["end"]) - datetime.fromisoformat(v["start"])).total_seconds()
        for v in values
    ) == [1800, 12600]


def test_runtime_checkpoint_can_use_different_filesystem(tmp_path: Path) -> None:
    import os
    import tempfile

    if not Path("/dev/shm").is_dir() or os.stat("/dev/shm").st_dev == os.stat(tmp_path).st_dev:
        pytest.skip("requires isolated tmpfs for cross-filesystem verification")
    with tempfile.TemporaryDirectory(prefix="codex-time-", dir="/dev/shm") as other:
        store = Store(tmp_path / "data", Path(other))
        with store.writer():
            store.save(fixture_ledger())
            store.runtime_save({"heartbeat": "2026-10-06T16:00:00Z"})
        assert store.runtime_read()["heartbeat"] == "2026-10-06T16:00:00Z"
