"""Overview's disposable report cache stays fresh without rereading ledger evidence."""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest
from test_overview import BASE, quota, sample_ledger

from codex_time.cli import main
from codex_time.models import Ledger
from codex_time.storage import Store

SELECTED = date(2026, 10, 6)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    result = Store(tmp_path / "data", tmp_path / "state")
    result.root.mkdir()
    (result.root / "ledger.json").write_text(sample_ledger().model_dump_json())
    return result


def cached(store: Store, **options: object) -> dict:
    from codex_time.overview_cache import cached_overview

    return cached_overview(store, **({"selected_date": SELECTED} | options))


def test_repeated_cli_uses_cached_report_without_load_or_compute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, runtime = tmp_path / "data", tmp_path / "state"
    root.mkdir()
    (root / "ledger.json").write_text(Ledger().model_dump_json())
    monkeypatch.setattr(sys, "argv", [
        "codex-time", "--data-dir", str(root), "--state-dir", str(runtime),
        "overview", "day", "--date", "2026-10-06", "--json",
    ])
    assert main() == 0
    first = json.loads(capsys.readouterr().out)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("unchanged overview must not reload or recompute")

    monkeypatch.setattr(Store, "load", forbidden)
    monkeypatch.setattr("codex_time.overview.overview_report", forbidden)
    monkeypatch.setattr("codex_time.overview_cache.overview_report", forbidden)
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == first


