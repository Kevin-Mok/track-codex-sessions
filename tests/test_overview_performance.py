"""Period reports avoid reconstructing unrelated historical sessions."""

from datetime import UTC, date, datetime, timedelta

import pytest
from test_overview import sample_ledger

from codex_time.burn import burn_report
from codex_time.model_usage import model_report
from codex_time.models import Ledger, Session, Span, Turn


@pytest.mark.parametrize("reporter", [model_report, burn_report])
def test_old_sessions_never_reconstruct_work(reporter, monkeypatch: pytest.MonkeyPatch) -> None:
    import codex_time.model_usage as module

    data = sample_ledger()
    original = module.segments
    old = data.sessions["root"].model_copy(deep=True)
    old.id = "old"
    for turn in old.turns.values():
        turn.start -= timedelta(days=10)
        if turn.end:
            turn.end -= timedelta(days=10)
        for wait in turn.waits:
            wait.start -= timedelta(days=10)
            wait.end -= timedelta(days=10)
    data.sessions[old.id] = old
    expected = reporter(data, period="day", selected_date=date(2026, 10, 6))

    def guarded(turns):
        assert all(t.start.date() != date(2026, 9, 26) for t in turns), "old work reconstructed"
        return original(turns)

    monkeypatch.setattr(module, "segments", guarded)
    assert reporter(data, period="day", selected_date=date(2026, 10, 6)) == expected


@pytest.mark.parametrize(
    "timezone_name,selected",
    [
        ("America/Toronto", date(2026, 11, 1)),
        ("America/Toronto", date(2026, 3, 8)),
        ("UTC", date(2026, 10, 6)),
    ],
)
def test_period_filter_matches_full_reconstruction(timezone_name, selected, monkeypatch):
    from zoneinfo import ZoneInfo

    import codex_time.model_usage as module

    start = datetime.combine(selected, datetime.min.time(), ZoneInfo(timezone_name)).astimezone(UTC)
    data = Ledger(
        sessions={
            "s": Session(
                id="s",
                cwd="/one",
                created=start,
                updated=start,
                turns={
                    "cross": Turn(
                        id="cross",
                        cwd="/one",
                        start=start - timedelta(hours=1),
                        end=start + timedelta(hours=2),
                    ),
                    "wait": Turn(
                        id="wait",
                        cwd="/one",
                        start=start - timedelta(days=2),
                        end=start - timedelta(days=1),
                        waits=[Span(start=start, end=start + timedelta(minutes=30))],
                    ),
                    "open": Turn(
                        id="open",
                        cwd="/one",
                        start=start - timedelta(days=1),
                        coverage=[
                            Span(start=start + timedelta(hours=3), end=start + timedelta(hours=4))
                        ],
                    ),
                },
            )
        }
    )
    actual = model_report(data, period="day", selected_date=selected, timezone_name=timezone_name)
    # Disable only the conservative session filter, retaining the existing full accounting.
    monkeypatch.setattr(module, "has_work_in_period", lambda *args: True)
    assert actual == model_report(
        data, period="day", selected_date=selected, timezone_name=timezone_name
    )
    assert actual["total_seconds"] == 9000


def test_report_observes_new_work_without_cache() -> None:
    data = sample_ledger()
    selected = date(2026, 10, 16)
    assert model_report(data, period="day", selected_date=selected)["total_seconds"] == 0
    turn = data.sessions["root"].turns["first"].model_copy(deep=True)
    turn.id = "new"
    future = turn.start + timedelta(days=10)
    turn.end = future + timedelta(minutes=1)
    turn.start = future
    turn.waits = []
    turn.model_contexts = []
    data.sessions["root"].turns[turn.id] = turn
    assert model_report(data, period="day", selected_date=selected)["total_seconds"] == 60
