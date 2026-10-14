"""Guard lightweight reads against accidental raw/history I/O."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_ingest import base, line, rollout

from codex_time.ingest import RolloutReader
from codex_time.models import Ledger, Session
from codex_time.storage import Store


def test_unchanged_rollout_restart_does_not_open_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = rollout(tmp_path, base())
    ledger = Ledger()
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)
    restarted = RolloutReader(tmp_path, reader.checkpoints)
    original = Path.open

    def guarded(self: Path, *args: object, **kwargs: object) -> object:
        assert self != path, "unchanged source must not be opened"
        return original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "open", guarded)
    restarted.scan(ledger)
    assert ledger.sessions["s1"].turns["t1"].end is None


def test_timing_snapshot_ignores_quota_journal_and_reloads_changed_ledger(tmp_path: Path) -> None:
    store = Store(tmp_path / "data", tmp_path / "state")
    store.root.mkdir()
    now = datetime(2026, 10, 14, tzinfo=UTC)
    ledger = Ledger(sessions={"one": Session(id="one", cwd="/a", created=now, updated=now)})
    (store.root / "ledger.json").write_text(ledger.model_dump_json())
    (store.root / "quota-observations.jsonl").write_text("deliberately invalid quota history\n")
    assert hasattr(store, "load_timing"), "timing-only snapshot reader is missing"
    first = store.load_timing()
    assert list(first.sessions) == ["one"]
    assert first.quota_observations == []
    assert store.load_timing() is first
    ledger.sessions["one"].cwd = "/longer/new-directory"
    (store.root / "ledger.json").write_text(ledger.model_dump_json())
    assert store.load_timing().sessions["one"].cwd == "/longer/new-directory"


def test_incremental_reader_does_not_reread_short_prefix_on_append(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = rollout(tmp_path, [line("session_meta", 0, id="s1", cwd="/a", source="cli")])
    reader = RolloutReader(tmp_path)
    ledger = Ledger()
    reader.scan(ledger)
    seen: list[object] = []
    original = reader._event

    def observe(record: dict[str, object], state: object, current: Ledger) -> None:
        seen.append(record.get("type"))
        original(record, state, current)  # type: ignore[arg-type]

    monkeypatch.setattr(reader, "_event", observe)
    with path.open("a") as output:
        output.write(line("event_msg", 1, type="task_started", turn_id="t1"))
    reader.scan(ledger)
    assert seen == ["event_msg"]
    assert "t1" in ledger.sessions["s1"].turns


@pytest.mark.parametrize(
    "command",
    [
        ["health", "--json"],
        ["sessions", "--json"],
        ["history", "--json"],
        ["model-time", "day", "--json"],
    ],
)
def test_lightweight_cli_does_not_load_full_journals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: list[str]
) -> None:
    import sys

    from codex_time.cli import main

    def forbidden(self: Store) -> Ledger:
        raise AssertionError("lightweight command loaded full history")

    monkeypatch.setattr(Store, "load", forbidden)
    monkeypatch.setattr(
        sys, "argv",
        ["codex-time", "--data-dir", str(tmp_path / "data"), "--state-dir",
         str(tmp_path / "state"), *command],
    )
    assert main() == 0


def test_status_reads_rollout_state_without_loading_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import json
    import sys

    from codex_time.cli import main

    rollout(tmp_path, base())

    def forbidden(self: Store) -> Ledger:
        raise AssertionError("status loaded full history")

    monkeypatch.setattr(Store, "load", forbidden)
    monkeypatch.setattr(
        sys, "argv",
        ["codex-time", "--codex-home", str(tmp_path), "--data-dir", str(tmp_path / "data"),
         "--state-dir", str(tmp_path / "state"), "status", "--json"],
    )
    assert main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["daemon"] == "stopped_or_stale"
    assert data["sessions"][0]["session_id"] == "s1"
    assert data["sessions"][0]["status"] == "mid_turn"


def test_ingester_observed_empty_file_still_detects_grown_replacement(tmp_path: Path) -> None:
    path = rollout(tmp_path, [])
    reader, ledger = RolloutReader(tmp_path), Ledger()
    reader.scan(ledger)
    path.write_text("".join(base()))
    reader.scan(ledger)
    assert "s1" in ledger.sessions
    path.write_text(
        line("session_meta", 0, id="replacement", cwd="/replacement", source="cli")
        + line("event_msg", 1, type="task_started", turn_id="new")
        + line("event_msg", 2, type="task_complete", turn_id="new")
    )
    reader.scan(ledger)
    assert "replacement" in ledger.sessions
    assert ledger.sessions["replacement"].turns["new"].end is not None


def test_partitioned_timing_observes_restore_without_layout_change(tmp_path: Path) -> None:
    import json

    from test_incremental_storage import fixture

    from codex_time.incremental_storage import IndexedStore

    root, state = tmp_path / "data", tmp_path / "state"
    fixture(root, state, 1)
    with IndexedStore(root, state):
        pass
    store = Store(root, state)
    layout = (root / "layout.json").read_bytes()
    path = next((root / "sessions").glob("*.json"))
    original = path.read_bytes()
    # Neither evidence journal is relevant to a timing-only snapshot.
    (root / "quota-observations.jsonl").write_text("invalid quota history\n")
    (root / "usage-observations.jsonl").write_text("invalid token history\n")
    first = store.load_timing()
    assert first.quota_observations == first.usage_observations == []
    updated = json.loads(original)
    updated["title"] = "Changed snapshot"
    path.write_text(json.dumps(updated))
    assert store.load_timing().sessions["0"].title == "Changed snapshot"
    path.write_bytes(original)
    assert store.load_timing().sessions["0"].title == first.sessions["0"].title
    assert (root / "layout.json").read_bytes() == layout
