"""Compact, responsive working-time and token-cost reports by directory/session."""

import io
import os
from collections import Counter
from datetime import date
from pathlib import PurePath

from rich.cells import cell_len
from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from codex_time.presentation import safe_text
from codex_time.reporting import DailyReport
from codex_time.token_output import compact_tokens, money, provenance, usage_details, usage_line
from codex_time.token_reporting import UsageSummary


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


def _usage_cells(usage: UsageSummary | None) -> tuple[str, str, str]:
    """Currency headers provide units; missing evidence must never look free."""
    if usage is None or usage["status"] == "unavailable":
        return ("unavailable",) * 3
    if usage["status"] == "excluded":
        return ("excluded",) * 3
    if (
        usage["tokens"]["total_tokens"] is None
        and not usage["priced_tokens"]
        and not usage["unpriced_tokens"]
    ):
        return ("unavailable",) * 3
    tokens = compact_tokens(usage["tokens"]["total_tokens"])
    if not usage["priced_tokens"] and usage["unpriced_tokens"]:
        return tokens, "unpriced", "unpriced" if usage["cad"] is not None else "unavailable"
    suffix = "*" if not usage["cost_complete"] else ""
    usd = money(usage["usd"], "USD").removeprefix("USD ") + suffix
    cad = money(usage["cad"], "CAD").removeprefix("CAD ")
    if usage["cad"] is not None:
        cad += suffix
    return tokens, usd, cad


def _same_usage(left: UsageSummary, right: UsageSummary) -> bool:
    """Only omit a model's duplicated costs when its underlying totals agree."""
    return all(
        left[key] == right[key]
        for key in (
            "status",
            "tokens",
            "usd",
            "cad",
            "cost_complete",
            "priced_tokens",
            "unpriced_tokens",
        )
    )


def _share(value: float) -> str:
    return "<0.1%" if 0 < value < 0.1 else f"{value:.1f}%"


