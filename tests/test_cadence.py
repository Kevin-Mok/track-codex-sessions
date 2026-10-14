from datetime import UTC, datetime, timedelta

import pytest

from codex_time import cadence


@pytest.mark.parametrize(
    ("age_seconds", "expected"),
    [(0, True), (60, True), (90, True), (90.001, False), (120, False), (-1, False)],
)
def test_minute_heartbeat_remains_fresh_until_grace_expires(
    age_seconds: float, expected: bool
) -> None:
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    at = now - timedelta(seconds=age_seconds)
    assert cadence.is_fresh(at, now) is expected


def test_naive_heartbeat_is_not_fresh() -> None:
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    assert not cadence.is_fresh(now.replace(tzinfo=None), now)


def test_observation_freshness_uses_its_shorter_outage_threshold() -> None:
    now = datetime(2026, 10, 14, 12, tzinfo=UTC)
    assert cadence.is_fresh(
        now - timedelta(seconds=75), now, max_age_seconds=cadence.MAX_OBSERVATION_GAP_SECONDS
    )
    assert not cadence.is_fresh(
        now - timedelta(seconds=75.001), now, max_age_seconds=cadence.MAX_OBSERVATION_GAP_SECONDS
    )
