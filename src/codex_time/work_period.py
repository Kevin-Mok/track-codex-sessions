"""Conservative period eligibility without reconstructing historical accounting."""

from datetime import datetime

from codex_time.models import Session


def has_work_in_period(session: Session, start: datetime, end: datetime) -> bool:
    """False proves no counted work can intersect [start, end).

    Inspect lifecycle/coverage rather than coarse session metadata. Retained
    sessions still use all turns, waits and contexts in the existing accounting.
    """
    for turn in session.turns.values():
        if turn.end is not None:
            if turn.start < end and turn.end > start and turn.end > turn.start:
                return True
        elif any(span.start < end and span.end > start and span.end > span.start
                 for span in turn.coverage):
            return True
    return False
