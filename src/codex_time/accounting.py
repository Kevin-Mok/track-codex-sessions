"""Union counted work and waits using UTC elapsed seconds."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from codex_time.models import Span, Turn, WorkSegment


def merge_spans(spans: list[Span]) -> list[Span]:
    result: list[Span] = []
    for span in sorted(spans, key=lambda s: s.start):
        if span.end <= span.start:
            continue
        if result and span.start <= result[-1].end:
            result[-1].end = max(result[-1].end, span.end)
        else:
            result.append(span.model_copy())
    return result


def subtract(work: list[Span], waits: list[Span]) -> list[Span]:
    result: list[Span] = []
    for span in merge_spans(work):
        cursor = span.start
        for wait in merge_spans(waits):
            if wait.end <= cursor or wait.start >= span.end:
                continue
            if wait.start > cursor:
                result.append(Span(start=cursor, end=min(wait.start, span.end)))
            cursor = max(cursor, wait.end)
            if cursor >= span.end:
                break
        if cursor < span.end:
            result.append(Span(start=cursor, end=span.end))
    return result


def segments(turns: list[Turn]) -> list[WorkSegment]:
    """Disjoint same-session work, latest-starting turn owns overlapping cwd."""
    pieces: list[tuple[Span, Turn]] = []
    waits = merge_spans([wait for turn in turns for wait in turn.waits])
    for turn in turns:
        work = [Span(start=turn.start, end=turn.end)] if turn.end else turn.coverage
        pieces.extend((span, turn) for span in subtract(work, waits))
    boundaries = sorted({point for span, _ in pieces for point in (span.start, span.end)})
    result: list[WorkSegment] = []
    for start, end in zip(boundaries, boundaries[1:], strict=False):
        active = [turn for span, turn in pieces if span.start <= start and span.end >= end]
        if not active:
            continue
        owner = max(active, key=lambda turn: (turn.start, turn.id))
        ids = sorted({turn.id for turn in active})
        quality = sorted({flag for turn in active for flag in turn.quality})
        if (
            result
            and result[-1].end == start
            and result[-1].cwd == owner.cwd
            and result[-1].turn_ids == ids
            and result[-1].quality == quality
        ):
            result[-1].end = end
        else:
            result.append(
                WorkSegment(start=start, end=end, cwd=owner.cwd, turn_ids=ids, quality=quality)
            )
    return result


def elapsed_microseconds(span: Span) -> int:
    delta = span.end - span.start
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def total_seconds(work: list[WorkSegment]) -> float:
    return sum(elapsed_microseconds(span) for span in work) / 1_000_000


def daily_microseconds(work: list[WorkSegment], timezone_name: str) -> dict[str, int]:
    zone = ZoneInfo(timezone_name)
    totals: dict[str, int] = {}
    for span in work:
        cursor = span.start
        while cursor < span.end:
            local_day = cursor.astimezone(zone).date()
            midnight = datetime.combine(local_day + timedelta(days=1), time(), zone)
            end = min(midnight.astimezone(UTC), span.end)
            key = local_day.isoformat()
            totals[key] = totals.get(key, 0) + elapsed_microseconds(Span(start=cursor, end=end))
            cursor = end
    return dict(sorted(totals.items()))


def daily_totals(work: list[WorkSegment], timezone_name: str) -> dict[str, float]:
    return {
        day: micros / 1_000_000 for day, micros in daily_microseconds(work, timezone_name).items()
    }
