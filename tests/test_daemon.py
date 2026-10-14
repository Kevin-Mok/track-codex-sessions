from pathlib import Path

import pytest

from codex_time.daemon import runtime_status
from codex_time.storage import Store


@pytest.mark.parametrize(
    "heartbeat", ["2026-10-06T16:00:00", "wrong", "2099-01-01T00:00:00+00:00", None, 42]
)
def test_corrupt_or_stale_heartbeat_is_not_running(tmp_path: Path, heartbeat: object) -> None:
    store = Store(tmp_path / "data", tmp_path / "state")
    with store.writer():
        store.runtime_save({"heartbeat": heartbeat})
    assert runtime_status(store)["daemon"] == "stopped_or_stale"


def test_heartbeat_accepts_minute_cadence(tmp_path: Path) -> None:
    from datetime import UTC, datetime, timedelta

    store = Store(tmp_path / "data", tmp_path / "state")
    with store.writer():
        store.runtime_save({"heartbeat": (datetime.now(UTC) - timedelta(seconds=65)).isoformat()})
    assert runtime_status(store)["daemon"] == "running"


def test_daemon_default_sampling_is_minute() -> None:
    from codex_time.cli import parser

    assert parser().parse_args(["daemon"]).sample_seconds == 60


async def test_unknown_runtime_cwd_does_not_overwrite_new_rollout_cwd(
    tmp_path, monkeypatch
) -> None:
    import asyncio
    import json
    from datetime import UTC, datetime

    from codex_time import daemon
    from codex_time.models import Observation

    home = tmp_path / "home"
    path = home / "sessions" / "one.jsonl"
    path.parent.mkdir(parents=True)
    at = datetime.now(UTC)
    path.write_text(
        json.dumps(
            {
                "timestamp": at.isoformat(),
                "type": "session_meta",
                "payload": {"id": "one", "cwd": "/fixture/new", "source": "cli"},
            }
        )
        + "\n"
    )
    stop = asyncio.Event()

    class Client:
        diagnostic = None

        def __init__(self, *args, **kwargs):
            pass

        async def poll(self):
            stop.set()
            return [Observation(session_id="one", state="unknown", at=at, cwd="/fixture/old")]

        async def close(self):
            pass

    monkeypatch.setattr(daemon, "LiveClient", Client)
    store = Store(tmp_path / "data", tmp_path / "state")
    await daemon.run_daemon(store, home, None, stop, sample_seconds=1)
    assert store.load().sessions["one"].cwd == "/fixture/new"


async def test_initial_name_index_pages_complete_before_minute_sleep(tmp_path, monkeypatch) -> None:
    import asyncio

    from codex_time import daemon

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    clock = [0.0]
    reads = []

    class Client:
        diagnostic = None

        def __init__(self, *args, **kwargs):
            pass

        async def poll(self):
            return []

        async def close(self):
            pass

    def metadata(*args, index_state, **kwargs):
        reads.append(clock[0])
        index_state["pending"] = len(reads) < 3
        if len(reads) == 3:
            stop.set()
        return index_state["pending"]

    async def advance(tasks, *, timeout, **kwargs):
        clock[0] += timeout
        await asyncio.sleep(0)
        return set(), set(tasks)

    monkeypatch.setattr(loop, "time", lambda: clock[0])
    monkeypatch.setattr(daemon.asyncio, "wait", advance)
    monkeypatch.setattr(daemon, "LiveClient", Client)
    monkeypatch.setattr(daemon, "refresh_metadata", metadata)
    monkeypatch.setattr(daemon, "refresh_due", lambda _: False)
    await daemon.run_daemon(
        Store(tmp_path / "data", tmp_path / "state"),
        tmp_path / "home",
        None,
        stop,
        sample_seconds=60,
    )
    assert len(reads) == 3
    assert max(reads) < 1  # Historical table wraps must not end or extend name bootstrap.
