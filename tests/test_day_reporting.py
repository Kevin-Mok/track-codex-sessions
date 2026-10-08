from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from codex_time.models import Ledger, Session, Span, Turn
from codex_time.reporting import report


def session(
    sid: str,
    cwd: str,
    start: str,
    end: str,
    *,
    archived: bool = False,
    child: bool = False,
    parent: str | None = None,
) -> Session:
    first, last = datetime.fromisoformat(start), datetime.fromisoformat(end)
    return Session(
        id=sid,
        cwd=cwd,
        title=f"Task {sid}",
        created=first,
        updated=last,
        archived=archived,
        is_child=child,
        parent_id=parent,
        turns={sid: Turn(id=sid, cwd=cwd, start=first, end=last)},
    )


def fixture() -> Ledger:
    a = session("alpha", "/repos/a", "2026-10-06T13:00:00Z", "2026-10-06T15:00:00Z")
    a.turns["alpha"].waits = [
        Span(
            start=datetime(2026, 10, 6, 14, tzinfo=UTC),
            end=datetime(2026, 10, 6, 14, 30, tzinfo=UTC),
        )
    ]
    a.cwd = "/repos/b"
    a.turns["later"] = Turn(
        id="later",
        cwd="/repos/b",
        start=datetime(2026, 10, 6, 15, tzinfo=UTC),
        end=datetime(2026, 10, 6, 15, 30, tzinfo=UTC),
    )
    b = session("beta", "/repos/a", "2026-10-06T13:00:00Z", "2026-10-06T14:00:00Z", archived=True)
    child = session("child", "/repos/a", "2026-10-06T13:00:00Z", "2026-10-06T14:00:00Z", child=True)
    parented = session(
        "parented", "/repos/a", "2026-10-06T13:00:00Z", "2026-10-06T14:00:00Z", parent="alpha"
    )
    old = session("old", "/repos/a", "2026-10-05T13:00:00Z", "2026-10-05T14:00:00Z")
    return Ledger(sessions={s.id: s for s in [a, b, child, parented, old]})


def test_day_groups_original_directories_and_sessions_conserving_work() -> None:
    from codex_time.reporting import daily_report

    ledger = fixture()
    before = ledger.model_dump(mode="json")
    data = daily_report(ledger, selected_date=date(2026, 10, 6))
    assert ledger.model_dump(mode="json") == before
    assert data["date"] == "2026-10-06"
    assert data["timezone"] == "America/Toronto"
    assert data["total_seconds"] == 10800
    assert data["total_microseconds"] == 10_800_000_000
    assert [d["cwd"] for d in data["directories"]] == ["/repos/a", "/repos/b"]
    first, last = data["directories"]
    assert first["total_seconds"] == 9000
    assert first["share_percent"] == pytest.approx(100 * 9000 / 10800)
    assert [(s["id"], s["total_seconds"]) for s in first["sessions"]] == [
        ("alpha", 5400),
        ("beta", 3600),
    ]
    assert first["sessions"][0]["title"] == "Task alpha"
    assert [(s["id"], s["total_seconds"]) for s in last["sessions"]] == [("alpha", 1800)]
    assert "historical_upper_bound" in data["quality"]
    assert data["total_microseconds"] == sum(d["total_microseconds"] for d in data["directories"])
    for directory in data["directories"]:
        assert directory["total_microseconds"] == sum(
            s["total_microseconds"] for s in directory["sessions"]
        )
    existing = report(
        ledger,
        cwd="/",
        all_directories=True,
        archive="all",
        start=date(2026, 10, 6),
        end=date(2026, 10, 6),
    )
    assert data["total_microseconds"] == existing["total_microseconds"]


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"cwd": "/repos/a"}, 9000),
        ({"cwd": "/repos/b"}, 1800),
        ({"archive": "active"}, 7200),
        ({"archive": "archived"}, 3600),
        ({"session_id": "alpha"}, 7200),
        ({"session_id": "child"}, 0),
        ({"session_id": "missing"}, 0),
        ({"cwd": "/repos/missing"}, 0),
    ],
)
def test_day_filters(kwargs: dict[str, str], expected: int) -> None:
    from codex_time.reporting import daily_report

    data = daily_report(fixture(), selected_date=date(2026, 10, 6), **kwargs)
    assert data["total_seconds"] == expected
    assert all(s["total_seconds"] > 0 for d in data["directories"] for s in d["sessions"])


def test_same_session_overlap_waits_and_microseconds() -> None:
    from codex_time.reporting import daily_report

    s = session("one", "/a", "2026-10-06T13:00:00Z", "2026-10-06T13:00:01.000001Z")
    start = s.created
    s.turns["two"] = Turn(
        id="two",
        cwd="/b",
        start=start + timedelta(microseconds=1),
        end=start + timedelta(seconds=2, microseconds=3),
    )
    s.turns["one"].waits = [
        Span(
            start=start + timedelta(microseconds=2),
            end=start + timedelta(seconds=1, microseconds=2),
        )
    ]
    data = daily_report(Ledger(sessions={s.id: s}), selected_date=date(2026, 10, 6))
    assert data["total_microseconds"] == 1_000_003
    assert [d["cwd"] for d in data["directories"]] == ["/b", "/a"]
    assert data["directories"][1]["total_microseconds"] == 1
    assert sum(d["total_microseconds"] for d in data["directories"]) == 1_000_003


