"""Slow report status stays off stdout and stops when the report finishes."""

from threading import Event


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
