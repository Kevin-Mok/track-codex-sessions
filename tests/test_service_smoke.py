"""Actual CLI process and Unix socket exercise the packaged smoke contract."""

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "service-smoke.py"


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
