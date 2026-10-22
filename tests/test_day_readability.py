"""Compact daily rows retain session values and disclose incomplete cost evidence."""

from __future__ import annotations

import copy
import re

import pytest
from rich.cells import cell_len

from codex_time.day_output import day_table
from codex_time.reporting import DailyReport, DirectoryTime, SessionTime
from codex_time.token_reporting import UsageSummary


def recorded_usage(tokens: int, usd: str, cad: str) -> UsageSummary:
    return {
        "status": "recorded",
        "tokens": {
            "input_tokens": tokens,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_output_tokens": 0,
            "total_tokens": tokens,
        },
        "observations": 1,
        "uncertain_observations": 0,
        "unavailable_session_count": 0,
        "unavailable_sessions": [],
        "priced_tokens": tokens,
        "unpriced_tokens": 0,
        "cost_complete": True,
        "usd": usd,
        "cad": cad,
        "diagnostics": [],
    }


# Independent, hand-checked times and amounts make dropped/misassociated rows observable.
SESSION_VALUES = [
    ("Plan ingestion", "11s", 11, 1000, "1k", "0.11", "0.15"),
    ("Repair parser", "22s", 22, 2000, "2k", "0.22", "0.30"),
    ("Review storage", "33s", 33, 3000, "3k", "0.33", "0.45"),
    ("Ship import", "44s", 44, 4000, "4k", "0.44", "0.60"),
    ("Design lesson", "55s", 55, 5000, "5k", "0.55", "0.75"),
    ("Write exercise", "1m 6s", 66, 6000, "6k", "0.66", "0.90"),
    ("Check sources", "1m 17s", 77, 7000, "7k", "0.77", "1.05"),
    ("Publish lesson", "1m 28s", 88, 8000, "8k", "0.88", "1.20"),
    ("Plan dashboard", "1m 39s", 99, 9000, "9k", "0.99", "1.35"),
    ("Build dashboard", "1m 50s", 110, 10000, "10k", "1.10", "1.50"),
    ("Review dashboard", "2m 1s", 121, 11000, "11k", "1.21", "1.65"),
    ("Ship dashboard", "2m 12s", 132, 12000, "12k", "1.32", "1.80"),
]
PROJECT_VALUES = [
    ("atlas", "1m 50s", 110, 12.8, 10000, "10k", "1.10", "1.50"),
    ("boreal", "4m 46s", 286, 33.3, 26000, "26k", "2.86", "3.90"),
    ("cobalt", "7m 42s", 462, 53.8, 42000, "42k", "4.62", "6.30"),
]


def busy_day() -> DailyReport:
    directories: list[DirectoryTime] = []
    for project_index, (name, _, seconds, share, tokens, _, usd, cad) in enumerate(PROJECT_VALUES):
        sessions: list[SessionTime] = []
        for index in range(project_index * 4, project_index * 4 + 4):
            title, _, duration, amount, _, cost_usd, cost_cad = SESSION_VALUES[index]
            usage = recorded_usage(amount, cost_usd, cost_cad)
            sessions.append(
                {
                    "id": f"full-session-identifier-{index:02d}-2026-10-13",
                    "title": title,
                    "total_seconds": duration,
                    "total_microseconds": duration * 1_000_000,
                    "quality": ["session_evidence_flag"] if index == 0 else [],
                    "usage": usage,
                    "models": [{"model_id": "gpt-4.1" if index % 2 else "gpt-6", "usage": usage}],
                    "children": [],
                }
            )
        directories.append(
            {
                "cwd": f"/home/example/coding/{name}",
                "total_seconds": seconds,
                "total_microseconds": seconds * 1_000_000,
                "share_percent": share,
                "quality": ["directory_evidence_flag"] if project_index == 0 else [],
                "usage": recorded_usage(tokens, usd, cad),
                "sessions": sessions,
            }
        )
    return {
        "date": "2026-10-13",
        "timezone": "America/Toronto",
        "total_seconds": 858,
        "total_microseconds": 858_000_000,
        "quality": ["historical_upper_bound"],
        "diagnostics": ["Recorded source evidence needs review."],
        "directories": directories,
        "usage": recorded_usage(78000, "8.58", "11.70"),
        "pricing": {
            "version": "test-standard-v1",
            "verified_at": "2026-10-13",
            "source_url": "https://example.com/official-model-prices",
        },
        "fx": {
            "rate": "1.35",
            "observation_date": "2026-10-13",
            "age_days": 1,
            "source_url": "https://example.com/official-usd-cad",
        },
    }


