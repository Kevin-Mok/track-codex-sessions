from datetime import datetime, timedelta

from codex_time.accounting import daily_totals, segments, total_seconds
from codex_time.models import Span, Turn


def t(seconds: int) -> datetime:
    return datetime.fromisoformat("2026-10-06T16:00:00+00:00") + timedelta(seconds=seconds)


def test_sixty_seconds_minus_twenty_wait() -> None:
    turn = Turn(
        id="one",
        start=t(0),
        end=t(60),
        cwd="/work",
        waits=[Span(start=t(10), end=t(30)), Span(start=t(20), end=t(25))],
    )
    assert total_seconds(segments([turn])) == 40


def test_overlap_work_and_idle_gaps() -> None:
    turns = [
        Turn(id="a", start=t(0), end=t(60), cwd="/work"),
        Turn(id="b", start=t(30), end=t(90), cwd="/work"),
        Turn(id="c", start=t(120), end=t(150), cwd="/work"),
    ]
    assert total_seconds(segments(turns)) == 120


def test_unfinished_has_no_invented_end() -> None:
    turn = Turn(id="one", start=t(0), cwd="/work", coverage=[Span(start=t(5), end=t(9))])
    assert total_seconds(segments([turn])) == 4


def test_cwd_preserved() -> None:
    turns = [
        Turn(id="one", start=t(0), end=t(30), cwd="/old"),
        Turn(id="two", start=t(30), end=t(60), cwd="/new"),
    ]
    assert [(x.cwd, (x.end - x.start).total_seconds()) for x in segments(turns)] == [
        ("/old", 30),
        ("/new", 30),
    ]


def test_midnight_and_dst() -> None:
    turn = Turn(
        id="night",
        cwd="/work",
        start=datetime.fromisoformat("2026-11-01T03:30:00+00:00"),
        end=datetime.fromisoformat("2026-11-01T07:30:00+00:00"),
    )
    assert daily_totals(segments([turn]), "America/Toronto") == {
        "2026-10-31": 1800,
        "2026-11-01": 12600,
    }


def test_session_waits_subtracted_after_overlapping_turn_union() -> None:
    turns = [
        Turn(id="a", start=t(0), end=t(60), cwd="/work", waits=[Span(start=t(20), end=t(40))]),
        Turn(id="b", start=t(30), end=t(90), cwd="/work"),
    ]
    assert total_seconds(segments(turns)) == 70
