"""Readable daily terminal hierarchy, narrow layouts, and safe metadata."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import pytest
from rich.cells import cell_len

from codex_time.day_output import day_table

if TYPE_CHECKING:
    from codex_time.reporting import DailyReport


def example() -> DailyReport:
    return {
        "date": "2026-10-06",
        "timezone": "America/Toronto",
        "total_seconds": 3760.25,
        "total_microseconds": 3_760_250_000,
        "quality": ["historical_upper_bound"],
        "diagnostics": ["Native read skipped a damaged record."],
        "directories": [
            {
                "cwd": "/home/kevin/coding/tracker",
                "total_seconds": 3723.0,
                "total_microseconds": 3_723_000_000,
                "share_percent": 99.009,
                "quality": ["historical_upper_bound"],
                "sessions": [
                    {
                        "id": "same-prefix-first-session",
                        "title": "Build daily report",
                        "total_seconds": 3661.0,
                        "total_microseconds": 3_661_000_000,
                        "quality": ["historical_upper_bound"],
                    },
                    {
                        "id": "same-prefix-second-session",
                        "title": "Review report",
                        "total_seconds": 62.0,
                        "total_microseconds": 62_000_000,
                        "quality": [],
                    },
                ],
            },
            {
                "cwd": "/tmp/notes",
                "total_seconds": 37.25,
                "total_microseconds": 37_250_000,
                "share_percent": 0.991,
                "quality": [],
                "sessions": [
                    {
                        "id": "notes-session",
                        "title": "Record notes",
                        "total_seconds": 37.25,
                        "total_microseconds": 37_250_000,
                        "quality": [],
                    },
                ],
            },
        ],
    }


def test_day_directory_session_hierarchy_preserves_visible_values() -> None:
    text = day_table(example())
    assert "Tue, Oct 6, 2026" in text and "America/Toronto" in text
    assert "1h 2m 40s" in text and "1h 2m 3s" in text
    assert "1h 1m 1s" in text and "1m 2s" in text and "37s" in text
    assert "99.0%" in text and "1.0%" in text
    assert text.index("Day total") < text.index("tracker") < text.index("Build daily report")
    detail_text = text.split("Session details", 1)[1]
    assert (
        detail_text.index("Review report")
        < detail_text.index("notes")
        < detail_text.index("Record notes")
    )
    assert "/home/kevin/coding/tracker" in text and "/tmp/notes" in text
    assert "same-prefix-first-session" in text and "same-prefix-second-session" in text
    assert "historical_upper_bound" not in text and "damaged record" not in text
    assert "estimated" in text and "concurrent" in text and "--details" in text
    for line in detail_text.splitlines():
        if "1h 1m 1s" in line:
            assert line.startswith("    ") and "Build daily report" not in line
        if "1h 2m 3s" in line:
            assert "tracker" not in line


@pytest.mark.parametrize("width", [20, 48, 88])
def test_long_unicode_metadata_wraps_without_hiding_paths_ids_or_durations(width: int) -> None:
    data = example()
    path = "/home/研究/" + "long-directory-name/" * 8 + "tracker"
    title = "研究 " + "long-session-title " * 12 + "END-TITLE"
    data["directories"][0]["cwd"] = path
    data["directories"][0]["sessions"][0]["title"] = title
    text = day_table(data, width=width)
    assert all(cell_len(line) <= width for line in text.splitlines())
    compact = "".join(text.split())
    assert path in compact and "END-TITLE" in compact
    assert "same-prefix-first-session" in compact and "same-prefix-second-session" in compact
    assert "1h1m1s" in compact and "1h2m3s" in compact and "1h2m40s" in compact
    assert "99.0%" in compact and "1.0%" in compact and "37s" in compact


def test_details_show_all_quality_and_diagnostics_without_changing_data() -> None:
    data = example()
    data["directories"][0]["quality"].append("directory_flag")
    data["directories"][0]["sessions"][0]["quality"].append("session_flag")
    before = copy.deepcopy(data)
    text = day_table(data, details=True)
    assert "historical_upper_bound" in text
    assert "directory_flag" in text and "session_flag" in text
    assert "Native read skipped a damaged record." in text
    assert data == before
    assert text == day_table(data, details=True)


def test_plain_is_ascii_and_metadata_cannot_inject_controls_or_rich_markup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    data = example()
    data["directories"][0]["cwd"] = "/tmp/[red]研究\x1b[2J\nproject"
    data["directories"][0]["sessions"][0]["title"] = "[bold]Task[/bold]\x1b[2J\rnext\tpart"
    data["directories"][0]["sessions"][0]["id"] = "session\x07-id"
    data["diagnostics"] = ["Diagnostic\x1b[2J"]
    colored = day_table(data, color=True, details=True)
    assert "\x1b[" in colored and "\x1b[2J" not in colored
    assert "[bold]Task[/bold]" in colored and "session?-id" in colored
    plain = day_table(data, plain=True, color=True, details=True)
    assert plain.isascii() and "\x1b" not in plain and "\x07" not in plain
    assert "[bold]Task[/bold]" in plain and "[red]" in plain
    assert "1h 2m 40s" in plain and "99.0%" in plain


def test_no_color_environment_overrides_requested_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "")
    assert "\x1b" not in day_table(example(), color=True)
    assert "\x1b" not in day_table(example(), color=False)


def test_empty_day_has_zero_total_and_actionable_next_step() -> None:
    data = example()
    data.update(total_seconds=0.0, total_microseconds=0, directories=[])
    text = day_table(data)
    assert "Day total" in text and "0s" in text
    assert "No recorded work" in text and "codex-time status" in text
    assert "date" in text and "--date" in text
    assert "99.0%" not in text


def test_nonzero_subsecond_work_is_visible_and_missing_metadata_has_fallbacks() -> None:
    data = example()
    data["directories"] = [data["directories"][0]]
    data["directories"][0]["cwd"] = ""
    data["directories"][0]["sessions"] = [data["directories"][0]["sessions"][0]]
    session = data["directories"][0]["sessions"][0]
    session.update(title="", total_seconds=0.25, total_microseconds=250_000)
    text = day_table(data)
    assert "Unknown directory" in text and "Untitled session" in text
    assert "0.25s" in text and "same-prefix-first-session" in text


@pytest.mark.parametrize("width", [20, 48, 88])
def test_directory_share_bars_precede_all_session_details(width: int) -> None:
    data = example()
    before = copy.deepcopy(data)
    output = day_table(data, width=width, plain=True)
    assert "Directory shares" in output
    summary, details = output.split("Session details", 1)
    compact = "".join(summary.split())
    assert "/home/kevin/coding/tracker" in compact and "/tmp/notes" in compact
    assert "99.0%" in compact and "1.0%" in compact
    assert "#" in summary and "-" in summary
    assert "1h2m3s" in compact and "37s" in compact
    assert "Build daily report" not in summary
    assert "Build daily report" in details and "Review report" in details
    assert all(cell_len(line) <= width for line in output.splitlines())
    assert output.isascii() and "\x1b" not in output
    assert data == before
