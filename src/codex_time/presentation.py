"""Curses session browser and content-free, bounded display projections."""

from __future__ import annotations

import curses
import os
import subprocess
import sys
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from codex_time.accounting import daily_totals, segments, total_seconds
from codex_time.model_usage import attributed_segments, latest_model
from codex_time.models import (
    AttributedSegment,
    Ledger,
    Observation,
    Session,
    Span,
    Turn,
    WorkSegment,
)

ArchiveFilter = Literal["active", "archived", "all"]
SortOrder = Literal["updated", "created", "time"]
SnapshotLoader = Callable[[], tuple[Ledger, dict[str, Observation]]]


@dataclass(frozen=True)
class SessionRow:
    id: str
    title: str
    cwd: str
    state: str
    archived: bool
    today: float
    total: float
    quality: str
    intervals: list[AttributedSegment]
    model_id: str | None
    reasoning_level: str | None


def safe_text(value: str) -> str:
    """Never send metadata control characters to the terminal."""
    return "".join(
        " " if char in "\r\n\t" else "?" if unicodedata.category(char).startswith("C") else char
        for char in value
    )


def duration(seconds: float) -> str:
    minutes, second = divmod(max(0, int(seconds)), 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours}:{minute:02}:{second:02}"


def display_segments(
    session: Session, observation: Observation | None, now: datetime
) -> list[WorkSegment]:
    if session.is_child or session.parent_id:
        return []
    turns: list[Turn] = []
    candidates = [
        turn
        for turn in session.turns.values()
        if turn.end is None and observation is not None and turn.start <= observation.at
    ]
    latest = max(candidates, key=lambda turn: (turn.start, turn.id), default=None)
    for turn in session.turns.values():
        fresh = observation is not None and timedelta(0) <= now - observation.at <= timedelta(
            seconds=3
        )
        selected = observation is not None and (
            observation.turn_id == turn.id
            or (observation.turn_id is None and latest is not None and latest.id == turn.id)
        )
        if (
            turn.end is None
            and fresh
            and selected
            and observation is not None
            and (observation.state == "working")
        ):
            turns.append(
                turn.model_copy(
                    update={
                        "coverage": [*turn.coverage, Span(start=observation.at, end=now)],
                        "quality": list(set(turn.quality + ["live_sample_estimate"])),
                    }
                )
            )
        else:
            turns.append(turn)
    return segments(turns)


def build_rows(
    ledger: Ledger,
    observations: dict[str, Observation],
    *,
    cwd: str,
    now: datetime | None = None,
    timezone_name: str = "America/Toronto",
    all_directories: bool = False,
    archive: ArchiveFilter = "active",
    sort: SortOrder = "updated",
    query: str = "",
) -> list[SessionRow]:
    now = now or datetime.now(UTC)
    today = now.astimezone(ZoneInfo(timezone_name)).date().isoformat()
    selected: list[tuple[Session, SessionRow]] = []
    for session in ledger.sessions.values():
        if not all_directories and Path(session.cwd).resolve() != Path(cwd).resolve():
            continue
        if archive != "all" and session.archived != (archive == "archived"):
            continue
        if query.casefold() not in f"{session.id} {session.title} {session.cwd}".casefold():
            continue
        observation = observations.get(session.id)
        state = "unknown"
        if observation is not None and timedelta(0) <= now - observation.at <= timedelta(seconds=3):
            state = observation.state
        work = display_segments(session, observation, now)
        intervals = attributed_segments(session, work)
        quality = set(session.quality)
        for turn in session.turns.values():
            quality.update(turn.quality)
            if turn.end is None:
                quality.add("unfinished")
        for interval in intervals:
            quality.update(interval.quality)
        if session.is_child or session.parent_id:
            quality.add("child_excluded")
        selected.append(
            (
                session,
                SessionRow(
                    session.id,
                    safe_text(session.title.strip() or f"Session {session.id[:8]}"),
                    safe_text(session.cwd),
                    state,
                    session.archived,
                    daily_totals(work, timezone_name).get(today, 0.0),
                    total_seconds(work),
                    ",".join(sorted(quality)) or "observed",
                    intervals,
                    *latest_model(session),
                ),
            )
        )
    selected.sort(
        key=lambda pair: (
            pair[1].total
            if sort == "time"
            else pair[0].created
            if sort == "created"
            else pair[0].updated,
            pair[0].id,
        ),
        reverse=True,
    )
    return [row for _, row in selected]


