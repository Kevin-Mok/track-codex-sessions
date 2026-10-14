"""Bound historical reconciliation while prioritizing currently observed sources."""

from collections import deque
from collections.abc import Callable, Iterable, Iterator
from itertools import islice
from pathlib import Path


class Reconciliation:
    def __init__(
        self,
        discover: Callable[[], Iterator[Path]],
        *,
        notifications: bool,
        batch_size: int = 128,
        interval: float = 60,
    ) -> None:
        self.discover = discover
        self.notifications = notifications
        self.batch_size = batch_size
        self.interval = interval
        self.iterator: Iterator[Path] | None = discover()
        self.initializing = True
        self.full = True
        self.due = 0.0
        self.restart_requested = False

    def take(self, now: float, *, overflow: bool = False, limit: int | None = None) -> list[Path]:
        if overflow:
            self.full = True
            # Finish the current iterator, then revisit names already passed when
            # notifications were lost. Repeated overflow cannot restart/starve it.
            self.restart_requested = self.iterator is not None
        count = self.batch_size if limit is None else min(self.batch_size, max(0, limit))
        if not count:
            return []
        if not self.full and now < self.due:
            return []
        if self.iterator is None:
            self.iterator = self.discover()
        page = list(islice(self.iterator, count))
        if not page:
            self.iterator = None
            self.full = False
            self.initializing = False
            self.due = now + self.interval
            if self.restart_requested:
                self.full = True
                self.restart_requested = False
                self.due = now
        elif self.full or not self.notifications:
            self.due = now
        else:
            self.due = now + self.interval
        return page

    def delay(self, now: float) -> float:
        return max(0.1, self.due - now)


class ScanScheduler:
    """Share one page and backlog budget across events, discovery and retries.

    Selected paths reserve capacity until ``finish`` returns their continuation
    status. Discovery never advances past paths that cannot fit in that budget.
    Events receive half the page when both new events and retained work exist;
    FIFO retained work receives the other half, avoiding either form of starvation.
    """

    def __init__(
        self,
        reconciliation: Reconciliation,
        pending: deque[Path] | None = None,
        queued: set[Path] | None = None,
        *,
        capacity: int = 4096,
        page_size: int = 128,
    ) -> None:
        if capacity < 1 or not 0 < page_size <= capacity:
            raise ValueError("scan page must be positive and fit the pending capacity")
        self.reconciliation = reconciliation
        self.pending = pending if pending is not None else deque()
        self.queued = queued if queued is not None else set()
        self.capacity, self.page_size = capacity, page_size
        self._events: deque[Path] = deque()
        self._event_set: set[Path] = set()
        self._page: list[Path] = []
        self._overflow = False

    @property
    def queued_count(self) -> int:
        return len(self.pending) + len(self._page)

    def _admit(self, path: Path, *, event: bool = False) -> None:
        if path not in self.queued:
            if self.queued_count >= self.capacity:
                self._overflow = True
                return
            self.pending.append(path)
            self.queued.add(path)
        if event and path not in self._event_set:
            self._event_set.add(path)
            self._events.append(path)

    def _select(self, path: Path) -> None:
        self.pending.remove(path)
        self.queued.remove(path)
        self._event_set.discard(path)
        self._page.append(path)

    def take(
        self, now: float, *, notifications: Iterable[Path] = (), overflow: bool = False
    ) -> list[Path]:
        if self._page:
            raise RuntimeError("finish the current scan before taking another page")
        for path in notifications:
            self._admit(path, event=True)
        lost = overflow or self._overflow
        self._overflow = False
        available = self.capacity - self.queued_count
        for path in self.reconciliation.take(now, overflow=lost, limit=available):
            self._admit(path)
        event_budget = max(1, self.page_size // 2)
        while self._events and len(self._page) < event_budget:
            path = self._events.popleft()
            if path in self._event_set:
                self._select(path)
        remaining = self.page_size - len(self._page)
        work = list(islice(
            (path for path in self.pending if path not in self._event_set), remaining
        ))
        for path in work:
            self._select(path)
        while self._events and len(self._page) < self.page_size:
            path = self._events.popleft()
            if path in self._event_set:
                self._select(path)
        return list(self._page)

    def finish(self, unfinished: Iterable[Path]) -> None:
        expected = set(self._page)
        continued: set[Path] = set()
        for path in unfinished:
            if path in expected:
                continued.add(path)
            else:
                # Defensive ingress guard, including callers handing back paths
                # outside the current page. Reserved continuation slots stay safe.
                self._admit(path)
        for path in self._page:
            if path in continued:
                self.pending.append(path)
                self.queued.add(path)
        self._page.clear()
