"""Combined reports use one snapshot and keep accounting denominators separate."""

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta

import pytest
from rich.cells import cell_len

from codex_time.models import Ledger, ModelContext, QuotaObservation, Session, Span, Turn

BASE = datetime(2026, 10, 6, 16, tzinfo=UTC)


def at(seconds: int) -> datetime:
    return BASE + timedelta(seconds=seconds)


def sample_ledger() -> Ledger:
    first = Turn(
        id="first",
        cwd="/one",
        start=BASE,
        end=at(600),
        waits=[Span(start=at(120), end=at(180))],
        model_contexts=[
            ModelContext(at=BASE, model_id="A", reasoning_level="high"),
            ModelContext(at=at(300), model_id="A", reasoning_level="max"),
        ],
    )
    unknown = Turn(id="unknown", cwd="/one", start=at(600), end=at(720))
    effort = Turn(
        id="effort",
        cwd="/one",
        start=at(720),
        end=at(780),
        model_contexts=[ModelContext(at=at(720), model_id="A")],
    )
    root = Session(
        id="root",
        cwd="/one",
        created=BASE,
        updated=at(780),
        turns={t.id: t for t in [first, unknown, effort]},
    )
    other = Session(
        id="other",
        cwd="/two",
        created=BASE,
        updated=at(600),
        archived=True,
        turns={
            "second": Turn(
                id="second",
                cwd="/two",
                start=BASE,
                end=at(600),
                model_contexts=[ModelContext(at=BASE, model_id="A", reasoning_level="high")],
            )
        },
    )
    observations = [quota(0, 10), quota(300, 12), quota(600, 14)]
    return Ledger(
        sessions={
            "root": root,
            "other": other,
            "child": other.model_copy(deep=True, update={"id": "child", "parent_id": "root"}),
        },
        quota_observations=observations,
        diagnostics=["fixture diagnostic: timing evidence"],
    )


def quota(seconds: int, used: float, reset: int = 1791760139) -> QuotaObservation:
    return QuotaObservation(
        at=at(seconds),
        used_percent=used,
        resets_at=reset,
        window_minutes=10080,
        bucket="primary",
        limit_id="codex",
        plan_type="pro",
    )


def overview(data: Ledger | None = None, **kwargs: object) -> dict:
    from codex_time.overview import overview_report

    return overview_report(data or sample_ledger(), selected_date=date(2026, 10, 6), **kwargs)


def render(data: dict | None = None, **kwargs: object) -> str:
    from codex_time.overview_output import overview_table

    return overview_table(data or overview(), **kwargs)


def test_snapshot_conserves_work_without_reusing_allowance_denominator() -> None:
    ledger = sample_ledger()
    before = ledger.model_dump_json()
    data = overview(ledger)
    assert set(data) == {"allowance", "model_totals", "reasoning"}
    totals, reasoning = data["model_totals"], data["reasoning"]
    assert totals["total_microseconds"] == reasoning["total_microseconds"] == 1320_000_000
    assert sum(row["working_microseconds"] for row in totals["rows"]) == 1320_000_000
    assert sum(row["working_microseconds"] for row in reasoning["rows"]) == 1320_000_000
    assert [(r["model_id"], r["working_seconds"], r["session_count"]) for r in totals["rows"]] == [
        ("A", 1200, 2),
        (None, 120, 1),
    ]
    rows = {r["reasoning_level"]: r for r in reasoning["rows"] if r["model_id"] == "A"}
    assert rows["high"]["working_seconds"] == 840 and rows["high"]["session_count"] == 2
    assert rows["max"]["working_seconds"] == 300 and rows["max"]["session_count"] == 1
    assert rows[None]["working_seconds"] == 60
    assert rows["high"]["percentage"] == pytest.approx(840 / 1320 * 100)
    matched = data["allowance"]["rows"][0]
    assert matched["working_microseconds"] == 1140_000_000
    assert matched["matched_points"] == 4
    assert matched["points_per_working_hour"] == pytest.approx(4 / (1140 / 3600))
    assert ledger.model_dump_json() == before


def test_default_date_resolved_once_in_selected_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    import codex_time.overview as module

    class MidnightClock(datetime):
        calls = 0

        @classmethod
        def now(cls, tz=None):
            cls.calls += 1
            return datetime(2026, 10, 7, 3, 59, 59, tzinfo=UTC) if cls.calls == 1 else at(86400)

    monkeypatch.setattr(module, "datetime", MidnightClock)
    data = module.overview_report(sample_ledger())
    assert MidnightClock.calls == 1
    assert all(part["from"] == "2026-10-06" for part in data.values())
    assert data["model_totals"]["total_seconds"] == 1320


