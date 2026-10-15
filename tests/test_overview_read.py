"""Overview reuses only a current disposable evidence index, without taking its writer lock."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from test_overview import BASE, quota, sample_ledger

from codex_time.incremental_storage import IndexedStore
from codex_time.models import TokenCounts, UsageObservation
from codex_time.overview import overview_report
from codex_time.storage import Store


def prepared(tmp_path: Path) -> Store:
    store = Store(tmp_path / "data", tmp_path / "state")
    ledger = sample_ledger()
    ledger.usage_observations = [
        UsageObservation(
            id=str(day), session_id="root", at=BASE + timedelta(days=day), cwd="/one",
            model_id="gpt-4.1", delta=TokenCounts(input_tokens=10, output_tokens=1),
        ) for day in (-20, 0, 20)
    ]
    ledger.quota_observations += [quota(-86400, 9), quota(90000, 15)]
    with store.writer():
        store.save(ledger)
    with IndexedStore(store.root, store.runtime):
        pass
    return store


def read(store: Store, **kwargs):
    from codex_time.overview_read import load_overview

    return load_overview(store, period="day", selected_date=date(2026, 10, 6), **kwargs)


def test_current_index_skips_journal_reads_and_filters_usage(tmp_path, monkeypatch):
    store = prepared(tmp_path)
    monkeypatch.delattr(Store, "load_timing")
    expected = overview_report(store.load(), selected_date=date(2026, 10, 6))
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert path.suffix != ".jsonl", "overview reread indexed historical evidence"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    # The daemon writer can remain active; the reader must never take its lock.
    with store.writer():
        ledger = read(store)
    assert [u.id for u in ledger.usage_observations] == ["0"]
    assert overview_report(ledger, selected_date=date(2026, 10, 6)) == expected


@pytest.mark.parametrize("damage", ["missing", "corrupt", "stale", "schema", "invalid-row"])
def test_unusable_index_reads_authoritative_journals(tmp_path, damage):
    store = prepared(tmp_path)
    index = store.runtime / "index.sqlite"
    if damage == "missing":
        index.unlink()
    elif damage == "corrupt":
        index.write_bytes(b"corrupt database")
    elif damage == "stale":
        with (store.root / "quota-observations.jsonl").open("a") as out:
            out.write(quota(700, 18).model_dump_json() + "\n")
    else:
        with sqlite3.connect(index) as db:
            if damage == "schema":
                db.execute("DROP TABLE usage")
            else:
                db.execute("UPDATE usage SET body='{}' WHERE id='0'")
    expected = overview_report(store.load(), selected_date=date(2026, 10, 6))
    assert overview_report(read(store), selected_date=date(2026, 10, 6)) == expected


def test_source_change_during_index_read_falls_back(tmp_path, monkeypatch):
    from codex_time import incremental_storage

    store = prepared(tmp_path)
    original = incremental_storage.IndexedStore._stamp
    calls = 0

    def changing(index):
        nonlocal calls
        calls += 1
        if calls == 2:
            with (store.root / "quota-observations.jsonl").open("a") as out:
                out.write(quota(700, 18).model_dump_json() + "\n")
        return original(index)

    monkeypatch.setattr(incremental_storage.IndexedStore, "_stamp", changing)
    actual = overview_report(read(store), selected_date=date(2026, 10, 6))
    expected = overview_report(store.load(), selected_date=date(2026, 10, 6))
    assert actual == expected


@pytest.mark.parametrize("period", ["day", "week", "month", "all"])
def test_periods_preserve_full_report(tmp_path, period):
    from codex_time.overview_read import load_overview

    store = prepared(tmp_path)
    selected = None if period == "all" else date(2026, 10, 6)
    ledger = load_overview(store, period=period, selected_date=selected)
    assert overview_report(ledger, period=period, selected_date=selected) == overview_report(
        store.load(), period=period, selected_date=selected
    )
