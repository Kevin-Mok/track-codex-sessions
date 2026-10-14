"""Real Linux source events coalesce and lost notifications request reconciliation."""

from pathlib import Path


def test_real_file_events_coalesce_and_discover_new_directories(tmp_path: Path) -> None:
    from codex_time.changes import ChangeWatcher

    sessions = tmp_path / "sessions"
    sessions.mkdir()
    watcher = ChangeWatcher(tmp_path)
    try:
        assert watcher.available
        nested = sessions / "2026" / "10"
        nested.mkdir(parents=True)
        path = nested / "rollout.jsonl"
        path.write_text("one\n")
        paths, overflow = watcher.drain()
        assert path in paths
        assert not overflow
        for i in range(200):
            with path.open("a") as stream:
                stream.write(f"{i}\n")
        paths, overflow = watcher.drain()
        assert paths == [path]
        assert not overflow
        assert watcher.drain() == ([], False)
    finally:
        watcher.close()
    assert watcher.fd is None


def test_queue_limit_requests_reconciliation_without_retaining_storm(tmp_path: Path) -> None:
    from codex_time.changes import ChangeWatcher

    sessions = tmp_path / "sessions"
    sessions.mkdir()
    watcher = ChangeWatcher(tmp_path, max_pending=3)
    try:
        for i in range(20):
            (sessions / f"{i}.jsonl").write_text("record\n")
        paths, overflow = watcher.drain()
        assert len(paths) <= 3
        assert overflow
        assert watcher.drain() == ([], False)
    finally:
        watcher.close()


def test_watch_limit_falls_back_explicitly(tmp_path: Path) -> None:
    from codex_time.changes import ChangeWatcher

    (tmp_path / "sessions" / "nested").mkdir(parents=True)
    watcher = ChangeWatcher(tmp_path, max_watches=1)
    try:
        _, overflow = watcher.drain()
        assert overflow
        assert watcher.needs_reconciliation
    finally:
        watcher.close()


def test_archive_move_keeps_source_visible(tmp_path: Path) -> None:
    from codex_time.changes import ChangeWatcher

    sessions, archive = tmp_path / "sessions", tmp_path / "archived_sessions"
    sessions.mkdir()
    archive.mkdir()
    path = sessions / "one.jsonl"
    path.write_text("record\n")
    watcher = ChangeWatcher(tmp_path)
    try:
        moved = archive / path.name
        path.rename(moved)
        paths, overflow = watcher.drain()
        assert moved in paths
        assert not overflow
    finally:
        watcher.close()