def launch_session(session: Session, codex_home: Path, *, executable: str = "codex") -> str | None:
    """Run only an explicitly selected session, with no shell or prompt content."""
    if not Path(session.cwd).is_dir():
        return (
            f"Working directory no longer exists: {safe_text(session.cwd)}. "
            "Restore it before resuming."
        )
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home.expanduser())
    try:
        result = subprocess.run(
            [executable, "resume", session.id], cwd=session.cwd, env=env, check=False
        )
    except FileNotFoundError:
        return "Cannot find Codex. Install the codex command and ensure it is on PATH."
    except OSError as error:
        return (
            f"Cannot launch Codex: {safe_text(str(error))}. "
            "Check executable and directory permissions."
        )
    if result.returncode:
        return (
            f"Codex exited with status {result.returncode}. Review its output and retry with Enter."
        )
    return None


def _write(screen: curses.window, y: int, text: str, *, selected: bool = False) -> None:
    height, width = screen.getmaxyx()
    if y < 0 or y >= height or width < 2:
        return
    try:
        screen.addnstr(
            y, 0, safe_text(text), width - 1, curses.A_REVERSE if selected else curses.A_NORMAL
        )
    except curses.error:
        # Curses can reject wide characters or terminal resize races.
        pass


def _details(row: SessionRow, timezone_name: str) -> list[str]:
    lines = [
        f"{row.title}  {row.id}",
        row.cwd,
        f"{row.state} | {'Archived' if row.archived else 'Active'} | {row.quality}",
        f"Latest observed model: {row.model_id or 'Unknown'} / {row.reasoning_level or 'Unknown'}",
        "Daily working time:",
    ]
    lines.extend(
        f"{day}  {duration(total)}"
        for day, total in sorted(
            daily_totals(list(row.intervals), timezone_name).items(), reverse=True
        )
    )
    lines.append("Intervals (UTC; attributed model and directory):")
    lines.extend(
        f"{span.start.isoformat()} -> {span.end.isoformat()}  "
        f"{duration((span.end - span.start).total_seconds())}  "
        f"{span.model_id or 'Unknown'} / {span.reasoning_level or 'Unknown'}  {span.cwd}"
        for span in reversed(row.intervals)
    )
    return lines