def two_sessions() -> DailyReport:
    data = busy_day()
    directory = data["directories"][0]
    directory.update(
        total_seconds=33,
        total_microseconds=33_000_000,
        share_percent=100,
        usage=recorded_usage(3000, "0.33", "0.45"),
        sessions=directory["sessions"][:2],
    )
    data.update(
        directories=[directory],
        total_seconds=33,
        total_microseconds=33_000_000,
        usage=recorded_usage(3000, "0.33", "0.45"),
    )
    return data


def compact(text: str) -> str:
    return "".join(text.split())


def test_busy_day_is_short_without_hiding_any_session_values() -> None:
    data = busy_day()
    before = copy.deepcopy(data)
    text = day_table(data, width=120, plain=True)
    assert len(text.splitlines()) <= 65, text
    assert all(cell_len(line) <= 120 for line in text.splitlines())
    assert "14m18s" in compact(text) and "78k" in text
    assert "8.58" in text and "11.70" in text
    for title, duration, _, _, tokens, usd, cad in SESSION_VALUES:
        rows = [line for line in text.splitlines() if title in line]
        assert len(rows) == 1, f"Expected one session row for {title!r}:\n{text}"
        row = rows[0]
        assert duration in row and tokens in row and usd in row and cad in row, row
    assert "gpt-4.1" in text and "gpt-6" in text
    assert data == before


def test_project_summary_has_aligned_time_share_tokens_and_currency_columns() -> None:
    text = day_table(busy_day(), width=120, plain=True)
    headers = [
        line
        for line in text.splitlines()
        if all(label in line for label in ["Time", "Share", "Tokens", "USD", "CAD"])
    ]
    assert headers, f"Expected labeled project metric columns:\n{text}"
    rows = []
    for name, duration, _, share, _, tokens, usd, cad in PROJECT_VALUES:
        row = next(
            (line for line in text.splitlines() if name in line and f"{share:.1f}%" in line),
            "",
        )
        assert all(value in row for value in [duration, tokens, usd, cad]), row
        rows.append(row)
    # Numeric values of different lengths must end at the same columns.
    for values in [
        ["1m 50s", "4m 46s", "7m 42s"],
        ["12.8%", "33.3%", "53.8%"],
        ["10k", "26k", "42k"],
        ["1.10", "2.86", "4.62"],
        ["1.50", "3.90", "6.30"],
    ]:
        assert (
            len({row.rindex(value) + len(value) for row, value in zip(rows, values, strict=True)})
            == 1
        )


