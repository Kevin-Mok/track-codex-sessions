"""Shared minute-cadence boundaries for runtime evidence and heartbeat health."""

from datetime import datetime

SAMPLE_SECONDS = 60.0
# Permit scheduling jitter, but never bridge an entire missed minute sample.
MAX_OBSERVATION_GAP_SECONDS = 75.0
# Heartbeat grace is health-only; it must not extend observed work intervals.
HEARTBEAT_FRESH_SECONDS = 90.0


def is_fresh(
    at: datetime,
    now: datetime,
    *,
    max_age_seconds: float = HEARTBEAT_FRESH_SECONDS,
) -> bool:
    """Reject future, stale, and timezone-less evidence using a caller-owned clock."""
    if at.tzinfo is None or now.tzinfo is None:
        return False
    return 0 <= (now - at).total_seconds() <= max_age_seconds