def _browse(
    screen: curses.window, load: SnapshotLoader, timezone_name: str, cwd: str, codex_home: Path
) -> None:
    screen.timeout(1000)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    index = 0
    archive: ArchiveFilter = "active"
    sort: SortOrder = "updated"
    all_directories = False
    query = ""
    searching = False
    details = False
    detail_offset = 0
    notice = ""
    previous_id = ""
    while True:
        try:
            ledger, observations = load()
        except (OSError, ValueError) as error:
            ledger, observations = Ledger(), {}
            notice = f"Cannot read snapshot: {error}; retrying."
        rows = build_rows(
            ledger,
            observations,
            cwd=cwd,
            timezone_name=timezone_name,
            all_directories=all_directories,
            archive=archive,
            sort=sort,
            query=query,
        )
        if previous_id:
            index = next((i for i, row in enumerate(rows) if row.id == previous_id), index)
        index = max(0, min(index, len(rows) - 1))
        previous_id = rows[index].id if rows else ""
        screen.erase()
        height, _ = screen.getmaxyx()
        _write(
            screen,
            0,
            f"Codex time | {'All directories' if all_directories else cwd} | "
            f"{archive} | {sort} | {timezone_name}",
        )
        _write(screen, 1, f"Search: {query}{'_' if searching else ''}")
        body_height = max(0, height - 5)
        if details and rows:
            lines = _details(rows[index], timezone_name)
            detail_offset = max(0, min(detail_offset, max(0, len(lines) - body_height)))
            for y, line in enumerate(lines[detail_offset : detail_offset + body_height], 2):
                _write(screen, y, line)
        else:
            visible_rows = max(1, body_height // 4)
            offset = max(0, index - visible_rows + 1)
            for row_index, row in enumerate(rows[offset : offset + visible_rows]):
                y = 2 + row_index * 4
                selected = offset + row_index == index
                _, width = screen.getmaxyx()
                title_width = max(1, width - 30)
                _write(
                    screen,
                    y,
                    f"{row.title[:title_width]} | {row.state} | "
                    f"{'Archived' if row.archived else 'Active'}",
                    selected=selected,
                )
                _write(
                    screen,
                    y + 1,
                    f"today {duration(row.today)} | total {duration(row.total)} | {row.quality}",
                    selected=selected,
                )
                _write(
                    screen,
                    y + 2,
                    f"Model: {row.model_id or 'Unknown'} / {row.reasoning_level or 'Unknown'}",
                    selected=selected,
                )
                _write(screen, y + 3, row.cwd, selected=selected)
            if not rows:
                _write(
                    screen,
                    2,
                    "No matching sessions. Press a for all directories or r for archives.",
                )
        _write(screen, height - 3, notice)
        _write(
            screen,
            height - 2,
            "↑/↓ select  Enter resume  / search  a directories  r archive  s sort",
        )
        _write(screen, height - 1, "d details/back  Esc clear/back  q quit (tracking continues)")
        screen.refresh()
        try:
            key = screen.get_wch()
        except curses.error:
            continue
        if searching:
            if key in ("\n", "\r", "\x1b"):
                searching = False
            elif key in ("\b", "\x7f", curses.KEY_BACKSPACE):
                query = query[:-1]
                index = 0
            elif isinstance(key, str) and key.isprintable():
                query += key
                index = 0
            previous_id = ""
            continue
        if key == "q":
            return
        if key == "\x1b":
            if details:
                details = False
            else:
                query = ""
        elif key == "/":
            searching = True
        elif key == "a":
            all_directories = not all_directories
            index = 0
            previous_id = ""
        elif key == "r":
            archive = {"active": "archived", "archived": "all", "all": "active"}[archive]  # type: ignore[assignment]
            index = 0
            previous_id = ""
        elif key == "s":
            sort = {"updated": "created", "created": "time", "time": "updated"}[sort]  # type: ignore[assignment]
        elif key == "d":
            details = not details
            detail_offset = 0
        elif key in (curses.KEY_UP, "k"):
            if details:
                detail_offset -= 1
            else:
                index = max(0, index - 1)
                previous_id = ""
        elif key in (curses.KEY_DOWN, "j"):
            if details:
                detail_offset += 1
            else:
                index = min(len(rows) - 1, index + 1)
                previous_id = ""
        elif key in ("\n", "\r", curses.KEY_ENTER) and rows:
            curses.def_prog_mode()
            curses.endwin()
            try:
                notice = launch_session(ledger.sessions[rows[index].id], codex_home) or ""
            except KeyboardInterrupt:
                notice = "Codex interrupted. Press Enter to resume again."
            finally:
                curses.reset_prog_mode()
                screen.refresh()
                screen.timeout(1000)


def run_ui(load: SnapshotLoader, timezone_name: str, cwd: str, codex_home: Path) -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError(
            "The session browser needs a terminal. "
            "Use codex-time sessions for noninteractive output."
        )
    try:
        curses.wrapper(_browse, load, timezone_name, cwd, codex_home)
    except KeyboardInterrupt:
        return
