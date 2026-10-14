"""Calendar bounds shared by token and elapsed-time reports."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from codex_time.models import Ledger


def calendar_dates(period: str, selected: date) -> tuple[date, date]:
    if period == "day":
        return selected, selected
    if period == "week":
        start = selected - timedelta(days=selected.weekday())
        return start, start + timedelta(days=6)
    if period == "month":
        start = selected.replace(day=1)
        following = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        return start, following - timedelta(days=1)
    raise ValueError("report period must be day, week, month or all")


def report_dates(
    ledger: Ledger, period: str, selected: date | None, timezone_name: str
) -> tuple[date, date]:
    if period == "all" and selected is not None:
        raise ValueError("--date cannot be combined with all")
    zone = ZoneInfo(timezone_name)
    if period != "all":
        return calendar_dates(period, selected or datetime.now(UTC).astimezone(zone).date())
    stamps = [q.at for q in ledger.quota_observations]
    stamps.extend(o.at for o in ledger.usage_observations)
    for session in ledger.sessions.values():
        stamps.extend((session.created, session.updated))
        for turn in session.turns.values():
            stamps.append(turn.start)
            if turn.end is not None:
                stamps.append(turn.end)
            stamps.extend(span.end for span in turn.coverage)
    if not stamps:
        today = datetime.now(UTC).astimezone(zone).date()
        return today, today
    dates = [stamp.astimezone(zone).date() for stamp in stamps]
    return min(dates), max(dates)
