"""Historical model projections over the existing counted working-time intervals."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from itertools import groupby
from pathlib import Path
from typing import TypedDict
from zoneinfo import ZoneInfo

from codex_time.accounting import daily_microseconds, segments
from codex_time.models import AttributedSegment, Ledger, Session, Turn, WorkSegment
from codex_time.reporting import selected_sessions


class ModelUsageRow(TypedDict):
    rank: int | None
    model_id: str | None
    reasoning_level: str | None
    working_seconds: float
    working_microseconds: int
    percentage: float
    session_count: int
    quality: list[str]
    sampling_uncertainty_seconds: float


ModelUsageReport = TypedDict(
    "ModelUsageReport",
    {
        "label": str,
        "period": str,
        "from": str,
        "to": str,
        "timezone": str,
        "model_only": bool,
        "total_seconds": float,
        "total_microseconds": int,
        "rows": list[ModelUsageRow],
        "quality": list[str],
        "sampling_uncertainty_seconds": float,
        "diagnostics": list[str],
    },
)


def context_timeline(turn: Turn) -> list[tuple[datetime, str | None, str | None]]:
    """First evidence covers the start; conflicts and missing fields stay Unknown.

    Keep distinct observations in the ledger for conflict detection. Collapse
    repeated settings here, so they neither split work nor add report time.
    """
    result: list[tuple[datetime, str | None, str | None]] = []
    for at, contexts in groupby(
        sorted(turn.model_contexts, key=lambda c: c.at), key=lambda c: c.at
    ):
        settings = {(c.model_id, c.reasoning_level) for c in contexts}
        model, effort = next(iter(settings)) if len(settings) == 1 else (None, None)
        effective = turn.start if not result else max(turn.start, at)
        if result and result[-1][1:] == (model, effort):
            continue
        if result and effective == result[-1][0]:
            result[-1] = (effective, model, effort)
        else:
            result.append((effective, model, effort))
    return result


def latest_model(session: Session) -> tuple[str | None, str | None]:
    """Latest observed context only; never a current SQLite configuration."""
    contexts = [c for turn in session.turns.values() for c in turn.model_contexts]
    if not contexts:
        return None, None
    latest = max(c.at for c in contexts)
    settings = {(c.model_id, c.reasoning_level) for c in contexts if c.at == latest}
    return next(iter(settings)) if len(settings) == 1 else (None, None)


def attributed_segments(
    session: Session, work: list[WorkSegment] | None = None
) -> list[AttributedSegment]:
    if session.is_child or session.parent_id:
        return []
    work = segments(list(session.turns.values())) if work is None else work
    timelines = {tid: context_timeline(turn) for tid, turn in session.turns.items()}
    result: list[AttributedSegment] = []
    for span in work:
        owner = max((session.turns[tid] for tid in span.turn_ids), key=lambda t: (t.start, t.id))
        timeline = timelines[owner.id]
        boundaries = [
            span.start,
            *[at for at, _, _ in timeline if span.start < at < span.end],
            span.end,
        ]
        for start, end in zip(boundaries, boundaries[1:], strict=False):
            model, effort = None, None
            for at, declared_model, declared_effort in timeline:
                if at > start:
                    break
                model, effort = declared_model, declared_effort
            quality = set(span.quality) | set(session.quality)
            if owner.end is None:
                quality.add("unfinished")
            if model is None:
                quality.add("unknown_model")
            if effort is None:
                quality.add("unknown_reasoning")
            result.append(
                AttributedSegment(
                    start=start,
                    end=end,
                    cwd=span.cwd,
                    turn_ids=span.turn_ids,
                    quality=sorted(quality),
                    model_id=model,
                    reasoning_level=effort,
                )
            )
    return result


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
    raise ValueError("model report period must be day, week or month")


@dataclass
class Bucket:
    micros: int = 0
    sessions: set[str] = field(default_factory=set)
    quality: set[str] = field(default_factory=set)
    uncertainty: dict[tuple[str, str], float] = field(default_factory=dict)


def model_report(
    ledger: Ledger,
    *,
    period: str,
    selected_date: date | None = None,
    cwd: str | None = None,
    archive: str = "all",
    model_only: bool = False,
    timezone_name: str = "America/Toronto",
    now: datetime | None = None,
) -> ModelUsageReport:
    selected_date = (
        selected_date or (now or datetime.now(UTC)).astimezone(ZoneInfo(timezone_name)).date()
    )
    start, end = calendar_dates(period, selected_date)
    buckets: dict[tuple[str | None, str | None], Bucket] = {}
    for session in selected_sessions(
        ledger, cwd=cwd or "/", all_directories=cwd is None, archive=archive
    ):
        for span in attributed_segments(session):
            if cwd is not None and Path(span.cwd).resolve() != Path(cwd).resolve():
                continue
            micros = sum(
                value
                for day, value in daily_microseconds([span], timezone_name).items()
                if start.isoformat() <= day <= end.isoformat()
            )
            if micros <= 0:
                continue
            key = (span.model_id, None if model_only else span.reasoning_level)
            bucket = buckets.setdefault(key, Bucket())
            bucket.micros += micros
            bucket.sessions.add(session.id)
            bucket.quality.update(span.quality)
            for tid in span.turn_ids:
                bucket.uncertainty[(session.id, tid)] = session.turns[
                    tid
                ].sampling_uncertainty_seconds
    total = sum(bucket.micros for bucket in buckets.values())
    ordered = sorted(
        buckets, key=lambda key: (key[0] is None, -buckets[key].micros, key[0] or "", key[1] or "")
    )
    rows: list[ModelUsageRow] = []
    quality: set[str] = set()
    uncertainty: dict[tuple[str, str], float] = {}
    for index, key in enumerate(ordered, 1):
        bucket = buckets[key]
        quality.update(bucket.quality)
        uncertainty.update(bucket.uncertainty)
        rows.append(
            {
                "rank": index if key[0] is not None else None,
                "model_id": key[0],
                "reasoning_level": key[1],
                "working_seconds": bucket.micros / 1_000_000,
                "working_microseconds": bucket.micros,
                "percentage": bucket.micros / total * 100 if total else 0,
                "session_count": len(bucket.sessions),
                "quality": sorted(bucket.quality),
                "sampling_uncertainty_seconds": sum(bucket.uncertainty.values()),
            }
        )
    return {
        "label": "working-time usage",
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "timezone": timezone_name,
        "model_only": model_only,
        "total_seconds": total / 1_000_000,
        "total_microseconds": total,
        "rows": rows,
        "quality": sorted(quality),
        "sampling_uncertainty_seconds": sum(uncertainty.values()),
        "diagnostics": ledger.diagnostics,
    }
