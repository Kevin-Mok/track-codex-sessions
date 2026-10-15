"""Single-writer observation loop, independent of the terminal UI."""

import asyncio
import os
import signal
import sys
from collections import deque
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from codex_time.bootstrap import prepare_store
from codex_time.cadence import SAMPLE_SECONDS, is_fresh
from codex_time.changes import ChangeWatcher
from codex_time.fx import FXSnapshot, read_fx, refresh_due, refresh_fx
from codex_time.incremental_storage import IndexedStore
from codex_time.ingest import RolloutReader, diagnostic
from codex_time.live import LiveClient
from codex_time.metadata import current_rollouts, refresh_metadata
from codex_time.models import Ledger, Observation
from codex_time.observer import Observer
from codex_time.reconciliation import Reconciliation, ScanScheduler
from codex_time.storage import Store


def observations(store: Store) -> dict[str, Observation]:
    raw = store.runtime_read().get("observations", {})
    if not isinstance(raw, dict):
        return {}
    result = {}
    for sid, value in raw.items():
        try:
            result[str(sid)] = Observation.model_validate(value)
        except ValidationError:
            continue
    return result


def runtime_status(store: Store) -> dict[str, object]:
    raw = store.runtime_read()
    try:
        stamp = raw.get("heartbeat")
        at = datetime.fromisoformat(stamp) if isinstance(stamp, str) else None
        fresh = at is not None and is_fresh(at, datetime.now(UTC))
    except ValueError:
        fresh = False
    return {
        "daemon": "running" if fresh else "stopped_or_stale",
        "heartbeat": raw.get("heartbeat"),
        "pid": raw.get("pid"),
        "live_diagnostic": raw.get("live_diagnostic"),
        "data_dir": str(store.root),
        "state_dir": str(store.runtime),
        "sampling_interval_seconds": raw.get(
            "sampling_interval_seconds", 1 if raw.get("version") == 1 else SAMPLE_SECONDS
        ),
        "notification_mode": raw.get("notification_mode"),
    }


def import_history(store: Store, home: Path) -> Ledger:
    with store.writer():
        ledger = store.load()
        reader = RolloutReader(
            home, progress=lambda message: print(message, file=sys.stderr, flush=True)
        )
        # Force full idempotent reconciliation.
        reader.scan(ledger)
        refresh_metadata(home, ledger)
        reader.reconcile_contexts(ledger)
        store.save(ledger)
        # Historical import does not fabricate a daemon heartbeat or live state.
        return ledger


