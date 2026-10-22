"""Isolate cold migration/index allocations from the long-lived tracking process."""

import argparse
import asyncio
import os
import sys
from asyncio import wait as wait_for_first
from contextlib import suppress
from pathlib import Path

from codex_time.incremental_storage import IndexedStore
from codex_time.progress import report_progress
from codex_time.storage import Store, StoreError


async def _reap(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        with suppress(ProcessLookupError):
            process.terminate()
    try:
        await asyncio.wait_for(asyncio.shield(process.wait()), 5)
    except TimeoutError:
        with suppress(ProcessLookupError):
            process.kill()
        await process.wait()


async def prepare_store(store: Store, stop: asyncio.Event) -> bool:
    """Prepare portable evidence and disposable indexes in a short-lived child."""
    if stop.is_set():
        return False
    launch = asyncio.create_task(
        asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "codex_time.bootstrap",
            "--data-dir",
            str(store.root),
            "--state-dir",
            str(store.runtime),
        )
    )
    try:
        process = await asyncio.shield(launch)
    except asyncio.CancelledError:
        # Cancellation may arrive after fork but before create_subprocess_exec
        # returns its handle. Obtain it before reaping to avoid an orphan writer.
        process = await launch
        await _reap(process)
        raise
    finished = asyncio.create_task(process.wait())
    stopping = asyncio.create_task(stop.wait())
    try:
        await wait_for_first((finished, stopping), return_when=asyncio.FIRST_COMPLETED)
        if stop.is_set():
            await _reap(process)
            return False
        status = finished.result()
        if status:
            raise StoreError(f"tracking bootstrap failed (exit {status}); evidence was preserved")
        return True
    except asyncio.CancelledError:
        await _reap(process)
        raise
    finally:
        for task in (finished, stopping):
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    args = parser.parse_args()
    plain = os.environ.get("CLI_PLAIN") == "1"
    label = ("" if plain else "⏳ ") + "Preparing tracking history and indexes"
    print(label, file=sys.stderr, flush=True)
    try:
        with report_progress(label, interactive=False), IndexedStore(args.data_dir, args.state_dir):
            pass
        return 0
    except (StoreError, OSError, ValueError) as exc:
        print(("" if plain else "⚠️ ") + str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
