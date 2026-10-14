"""Changed-source ingestion uses disk lookup state and bounded continuation."""

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from test_token_ingest import counts, event, source, usage

from codex_time.ingest import FileState, RolloutReader
from codex_time.models import Ledger, QuotaObservation, UsageObservation


class Backend:
    """Small independent backend for exercising the ingestion protocol."""

    def __init__(self) -> None:
        self.usage: dict[str, UsageObservation] = {}
        self.quota: dict[str, QuotaObservation] = {}
        self.states: dict[str, FileState] = {}
        self.checkpoint_writes = 0

    def has_usage(self, identity: str) -> bool:
        return identity in self.usage

    def previous_usage(self, sid: str, at: datetime) -> UsageObservation | None:
        return max(
            (u for u in self.usage.values() if u.session_id == sid and u.at < at
             and u.cumulative is not None),
            key=lambda u: u.at, default=None,
        )

    def has_later_usage(self, sid: str, at: datetime) -> bool:
        return any(u.session_id == sid and u.at > at for u in self.usage.values())

    def append_usage(self, observation: UsageObservation) -> None:
        self.usage.setdefault(observation.id, observation)

    def append_quota(self, observation: QuotaObservation) -> None:
        self.quota.setdefault(observation.model_dump_json(), observation)

    def checkpoint_get(self, inode: str) -> FileState | None:
        state = self.states.get(inode)
        return state.model_copy(deep=True) if state else None

    def checkpoint_put(self, inode: str, state: FileState) -> None:
        self.states[inode] = state.model_copy(deep=True)
        self.checkpoint_writes += 1

    def checkpoint_keys(self) -> Iterator[str]:
        return iter(self.states)

    def checkpoint_pending_keys(self) -> Iterator[str]:
        return (key for key, state in self.states.items() if state.contexts)


def test_disk_backend_preserves_token_dedup_without_populating_history(tmp_path: Path) -> None:
    path = source(tmp_path, [usage(1, 100), usage(2, 150, last=50)])
    expected = Ledger()
    RolloutReader(tmp_path).scan(expected)
    backend = Backend()
    ledger = Ledger()
    reader = RolloutReader(tmp_path, backend=backend)
    reader.scan_paths(ledger, [path])
    assert list(backend.usage.values()) == expected.usage_observations
    assert ledger.usage_observations == []
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    assert list(backend.usage.values()) == expected.usage_observations


def test_unchanged_source_never_opens_or_rewrites_checkpoint(tmp_path: Path, monkeypatch) -> None:
    path = source(tmp_path, [usage(1, 100)])
    backend = Backend()
    ledger = Ledger()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    writes = backend.checkpoint_writes
    def fail_open(*args, **kwargs):
        raise AssertionError("unchanged sources must not be reopened")
    monkeypatch.setattr(Path, "open", fail_open)
    RolloutReader(tmp_path, backend=backend).scan(ledger)
    assert backend.checkpoint_writes == writes


def test_bounded_batch_continues_exactly_after_restart(tmp_path: Path) -> None:
    path = source(tmp_path, [usage(i, i * 10, last=10) for i in range(1, 30)])
    expected = Ledger()
    RolloutReader(tmp_path).scan(expected)
    backend = Backend()
    ledger = Ledger()
    pending = [path]
    rounds = 0
    while pending:
        reader = RolloutReader(tmp_path, backend=backend)
        pending = reader.scan_paths(ledger, pending, max_records=3)
        rounds += 1
        assert rounds < 20
    assert rounds > 1
    assert list(backend.usage.values()) == expected.usage_observations


def test_disk_backend_truncation_preserves_old_token_baseline(tmp_path: Path) -> None:
    path = source(tmp_path, [usage(1, 100)])
    ledger, backend = Ledger(), Backend()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    path.write_text(event("session_meta", 0, id="root", cwd="/a", source="cli")
                    + event("turn_context", 2, turn_id="t", cwd="/b", model="B")
                    + usage(3, 150, last=50))
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    assert [u.delta.input_tokens for u in backend.usage.values()] == [100, 50]


def test_disk_quota_dedup_survives_reader_restart(tmp_path: Path) -> None:
    rate = {"limit_id": "codex", "primary": {"window_minutes": 300,
            "resets_at": 2000000000, "used_percent": 12.0}}
    path = source(tmp_path, [event("event_msg", 1, type="token_count",
                                info={"total_token_usage": counts(100)}, rate_limits=rate)])
    ledger, backend = Ledger(), Backend()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    backend.states.clear()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    assert len(backend.quota) == 1
    assert len(backend.usage) == 1


def test_unchanged_batch_does_not_reconcile_unrelated_pending_contexts(tmp_path: Path) -> None:
    path = source(tmp_path, [usage(1, 100)])
    ledger, backend = Ledger(), Backend()
    reader = RolloutReader(tmp_path, backend=backend)
    reader.scan_paths(ledger, [path])
    def fail_pending():
        raise AssertionError("unchanged scan must not enumerate pending history")
    backend.checkpoint_pending_keys = fail_pending
    reader.scan_paths(ledger, [path])


def test_irrelevant_bodies_are_not_decoded_as_json_values(tmp_path: Path, monkeypatch) -> None:
    import codex_time.ingest as ingest

    source(tmp_path, [event("response_item", 1, type="function_call_output",
                           call_id="not-a-wait", output="SECRET" * 100000), usage(2, 100)])
    original = ingest.json.loads
    def guarded_loads(value, *args, **kwargs):
        assert "SECRET" not in (value.decode() if isinstance(value, bytes) else value)
        return original(value, *args, **kwargs)
    monkeypatch.setattr(ingest.json, "loads", guarded_loads)
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert ledger.usage_observations[0].delta.input_tokens == 100


