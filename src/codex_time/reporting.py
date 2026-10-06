"""Directory-attributed reports from durable disjoint work segments."""

from datetime import date
from pathlib import Path
from typing import TypedDict

from codex_time.accounting import daily_microseconds, segments
from codex_time.models import Ledger, Session


class Report(TypedDict):
    timezone: str
    total_seconds: float
    total_microseconds: int
    days: dict[str, float]
    directories: dict[str, float]
    sessions: dict[str, float]
    quality: list[str]
    diagnostics: list[str]


def selected_sessions(
    ledger: Ledger,
    *,
    cwd: str,
    all_directories: bool,
    archive: str = "active",
    session_id: str | None = None,
) -> list[Session]:
    return [
        s
        for s in ledger.sessions.values()
        if (
            all_directories
            or Path(s.cwd).resolve() == Path(cwd).resolve()
            or any(Path(t.cwd).resolve() == Path(cwd).resolve() for t in s.turns.values())
        )
        and (archive == "all" or s.archived == (archive == "archived"))
        and (session_id is None or s.id == session_id)
    ]


def report(
    ledger: Ledger,
    *,
    cwd: str,
    all_directories: bool = False,
    archive: str = "active",
    session_id: str | None = None,
    timezone_name: str = "America/Toronto",
    start: date | None = None,
    end: date | None = None,
) -> Report:
    days: dict[str, int] = {}
    directories: dict[str, int] = {}
    sessions: dict[str, int] = {}
    quality: set[str] = set()
    for session in selected_sessions(
        ledger, cwd=cwd, all_directories=all_directories, archive=archive, session_id=session_id
    ):
        if session.is_child or session.parent_id:
            continue
        quality.update(session.quality)
        sessions[session.id] = 0
        for turn in session.turns.values():
            quality.update(turn.quality)
        for span in segments(list(session.turns.values())):
            if not all_directories and Path(span.cwd).resolve() != Path(cwd).resolve():
                continue
            for day, micros in daily_microseconds([span], timezone_name).items():
                if (start and day < start.isoformat()) or (end and day > end.isoformat()):
                    continue
                days[day] = days.get(day, 0) + micros
                directories[span.cwd] = directories.get(span.cwd, 0) + micros
                sessions[session.id] += micros
    return {
        "timezone": timezone_name,
        "total_seconds": sum(days.values()) / 1_000_000,
        "total_microseconds": sum(days.values()),
        "days": {day: micros / 1_000_000 for day, micros in sorted(days.items())},
        "directories": {cwd: micros / 1_000_000 for cwd, micros in sorted(directories.items())},
        "sessions": {sid: micros / 1_000_000 for sid, micros in sorted(sessions.items())},
        "quality": sorted(quality),
        "diagnostics": ledger.diagnostics,
    }
