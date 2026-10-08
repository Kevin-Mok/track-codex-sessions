import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from codex_time.cli import main
from codex_time.models import Ledger, Session, Turn


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    start = datetime(2026, 10, 6, 13, tzinfo=UTC)
    end = datetime(2026, 10, 6, 14, tzinfo=UTC)
    s = Session(
        id="stable-session",
        title="Build day report",
        cwd="/fixture/repo",
        created=start,
        updated=end,
        archived=True,
        turns={"one": Turn(id="one", cwd="/fixture/repo", start=start, end=end)},
    )
    root = tmp_path / "data"
    root.mkdir()
    (root / "ledger.json").write_text(Ledger(sessions={s.id: s}).model_dump_json())
    return root


def run_day(monkeypatch: pytest.MonkeyPatch, data_dir: Path, *args: str) -> int:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "codex-time",
            "--data-dir",
            str(data_dir),
            "--state-dir",
            str(data_dir.parent / "state"),
            *args,
        ],
    )
    return main()


def test_day_cli_json_includes_archived_all_directories_and_is_read_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    data_dir: Path,
) -> None:
    before = {p.relative_to(data_dir): p.read_bytes() for p in data_dir.rglob("*") if p.is_file()}
    assert run_day(monkeypatch, data_dir, "day", "--date", "2026-10-06", "--json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total_seconds"] == 3600
    assert data["total_microseconds"] == 3_600_000_000
    directory = data["directories"][0]
    assert directory["cwd"] == "/fixture/repo"
    assert directory["sessions"][0]["id"] == "stable-session"
    assert before == {
        p.relative_to(data_dir): p.read_bytes() for p in data_dir.rglob("*") if p.is_file()
    }
    assert not (data_dir.parent / "state").exists()


@pytest.mark.parametrize(
    "filter_args",
    [
        ["--cwd", "/elsewhere"],
        ["--archive", "active"],
        ["--session", "missing"],
    ],
)
def test_day_cli_filters(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    data_dir: Path,
    filter_args: list[str],
) -> None:
    assert (
        run_day(monkeypatch, data_dir, "day", "--date", "2026-10-06", "--json", *filter_args) == 0
    )
    assert json.loads(capsys.readouterr().out)["directories"] == []


def test_day_cli_human_plain_and_details(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    data_dir: Path,
) -> None:
    assert run_day(monkeypatch, data_dir, "day", "--date", "2026-10-06", "--plain") == 0
    output = capsys.readouterr().out
    assert "Oct 6, 2026" in output
    assert "1h" in output
    assert "Build day report" in output
    assert "/fixture/repo" in output
    assert "historical_upper_bound" not in output
    assert output.isascii() and "\x1b" not in output
    assert (
        run_day(monkeypatch, data_dir, "day", "--date", "2026-10-06", "--details", "--plain") == 0
    )
    assert "historical_upper_bound" in capsys.readouterr().out


def test_day_cli_timezone_today_and_invalid_date(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    data_dir: Path,
) -> None:
    assert run_day(monkeypatch, data_dir, "--timezone", "UTC", "day", "--json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["timezone"] == "UTC"
    assert data["date"] == datetime.now(UTC).date().isoformat()
    with pytest.raises(SystemExit) as error:
        run_day(monkeypatch, data_dir, "day", "--date", "bad-date")
    assert error.value.code == 2


def test_day_cli_no_color_and_old_report_json_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    data_dir: Path,
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    assert run_day(monkeypatch, data_dir, "day", "--date", "2026-10-06", "--color", "always") == 0
    assert "\x1b" not in capsys.readouterr().out
    assert (
        run_day(
            monkeypatch,
            data_dir,
            "report",
            "--all-dirs",
            "--archive",
            "all",
            "--from",
            "2026-10-06",
            "--to",
            "2026-10-06",
            "--json",
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["sessions"] == {"stable-session": 3600}
    assert data["directories"] == {"/fixture/repo": 3600}
    assert data["total_microseconds"] == 3_600_000_000


@pytest.mark.parametrize(
    "filter_args",
    [
        ["--cwd", "/fixture/repo"],
        ["--session", "stable-session"],
        ["--archive", "archived"],
    ],
)
def test_day_cli_positive_filters(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    data_dir: Path,
    filter_args: list[str],
) -> None:
    assert (
        run_day(monkeypatch, data_dir, "day", "--date", "2026-10-06", "--json", *filter_args) == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["total_seconds"] == 3600
    assert data["directories"][0]["sessions"][0]["id"] == "stable-session"
