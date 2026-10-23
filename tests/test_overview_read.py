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


@pytest.mark.parametrize("alternate_quota", [False, True])
@pytest.mark.parametrize("command", ["projects", "allowance"])
@pytest.mark.parametrize("period", ["day", "week", "month"])
def test_other_period_reports_reuse_current_evidence_index(
    tmp_path, monkeypatch, capsys, command, period, alternate_quota
):
    import json
    import sys

    from codex_time import cli
    from codex_time.burn import burn_report
    from codex_time.fx import read_fx
    from codex_time.reporting import daily_report

    store = prepared(tmp_path)
    quota_options = {"limit_id": "other", "window_minutes": 300} if alternate_quota else {}
    if alternate_quota:
        with (store.root / "quota-observations.jsonl").open("a") as out:
            for seconds, used in [(0, 20), (300, 21)]:
                out.write(quota(seconds, used).model_copy(update=quota_options).model_dump_json()
                          + "\n")
        with IndexedStore(store.root, store.runtime):
            pass
    ledger = store.load()
    options = {"period": period, "selected_date": date(2026, 10, 6)}
    expected = (
        daily_report(ledger, fx=read_fx(store.runtime), **options)
        if command == "projects"
        else burn_report(ledger, **options, **quota_options)
    )
    extra = (
        ["--limit-id", "other", "--window-minutes", "300"]
        if alternate_quota and command == "allowance" else []
    )
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert path.suffix != ".jsonl", "report reread indexed historical evidence"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    monkeypatch.setattr(
        sys, "argv",
        ["codex-time", "--data-dir", str(store.root), "--state-dir", str(store.runtime),
         command, period, "--date", "2026-10-06", "--json", *extra],
    )
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out) == expected


@pytest.mark.parametrize("command", ["projects", "allowance"])
@pytest.mark.parametrize("damage", ["missing", "corrupt", "stale", "schema", "invalid-row"])
def test_period_command_fallback_and_options(tmp_path, monkeypatch, capsys, command, damage):
    import json
    import sys

    from codex_time import cli
    from codex_time.burn import burn_report
    from codex_time.fx import read_fx
    from codex_time.reporting import daily_report

    store = prepared(tmp_path)
    index = store.runtime / "index.sqlite"
    if damage == "missing":
        index.unlink()
    elif damage == "corrupt":
        index.write_bytes(b"invalid database")
    elif damage == "stale":
        with (store.root / "quota-observations.jsonl").open("a") as out:
            out.write(quota(700, 18).model_dump_json() + "\n")
    else:
        with sqlite3.connect(index) as db:
            if damage == "schema":
                db.execute("DROP TABLE usage")
            else:
                db.execute("UPDATE usage SET body='{}' WHERE id='0'")
    options = {"period": "week", "selected_date": date(2026, 10, 6), "timezone_name": "UTC"}
    extra = (
        ["--cwd", "/one", "--archive", "active", "--session", "root"]
        if command == "projects"
        else ["--limit-id", "codex", "--window-minutes", "10080", "--max-gap-seconds", "300"]
    )
    ledger = store.load()
    expected = (
        daily_report(ledger, fx=read_fx(store.runtime), cwd="/one", archive="active",
                     session_id="root", **options)
        if command == "projects"
        else burn_report(ledger, max_gap_seconds=300, **options)
    )
    monkeypatch.setattr(
        sys, "argv",
        ["codex-time", "--data-dir", str(store.root), "--state-dir", str(store.runtime),
         "--timezone", "UTC", command, "week", "--date", "2026-10-06", "--json", *extra],
    )
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out) == expected


@pytest.mark.parametrize("command", ["projects", "allowance"])
@pytest.mark.parametrize(
    "period,before",
    [
        ("day", "2026-10-07T03:59:59+00:00"),
        ("week", "2026-10-12T03:59:59+00:00"),
        ("month", "2026-11-01T03:59:59+00:00"),
    ],
)
def test_default_period_survives_calendar_boundary(
    tmp_path, monkeypatch, capsys, command, period, before
):
    import json
    import sys
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from codex_time import burn, cli, overview_read, periods, reporting
    from codex_time.fx import read_fx

    before = datetime.fromisoformat(before)
    after = before + timedelta(seconds=2)
    selected = before.astimezone(ZoneInfo("America/Toronto")).date()
    store = prepared(tmp_path)
    with (store.root / "usage-observations.jsonl").open("a") as output:
        for name, at, tokens in [("before", before, 101), ("after", after, 303)]:
            observation = UsageObservation(
                id=name, session_id="root", at=at, cwd="/one", model_id="gpt-4.1",
                delta=TokenCounts(input_tokens=tokens, output_tokens=1),
            )
            output.write(observation.model_dump_json() + "\n")
    with IndexedStore(store.root, store.runtime):
        pass
    full = store.load()
    expected = (
        reporting.daily_report(full, period=period, selected_date=selected,
                               fx=read_fx(store.runtime))
        if command == "projects"
        else burn.burn_report(full, period=period, selected_date=selected)
    )

    class Before(datetime):
        @classmethod
        def now(cls, tz=None):
            return before.astimezone(tz) if tz else before.replace(tzinfo=None)

    class After(datetime):
        @classmethod
        def now(cls, tz=None):
            return after.astimezone(tz) if tz else after.replace(tzinfo=None)

    for module in (periods, reporting, burn):
        monkeypatch.setattr(module, "datetime", Before)
    monkeypatch.setattr(cli, "datetime", Before, raising=False)
    original = overview_read.load_overview

    def crossing(*args, **kwargs):
        result = original(*args, **kwargs)
        for module in (periods, reporting, burn):
            monkeypatch.setattr(module, "datetime", After)
        return result

    monkeypatch.setattr(cli, "load_overview", crossing)
    monkeypatch.setattr(
        sys, "argv",
        ["codex-time", "--data-dir", str(store.root), "--state-dir", str(store.runtime),
         command, period, "--json"],
    )
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out) == expected
