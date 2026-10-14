"""Historical pages stay bounded while live metadata bypasses row-time ordering."""

import gc
import json
import os
import sqlite3
from pathlib import Path

import pytest

from codex_time.metadata import refresh_metadata
from codex_time.models import Ledger


def databases(home: Path, count: int = 1000) -> None:
    with sqlite3.connect(home / "state_1.sqlite") as db:
        db.execute("CREATE TABLE threads(id TEXT PRIMARY KEY,cwd,created_at,updated_at,name)")
        db.executemany(
            "INSERT INTO threads VALUES (?, '/fixture',1700000000,1700000010,?)",
            ((f"s{i}", f"Name {i}") for i in range(count)),
        )
        db.execute("CREATE TABLE thread_spawn_edges(parent_thread_id,child_thread_id)")
        db.execute("INSERT INTO thread_spawn_edges VALUES ('s999','s998')")
    with sqlite3.connect(home / "thread_history_1.sqlite") as db:
        db.execute("CREATE TABLE thread_turns(thread_id,turn_id,status,started_at,completed_at)")
        db.executemany(
            "INSERT INTO thread_turns VALUES (?, 't', 'completed',1700000000,1700000005)",
            ((f"s{i}",) for i in range(count)),
        )


def test_history_pages_bound_decoded_rows_and_active_changes_ignore_old_timestamps(
    tmp_path: Path,
) -> None:
    databases(tmp_path)
    ledger, cursors = Ledger(), {}
    calls: list[str] = []
    signatures: dict[str, str] = {}

    def changed(identity: str, signature: str) -> bool:
        calls.append(identity)
        previous = signatures.get(identity)
        signatures[identity] = signature
        return previous != signature

    assert refresh_metadata(
        tmp_path,
        ledger,
        active_ids=["s998", "s999"],
        cursors=cursors,
        row_changed=changed,
        batch_size=128,
    )
    assert len(ledger.sessions) == 130
    assert len(calls) <= 261  # 130 threads + 130 turns + one matching edge.
    assert ledger.sessions["s998"].parent_id == "s999"
    assert ledger.sessions["s998"].turns["t"].end is not None
    with sqlite3.connect(tmp_path / "state_1.sqlite") as db:
        db.execute("UPDATE threads SET name='Renamed',updated_at=1000000000 WHERE id='s999'")
    calls.clear()
    refresh_metadata(
        tmp_path, ledger, active_ids=["s999"], cursors=cursors, row_changed=changed, batch_size=128
    )
    assert ledger.sessions["s999"].title == "Renamed"
    assert len(calls) <= 261


def test_history_reconciliation_finishes_without_database_changes_and_wraps(tmp_path: Path) -> None:
    databases(tmp_path, 1000)
    ledger, cursors = Ledger(), {}
    pending = True
    rounds = 0
    while pending:
        pending = refresh_metadata(tmp_path, ledger, active_ids=[], cursors=cursors, batch_size=128)
        rounds += 1
        assert rounds <= 8
    assert rounds == 8
    assert len(ledger.sessions) == 1000
    assert sum(len(s.turns) for s in ledger.sessions.values()) == 1000
    assert all(value == 0 for value in cursors.values())
    with sqlite3.connect(tmp_path / "state_1.sqlite") as db:
        db.execute("UPDATE threads SET name='Changed historical row' WHERE id='s0'")
    assert refresh_metadata(tmp_path, ledger, active_ids=[], cursors=cursors, batch_size=128)
    assert ledger.sessions["s0"].title == "Changed historical row"


def test_incremental_index_complete_lines_precedence_and_replacement(tmp_path: Path) -> None:
    databases(tmp_path, 5)
    ledger, cursors, state, titles = Ledger(), {}, {}, {}
    index = tmp_path / "session_index.jsonl"
    index.write_text(
        json.dumps({"id": "s0", "thread_name": "Explicit"})
        + "\n"
        + '{"id":"s1","thread_name":"Partial'
    )
    refresh_metadata(
        tmp_path,
        ledger,
        cursors=cursors,
        index_state=state,
        title_get=titles.get,
        title_put=titles.__setitem__,
        batch_size=128,
    )
    assert ledger.sessions["s0"].title == "Explicit"
    first_offset = state["offset"]
    with sqlite3.connect(tmp_path / "state_1.sqlite") as db:
        db.execute("UPDATE threads SET name='Database fallback' WHERE id='s0'")
    refresh_metadata(
        tmp_path,
        ledger,
        cursors=cursors,
        index_state=state,
        title_get=titles.get,
        title_put=titles.__setitem__,
        batch_size=128,
    )
    assert ledger.sessions["s0"].title == "Explicit"
    assert state["offset"] == first_offset
    with index.open("a") as output:
        output.write(' title"}\n')
    refresh_metadata(
        tmp_path,
        ledger,
        cursors=cursors,
        index_state=state,
        title_get=titles.get,
        title_put=titles.__setitem__,
        batch_size=128,
    )
    assert ledger.sessions["s1"].title == "Partial title"
    replacement = tmp_path / "replacement"
    replacement.write_text(json.dumps({"id": "s0", "thread_name": "Replaced"}) + "\n")
    replacement.replace(index)
    refresh_metadata(
        tmp_path,
        ledger,
        cursors=cursors,
        index_state=state,
        title_get=titles.get,
        title_put=titles.__setitem__,
        batch_size=128,
    )
    assert ledger.sessions["s0"].title == "Replaced"
    assert "pending_titles" not in state


