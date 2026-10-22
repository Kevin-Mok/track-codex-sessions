"""Human CLI summaries stay useful while JSON keeps the full evidence."""

import json
import os
import shutil
import sys
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest

from codex_time import cli
from codex_time.models import Ledger, Session, Turn
from codex_time.presentation import SessionRow


@pytest.fixture
def cli_data(monkeypatch: pytest.MonkeyPatch) -> Ledger:
    at = datetime(2026, 10, 21, 16, tzinfo=UTC)
    ledger = Ledger(
        sessions={
            "thread-full-id": Session(
                id="thread-full-id",
                cwd="/work/project",
                title="Fix login",
                created=at,
                updated=at,
                turns={
                    "one": Turn(
                        id="one",
                        cwd="/work/project",
                        start=at,
                        end=at.replace(minute=1),
                        quality=["historical_upper_bound"],
                    )
                },
            ),
        },
        diagnostics=["raw diagnostic one", "raw diagnostic two"],
    )

    class FakeStore:
        runtime = Path("/tmp/runtime")

        def __init__(self, *args: object) -> None:
            pass

        def load_timing(self) -> Ledger:
            return ledger

        def summary(self) -> dict[str, object]:
            return {"sessions": len(ledger.sessions), "diagnostics": ledger.diagnostics}

    monkeypatch.setattr(cli, "Store", FakeStore)
    monkeypatch.setattr(cli, "observations", lambda store: {})
    monkeypatch.setattr(
        cli,
        "runtime_status",
        lambda store: {
            "daemon": "stopped_or_stale",
            "heartbeat": None,
            "pid": None,
            "live_diagnostic": "ConnectionClosedError",
            "data_dir": "/tmp/data",
            "state_dir": "/tmp/runtime",
            "sampling_interval_seconds": 60,
            "notification_mode": None,
        },
    )
    monkeypatch.setattr(shutil, "get_terminal_size", lambda *args: os.terminal_size((40, 24)))
    return ledger


def invoke(monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["codex-time", *args])
    return cli.main()


@pytest.mark.parametrize(
    ("stdout_tty", "json_output", "expected"),
    [(False, False, False), (True, False, True), (True, True, False)],
)
def test_transient_progress_requires_human_terminal_stdout(
    cli_data,
    monkeypatch,
    capsys,
    stdout_tty,
    json_output,
    expected,
):
    modes = []

    @contextmanager
    def progress(label, *, interactive):
        modes.append(interactive)
        yield

    monkeypatch.setattr(cli.Store, "load", lambda self: cli_data, raising=False)
    monkeypatch.setattr(cli, "report_progress", progress)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: stdout_tty)
    args = ["projects", "--date", "2026-10-21"] + (["--json"] if json_output else [])
    assert invoke(monkeypatch, *args) == 0
    capsys.readouterr()
    assert modes == [expected]


