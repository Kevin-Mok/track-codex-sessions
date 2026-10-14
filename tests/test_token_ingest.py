"""Token evidence survives incremental replay without multiplying consumption."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from codex_time.ingest import RolloutReader
from codex_time.models import Ledger
from codex_time.storage import Store

BASE = datetime(2026, 10, 8, 16, tzinfo=UTC)


def event(kind: str, second: int, **payload: object) -> str:
    return (
        json.dumps(
            {
                "type": kind,
                "timestamp": (BASE + timedelta(seconds=second)).isoformat(),
                "payload": payload,
            }
        )
        + "\n"
    )


def counts(value: int, cached: int = 0) -> dict[str, int]:
    return {
        "input_tokens": value,
        "cached_input_tokens": cached,
        "output_tokens": value // 10,
        "reasoning_output_tokens": value // 20,
        "total_tokens": value + value // 10,
    }


def usage(second: int, value: int, *, last: int | None = None, **extra: object) -> str:
    return event(
        "event_msg",
        second,
        type="token_count",
        info={
            "total_token_usage": counts(value),
            "last_token_usage": counts(value if last is None else last),
            **extra,
        },
    )


def source(home: Path, tail: list[str], **meta: object) -> Path:
    path = home / "sessions" / "one.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        event("session_meta", 0, id="root", cwd="/a", source="cli", **meta)
        + event("turn_context", 0, turn_id="t", cwd="/a", model="A")
        + "".join(tail)
    )
    return path


def test_cumulative_duplicates_count_once_and_preserve_content_free_evidence(
    tmp_path: Path,
) -> None:
    source(tmp_path, [usage(1, 100, prompt="SECRET"), usage(2, 100), usage(3, 160, last=60)])
    ledger = Ledger()
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)
    observations = getattr(ledger, "usage_observations", [])
    assert len(observations) == 3
    assert [u.delta.input_tokens for u in observations] == [100, 0, 60]
    assert [u.request_input_tokens for u in observations] == [100, None, 60]
    assert [u.model_id for u in observations] == ["A", "A", "A"]
    assert [u.cwd for u in observations] == ["/a", "/a", "/a"]
    assert all(u.turn_id == "t" for u in observations)
    assert "SECRET" not in ledger.model_dump_json() + json.dumps(reader.checkpoints)
    before = ledger.model_dump_json()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.model_dump_json() == before


def test_usage_only_session_keeps_historical_context_across_restart_and_archive(
    tmp_path: Path,
) -> None:
    path = source(tmp_path, [usage(1, 100)])
    ledger = Ledger()
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)
    with path.open("a") as stream:
        stream.write(event("turn_context", 2, turn_id="next", cwd="/b", model="B"))
        stream.write(usage(3, 150, last=50))
    archive = tmp_path / "archived_sessions"
    archive.mkdir()
    path.rename(archive / path.name)
    RolloutReader(tmp_path, reader.checkpoints).scan(ledger)
    assert [(u.cwd, u.model_id, u.delta.input_tokens) for u in ledger.usage_observations] == [
        ("/a", "A", 100),
        ("/b", "B", 50),
    ]
    assert not ledger.sessions["root"].turns
    assert ledger.sessions["root"].archived


def test_reset_and_last_only_samples_retain_uncertainty_without_adding_last(tmp_path: Path) -> None:
    source(
        tmp_path,
        [
            usage(1, 100),
            usage(2, 10),
            usage(3, 30, last=20),
            event("event_msg", 4, type="token_count", info={"last_token_usage": counts(20)}),
            event("event_msg", 5, type="token_count", info={"last_token_usage": counts(20)}),
        ],
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    samples = ledger.usage_observations
    assert [u.delta.input_tokens if u.delta is not None else None for u in samples] == [
        100,
        None,
        20,
        None,
        None,
    ]
    assert "counter_reset" in samples[1].diagnostics
    assert "missing_cumulative_usage" in samples[3].diagnostics


def test_context_gap_retains_tokens_without_guessing_model_or_directory(tmp_path: Path) -> None:
    source(
        tmp_path,
        [
            usage(1, 100),
            event("turn_context", 2, turn_id="next", cwd="/b", model="B"),
            usage(3, 200, last=20),
        ],
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    last = ledger.usage_observations[-1]
    assert last.delta.input_tokens == 100
    assert last.model_id is None and last.cwd is None
    assert last.request_input_tokens is None
    assert "ambiguous_model_attribution" in last.diagnostics
    assert "ambiguous_directory_attribution" in last.diagnostics


def test_v3_checkpoint_cannot_hide_backfill_and_roundtrip_is_idempotent(tmp_path: Path) -> None:
    home = tmp_path / "home"
    path = source(home, [usage(1, 100)])
    stat = path.stat()
    old = {
        "version": 3,
        "files": {
            f"{stat.st_dev}:{stat.st_ino}": {
                "offset": stat.st_size,
                "session_id": "root",
                "cwd": "/a",
            }
        },
    }
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    (store.root / "ledger.json").write_text('{"version":3,"sessions":{}}')
    ledger = store.load()
    reader = RolloutReader(home, old)
    reader.scan(ledger)
    assert ledger.version == 4
    assert ledger.usage_observations[0].delta.input_tokens == 100
    assert reader.checkpoints["version"] == 4
    with store.writer():
        store.save(ledger)
    restored = Store(store.root, store.runtime).load()
    before = restored.model_dump_json()
    RolloutReader(home).scan(restored)
    assert restored.model_dump_json() == before
    assert restored == ledger


def test_fork_inherited_history_is_baseline_and_fork_stays_root(tmp_path: Path) -> None:
    path = source(tmp_path, [usage(-20, 100), usage(2, 150, last=50)], forked_from_id="parent")
    # The inherited context precedes fork creation and is safe evidence, not new usage.
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.sessions["root"].parent_id is None
    assert not ledger.sessions["root"].is_child
    assert len(ledger.usage_observations) == 1
    assert ledger.usage_observations[0].delta.input_tokens == 50
    original = ledger.model_dump_json()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.model_dump_json() == original
    assert path.exists()


def test_fork_without_inherited_baseline_does_not_claim_first_cumulative(tmp_path: Path) -> None:
    source(tmp_path, [usage(1, 1000, last=10), usage(2, 1030, last=30)], forked_from_id="parent")
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.usage_observations[0].delta is None
    assert "fork_baseline_unavailable" in ledger.usage_observations[0].diagnostics
    assert ledger.usage_observations[1].delta.input_tokens == 30


def test_missing_invalid_counts_are_not_coerced_to_zero_and_partial_line_waits(
    tmp_path: Path,
) -> None:
    final = usage(2, 150, last=50)
    path = source(
        tmp_path,
        [
            event(
                "event_msg",
                1,
                type="token_count",
                info={
                    "total_token_usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": True,
                        "output_tokens": -1,
                        "cache_write_input_tokens": "12",
                    },
                },
            ),
            final[:40],
        ],
    )
    ledger = Ledger()
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)
    first = ledger.usage_observations[0]
    assert first.delta.input_tokens == 100
    assert first.delta.cached_input_tokens is None
    assert first.delta.output_tokens is None
    assert first.delta.cache_write_input_tokens is None
    assert first.delta.total_tokens is None
    with path.open("a") as stream:
        stream.write(final[40:])
    reader.scan(ledger)
    assert len(ledger.usage_observations) == 2
    assert ledger.usage_observations[-1].delta.output_tokens is None


def test_scan_reports_progress_during_large_source(tmp_path: Path) -> None:
    source(tmp_path, [usage(second, second * 10) for second in range(1, 2501)])
    progress: list[str] = []
    ledger = Ledger()
    RolloutReader(tmp_path, progress=progress.append).scan(ledger)
    assert len(progress) >= 4
    assert len(ledger.usage_observations) == 2500


def test_truncated_source_recovers_prior_durable_baseline_without_recounting(
    tmp_path: Path,
) -> None:
    path = source(tmp_path, [usage(1, 100)])
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    path.write_text(
        event("session_meta", 0, id="root", cwd="/a", source="cli")
        + event("turn_context", 2, turn_id="t", cwd="/b", model="B")
        + usage(3, 150, last=50)
    )
    RolloutReader(tmp_path).scan(ledger)
    assert [u.delta.input_tokens for u in ledger.usage_observations] == [100, 50]
    assert ledger.usage_observations[-1].cwd == "/b"
    assert ledger.usage_observations[-1].model_id == "B"


def test_unobserved_model_after_new_turn_is_explicitly_unknown(tmp_path: Path) -> None:
    source(
        tmp_path,
        [
            usage(1, 100),
            event("event_msg", 2, type="task_started", turn_id="new"),
            event("turn_context", 3, turn_id="new", cwd="/b"),
            usage(4, 150, last=50),
        ],
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.usage_observations[-1].model_id is None
    assert "unknown_model" in ledger.usage_observations[-1].diagnostics


def test_malformed_prefix_marks_first_counter_baseline_uncertain(tmp_path: Path) -> None:
    source(tmp_path, ["bad record\n", usage(3, 100), usage(4, 150, last=50)])
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.usage_observations[0].delta is None
    assert "baseline_unavailable" in ledger.usage_observations[0].diagnostics
    assert ledger.usage_observations[1].delta.input_tokens == 50


def test_child_initial_usage_requires_evidence_it_is_not_inherited(tmp_path: Path) -> None:
    path = tmp_path / "sessions" / "child.jsonl"
    path.parent.mkdir()
    path.write_text(
        event(
            "session_meta",
            0,
            id="child",
            cwd="/a",
            parent_thread_id="root",
            source={"subagent": {"thread_spawn": {"parent_thread_id": "root"}}},
        )
        + event("turn_context", 0, turn_id="t", cwd="/a", model="A")
        + usage(1, 1000, last=10)
        + usage(2, 1050, last=50)
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.usage_observations[0].delta is None
    assert "child_baseline_unavailable" in ledger.usage_observations[0].diagnostics
    assert ledger.usage_observations[1].delta.input_tokens == 50
    assert ledger.sessions["child"].parent_id == "root"


def test_fresh_child_with_matching_first_request_counts_actual_usage(tmp_path: Path) -> None:
    path = tmp_path / "sessions" / "child.jsonl"
    path.parent.mkdir()
    path.write_text(
        event("session_meta", 0, id="child", cwd="/a", parent_thread_id="root", source="subagent")
        + event("turn_context", 0, turn_id="t", cwd="/a", model="A")
        + usage(1, 100)
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.usage_observations[0].delta.input_tokens == 100


def test_unreadable_context_gap_does_not_assign_old_model_to_new_usage(tmp_path: Path) -> None:
    source(tmp_path, [usage(1, 100), "broken context record\n", usage(3, 150, last=50)])
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.usage_observations[-1].delta.input_tokens == 50
    assert ledger.usage_observations[-1].model_id is None
    assert ledger.usage_observations[-1].cwd is None
    assert "source_gap_attribution_unavailable" in ledger.usage_observations[-1].diagnostics


def test_restored_earlier_history_cannot_charge_a_later_counted_tranche_twice(tmp_path):
    source(tmp_path, [usage(3, 150, last=50)])
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    source(tmp_path, [usage(1, 100), usage(3, 150, last=50)])
    RolloutReader(tmp_path).scan(ledger)
    assert sum(u.delta.input_tokens or 0 for u in ledger.usage_observations if u.delta) == 150
    earlier = next(u for u in ledger.usage_observations if u.at == BASE + timedelta(seconds=1))
    assert earlier.delta is None
    assert "earlier_history_overlap" in earlier.diagnostics
    before = ledger.model_dump_json()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.model_dump_json() == before


def test_unsupported_context_payload_invalidates_stale_attribution(tmp_path):
    invalid = (
        json.dumps(
            {
                "type": "turn_context",
                "timestamp": (BASE + timedelta(seconds=2)).isoformat(),
                "payload": None,
            }
        )
        + "\n"
    )
    source(tmp_path, [usage(1, 100), invalid, usage(3, 150, last=50)])
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    observation = ledger.usage_observations[-1]
    assert observation.delta.input_tokens == 50
    assert observation.model_id is None and observation.cwd is None
    assert "source_gap_attribution_unavailable" in observation.diagnostics
