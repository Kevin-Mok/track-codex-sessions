"""Working-time model rankings conserve root-session work through switches and waits."""

import csv
import io
import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from codex_time.accounting import segments, total_seconds
from codex_time.models import Ledger, ModelContext, Session, Span, Turn
from codex_time.reporting import report
from codex_time.storage import Store

BASE = datetime(2026, 10, 6, 16, tzinfo=UTC)


def t(seconds: int) -> datetime:
    return BASE + timedelta(seconds=seconds)


def context(second: int, model: str | None, effort: str | None) -> ModelContext:
    return ModelContext(at=t(second), model_id=model, reasoning_level=effort)


def turn(tid: str, start: int, end: int, contexts: list[ModelContext], **kw: object) -> Turn:
    return Turn.model_validate(
        dict(id=tid, cwd="/work", start=t(start), end=t(end), model_contexts=contexts, **kw)
    )


def ledger(*turns: Turn) -> Ledger:
    return Ledger(
        sessions={
            "root": Session(
                id="root",
                cwd="/work",
                created=BASE,
                updated=BASE,
                turns={tr.id: tr for tr in turns},
            )
        }
    )


def usage(data: Ledger, **kwargs: object) -> dict:
    from codex_time.model_usage import model_report

    return model_report(data, period="day", selected_date=date(2026, 10, 6), **kwargs)


def values(result: dict) -> dict:
    return {(r["model_id"], r["reasoning_level"]): r["working_seconds"] for r in result["rows"]}


def test_mixed_models_ranking_unknown_denominator_and_model_only() -> None:
    data = ledger(
        turn("a", 0, 120, [context(2, "A", "high")]),
        turn("b", 120, 300, [context(121, "B", "max")]),
        turn("unknown", 300, 360, []),
        turn("effort", 360, 400, [context(361, "A", "max")]),
    )
    result = usage(data)
    assert values(result) == {
        ("A", "high"): 120,
        ("B", "max"): 180,
        ("A", "max"): 40,
        (None, None): 60,
    }
    assert [r["rank"] for r in result["rows"]] == [1, 2, 3, None]
    assert result["rows"][0]["model_id"] == "B"
    assert result["rows"][0]["percentage"] == 45
    assert result["total_seconds"] == 400
    assert values(usage(data, model_only=True)) == {
        ("A", None): 160,
        ("B", None): 180,
        (None, None): 60,
    }


def test_within_turn_switch_overlap_wait_and_directory_conserve_time() -> None:
    first = turn(
        "a",
        0,
        60,
        [context(2, "A", "high"), context(25, "B", "max")],
        waits=[Span(start=t(20), end=t(40))],
    )
    second = turn(
        "b", 30, 90, [context(31, "C", "low"), context(50, "C", "high"), context(55, "C", "high")]
    )
    second.cwd = "/other"
    data = ledger(first, second)
    result = usage(data)
    assert values(result) == {("A", "high"): 20, ("C", "low"): 10, ("C", "high"): 40}
    assert sum(values(result).values()) == total_seconds(segments([first, second])) == 70
    assert values(usage(data, cwd="/work")) == {("A", "high"): 20}
    expected = report(
        data,
        cwd="/work",
        all_directories=False,
        archive="all",
        start=date(2026, 10, 6),
        end=date(2026, 10, 6),
    )
    assert usage(data, cwd="/work")["total_seconds"] == expected["total_seconds"]


def test_concurrent_roots_children_session_counts_and_archive_filters() -> None:
    data = ledger(turn("a", 0, 300, [context(1, "A", "high")]))
    root = data.sessions["root"]
    data.sessions["other"] = root.model_copy(deep=True, update={"id": "other", "archived": True})
    data.sessions["child"] = root.model_copy(deep=True, update={"id": "child", "parent_id": "root"})
    result = usage(data)
    assert result["total_seconds"] == 600
    assert result["rows"][0]["session_count"] == 2
    assert usage(data, archive="active")["total_seconds"] == 300
    assert usage(data, archive="archived")["total_seconds"] == 300


