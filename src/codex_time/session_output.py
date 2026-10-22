"""Compact human summaries; machine output keeps the complete stored evidence."""

import io
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rich.console import Console
from rich.text import Text

from codex_time.model_output import _working_duration
from codex_time.models import Ledger
from codex_time.output_notes import diagnostic_note, quality_note
from codex_time.presentation import SessionRow, safe_text
from codex_time.reporting import Report


def _duration(seconds: float) -> str:
    return _working_duration(round(seconds * 1_000_000))


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" + ("" if number == 1 else "s")


def _render(lines: Sequence[str], width: int, plain: bool) -> str:
    output = io.StringIO()
    console = Console(
        file=output,
        width=max(20, min(width, 96)),
        color_system=None,
        no_color=True,
        markup=False,
        highlight=False,
    )
    for line in lines:
        line = safe_text(line)
        if plain:
            line = line.encode("ascii", "backslashreplace").decode()
        console.print(Text(line, overflow="fold"))
    return output.getvalue().rstrip()


def _heading(emoji: str, text: str, plain: bool) -> str:
    return text if plain else f"{emoji} {text}"


def _directory_names(paths: Sequence[str]) -> dict[str, str]:
    names = {path: Path(path).name or path for path in paths}
    counts = Counter(names.values())
    return {path: path if counts[name] > 1 else name for path, name in names.items()}


def progress_text(message: str, *, width: int = 88, plain: bool = False) -> str:
    return _render([_heading("⏳", message, plain)], width, plain)


def sessions_text(
    rows: Sequence[SessionRow],
    *,
    width: int = 88,
    details: bool = False,
    plain: bool = False,
) -> str:
    lines = [_heading("💬", _count(len(rows), "session"), plain)]
    directories = _directory_names([row.cwd for row in rows])
    if not rows:
        lines.extend(
            ["No sessions match this directory or filter.", "Try --all-dirs or --archive all."]
        )
    for row in rows:
        state = {
            "working": "Working",
            "idle": "Idle",
            "waiting": "Waiting",
            "unknown": "State unknown",
        }.get(row.state, row.state)
        lines.extend(
            [
                "",
                row.title + (" (archived)" if row.archived else ""),
                f"{_duration(row.today)} today | {_duration(row.total)} total | {state}",
                f"{directories[row.cwd]} | {row.model_id or 'Model unknown'}"
                + (f" / {row.reasoning_level}" if row.reasoning_level else ""),
            ]
        )
        if details:
            lines.extend([f"ID: {row.id}", f"Directory: {row.cwd}"])
        if "child_excluded" in row.quality.split(","):
            lines.append("Child session; time counted in parent.")
    note = quality_note(
        sorted(
            {
                flag
                for row in rows
                for flag in row.quality.split(",")
                if flag not in {"observed", "child_excluded"}
            }
        )
    )
    if note:
        lines.extend(["", _heading("⚠️", note, plain)])
    if rows and not details:
        lines.extend(["", "Full IDs and paths: --details"])
    return _render(lines, width, plain)


def history_text(
    data: Report,
    ledger: Ledger,
    *,
    width: int = 88,
    details: bool = False,
    plain: bool = False,
) -> str:
    directories = _directory_names(list(data["directories"]))
    working_sessions = {sid: seconds for sid, seconds in data["sessions"].items() if seconds > 0}
    session_rows = data["sessions"] if details else working_sessions
    omitted = len(data["sessions"]) - len(working_sessions)
    lines = [
        _heading("🕒", "Working time", plain),
        f"{_duration(data['total_seconds'])} | {_count(len(data['days']), 'day')}",
        f"{_count(len(working_sessions), 'session')} with recorded work | "
        f"{len(data['sessions'])} selected",
        data["timezone"],
    ]
    if not data["sessions"]:
        lines.extend(
            ["", "No sessions match this directory or filter.", "Try --all-dirs or --archive all."]
        )
    elif not data["days"]:
        lines.extend(["", "No recorded working time in this date range."])
    for label, entries in (
        ("📅 Daily usage", data["days"]),
        ("📁 Directories", data["directories"]),
        ("💬 Sessions", session_rows),
    ):
        if not entries:
            continue
        lines.extend(["", label[2:] if plain else label])
        for key, seconds in entries.items():
            if entries is data["days"]:
                name = date.fromisoformat(key).strftime("%a, %b %-d, %Y")
            elif entries is data["directories"]:
                name = key if details else directories[key]
            else:
                session = ledger.sessions.get(key)
                name = session.title.strip() if session and session.title.strip() else key[:8]
            lines.append(f"{_duration(seconds):>8}  {name}")
            if entries is session_rows and details:
                lines.append(f"  ID: {key}")
    for note in (quality_note(data["quality"]), diagnostic_note(data["diagnostics"])):
        if note:
            lines.extend(["", _heading("⚠️", note, plain)])
    if data["sessions"] and not details:
        if omitted:
            lines.extend(["", f"{_count(omitted, 'session')} with no recorded work omitted."])
        lines.extend(["", "All selected sessions, IDs and paths: --details"])
    return _render(lines, width, plain)


