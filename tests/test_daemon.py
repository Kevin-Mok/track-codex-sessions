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


@pytest.mark.parametrize("observed", [False, True])
async def test_warm_notifications_batch_at_anchored_minute_and_reopen_exact_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, observed: bool
) -> None:
    import asyncio
    import json
    from collections import deque
    from datetime import UTC, datetime, timedelta

    from codex_time import daemon
    from codex_time.models import (
        Ledger,
        ModelContext,
        Observation,
        Session,
        Span,
        TokenCounts,
        Turn,
        UsageObservation,
    )

    at = datetime(2026, 10, 14, 15, tzinfo=UTC)
    history_at = at - timedelta(days=1)
    historical = Session(
        id="historical",
        cwd="/fixture/history",
        title="Recorded history",
        created=history_at,
        updated=history_at + timedelta(seconds=20),
        turns={
            "closed": Turn(
                id="closed",
                cwd="/fixture/history",
                start=history_at + timedelta(microseconds=125000),
                end=history_at + timedelta(seconds=20, microseconds=875000),
                waits=[
                    Span(
                        start=history_at + timedelta(seconds=4, microseconds=250000),
                        end=history_at + timedelta(seconds=6, microseconds=500000),
                    )
                ],
                model_contexts=[
                    ModelContext(at=history_at, model_id="gpt-4.1", reasoning_level="high")
                ],
            )
        },
    )
    child = Session(
        id="child",
        cwd="/fixture/history",
        created=history_at,
        updated=history_at,
        parent_id="historical",
        is_child=True,
    )
    old_usage = UsageObservation(
        id="old-usage",
        session_id="historical",
        at=history_at,
        cumulative=TokenCounts(input_tokens=41, output_tokens=2, total_tokens=43),
    )
    store = Store(tmp_path / "data", tmp_path / "state")
    with store.writer():
        store.save(
            Ledger(
                sessions={historical.id: historical, child.id: child},
                usage_observations=[old_usage],
            )
        )
    home = tmp_path / "home"
    path = home / "sessions" / "live.jsonl"
    path.parent.mkdir(parents=True)

    def event(seconds: float, kind: str, payload: dict[str, object]) -> str:
        return (
            json.dumps(
                {
                    "timestamp": (at + timedelta(seconds=seconds)).isoformat(),
                    "type": kind,
                    "payload": payload,
                }
            )
            + "\n"
        )

    path.write_text(
        event(0, "session_meta", {"id": "live", "cwd": "/fixture/live", "source": "cli"})
        + event(0.125, "event_msg", {"type": "task_started", "turn_id": "precise"})
        + event(
            0.125,
            "turn_context",
            {"turn_id": "precise", "cwd": "/fixture/live", "model": "gpt-4.1", "effort": "medium"},
        )
    )
    large = 9_007_199_254_741_001

    def tokens(seconds: float, extra: int) -> str:
        cumulative = {
            "input_tokens": large + extra,
            "cached_input_tokens": 20 + bool(extra),
            "output_tokens": 17 + (2 if extra else 0),
            "reasoning_output_tokens": 6 + bool(extra),
            "total_tokens": large + extra + 17 + (2 if extra else 0),
        }
        last = (
            {
                "input_tokens": 7,
                "cached_input_tokens": 1,
                "output_tokens": 2,
                "reasoning_output_tokens": 1,
                "total_tokens": 9,
            }
            if extra
            else cumulative
        )
        return event(
            seconds,
            "event_msg",
            {
                "type": "token_count",
                "info": {
                    "total_token_usage": cumulative,
                    "last_token_usage": last,
                },
            },
        )

    notifications: deque[tuple[float, str]] = deque()
    for second in range(5, 126):
        body = event(
            second + 0.125,
            "response_item",
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "synthetic ignored body"}],
            },
        )
        if second == 10:
            body += event(
                10.25,
                "response_item",
                {"type": "function_call", "name": "request_user_input", "call_id": "known-wait"},
            )
        if second == 20:
            body += event(
                20.75, "response_item", {"type": "function_call_output", "call_id": "known-wait"}
            )
        if second == 30:
            body += tokens(30.5, 0)
        notifications.append((float(second), body))
    notifications.append(
        (
            126.5,
            event(126.375, "event_msg", {"type": "task_complete", "turn_id": "precise"})
            + tokens(126.625, 7),
        )
    )
    clock, waits, scans, writes = [0.0], [], [], []
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    real_scan = daemon.RolloutReader.scan_paths
    real_write = Store._write

    class Watcher:
        fd = None
        available = True
        needs_reconciliation = False

        def __init__(self, *args, **kwargs):
            pass

        def drain(self):
            changed = False
            while notifications and notifications[0][0] <= clock[0]:
                _, body = notifications.popleft()
                with path.open("a") as output:
                    output.write(body)
                changed = True
            return ([path] if changed else []), False

        def close(self):
            pass

    class Client:
        diagnostic = None

        def __init__(self, *args, **kwargs):
            pass

        async def poll(self):
            if observed:
                return [
                    Observation(
                        session_id="live",
                        state="idle",
                        at=at + timedelta(seconds=clock[0]),
                        cwd="/fixture/live",
                        turn_id="precise",
                    )
                ]
            return []

        async def close(self):
            pass

    async def prepared(*args):
        return True

    def scan(reader, ledger, paths, **kwargs):
        result = real_scan(reader, ledger, paths, **kwargs)
        if reader._records and clock[0] >= 5:
            scans.append(clock[0])
        return result

    def write(owner, destination, value):
        if destination.parent == store.root / "sessions" and clock[0] >= 5:
            writes.append(clock[0])
        return real_write(owner, destination, value)

    async def advance(tasks, *, timeout, **kwargs):
        waits.append((clock[0], timeout))
        assert len(waits) <= 160, "deferred notifications must not cause a 100ms busy loop"
        next_event = notifications[0][0] if notifications else 127.0
        clock[0] = min(clock[0] + timeout, next_event, 127.0)
        if clock[0] >= 127:
            stop.set()
        await asyncio.sleep(0)
        return set(), set(tasks)

    with monkeypatch.context() as patch:
        patch.setattr(loop, "time", lambda: clock[0])
        patch.setattr(daemon.asyncio, "wait", advance)
        patch.setattr(daemon, "ChangeWatcher", Watcher)
        patch.setattr(daemon, "LiveClient", Client)
        patch.setattr(daemon, "prepare_store", prepared)
        patch.setattr(daemon, "refresh_due", lambda _: False)
        patch.setattr(daemon.RolloutReader, "scan_paths", scan)
        patch.setattr(Store, "_write", write)
        await daemon.run_daemon(store, home, None, stop, sample_seconds=60)
    assert len(scans) <= 2, f"warm events were decoded before their minute batch: {scans}"
    assert len(writes) <= 2, f"warm events repeatedly saved whole sessions: {writes}"
    assert scans and 5 < scans[0] <= 65
    assert len(scans) == 2 and scans[1] <= 126  # Continuous events cannot reset the first deadline.
    before_reopen = store.load()
    assert before_reopen.sessions["live"].turns["precise"].end is None
    # SIGTERM-style stop leaves the deferred source tail unread, not falsely checkpointed.
    restored = daemon.import_history(store, home)
    assert restored.sessions["historical"] == historical
    assert restored.sessions["child"] == child
    turn = restored.sessions["live"].turns["precise"]
    assert turn.start == at + timedelta(microseconds=125000)
    assert turn.end == at + timedelta(seconds=126, microseconds=375000)
    assert turn.waits == [
        Span(
            start=at + timedelta(seconds=10, microseconds=250000),
            end=at + timedelta(seconds=20, microseconds=750000),
        )
    ]
    assert turn.model_contexts[0].model_id == "gpt-4.1"
    assert old_usage in restored.usage_observations
    live_usage = [item for item in restored.usage_observations if item.session_id == "live"]
    assert len(live_usage) == 2
    assert live_usage[-1].cumulative.input_tokens == large + 7
    assert live_usage[-1].delta.input_tokens == 7
    assert sum(item.delta.input_tokens for item in live_usage) == large + 7


