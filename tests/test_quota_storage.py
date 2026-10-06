"""Durable allowance journal migration, validation and incremental writes."""

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from codex_time.models import Ledger, QuotaObservation, Session, Turn
from codex_time.storage import Store, StoreError


def quota(second: int = 0, used: float = 10) -> QuotaObservation:
    return QuotaObservation(
        at=datetime(2026, 10, 6, 16, tzinfo=UTC) + timedelta(seconds=second),
        limit_id="codex", plan_type="pro", bucket="primary", window_minutes=10080,
        resets_at=1791760139, used_percent=used,
    )


def data() -> Ledger:
    first = quota()
    return Ledger(quota_observations=[first], sessions={"s": Session(
        id="s", cwd="/work", created=first.at, updated=first.at,
        turns={"t": Turn(id="t", cwd="/work", start=first.at,
                         end=first.at + timedelta(seconds=60))},
    )})


def test_journal_append_restart_and_native_projection_stay_idempotent(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    ledger = data()
    with store.writer():
        store.save(ledger)
        journal = store.root / "quota-observations.jsonl"
        original = journal.read_bytes()
        stat = journal.stat()
        records = {p.name: p.read_bytes() for p in (store.root / "records").rglob("*.json")}
        store.save(ledger)
        assert journal.stat().st_mtime_ns == stat.st_mtime_ns
        ledger.quota_observations.append(quota(60, 11))
        store.save(ledger)
        assert journal.read_bytes().startswith(original)
        assert len(journal.read_text().splitlines()) == 2
        assert "quota_observations" not in json.loads((store.root / "ledger.json").read_text())
        assert records == {p.name: p.read_bytes() for p in (store.root / "records").rglob("*.json")}
    reloaded = Store(store.root, store.runtime).load()
    assert reloaded == ledger
    with store.writer():
        store.save(reloaded)
    assert len(journal.read_text().splitlines()) == 2
    allowed = {"at", "limit_id", "plan_type", "bucket", "window_minutes", "resets_at",
               "used_percent", "provenance"}
    assert all(set(json.loads(line)) == allowed for line in journal.read_text().splitlines())


@pytest.mark.parametrize("version", [1, 2, 3])
def test_embedded_history_union_migrates_without_losing_existing_journal(
    tmp_path: Path, version: int,
) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    payload = data().model_dump(mode="json")
    payload["version"] = version
    (store.root / "ledger.json").write_text(json.dumps(payload))
    journal = store.root / "quota-observations.jsonl"
    journal.write_text(quota().model_dump_json() + "\n" + quota(60, 11).model_dump_json() + "\n")
    ledger = store.load()
    assert ledger.quota_observations == [quota(), quota(60, 11)]
    with store.writer():
        store.save(ledger)
    assert "quota_observations" not in json.loads((store.root / "ledger.json").read_text())
    assert len(journal.read_text().splitlines()) == 2
    assert Store(store.root, store.runtime).load() == ledger


@pytest.mark.parametrize("suffix", ['{"used_percent": "SECRET"}\n', '{"at":'])
def test_corrupt_or_partial_journal_blocks_load_and_save_without_truncation(
    tmp_path: Path, suffix: str,
) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    with store.writer():
        store.save(data())
    journal = store.root / "quota-observations.jsonl"
    with journal.open("a") as out:
        out.write(suffix)
    before = journal.read_bytes()
    with pytest.raises(StoreError, match="quota-observations.jsonl"):
        Store(store.root, store.runtime).load()
    with store.writer(), pytest.raises(StoreError, match="quota-observations.jsonl"):
        store.save(data())
    assert journal.read_bytes() == before


def test_fingerprint_tracks_journal_append_and_external_same_size_restore(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    ledger = data()
    with store.writer():
        store.save(ledger)
    initial = store.fingerprint()
    journal = store.root / "quota-observations.jsonl"
    stat = journal.stat()
    original = journal.read_bytes()
    journal.write_bytes(original.replace(b'10.0', b'20.0'))
    os.utime(journal, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    changed = store.fingerprint()
    assert changed != initial
    assert Store(store.root, store.runtime).fingerprint() == changed
    journal.write_bytes(original)
    assert store.fingerprint() == initial
    with store.writer():
        ledger.quota_observations.append(quota(60, 11))
        store.save(ledger)
    assert store.fingerprint() != initial


def test_journal_only_history_is_preserved_when_ledger_missing(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    journal = store.root / "quota-observations.jsonl"
    journal.write_text(quota().model_dump_json() + "\n")
    assert store.load().quota_observations == [quota()]


def test_unchanged_and_append_saves_do_not_reserialize_old_quota_samples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    ledger = data()
    with store.writer():
        store.save(ledger)
        original = QuotaObservation.model_dump_json
        def reject_old(self: QuotaObservation, *args: object, **kwargs: object) -> str:
            if self is ledger.quota_observations[0]:
                raise AssertionError("unchanged saved quota was serialized again")
            return original(self, *args, **kwargs)
        monkeypatch.setattr(QuotaObservation, "model_dump_json", reject_old)
        store.save(ledger)
        ledger.quota_observations.append(quota(60, 11))
        store.save(ledger)


def test_embedded_duplicate_observations_load_as_exact_union(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    ledger = data()
    ledger.quota_observations.append(quota())
    (store.root / "ledger.json").write_text(ledger.model_dump_json())
    assert store.load().quota_observations == [quota()]


def test_migration_preserves_evidence_if_ledger_write_is_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    store.root.mkdir()
    original = data().model_dump_json().encode()
    (store.root / "ledger.json").write_bytes(original)
    assert store.fingerprint() == hashlib.sha256(original).hexdigest()
    ledger = store.load()
    def interrupt(path: Path, value: object) -> None:
        raise OSError("simulated interruption before ledger replacement")
    monkeypatch.setattr(store, "_write", interrupt)
    with store.writer(), pytest.raises(OSError, match="simulated interruption"):
        store.save(ledger)
    assert (store.root / "ledger.json").read_bytes() == original
    assert Store(store.root, store.runtime).load() == ledger
    assert (store.root / "quota-observations.jsonl").read_text() == quota().model_dump_json() + "\n"


def test_fingerprint_cache_avoids_unchanged_file_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "data", tmp_path / "runtime")
    with store.writer():
        store.save(data())
    expected = store.fingerprint()
    original_open = Path.open
    def refuse_read(path: Path, *args: object, **kwargs: object):
        if path.name in {"ledger.json", "quota-observations.jsonl"}:
            raise AssertionError("unchanged durable file was reopened")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", refuse_read)
    assert store.fingerprint() == expected
