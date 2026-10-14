"""Runtime-only CAD rates, using synthetic Bank of Canada responses."""

import asyncio
import io
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Event

import pytest

BASE = datetime(2026, 10, 8, 16, tzinfo=UTC)


def bank_response(value="1.35", observed="2026-10-07"):
    return json.dumps(
        {
            "terms": {"url": "https://www.bankofcanada.ca/terms/"},
            "seriesDetail": {
                "FXUSDCAD": {
                    "label": "USD/CAD",
                    "description": "US dollar to Canadian dollar",
                    "dimension": {"key": "d", "name": "Date"},
                }
            },
            "observations": [{"d": observed, "FXUSDCAD": {"v": value}}],
        }
    ).encode()


def fake_response(monkeypatch, body=None):
    from codex_time import fx

    def open_response(url, *, timeout):
        assert "FXUSDCAD/json?recent=1" in url
        assert 0 < timeout <= 10
        return io.BytesIO(body or bank_response())

    monkeypatch.setattr(fx, "urlopen", open_response)


def test_missing_and_corrupt_fx_reads_do_not_create_or_rewrite_files(tmp_path):
    from codex_time.fx import read_fx

    runtime = tmp_path / "runtime"
    assert read_fx(runtime).rate is None and not runtime.exists()
    runtime.mkdir()
    cache = runtime / "fx-usd-cad.json"
    cache.write_text('{"version": 900, "rate": "NaN"}')
    before = cache.read_bytes()
    result = read_fx(runtime)
    assert result.rate is None and "invalid" in result.last_error.lower()
    assert cache.read_bytes() == before


async def test_success_is_exact_and_runtime_only(tmp_path, monkeypatch):
    from codex_time.fx import read_fx, refresh_fx

    fake_response(monkeypatch)
    runtime = tmp_path / "runtime"
    snapshot = await refresh_fx(runtime, now=BASE)
    assert snapshot.rate == Decimal("1.35")
    assert snapshot.observation_date == date(2026, 10, 7)
    assert snapshot.convert(Decimal("2.40")) == Decimal("3.2400")
    assert snapshot.last_success == snapshot.last_attempt == BASE
    assert read_fx(runtime) == snapshot
    payload = json.loads((runtime / "fx-usd-cad.json").read_text())
    assert payload["rate"] == "1.35"
    assert set(tmp_path.iterdir()) == {runtime}


async def test_network_failure_preserves_valid_rate_and_reports_age(tmp_path, monkeypatch):
    from codex_time import fx

    fake_response(monkeypatch)
    original = await fx.refresh_fx(tmp_path, now=BASE)

    def fail(url, *, timeout):
        raise TimeoutError("offline")

    monkeypatch.setattr(fx, "urlopen", fail)
    failed = await fx.refresh_fx(tmp_path, now=BASE + timedelta(days=2))
    assert failed.rate == original.rate and failed.observation_date == original.observation_date
    assert failed.last_success == BASE and "offline" in failed.last_error
    assert failed.metadata(BASE + timedelta(days=2))["age_days"] == 3
    assert failed.metadata(BASE + timedelta(days=2))["status"] == "stale"


async def test_success_waits_24h_and_failures_wait_1h(tmp_path, monkeypatch):
    from codex_time import fx

    fake_response(monkeypatch)
    await fx.refresh_fx(tmp_path, now=BASE)
    payload = (tmp_path / "fx-usd-cad.json").read_bytes()

    def fail(url, *, timeout):
        raise TimeoutError("offline")

    monkeypatch.setattr(fx, "urlopen", fail)
    within_day = await fx.refresh_fx(tmp_path, now=BASE + timedelta(hours=23, minutes=59))
    assert within_day.last_error is None
    assert (tmp_path / "fx-usd-cad.json").read_bytes() == payload
    failed = await fx.refresh_fx(tmp_path, now=BASE + timedelta(days=1))
    assert failed.last_error == "FX refresh failed: offline"
    retry_wait = await fx.refresh_fx(tmp_path, now=BASE + timedelta(days=1, minutes=59))
    assert retry_wait.last_attempt == failed.last_attempt
    retried = await fx.refresh_fx(tmp_path, now=BASE + timedelta(days=1, hours=1))
    assert retried.last_attempt == BASE + timedelta(days=1, hours=1)


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "not-a-rate"])
async def test_invalid_network_rates_never_replace_last_valid(tmp_path, monkeypatch, value):
    from codex_time.fx import refresh_fx

    fake_response(monkeypatch)
    await refresh_fx(tmp_path, now=BASE)
    fake_response(monkeypatch, bank_response(value))
    rejected = await refresh_fx(tmp_path, now=BASE + timedelta(days=1))
    assert rejected.rate == Decimal("1.35")
    assert rejected.last_success == BASE and rejected.last_error is not None


async def test_no_valid_rate_preserves_usd_and_makes_cad_unavailable(tmp_path, monkeypatch):
    from codex_time.fx import refresh_fx

    fake_response(monkeypatch, b'{"observations": []}')
    result = await refresh_fx(tmp_path, now=BASE)
    assert result.convert(Decimal("2.40")) is None
    assert result.rate is None and result.metadata(BASE)["status"] == "unavailable"
    assert result.last_attempt == BASE and result.last_success is None


async def test_refresh_never_blocks_event_loop_and_cancellation_cannot_write_late(
    tmp_path, monkeypatch
):
    from codex_time import fx

    fake_response(monkeypatch)
    await fx.refresh_fx(tmp_path, now=BASE)
    started, release = Event(), Event()

    def slow_response(url, *, timeout):
        started.set()
        release.wait(2)
        return io.BytesIO(bank_response("1.99"))

    monkeypatch.setattr(fx, "urlopen", slow_response)
    task = asyncio.create_task(fx.refresh_fx(tmp_path, now=BASE + timedelta(days=1)))
    try:
        for _ in range(100):
            await asyncio.sleep(0.001)
            if started.is_set():
                break
        assert started.is_set()
        assert not task.done()
        concurrent = await fx.refresh_fx(tmp_path, now=BASE + timedelta(days=1))
        assert concurrent.rate == Decimal("1.35")
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        release.set()
    await asyncio.sleep(0.02)
    assert fx.read_fx(tmp_path).rate == Decimal("1.35")


def test_fx_rejects_naive_cache_timestamps(tmp_path: Path):
    from codex_time.fx import read_fx

    path = tmp_path / "fx-usd-cad.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "rate": "1.35",
                "observation_date": "2026-10-07",
                "last_success": "2026-10-08T00:00:00",
            }
        )
    )
    assert read_fx(tmp_path).rate is None


async def test_timeout_without_message_has_an_actionable_diagnostic(tmp_path, monkeypatch):
    from codex_time import fx

    def fail(url, *, timeout):
        raise TimeoutError()

    monkeypatch.setattr(fx, "urlopen", fail)
    failed = await fx.refresh_fx(tmp_path, now=BASE)
    assert failed.last_error == "FX refresh failed: TimeoutError"
    assert failed.rate is None