def test_hit_keeps_complete_report_and_never_reads_authoritative_contents(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = cached(store)
    original = Path.read_bytes

    def read(path: Path) -> bytes:
        assert not path.is_relative_to(store.root)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    assert cached(Store(store.root, store.runtime)) == expected


def test_cache_is_private_and_never_changes_durable_inputs(store: Store) -> None:
    before = {p: p.read_bytes() for p in store.root.iterdir()}
    cached(store)
    assert {p: p.read_bytes() for p in store.root.iterdir()} == before
    assert (store.runtime / "overview-report.json").stat().st_mode & 0o777 == 0o600
    assert store.runtime.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("replacement", [False, True])
def test_same_size_and_mtime_session_source_change_invalidates(
    store: Store, replacement: bool
) -> None:
    assert cached(store)["model_totals"]["rows"][0]["model_id"] == "A"
    path = store.root / "ledger.json"
    stamp = path.stat()
    changed = path.read_text().replace('"model_id":"A"', '"model_id":"B"')
    destination = path.with_suffix(".replacement") if replacement else path
    destination.write_text(changed)
    os.utime(destination, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    if replacement:
        destination.replace(path)
    assert path.stat().st_size == stamp.st_size
    assert path.stat().st_mtime_ns == stamp.st_mtime_ns
    assert cached(store)["model_totals"]["rows"][0]["model_id"] == "B"


def test_quota_and_usage_journal_updates_change_report(store: Store) -> None:
    from codex_time.models import TokenCounts, UsageObservation

    first = cached(store)
    (store.root / "quota-observations.jsonl").write_text(quota(660, 20).model_dump_json() + "\n")
    assert cached(store)["allowance"]["latest"]["used_percent"] == 20
    usage = UsageObservation(
        id="new", session_id="root", at=BASE, model_id="gpt-5",
        delta=TokenCounts(input_tokens=100, total_tokens=100),
    )
    (store.root / "usage-observations.jsonl").write_text(usage.model_dump_json() + "\n")
    assert cached(store)["token_usage"]["usage"] != first["token_usage"]["usage"]


def test_partitioned_session_change_without_layout_revision_invalidates(store: Store) -> None:
    from codex_time.incremental_storage import session_path

    ledger = sample_ledger()
    (store.root / "layout.json").write_text(json.dumps({"version": 1, "revision": "same"}))
    (store.root / "sessions").mkdir()
    for sid, session in ledger.sessions.items():
        session_path(store.root, sid).write_text(session.model_dump_json())
    first = cached(store)
    session = ledger.sessions["root"]
    session.turns["first"].end = BASE + timedelta(seconds=60)
    session.turns["first"].waits = []
    session_path(store.root, "root").write_text(session.model_dump_json())
    assert cached(store)["model_totals"] != first["model_totals"]


@pytest.mark.parametrize("name", [
    "layout.json", "ledger.json", "quota-observations.jsonl", "usage-observations.jsonl",
    "legacy-quota-observations.jsonl", "legacy-usage-observations.jsonl",
])
def test_every_durable_source_identity_is_tracked(store: Store, name: str) -> None:
    from codex_time.overview_cache import source_identity

    before = source_identity(store)
    with (store.root / name).open("a") as output:
        output.write(" ")
    assert source_identity(store) != before


@pytest.mark.parametrize("options", [
    {"period": "week"}, {"selected_date": date(2026, 10, 7)},
    {"timezone_name": "UTC"}, {"window_minutes": 300}, {"limit_id": "other"},
    {"max_gap_seconds": 120}, {"period": "all", "selected_date": None},
])
def test_semantic_options_invalidate_cache(
    store: Store, monkeypatch: pytest.MonkeyPatch, options: dict
) -> None:
    import codex_time.overview_cache as module

    cached(store)
    spy = Mock(wraps=module.overview_report)
    monkeypatch.setattr(module, "overview_report", spy)
    cached(store, **options)
    assert spy.call_count == 1


@pytest.mark.parametrize("corruption", [
    "invalid", "version", "no_version", "missing", "nested", "extra", "non_finite",
])
def test_corrupt_or_incompatible_cache_rebuilds(store: Store, corruption: str) -> None:
    expected = cached(store)
    path = store.runtime / "overview-report.json"
    data = json.loads(path.read_bytes())
    if corruption == "version":
        data["version"] = 2
    elif corruption == "no_version":
        del data["version"]
    elif corruption == "missing":
        del data["report"]["model_totals"]["rows"]
    elif corruption == "nested":
        data["report"]["reasoning"]["rows"][0]["working_microseconds"] = "wrong"
    elif corruption == "extra":
        data["unexpected"] = True
    elif corruption == "non_finite":
        data["report"]["model_totals"]["rows"][0]["percentage"] = float("nan")
    path.write_text("{" if corruption == "invalid" else json.dumps(data))
    assert cached(store) == expected
    assert json.loads(path.read_bytes())["version"] == 1


def test_cache_write_failure_does_not_prevent_report(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    def denied(*args: object) -> None:
        raise PermissionError("cache unavailable")

    monkeypatch.setattr(store, "_write", denied)
    assert cached(store)["model_totals"]["total_seconds"] == 1320
    assert not (store.runtime / "overview-report.json").exists()


def test_cache_path_unreadable_as_file_falls_back_safely(store: Store) -> None:
    (store.runtime / "overview-report.json").mkdir(parents=True)
    assert cached(store)["model_totals"]["total_seconds"] == 1320


def test_stat_failure_disables_cache_without_disabling_report(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_time.overview_cache as module

    def denied(*args: object) -> str:
        raise PermissionError("stat unavailable")

    monkeypatch.setattr(module, "source_identity", denied)
    assert cached(store)["model_totals"]["total_seconds"] == 1320
    assert not (store.runtime / "overview-report.json").exists()


def test_source_build_and_pricing_identity_changes_invalidate(
    store: Store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_time.overview_cache as module

    package = tmp_path / "package"
    package.mkdir()
    monkeypatch.setattr(module, "__file__", str(package / "overview_cache.py"))
    original = module.source_identity(store)
    (package / "accounting.py").write_text("changed code")
    changed_code = module.source_identity(store)
    assert changed_code != original
    (package / "pricing-v1.json").write_text("changed pricing")
    assert module.source_identity(store) != changed_code


def test_shared_runtime_never_reuses_another_data_root(store: Store, tmp_path: Path) -> None:
    assert cached(store)["model_totals"]["total_seconds"] == 1320
    other = Store(tmp_path / "other-data", store.runtime)
    assert cached(other)["model_totals"]["total_seconds"] == 0


def test_presentation_flags_share_cached_accounting(
    store: Store, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import codex_time.overview_cache as module

    cached(store)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("rendering must reuse complete accounting")

    monkeypatch.setattr(module, "overview_report", forbidden)
    monkeypatch.setattr(Store, "load", forbidden)
    for flags in (["--json"], ["--plain"], ["--details", "--color", "always"]):
        monkeypatch.setattr(sys, "argv", [
            "codex-time", "--data-dir", str(store.root), "--state-dir", str(store.runtime),
            "overview", "--date", SELECTED.isoformat(), *flags,
        ])
        assert main() == 0
        output = capsys.readouterr().out
        if "--json" in flags:
            assert json.loads(output)["model_totals"]["total_seconds"] == 1320
        else:
            assert "Recorded work" in output
            if "--plain" in flags:
                assert output.isascii()
            else:
                assert "Matched model mix" in output


def test_changed_source_during_build_is_not_published(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_time.overview_cache as module

    real = module.overview_report

    def raced(*args: object, **kwargs: object) -> dict:
        result = real(*args, **kwargs)
        with (store.root / "ledger.json").open("a") as output:
            output.write(" ")
        return result

    monkeypatch.setattr(module, "overview_report", raced)
    assert cached(store)["model_totals"]["total_seconds"] == 1320
    assert not (store.runtime / "overview-report.json").exists()


def test_concurrent_publishers_leave_valid_cache(store: Store) -> None:
    from codex_time.overview_cache import ReportCache

    with ThreadPoolExecutor(max_workers=4) as executor:
        reports = list(executor.map(lambda _: cached(Store(store.root, store.runtime)), range(8)))
    assert all(result == reports[0] for result in reports)
    validated = ReportCache.model_validate_json(
        (store.runtime / "overview-report.json").read_bytes()
    )
    assert validated.report == reports[0]


def test_fx_changes_recompute_cost_and_hits_refresh_age(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_time.fx as fx_module
    import codex_time.overview_cache as module
    from codex_time.fx import FXSnapshot

    snapshot = FXSnapshot(rate="1.35", observation_date=SELECTED, last_success=BASE)
    store.runtime.mkdir()
    (store.runtime / "fx-usd-cad.json").write_text(snapshot.model_dump_json())
    cached(store)
    spy = Mock(wraps=module.overview_report)
    monkeypatch.setattr(module, "overview_report", spy)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return BASE + timedelta(days=2)

    monkeypatch.setattr(fx_module, "datetime", Clock)
    hit = cached(store)
    assert hit["token_usage"]["fx"] == snapshot.metadata(BASE + timedelta(days=2))
    assert hit["token_usage"]["fx"]["status"] == "stale"
    assert spy.call_count == 0
    (store.runtime / "fx-usd-cad.json").write_text(
        snapshot.model_copy(update={"rate": Decimal("1.40")}).model_dump_json()
    )
    assert cached(store)["token_usage"]["fx"]["rate"] == "1.40"
    assert spy.call_count == 1


@pytest.mark.parametrize("period", ["day", "week", "month", "all"])
def test_implicit_today_invalidates_at_local_midnight(
    store: Store, monkeypatch: pytest.MonkeyPatch, period: str
) -> None:
    import codex_time.overview_cache as module

    current = [datetime(2026, 10, 7, 3, 59, 59, tzinfo=UTC)]

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return current[0]

    monkeypatch.setattr(module, "datetime", Clock)
    spy = Mock(wraps=module.overview_report)
    monkeypatch.setattr(module, "overview_report", spy)
    first = cached(store, selected_date=None, period=period)
    assert cached(store, selected_date=None, period=period) == first
    assert spy.call_count == 1
    current[0] += timedelta(seconds=2)
    cached(store, selected_date=None, period=period)
    assert spy.call_count == 2
