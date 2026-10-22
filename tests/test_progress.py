"""Slow report status stays off stdout and stops when the report finishes."""

from io import StringIO
from os import terminal_size
from threading import Event

import pytest


@pytest.mark.parametrize("command", ["overview", "projects"])
@pytest.mark.parametrize("plain", [False, True])
def test_report_loading_emoji_respects_plain(command, plain, tmp_path, monkeypatch, capsys):
    from contextlib import contextmanager

    from codex_time import cli
    from codex_time.progress import report_progress

    @contextmanager
    def slow_progress(label, **kwargs):
        with report_progress(label, interval=0.01, **kwargs):
            Event().wait(0.04)
            yield

    monkeypatch.setattr(cli, "report_progress", slow_progress)
    monkeypatch.setattr(
        "sys.argv",
        [
            "codex-time",
            "--data-dir",
            str(tmp_path / "data"),
            "--state-dir",
            str(tmp_path / "state"),
            command,
            "--json",
            *(["--plain"] if plain else []),
        ],
    )
    assert cli.main() == 0
    captured = capsys.readouterr()
    prefix = "" if plain else "⏳ "
    assert captured.err.startswith(f"{prefix}Reading {command} report:")
    assert "elapsed" in captured.err
    assert "⏳" not in captured.out
    if plain:
        assert captured.err.isascii()


def test_slow_report_emits_periodic_stderr_and_stops(capsys):
    from codex_time.progress import report_progress

    with report_progress("Reading token report", interval=0.01):
        Event().wait(0.055)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("Reading token report") >= 2
    assert "elapsed" in captured.err
    Event().wait(0.025)
    assert capsys.readouterr().err == ""


def test_fast_report_keeps_piped_output_quiet(capsys):
    from codex_time.progress import report_progress

    with report_progress("Reading token report", interval=1):
        pass
    assert capsys.readouterr().err == ""


class Terminal(StringIO):
    def isatty(self):
        return True


def test_slow_terminal_report_updates_one_line_and_clears_it(monkeypatch):
    from codex_time.progress import report_progress

    terminal = Terminal()
    monkeypatch.setattr("sys.stderr", terminal)
    with report_progress("Reading token report", interval=0.01):
        Event().wait(0.055)
    rendered = terminal.getvalue()
    assert rendered.count("Reading token report") >= 2
    assert "\n" not in rendered and rendered.startswith("\r")
    assert rendered.endswith("\r") and rendered.rsplit("\r", 2)[-2].isspace()
    assert rendered.isascii()
    Event().wait(0.025)
    assert terminal.getvalue() == rendered


def test_json_progress_uses_newlines_even_with_a_terminal(monkeypatch):
    from codex_time.progress import report_progress

    terminal = Terminal()
    monkeypatch.setattr("sys.stderr", terminal)
    with report_progress("Reading token report", interval=0.01, interactive=False):
        Event().wait(0.04)
    rendered = terminal.getvalue()
    assert rendered.count("Reading token report") >= 2
    assert "\r" not in rendered and rendered.endswith("\n")


def test_terminal_status_sanitizes_labels_and_stays_within_one_line(monkeypatch):
    from rich.cells import cell_len

    from codex_time.progress import report_progress

    terminal = Terminal()
    monkeypatch.setattr("sys.stderr", terminal)
    monkeypatch.setattr("shutil.get_terminal_size", lambda fallback: terminal_size((24, 24)))
    with report_progress("Reading \x1b[2J\n模型 " * 10, interval=0.01):
        Event().wait(0.03)
    rendered = terminal.getvalue()
    assert "\x1b" not in rendered and "\n" not in rendered
    assert all(cell_len(part) <= 23 for part in rendered.split("\r"))


def test_fast_or_failed_terminal_report_leaves_no_indicator(monkeypatch):
    from codex_time.progress import report_progress

    terminal = Terminal()
    monkeypatch.setattr("sys.stderr", terminal)
    with report_progress("Reading token report", interval=1):
        pass
    assert terminal.getvalue() == ""
    with pytest.raises(ValueError, match="deliberate failure"):
        with report_progress("Reading token report", interval=0.01):
            Event().wait(0.03)
            raise ValueError("deliberate failure")
    rendered = terminal.getvalue()
    assert rendered.endswith("\r") and rendered.rsplit("\r", 2)[-2].isspace()
