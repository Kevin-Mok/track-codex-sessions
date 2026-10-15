"""Actual CLI process and Unix socket exercise the packaged smoke contract."""

import asyncio
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "service-smoke.py"


@pytest.mark.parametrize("interval", ["-0.1", "nan", "inf"])
def test_rollout_event_interval_rejects_invalid_values(tmp_path: Path, interval: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--executable",
            str(Path(sys.executable).parent / "codex-time"),
            "--work-dir",
            str(tmp_path),
            "--rollout-event-seconds",
            interval,
            "--plain",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "rollout event interval" in result.stderr.lower()
    assert not (tmp_path / "data").exists()


async def test_rollout_event_producer_cancellation_leaves_complete_records(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("service_smoke_rollout_producer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.make_fixture(tmp_path)
    roots = list(module.selected_sessions(tmp_path / "data"))
    producer = module.RolloutEvents(tmp_path / "home", roots, 0.01)
    task = asyncio.create_task(producer.run())
    await asyncio.sleep(0.075)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    before = {p.name: p.stat().st_size for p in (tmp_path / "home/sessions").glob("*.jsonl")}
    await asyncio.sleep(0.025)
    after = {p.name: p.stat().st_size for p in (tmp_path / "home/sessions").glob("*.jsonl")}
    assert after == before
    counts = []
    written_bytes = 0
    for path in sorted((tmp_path / "home/sessions").glob("*.jsonl")):
        count = 0
        for line in path.read_bytes().splitlines(keepends=True):
            assert line.endswith(b"\n")
            record = json.loads(line)
            if record.get("payload", {}).get("role") == "assistant":
                assert record["type"] == "response_item"
                assert record["payload"]["type"] == "message"
                assert len(record["payload"]["content"][0]["text"].encode()) == 4096
                written_bytes += len(line)
                count += 1
        counts.append(count)
    report = producer.report()
    assert sum(counts) == report["events_written"] >= 5
    assert max(counts) - min(counts) <= 1
    assert report["bytes_written"] == written_bytes
    assert report["roots"] == 5
    assert report["payload_bytes"] == 4096


@pytest.mark.parametrize("output_mode", ["json", "plain", "default"])
def test_actual_rollout_event_workload_stops_before_idle(tmp_path: Path, output_mode: str) -> None:
    interval = 0.02
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--executable",
            str(Path(sys.executable).parent / "codex-time"),
            "--work-dir",
            str(tmp_path),
            "--duration",
            "0.2",
            "--idle-seconds",
            "0.1",
            "--rollout-event-seconds",
            str(interval),
            "--sample-seconds",
            "1",
            "--allow-source",
            "--metadata-fixture",
            *(["--plain"] if output_mode != "default" else []),
            *(["--json"] if output_mode == "json" else []),
        ],
        capture_output=True,
        text=True,
        timeout=25,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(
        result.stdout if output_mode == "json" else (tmp_path / "report.json").read_text()
    )
    workload = report["rollout_events"]
    assert workload["enabled"] is True
    assert workload["interval_seconds"] == interval
    assert workload["roots"] == 5
    assert workload["payload_bytes"] == 4096
    assert (
        5
        <= workload["events_written"]
        <= math.ceil(report["active"]["wall_seconds"] / interval) + 1
    )
    assert workload["bytes_written"] > workload["events_written"] * 4096
    assert workload["tail_sources_consumed"] == 5
    assert report["active_tail_drain"]["wall_seconds"] >= 0
    assert report["idle"]["wall_seconds"] >= 0.1
    assert report["daemon_exit_status"] == 0
    assert report["evidence"]["lifecycle_preserved"] is True
    assert report["evidence"]["precise_wait_seconds"] == 2.125
    assert report["evidence"]["token_journals_unchanged"] is True
    assert report["cycles"] == {
        "waiting_observed": True,
        "unknown_observed": True,
        "reconnected": True,
    }
    if output_mode != "default":
        assert result.stderr.isascii()
    else:
        assert "✅ Packaged service smoke completed" in result.stdout
    if output_mode != "json":
        drain = report["active_tail_drain"]
        assert f"Post-active drain: {drain['wall_seconds']:.3f}s wall" in result.stdout
        assert f"Daemon CPU: {drain['cpu_seconds_by_process']['daemon']:.3f}s" in result.stdout
        io = drain["daemon_logical_io_delta"]
        assert f"Logical I/O: read {io['rchar']} B, write {io['wchar']} B" in result.stdout
    assert all("x" * 256 not in p.read_text() for p in (tmp_path / "data/sessions").glob("*.json"))


@pytest.mark.parametrize(
    ("ending", "returncode", "signal_name"),
    [
        ("raise SystemExit(7)", 7, "none"),
        ("import os,signal;os.kill(os.getpid(),signal.SIGTERM)", -15, "SIGTERM"),
    ],
)
async def test_window_reports_unexpected_daemon_exit_instead_of_missing_proc(
    tmp_path: Path, ending: str, returncode: int, signal_name: str
) -> None:
    spec = importlib.util.spec_from_file_location("service_smoke_exit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    smoke = module.Smoke(SimpleNamespace(work_dir=tmp_path, plain=True))
    smoke.daemon = await asyncio.create_subprocess_exec(
        sys.executable, "-c", "import time;time.sleep(.05);" + ending
    )
    try:
        with pytest.raises(RuntimeError) as error:
            await smoke.window(0.2, "Unexpected exit fixture")
        message = str(error.value)
        assert f"returncode={returncode}" in message
        assert f"signal={signal_name}" in message
        assert str(tmp_path / "daemon.log") in message
        assert smoke.daemon.returncode == returncode
    finally:
        if smoke.daemon.returncode is None:
            smoke.daemon.terminate()
        await smoke.daemon.wait()


def test_resource_cpu_includes_reaped_startup_workers() -> None:
    spec = importlib.util.spec_from_file_location("service_smoke_resources", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = module.resources(os.getpid())
    subprocess.run([sys.executable, "-c", "sum(i*i for i in range(2000000))"], check=True)
    after = module.resources(os.getpid())
    assert after["children_cpu_seconds"] > before["children_cpu_seconds"]
    assert after["cpu_seconds"] == after["self_cpu_seconds"] + after["children_cpu_seconds"]


async def test_startup_monitor_captures_child_peak_and_counts_reaped_cpu_once() -> None:
    spec = importlib.util.spec_from_file_location("service_smoke_startup", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    child = "import time;buf=bytearray(8*1024*1024);sum(i*i for i in range(1500000));time.sleep(.3)"
    parent = (
        "import subprocess,sys,time;"
        f"subprocess.run([sys.executable,'-c',{child!r}],check=True);"
        "print('reaped',flush=True);time.sleep(5)"
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-c", parent, stdout=asyncio.subprocess.PIPE
    )
    done = asyncio.Event()
    monitor = asyncio.create_task(module.startup_workers(process.pid, done, interval=0.02))
    try:
        assert await asyncio.wait_for(process.stdout.readline(), 3) == b"reaped\n"
        done.set()
        result = await monitor
        measured = module.resources(process.pid)
        assert result["sample_count"] >= 2
        assert result["max_simultaneous_workers"] == 2
        assert result["observed_processes"] == 2
        assert result["peak_sampled_aggregate_rss_mib"] > measured["rss_mib"]
        assert measured["children_cpu_seconds"] > 0
        assert abs(result["cumulative_cpu_seconds"] - measured["cpu_seconds"]) < 0.03
        assert result["truncated"] is False
    finally:
        done.set()
        await monitor
        process.terminate()
        await process.wait()


def test_actual_executable_socket_reconnect_and_precise_evidence(tmp_path: Path) -> None:
    executable = Path(sys.executable).parent / "codex-time"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--executable",
            str(executable),
            "--work-dir",
            str(tmp_path),
            "--duration",
            "0.05",
            "--sample-seconds",
            "1",
            "--allow-source",
            "--metadata-fixture",
            "--plain",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    report = json.loads(result.stdout)
    assert result.stderr.isascii()
    assert report["daemon_exit_status"] == 0
    assert report["rollout_events"]["enabled"] is False
    assert report["rollout_events"]["events_written"] == 0
    assert report["observed_roots"] == 5
    assert report["metadata_fixture"] == {"threads": 5, "turns": 10, "names": 5}
    assert report["cycles"]["waiting_observed"] is True
    assert report["cycles"]["unknown_observed"] is True
    assert report["cycles"]["reconnected"] is True
    assert report["evidence"]["precise_wait_seconds"] == 2.125
    assert report["evidence"]["lifecycle_preserved"] is True
    assert report["evidence"]["token_journals_unchanged"] is True
    assert report["health_at_65_seconds"]["daemon"] == "running"
    assert report["active"]["aggregate"]["rss_mib"] > 0
    assert report["active"]["aggregate"]["cpu_percent_one_core"] >= 0
    startup = report["startup"]["workers"]
    assert startup["sample_count"] >= 1
    assert startup["max_simultaneous_workers"] >= 1
    assert startup["peak_sampled_aggregate_rss_mib"] > 0
    assert startup["observed_process_hwm_sum_mib"] > 0
    assert "non-simultaneous" in startup["hwm_scope"]
    assert startup["cumulative_cpu_seconds"] >= report["startup"]["daemon"]["cpu_seconds"]
    assert set(report["rpc_counts"]) == {
        "initialize",
        "initialized",
        "thread/loaded/list",
        "thread/read",
    }
    assert "five-minute" in " ".join(report["unvalidated_or_misses"])
    assert "minute cadence" in " ".join(report["unvalidated_or_misses"])


def test_unsafe_existing_work_directory_is_not_overwritten(tmp_path: Path) -> None:
    marker = tmp_path / "data"
    marker.mkdir()
    (marker / "preserve.txt").write_text("existing work")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--executable",
            str(Path(sys.executable).parent / "codex-time"),
            "--work-dir",
            str(tmp_path),
            "--duration",
            "0",
            "--sample-seconds",
            "1",
            "--allow-source",
            "--plain",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert (marker / "preserve.txt").read_text() == "existing work"
    assert "fresh" in result.stderr.lower()


def test_skipped_reconnect_is_reported_without_claiming_it_ran(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), "--executable",
            str(Path(sys.executable).parent / "codex-time"),
            "--work-dir", str(tmp_path), "--duration", "0",
            "--sample-seconds", "1", "--skip-cycles", "--allow-source", "--plain", "--json",
        ],
        capture_output=True, text=True, timeout=20, check=True,
    )
    report = json.loads(result.stdout)
    assert not any(report["cycles"].values())
    assert "Reconnect cycles skipped (--skip-cycles)." in report["notes"]
    assert "actual Unix reconnect are exercised" not in " ".join(report["notes"])
