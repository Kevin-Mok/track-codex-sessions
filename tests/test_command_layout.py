"""Canonical commands stay discoverable while old invocations remain equivalent."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from test_overview import sample_ledger

from codex_time import cli
from codex_time.storage import Store


def run(data: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from codex_time.cli import main; raise SystemExit(main())",
            "--data-dir",
            str(data),
            "--state-dir",
            str(data.parent / "state"),
            *args,
        ],
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONPATH=str(Path("src").resolve())),
    )


def test_top_level_help_advertises_canonical_commands_only() -> None:
    text = cli.parser().format_help()
    for name in [
        "overview",
        "allowance",
        "model-time",
        "projects",
        "sessions",
        "history",
        "health",
        "resume",
    ]:
        assert name in text
    advertised = re.findall(r"^    (\S+)\s", text, re.MULTILINE)
    for name in ["burn", "models", "day", "list", "report", "status"]:
        assert name not in advertised
    assert "daemon" in text and "import-history" in text


@pytest.mark.parametrize(
    "old,new,arguments",
    [
        ("burn", "allowance", ["day", "--date", "2026-10-06", "--json"]),
        ("burn", "allowance", ["week", "--date", "2026-10-06", "--csv"]),
        ("burn", "allowance", ["month", "--date", "2026-10-06", "--plain", "--details"]),
        ("models", "model-time", ["day", "--date", "2026-10-06", "--json"]),
        ("models", "model-time", ["week", "--date", "2026-10-06", "--csv", "--model-only"]),
        ("models", "model-time", ["month", "--date", "2026-10-06", "--plain", "--cwd", "/one"]),
        ("day", "projects", ["--date", "2026-10-06", "--json"]),
        ("day", "projects", ["--date", "2026-10-06", "--plain", "--details"]),
        (
            "list",
            "sessions",
            ["--all-dirs", "--archive", "all", "--search", "root", "--sort", "time", "--json"],
        ),
        (
            "report",
            "history",
            [
                "--all-dirs",
                "--archive",
                "all",
                "--from",
                "2026-10-06",
                "--to",
                "2026-10-06",
                "--json",
            ],
        ),
        ("report", "history", ["--from", "2026-10-07", "--to", "2026-10-06"]),
        ("status", "health", ["--json"]),
    ],
)
def test_aliases_keep_output_exports_and_exit_codes(
    tmp_path: Path, old: str, new: str, arguments: list[str]
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "ledger.json").write_text(sample_ledger().model_dump_json())
    before = {p: p.read_bytes() for p in data.rglob("*") if p.is_file()}
    legacy, canonical = run(data, old, *arguments), run(data, new, *arguments)
    assert (canonical.returncode, canonical.stdout, canonical.stderr) == (
        legacy.returncode,
        legacy.stdout,
        legacy.stderr,
    )
    assert canonical.returncode == (2 if "2026-10-07" in arguments else 0)
    assert before == {p: p.read_bytes() for p in data.rglob("*") if p.is_file()}


def test_overview_clean_json_and_read_only_snapshot(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "ledger.json").write_text(sample_ledger().model_dump_json())
    before = {p: p.read_bytes() for p in data.rglob("*") if p.is_file()}
    result = run(data, "overview", "--date", "2026-10-06", "--json", "--color", "always")
    assert result.returncode == 0, result.stderr
    parsed = json.loads(result.stdout)
    assert parsed["model_totals"]["total_seconds"] == 1320
    assert parsed["allowance"]["rows"][0]["working_microseconds"] == 1140_000_000
    assert result.stderr == "" and "\x1b" not in result.stdout
    assert before == {p: p.read_bytes() for p in data.rglob("*") if p.is_file()}


def test_overview_loads_ledger_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "ledger.json").write_text(sample_ledger().model_dump_json())
    original = Store.load
    loads = []

    def load(self):
        loads.append(self.root)
        return original(self)

    monkeypatch.setattr(Store, "load", load)
    monkeypatch.setattr(
        sys,
        "argv",
        ["codex-time", "--data-dir", str(data), "overview", "--date", "2026-10-06", "--json"],
    )
    assert cli.main() == 0
    assert len(loads) == 1
    assert json.loads(capsys.readouterr().out)["reasoning"]["total_seconds"] == 1320


@pytest.mark.parametrize("arguments", [[], ["resume"]])
def test_resume_and_no_arguments_open_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    calls = []
    monkeypatch.setattr(cli, "run_ui", lambda *args: calls.append(args))
    monkeypatch.setattr(
        sys, "argv", ["codex-time", "--data-dir", str(tmp_path / "data"), *arguments]
    )
    assert cli.main() == 0 and len(calls) == 1


def test_overview_defaults_and_window_options() -> None:
    args = cli.parser().parse_args(["overview", "--date", "2026-10-06"])
    assert args.period == "day" and args.window_minutes == 10080
    args = cli.parser().parse_args(
        [
            "overview",
            "week",
            "--window-minutes",
            "300",
            "--limit-id",
            "other",
            "--max-gap-seconds",
            "120",
            "--plain",
        ]
    )
    assert args.period == "week" and args.window_minutes == 300
    assert args.limit_id == "other" and args.max_gap_seconds == 120 and args.plain
    with pytest.raises(SystemExit):
        cli.parser().parse_args(["overview", "--cwd", "/one"])


def test_piped_and_no_color_overview_output(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "ledger.json").write_text(sample_ledger().model_dump_json())
    result = run(data, "overview", "--date", "2026-10-06")
    assert result.returncode == 0 and "\x1b" not in result.stdout
    assert "Model work" in result.stdout and "--details" in result.stdout


@pytest.mark.parametrize("command", ["projects", "model-time", "allowance"])
def test_empty_report_guidance_uses_advertised_health_command(tmp_path: Path, command: str) -> None:
    arguments = [command]
    if command in {"model-time", "allowance"}:
        arguments.append("day")
    result = run(tmp_path / "data", *arguments, "--plain")
    assert result.returncode == 0
    assert "codex-time health" in result.stdout and "codex-time status" not in result.stdout


def test_noninteractive_picker_guidance_uses_sessions_command(tmp_path: Path) -> None:
    result = run(tmp_path / "data", "resume")
    assert result.returncode == 2
    assert "codex-time sessions" in result.stderr and "codex-time list" not in result.stderr
