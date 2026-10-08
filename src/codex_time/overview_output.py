"""Readable combined usage, with reasoning nested beneath independently counted models."""

import os
from datetime import date
from io import StringIO
from zoneinfo import ZoneInfo

from rich.cells import cell_len
from rich.console import Console
from rich.table import Table
from rich.text import Text

from codex_time.burn_output import local_stamp
from codex_time.model_output import _working_duration
from codex_time.model_usage import ModelUsageRow
from codex_time.overview import OverviewReport
from codex_time.presentation import safe_text


def overview_table(
    data: OverviewReport,
    *,
    width: int = 88,
    color: bool = False,
    details: bool = False,
    plain: bool = False,
) -> str:
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
    allowance, models = data["allowance"], data["model_totals"]
    zone = ZoneInfo(models["timezone"])
    separator = "|" if plain else "·"

    def text(value: str, style: str = "") -> Text:
        value = safe_text(value)
        if plain:
            value = value.encode("ascii", "backslashreplace").decode()
        return Text(value, style=style, overflow="fold")

    def say(value: str = "", style: str = "") -> None:
        console.print(text(value, style))

    def heading(label: str, icon: str) -> None:
        say(("" if plain else icon + " ") + label, "bold cyan")

    def bar(percentage: float, size: int, *, show_positive: bool = False) -> Text:
        filled = round(max(0, min(100, percentage)) * size / 100)
        if show_positive and percentage > 0:
            filled = max(1, filled)
        result = Text(("#" if plain else "━") * filled, style="cyan")
        result.append(("-" if plain else "·") * (size - filled), style="bright_black")
        return result

    def share(percentage: float, *, bars: bool = True) -> Text:
        result = bar(percentage, 10, show_positive=True) if bars else Text()
        if bars:
            result.append("  ")
        result.append("<0.01%" if 0 < percentage < 0.005 else f"{percentage:.2f}%")
        return result

    first, last = date.fromisoformat(models["from"]), date.fromisoformat(models["to"])
    calendar = f"{first:%a, %b} {first.day}, {first.year}"
    if first != last:
        year = f", {first.year}" if first.year != last.year else ""
        calendar = f"{first:%b} {first.day}{year} - {last:%b} {last.day}, {last.year}"
    say()
    heading("Codex overview", "📊")
    say(f"{calendar} {separator} {models['timezone']}", "dim")
    say(f"Recorded work: {_working_duration(models['total_microseconds'])}", "bold")
    say()
    heading("Allowance", "🔋")
    say(
        "Weekly allowance"
        if allowance["window_minutes"] == 10080
        else f"{allowance['window_minutes'] / 60:g}-hour allowance",
        "dim",
    )
    latest = allowance["latest"]
    if latest is not None:
        remaining, used = latest.get("remaining_percent"), latest.get("used_percent")
        if isinstance(remaining, (int, float)) and isinstance(used, (int, float)):
            say(f"{remaining:g}% remaining   {used:g}% used", "bold")
            console.print(bar(remaining, min(32, width - 2)))
        at, reset = latest.get("at"), latest.get("resets_at")
        if isinstance(at, str):
            say(f"Observed {local_stamp(at, zone)}", "dim")
        if isinstance(reset, int):
            say(f"Reset {local_stamp(reset, zone)}", "dim")
    elif not allowance["rows"]:
        say("No allowance readings for this period.")
        say("Choose another --date or check codex-time health.", "dim")
    else:
        say("Allowance balance unavailable: no unambiguous latest reading.", "yellow")
    say()
    heading("Observed consumption", "⚡")
    if not allowance["rows"]:
        say("Rate unavailable without allowance readings.", "dim")
    for row in allowance["rows"]:
        selected = date.fromisoformat(row["date"])
        say(
            f"{selected:%a, %b} {selected.day} {separator} "
            f"Reset {local_stamp(row['resets_at'], zone)}",
            "dim",
        )
        if len({(r["plan_type"], r["bucket"]) for r in allowance["rows"]}) > 1:
            say(f"{row['plan_type'] or 'Unknown plan'} / {row['bucket']}", "dim")
        rate = row["points_per_working_hour"]
        say(
            f"{rate:.2f} pts / working hour"
            if rate is not None
            else "Consumption rate unavailable",
            "bold",
        )
        say(
            f"{row['matched_points']:g} pts matched {separator} "
            f"{_working_duration(row['working_microseconds'])} working",
            "dim",
        )
        for points, reason in [
            (row["excluded_gap_points"], "across observation gaps"),
            (row["excluded_no_work_points"], "without recorded work"),
            (row["excluded_boundary_points"], "across day boundaries"),
        ]:
            if points:
                say(f"{points:g} pts excluded {reason}.", "yellow")
        say(f"Rough estimate {separator} low confidence", "yellow")
        sensitivity = row["rounding_sensitivity_points_per_hour"]
        if sensitivity is not None and rate is not None and sensitivity > rate:
            say("Rounded readings can outweigh this rate.", "dim")
        if "conflicting_quota_observation" in row["quality"]:
            say("Conflicting readings were left out.", "yellow")
        if details:
            say("Allowance evidence", "bold")
            say(f"Plan / bucket: {row['plan_type'] or 'Unknown'} / {row['bucket']}")
            say(f"Reset timestamp: {row['resets_at']}")
            say(
                f"Matched windows: {row['matched_windows']}; "
                f"stale readings skipped: {row['stale_readings']}"
            )
            if sensitivity is not None:
                say(f"Rounding sensitivity: +/-{sensitivity:.2f} pts/h")
            say(f"Sampling uncertainty: {row['sampling_uncertainty_seconds']:g}s")
            say("Flags: " + ", ".join(row["quality"]))
            say("Matched model mix", "bold")
            for item in row["mix"]:
                say(
                    f"  {item['model_id'] or 'Unknown'} / {item['reasoning_level'] or 'Unknown'}: "
                    f"{_working_duration(item['working_microseconds'])}; {item['percentage']:.2f}%"
                )
        say()
    heading("Model work", "🤖")
    grouped: dict[str | None, list[ModelUsageRow]] = {}
    for usage in data["reasoning"]["rows"]:
        grouped.setdefault(usage["model_id"], []).append(usage)
    stacked = width < 70 or any(
        cell_len(safe_text(usage["model_id"] or "Unknown")) > max(16, width // 3)
        for usage in models["rows"]
    )
    if not models["rows"]:
        say("No recorded work in this period.")
        say("Choose another --date or check codex-time health.", "dim")
    elif stacked:
        for model in models["rows"]:
            label = f"{model['rank'] or '?'} {model['model_id'] or 'Unknown'}"
            say(label, "bold")
            say(
                f"  {_working_duration(model['working_microseconds'])} {separator} "
                f"{model['session_count']} sessions"
            )
            console.print(share(model["percentage"]))
            for usage in grouped.get(model["model_id"], []):
                say(
                    f"  {'->' if plain else '↳'} {usage['reasoning_level'] or 'Unknown'}",
                    "dim",
                )
                say(
                    f"    {_working_duration(usage['working_microseconds'])} {separator} "
                    f"{usage['session_count']} sessions"
                )
                console.print(Text("    ") + share(usage["percentage"], bars=False))
            say()
    else:
        table = Table(box=None, padding=(0, 1), pad_edge=False, header_style="dim")
        table.add_column("Model / reasoning", overflow="fold")
        table.add_column("Worked", justify="right")
        table.add_column("Share of all work", justify="right")
        table.add_column("Sessions", justify="right")
        for model in models["rows"]:
            table.add_row(
                text(f"{model['rank'] or '?'} {model['model_id'] or 'Unknown'}", "bold"),
                text(_working_duration(model["working_microseconds"])),
                share(model["percentage"]),
                text(f"{model['session_count']} sessions"),
            )
            for usage in grouped.get(model["model_id"], []):
                table.add_row(
                    text(
                        f"  {'->' if plain else '↳'} {usage['reasoning_level'] or 'Unknown'}",
                        "dim",
                    ),
                    text(_working_duration(usage["working_microseconds"])),
                    share(usage["percentage"], bars=False),
                    text(str(usage["session_count"])),
                )
        console.print(table)
        say()
    say("Shares use all recorded work; consumption uses matched work.", "dim")
    say("Concurrent root sessions add; child work is included in its root.", "dim")
    if models["quality"] or models["diagnostics"] or models["sampling_uncertainty_seconds"]:
        say("Times are estimates; some work may be incomplete. Use --details.", "yellow")
    if details:
        say()
        heading("Timing details", "🔎")
        say(f"Total: {models['total_seconds']:g} seconds")
        say(
            f"Sampling uncertainty: {models['sampling_uncertainty_seconds']:g}s "
            "(not additive across rows)"
        )
        for usage in data["reasoning"]["rows"]:
            say(
                f"{usage['model_id'] or 'Unknown'} / {usage['reasoning_level'] or 'Unknown'}: "
                f"{', '.join(usage['quality']) or 'observed'}; "
                f"{usage['sampling_uncertainty_seconds']:g}s uncertainty"
            )
        say(
            f"Limit: {allowance['limit_id']}; window: {allowance['window_minutes']} min; "
            f"maximum observation gap: {allowance['max_gap_seconds']}s"
        )
        for message in models["diagnostics"]:
            say("Diagnostic: " + message)
    else:
        say("More evidence: --details", "dim")
    return "\n".join(line.rstrip() for line in output.getvalue().splitlines())
