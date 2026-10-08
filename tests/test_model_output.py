"""Readable model rankings retain accounting and technical evidence."""

from copy import deepcopy

import pytest
from rich.cells import cell_len

from codex_time.model_output import model_csv, model_table
from codex_time.model_usage import ModelUsageReport, ModelUsageRow


def fixture(*, model_only: bool = True) -> ModelUsageReport:
    rows: list[ModelUsageRow] = []
    for rank, model, effort, seconds, percentage in [
        (1, "gpt-6.1-sol", "high", 180, 50),
        (2, "gpt-6-astra", "max", 120, 100 / 3),
        (None, None, None, 60, 100 / 6),
    ]:
        rows.append(
            {
                "rank": rank,
                "model_id": model,
                "reasoning_level": effort,
                "working_seconds": seconds,
                "working_microseconds": seconds * 1_000_000,
                "percentage": percentage,
                "session_count": 2,
                "quality": ["observation_gap"],
                "sampling_uncertainty_seconds": 2.5,
            }
        )
    return {
        "label": "Working-time usage",
        "period": "day",
        "from": "2026-10-08",
        "to": "2026-10-08",
        "timezone": "America/Toronto",
        "model_only": model_only,
        "total_seconds": 360,
        "total_microseconds": 360_000_000,
        "rows": rows,
        "quality": ["observation_gap"],
        "sampling_uncertainty_seconds": 5,
        "diagnostics": ["invalid rollout checkpoint; rereading safely"],
    }


def test_default_ranking_is_readable_and_compact() -> None:
    rendered = model_table(fixture())
    assert "🤖" in rendered and "🏆" in rendered
    assert "Oct 8, 2026" in rendered and "America/Toronto" in rendered
    assert "6m" in rendered and "3m" in rendered and "2m" in rendered
    assert all(value in rendered for value in ("50.00%", "33.33%", "16.67%", "Unknown"))
    assert "Reasoning" not in rendered and "All" not in rendered
    assert "observation_gap" not in rendered and "invalid rollout" not in rendered
    assert "estimate" in rendered and "--details" in rendered
    assert rendered.index("gpt-6.1-sol") < rendered.index("gpt-6-astra")


def test_reasoning_details_plain_and_exports_are_preserved() -> None:
    data = fixture(model_only=False)
    saved, csv_before = deepcopy(data), model_csv(data)
    rendered = model_table(data, details=True)
    assert "Reasoning" in rendered and "high" in rendered and "max" in rendered
    assert "observation_gap" in rendered and "invalid rollout checkpoint" in rendered
    assert "not additive" in rendered
    plain = model_table(data, plain=True, color=True)
    assert plain.isascii() and "\x1b" not in plain
    assert "Model" in plain and "high" in plain
    assert data == saved and model_csv(data) == csv_before


@pytest.mark.parametrize("width", [20, 32, 48, 69, 70, 88, 120])
def test_narrow_unicode_rows_preserve_values_without_overflow(width: int) -> None:
    data = fixture(model_only=False)
    data["rows"][0]["model_id"] = "非常長いmodel-" * 5
    rendered = model_table(data, width=width)
    assert all(cell_len(line) <= width for line in rendered.splitlines())
    folded = "".join(rendered.split())
    assert data["rows"][0]["model_id"] in folded
    assert "50.00%" in folded and "3m" in folded


def test_unknown_empty_and_subsecond_reports() -> None:
    data = fixture()
    data["rows"] = [data["rows"][-1]]
    assert "🏆" not in model_table(data)
    assert "Unknown" in model_table(data)
    data["rows"] = []
    data["total_seconds"] = 0
    data["total_microseconds"] = 0
    empty = model_table(data)
    assert "No counted work" in empty and "--date" in empty and "🏆" not in empty
    data = fixture()
    data["rows"][0].update(working_seconds=0.25, working_microseconds=250_000)
    data["rows"][1].update(working_seconds=39, working_microseconds=39_000_000)
    assert "0.25s" in model_table(data) and "39s" in model_table(data)


def test_terminal_metadata_and_no_color(monkeypatch: pytest.MonkeyPatch) -> None:
    data = fixture(model_only=False)
    data["rows"][0]["model_id"] = "[red]name\x1b[2J\nnext"
    data["diagnostics"] = ["warning\x1b[2J"]
    monkeypatch.setenv("NO_COLOR", "")
    rendered = model_table(data, color=True, details=True)
    assert "\x1b" not in rendered and "[red]name" in rendered
    assert "next" in rendered


@pytest.mark.parametrize("width,long_name", [(48, False), (88, False), (88, True)])
def test_tiny_positive_share_stays_visible(width: int, long_name: bool) -> None:
    data = fixture()
    data["rows"][0]["percentage"] = 0.001
    if long_name:
        data["rows"][0]["model_id"] = "long-model-name-" * 5
    rendered = model_table(data, width=width)
    assert "<0.01%" in rendered and "0.00%" not in rendered
