"""User-visible terminal behavior: readable summary, width safety and export isolation."""

import copy
import unicodedata

import pytest

from codex_time.burn import BurnReport
from codex_time.burn_output import burn_csv, burn_table
from codex_time.cli import parser


def example() -> BurnReport:
    return {
        "label": "allowance percentage points per summed root working hour (low confidence)",
        "from": "2026-10-06",
        "to": "2026-10-06",
        "timezone": "America/Toronto",
        "period": "day",
        "limit_id": "codex",
        "window_minutes": 10080,
        "max_gap_seconds": 600,
        "latest": {
            "at": "2026-10-06T17:20:41.746000Z",
            "remaining_percent": 60.0,
            "used_percent": 40.0,
        },
        "quality": ["low_confidence"],
        "diagnostics": [],
        "rows": [
            {
                "date": "2026-10-06",
                "limit_id": "codex",
                "plan_type": "pro",
                "bucket": "primary",
                "window_minutes": 10080,
                "resets_at": 1791760139,
                "matched_points": 3.0,
                "working_microseconds": 15300_000_000,
                "working_hours": 4.25,
                "points_per_working_hour": 3 / 4.25,
                "matched_windows": 15,
                "rounding_sensitivity_points_per_hour": 1.41,
                "excluded_gap_points": 0,
                "excluded_no_work_points": 0,
                "excluded_boundary_points": 18,
                "stale_readings": 0,
                "sampling_uncertainty_seconds": 65.96,
                "quality": [
                    "historical_upper_bound",
                    "observation_gap",
                    "unfinished",
                    "low_confidence",
                ],
                "mix": [
                    {
                        "model_id": "gpt-6.1-sol",
                        "reasoning_level": "high",
                        "working_microseconds": 9180_000_000,
                        "percentage": 60.0,
                    },
                    {
                        "model_id": "gpt-6.1-sol",
                        "reasoning_level": "xhigh",
                        "working_microseconds": 6120_000_000,
                        "percentage": 40.0,
                    },
                ],
            }
        ],
    }


def test_summary_puts_allowance_and_rate_before_model_evidence() -> None:
    text = burn_table(example())
    assert "60% remaining" in text and "0.71 pts / working hour" in text
    assert text.index("60% remaining") < text.index("gpt-6.1-sol")
    assert "4h 15m" in text and "3 pts" in text and "18 pts" in text
    assert "1:20 PM EDT" in text and "1791760139" not in text
    assert "historical_upper_bound" not in text and "sampling_uncertainty" not in text
    assert "--details" in text and "low confidence" in text
    assert "🔥" in text and "🔋" in text
    assert "60.0%" in text and "40.0%" in text


def test_details_preserve_audit_evidence_and_do_not_mutate_exports() -> None:
    data = example()
    before = copy.deepcopy(data)
    csv_before = burn_csv(data)
    text = burn_table(data, details=True)
    assert "historical_upper_bound" in text and "1791760139" in text
    assert "1.41" in text and "65.96" in text
    assert data == before and burn_csv(data) == csv_before


@pytest.mark.parametrize("width", [32, 40, 80, 120])
def test_terminal_width_wraps_long_unicode_metadata_without_losing_numbers(width: int) -> None:
    data = example()
    data["rows"][0]["mix"][0]["model_id"] = "模型-" + "long-model-" * 9
    text = burn_table(data, width=width)
    for line in text.splitlines():
        cells = sum(
            0
            if unicodedata.combining(c) or c == "\ufe0f"
            else 2
            if unicodedata.east_asian_width(c) in "WF"
            else 1
            for c in line
        )
        assert cells <= width
    assert "0.71" in text and "60%" in text and "18 pts" in text
    assert "long-model-" in text


def test_color_plain_and_untrusted_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    data = example()
    data["rows"][0]["mix"][0]["model_id"] = "[red]A\x1b[2J\nB"
    colored = burn_table(data, color=True)
    assert "\x1b[" in colored and "\x1b[2J" not in colored
    plain = burn_table(data, plain=True, color=True)
    assert plain.isascii() and "\x1b" not in plain and "[red]A" in plain
    assert "60% remaining" in plain and "0.71" in plain
    assert "\x1b" not in burn_table(example(), color=False)


def test_empty_report_explains_what_to_do_and_omits_fake_zero_rate() -> None:
    data = example()
    data["rows"] = []
    data["latest"] = None
    text = burn_table(data)
    assert "No allowance readings" in text and "codex-time health" in text
    assert "0.00 pts" not in text and "remaining" not in text


def test_distinct_reset_rows_keep_separate_rates() -> None:
    data = example()
    second = copy.deepcopy(data["rows"][0])
    second["resets_at"] += 86400
    second["points_per_working_hour"] = 8
    data["rows"].append(second)
    text = burn_table(data)
    assert "0.71 pts / working hour" in text and "8.00 pts / working hour" in text
    assert "Run 1" in text and "Run 2" in text


def test_burn_cli_exposes_display_controls() -> None:
    args = parser().parse_args(["burn", "day", "--details", "--plain", "--color", "never"])
    assert args.details and args.plain and args.color == "never"


def test_no_color_environment_wins_over_requested_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    assert "\x1b" not in burn_table(example(), color=True)


def test_parallel_allowance_streams_are_not_presented_as_sequential_resets() -> None:
    data = example()
    second = copy.deepcopy(data["rows"][0])
    second["bucket"] = "secondary"
    data["rows"].append(second)
    text = burn_table(data)
    assert "Run 1" not in text and "Run 2" not in text
    assert "pro / primary" in text and "pro / secondary" in text