async def test_readable_notification_fd_does_not_spin_callbacks_during_coalescing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real level-triggered inotify must be disarmed while the daemon is awaiting.

    A fake watcher cannot expose this selector behavior. One real file event is
    enough: leaving its fd registered during the 100ms coalescing sleep invokes
    the callback thousands of times before the pending bytes are drained.
    """
    import asyncio
    import json
    from datetime import UTC, datetime

    from codex_time import daemon

    home = tmp_path / "home"
    source = home / "sessions" / "one.jsonl"
    source.parent.mkdir(parents=True)
    probe = daemon.ChangeWatcher(home)
    if probe.fd is None:
        probe.close()
        pytest.skip("native inotify is unavailable")
    probe.close()
    stop, registered = asyncio.Event(), asyncio.Event()
    loop = asyncio.get_running_loop()
    actual_add_reader = loop.add_reader
    callbacks = [0]

    class Client:
        diagnostic = None

        def __init__(self, *args, **kwargs):
            pass

        async def poll(self):
            return []

        async def close(self):
            pass

    async def prepared(*args):
        return True

    def add_reader(fd, callback, *args):
        def counted():
            callbacks[0] += 1
            callback(*args)

        registered.set()
        return actual_add_reader(fd, counted)

    with monkeypatch.context() as patch:
        patch.setattr(loop, "add_reader", add_reader)
        patch.setattr(daemon, "LiveClient", Client)
        patch.setattr(daemon, "prepare_store", prepared)
        patch.setattr(daemon, "refresh_due", lambda _: False)
        task = asyncio.create_task(
            daemon.run_daemon(
                Store(tmp_path / "data", tmp_path / "state"),
                home,
                None,
                stop,
                sample_seconds=60,
            )
        )
        try:
            await asyncio.wait_for(registered.wait(), timeout=2)
            source.write_text(
                json.dumps(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "type": "session_meta",
                        "payload": {"id": "one", "cwd": "/fixture", "source": "cli"},
                    }
                )
                + "\n"
            )
            await asyncio.sleep(0.25)
        finally:
            stop.set()
            await asyncio.wait_for(task, timeout=2)
    assert callbacks[0] < 20, (
        f"readable source fd invoked {callbacks[0]} callbacks during one coalescing event; "
        "disarm the level-triggered reader until its queued bytes can be drained"
    )


async def test_notification_during_async_poll_is_drained_before_waiting_another_minute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A one-shot real fd isolates wake retention from level-triggered repetition."""
    import asyncio
    import json
    import os
    from datetime import UTC, datetime

    from codex_time import daemon

    home = tmp_path / "home"
    source = home / "sessions" / "one.jsonl"
    source.parent.mkdir(parents=True)
    read_fd, write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
    stop, notified = asyncio.Event(), asyncio.Event()
    loop = asyncio.get_running_loop()
    real_add_reader, real_sleep = loop.add_reader, asyncio.sleep
    clock, drained = [0.0], []

    class Watcher:
        fd = read_fd
        available = True
        needs_reconciliation = False

        def __init__(self, *args, **kwargs):
            pass

        def drain(self):
            try:
                value = os.read(read_fd, 1024)
            except BlockingIOError:
                value = b""
            if value:
                drained.append(clock[0])
                stop.set()
            return ([source] if value else []), False

        def close(self):
            os.close(read_fd)

    class Client:
        diagnostic = None

        def __init__(self, *args, **kwargs):
            self.first = True

        async def poll(self):
            if self.first:
                self.first = False
                source.write_text(
                    json.dumps(
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "type": "session_meta",
                            "payload": {"id": "one", "cwd": "/fixture", "source": "cli"},
                        }
                    )
                    + "\n"
                )
                os.write(write_fd, b"changed")
                await notified.wait()  # A callback arrives while poll() is still awaiting.
            return []

        async def close(self):
            pass

    async def prepared(*args):
        return True

    def add_reader(fd, callback, *args):
        def one_shot():
            loop.remove_reader(fd)
            callback(*args)
            notified.set()

        return real_add_reader(fd, one_shot)

    async def sleep(delay, *args, **kwargs):
        clock[0] += delay
        await real_sleep(0)

    async def advance(tasks, *, timeout, **kwargs):
        await real_sleep(0)
        await real_sleep(0)
        done = {task for task in tasks if task.done()}
        if not done:
            clock[0] += timeout
            assert clock[0] <= 120, "notification wake was never serviced"
        return done, set(tasks) - done

    store = Store(tmp_path / "data", tmp_path / "state")
    try:
        with monkeypatch.context() as patch:
            patch.setattr(loop, "time", lambda: clock[0])
            patch.setattr(loop, "add_reader", add_reader)
            patch.setattr(daemon.asyncio, "sleep", sleep)
            patch.setattr(daemon.asyncio, "wait", advance)
            patch.setattr(daemon, "ChangeWatcher", Watcher)
            patch.setattr(daemon, "LiveClient", Client)
            patch.setattr(daemon, "prepare_store", prepared)
            patch.setattr(daemon, "refresh_due", lambda _: False)
            await daemon.run_daemon(store, home, None, stop, sample_seconds=60)
    finally:
        os.close(write_fd)
    assert drained and drained[0] < 1, f"poll-time notification was only drained at {drained}"
    assert daemon.import_history(store, home).sessions["one"].cwd == "/fixture"