@pytest.mark.parametrize(
    ("day", "start", "end", "hours"),
    [
        (date(2026, 3, 8), "2026-03-08T05:00:00Z", "2026-03-09T04:00:00Z", 23),
        (date(2026, 11, 1), "2026-11-01T04:00:00Z", "2026-11-02T05:00:00Z", 25),
    ],
)
def test_local_dst_day_uses_elapsed_utc(day: date, start: str, end: str, hours: int) -> None:
    from codex_time.reporting import daily_report

    s = session("dst", "/work", start, end)
    assert (
        daily_report(Ledger(sessions={s.id: s}), selected_date=day)["total_seconds"] == hours * 3600
    )


def test_midnight_timezone_and_empty_day() -> None:
    from codex_time.reporting import daily_report

    s = session("midnight", "/work", "2026-10-07T03:30:00Z", "2026-10-07T04:30:00Z")
    ledger = Ledger(sessions={s.id: s}, diagnostics=["Fixture diagnostic"])
    for day in [date(2026, 10, 6), date(2026, 10, 7)]:
        assert daily_report(ledger, selected_date=day)["total_seconds"] == 1800
    assert (
        daily_report(ledger, selected_date=date(2026, 10, 7), timezone_name="UTC")["total_seconds"]
        == 3600
    )
    empty = daily_report(ledger, selected_date=date(2026, 10, 8))
    assert empty["total_microseconds"] == 0
    assert empty["directories"] == []
    assert empty["quality"] == []
    assert empty["diagnostics"] == ["Fixture diagnostic"]


def test_unfinished_only_uses_bounded_coverage_and_deterministic_ties() -> None:
    from codex_time.reporting import daily_report

    a = session("z", "/a", "2026-10-06T13:00:00Z", "2026-10-06T13:01:00Z")
    b = a.model_copy(deep=True, update={"id": "a"})
    turn = b.turns["z"]
    turn.end = None
    turn.coverage = [Span(start=turn.start, end=turn.start + timedelta(seconds=60))]
    c = a.model_copy(deep=True, update={"id": "b", "cwd": "/b"})
    c.turns["z"].cwd = "/b"
    ledger = Ledger(sessions={s.id: s for s in [c, a, b]})
    data = daily_report(ledger, selected_date=date(2026, 10, 6))
    assert data["total_seconds"] == 180
    assert [d["cwd"] for d in data["directories"]] == ["/a", "/b"]
    assert [s["id"] for s in data["directories"][0]["sessions"]] == ["a", "z"]
    assert (
        daily_report(Ledger())["date"]
        == datetime.now(UTC).astimezone(ZoneInfo("America/Toronto")).date().isoformat()
    )


def test_empty_waited_unobserved_and_exact_midnight_have_no_rows() -> None:
    from codex_time.reporting import daily_report

    waited = session("waited", "/work", "2026-10-06T13:00:00Z", "2026-10-06T14:00:00Z")
    waited.turns["waited"].waits = [Span(start=waited.created, end=waited.updated)]
    unknown = waited.model_copy(deep=True, update={"id": "unknown"})
    unknown.turns["waited"].end = None
    midnight = session("boundary", "/work", "2026-10-06T03:30:00Z", "2026-10-06T04:00:00Z")
    ledger = Ledger(sessions={s.id: s for s in [waited, unknown, midnight]})
    assert daily_report(ledger, selected_date=date(2026, 10, 6))["directories"] == []
    assert daily_report(ledger, selected_date=date(2026, 10, 5))["total_seconds"] == 1800


def test_today_uses_selected_timezone_at_year_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    import codex_time.reporting as reporting

    class Clock(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            value = datetime(2027, 1, 1, 2, tzinfo=UTC)
            return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr(reporting, "datetime", Clock)
    assert reporting.daily_report(Ledger())["date"] == "2026-12-31"
    assert reporting.daily_report(Ledger(), timezone_name="UTC")["date"] == "2027-01-01"


def test_directory_duration_ties_sort_by_original_path() -> None:
    from codex_time.reporting import daily_report

    a = session("a", "/a", "2026-10-06T13:00:00Z", "2026-10-06T13:01:00Z")
    b = session("b", "/b", "2026-10-06T13:00:00Z", "2026-10-06T13:01:00Z")
    data = daily_report(Ledger(sessions={"b": b, "a": a}), selected_date=date(2026, 10, 6))
    assert [d["cwd"] for d in data["directories"]] == ["/a", "/b"]
    assert [d["share_percent"] for d in data["directories"]] == [50, 50]


def test_many_fractional_intervals_conserve_nested_integer_totals() -> None:
    from codex_time.reporting import daily_report

    ledger = Ledger()
    for index in range(30):
        s = session(
            str(index), f"/repo/{index % 3}", "2026-10-06T13:00:00Z", "2026-10-06T13:00:00.100000Z"
        )
        ledger.sessions[s.id] = s
    data = daily_report(ledger, selected_date=date(2026, 10, 6))
    assert data["total_microseconds"] == 3_000_000
    for directory in data["directories"]:
        assert directory["total_microseconds"] == 1_000_000
        assert sum(s["total_microseconds"] for s in directory["sessions"]) == 1_000_000
    assert sum(d["total_microseconds"] for d in data["directories"]) == data["total_microseconds"]
