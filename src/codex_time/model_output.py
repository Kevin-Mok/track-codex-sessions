"""Readable model working-time rankings and unchanged CSV exports."""

import csv
import json
import os
from datetime import date
from io import StringIO

from rich.cells import cell_len
from rich.console import Console
from rich.table import Table
from rich.text import Text

from codex_time.model_usage import ModelUsageReport, ModelUsageRow
from codex_time.presentation import safe_text


def _working_duration(microseconds: int) -> str:
    if 0 < microseconds < 1_000_000:
        return f"{microseconds / 1_000_000:.6f}".rstrip("0") + "s"
    minutes, seconds = divmod(max(0, microseconds) // 1_000_000, 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def model_table(
    data: ModelUsageReport,
    *,
    width: int = 88,
    color: bool = False,
    details: bool = False,
    plain: bool = False,
) -> str:
    """Present work shares without allowing technical evidence to overwhelm them."""
    output = StringIO()
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
    separator = "|" if plain else "·"

    def text(value: str, style: str = "") -> Text:
        value = safe_text(value)
        if plain:
            value = value.encode("ascii", "backslashreplace").decode()
        return Text(value, style=style, overflow="fold")

    def say(value: str = "", style: str = "") -> None:
        console.print(text(value, style))

    def icon(value: str) -> str:
        return "" if plain else value + " "

    def rank(row: ModelUsageRow) -> str:
        value = row["rank"]
        if value is None:
            return "?" if plain else "—"
        medals = {1: "🏆", 2: "🥈", 3: "🥉"}
        return str(value) if plain else medals.get(value, str(value))

    def percentage_label(value: float) -> str:
        return "<0.01%" if 0 < value < 0.005 else f"{value:.2f}%"

    def share(row: ModelUsageRow) -> Text:
        percentage = row["percentage"]
        result = Text()
        if width >= 88:
            filled = round(max(0, min(100, percentage)) / 10)
            if percentage > 0:
                filled = max(1, filled)
            result.append(("#" if plain else "━") * filled, style="cyan")
            result.append(("-" if plain else "·") * (10 - filled), style="bright_black")
            result.append("  ")
        result.append(percentage_label(percentage))
        return result

    first, last = date.fromisoformat(data["from"]), date.fromisoformat(data["to"])
    calendar = f"{first:%a, %b} {first.day}, {first.year}"
    if first != last:
        year = f", {first.year}" if first.year != last.year else ""
        calendar = f"{first:%b} {first.day}{year} - {last:%b} {last.day}, {last.year}"
    say()
    say(icon("🤖") + f"Model usage {separator} {data['period'].title()}", "bold cyan")
    say(icon("📅") + f"{calendar} {separator} {data['timezone']}", "dim")
    say(icon("⏱️") + f"Working-time usage: {_working_duration(data['total_microseconds'])}", "bold")
    say()
    if not data["rows"]:
        say("No counted work in this period.")
        say("Try another --date or check codex-time health.", "dim")
    elif width < 70 or any(
        cell_len(safe_text(row["model_id"] or "Unknown")) > max(16, width // 3)
        for row in data["rows"]
    ):
        for row in data["rows"]:
            say(f"{rank(row)} {row['model_id'] or 'Unknown'}", "bold")
            if not data["model_only"]:
                say(f"  Reasoning: {row['reasoning_level'] or 'Unknown'}", "dim")
            say(
                f"  {_working_duration(row['working_microseconds'])} {separator} "
                f"{percentage_label(row['percentage'])} of work"
            )
            say(f"  {row['session_count']} sessions", "dim")
            say()
    else:
        table = Table(box=None, padding=(0, 1), pad_edge=False, header_style="dim")
        table.add_column("#", width=2)
        table.add_column("Model", overflow="fold")
        if not data["model_only"]:
            table.add_column("Reasoning", overflow="fold")
        table.add_column("Worked", justify="right", overflow="fold")
        table.add_column("Share", justify="right", overflow="fold")
        table.add_column("Sessions", justify="right")
        for row in data["rows"]:
            values = [text(rank(row)), text(row["model_id"] or "Unknown", "bold")]
            if not data["model_only"]:
                values.append(text(row["reasoning_level"] or "Unknown"))
            values.extend(
                [
                    text(_working_duration(row["working_microseconds"])),
                    share(row),
                    text(str(row["session_count"])),
                ]
            )
            table.add_row(*values)
        console.print(table)
        say()
    say("Share = working time, including tools; simultaneous sessions count separately.", "dim")
    if data["quality"] or data["diagnostics"] or data["sampling_uncertainty_seconds"]:
        say(
            icon("⚠️") + "Times are estimates; some work may be incomplete. Use --details.", "yellow"
        )
    if details:
        say()
        say(icon("🔎") + "Timing details", "bold")
        say(f"Total: {data['total_seconds']:g} seconds")
        say(
            f"Sampling uncertainty: {data['sampling_uncertainty_seconds']:g}s "
            "(not additive across rows)"
        )
        for row in data["rows"]:
            effort = "" if data["model_only"] else f" / {row['reasoning_level'] or 'Unknown'}"
            say(
                f"{row['model_id'] or 'Unknown'}{effort}: "
                f"{', '.join(row['quality']) or 'observed'}; "
                f"{row['sampling_uncertainty_seconds']:g}s uncertainty"
            )
        for message in data["diagnostics"]:
            say(f"Diagnostic: {message}")
    return output.getvalue().rstrip()


def model_csv(data: ModelUsageReport) -> str:
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        [
            "label",
            "period",
            "from",
            "to",
            "timezone",
            "model_only",
            "total_seconds",
            "total_microseconds",
            "rank",
            "model_id",
            "reasoning_level",
            "working_seconds",
            "working_microseconds",
            "percentage",
            "session_count",
            "quality",
            "sampling_uncertainty_seconds",
        ]
    )
    for row in data["rows"]:
        writer.writerow(
            [
                data["label"],
                data["period"],
                data["from"],
                data["to"],
                data["timezone"],
                data["model_only"],
                data["total_seconds"],
                data["total_microseconds"],
                row["rank"],
                row["model_id"] or "Unknown",
                "All" if data["model_only"] else row["reasoning_level"] or "Unknown",
                row["working_seconds"],
                row["working_microseconds"],
                row["percentage"],
                row["session_count"],
                json.dumps(row["quality"]),
                row["sampling_uncertainty_seconds"],
            ]
        )
    return stream.getvalue()