def test_sessions_are_readable_sanitized_and_keep_every_row(
    cli_data: Ledger,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = [
        SessionRow(
            f"thread-full-id-{index}",
            f"Fix login {index}\x1b[31m",
            "/work/project",
            "idle",
            False,
            60,
            3600,
            "historical_upper_bound,observation_gap",
            [],
            "gpt-6-luna",
            "low",
        )
        for index in range(22)
    ]
    monkeypatch.setattr(cli, "build_rows", lambda *args, **kwargs: rows)
    assert invoke(monkeypatch, "sessions", "--all-dirs") == 0
    output = capsys.readouterr().out
    assert "💬" in output and "22 sessions" in output
    assert all(f"Fix login {index}" in output for index in range(22))
    assert "thread-full-id" not in output and "historical_upper_bound" not in output
    assert "\x1b" not in output
    assert max(map(len, output.splitlines())) <= 40
    assert invoke(monkeypatch, "sessions", "--details", "--plain") == 0
    detailed = capsys.readouterr().out
    assert "thread-full-id-21" in detailed and detailed.isascii()


def test_sessions_empty_state_explains_scope(
    cli_data: Ledger,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "build_rows", lambda *args, **kwargs: [])
    assert invoke(monkeypatch, "sessions", "--cwd", "/missing") == 0
    output = capsys.readouterr().out
    assert "No sessions" in output and "--all-dirs" in output


def test_matching_directory_basenames_are_disambiguated(
    cli_data: Ledger,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = ["/work/project", "/other/project"]
    rows = [
        SessionRow(
            f"session-{index}",
            f"Thread {index}",
            path,
            "idle",
            False,
            60,
            60,
            "observed",
            [],
            None,
            None,
        )
        for index, path in enumerate(paths)
    ]
    monkeypatch.setattr(cli, "build_rows", lambda *args, **kwargs: rows)
    assert invoke(monkeypatch, "sessions", "--all-dirs") == 0
    output = capsys.readouterr().out
    assert all(path in output for path in paths)
    session = cli_data.sessions["thread-full-id"]
    turn = session.turns["one"].model_copy(update={"cwd": paths[1]})
    cli_data.sessions["other-id"] = session.model_copy(
        update={
            "id": "other-id",
            "cwd": paths[1],
            "turns": {"one": turn},
        }
    )
    assert invoke(monkeypatch, "history", "--all-dirs") == 0
    output = capsys.readouterr().out
    assert all(path in output for path in paths)
    from codex_time import session_status

    monkeypatch.setattr(
        session_status,
        "session_status",
        lambda *args: {
            "fresh": True,
            "sessions": [
                {
                    "session_id": row.id,
                    "cwd": row.cwd,
                    "status": "idle",
                }
                for row in rows
            ],
        },
    )
    assert invoke(monkeypatch, "status") == 0
    output = capsys.readouterr().out
    assert all(path in output for path in paths)


def test_history_is_a_daily_summary_with_session_titles_and_optional_ids(
    cli_data: Ledger,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert invoke(monkeypatch, "history", "--all-dirs") == 0
    output = capsys.readouterr().out
    assert "🕒" in output and "Oct 21" in output and "Fix login" in output
    assert "project" in output and "1m" in output
    assert "thread-full-id" not in output
    assert "historical_upper_bound" not in output and '"days"' not in output
    assert "raw diagnostic" not in output and "--json" in output
    assert max(map(len, output.splitlines())) <= 40
    assert invoke(monkeypatch, "report", "--all-dirs", "--details", "--plain") == 0
    detailed = capsys.readouterr().out
    assert "thread-full-id" in detailed and detailed.isascii()
    assert invoke(monkeypatch, "history", "--all-dirs", "--json") == 0
    machine = json.loads(capsys.readouterr().out)
    assert machine["sessions"] == {"thread-full-id": 60}
    assert machine["diagnostics"] == cli_data.diagnostics


def test_history_omits_zero_activity_sessions_until_details(
    cli_data: Ledger,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    active = cli_data.sessions["thread-full-id"]
    for index in range(37):
        sid = f"inactive-thread-{index}"
        cli_data.sessions[sid] = active.model_copy(
            update={"id": sid, "title": f"Inactive thread {index}", "turns": {}},
        )
    assert invoke(monkeypatch, "history", "--all-dirs") == 0
    output = " ".join(capsys.readouterr().out.split())
    assert "Inactive thread" not in output and "Fix login" in output
    assert "1 day" in output and "1 days" not in output
    assert "1 session with recorded work" in output and "38 selected" in output
    assert "37 sessions with no recorded work omitted" in output and "--details" in output
    assert invoke(monkeypatch, "history", "--all-dirs", "--details") == 0
    detailed = capsys.readouterr().out
    assert all(f"Inactive thread {index}" in detailed for index in range(37))
    assert "omitted" not in detailed
    assert invoke(monkeypatch, "history", "--all-dirs", "--json") == 0
    machine = json.loads(capsys.readouterr().out)
    assert len(machine["sessions"]) == 38
    assert machine["sessions"]["inactive-thread-36"] == 0
    assert machine["sessions"]["thread-full-id"] == 60


def test_single_session_heading_uses_singular(
    cli_data: Ledger,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert invoke(monkeypatch, "sessions", "--all-dirs") == 0
    heading = capsys.readouterr().out.splitlines()[0]
    assert "1 session" in heading and "1 sessions" not in heading


def test_history_duration_keeps_subseconds_and_matches_projects() -> None:
    from codex_time.model_output import _working_duration
    from codex_time.reporting import Report
    from codex_time.session_output import history_text

    for microseconds in (250_000, 3_086_550_000):
        seconds = microseconds / 1_000_000
        data = Report(
            timezone="America/Toronto",
            total_seconds=seconds,
            total_microseconds=microseconds,
            days={"2026-10-21": seconds},
            directories={"/work": seconds},
            sessions={"thread": seconds},
            quality=[],
            diagnostics=[],
        )
        output = history_text(data, Ledger(), plain=True)
        assert output.splitlines()[1].startswith(_working_duration(microseconds) + " |")
        assert "0.25s" in output if microseconds == 250_000 else "51m 26s" in output


def test_health_summarizes_diagnostics_instead_of_dumping_them(
    cli_data: Ledger,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert invoke(monkeypatch, "health") == 0
    output = capsys.readouterr().out
    assert "🩺" in output and "stopped_or_stale" not in output
    assert "raw diagnostic" not in output and "ConnectionClosedError" not in output
    assert "--json" in output and max(map(len, output.splitlines())) <= 40
    assert invoke(monkeypatch, "health", "--details", "--plain") == 0
    detailed = capsys.readouterr().out
    assert "/tmp/runtime" in detailed and detailed.isascii()


def test_status_names_omitted_count_and_keeps_full_json(
    cli_data: Ledger,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from codex_time import session_status

    entries = [
        {
            "session_id": f"full-thread-{index}",
            "status": "idle",
            "tty": None,
            "cwd": "/work/a-very-long-project-directory",
            "last_updated": str(index),
        }
        for index in range(23)
    ]
    monkeypatch.setattr(
        session_status,
        "session_status",
        lambda *args: {
            "fresh": True,
            "sessions": entries,
            "cache_path": "/tmp/runtime/session-status.json",
        },
    )
    assert invoke(monkeypatch, "status") == 0
    output = capsys.readouterr().out
    assert "3 more" in output and "--json" in output
    assert max(map(len, output.splitlines())) <= 40
    assert invoke(monkeypatch, "status", "--json") == 0
    assert json.loads(capsys.readouterr().out)["sessions"] == entries


def test_import_history_has_decorated_summary_and_ascii_option(
    cli_data: Ledger,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_import(
        store: object,
        home: Path,
        *,
        progress: Callable[[str], None],
    ) -> Ledger:
        progress("Reading history: 1 file")
        return cli_data

    monkeypatch.setattr(cli, "import_history", fake_import)
    assert invoke(monkeypatch, "import-history") == 0
    captured = capsys.readouterr()
    assert "✅" in captured.out and "1 session" in captured.out
    assert "raw diagnostic" not in captured.err and "2 import notices" in captured.err
    assert "health --json" in captured.err
    assert "⏳ Reading history" in captured.err
    assert invoke(monkeypatch, "import-history", "--plain") == 0
    captured = capsys.readouterr()
    assert (captured.out + captured.err).isascii()
