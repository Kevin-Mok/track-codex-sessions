"""User-facing filters, bounded display clocks, and safe resume invocation."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from codex_time.models import Ledger, Observation, Session, Span, Turn
from codex_time.presentation import build_rows, launch_session, safe_text

NOW = datetime(2026, 10, 6, 16, tzinfo=UTC)


def session(sid: str, **changes: object) -> Session:
    return Session.model_validate(
        {
            "id": sid,
            "cwd": "/work",
            "title": f"Title {sid}",
            "created": NOW - timedelta(days=1),
            "updated": NOW,
            **changes,
        }
    )


def test_defaults_and_filters_keep_archive_separate_from_runtime() -> None:
    ledger = Ledger(
        sessions={
            "a": session("a"),
            "b": session("b", archived=True),
            "c": session("c", cwd="/elsewhere"),
        }
    )
    observations = {"a": Observation(session_id="a", state="waiting", at=NOW)}
    rows = build_rows(ledger, observations, cwd="/work", now=NOW)
    assert [(row.id, row.state) for row in rows] == [("a", "waiting")]
    rows = build_rows(
        ledger,
        observations,
        cwd="/work",
        now=NOW,
        all_directories=True,
        archive="all",
        query="elsewhere",
    )
    assert [row.id for row in rows] == ["c"]
    rows = build_rows(ledger, observations, cwd="/work", now=NOW, archive="archived")
    assert [row.id for row in rows] == ["b"]


def test_live_totals_stop_at_freshness_boundary_and_exclude_children() -> None:
    active = session(
        "a",
        turns={
            "t": Turn(
                id="t",
                cwd="/work",
                start=NOW - timedelta(seconds=60),
                coverage=[Span(start=NOW - timedelta(seconds=60), end=NOW)],
            )
        },
    )
    child = session("child", is_child=True, turns=active.turns)
    ledger = Ledger(sessions={"a": active, "child": child})
    observations = {
        sid: Observation(session_id=sid, state="working", at=NOW, turn_id="t")
        for sid in ledger.sessions
    }
    fresh = build_rows(ledger, observations, cwd="/work", now=NOW + timedelta(seconds=2))
    assert next(row for row in fresh if row.id == "a").total == 62
    assert next(row for row in fresh if row.id == "child").total == 0
    stale = build_rows(ledger, observations, cwd="/work", now=NOW + timedelta(seconds=30))
    assert next(row for row in stale if row.id == "a").total == 60
    assert next(row for row in stale if row.id == "a").state == "unknown"


def test_time_sort_and_search_use_identity_title_and_directory() -> None:
    ledger = Ledger(
        sessions={
            "a": session(
                "a",
                turns={"t": Turn(id="t", cwd="/work", start=NOW - timedelta(seconds=10), end=NOW)},
            ),
            "b": session(
                "b",
                turns={"t": Turn(id="t", cwd="/work", start=NOW - timedelta(seconds=20), end=NOW)},
            ),
        }
    )
    rows = build_rows(ledger, {}, cwd="/work", now=NOW, sort="time")
    assert [row.id for row in rows] == ["b", "a"]
    assert [row.id for row in build_rows(ledger, {}, cwd="/work", now=NOW, query="TITLE A")] == [
        "a"
    ]


def test_resume_uses_stable_id_vector_recorded_cwd_and_override(tmp_path: Path) -> None:
    executable = tmp_path / "fake codex"
    result = tmp_path / "result.json"
    executable.write_text(
        "#!/usr/bin/env python3\nimport json, os, sys\n"
        f'open({str(result)!r}, "w").write(json.dumps([sys.argv[1:], os.getcwd(), '
        'os.environ["CODEX_HOME"]]))\n'
    )
    executable.chmod(0o755)
    selected = session("id;literal", cwd=str(tmp_path), title="Renamed session")
    assert launch_session(selected, tmp_path / "codex home", executable=str(executable)) is None
    assert json.loads(result.read_text()) == [
        ["resume", "id;literal"],
        str(tmp_path),
        str(tmp_path / "codex home"),
    ]
    error = launch_session(selected, tmp_path, executable="/does/not/exist")
    assert error and "install" in error.lower()
    error = launch_session(session("gone", cwd="/does/not/exist"), tmp_path)
    assert error and "directory" in error.lower()


def test_terminal_text_cannot_inject_escape_sequences() -> None:
    assert safe_text("Name\x1b[31m\n\tTail") == "Name?[31m  Tail"


def test_fresh_observation_never_fills_unknown_history_and_infers_latest_turn() -> None:
    old = Turn(id="old", cwd="/old", start=NOW - timedelta(hours=2))
    latest = Turn(
        id="latest",
        cwd="/work",
        start=NOW - timedelta(hours=1),
        coverage=[Span(start=NOW - timedelta(seconds=30), end=NOW - timedelta(seconds=20))],
    )
    ledger = Ledger(sessions={"a": session("a", turns={"old": old, "latest": latest})})
    for turn_id in (None, "latest"):
        obs = Observation(session_id="a", state="working", at=NOW, turn_id=turn_id)
        rows = build_rows(ledger, {"a": obs}, cwd="/work", now=NOW + timedelta(seconds=1))
        assert rows[0].total == 11
        assert rows[0].intervals[-1].cwd == "/work"
    assert ledger.sessions["a"].turns["latest"].end is None
    assert len(ledger.sessions["a"].turns["latest"].coverage) == 1


def test_ui_resume_and_quit_restore_terminal_even_when_tiny(tmp_path: Path) -> None:
    """Exercise curses and its subprocess boundary through a real pseudo-terminal."""
    import fcntl
    import os
    import pty
    import select
    import struct
    import subprocess
    import sys
    import termios
    import time

    result = tmp_path / "launched.json"
    executable = tmp_path / "codex"
    executable.write_text(
        "#!/usr/bin/env python3\nimport os, sys, termios, json\n"
        f'with open({str(result)!r}, "w") as f:\n'
        ' json.dump([sys.argv[1:], os.getcwd(), os.environ["CODEX_HOME"], '
        "bool(termios.tcgetattr(0)[3] & termios.ICANON)], f)\n"
    )
    executable.chmod(0o755)
    source = (
        "from codex_time.presentation import run_ui\n"
        "from codex_time.models import Ledger, Session\n"
        "from datetime import datetime, UTC\nfrom pathlib import Path\n"
        "now=datetime.now(UTC)\n"
        f's=Session(id="stable-id",title="Tiny terminal",cwd={str(tmp_path)!r},'
        "created=now,updated=now)\n"
        "ledger=Ledger(sessions={s.id:s})\n"
        f'run_ui(lambda: (ledger, {{}}), "America/Toronto", {str(tmp_path)!r}, '
        f"Path({str(tmp_path / 'home')!r}))\n"
    )
    for height, width in ((2, 12), (24, 80)):
        result.unlink(missing_ok=True)
        master, slave = pty.openpty()
        original = termios.tcgetattr(slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
        env = {
            **os.environ,
            "TERM": "xterm",
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        }
        process = subprocess.Popen(
            [sys.executable, "-c", source], stdin=slave, stdout=slave, stderr=slave, env=env
        )
        output = b""
        deadline = time.monotonic() + 10
        sent_enter = False
        sent_quit = False
        try:
            while process.poll() is None and time.monotonic() < deadline:
                readable, _, _ = select.select([master], [], [], 0.1)
                if readable:
                    output += os.read(master, 65536)
                if output and not sent_enter:
                    os.write(master, b"\n")
                    sent_enter = True
                if result.exists() and not sent_quit:
                    os.write(master, b"q")
                    sent_quit = True
            assert process.poll() == 0, output.decode(errors="replace")
            assert json.loads(result.read_text()) == [
                ["resume", "stable-id"],
                str(tmp_path),
                str(tmp_path / "home"),
                True,
            ]
            assert termios.tcgetattr(slave) == original
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)


def test_long_titles_and_paths_do_not_hide_timers(tmp_path: Path) -> None:
    import fcntl
    import os
    import pty
    import select
    import struct
    import subprocess
    import sys
    import termios
    import time

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    source = (
        "from codex_time.presentation import run_ui\n"
        "from codex_time.models import Ledger,Session\n"
        "from datetime import datetime,UTC\nfrom pathlib import Path\n"
        "now=datetime.now(UTC)\n"
        "s=Session(id='one',title='A'*200,cwd='/'+'directory'*20,created=now,updated=now)\n"
        "run_ui(lambda:(Ledger(sessions={'one':s}),{}),'America/Toronto',s.cwd,Path('/unused'))\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", source],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env={**os.environ, "TERM": "xterm"},
    )
    output = b""
    deadline = time.monotonic() + 5
    try:
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                output += os.read(master, 65536)
                if b"today 0:00:00" in output and b"total 0:00:00" in output:
                    break
        os.write(master, b"q")
        process.wait(timeout=5)
        assert process.returncode == 0
        assert b"today 0:00:00" in output and b"total 0:00:00" in output
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
        os.close(slave)
