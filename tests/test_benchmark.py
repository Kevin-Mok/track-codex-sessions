"""Benchmark fixtures and resource claims must describe real measured workloads."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from codex_time.storage import Store

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark.py"


def load_benchmark():
    spec = importlib.util.spec_from_file_location("codex_benchmark", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_streamed_fixture_preserves_exact_counts_and_open_root_workload(tmp_path: Path) -> None:
    benchmark = load_benchmark()
    result = benchmark.generate_fixture(tmp_path, sessions=7, turns=19, quota=13, usage=17)
    ledger = Store(tmp_path / "data", tmp_path / "state").load()
    assert len(ledger.sessions) == 7
    assert sum(len(s.turns) for s in ledger.sessions.values()) == 19
    assert len(ledger.quota_observations) == 13
    assert len(ledger.usage_observations) == 17
    assert len({u.id for u in ledger.usage_observations}) == 17
    roots = [s for s in ledger.sessions.values() if not s.is_child and not s.parent_id]
    assert sum(t.end is None for s in roots for t in s.turns.values()) == 5
    assert result["counts"] == {"sessions": 7, "turns": 19, "quota": 13, "usage": 17}
    assert result["content_free"] is True


def test_fixture_is_deterministic_without_conversation_or_auth_content(tmp_path: Path) -> None:
    benchmark = load_benchmark()
    first, second = tmp_path / "first", tmp_path / "second"
    one = benchmark.generate_fixture(first, sessions=5, turns=10, quota=2, usage=4)
    two = benchmark.generate_fixture(second, sessions=5, turns=10, quota=2, usage=4)
    assert one["sha256"] == two["sha256"]
    for path in first.rglob("*.jsonl"):
        for line in path.read_text().splitlines():
            payload = json.loads(line)
            private = {"message", "messages", "arguments", "output", "credentials", "auth"}
            assert not private.intersection(payload)


def test_resource_window_reports_actual_cpu_io_and_operation_counts() -> None:
    benchmark = load_benchmark()
    result = benchmark.measure(lambda: sum(i * i for i in range(10000)), operations=1)
    assert result["cpu_seconds"] > 0
    assert result["wall_seconds"] > 0
    assert result["rss_mib"] > 0
    assert result["peak_rss_mib"] >= result["rss_mib"]
    assert result["operations"] == 1
    assert result["logical_io"]["rchar"] >= 0


def test_fixture_only_json_is_clean_and_plain_progress_is_ascii(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--work-dir",
            str(tmp_path),
            "--fixture-only",
            "--json",
            "--plain",
            "--sessions",
            "5",
            "--turns",
            "10",
            "--quota",
            "2",
            "--usage",
            "4",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert data["fixture"]["counts"]["turns"] == 10
    assert "Fixture" in result.stderr
    assert result.stderr.isascii()
    assert data["measurements"] == []


def test_real_workers_separate_startup_and_phase_timing_with_known_imports(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--work-dir",
            str(tmp_path),
            "--baseline",
            str(SCRIPT.parents[1]),
            "--json",
            "--plain",
            "--sessions",
            "5",
            "--turns",
            "10",
            "--quota",
            "2",
            "--usage",
            "4",
            "--idle-seconds",
            "0.02",
            "--active-seconds",
            "0.02",
            "--soak-seconds",
            "0",
            "--cycles",
            "2",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert result.stderr.isascii()
    assert [(r["backend"], r["phase"]) for r in data["measurements"]] == [
        ("baseline", "cold"),
        ("baseline", "steady"),
        ("optimized", "cold"),
        ("optimized", "steady"),
    ]
    cold, steady = data["measurements"][2:]
    assert cold["fixture_sha256"] == data["fixture"]["sha256"]
    assert cold["parity_counts"] == data["fixture"]["counts"]
    assert cold["backup_verified"] is True
    assert len(cold["package_sha256_start"]) == 64
    assert cold["build_unchanged_during_measurement"] is True
    assert steady["package_sha256_start"] == cold["package_sha256_start"]
    assert "cold_start" in cold["operations"]
    assert "restart" in steady["operations"]
    assert steady["operations"]["observer_reconnect_cycles"]["fd_change"] == 0
    assert (
        cold["operations"]["persistence_including_projection"]["phase_wall_seconds"][
            "projection_seconds"
        ]
        >= 0
    )
    assert steady["operations"]["idle"]["historical_files_unchanged"]
    assert "five-minute target remains unvalidated" in " ".join(data["misses_or_unvalidated"])


def test_historical_stamp_streams_entries_without_history_lists(tmp_path, monkeypatch):
    module = load_benchmark()
    root = tmp_path / "history"
    root.mkdir()
    for i in range(50):
        (root / f"{i}.json").write_text("{}")
    first = module.historical_stamp(root)

    def refuse(*args, **kwargs):
        raise AssertionError("history-sized os.walk file lists are forbidden")

    monkeypatch.setattr(module.os, "walk", refuse)
    assert module.historical_stamp(root) == first


def test_inventory_avoids_pathlib_filename_interning(tmp_path, monkeypatch):
    module = load_benchmark()
    (tmp_path / "one.json").write_text("{}")
    expected = module.historical_stamp(tmp_path)

    def refuse(*args, **kwargs):
        raise AssertionError("per-file pathlib parsing retains interned historical names")

    monkeypatch.setattr(module, "Path", refuse)
    assert module.historical_stamp(tmp_path) == expected


def test_repeated_workers_observe_new_evidence_after_existing_coverage(tmp_path):
    module = load_benchmark()
    fixture = module.generate_fixture(tmp_path, sessions=5, turns=10, quota=2, usage=4)
    config = {
        "backend": "optimized",
        "phase": "cold",
        "data": str(tmp_path / "data"),
        "state": str(tmp_path / "state"),
        "home": str(tmp_path / "home"),
        "counts": fixture["counts"],
        "fixture_sha256": fixture["sha256"],
        "plain": True,
    }
    module.worker(config)
    first = Store(tmp_path / "data", tmp_path / "state").load()
    end = max(span.end for span in first.sessions["s000000"].turns["live"].coverage)
    module.worker(config)
    after = Store(tmp_path / "data", tmp_path / "state").load()
    assert max(span.end for span in after.sessions["s000000"].turns["live"].coverage) > end
