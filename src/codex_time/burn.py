"""Replay account-wide quota observations against counted root workloads."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from itertools import groupby
from typing import TypedDict
from zoneinfo import ZoneInfo

from codex_time.model_usage import attributed_segments, calendar_dates
from codex_time.models import AttributedSegment, Ledger, QuotaObservation


class MixRow(TypedDict):
    model_id: str | None
    reasoning_level: str | None
    working_microseconds: int
    percentage: float


class BurnRow(TypedDict):
    date: str
    limit_id: str
    plan_type: str | None
    bucket: str
    window_minutes: int
    resets_at: int
    matched_points: float
    working_microseconds: int
    working_hours: float
    points_per_working_hour: float | None
    matched_windows: int
    rounding_sensitivity_points_per_hour: float | None
    excluded_gap_points: float
    excluded_no_work_points: float
    excluded_boundary_points: float
    stale_readings: int
    mix: list[MixRow]
    quality: list[str]
    sampling_uncertainty_seconds: float


BurnReport = TypedDict(
    "BurnReport",
    {
        "label": str,
        "from": str,
        "to": str,
        "timezone": str,
        "period": str,
        "limit_id": str,
        "window_minutes": int,
        "max_gap_seconds": int,
        "rows": list[BurnRow],
        "latest": dict[str, object] | None,
        "quality": list[str],
        "diagnostics": list[str],
    },
)


@dataclass
class Accumulator:
    points: float = 0
    mix: dict[tuple[str | None, str | None], int] = field(default_factory=lambda: defaultdict(int))
    quality: set[str] = field(default_factory=lambda: {"low_confidence", "account_wide_allowance"})
    uncertainty: dict[tuple[str, str], float] = field(default_factory=dict)
    gap: float = 0
    no_work: float = 0
    boundary: float = 0
    stale: int = 0
    windows: int = 0
    blocks: int = 0
    previous_end: datetime | None = None


class WorkIndex:
    """Sweep disjoint root work for monotonically ordered observation pairs."""

    def __init__(self, spans: list[tuple[str, AttributedSegment]], ledger: Ledger) -> None:
        self.spans = spans
        self.ledger = ledger
        self.cursor = 0
        self.active: list[tuple[str, AttributedSegment]] = []

    def add(self, start: datetime, end: datetime, row: Accumulator) -> int:
        self.active = [(sid, s) for sid, s in self.active if s.end > start]
        while self.cursor < len(self.spans) and self.spans[self.cursor][1].start < end:
            sid, span = self.spans[self.cursor]
            if span.end > start:
                self.active.append((sid, span))
            self.cursor += 1
        micros = 0
        for sid, span in self.active:
            left, right = max(start, span.start), min(end, span.end)
            if right <= left:
                continue
            elapsed = (right - left) // timedelta(microseconds=1)
            micros += elapsed
            row.mix[(span.model_id, span.reasoning_level)] += elapsed
            row.quality.update(span.quality)
            for tid in span.turn_ids:
                row.uncertainty[(sid, tid)] = (
                    self.ledger.sessions[sid].turns[tid].sampling_uncertainty_seconds
                )
        return micros


def burn_report(
    ledger: Ledger,
    *,
    period: str,
    selected_date: date | None = None,
    timezone_name: str = "America/Toronto",
    window_minutes: int = 10080,
    limit_id: str = "codex",
    max_gap_seconds: int = 600,
) -> BurnReport:
    if window_minutes <= 0 or max_gap_seconds <= 0:
        raise ValueError("quota window and maximum gap must be positive")
    zone = ZoneInfo(timezone_name)
    first, last = calendar_dates(period, selected_date or datetime.now(UTC).astimezone(zone).date())
    start = datetime.combine(first, datetime.min.time(), zone).astimezone(UTC)
    end = datetime.combine(last + timedelta(days=1), datetime.min.time(), zone).astimezone(UTC)
    observations = sorted(
        {
            q.model_dump_json(): q
            for q in ledger.quota_observations
            if q.limit_id == limit_id and q.window_minutes == window_minutes and q.at < end
        }.values(),
        key=lambda q: (q.at, q.bucket, q.plan_type or "", q.resets_at, q.used_percent),
    )
    # Canonical reset cohorts within each stream; never cross materially different resets.
    streams: dict[tuple[str, str | None], dict[int, list[QuotaObservation]]] = {}
    active_reset: dict[tuple[str, str | None], int] = {}
    retired: dict[tuple[str, str | None], set[int]] = defaultdict(set)
    retired_stale: dict[tuple[str, str | None, int, str], int] = defaultdict(int)
    conflicts: dict[tuple[str, str | None], set[datetime]] = defaultdict(set)
    for (at, bucket, plan), simultaneous in groupby(
        observations, key=lambda q: (q.at, q.bucket, q.plan_type)
    ):
        stream = (bucket, plan)
        cohorts = streams.setdefault(stream, {})
        grouped: dict[int, list[QuotaObservation]] = defaultdict(list)
        for q in simultaneous:
            canonical = next(
                (reset for reset in cohorts if abs(reset - q.resets_at) <= 5), q.resets_at
            )
            cohorts.setdefault(canonical, [])
            grouped[canonical].append(q)
        if len(grouped) != 1 or len({q.used_percent for qs in grouped.values() for q in qs}) != 1:
            conflicts[stream].add(at)
            continue  # Ambiguity must not retire a cohort or establish a baseline.
        canonical, qs = next(iter(grouped.items()))
        if canonical in retired[stream]:
            if start <= at < end:
                retired_stale[
                    (bucket, plan, canonical, at.astimezone(zone).date().isoformat())
                ] += 1
            continue
        prior = active_reset.get(stream)
        if prior is not None and prior != canonical:
            retired[stream].add(prior)
        active_reset[stream] = canonical
        cohorts[canonical].extend(qs)
    spans = sorted(
        [
            (session.id, span)
            for session in ledger.sessions.values()
            for span in attributed_segments(session)
            if span.start < end and span.end > start
        ],
        key=lambda item: item[1].start,
    )
    accepted: list[QuotaObservation] = []
    rows: list[BurnRow] = []
    quality: set[str] = {"low_confidence", "account_wide_allowance"}
    for (bucket, plan), cohorts in sorted(
        streams.items(), key=lambda item: (item[0][0], item[0][1] or "")
    ):
        for reset, readings in sorted(cohorts.items()):
            by_day: dict[str, Accumulator] = {
                day: Accumulator(
                    stale=count,
                    quality={"low_confidence", "account_wide_allowance", "retired_reset_reading"},
                )
                for (old_bucket, old_plan, old_reset, day), count in retired_stale.items()
                if (old_bucket, old_plan, old_reset) == (bucket, plan, reset)
            }
            for at in conflicts[(bucket, plan)]:
                if start <= at < end:
                    by_day.setdefault(
                        at.astimezone(zone).date().isoformat(), Accumulator()
                    ).quality.add("conflicting_quota_observation")
            previous: QuotaObservation | None = None
            high_water: float | None = None
            work = WorkIndex(spans, ledger)
            for at, same_time in groupby(readings, key=lambda q: q.at):
                values = list(same_time)
                in_period = start <= at < end
                day = at.astimezone(zone).date().isoformat()
                if len({q.used_percent for q in values}) != 1:
                    if in_period:
                        row = by_day.setdefault(day, Accumulator())
                        row.quality.add("conflicting_quota_observation")
                    previous = None  # Never bridge ambiguous readings.
                    continue
                q = values[0]
                if previous is not None and any(
                    previous.at < conflict <= at for conflict in conflicts[(bucket, plan)]
                ):
                    previous = None  # First unambiguous reading after conflict is a new baseline.
                if high_water is not None and q.used_percent < high_water:
                    if in_period:
                        by_day.setdefault(day, Accumulator()).stale += 1
                    continue
                high_water = q.used_percent
                if in_period:
                    accepted.append(q)
                    row = by_day.setdefault(day, Accumulator())
                    if previous is not None:
                        delta = q.used_percent - previous.used_percent
                        if (
                            previous.at < start
                            or previous.at.astimezone(zone).date().isoformat() != day
                        ):
                            row.boundary += delta
                            row.quality.add("calendar_boundary_excluded")
                        elif (q.at - previous.at).total_seconds() > max_gap_seconds:
                            row.gap += delta
                            row.quality.add("quota_observation_gap")
                        elif work.add(previous.at, q.at, row) == 0:
                            row.no_work += delta
                            row.quality.add("quota_without_root_work")
                        else:
                            row.points += delta
                            row.windows += 1
                            if row.previous_end != previous.at:
                                row.blocks += 1
                            row.previous_end = q.at
                previous = q
            for day, acc in sorted(by_day.items()):
                micros = sum(acc.mix.values())
                hours = micros / 3_600_000_000
                mix: list[MixRow] = [
                    {
                        "model_id": model,
                        "reasoning_level": effort,
                        "working_microseconds": value,
                        "percentage": value / micros * 100,
                    }
                    for (model, effort), value in sorted(
                        acc.mix.items(),
                        key=lambda item: (-item[1], item[0][0] or "", item[0][1] or ""),
                    )
                ]
                quality.update(acc.quality)
                rows.append(
                    {
                        "date": day,
                        "limit_id": limit_id,
                        "plan_type": plan,
                        "bucket": bucket,
                        "window_minutes": window_minutes,
                        "resets_at": reset,
                        "matched_points": acc.points,
                        "working_microseconds": micros,
                        "working_hours": hours,
                        "points_per_working_hour": acc.points / hours if hours else None,
                        "matched_windows": acc.windows,
                        "rounding_sensitivity_points_per_hour": acc.blocks / hours
                        if hours
                        else None,
                        "excluded_gap_points": acc.gap,
                        "excluded_no_work_points": acc.no_work,
                        "excluded_boundary_points": acc.boundary,
                        "stale_readings": acc.stale,
                        "mix": mix,
                        "quality": sorted(acc.quality),
                        "sampling_uncertainty_seconds": sum(acc.uncertainty.values()),
                    }
                )
    latest: dict[str, object] | None = None
    selected = accepted
    if selected:
        at = max(q.at for q in selected)
        newest = [q for q in selected if q.at == at]
        if len({q.model_dump_json() for q in newest}) == 1:
            latest = newest[0].model_dump(mode="json")
            latest["remaining_percent"] = 100 - newest[0].used_percent
        else:
            quality.add("ambiguous_latest_quota")
    return {
        "label": "allowance percentage points per summed root working hour (low confidence)",
        "from": first.isoformat(),
        "to": last.isoformat(),
        "period": period,
        "timezone": timezone_name,
        "limit_id": limit_id,
        "window_minutes": window_minutes,
        "max_gap_seconds": max_gap_seconds,
        "rows": sorted(
            rows, key=lambda r: (r["date"], r["resets_at"], r["bucket"], r["plan_type"] or "")
        ),
        "latest": latest,
        "quality": sorted(quality),
        "diagnostics": ledger.diagnostics,
    }