@pytest.mark.parametrize(
    "period,start,end",
    [
        ("day", "2026-10-06", "2026-10-06"),
        ("week", "2026-10-05", "2026-10-11"),
        ("month", "2026-10-01", "2026-10-31"),
    ],
)
def test_all_sections_select_same_calendar_period(period: str, start: str, end: str) -> None:
    data = overview(period=period)
    assert all(p["from"] == start and p["to"] == end for p in data.values())


def test_grouped_models_follow_allowance_and_use_overall_shares() -> None:
    data = overview()
    before = deepcopy(data)
    text = render(data, plain=True)
    assert (
        text.index("Recorded work") < text.index("Allowance") < text.index("Observed consumption")
    )
    assert text.index("Observed consumption") < text.index("Model work")
    assert "22m" in text and "20m" in text and "14m" in text and "5m" in text
    assert "86% remaining" in text and "14% used" in text and "Reset Oct" in text
    assert "12.63 pts / working hour" in text and "4 pts matched" in text
    assert "19m" in text and "low confidence" in text
    assert text.index("A") < text.index("high") < text.index("max")
    assert "90.91%" in text and "63.64%" in text and "22.73%" in text and "9.09%" in text
    assert "2 sessions" in text and "Unknown" in text
    assert "historical_upper_bound" not in text and "fixture diagnostic" not in text
    assert "Matched model mix" not in text and "Sampling uncertainty" not in text
    assert data == before


@pytest.mark.parametrize("width", [20, 32, 48, 69, 88, 120])
def test_long_names_and_tiny_shares_remain_visible_in_narrow_layout(width: int) -> None:
    data = overview()
    long_name = "非常長いmodel-" * 6
    data["model_totals"]["rows"][0]["model_id"] = long_name
    for row in data["reasoning"]["rows"]:
        if row["model_id"] == "A":
            row["model_id"] = long_name
    data["model_totals"]["rows"][0]["percentage"] = 0.001
    text = render(data, width=width)
    assert all(cell_len(line) <= width for line in text.splitlines())
    compact = "".join(text.split())
    assert long_name in compact and "<0.01%" in compact
    assert "20m" in compact and "63.64%" in compact and "2sessions" in compact


def test_details_expose_evidence_without_changing_data() -> None:
    data = overview()
    before = deepcopy(data)
    text = render(data, details=True)
    assert "Matched model mix" in text and "historical_upper_bound" in text
    assert "Sampling uncertainty" in text and "fixture diagnostic" in text
    assert "Rounding sensitivity" in text and "10080" in text
    assert data == before


def test_missing_allowance_keeps_model_work_and_empty_work_is_actionable() -> None:
    ledger = sample_ledger()
    ledger.quota_observations = []
    text = render(overview(ledger))
    assert "No allowance readings" in text and "22m" in text and "high" in text
    assert "0.00 pts" not in text and "remaining" not in text
    text = render(overview(Ledger()))
    assert "No recorded work" in text and "codex-time health" in text


def test_multiple_reset_cohorts_and_exclusions_stay_separate() -> None:
    ledger = sample_ledger()
    ledger.quota_observations = [
        quota(0, 10),
        quota(300, 12),
        quota(400, 1, 1791846539),
        quota(600, 3, 1791846539),
        quota(1300, 6, 1791846539),
    ]
    data = overview(ledger)
    assert [r["matched_points"] for r in data["allowance"]["rows"]] == [2, 2]
    text = render(data, plain=True)
    assert "13.33 pts / working hour" in text and "18.00 pts / working hour" in text
    assert text.count("Reset Oct") >= 2 and "3 pts excluded across observation gaps" in text


def test_ascii_no_color_and_metadata_escaping(monkeypatch: pytest.MonkeyPatch) -> None:
    data = overview()
    data["model_totals"]["rows"][0]["model_id"] = "[red]A\x1b[2J\nnext"
    monkeypatch.setenv("NO_COLOR", "")
    assert "\x1b" not in render(data, color=True)
    text = render(data, color=True, plain=True)
    assert text.isascii() and "\x1b" not in text and "[red]A" in text
    monkeypatch.delenv("NO_COLOR")
    assert "\x1b[" in render(color=True)


@pytest.mark.parametrize("width", [20, 32, 48, 88])
def test_plain_cohort_labels_wrap_without_unicode_or_lost_resets(width: int) -> None:
    data = overview()
    text = render(data, width=width, plain=True)
    assert text.isascii()
    compact = "".join(text.split())
    assert "Tue,Oct6|ResetOct11,7:08PMEDT" in compact


def test_positive_subsecond_work_is_visible() -> None:
    ledger = sample_ledger()
    ledger.sessions = {"root": ledger.sessions["root"]}
    turn = ledger.sessions["root"].turns["first"]
    turn.end = BASE + timedelta(microseconds=250_000)
    turn.waits = []
    turn.model_contexts = turn.model_contexts[:1]
    ledger.sessions["root"].turns = {"first": turn}
    assert overview(ledger)["model_totals"]["total_microseconds"] == 250_000
    assert "0.25s" in render(overview(ledger))