@pytest.mark.parametrize("width", [120, 160])
def test_available_terminal_width_keeps_long_project_path_on_one_line(width: int) -> None:
    data = two_sessions()
    path = "/home/example/" + "project-" * ((width - 28) // 8) + "END-PATH"
    data["directories"][0]["cwd"] = path
    text = day_table(data, width=width, plain=True)
    assert any(path in line for line in text.splitlines()), text
    assert max(cell_len(line) for line in text.splitlines()) > 96
    assert all(cell_len(line) <= width for line in text.splitlines())


def test_single_model_name_is_visible_without_repeating_its_session_cost() -> None:
    text = day_table(two_sessions(), width=120, plain=True)
    assert "gpt-6" in text and "Plan ingestion" in text
    assert len(re.findall(r"(?<!\d)0\.11(?!\d)", text)) == 1, text
    assert len(re.findall(r"(?<!\d)0\.15(?!\d)", text)) == 1, text


def test_multiple_models_keep_their_individual_token_and_cost_breakdown() -> None:
    data = two_sessions()
    session = data["directories"][0]["sessions"][0]
    session["models"] = [
        {"model_id": "gpt-4.1", "usage": recorded_usage(400, "0.03", "0.04")},
        {"model_id": "gpt-6", "usage": recorded_usage(600, "0.08", "0.11")},
    ]
    text = day_table(data, width=120, plain=True)
    for model, tokens, usd, cad in [
        ("gpt-4.1", "400", "0.03", "0.04"),
        ("gpt-6", "600", "0.08", "0.11"),
    ]:
        row = next((line for line in text.splitlines() if model in line and tokens in line), "")
        assert row and usd in row and cad in row, text
    assert "1k" in text and "0.15" in text


def test_single_model_with_distinct_usage_keeps_its_cost_breakdown() -> None:
    data = two_sessions()
    session = data["directories"][0]["sessions"][0]
    session["models"] = [{"model_id": "gpt-6", "usage": recorded_usage(600, "0.08", "0.11")}]
    text = day_table(data, width=120, plain=True)
    row = next((line for line in text.splitlines() if "gpt-6" in line and "600" in line), "")
    assert row and "0.08" in row and "0.11" in row, text
    session_row = next(line for line in text.splitlines() if "Plan ingestion" in line)
    assert "1k" in session_row and "0.15" in session_row, text


def test_details_keep_identity_and_breakdown_with_full_evidence_in_json() -> None:
    data = two_sessions()
    session = data["directories"][0]["sessions"][0]
    session["children"] = [
        {
            "session_id": "full-child-session-identifier",
            "model_id": "gpt-4.1",
            "usage": recorded_usage(100, "0.01", "0.02"),
        }
    ]
    before = copy.deepcopy(data)
    default = day_table(data, width=120, plain=True)
    detailed = day_table(data, width=120, plain=True, details=True)
    for row in data["directories"][0]["sessions"]:
        assert row["id"] not in default
        assert row["id"] in detailed
        assert row["title"] in default and row["title"] in detailed
    assert "/home/example/coding/atlas" in default
    for evidence in [
        "Input: 1k",
        "Cached: 0",
        "Output: 0",
        "Some work is estimated",
        "1 recording notice",
        "Child contributions",
        "test-standard-v1",
        "--json",
    ]:
        assert evidence in detailed, evidence
    for machine_evidence in [
        "Exact USD:",
        "session_evidence_flag",
        "directory_evidence_flag",
        "historical_upper_bound",
        "Recorded source evidence needs review.",
        "full-child-session-identifier",
        "https://example.com/official-model-prices",
        "https://example.com/official-usd-cad",
    ]:
        assert machine_evidence not in detailed, machine_evidence
    assert "session_evidence_flag" not in default and "Child contributions" not in default
    assert data == before


def test_narrow_plain_layout_folds_all_metadata_and_keeps_labeled_values() -> None:
    data = two_sessions()
    directory = data["directories"][0]
    directory["cwd"] = "/home/example/" + "very-long-directory/" * 6 + "PATH-END"
    directory["sessions"][0]["title"] = "Detailed session title " * 6 + "TITLE-END"
    directory["sessions"][0]["models"][0]["model_id"] = "exact-model-identifier-" * 4 + "MODEL-END"
    output = day_table(data, width=48, plain=True)
    details = day_table(data, width=48, plain=True, details=True)
    for rendered in [output, details]:
        assert rendered.isascii() and "\x1b" not in rendered
        assert all(cell_len(line) <= 48 for line in rendered.splitlines())
        flattened = compact(rendered)
        assert compact(directory["cwd"]) in flattened
        assert compact(directory["sessions"][0]["title"]) in flattened
        assert compact(directory["sessions"][0]["models"][0]["model_id"]) in flattened
        assert (
            "11s" in flattened and "1k" in flattened and "0.11" in flattened and "0.15" in flattened
        )
        assert "USD" in rendered and "CAD" in rendered
    assert directory["sessions"][0]["id"] in compact(details)


@pytest.mark.parametrize("status", ["unavailable", "excluded", "unpriced", "subtotal"])
@pytest.mark.parametrize("width", [48, 120])
def test_incomplete_cost_statuses_never_render_as_zero(status: str, width: int) -> None:
    data = two_sessions()
    usage = recorded_usage(7000, "0", "0")
    if status in {"unavailable", "excluded"}:
        usage.update(
            status=status,
            tokens=dict.fromkeys(usage["tokens"]),
            priced_tokens=0,
            cost_complete=False,
        )
        if status == "unavailable":
            usage["cad"] = None
        else:
            data["excluded_models"] = ["codex-auto-review"]
    else:
        usage.update(cost_complete=False, priced_tokens=0, unpriced_tokens=7000)
        if status == "subtotal":
            usage.update(priced_tokens=2000, unpriced_tokens=5000, usd="0.17", cad="0.23")
    directory = data["directories"][0]
    directory["sessions"] = directory["sessions"][:1]
    session = directory["sessions"][0]
    session["usage"] = directory["usage"] = data["usage"] = usage
    session["models"] = []
    rendered = day_table(data, width=width, plain=True)
    assert status in rendered.lower(), rendered
    assert "0.00" not in rendered, rendered
    assert "Planingestion" in compact(rendered)
    if status == "subtotal":
        assert "0.17" in compact(rendered) and "0.23" in compact(rendered)
    elif status == "unpriced":
        assert "7k" in rendered


def test_model_usage_survives_missing_optional_session_usage() -> None:
    data = two_sessions()
    for session in data["directories"][0]["sessions"]:
        del session["usage"]
    text = day_table(data, width=120, plain=True)
    models = text.split("Session details", 1)[1]
    for model, tokens, usd, cad in [
        ("gpt-6", "1k", "0.11", "0.15"),
        ("gpt-4.1", "2k", "0.22", "0.30"),
    ]:
        row = next(line for line in models.splitlines() if model in line)
        assert tokens in row and usd in row and cad in row
