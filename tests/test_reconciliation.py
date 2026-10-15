from pathlib import Path

from codex_time.reconciliation import Reconciliation


def test_healthy_notifications_bound_historical_work_per_minute() -> None:
    sources = [Path(str(i)) for i in range(1000)]
    scans = Reconciliation(lambda: iter(sources), notifications=True, batch_size=10)
    for _ in range(101):
        scans.take(0)
    assert not scans.initializing
    assert len(scans.take(60)) == 10
    assert scans.take(61) == []
    assert len(scans.take(120)) == 10


def test_missing_notifications_finish_full_fallback_without_overlap() -> None:
    sources = [Path(str(i)) for i in range(25)]
    count = 0

    def discover():
        nonlocal count
        count += 1
        return iter(sources)

    scans = Reconciliation(discover, notifications=False, batch_size=10)
    collected = []
    for _ in range(4):
        collected += scans.take(0)
    assert collected == sources and count == 1
    assert scans.take(59) == []
    assert scans.take(60) == sources[:10]
    assert count == 2


def test_overflow_accelerates_existing_reconciliation() -> None:
    sources = [Path(str(i)) for i in range(25)]
    scans = Reconciliation(lambda: iter(sources), notifications=True, batch_size=10)
    for _ in range(4):
        scans.take(0)
    assert scans.take(60) == sources[:10]
    assert scans.take(61) == []
    assert scans.take(61, overflow=True) == sources[10:20]
    assert scans.take(61) == sources[20:]


def test_ten_thousand_unfinished_sources_bound_queue_and_total_page() -> None:
    from codex_time.reconciliation import ScanScheduler

    discovered = 0

    def discover():
        nonlocal discovered
        for i in range(10_000):
            discovered += 1
            yield Path(f"source-{i}")

    scheduler = ScanScheduler(Reconciliation(discover, notifications=True))
    seen = set()
    for _ in range(100):
        page = scheduler.take(0)
        assert len(page) <= 128
        seen.update(page)
        scheduler.finish(page)  # every large source still has unread records
        assert scheduler.queued_count <= 4096
    assert discovered == 4096  # discovery cannot discard unfinished continuations
    for _ in range(200):
        page = scheduler.take(0)
        assert len(page) <= 128
        seen.update(page)
        scheduler.finish([])
        assert scheduler.queued_count <= 4096
        if len(seen) == 10_000 and scheduler.queued_count == 0:
            break
    assert seen == {Path(f"source-{i}") for i in range(10_000)}


def test_event_priority_and_overflow_do_not_lose_continuations() -> None:
    from codex_time.reconciliation import ScanScheduler

    sources = [Path(f"source-{i}") for i in range(200)]
    urgent = Path("urgent")
    scheduler = ScanScheduler(
        Reconciliation(lambda: iter([*sources, urgent]), notifications=True),
        capacity=16,
        page_size=4,
    )
    for _ in range(8):
        page = scheduler.take(0)
        scheduler.finish(page)
    assert scheduler.queued_count == 16
    page = scheduler.take(0, notifications=[urgent])
    assert urgent not in page  # no continuation is evicted to admit the event
    scheduler.finish([])
    page = scheduler.take(0, notifications=[urgent])
    assert urgent in page
    assert any(path != urgent for path in page)  # retained work also progresses
    assert len(page) <= 4
    scheduler.finish([])
    seen = set(page)
    for _ in range(100):
        page = scheduler.take(0)
        seen.update(page)
        scheduler.finish([])
    assert set(sources) <= seen


def test_discovery_and_notifications_share_one_page_budget() -> None:
    from codex_time.reconciliation import ScanScheduler

    events = [Path(f"event-{i}") for i in range(256)]
    scheduler = ScanScheduler(
        Reconciliation(
            lambda: (Path(f"source-{i}") for i in range(1000)),
            notifications=True,
        )
    )
    page = scheduler.take(0, notifications=events)
    assert len(page) == 128
    assert any(path in events for path in page)
    assert any(str(path).startswith("source-") for path in page)
    scheduler.finish([])


def test_warm_event_deadline_is_anchored_and_deferred_work_can_sleep() -> None:
    from codex_time.reconciliation import ScanScheduler

    scheduler = ScanScheduler(
        Reconciliation(lambda: iter(()), notifications=True), event_interval=60
    )
    assert scheduler.take(0) == []
    scheduler.finish([])
    path = Path("live")
    for now in range(1, 61):
        assert scheduler.take(now, notifications=[path]) == []
        assert scheduler.queued_count == 1
        assert scheduler.delay(now) > 0
        scheduler.finish([])
    assert scheduler.take(61, notifications=[path]) == [path]
    scheduler.finish([])
    assert scheduler.queued_count == 0


def test_warm_event_interval_does_not_delay_startup_or_unfinished_records() -> None:
    from codex_time.reconciliation import ScanScheduler

    source = Path("large")
    scheduler = ScanScheduler(
        Reconciliation(lambda: iter([source]), notifications=True), event_interval=60
    )
    assert scheduler.take(0) == [source]
    scheduler.finish([source])
    assert scheduler.take(0.1) == [source]
    scheduler.finish([])
    assert scheduler.take(0.2) == []
    scheduler.finish([])
    assert not scheduler.reconciliation.initializing
    assert scheduler.take(1, notifications=[source]) == []
    scheduler.finish([])
    assert scheduler.delay(1) > 1  # Pending deferred events must not force 100ms wakeups.
    assert scheduler.take(61) == [source]
    scheduler.finish([])


def test_deferred_event_overflow_remains_bounded_and_reconciles_every_source() -> None:
    from codex_time.reconciliation import ScanScheduler

    sources = [Path(f"source-{i}") for i in range(1000)]
    scheduler = ScanScheduler(
        Reconciliation(lambda: iter(sources), notifications=True),
        capacity=16,
        page_size=4,
        event_interval=60,
    )
    while scheduler.reconciliation.initializing or scheduler.queued_count:
        scheduler.take(0)
        scheduler.finish([])
    seen = set()
    for now in range(1, 601):
        page = scheduler.take(now, notifications=sources if now == 1 else ())
        assert len(page) <= 4
        seen.update(page)
        scheduler.finish(page[:1] if now < 20 else [])
        assert scheduler.queued_count <= 16
        if len(seen) == len(sources):
            break
    assert seen == set(sources)
