"""Render the same working-time usage rows as terminal tables or CSV."""

import csv
import json
from io import StringIO

from codex_time.model_usage import ModelUsageReport
from codex_time.presentation import duration, safe_text


def model_table(data: ModelUsageReport) -> str:
    headings = ["Rank", "Model", "Reasoning", "Working", "%", "Sessions", "Quality / uncertainty"]
    rows = [
        [
            str(row["rank"]) if row["rank"] is not None else "—",
            safe_text(row["model_id"] or "Unknown"),
            "All" if data["model_only"] else safe_text(row["reasoning_level"] or "Unknown"),
            duration(row["working_seconds"]),
            f"{row['percentage']:.2f}%",
            str(row["session_count"]),
            f"{', '.join(row['quality']) or 'observed'}; {row['sampling_uncertainty_seconds']:g}s",
        ]
        for row in data["rows"]
    ]
    widths = [max(len(row[i]) for row in [headings, *rows]) for i in range(len(headings))]
    lines = [
        f"Working-time usage ({data['timezone']}): {data['from']} to {data['to']}",
        f"Total: {duration(data['total_seconds'])} ({data['total_seconds']:g} seconds)",
        "",
    ]
    for row in [headings, *rows]:
        lines.append(
            "  ".join(value.ljust(width) for value, width in zip(row, widths, strict=True))
        )
    if not rows:
        lines.append("No counted work in this period.")
    lines.append(
        f"Sampling uncertainty: {data['sampling_uncertainty_seconds']:g}s "
        "(not additive across rows)"
    )
    lines.extend(f"Diagnostic: {message}" for message in data["diagnostics"])
    return "\n".join(lines)


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
