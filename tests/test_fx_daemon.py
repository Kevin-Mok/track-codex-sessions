"""A slow or broken currency refresh must not stop session tracking."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from codex_time import daemon
from codex_time.fx import FXSnapshot
from codex_time.storage import Store


async def test_slow_fx_runs_beside_tracking_and_is_cancelled_on_stop(tmp_path, monkeypatch):
    stop = asyncio.Event()
    started = asyncio.Event()
    cancelled = asyncio.Event()
    calls = []

    async def refresh(runtime):
        calls.append(runtime)
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    class Client:
        diagnostic = None

        def __init__(self, *args):
            self.polls = 0

        async def poll(self):
            self.polls += 1
            if self.polls == 2:
                stop.set()
            return []

        async def close(self):
            pass

    monkeypatch.setattr(daemon, "refresh_fx", refresh, raising=False)
    monkeypatch.setattr(daemon, "LiveClient", Client)
    store = Store(tmp_path / "data", tmp_path / "state")
    await asyncio.wait_for(daemon.run_daemon(store, tmp_path / "codex", None, stop), 3)
    assert started.is_set() and cancelled.is_set()
    assert calls == [store.runtime]
    assert store.load().version == 4
    assert store.runtime_read()["heartbeat"] is None


async def test_fx_cache_write_failure_does_not_break_or_retry_each_iteration(tmp_path, monkeypatch):
    stop = asyncio.Event()
    calls = []

    async def refresh(runtime):
        calls.append(runtime)
        raise OSError("synthetic cache permission failure")

    class Client:
        diagnostic = None

        def __init__(self, *args):
            self.polls = 0

        async def poll(self):
            self.polls += 1
            if self.polls == 3:
                stop.set()
            return []

        async def close(self):
            pass

    monkeypatch.setattr(daemon, "refresh_fx", refresh, raising=False)
    monkeypatch.setattr(daemon, "LiveClient", Client)
    store = Store(tmp_path / "data", tmp_path / "state")
    await asyncio.wait_for(daemon.run_daemon(store, tmp_path / "codex", None, stop), 4)
    assert len(calls) == 1
    assert any("FX cache" in d for d in store.load().diagnostics)


async def test_successful_cached_check_does_not_schedule_network(tmp_path, monkeypatch):
    stop = asyncio.Event()

    async def refresh(runtime):
        raise AssertionError("cached successful check must wait 24 hours")

    class Client:
        diagnostic = None

        def __init__(self, *args):
            pass

        async def poll(self):
            stop.set()
            return []

        async def close(self):
            pass

    monkeypatch.setattr(daemon, "refresh_fx", refresh, raising=False)
    monkeypatch.setattr(daemon, "LiveClient", Client)
    store = Store(tmp_path / "data", tmp_path / "state")
    store.runtime.mkdir()
    (store.runtime / "fx-usd-cad.json").write_text(
        FXSnapshot(last_success=datetime.now(UTC)).model_dump_json()
    )
    await daemon.run_daemon(store, tmp_path / "codex", None, stop)


def test_import_history_reports_progress_on_stderr(tmp_path: Path, capsys):
    store = Store(tmp_path / "data", tmp_path / "state")
    daemon.import_history(store, tmp_path / "codex")
    output = capsys.readouterr()
    assert not output.out
    assert "rollout" in output.err.lower()