def test_unknown_index_title_joins_later_without_retaining_history_in_state(tmp_path: Path) -> None:
    ledger, state, titles = Ledger(), {}, {}
    index = tmp_path / "session_index.jsonl"
    index.write_text(
        "".join(
            json.dumps({"id": f"s{i}", "thread_name": f"Explicit {i}"}) + "\n" for i in range(300)
        )
    )
    pending = True
    rounds = 0
    while pending:
        pending = refresh_metadata(
            tmp_path,
            ledger,
            index_state=state,
            title_get=titles.get,
            title_put=titles.__setitem__,
            batch_size=128,
        )
        rounds += 1
    assert rounds == 3
    assert len(titles) == 300
    assert len(state) < 12
    databases(tmp_path, 1000)
    refresh_metadata(
        tmp_path,
        ledger,
        active_ids=["s299"],
        cursors={},
        index_state=state,
        title_get=titles.get,
        title_put=titles.__setitem__,
        batch_size=128,
    )
    assert ledger.sessions["s299"].title == "Explicit 299"


def test_incremental_index_requires_exact_title_callbacks(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="title"):
        refresh_metadata(tmp_path, Ledger(), index_state={})


def test_unchanged_partial_index_does_not_reopen_until_append(tmp_path: Path, monkeypatch) -> None:
    index = tmp_path / "session_index.jsonl"
    index.write_text('{"id":"future","thread_name":"incomplete')
    state, titles = {}, {}
    ledger = Ledger()
    assert not refresh_metadata(
        tmp_path, ledger, index_state=state, title_get=titles.get, title_put=titles.__setitem__
    )
    real_open = Path.open

    def guard(path: Path, *args, **kwargs):
        if path == index:
            raise AssertionError("unchanged partial metadata must not be reopened")
        return real_open(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", guard)
        assert not refresh_metadata(
            tmp_path, ledger, index_state=state, title_get=titles.get, title_put=titles.__setitem__
        )
    with index.open("a") as output:
        output.write(' name"}\n')
    refresh_metadata(
        tmp_path, ledger, index_state=state, title_get=titles.get, title_put=titles.__setitem__
    )
    assert titles == {"future": "incomplete name"}


def test_deleted_metadata_sources_preserve_recorded_sessions_and_turns(tmp_path: Path) -> None:
    databases(tmp_path, 5)
    ledger, cursors = Ledger(), {}
    refresh_metadata(tmp_path, ledger, cursors=cursors)
    before = ledger.model_copy(deep=True)
    for path in tmp_path.glob("*.sqlite"):
        path.unlink()
    assert not refresh_metadata(tmp_path, ledger, cursors=cursors)
    assert ledger == before


def test_read_only_database_connections_close_without_waiting_for_gc(tmp_path: Path) -> None:
    databases(tmp_path, 5)
    ledger, cursors = Ledger(), {}
    gc.collect()
    before = len(os.listdir("/proc/self/fd"))
    enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(10):
            refresh_metadata(tmp_path, ledger, cursors=cursors)
        assert len(os.listdir("/proc/self/fd")) <= before
    finally:
        if enabled:
            gc.enable()
        gc.collect()


def test_new_historical_child_is_classified_before_its_edge_page(tmp_path: Path) -> None:
    databases(tmp_path, 200)
    with sqlite3.connect(tmp_path / "state_1.sqlite") as db:
        db.executemany(
            "INSERT INTO thread_spawn_edges VALUES ('external-parent',?)",
            ((f"s{i}",) for i in reversed(range(200))),
        )
    ledger = Ledger()
    assert refresh_metadata(tmp_path, ledger, active_ids=[], cursors={}, batch_size=128)
    assert ledger.sessions["s10"].is_child
    assert ledger.sessions["s10"].parent_id == "external-parent"