def test_selective_parser_preserves_invalid_nested_schema_diagnostics(tmp_path: Path) -> None:
    source(tmp_path, [event("event_msg", 1, type="token_count",
                           info={"total_token_usage": ["private"]}, rate_limits=["private"])])
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert "invalid_token_counts" in ledger.usage_observations[0].diagnostics
    assert "unsupported quota metadata skipped" in ledger.diagnostics


def padded_meta() -> str:
    return event("session_meta", 0, id="root", cwd="/a", source="cli", padding="x" * 1024)


def padded_start(tid: str) -> str:
    value = event("event_msg", 1, type="task_started", turn_id=tid)
    return " " * (512 - len(value)) + value


def rewrite_source(tmp_path: Path, tail: str) -> Path:
    path = tmp_path / "sessions" / "rewrite.jsonl"
    path.parent.mkdir()
    path.write_text(padded_meta() + tail)
    return path


def test_same_inode_same_size_rewrite_after_unchanged_prefix_is_ingested(tmp_path: Path) -> None:
    path = rewrite_source(tmp_path, padded_start("old"))
    before = path.read_bytes()
    inode = path.stat().st_ino
    ledger, backend = Ledger(), Backend()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    path.write_text(padded_meta() + padded_start("new"))
    assert path.stat().st_ino == inode
    assert path.stat().st_size == len(before)
    assert path.read_bytes()[:256] == before[:256]
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    assert "new" in ledger.sessions["root"].turns
    assert "old" in ledger.sessions["root"].turns  # durable evidence is retained


def test_same_size_rewrite_with_identical_stat_signature_checks_boundary(tmp_path: Path,
                                                                       monkeypatch) -> None:
    path = rewrite_source(tmp_path, padded_start("old"))
    ledger, backend = Ledger(), Backend()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    saved = path.stat()
    path.write_text(padded_meta() + padded_start("new"))
    original = Path.stat
    def identical_stat(self, *args, **kwargs):
        return saved if self == path else original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", identical_stat)
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    assert "new" in ledger.sessions["root"].turns


def test_verified_unchanged_source_reads_only_boundaries_and_decodes_nothing(tmp_path: Path,
                                                                          monkeypatch) -> None:
    import codex_time.ingest as ingest

    path = rewrite_source(tmp_path, padded_start("old"))
    ledger, backend = Ledger(), Backend()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    writes = backend.checkpoint_writes
    original = Path.open
    read_bytes = []
    class CountReads:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def read(self, size):
            value = self.stream.read(size)
            read_bytes.append(len(value))
            return value
        def seek(self, *args):
            return self.stream.seek(*args)
    def count_reads(self, *args, **kwargs):
        return CountReads(original(self, *args, **kwargs))
    def fail_decode(raw):
        raise AssertionError("unchanged verified input must not decode historical records")
    monkeypatch.setattr(Path, "open", count_reads)
    monkeypatch.setattr(ingest, "content_free_record", fail_decode)
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    assert sum(read_bytes) == 512
    assert backend.checkpoint_writes == writes


def test_shrink_above_consumed_offset_still_reconciles_rewritten_records(tmp_path: Path) -> None:
    partial = event("response_item", 2, type="message", content="x" * 3000).rstrip("\n")
    path = rewrite_source(tmp_path, padded_start("old") + partial)
    ledger, backend = Ledger(), Backend()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    old_state = next(iter(backend.states.values()))
    path.write_text(padded_meta() + padded_start("new") + partial[:100])
    assert old_state.offset <= path.stat().st_size < old_state.size
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    assert "new" in ledger.sessions["root"].turns


def test_growth_rewrite_checks_consumed_tail_anchor_across_restart(tmp_path: Path) -> None:
    path = rewrite_source(tmp_path, padded_start("old"))
    ledger, backend = Ledger(), Backend()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    original_prefix = path.read_bytes()[:256]
    path.write_text(padded_meta() + padded_start("new")
                    + event("event_msg", 3, type="task_complete", turn_id="new"))
    assert path.read_bytes()[:256] == original_prefix
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    assert ledger.sessions["root"].turns["new"].end is not None


def test_normal_append_decodes_only_new_records(tmp_path: Path, monkeypatch) -> None:
    import codex_time.ingest as ingest

    path = rewrite_source(tmp_path, padded_start("old"))
    ledger, backend = Ledger(), Backend()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    original = ingest.content_free_record
    decoded = []
    def count_records(raw):
        decoded.append(raw)
        return original(raw)
    monkeypatch.setattr(ingest, "content_free_record", count_records)
    with path.open("a") as output:
        output.write(event("event_msg", 3, type="task_complete", turn_id="old"))
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    assert len(decoded) == 1
    assert ledger.sessions["root"].turns["old"].end is not None


@pytest.mark.parametrize("contents", ["", "malformed record\n"])
def test_unchanged_source_without_metadata_is_not_reopened(tmp_path: Path, monkeypatch,
                                                         contents: str) -> None:
    path = rewrite_source(tmp_path, "")
    path.write_text(contents)
    ledger, backend = Ledger(), Backend()
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path])
    writes = backend.checkpoint_writes
    def fail_open(*args, **kwargs):
        raise AssertionError("unchanged empty or malformed sources must not be reopened")
    monkeypatch.setattr(Path, "open", fail_open)
    RolloutReader(tmp_path, backend=backend).scan_paths(ledger, [path], verify=False)
    assert backend.checkpoint_writes == writes
