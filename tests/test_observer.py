from datetime import UTC, datetime, timedelta

from codex_time.accounting import segments, total_seconds
from codex_time.models import Ledger, Observation, Session, Turn
from codex_time.observer import Observer


def ledger() -> Ledger:
    now = datetime(2026, 10, 6, 16, tzinfo=UTC)
    return Ledger(
        sessions={
            "a": Session(
                id="a",
                cwd="/work",
                created=now,
                updated=now,
                turns={"turn": Turn(id="turn", start=now, cwd="/work")},
            )
        }
    )


def sample(state: str, seconds: int) -> Observation:
    return Observation.model_validate(
        {
            "session_id": "a",
            "state": state,
            "at": datetime(2026, 10, 6, 16, tzinfo=UTC) + timedelta(seconds=seconds),
        }
    )


def test_silent_work_wait_and_idle() -> None:
    data = ledger()
    observer = Observer()
    for state, sec in [
        ("working", 0),
        ("working", 1),
        ("waiting", 2),
        ("waiting", 3),
        ("working", 4),
        ("working", 5),
        ("idle", 6),
    ]:
        observer.apply(data, [sample(state, sec)])
    assert total_seconds(segments(list(data.sessions["a"].turns.values()))) == 4
    assert (
        sum((s.end - s.start).total_seconds() for s in data.sessions["a"].turns["turn"].waits) == 2
    )


def test_outage_restart_and_stale_no_extrapolation() -> None:
    data = ledger()
    observer = Observer()
    observer.apply(data, [sample("working", 0)])
    observer.apply(data, [sample("working", 1)])
    observer.apply(data, [])
    observer.apply(data, [sample("working", 60)])
    restarted = Observer()
    restarted.apply(data, [sample("working", 90)])
    restarted.apply(data, [sample("working", 91)])
    assert total_seconds(segments(list(data.sessions["a"].turns.values()))) == 2
    assert "observation_gap" in data.sessions["a"].turns["turn"].quality


def test_concurrent_roots_accrue_independently() -> None:
    data = ledger()
    data.sessions["b"] = data.sessions["a"].model_copy(deep=True)
    data.sessions["b"].id = "b"
    observer = Observer()
    for sec in range(3):
        a = sample("working", sec)
        b = a.model_copy(update={"session_id": "b"})
        observer.apply(data, [a, b])
    assert sum(total_seconds(segments(list(s.turns.values()))) for s in data.sessions.values()) == 4


def test_unknown_marks_gap_and_does_not_count_prior_state_until_failed_poll() -> None:
    data = ledger()
    observer = Observer()
    observer.apply(data, [sample("working", 0)])
    observer.apply(data, [sample("unknown", 1)])
    assert total_seconds(segments(list(data.sessions["a"].turns.values()))) == 0
    assert "observation_gap" in data.sessions["a"].turns["turn"].quality


def test_sampling_uncertainty_is_durable() -> None:
    data = ledger()
    observer = Observer()
    a = sample("working", 0)
    b = sample("waiting", 1)
    b = b.model_copy(update={"uncertainty_seconds": 1.25})
    observer.apply(data, [a])
    observer.apply(data, [b])
    assert data.sessions["a"].turns["turn"].sampling_uncertainty_seconds == 1.25
    assert "live_status" in data.sessions["a"].turns["turn"].provenance


def test_restart_preserves_gap_provenance() -> None:
    data = ledger()
    observer = Observer()
    observer.apply(data, [sample("working", 0)])
    observer.apply(data, [sample("working", 1)])
    Observer().apply(data, [sample("working", 30)])
    assert "observation_gap" in data.sessions["a"].turns["turn"].quality
