"""Saved picker generations refresh promptly without repeating idle history work."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import codex_time.presentation as presentation
import codex_time.storage as storage
from codex_time.incremental_storage import IndexedStore, session_path
from codex_time.models import Ledger, Observation, Session, Turn
from codex_time.storage import Store

AT = datetime(2026, 10, 14, 15, tzinfo=UTC)


def seed(root: Path, state: Path) -> None:
    value = Session(
        id="one",
        cwd="/fixture",
        title="Original title",
        created=AT,
        updated=AT,
        turns={"turn": Turn(id="turn", cwd="/fixture", start=AT, end=AT + timedelta(seconds=10))},
    )
    writer = Store(root, state)
    with writer.writer():
        writer.save(Ledger(sessions={value.id: value}))


def test_picker_observes_real_indexed_save_before_cache_ttl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "state"
    seed(root, state)
    clock = [0.0]
    monkeypatch.setattr(storage, "monotonic", lambda: clock[0])
    with IndexedStore(root, state) as index:
        picker = Store(root, state)
        first = picker.picker_snapshot()
        changed = index.ledger.sessions["one"]
        changed.title = "Persisted rename"
        changed.turns["turn"].end = AT + timedelta(seconds=10, microseconds=125000)
        index.flush()
        clock[0] = 1
        refreshed = picker.picker_snapshot()
        assert refreshed.sessions["one"].title == "Persisted rename"
        assert refreshed.sessions["one"].turns["turn"].end == changed.turns["turn"].end
        assert refreshed is not first


def test_picker_unchanged_reads_do_not_load_serialize_or_walk_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "state"
    seed(root, state)
    with IndexedStore(root, state):
        pass
    clock = [0.0]
    monkeypatch.setattr(storage, "monotonic", lambda: clock[0])
    picker = Store(root, state)
    first = picker.picker_snapshot()

    def refuse(*args, **kwargs):
        raise AssertionError("unchanged picker ticks must not process history")

    with monkeypatch.context() as patch:
        patch.setattr(picker, "load", refuse)
        patch.setattr(Session, "model_dump_json", refuse)
        patch.setattr(Path, "glob", refuse)
        patch.setattr(Path, "rglob", refuse)
        for now in range(1, 60):
            clock[0] = float(now)
            assert picker.picker_snapshot() is first


def test_picker_keeps_preload_generation_when_writer_changes_during_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "state"
    seed(root, state)
    clock = [0.0]
    monkeypatch.setattr(storage, "monotonic", lambda: clock[0])
    with IndexedStore(root, state) as index:
        picker = Store(root, state)
        original_load = picker.load
        calls = []

        def load(*args, **kwargs):
            value = original_load(*args, **kwargs)
            calls.append(clock[0])
            if len(calls) == 1:
                index.ledger.sessions["one"].title = "Changed after its snapshot was read"
                index.flush()
            return value

        monkeypatch.setattr(picker, "load", load)
        assert picker.picker_snapshot().sessions["one"].title == "Original title"
        clock[0] = 1
        assert (
            picker.picker_snapshot().sessions["one"].title == "Changed after its snapshot was read"
        )
        assert len(calls) == 2


def test_picker_observes_legacy_ledger_replacement_before_ttl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "state"
    seed(root, state)
    clock = [0.0]
    monkeypatch.setattr(storage, "monotonic", lambda: clock[0])
    picker = Store(root, state)
    assert picker.picker_snapshot().sessions["one"].title == "Original title"
    writer = Store(root, state)
    with writer.writer():
        value = writer.load()
        value.sessions["one"].title = "Restored legacy name"
        writer.save(value)
    clock[0] = 1
    assert picker.picker_snapshot().sessions["one"].title == "Restored legacy name"


def test_picker_isolated_snapshot_restore_has_periodic_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "state"
    seed(root, state)
    with IndexedStore(root, state):
        pass
    clock = [0.0]
    monkeypatch.setattr(storage, "monotonic", lambda: clock[0])
    picker = Store(root, state)
    first = picker.picker_snapshot()
    restored = first.sessions["one"].model_copy(update={"title": "Isolated restored snapshot"})
    session_path(root, "one").write_text(restored.model_dump_json())
    clock[0] = 59
    assert picker.picker_snapshot() is first
    clock[0] = 60
    assert picker.picker_snapshot().sessions["one"].title == "Isolated restored snapshot"


class Screen:
    def __init__(
        self, clock: list[float], keys: list[object], tick=None, seconds_per_timeout=None
    ) -> None:
        self.clock, self.keys, self.tick = clock, iter(keys), tick
        self.seconds_per_timeout = seconds_per_timeout
        self.wait_ms = 60000
        self.frames: list[tuple[float, list[str]]] = []
        self.lines: list[str] = []

    def timeout(self, milliseconds):
        self.wait_ms = milliseconds

    def getmaxyx(self):
        return 24, 100

    def erase(self):
        self.lines = []

    def addnstr(self, y, x, text, limit, attributes):
        self.lines.append(text[:limit])

    def refresh(self):
        self.frames.append((self.clock[0], list(self.lines)))

    def get_wch(self):
        key = next(self.keys)
        if key is None:
            self.clock[0] += (
                self.wait_ms / 1000
                if self.seconds_per_timeout is None
                else self.seconds_per_timeout
            )
            if self.tick is not None:
                self.tick()
            raise presentation.curses.error()
        return key


def test_browser_refreshes_saved_change_promptly_without_rebuilding_unchanged_ticks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, state = tmp_path / "data", tmp_path / "state"
    seed(root, state)
    clock = [0.0]
    monkeypatch.setattr(storage, "monotonic", lambda: clock[0])
    monkeypatch.setattr(presentation, "monotonic", lambda: clock[0], raising=False)
    monkeypatch.setattr(presentation.curses, "curs_set", lambda _: None)
    calls, row_builds = [], []
    real_rows = presentation.build_rows
    with IndexedStore(root, state) as index:
        picker = Store(root, state)
        real_load = picker.load

        def load(*args, **kwargs):
            calls.append(clock[0])
            return real_load(*args, **kwargs)

        def rows(*args, **kwargs):
            row_builds.append(clock[0])
            return real_rows(*args, **kwargs)

        def tick():
            if clock[0] >= 2 and index.ledger.sessions["one"].title != "Painted rename":
                index.ledger.sessions["one"].title = "Painted rename"
                index.flush()

        monkeypatch.setattr(picker, "load", load)
        monkeypatch.setattr(presentation, "build_rows", rows)
        screen = Screen(clock, [None, None, None, None, "q"], tick)
        presentation._browse(
            screen,
            lambda: (
                picker.picker_snapshot(),
                {
                    "one": Observation(session_id="one", state="idle", at=AT),
                },
            ),
            "America/Toronto",
            "/fixture",
            tmp_path / "home",
        )
    painted = [
        stamp for stamp, lines in screen.frames if any("Painted rename" in line for line in lines)
    ]
    assert painted and painted[0] <= 3, f"saved change was not painted promptly: {painted}"
    assert len(calls) == 2, f"unchanged ticks reloaded history: {calls}"
    assert len(row_builds) == 2, f"unchanged ticks reprojected history: {row_builds}"
    assert len(screen.frames) == 2


def test_browser_reuses_rows_until_minute_refresh_and_still_handles_filter_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = [0.0]
    monkeypatch.setattr(presentation, "monotonic", lambda: clock[0], raising=False)
    monkeypatch.setattr(presentation.curses, "curs_set", lambda _: None)
    ledger = Ledger(
        sessions={
            sid: Session(id=sid, title=f"Title {sid}", cwd="/fixture", created=AT, updated=AT)
            for sid in ("a", "b")
        }
    )
    row_builds = []
    original = presentation.build_rows

    def rows(*args, **kwargs):
        row_builds.append(clock[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(presentation, "build_rows", rows)
    screen = Screen(clock, [*[None] * 61, "/", "b", "\n", "q"], seconds_per_timeout=1)
    presentation._browse(screen, lambda: (ledger, {}), "America/Toronto", "/fixture", tmp_path)
    before_input = [stamp for stamp in row_builds if stamp <= 60]
    assert before_input == [0, 60], f"unchanged elapsed-time refresh rebuilt history: {row_builds}"
    assert any("Title b" in line for line in screen.frames[-1][1])
    assert not any("Title a" in line for line in screen.frames[-1][1])


def test_browser_refreshes_changed_runtime_observation_before_minute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = [0.0]
    monkeypatch.setattr(presentation, "monotonic", lambda: clock[0], raising=False)
    monkeypatch.setattr(presentation.curses, "curs_set", lambda _: None)
    ledger = Ledger(
        sessions={
            "one": Session(id="one", title="Runtime state", cwd="/fixture", created=AT, updated=AT)
        }
    )
    real_rows = presentation.build_rows

    def rows(*args, **kwargs):
        kwargs["now"] = AT + timedelta(seconds=clock[0])
        return real_rows(*args, **kwargs)

    def load():
        changed = clock[0] >= 2
        return ledger, {
            "one": Observation(
                session_id="one",
                state="working" if changed else "idle",
                at=AT + timedelta(seconds=2 if changed else 0),
            )
        }

    monkeypatch.setattr(presentation, "build_rows", rows)
    screen = Screen(clock, [None, None, None, "q"])
    presentation._browse(screen, load, "America/Toronto", "/fixture", tmp_path)
    painted = [
        stamp for stamp, lines in screen.frames if any("| working |" in line for line in lines)
    ]
    assert painted and painted[0] <= 3, f"runtime-only change was not painted promptly: {painted}"