def test_unknown_reasoning_conflicting_context_and_sampled_uncertainty() -> None:
    tr = turn(
        "a",
        0,
        60,
        [
            context(2, "A", None),
            context(20, "B", "high"),
            context(20, "C", "high"),
            context(40, "D", "max"),
        ],
        sampling_uncertainty_seconds=2.5,
        quality=["sampled_waits_1s", "observation_gap", "model_context_conflict"],
    )
    result = usage(ledger(tr))
    assert values(result) == {("A", None): 20, (None, None): 20, ("D", "max"): 20}
    assert [r["model_id"] for r in result["rows"]] == ["A", "D", None]
    assert all(r["sampling_uncertainty_seconds"] == 2.5 for r in result["rows"])
    assert all("observation_gap" in r["quality"] for r in result["rows"])
    assert "unknown_reasoning" in result["rows"][0]["quality"]
    assert "unknown_model" in result["rows"][-1]["quality"]


def test_unfinished_counts_only_closed_coverage_and_no_model_leaks_between_turns() -> None:
    first = turn("a", 0, 20, [context(2, "A", "high")])
    ongoing = Turn(
        id="b",
        cwd="/work",
        start=t(30),
        coverage=[Span(start=t(40), end=t(50)), Span(start=t(70), end=t(90))],
    )
    result = usage(ledger(first, ongoing))
    assert values(result) == {("A", "high"): 20, (None, None): 30}
    assert "unfinished" in result["rows"][-1]["quality"]


@pytest.mark.parametrize(
    "period,selected,start,end,hours",
    [
        ("day", "2026-03-08", "2026-03-08", "2026-03-08", 23),
        ("day", "2026-11-01", "2026-11-01", "2026-11-01", 25),
        ("week", "2026-01-01", "2025-12-29", "2026-01-04", 168),
        ("month", "2026-12-20", "2026-12-01", "2026-12-31", 744),
        ("month", "2028-02-20", "2028-02-01", "2028-02-29", 696),
        ("month", "2026-03-15", "2026-03-01", "2026-03-31", 743),
    ],
)
def test_calendar_boundaries_dst_and_existing_report_conservation(
    period: str, selected: str, start: str, end: str, hours: int
) -> None:
    from codex_time.model_usage import model_report

    zone = ZoneInfo("America/Toronto")
    begin = datetime.combine(date.fromisoformat(start), datetime.min.time(), zone).astimezone(UTC)
    finish = datetime.combine(
        date.fromisoformat(end) + timedelta(days=1), datetime.min.time(), zone
    ).astimezone(UTC)
    tr = Turn(
        id="calendar",
        cwd="/work",
        start=begin - timedelta(seconds=5),
        end=finish + timedelta(seconds=5),
        model_contexts=[
            ModelContext(at=begin, model_id="A", reasoning_level="high"),
            ModelContext(at=begin + timedelta(seconds=3600), model_id="B", reasoning_level="max"),
        ],
    )
    data = ledger(tr)
    result = model_report(data, period=period, selected_date=date.fromisoformat(selected))
    assert result["from"] == start and result["to"] == end
    assert result["total_seconds"] == hours * 3600
    assert sum(r["working_seconds"] for r in result["rows"]) == result["total_seconds"]
    assert (
        result["total_seconds"]
        == report(
            data,
            cwd="/work",
            all_directories=True,
            archive="all",
            start=date.fromisoformat(start),
            end=date.fromisoformat(end),
        )["total_seconds"]
    )


def test_default_current_period_respects_timezone() -> None:
    from codex_time.model_usage import model_report

    now = datetime(2027, 1, 1, 2, tzinfo=UTC)
    assert model_report(Ledger(), period="day", now=now)["from"] == "2026-12-31"
    assert (
        model_report(Ledger(), period="month", now=now, timezone_name="UTC")["from"] == "2027-01-01"
    )


