"""Cold initialization runs outside the live daemon without losing evidence."""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from codex_time.models import Ledger, Session, Span, Turn
from codex_time.storage import Store


async def test_actual_bootstrap_migrates_with_parity_and_idempotent_restart(
    tmp_path: Path, monkeypatch, capfd
) -> None:
    from codex_time.bootstrap import prepare_store

    monkeypatch.setenv("CLI_PLAIN", "1")
    store = Store(tmp_path / "data", tmp_path / "runtime")
    at = datetime(2026, 10, 14, tzinfo=UTC)
    before = Ledger(
        sessions={
            "one": Session(
                id="one",
                cwd="/sanitized",
                created=at,
                updated=at,
                turns={
                    "turn": Turn(
                        id="turn",
                        cwd="/sanitized",
                        start=at,
                        end=at + timedelta(seconds=60),
                        waits=[
                            Span(
                                start=at + timedelta(seconds=2.125),
                                end=at + timedelta(seconds=7.25),
                            )
                        ],
                        sampling_uncertainty_seconds=60,
                    )
                },
            )
        }
    )
    with store.writer():
        store.save(before)
    processes = []
    create = asyncio.create_subprocess_exec

    async def capture(*args, **kwargs):
        process = await create(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    assert await prepare_store(store, asyncio.Event()) is True
    assert Store(store.root, store.runtime).load() == before
    assert (store.root / "layout.json").exists()
    stamps = {
        p: (p.stat().st_mtime_ns, p.read_bytes()) for p in store.root.rglob("*") if p.is_file()
    }
    assert await prepare_store(store, asyncio.Event()) is True
    assert Store(store.root, store.runtime).load() == before
    assert all((p.stat().st_mtime_ns, p.read_bytes()) == stamp for p, stamp in stamps.items())
    assert len(processes) == 2
    assert all(process.pid != os.getpid() and process.returncode == 0 for process in processes)
    assert capfd.readouterr().err.isascii()


@pytest.mark.parametrize("action", ["stop", "cancel"])
async def test_stop_or_cancel_reaps_bootstrap_and_releases_writer_lock(
    tmp_path: Path, monkeypatch, action: str
) -> None:
    from codex_time.bootstrap import prepare_store

    store = Store(tmp_path / "data", tmp_path / "state")
    ready = tmp_path / "child-ready"
    create = asyncio.create_subprocess_exec
    processes = []
    code = (
        "import time;from pathlib import Path;from codex_time.storage import Store\n"
        f"with Store(Path({str(store.root)!r}),Path({str(store.runtime)!r})).writer():\n"
        f"    Path({str(ready)!r}).write_text('writer acquired')\n"
        "    time.sleep(60)\n"
    )

    async def slow_child(*args, **kwargs):
        assert args[1:3] == ("-m", "codex_time.bootstrap")
        process = await create(sys.executable, "-c", code)
        processes.append(process)
        return process

    async def wait_ready() -> None:
        while not ready.exists():
            await asyncio.sleep(0.01)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_child)
    stop = asyncio.Event()
    task = asyncio.create_task(prepare_store(store, stop))
    try:
        await asyncio.wait_for(wait_ready(), 3)
        if action == "stop":
            stop.set()
            assert await asyncio.wait_for(task, 1) is False
        else:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert processes[0].returncode is not None
        with store.writer():
            pass
    finally:
        if not task.done():
            task.cancel()
        for process in processes:
            if process.returncode is None:
                process.kill()
            await process.wait()


async def test_failed_bootstrap_reports_failure_without_replacing_evidence(tmp_path: Path) -> None:
    from codex_time.bootstrap import prepare_store
    from codex_time.storage import StoreError

    store = Store(tmp_path / "data", tmp_path / "state")
    store.root.mkdir()
    original = b"not a valid ledger; preserve for recovery"
    (store.root / "ledger.json").write_bytes(original)
    with pytest.raises(StoreError, match="bootstrap failed"):
        await prepare_store(store, asyncio.Event())
    assert (store.root / "ledger.json").read_bytes() == original
    assert not (store.root / "layout.json").exists()
    with store.writer():
        pass


async def test_cancellation_during_launch_obtains_and_reaps_the_child(
    tmp_path: Path, monkeypatch
) -> None:
    from codex_time.bootstrap import prepare_store

    store = Store(tmp_path / "data", tmp_path / "state")
    launched = asyncio.Event()
    return_handle = asyncio.Event()
    processes = []
    create = asyncio.create_subprocess_exec

    async def delayed_handle(*args, **kwargs):
        process = await create(sys.executable, "-c", "import time;time.sleep(60)")
        processes.append(process)
        launched.set()
        await return_handle.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_handle)
    task = asyncio.create_task(prepare_store(store, asyncio.Event()))
    try:
        await asyncio.wait_for(launched.wait(), 3)
        task.cancel()
        return_handle.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 1)
        assert processes[0].returncode is not None
        with store.writer():
            pass
    finally:
        return_handle.set()
        if not task.done():
            task.cancel()
        for process in processes:
            if process.returncode is None:
                process.kill()
            await process.wait()


async def test_already_stopped_daemon_does_not_launch_child(tmp_path: Path, monkeypatch) -> None:
    from codex_time.bootstrap import prepare_store

    async def unexpected_launch(*args, **kwargs):
        raise AssertionError("a stopped daemon must not start migration")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", unexpected_launch)
    stop = asyncio.Event()
    stop.set()
    assert await prepare_store(Store(tmp_path / "data", tmp_path / "state"), stop) is False
    assert not (tmp_path / "data").exists()
