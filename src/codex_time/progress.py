"""Periodic stderr status for slow read-only reports, quiet for fast fixtures."""

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Event, Thread
from time import monotonic


@contextmanager
def report_progress(label: str, *, interval: float = 2) -> Iterator[None]:
    stopped = Event()
    start = monotonic()

    def status() -> None:
        while not stopped.wait(interval):
            print(f"{label}: {monotonic() - start:.0f}s elapsed", file=sys.stderr, flush=True)

    worker = Thread(target=status, daemon=True)
    worker.start()
    try:
        yield
    finally:
        stopped.set()
        worker.join()
