"""Validated token history is append-only and resilient to interrupted migration."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from codex_time.models import Ledger, TokenCounts, UsageObservation
from codex_time.storage import Store, StoreError


def sample(identity: str = "first") -> UsageObservation:
    return UsageObservation(
        id=identity,
        session_id="s",
        at=datetime(2026, 10, 8, tzinfo=UTC),
        cwd="/work",
        model_id="A",
        cumulative=TokenCounts(input_tokens=10),
        delta=TokenCounts(input_tokens=10),
    )


def test_token_journal_is_durable_append_only_and_idempotent(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    ledger = Ledger(usage_observations=[sample()])
    with store.writer():
        store.save(ledger)
        journal = store.root / "usage-observations.jsonl"
        assert journal.exists()
        before, stamp = journal.read_bytes(), journal.stat().st_mtime_ns
        assert "usage_observations" not in json.loads((store.root / "ledger.json").read_text())
        store.save(ledger)
        assert journal.stat().st_mtime_ns == stamp
        ledger.usage_observations.extend([sample(), sample("second")])
        store.save(ledger)
        assert journal.read_bytes().startswith(before)
        assert len(journal.read_text().splitlines()) == 2
    assert Store(store.root, store.runtime).load().usage_observations == [
        sample(),
        sample("second"),
    ]


def test_usage_journal_corruption_blocks_writes_and_changes_fingerprint(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    ledger = Ledger(usage_observations=[sample()])
    with store.writer():
        store.save(ledger)
    fingerprint = store.fingerprint()
    journal = store.root / "usage-observations.jsonl"
    with journal.open("a") as stream:
        stream.write('{"SECRET":')
    assert store.fingerprint() != fingerprint
    original = journal.read_bytes()
    with pytest.raises(StoreError, match="usage-observations.jsonl"):
        store.load()
    with store.writer(), pytest.raises(StoreError, match="usage-observations.jsonl"):
        store.save(ledger)
    assert journal.read_bytes() == original


def test_conflicting_identity_is_rejected_instead_of_silently_losing_evidence(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    changed = sample().model_copy(update={"delta": TokenCounts(input_tokens=50)})
    journal = store.root / "usage-observations.jsonl"
    journal.write_text(sample().model_dump_json() + "\n" + changed.model_dump_json() + "\n")
    with pytest.raises(StoreError, match="usage-observations.jsonl"):
        store.load()


@pytest.mark.parametrize("value", [-1, True, "12", 1.2])
def test_invalid_persisted_token_count_is_rejected(tmp_path: Path, value: object) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    payload = sample().model_dump(mode="json")
    payload["delta"]["input_tokens"] = value
    (store.root / "usage-observations.jsonl").write_text(json.dumps(payload) + "\n")
    with pytest.raises(StoreError, match="usage-observations.jsonl"):
        store.load()


def test_embedded_token_migration_survives_interrupted_ledger_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    original = Ledger(usage_observations=[sample()]).model_dump_json()
    (store.root / "ledger.json").write_text(original)
    ledger = store.load()

    def interrupt(path: Path, value: object) -> None:
        raise OSError("intentional simulated interruption")

    monkeypatch.setattr(store, "_write", interrupt)
    with store.writer(), pytest.raises(OSError, match="intentional"):
        store.save(ledger)
    journal = store.root / "usage-observations.jsonl"
    assert journal.exists()
    assert journal.read_text() == sample().model_dump_json() + "\n"
    assert Store(store.root, store.runtime).load() == ledger


def test_unchanged_save_does_not_reserialize_usage_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    ledger = Ledger(usage_observations=[sample()])
    with store.writer():
        store.save(ledger)
        original = UsageObservation.model_dump_json

        def refuse_old(self: UsageObservation, *args: object, **kwargs: object) -> str:
            if self is ledger.usage_observations[0]:
                raise AssertionError("already durable history reserialized")
            return original(self, *args, **kwargs)

        monkeypatch.setattr(UsageObservation, "model_dump_json", refuse_old)
        store.save(ledger)
        ledger.usage_observations.append(sample("second"))
        store.save(ledger)
