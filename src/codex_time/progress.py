"""Periodic stderr status for slow read-only reports, quiet for fast fixtures."""

import os
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Event, Thread
from time import monotonic

from rich.text import Text

from codex_time.presentation import safe_text


@contextmanager
def report_progress(label: str, *, interval: float = 2, interactive: bool = True) -> Iterator[None]:
    stopped = Event()
    start = monotonic()
    stream = sys.stderr
    transient = interactive and stream.isatty()
    drawn_width = 0
    label = safe_text(label)

    def columns() -> int:
        try:
            width = os.get_terminal_size(stream.fileno()).columns
        except (OSError, ValueError):
            width = shutil.get_terminal_size((88, 24)).columns
        return max(1, width - 1)

    def status() -> None:
        nonlocal drawn_width
        while not stopped.wait(interval):
            width = columns()
            suffix = f": {monotonic() - start:.0f}s elapsed"
            message = Text(label)
            message.truncate(max(0, width - len(suffix)), overflow="crop")
            message.append(suffix)
            message.truncate(width, overflow="crop")
            if transient:
                padding = " " * max(0, min(drawn_width, width) - message.cell_len)
                stream.write("\r" + message.plain + padding)
                drawn_width = message.cell_len
            else:
                stream.write(message.plain + "\n")
            stream.flush()

    worker = Thread(target=status, daemon=True)
    worker.start()
    try:
        yield
    finally:
        stopped.set()
        worker.join()
        if transient and drawn_width:
            stream.write("\r" + " " * min(drawn_width, columns()) + "\r")
            stream.flush()
