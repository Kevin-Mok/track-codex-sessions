"""Exercise installed native readers only against a fully isolated fixture store."""

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from codex_time.models import Ledger, Session, Turn
from codex_time.storage import Store


def test_native_timetrace_list_and_report(tmp_path: Path) -> None:
    executable = shutil.which("timetrace")
    if executable is None:
        pytest.skip("native timetrace reader is not installed")
    if Path("/etc/timetrace/config.yml").exists() or Path("/etc/timetrace/config.yaml").exists():
        pytest.skip("system-wide config could override isolation; refuse to access native store")
    native_home = tmp_path / "native-home"
    config = native_home / ".timetrace"
    config.mkdir(parents=True)
    store = Store(tmp_path / "data", tmp_path / "state")
    start = datetime(2026, 10, 6, 16, tzinfo=UTC)
    ledger = Ledger(
        sessions={
            "one": Session(
                id="one",
                cwd="/fixture",
                created=start,
                updated=start,
                turns={
                    "a": Turn(
                        id="a", cwd="/fixture", start=start, end=start + timedelta(seconds=10)
                    ),
                    "b": Turn(
                        id="b",
                        cwd="/fixture",
                        start=start + timedelta(seconds=20),
                        end=start + timedelta(seconds=40),
                    ),
                },
            )
        }
    )
    with store.writer():
        store.save(ledger)
    (config / "config.yml").write_text("store: " + str(store.root) + "\n")
    env = dict(os.environ, HOME=str(native_home), TZ="America/Toronto")
    before = {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob("*.json")}
    listed = subprocess.run(
        [executable, "list", "records", "2026-10-06"],
        cwd=native_home,
        env=env,
        capture_output=True,
        text=True,
    )
    assert listed.returncode == 0, listed.stderr
    project = next((store.root / "projects").glob("*.json")).stem
    assert project in listed.stdout
    assert "session:one, turn:a" in listed.stdout
    assert "session:one, turn:b" in listed.stdout
    output = tmp_path / "native-report.json"
    reported = subprocess.run(
        [
            executable,
            "report",
            "--start",
            "2026-10-06",
            "--end",
            "2026-10-06",
            "--output",
            "json",
            "--file",
            str(output),
        ],
        cwd=native_home,
        env=env,
        capture_output=True,
        text=True,
    )
    assert reported.returncode == 0, reported.stderr
    value = json.loads(output.read_text())
    assert set(value) == {project}
    assert value[project]["total"] == 30_000_000_000  # Go time.Duration nanoseconds.
    assert len(value[project]["records"]) == 2
    assert before == {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob("*.json")}