def test_cli_table_json_csv_share_rows_and_options(tmp_path: Path) -> None:
    data = ledger(
        turn("a", 0, 120, [context(1, "A", "high")]),
        turn("b", 120, 300, [context(121, "B", "max")]),
        turn("unknown", 300, 360, []),
    )
    store = Store(tmp_path / "data", tmp_path / "state")
    with store.writer():
        store.save(data)
    base = [
        sys.executable,
        "-c",
        "from codex_time.cli import main; raise SystemExit(main())",
        "--data-dir",
        str(store.root),
        "--state-dir",
        str(store.runtime),
    ]

    def invoke(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*base, *args], capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"}
        )

    for period in ("day", "week", "month"):
        args = ("models", period, "--date", "2026-10-06")
        exported = invoke(*args, "--json")
        assert exported.returncode == 0, exported.stderr
        result = json.loads(exported.stdout)
        csv_result = invoke(*args, "--csv")
        assert csv_result.returncode == 0, csv_result.stderr
        rows = list(csv.DictReader(io.StringIO(csv_result.stdout)))
        assert len(rows) == len(result["rows"])
        for actual, expected in zip(rows, result["rows"], strict=True):
            assert actual["model_id"] == (expected["model_id"] or "Unknown")
            assert float(actual["working_seconds"]) == expected["working_seconds"]
            assert int(actual["working_microseconds"]) == expected["working_microseconds"]
            assert int(actual["total_microseconds"]) == result["total_microseconds"]
            assert float(actual["percentage"]) == expected["percentage"]
            assert int(actual["session_count"]) == expected["session_count"]
            assert json.loads(actual["quality"]) == expected["quality"]
        table = invoke(*args)
        assert table.returncode == 0
        assert "working-time usage" in table.stdout.lower()
        assert "3m" in table.stdout and "2m" in table.stdout and "Unknown" in table.stdout
        assert "🤖" in table.stdout
        assert "--details" in invoke(*args, "--help").stdout
        detailed = invoke(*args, "--details", "--plain", "--color", "always")
        assert detailed.returncode == 0, detailed.stderr
        assert detailed.stdout.isascii() and "\x1b" not in detailed.stdout
        assert json.loads(invoke(*args, "--details", "--json").stdout) == result
        assert "50.00%" in table.stdout
    assert invoke("models", "day", "--json", "--csv").returncode == 2
    assert invoke("models", "week", "--date", "bad").returncode == 2
    combined = invoke(
        "models",
        "day",
        "--date",
        "2026-10-06",
        "--model-only",
        "--cwd",
        "/work",
        "--archive",
        "all",
        "--json",
    )
    assert combined.returncode == 0
    assert json.loads(combined.stdout)["total_seconds"] == 360


def test_picker_shows_latest_observed_and_details_attributed_model() -> None:
    from codex_time.presentation import _details, build_rows

    data = ledger(turn("a", 0, 60, [context(2, "A", "high"), context(30, "B", "max")]))
    rows = build_rows(data, {}, cwd="/work", now=t(100))
    assert rows[0].model_id == "B" and rows[0].reasoning_level == "max"
    details = "\n".join(_details(rows[0], "America/Toronto"))
    assert "A / high" in details and "B / max" in details
    assert "0:00:30" in details


def test_subsecond_total_and_exact_units_conserve_with_split_contexts() -> None:
    from codex_time.presentation import build_rows

    tr = Turn(
        id="fraction",
        cwd="/work",
        start=BASE,
        end=BASE + timedelta(microseconds=300000),
        model_contexts=[
            ModelContext(at=BASE, model_id="A", reasoning_level="high"),
            ModelContext(
                at=BASE + timedelta(microseconds=100000), model_id="B", reasoning_level="high"
            ),
        ],
    )
    data = ledger(tr)
    result = usage(data)
    original = report(data, cwd="/work", all_directories=True, archive="all")
    assert result["total_seconds"] == original["total_seconds"] == 0.3
    assert (
        sum(row["working_microseconds"] for row in result["rows"])
        == result["total_microseconds"]
        == 300000
    )
    assert build_rows(data, {}, cwd="/work", now=BASE)[0].total == 0.3


def test_many_fractional_intervals_conserve_exact_report_units() -> None:
    turns = [
        Turn(
            id=str(i),
            cwd="/work",
            start=BASE + timedelta(seconds=i),
            end=BASE + timedelta(seconds=i, microseconds=100000),
            model_contexts=[
                ModelContext(
                    at=BASE + timedelta(seconds=i), model_id=f"A{i % 3}", reasoning_level="high"
                )
            ],
        )
        for i in range(30)
    ]
    result = usage(ledger(*turns))
    original = report(ledger(*turns), cwd="/work", all_directories=True, archive="all")
    assert result["total_seconds"] == original["total_seconds"] == 3
    assert (
        sum(row["working_microseconds"] for row in result["rows"])
        == result["total_microseconds"]
        == 3000000
    )
