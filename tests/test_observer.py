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


def test_minute_cadence_counts_quiet_work_and_waits_with_real_uncertainty() -> None:
    data = ledger()
    observer = Observer(max_gap=75, sample_seconds=60)
    for state, seconds in [("working", 0), ("waiting", 60), ("working", 120), ("idle", 180)]:
        observer.apply(data, [sample(state, seconds)])
    turn = data.sessions["a"].turns["turn"]
    assert total_seconds(segments([turn])) == 120
    assert [(span.start, span.end) for span in turn.waits] == [
        (sample("waiting", 60).at, sample("working", 120).at)
    ]
    assert turn.sampling_uncertainty_seconds == 60
    assert "sampled_waits_60s" in turn.quality
    assert "sampled_waits_1s" not in turn.quality


def test_minute_cadence_never_bridges_a_missed_sample() -> None:
    data = ledger()
    observer = Observer(max_gap=75, sample_seconds=60)
    for seconds in [0, 60, 180, 240]:
        observer.apply(data, [sample("working", seconds)])
    turn = data.sessions["a"].turns["turn"]
    assert [(span.start, span.end) for span in turn.coverage] == [
        (sample("working", 0).at, sample("working", 60).at),
        (sample("working", 180).at, sample("working", 240).at),
    ]
    assert total_seconds(segments([turn])) == 120
    assert "observation_gap" in turn.quality
    assert turn.sampling_uncertainty_seconds == 60


def test_minute_cadence_reports_actual_jitter_instead_of_one_second_accuracy() -> None:
    data = ledger()
    observer = Observer(max_gap=75, sample_seconds=60)
    observer.apply(data, [sample("working", 0)])
    observer.apply(data, [sample("working", 75)])
    turn = data.sessions["a"].turns["turn"]
    assert total_seconds(segments([turn])) == 75
    assert turn.sampling_uncertainty_seconds == 75
    assert "sampled_waits_60s" in turn.quality


def test_minute_cadence_preserves_earlier_precise_waits() -> None:
    data = ledger()
    observer = Observer()
    for state, seconds in [("working", 0), ("waiting", 1), ("working", 2), ("idle", 3)]:
        observer.apply(data, [sample(state, seconds)])
    Observer(max_gap=75, sample_seconds=60).apply(data, [sample("working", 60)])
    turn = data.sessions["a"].turns["turn"]
    assert [(span.start, span.end) for span in turn.waits] == [
        (sample("waiting", 1).at, sample("working", 2).at)
    ]
    assert total_seconds(segments([turn])) == 2


def test_minute_idle_samples_do_not_modify_historical_evidence() -> None:
    data = ledger()
    observer = Observer(max_gap=75, sample_seconds=60)
    before = data.model_dump_json()
    for second in (0, 60, 120):
        observation = sample("idle", second)
        observation.uncertainty_seconds = 60 + second / 1000
        observer.apply(data, [observation])
    assert data.model_dump_json() == before
