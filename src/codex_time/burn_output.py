"""Human and reproducible machine output for allowance workload estimates."""

import csv
import io
import json
import os
from collections import Counter
from datetime import date, datetime
from zoneinfo import ZoneInfo

from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from codex_time.burn import BurnReport, BurnRow
from codex_time.presentation import safe_text


def burn_csv(data: BurnReport) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(BurnRow.__annotations__))
    writer.writeheader()
    for row in data["rows"]:
        writer.writerow(
            {**row, "mix": json.dumps(row["mix"]), "quality": json.dumps(row["quality"])}
        )
    return output.getvalue()


def working_duration(hours: float) -> str:
    seconds = max(0, round(hours * 3600))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    hour, minute = divmod(minutes, 60)
    return f"{hour}h {minute:02}m" if hour else f"{minute}m"


def local_stamp(value: str | int, zone: ZoneInfo) -> str:
    stamp = (
        datetime.fromtimestamp(value, zone)
        if isinstance(value, int)
        else (datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(zone))
    )
    return f"{stamp:%b} {stamp.day}, {stamp:%I:%M %p %Z}".replace(", 0", ", ")


def burn_table(
    data: BurnReport,
    *,
    width: int = 88,
    color: bool = False,
    details: bool = False,
    plain: bool = False,
) -> str:
    """Readable terminal projection; machine exports retain all original evidence."""
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
    zone = ZoneInfo(data["timezone"])
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

    def bar(percentage: float, size: int) -> Text:
        filled = round(max(0, min(100, percentage)) * size / 100)
        result = Text(("#" if plain else "━") * filled, style="green")
        result.append(("-" if plain else "·") * (size - filled), style="bright_black")
        return result

    def model_work(row: BurnRow) -> None:
        say(icon("🤖") + "Model work", "bold")
        if not row["mix"]:
            say("No matched working intervals.", "dim")
            return
        if width < 60:
            for item in row["mix"]:
                say(item["model_id"] or "Unknown", "bold")
                say(
                    f"  {item['reasoning_level'] or 'Unknown'}  |  "
                    f"{working_duration(item['working_microseconds'] / 3_600_000_000)}"
                    f"  |  {item['percentage']:.1f}%"
                )
            return
        table = Table(
            box=None,
            padding=(0, 1),
            pad_edge=False,
            expand=False,
            header_style="dim",
            collapse_padding=False,
        )
        table.add_column("Model", overflow="fold")
        table.add_column("Reasoning", overflow="fold")
        table.add_column("Working", justify="right", width=8)
        table.add_column("Share of work", justify="right", width=19 if width >= 76 else 13)
        for item in row["mix"]:
            share = Text()
            if width >= 76:
                share.append_text(bar(item["percentage"], 10))
                share.append("  ")
            share.append(f"{item['percentage']:5.1f}%")
            table.add_row(
                text(item["model_id"] or "Unknown", "bold"),
                text(item["reasoning_level"] or "Unknown"),
                text(working_duration(item["working_microseconds"] / 3_600_000_000)),
                share,
            )
        console.print(table)

    first, last = date.fromisoformat(data["from"]), date.fromisoformat(data["to"])
    calendar = f"{first:%a, %b} {first.day}, {first.year}"
    if first != last:
        year = f", {first.year}" if first.year != last.year else ""
        calendar = f"{first:%b} {first.day}{year} - {last:%b} {last.day}, {last.year}"
    window = (
        "Weekly allowance"
        if data["window_minutes"] == 10080
        else (f"{data['window_minutes'] / 60:g}-hour allowance")
    )
    say()
    say(icon("🔥") + "Codex allowance", "bold")
    say(f"{calendar}  {separator}  {data['timezone']}", "dim")
    say(window, "dim")
    say()
    latest = data["latest"]
    if latest is not None:
        remaining = latest.get("remaining_percent")
        used = latest.get("used_percent")
        at = latest.get("at")
        if isinstance(remaining, (int, float)) and isinstance(used, (int, float)):
            summary = text(icon("🔋") + f"{remaining:g}% remaining", "bold")
            summary.append(f"   {used:g}% used", style="dim")
            console.print(summary)
            console.print(bar(remaining, min(32, width - 2)))
        if isinstance(at, str):
            say(f"Observed {local_stamp(at, zone)}", "dim")
        say()
    if not data["rows"]:
        say("No allowance readings for this period.", "bold")
        say("Check codex-time health, or choose a date with recorded usage.")
    else:
        counts = Counter(row["date"] for row in data["rows"])
        multiple_streams = len({(r["plan_type"], r["bucket"]) for r in data["rows"]}) > 1
        runs: Counter[str] = Counter()
        for row in data["rows"]:
            selected = date.fromisoformat(row["date"])
            label = f"{selected:%a, %b} {selected.day}"
            runs[row["date"]] += 1
            if counts[row["date"]] > 1 and not multiple_streams:
                label += f" {separator} Run {runs[row['date']]}"
            if len(data["rows"]) > 1:
                console.print(
                    Rule(text(label), align="left", characters="-" if plain else "─", style="dim")
                )
                if multiple_streams:
                    say(f"{row['plan_type'] or 'Unknown plan'} / {row['bucket']}", "dim")
                say(f"Reset {local_stamp(row['resets_at'], zone)}", "dim")
            rate = row["points_per_working_hour"]
            say(
                icon("⚡")
                + (
                    f"{rate:.2f} pts / working hour"
                    if rate is not None
                    else "Burn rate unavailable"
                ),
                "bold",
            )
            say(
                f"{row['matched_points']:g} pts matched  {separator}  "
                f"{working_duration(row['working_hours'])} working",
                "dim",
            )
            say()
            model_work(row)
            say()
            excluded = [
                (row["excluded_gap_points"], "across observation gaps"),
                (row["excluded_no_work_points"], "without recorded work"),
                (row["excluded_boundary_points"], "across day boundaries"),
            ]
            for points, reason in excluded:
                if points:
                    say(icon("↳") + f"{points:g} pts excluded {reason}.", "yellow")
            say(icon("⚠") + f"Rough estimate {separator} low confidence", "yellow")
            sensitivity = row["rounding_sensitivity_points_per_hour"]
            if sensitivity is not None and rate is not None and sensitivity > rate:
                say("Rounded readings can outweigh this rate.", "dim")
            if any(q in row["quality"] for q in ("observation_gap", "historical_upper_bound")):
                say("Some working time is estimated.", "dim")
            if "conflicting_quota_observation" in row["quality"]:
                say("Conflicting readings were left out.", "yellow")
            if details:
                say()
                say("Evidence", "bold")
                say(f"Plan / bucket: {row['plan_type'] or 'Unknown'} / {row['bucket']}")
                say(f"Reset: {local_stamp(row['resets_at'], zone)} ({row['resets_at']})")
                say(
                    f"Matched windows: {row['matched_windows']}; "
                    f"stale readings skipped: {row['stale_readings']}"
                )
                if sensitivity is not None:
                    say(f"Rounding sensitivity: +/-{sensitivity:.2f} pts/h")
                say(f"Timing uncertainty: {row['sampling_uncertainty_seconds']:.2f}s")
                say("Flags: " + ", ".join(row["quality"]))
            say()
        say("pts = allowance percentage points; concurrent working hours add.", "dim")
        say("Model shares describe work, including tools and delegation.", "dim")
    if details:
        say(
            f"Limit: {data['limit_id']}; window: {data['window_minutes']} min; "
            f"maximum observation gap: {data['max_gap_seconds']}s",
            "dim",
        )
        for message in data["diagnostics"]:
            say("Diagnostic: " + message, "dim")
    else:
        say("More evidence: --details", "dim")
    return "\n".join(line.rstrip() for line in output.getvalue().splitlines())
