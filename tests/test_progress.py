"""Slow report status stays off stdout and stops when the report finishes."""

from threading import Event

import pytest


@pytest.mark.parametrize("command", ["overview", "projects"])
@pytest.mark.parametrize("plain", [False, True])
def test_report_loading_emoji_respects_plain(command, plain, tmp_path, monkeypatch, capsys):
    from contextlib import contextmanager

    from codex_time import cli
    from codex_time.progress import report_progress

    @contextmanager
    def slow_progress(label):
        with report_progress(label, interval=0.01):
            Event().wait(0.04)
            yield

    monkeypatch.setattr(cli, "report_progress", slow_progress)
    monkeypatch.setattr("sys.argv", [
        "codex-time", "--data-dir", str(tmp_path / "data"),
        "--state-dir", str(tmp_path / "state"), command, "--json",
        *(["--plain"] if plain else []),
    ])
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