def day_table(
    data: DailyReport,
    *,
    width: int = 88,
    color: bool = False,
    details: bool = False,
    plain: bool = False,
) -> str:
    """Keep every project/session/model visible without repeated metric blocks."""
    output = io.StringIO()
    width = max(20, min(width, 160))
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

    def text(value: str, style: str = "") -> Text:
        value = safe_text(value)
        if plain:
            value = value.encode("ascii", "backslashreplace").decode()
        return Text(value, style=style, overflow="fold")

    def say(value: str = "", style: str = "", *, indent: int = 0) -> None:
        rendered = text(value, style)
        console.print(Padding(rendered, (0, 0, 0, indent)) if indent else rendered)

    def icon(value: str) -> str:
        return "" if plain else value + " "

    def flags(quality: list[str], *, indent: int = 0) -> None:
        if details and quality:
            say("Flags: " + ", ".join(quality), "dim", indent=indent)

    def rows(headers: list[str], values: list[list[str]], styles: list[str]) -> None:
        """Use columns when each value and a readable label fit; otherwise stack."""
        sizes = [
            max(cell_len(header), *(cell_len(row[index]) for row in values))
            for index, header in enumerate(headers)
            if index
        ]
        if width >= 80 and sum(sizes) + 2 * (len(headers) - 1) + 22 <= width:
            table = Table(box=None, padding=(0, 1), pad_edge=False, expand=True)
            table.add_column(headers[0], min_width=22, overflow="fold")
            for header, size in zip(headers[1:], sizes, strict=True):
                table.add_column(header, width=size, justify="right", no_wrap=True)
            for row, style in zip(values, styles, strict=True):
                table.add_row(text(row[0], style), *(text(value) for value in row[1:]))
            console.print(table)
        else:
            for row, style in zip(values, styles, strict=True):
                say(row[0], style)
                say(
                    " | ".join(
                        f"{key}: {value}" for key, value in zip(headers[1:], row[1:], strict=True)
                    ),
                    indent=2,
                )

    period = data.get("period", "day")
    selected = date.fromisoformat(data["date"])
    if period == "all":
        label = "All recorded history"
    elif period != "day":
        label = f"{data.get('from')} - {data.get('to')}"
    else:
        label = f"{selected:%a, %b} {selected.day}, {selected.year}"
    say(icon("🕒") + ("Codex daily work" if period == "day" else "Codex working time"), "bold")
    say(label + " | " + data["timezone"], "dim")
    session_count = len(
        {session["id"] for directory in data["directories"] for session in directory["sessions"]}
    )
    total = "Day total" if period == "day" else "Period total"
    say(
        f"{total}: {_working_duration(data['total_microseconds'])} | "
        f"{len(data['directories'])} directories | {session_count} sessions",
        "bold green",
    )
    flags(data["quality"])
    if "usage" in data:
        say(
            icon("💰") + "Estimated API token cost " + ("-" if plain else "—") + " Standard", "bold"
        )
        usage = data["usage"]
        unavailable = _usage_cells(usage) == ("unavailable",) * 3
        say(
            "Tokens unavailable | USD unavailable | CAD unavailable"
            if unavailable
            else usage_line(usage),
            "bold",
        )
        if unavailable:
            say(
                icon("⚠️")
                + "Token usage unavailable. Run import-history after upgrading; see --details.",
                "yellow",
            )
        elif usage["status"] != "excluded" and not usage["cost_complete"]:
            say(
                icon("⚠️")
                + "* Known priced subtotal; "
                + compact_tokens(usage["unpriced_tokens"])
                + " tokens unpriced; missing evidence may affect costs.",
                "yellow",
            )
        if data.get("excluded_models"):
            say("Excluded from token/cost totals: " + ", ".join(data["excluded_models"]), "dim")
        fx = data.get("fx", {})
        if details:
            provenance(say, data.get("pricing", {}), fx)
            usage_details(say, usage)
        elif fx.get("rate") is None:
            say("CAD unavailable: no valid cached Bank of Canada rate.", "dim")
        else:
            age = fx.get("age_days")
            age_label = f"; {age} {'day' if age == 1 else 'days'} old" if age is not None else ""
            say(
                f"FX: 1 USD = {fx['rate']} CAD | "
                f"Bank of Canada {fx.get('observation_date')}{age_label}",
                "dim",
            )
            if fx.get("last_error"):
                say(icon("⚠️") + "FX refresh failed; using the last valid cached rate.", "yellow")
        if not details:
            say("Present-rate estimate; excludes non-token charges, hosting and taxes.", "dim")
    say()

    if not data["directories"]:
        say(
            "No recorded work for this day."
            if period == "day"
            else "No recorded work for this period.",
            "bold",
        )
        say("Choose another date with --date YYYY-MM-DD, or check codex-time health.")
    else:
        names = [
            PurePath(directory["cwd"]).name or directory["cwd"] or "Unknown directory"
            for directory in data["directories"]
        ]
        duplicates = Counter(names)
        labels = [
            directory["cwd"] if duplicates[name] > 1 and directory["cwd"] else name
            for directory, name in zip(data["directories"], names, strict=True)
        ]
        with_usage = any("usage" in directory for directory in data["directories"])
        headers = ["Project", "Time", "Share"] + (["Tokens", "USD", "CAD"] if with_usage else [])
        summary: list[list[str]] = []
        for directory, name in zip(data["directories"], labels, strict=True):
            row = [
                name,
                _working_duration(directory["total_microseconds"]),
                _share(directory["share_percent"]),
            ]
            if with_usage:
                row.extend(_usage_cells(directory.get("usage")))
            summary.append(row)
        say(icon("📊") + "Directory shares", "bold")
        rows(headers, summary, ["bold"] * len(summary))
        say()
        say(icon("💬") + "Session details", "bold")
        for directory, name in zip(data["directories"], names, strict=True):
            say(icon("📁") + name, "bold cyan")
            say(directory["cwd"] or "Unknown directory", "dim")
            flags(directory["quality"], indent=2)
            sessions = directory["sessions"]
            session_usage = any("usage" in session or session.get("models") for session in sessions)
            session_headers = ["Session / model", "Time"] + (
                ["Tokens", "USD", "CAD"] if session_usage else []
            )
            values: list[list[str]] = []
            styles: list[str] = []
            for session in sessions:
                title = session["title"].strip() or "Untitled session"
                models = session.get("models", [])
                duplicate = (
                    len(models) == 1
                    and "usage" in session
                    and _same_usage(session["usage"], models[0]["usage"])
                )
                if duplicate:
                    title += " (" + (models[0]["model_id"] or "Unknown model") + ")"
                row = [title, _working_duration(session["total_microseconds"])]
                if session_usage:
                    row.extend(_usage_cells(session.get("usage")))
                values.append(row)
                styles.append("bold")
                if not duplicate:
                    for model in models:
                        row = ["  " + (model["model_id"] or "Unknown model"), "-" if plain else "·"]
                        if session_usage:
                            row.extend(_usage_cells(model["usage"]))
                        values.append(row)
                        styles.append("dim")
            if values:
                rows(session_headers, values, styles)
            if details:
                for session in sessions:
                    say(session["title"].strip() or "Untitled session", "bold", indent=2)
                    say("ID: " + session["id"], "dim", indent=2)
                    flags(session["quality"], indent=2)
                    if "usage" in session:
                        usage_details(
                            lambda value, style: say(value, style, indent=2), session["usage"]
                        )
                    for model in session.get("models", []):
                        say(model["model_id"] or "Unknown model", "bold", indent=2)
                        usage_details(
                            lambda value, style: say(value, style, indent=4), model["usage"]
                        )
                    if session.get("children"):
                        say("Child contributions", "bold", indent=2)
                        for child in session["children"]:
                            say(
                                f"{child['session_id']} / {child['model_id'] or 'Unknown model'}",
                                indent=4,
                            )
                            say(usage_line(child["usage"]), indent=4)
            say()
        say("Some work may be estimated; concurrent sessions add.", "dim")

    if details:
        if "pricing" in data:
            provenance(say, data["pricing"], data.get("fx", {}), details=True)
        for message in data["diagnostics"]:
            say("Diagnostic: " + message, "dim")
    else:
        say("Full IDs, token categories and evidence: --details | Exact values: --json", "dim")
    return "\n".join(line.rstrip() for line in output.getvalue().splitlines())
