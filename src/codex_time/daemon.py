"""Single-writer observation loop, independent of the terminal UI."""

import asyncio
import os
import signal
import sys
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from codex_time.fx import FXSnapshot, read_fx, refresh_due, refresh_fx
from codex_time.ingest import RolloutReader, diagnostic
from codex_time.live import LiveClient
from codex_time.metadata import refresh_metadata
from codex_time.models import Ledger, Observation
from codex_time.observer import Observer
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
        fresh = (
            at is not None
            and at.tzinfo is not None
            and 0 <= (datetime.now(UTC) - at).total_seconds() <= 5
        )
    except ValueError:
        fresh = False
    return {
        "daemon": "running" if fresh else "stopped_or_stale",
        "heartbeat": raw.get("heartbeat"),
        "pid": raw.get("pid"),
        "live_diagnostic": raw.get("live_diagnostic"),
        "data_dir": str(store.root),
        "state_dir": str(store.runtime),
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
    store: Store, home: Path, socket_path: Path | None, stop: asyncio.Event | None = None
) -> None:
    stop = stop or asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    with store.writer():
        ledger = store.load()
        runtime = store.runtime_read()
        cached = (
            runtime.get("rollouts") if runtime.get("ledger_hash") == store.fingerprint() else None
        )
        # A checkpoint is valid only with the durable ledger that preceded it.
        reader = RolloutReader(
            home,
            cast(dict[str, object], cached) if isinstance(cached, dict) else None,
            progress=lambda message: print(message, file=sys.stderr, flush=True),
        )
        observer = Observer()
        client = LiveClient(home, socket_path)
        iteration = 0
        fx_state = read_fx(store.runtime)
        fx_task: asyncio.Task[FXSnapshot] | None = None
        try:
            while not stop.is_set():
                began = loop.time()
                if fx_task is not None and fx_task.done():
                    try:
                        fx_state = fx_task.result()
                    except OSError:
                        diagnostic(
                            ledger, "FX cache unavailable; tracking continues; retry in one hour"
                        )
                    fx_task = None
                if fx_task is None and refresh_due(fx_state):
                    # Local attempt timestamp also throttles a cache-write failure.
                    fx_state = fx_state.model_copy(update={"last_attempt": datetime.now(UTC)})
                    fx_task = asyncio.create_task(refresh_fx(store.runtime))
                # Backfills report progress; short steady-state scans stay quiet.
                scan_started = loop.time()
                reader.progress = lambda message, iteration=iteration, scan_started=scan_started: (
                    print(message, file=sys.stderr, flush=True)
                    if iteration == 0 or loop.time() - scan_started >= 2
                    else None
                )
                reader.scan(ledger)
                if iteration % 10 == 0:
                    refresh_metadata(home, ledger)
                    reader.reconcile_contexts(ledger)
                samples = await client.poll()
                if client.diagnostic:
                    diagnostic(ledger, client.diagnostic)
                observer.apply(ledger, samples)
                # Read-only runtime cwd can refresh resume location without rewriting past turns.
                for sample in samples:
                    session = ledger.sessions.get(sample.session_id)
                    if session and sample.cwd:
                        session.cwd = sample.cwd
                    if session and sample.turn_id is None:
                        ongoing = [
                            t
                            for t in session.turns.values()
                            if t.end is None and t.start <= sample.at
                        ]
                        if ongoing:
                            sample.turn_id = max(ongoing, key=lambda t: t.start).id
                store.save(ledger)
                store.runtime_save(
                    {
                        "version": 1,
                        "pid": os.getpid(),
                        "heartbeat": datetime.now(UTC).isoformat(),
                        "rollouts": reader.checkpoints,
                        "ledger_hash": store.fingerprint(),
                        "live_diagnostic": client.diagnostic,
                        "observations": {s.session_id: s.model_dump(mode="json") for s in samples},
                    }
                )
                iteration += 1
                try:
                    await asyncio.wait_for(
                        stop.wait(), timeout=max(0.01, 1 - (loop.time() - began))
                    )
                except TimeoutError:
                    pass
        finally:
            if fx_task is not None:
                fx_task.cancel()
                with suppress(asyncio.CancelledError, OSError):
                    await fx_task
            await client.close()
            raw = store.runtime_read()
            raw["heartbeat"] = None
            raw["observations"] = {}
            store.runtime_save(raw)
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)