async def run_daemon(
    store: Store,
    home: Path,
    socket_path: Path | None,
    stop: asyncio.Event | None = None,
    *,
    sample_seconds: float = SAMPLE_SECONDS,
) -> None:
    if not 0 < sample_seconds <= SAMPLE_SECONDS:
        raise ValueError("sampling interval must be greater than zero and at most 60 seconds")
    stop = stop or asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    wake = asyncio.Event()
    watcher = ChangeWatcher(home)

    def notification_ready() -> None:
        # Selector readers are level-triggered. Leave unread bytes queued, but
        # disarm immediately so coalescing sleeps or socket awaits cannot spin
        # thousands of callbacks before the next bounded drain.
        if watcher.fd is not None:
            loop.remove_reader(watcher.fd)
        wake.set()

    if watcher.fd is not None:
        loop.add_reader(watcher.fd, notification_ready)
    client = LiveClient(home, socket_path, sample_seconds=sample_seconds)
    fx_task: asyncio.Task[FXSnapshot] | None = None
    try:
        if not await prepare_store(store, stop):
            return
        with IndexedStore(store.root, store.runtime) as index:
            store = index.store  # the Store instance holding the canonical writer lock
            ledger = index.ledger
            reader = RolloutReader(home, backend=index)
            observer = Observer(
                max_gap=sample_seconds + max(2, sample_seconds / 4), sample_seconds=sample_seconds
            )
            pending: deque[Path] = deque()
            queued: set[Path] = set()
            reconciliation = Reconciliation(
                reader.source_paths,
                notifications=watcher.available and not watcher.needs_reconciliation,
            )
            scheduler = ScanScheduler(
                reconciliation, pending, queued, event_interval=sample_seconds
            )
            next_sample = 0.0
            next_heartbeat = 0.0
            next_metadata = 0.0
            metadata_cursors, metadata_index = index.metadata_read()
            metadata_pending = True
            active_ids: list[str] = []
            fx_state = read_fx(store.runtime)
            startup = True
            while not stop.is_set():
                now = loop.time()
                # A notification during client.poll() must survive until this
                # drain. Clearing at the end of the loop would erase its wake
                # while its self-disarmed descriptor still has unread bytes.
                wake.clear()
                paths, overflow = watcher.drain()
                if watcher.fd is not None:
                    loop.add_reader(watcher.fd, notification_ready)
                reconciliation.notifications = (
                    watcher.available and not watcher.needs_reconciliation
                )
                # Keep missed-event reconciliation bounded with healthy inotify;
                # startup, overflow and unavailable notifications reconcile fully.
                page = scheduler.take(
                    now, notifications=paths, overflow=overflow, immediate=startup
                )
                if page:
                    reader.progress = lambda message, startup=startup: (
                        index.progress(message) if startup else None
                    )
                    scheduler.finish(reader.scan_paths(ledger, page))
                # Metadata has no supported change feed. Check main + WAL files,
                # and reconcile changed rows only, at most once per sample interval.
                if now >= next_metadata:
                    # Exact active-ID reads do not assume source timestamps are
                    # monotonic. Historical rowid reconciliation has a fixed budget.
                    metadata_pending = refresh_metadata(
                        home,
                        ledger,
                        row_changed=index.row_changed,
                        active_ids=active_ids,
                        cursors=metadata_cursors,
                        index_state=metadata_index,
                        title_get=index.title_get,
                        title_put=index.title_put,
                    )
                    reader.reconcile_contexts(ledger, keys=index.context_batch(active_ids))
                    index.metadata_put(metadata_cursors, metadata_index)
                    next_metadata = now + (0.1 if startup and metadata_pending else sample_seconds)
                if fx_task is not None and fx_task.done():
                    try:
                        fx_state = fx_task.result()
                    except OSError:
                        diagnostic(
                            ledger, "FX cache unavailable; tracking continues; retry in one hour"
                        )
                    fx_task = None
                if fx_task is None and refresh_due(fx_state):
                    fx_state = fx_state.model_copy(update={"last_attempt": datetime.now(UTC)})
                    fx_task = asyncio.create_task(refresh_fx(store.runtime))
                samples = None
                if now >= next_sample:
                    samples = await client.poll()
                    ids = [sample.session_id for sample in samples]
                    active_ids = ids
                    active_paths = set(index.current_sources(ids))
                    active_paths.update(current_rollouts(home, ids))
                    unfinished = reader.scan_paths(ledger, active_paths)
                    scheduler.acknowledge(active_paths, unfinished)
                    if client.diagnostic:
                        diagnostic(ledger, client.diagnostic)
                    observer.apply(ledger, samples)
                    for sample in samples:
                        session = ledger.sessions.get(sample.session_id)
                        if session and sample.cwd and sample.state != "unknown":
                            session.cwd = sample.cwd
                        if session and sample.turn_id is None:
                            ongoing = [
                                t
                                for t in session.turns.values()
                                if t.end is None and t.start <= sample.at
                            ]
                            if ongoing:
                                sample.turn_id = max(ongoing, key=lambda t: t.start).id
                    next_sample = loop.time() + sample_seconds
                index.flush()
                if samples is not None or now >= next_heartbeat:
                    previous = store.runtime_read()
                    store.runtime_save(
                        {
                            "version": 2,
                            "pid": os.getpid(),
                            "heartbeat": datetime.now(UTC).isoformat(),
                            "sampling_interval_seconds": sample_seconds,
                            "notification_mode": "inotify" if watcher.available else "fallback",
                            "rollouts": reader.checkpoints,
                            "live_diagnostic": client.diagnostic,
                            "observations": {
                                s.session_id: s.model_dump(mode="json") for s in samples
                            }
                            if samples is not None
                            else previous.get("observations", {}),
                        }
                    )
                    next_heartbeat = loop.time() + sample_seconds
                startup = startup and bool(
                    pending or reconciliation.initializing or metadata_index.get("pending")
                )
                timeout = max(
                    0.01,
                    min(
                        loop.time() + scheduler.delay(loop.time()),
                        next_sample,
                        next_heartbeat,
                        next_metadata,
                    )
                    - loop.time(),
                )
                wake_task = asyncio.create_task(wake.wait())
                stop_task = asyncio.create_task(stop.wait())
                try:
                    await asyncio.wait(
                        (wake_task, stop_task), timeout=timeout, return_when=asyncio.FIRST_COMPLETED
                    )
                finally:
                    for task in (wake_task, stop_task):
                        task.cancel()
                        with suppress(asyncio.CancelledError):
                            await task
                if wake.is_set():
                    # Coalesce a short file-event burst; the scanner is single-writer.
                    await asyncio.sleep(0.1)
    finally:
        if watcher.fd is not None:
            loop.remove_reader(watcher.fd)
        watcher.close()
        if fx_task is not None:
            fx_task.cancel()
            with suppress(asyncio.CancelledError, OSError):
                await fx_task
        await client.close()
        with store.writer():
            raw = store.runtime_read()
            raw["heartbeat"] = None
            raw["observations"] = {}
            store.runtime_save(raw)
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)