def health_text(
    data: Mapping[str, object],
    *,
    timezone: str,
    width: int = 88,
    details: bool = False,
    plain: bool = False,
) -> str:
    running = data.get("daemon") == "running"
    sampling = data.get("sampling_interval_seconds", 60)
    interval = f"{sampling:g}s" if isinstance(sampling, (float, int)) else "unknown"
    lines = [
        _heading("🩺", "Codex Time health", plain),
        _heading(
            "✅" if running else "⚠️",
            "Observer running" if running else "Observer stopped or heartbeat stale",
            plain,
        ),
        f"{data.get('sessions', 0)} recorded session"
        + ("" if data.get("sessions") == 1 else "s")
        + f" | sampling every {interval}",
    ]
    heartbeat = data.get("heartbeat")
    if isinstance(heartbeat, str):
        try:
            heartbeat = (
                datetime.fromisoformat(heartbeat)
                .astimezone(ZoneInfo(timezone))
                .strftime("%a, %b %-d, %-I:%M %p %Z")
            )
        except ValueError:
            heartbeat = "Unavailable"
    lines.append(f"Last heartbeat: {heartbeat or 'Not recorded'}")
    if data.get("live_diagnostic"):
        lines.append(_heading("⚠️", "Live connection unavailable; timing may be incomplete.", plain))
    diagnostics = data.get("diagnostics")
    note = diagnostic_note(
        [str(item) for item in diagnostics] if isinstance(diagnostics, list) else []
    )
    if note:
        lines.append(_heading("⚠️", note, plain))
    if details:
        for key, label in (
            ("pid", "Process ID"),
            ("data_dir", "Data directory"),
            ("state_dir", "Runtime directory"),
            ("notification_mode", "File notifications"),
        ):
            lines.append(f"{label}: {data.get(key) or 'Not available'}")
    return _render(lines, width, plain)


def status_text(
    data: Mapping[str, object],
    *,
    width: int = 88,
    details: bool = False,
    plain: bool = False,
) -> str:
    raw = data.get("sessions")
    entries = [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
    directories = _directory_names(
        [str(entry.get("cwd") or "Directory unknown") for entry in entries]
    )
    freshness = "Fresh" if data.get("fresh") else "Incomplete; retry status"
    lines = [_heading("📋", f"{freshness} session state", plain), _count(len(entries), "session")]
    if not entries:
        lines.append("No recorded session state yet.")
    for entry in sorted(
        entries, key=lambda item: str(item.get("last_updated") or ""), reverse=True
    )[:20]:
        sid = str(entry.get("session_id", ""))
        state = {"mid_turn": "Working", "idle": "Idle"}.get(str(entry.get("status")), "Unknown")
        cwd = str(entry.get("cwd") or "Directory unknown")
        lines.append(f"{sid if details else sid[:8]}  {state}  {directories[cwd]}")
        if details:
            lines.extend([f"  Directory: {cwd}", f"  Terminal: {entry.get('tty') or 'Unknown'}"])
    if len(entries) > 20:
        lines.append(f"{_count(len(entries) - 20, 'more session')}; use --json for all.")
    elif entries and not details:
        lines.append("Full IDs and paths: --details or --json")
    if details:
        lines.append(f"Cache: {data.get('cache_path', 'Unavailable')}")
    return _render(lines, width, plain)


def import_summary(
    count: int, diagnostics: Sequence[str], *, width: int = 88, plain: bool = False
) -> tuple[str, str]:
    summary = _heading(
        "✅",
        f"Imported {_count(count, 'session')}; no duplicate intervals.",
        plain,
    )
    notices = (
        [
            _heading("⚠️", _count(len(diagnostics), "import notice") + ".", plain),
            "Inspect: codex-time health --json",
        ]
        if diagnostics
        else []
    )
    return _render([summary], width, plain), _render(notices, width, plain)
