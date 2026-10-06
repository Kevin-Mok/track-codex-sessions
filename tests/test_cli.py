import json
import os
import subprocess
from pathlib import Path


def event(ts: str, kind: str, payload: dict[str, object]) -> str:
    return json.dumps({"timestamp": ts, "type": kind, "payload": payload}) + "\n"


def test_history_entrypoint_and_idempotence(tmp_path: Path) -> None:
    home = tmp_path / "codex"
    rollout = home / "sessions" / "fixture.jsonl"
    rollout.parent.mkdir(parents=True)
    rollout.write_text(
        event(
            "2026-10-06T16:00:00Z",
            "session_meta",
            {"id": "fixture", "cwd": "/work", "timestamp": "2026-10-06T16:00:00Z", "source": "cli"},
        )
        + event("2026-10-06T16:00:00Z", "event_msg", {"type": "task_started", "turn_id": "one"})
        + event("2026-10-06T16:01:00Z", "event_msg", {"type": "task_complete", "turn_id": "one"})
    )
    base = [
        "uv",
        "run",
        "codex-time",
        "--codex-home",
        str(home),
        "--data-dir",
        str(tmp_path / "data"),
        "--state-dir",
        str(tmp_path / "state"),
    ]
    env = dict(os.environ, PYTHONPATH="src")
    first = subprocess.run([*base, "import-history"], env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    before = {
        p.relative_to(tmp_path / "data"): p.read_text() for p in (tmp_path / "data").rglob("*.json")
    }
    second = subprocess.run([*base, "import-history"], env=env, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    assert before == {
        p.relative_to(tmp_path / "data"): p.read_text() for p in (tmp_path / "data").rglob("*.json")
    }
    report = subprocess.run(
        [*base, "report", "--all-dirs", "--json"], env=env, capture_output=True, text=True
    )
    assert report.returncode == 0, report.stderr
    data = json.loads(report.stdout)
    assert data["total_seconds"] == 60
    assert data["days"] == {"2026-10-06": 60}
    assert "historical_upper_bound" in data["quality"]


def test_status_empty_and_bad_timezone(tmp_path: Path) -> None:
    base = [
        "uv",
        "run",
        "codex-time",
        "--data-dir",
        str(tmp_path / "data"),
        "--state-dir",
        str(tmp_path / "state"),
    ]
    env = dict(os.environ, PYTHONPATH="src")
    status = subprocess.run([*base, "status", "--json"], env=env, capture_output=True, text=True)
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["daemon"] == "stopped_or_stale"
    invalid = subprocess.run(
        [*base, "--timezone", "Invalid/Zone", "report"], env=env, capture_output=True, text=True
    )
    assert invalid.returncode == 2
    assert "timezone" in invalid.stderr
