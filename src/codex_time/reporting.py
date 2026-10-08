"""Directory-attributed reports from durable disjoint work segments."""

from datetime import date, datetime
from pathlib import Path
from typing import TypedDict
from zoneinfo import ZoneInfo

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


class SessionTime(TypedDict):
    id: str
    title: str
    total_seconds: float
    total_microseconds: int
    quality: list[str]


class DirectoryTime(TypedDict):
    cwd: str
    total_seconds: float
    total_microseconds: int
    share_percent: float
    sessions: list[SessionTime]
    quality: list[str]


class DailyReport(TypedDict):
    date: str
    timezone: str
    total_seconds: float
    total_microseconds: int
    directories: list[DirectoryTime]
    quality: list[str]
    diagnostics: list[str]


def daily_report(
    ledger: Ledger,
    *,
    selected_date: date | None = None,
    cwd: str | None = None,
    archive: str = "all",
    session_id: str | None = None,
    timezone_name: str = "America/Toronto",
) -> DailyReport:
    """Project one local day's work into directory/session groups without writes."""
    zone = ZoneInfo(timezone_name)
    day = (selected_date or datetime.now(zone).date()).isoformat()
    counted: dict[str, dict[str, SessionTime]] = {}
    directory_filter = Path(cwd).resolve() if cwd is not None else None
    for session in selected_sessions(
        ledger,
        cwd=cwd or "/",
        all_directories=cwd is None,
        archive=archive,
        session_id=session_id,
    ):
        if session.is_child or session.parent_id:
            continue
        for span in segments(list(session.turns.values())):
            if directory_filter is not None and Path(span.cwd).resolve() != directory_filter:
                continue
            micros = daily_microseconds([span], timezone_name).get(day, 0)
            if not micros:
                continue
            rows = counted.setdefault(span.cwd, {})
            if session.id not in rows:
                rows[session.id] = {
                    "id": session.id,
                    "title": session.title,
                    "total_seconds": 0,
                    "total_microseconds": 0,
                    "quality": list(session.quality),
                }
            row = rows[session.id]
            row["total_microseconds"] += micros
            row["quality"] = sorted(set(row["quality"]) | set(span.quality))
    total = sum(row["total_microseconds"] for rows in counted.values() for row in rows.values())
    directories: list[DirectoryTime] = []
    for directory, rows in counted.items():
        sessions = sorted(rows.values(), key=lambda row: (-row["total_microseconds"], row["id"]))
        for row in sessions:
            row["total_seconds"] = row["total_microseconds"] / 1_000_000
        micros = sum(row["total_microseconds"] for row in sessions)
        directories.append(
            {
                "cwd": directory,
                "total_seconds": micros / 1_000_000,
                "total_microseconds": micros,
                "share_percent": micros * 100 / total,
                "sessions": sessions,
                "quality": sorted({q for row in sessions for q in row["quality"]}),
            }
        )
    directories.sort(key=lambda row: (-row["total_microseconds"], row["cwd"]))
    return {
        "date": day,
        "timezone": timezone_name,
        "total_seconds": total / 1_000_000,
        "total_microseconds": total,
        "directories": directories,
        "quality": sorted({q for directory in directories for q in directory["quality"]}),
        "diagnostics": list(ledger.diagnostics),
    }
