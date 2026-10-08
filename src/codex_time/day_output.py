"""Readable daily working time grouped by original directory and session."""

import io
import os
from datetime import date
from pathlib import PurePath

from rich.console import Console
from rich.padding import Padding
from rich.text import Text

from codex_time.presentation import safe_text
from codex_time.reporting import DailyReport


def _working_duration(microseconds: int) -> str:
    """Keep seconds visible and avoid displaying nonzero short work as zero."""
    microseconds = max(0, microseconds)
    if 0 < microseconds < 1_000_000:
        return f"{microseconds / 1_000_000:.6f}".rstrip("0") + "s"
    minutes, seconds = divmod(microseconds // 1_000_000, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s" if minutes else f"{seconds}s"


def day_table(
    data: DailyReport,
    *,
    width: int = 88,
    color: bool = False,
    details: bool = False,
    plain: bool = False,
) -> str:
    """Render a day total, directory shares, and indented contributing sessions."""
    output = io.StringIO()
    width = max(20, min(width, 96))
    color = color and not plain and "NO_COLOR" not in os.environ
    console = Console(
        file=output,
        width=width,
        force_terminal=color,
        color_system="standard" if color else None,
        no_color=not color,
        highlight=False,
        markup=False,
    )

    def say(value: str = "", style: str = "", *, indent: int = 0) -> None:
        value = safe_text(value)
        if plain:
            value = value.encode("ascii", "backslashreplace").decode()
        text = Text(value, style=style, overflow="fold")
        console.print(Padding(text, (0, 0, 0, indent)) if indent else text)

    def icon(value: str) -> str:
        return "" if plain else value + " "

    def flags(quality: list[str], *, indent: int = 0) -> None:
        if details and quality:
            say("Flags: " + ", ".join(quality), "dim", indent=indent)

    selected = date.fromisoformat(data["date"])
    say()
    say(icon("🕒") + "Codex daily work", "bold")
    say(f"{selected:%a, %b} {selected.day}, {selected.year}", "dim")
    say(data["timezone"], "dim")
    say()
    say("Day total", "bold")
    say(_working_duration(data["total_microseconds"]), "bold green")
    flags(data["quality"])
    say()

    if not data["directories"]:
        say("No recorded work for this day.", "bold")
        say("Choose another date with --date YYYY-MM-DD, or check codex-time status.")
    else:
        say("Directory shares", "bold")
        size = max(4, min(24, width - 12))
        for directory in data["directories"]:
            say(directory["cwd"] or "Unknown directory", "bold")
            share = max(0, min(100, directory["share_percent"]))
            filled = max(1, round(share * size / 100)) if share > 0 else 0
            progress = Text(("#" if plain else "━") * filled, style="cyan")
            progress.append(("-" if plain else "·") * (size - filled), style="bright_black")
            progress.append(f"  {share:5.1f}%")
            console.print(Padding(progress, (0, 0, 0, 2)))
            say("Time: " + _working_duration(directory["total_microseconds"]), indent=2)
        say()
        say("Session details", "bold")
        for directory in data["directories"]:
            cwd = directory["cwd"]
            title = PurePath(cwd).name or cwd or "Unknown directory"
            say(icon("📁") + title, "bold")
            say(cwd or "Unknown directory", "dim", indent=2)
            say("Time: " + _working_duration(directory["total_microseconds"]), "bold", indent=2)
            say(f"Share: {directory['share_percent']:.1f}%", "dim", indent=2)
            flags(directory["quality"], indent=2)
            for session in directory["sessions"]:
                say(session["title"].strip() or "Untitled session", "bold", indent=2)
                say("ID: " + session["id"], "dim", indent=4)
                say("Time: " + _working_duration(session["total_microseconds"]), indent=4)
                flags(session["quality"], indent=4)
            say()
        say("Some work may be estimated; concurrent sessions add.", "dim")

    if details:
        for message in data["diagnostics"]:
            say("Diagnostic: " + message, "dim")
    else:
        say("More evidence: --details", "dim")
    return "\n".join(line.rstrip() for line in output.getvalue().splitlines())
