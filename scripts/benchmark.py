#!/usr/bin/env python3
"""Measure content-free tracking workloads with separate startup and steady windows.

Run from a checkout's environment. All inputs and results stay under --work-dir;
this harness never reads real Codex history or contacts a live socket. Baseline
and optimized workers import the explicitly selected source checkout in fresh
processes. Synthetic active windows represent five observed root sessions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codex_time.models import Ledger

COUNTS = {"sessions": 5449, "turns": 49885, "quota": 285348, "usage": 195166}
AT = datetime(2026, 10, 14, tzinfo=UTC)
LIVE_AT = AT + timedelta(days=1)
TARGETS = {"idle_cpu_percent": 0.5, "active_cpu_percent": 2.0, "steady_rss_mib": 128.0}


class Progress:
    """A heartbeat remains visible while scans, migrations, or copies are blocked."""

    def __init__(self, plain: bool = False, interval: float = 15.0) -> None:
        self.plain = plain
        self.interval = interval
        self.phase = "Preparing"
        self.started = time.monotonic()
        self.last_detail = 0.0
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._heartbeat, daemon=True)

    def say(self, message: str) -> None:
        print(("" if self.plain else "⏱️ ") + message, file=sys.stderr, flush=True)

    def set(self, phase: str) -> None:
        self.phase = phase
        self.say(phase)

    def detail(self, message: str) -> None:
        now = time.monotonic()
        if now - self.last_detail >= 2:
            self.say(message)
            self.last_detail = now

    def _heartbeat(self) -> None:
        while not self.stopped.wait(self.interval):
            self.say(f"{self.phase}: {time.monotonic() - self.started:.0f}s elapsed")

    def __enter__(self) -> Progress:
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.stopped.set()
        self.thread.join(timeout=1)


def _dump(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _stamp(seconds: int) -> str:
    return (AT + timedelta(seconds=seconds)).isoformat()


def generate_fixture(
    destination: Path,
    *,
    sessions: int,
    turns: int,
    quota: int,
    usage: int,
    progress: Progress | None = None,
) -> dict[str, object]:
    """Write exact-scale legacy history while retaining only one record at a time."""
    if sessions < 5 or turns < sessions or quota < 0 or usage < 0:
        raise ValueError(
            "fixture needs at least five sessions, one turn each, and nonnegative history"
        )
    data, home = destination / "data", destination / "home"
    data.mkdir(parents=True, exist_ok=True)
    (home / "sessions").mkdir(parents=True, exist_ok=True)
    if progress:
        progress.set(
            f"Fixture: {sessions:,} sessions; {turns:,} turns; {quota:,} quota; {usage:,} usage"
        )
    with (data / "ledger.json").open("w") as output:
        output.write('{"version":4,"diagnostics":[],"sessions":{')
        for i in range(sessions):
            sid = f"s{i:06d}"
            count = turns // sessions + (i < turns % sessions)
            meta = {
                "id": sid,
                "cwd": "/fixture/project",
                "title": f"Synthetic session {i}",
                "created": _stamp(0),
                "updated": _stamp(count * 10),
                "is_child": i == sessions - 1 and sessions > 5,
                "parent_id": "s000000" if i == sessions - 1 and sessions > 5 else None,
            }
            output.write(("," if i else "") + _dump(sid) + ":" + _dump(meta)[:-1] + ',"turns":{')
            for j in range(count):
                live = i < 5 and j == count - 1
                tid = "live" if live else f"t{j:06d}"
                turn = {
                    "id": tid,
                    "cwd": "/fixture/project",
                    "start": _stamp(j * 10),
                    "end": None if live else _stamp(j * 10 + 8),
                    "model_contexts": [
                        {"at": _stamp(j * 10), "model_id": "gpt-4.1", "reasoning_level": "medium"}
                    ],
                    "waits": []
                    if live or j % 7
                    else [{"start": _stamp(j * 10 + 2), "end": _stamp(j * 10 + 4)}],
                }
                output.write(("," if j else "") + _dump(tid) + ":" + _dump(turn))
            output.write("}}")
            if i < 5:
                records = [
                    {
                        "timestamp": _stamp(0),
                        "type": "session_meta",
                        "payload": {"id": sid, "cwd": "/fixture/project", "source": "cli"},
                    },
                    {
                        "timestamp": _stamp((count - 1) * 10),
                        "type": "event_msg",
                        "payload": {"type": "task_started", "turn_id": "live"},
                    },
                ]
                (home / "sessions" / f"{sid}.jsonl").write_text(
                    "".join(_dump(record) + "\n" for record in records)
                )
        output.write("}}\n")
    with (data / "quota-observations.jsonl").open("w") as output:
        for i in range(quota):
            output.write(
                _dump(
                    {
                        "at": _stamp(i),
                        "limit_id": "codex",
                        "plan_type": "fixture",
                        "bucket": "primary",
                        "window_minutes": 300,
                        "resets_at": 2000000000,
                        "used_percent": float(i % 100),
                    }
                )
                + "\n"
            )
    with (data / "usage-observations.jsonl").open("w") as output:
        for i in range(usage):
            amount = (i // sessions + 1) * 10
            output.write(
                _dump(
                    {
                        "id": f"u{i:09d}",
                        "session_id": f"s{i % sessions:06d}",
                        "at": _stamp(i),
                        "cwd": "/fixture/project",
                        "model_id": "gpt-4.1",
                        "cumulative": {"input_tokens": amount},
                        "delta": {"input_tokens": 10},
                    }
                )
                + "\n"
            )
    digest = hashlib.sha256()
    size = 0
    for name in ("ledger.json", "quota-observations.jsonl", "usage-observations.jsonl"):
        path = data / name
        size += path.stat().st_size
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                digest.update(block)
    result: dict[str, object] = {
        "counts": {"sessions": sessions, "turns": turns, "quota": quota, "usage": usage},
        "sha256": digest.hexdigest(),
        "bytes": size,
        "content_free": True,
        "observed_roots": 5,
    }
    (destination / "fixture.json").write_text(_dump(result) + "\n")
    return result


def snapshot() -> dict[str, Any]:
    status = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith(("VmRSS:", "VmHWM:")):
            key, value = line.split(":", 1)
            status[key] = int(value.split()[0]) / 1024
    io = {}
    for line in Path("/proc/self/io").read_text().splitlines():
        key, value = line.split(":", 1)
        io[key] = int(value)
    return {
        "rss_mib": status["VmRSS"],
        "peak_rss_mib": status["VmHWM"],
        "fds": len(os.listdir("/proc/self/fd")),
        "io": io,
    }


def measure(operation: Callable[[], object], *, operations: int = 1) -> dict[str, Any]:
    before = snapshot()
    wall, cpu = time.monotonic(), time.process_time()
    operation()
    elapsed_cpu, elapsed_wall = time.process_time() - cpu, time.monotonic() - wall
    after = snapshot()
    return {
        "wall_seconds": elapsed_wall,
        "cpu_seconds": elapsed_cpu,
        "cpu_percent_one_core": elapsed_cpu / elapsed_wall * 100 if elapsed_wall else 0,
        "rss_mib": after["rss_mib"],
        "peak_rss_mib": after["peak_rss_mib"],
        "rss_change_mib": after["rss_mib"] - before["rss_mib"],
        "fd_change": after["fds"] - before["fds"],
        "fds": after["fds"],
        "logical_io": {key: after["io"][key] - value for key, value in before["io"].items()},
        "operations": operations,
    }


def _window(
    seconds: float,
    interval: float,
    operation: Callable[[int], None],
    progress: Progress,
    label: str,
) -> dict[str, Any]:
    progress.set(f"{label}: requested {seconds:g}s window; cadence {interval:g}s")
    count, latencies = 0, []

    def run() -> None:
        nonlocal count
        started = time.monotonic()
        next_at = started
        while seconds > 0 and time.monotonic() < started + seconds:
            now = time.monotonic()
            if now >= next_at:
                began = time.monotonic()
                operation(count)
                latencies.append(time.monotonic() - began)
                count += 1
                # Never overlap or pile up work when an operation exceeds its cadence.
                next_at = max(next_at + interval, time.monotonic())
            remaining = min(next_at, started + seconds) - time.monotonic()
            if remaining > 0:
                time.sleep(min(remaining, 0.25))

    result = measure(run, operations=0)
    result.update(
        {
            "operations": count,
            "requested_seconds": seconds,
            "cadence_seconds": interval,
            "max_update_operation_seconds": max(latencies, default=0),
            "nominal_update_latency_seconds": interval,
            "workload": "synthetic five observed roots"
            if label.endswith("active")
            else "fixed input",
        }
    )
    return result


def historical_stamp(root: Path) -> str:
    """Order-independent metadata digest with no history-sized filename lists."""
    count, total = 0, 0
    modulus = 1 << 256

    prefix = str(root) + os.sep

    def visit(directory: str) -> None:
        nonlocal count, total
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    visit(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    stat = entry.stat(follow_symlinks=False)
                    # Pathlib interns parsed filename components process-wide.
                    # Keep per-file names as ordinary short-lived strings.
                    body = _dump((entry.path[len(prefix) :], stat.st_size, stat.st_mtime_ns))
                    total = (
                        total + int.from_bytes(hashlib.sha256(body.encode()).digest(), "big")
                    ) % modulus
                    count += 1

    visit(str(root))
    return hashlib.sha256(f"{count}:{total:064x}".encode()).hexdigest()


def package_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in (".py", ".json"):
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def observation_epoch(ledger: Ledger) -> datetime:
    """Repeated runs observe new time without traversing cold session history."""
    latest = LIVE_AT
    for index in range(5):
        session = ledger.sessions.get(f"s{index:06d}")
        turn = session.turns.get("live") if session else None
        if turn is not None:
            latest = max(latest, turn.start)
            for spans in (turn.coverage, turn.waits):
                for span in spans:
                    latest = max(latest, span.end)
    return latest + timedelta(seconds=1)


def worker(config: dict[str, Any]) -> dict[str, Any]:
    # Imports deliberately happen only after the process-specific PYTHONPATH is set.
    import codex_time
    from codex_time.ingest import RolloutReader
    from codex_time.models import Observation
    from codex_time.observer import Observer
    from codex_time.storage import Store

    kind, phase = config["backend"], config["phase"]
    root, state, home = (Path(config[key]) for key in ("data", "state", "home"))
    optimized = kind == "optimized"
    operations: dict[str, Any] = {}
    result: dict[str, Any] = {
        "backend": kind,
        "phase": phase,
        "fixture_sha256": config["fixture_sha256"],
        "package_path": str(Path(codex_time.__file__).resolve()),
        "pid": os.getpid(),
        "workload_kind": "sanitized synthetic; no live socket or network",
        "operations": operations,
    }
    package_root = Path(codex_time.__file__).resolve().parent
    result["package_sha256_start"] = package_digest(package_root)

    def finish() -> dict[str, Any]:
        result["package_sha256_end"] = package_digest(package_root)
        result["build_unchanged_during_measurement"] = (
            result["package_sha256_start"] == result["package_sha256_end"]
        )
        return result

    with Progress(config["plain"]) as progress, ExitStack() as stack:
        progress.set(f"{kind} {phase}: opening known-build storage")

        def open_store() -> None:
            nonlocal store, ledger
            if optimized:
                from codex_time.incremental_storage import IndexedStore

                indexed = IndexedStore(root, state)
                indexed.progress = progress.detail
                store = stack.enter_context(indexed)
                ledger = store.ledger
            else:
                store = Store(root, state)
                stack.enter_context(store.writer())
                ledger = store.load()

        store: Any = None
        ledger: Any = None

        def record(operation: Callable[[], object], *, count: int = 1) -> dict[str, Any]:
            before = dict(getattr(store, "timings", {}))
            measured = measure(operation, operations=count)
            after = getattr(store, "timings", {})
            if after:
                measured["phase_wall_seconds"] = {
                    key: value - before.get(key, 0) for key, value in after.items()
                }
            return measured

        operations["cold_start" if phase == "cold" else "restart"] = record(open_store)
        reader = RolloutReader(home, backend=store) if optimized else RolloutReader(home)
        interval = 60.0 if optimized else 1.0
        observer = Observer(max_gap=75, sample_seconds=60) if optimized else Observer()
        paths = sorted((home / "sessions").glob("*.jsonl"))
        live_epoch = observation_epoch(ledger)
        result["observation_epoch"] = live_epoch.isoformat()

        def ingest() -> None:
            if optimized:
                pending = reader.scan_paths(ledger, paths)
                while pending:
                    pending = reader.scan_paths(ledger, pending)
            else:
                reader.scan(ledger)

        def save() -> None:
            if optimized:
                store.flush()
            else:
                store.save(ledger)

        def observe(index: int, *, active: bool) -> None:
            samples = (
                [
                    Observation(
                        session_id=f"s{i:06d}",
                        turn_id="live",
                        state="working",
                        at=live_epoch + timedelta(seconds=index * interval),
                        uncertainty_seconds=interval,
                    )
                    for i in range(5)
                ]
                if active
                else []
            )
            observer.apply(ledger, samples)

        if phase == "cold":
            progress.set(f"{kind}: initial changed-source ingestion")
            operations["ingestion"] = record(ingest)
            operations["observation"] = record(
                lambda: (observe(0, active=True), observe(1, active=True)), count=2
            )
            progress.set(f"{kind}: initial persistence")
            operations["persistence_including_projection"] = record(save)
            if not optimized:
                operations["projection"] = measure(lambda: store.project(ledger))
            else:
                result["projection_note"] = (
                    "phase_wall_seconds separates internal persistence/projection/index; "
                    "CPU and I/O measure their aggregate"
                )
            operations["unchanged_ingestion"] = record(ingest)
            operations["unchanged_persistence_including_projection"] = record(save)
            progress.set(f"{kind}: verifying history counts and migration backup")

            def verify_counts() -> None:
                result["parity_counts"] = {
                    "sessions": len(ledger.sessions),
                    "turns": sum(len(session.turns) for session in ledger.sessions.values()),
                    "quota": store.db.execute("SELECT count(*) FROM quotas").fetchone()[0]
                    if optimized
                    else len(ledger.quota_observations),
                    "usage": store.db.execute("SELECT count(*) FROM usage").fetchone()[0]
                    if optimized
                    else len(ledger.usage_observations),
                }
                if result["parity_counts"] != config["counts"]:
                    raise RuntimeError("fixture history count parity failed")
                if optimized:
                    result["backup_verified"] = store.verify_backup()
                    if not result["backup_verified"]:
                        raise RuntimeError("pre-migration backup verification failed")

            operations["history_and_backup_verification"] = record(verify_counts)
            return finish()

        ingest()
        save()

        def tick(index: int, *, active: bool) -> None:
            # Full fallback is one bounded reconciliation per minute in the new design.
            ingest()
            observe(index, active=active)
            save()

        def window(seconds: float, *, active: bool, label: str) -> dict[str, Any]:
            if not active:
                # Transition-to-idle gap evidence belongs to warm-up, not fixed-input idle.
                observer.apply(ledger, [])
                save()
            before = dict(getattr(store, "timings", {}))
            stamp = historical_stamp(root) if not active else None
            measured = _window(
                seconds,
                interval,
                lambda i: tick(i + (2 if active else 0), active=active),
                progress,
                label,
            )
            after = getattr(store, "timings", {})
            if after:
                measured["phase_wall_seconds"] = {
                    key: value - before.get(key, 0) for key, value in after.items()
                }
            if stamp is not None:
                measured["historical_files_unchanged"] = historical_stamp(root) == stamp
            return measured

        operations["idle"] = window(config["idle_seconds"], active=False, label=kind + " idle")
        observer.previous.clear()
        operations["active"] = window(config["active_seconds"], active=True, label=kind + " active")
        if optimized:
            # Settle the active-to-missing transition outside the fixed-input soak.
            tick(-1, active=False)
            operations["idle_soak"] = window(
                config["soak_seconds"], active=False, label="optimized idle soak"
            )
            cycles = config["cycles"]
            progress.set(f"optimized: {cycles} observer open/close/reconnect cycles")

            def reconnects() -> None:
                for index in range(cycles):
                    observer.previous.clear()
                    observe(1000 + index * 2, active=True)
                    observe(1001 + index * 2, active=True)
                    observer.apply(ledger, [])
                    save()

            operations["observer_reconnect_cycles"] = record(reconnects, count=cycles)
            result["cycle_note"] = (
                "observer/store cycles; socket reconnect is covered by runtime smoke tests"
            )
        result["final_resources"] = snapshot()
    return finish()


def _run_worker(
    config: dict[str, Any], package: Path, progress: Progress, output: Path
) -> dict[str, Any]:
    env = dict(os.environ, PYTHONPATH=str(package / "src"))
    progress.set(f"Launching {config['backend']} {config['phase']} worker from {package}")
    with output.open("w") as destination:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker", _dump(config)],
            env=env,
            stdout=destination,
        )
        returncode = child.wait()
    if returncode:
        raise RuntimeError(
            f"{config['backend']} {config['phase']} worker failed with exit {returncode}; "
            "see stderr"
        )
    result = json.loads(output.read_text())
    loaded = Path(result["package_path"])
    if not loaded.is_relative_to((package / "src").resolve()):
        raise RuntimeError(f"worker imported unexpected package: {loaded}")
    return result


def evaluate(measurements: list[dict[str, Any]]) -> list[str]:
    misses = []
    for result in measurements:
        if not result.get("build_unchanged_during_measurement", False):
            misses.append(
                f"{result['backend']} {result['phase']}: package source changed during measurement"
            )
        if result["backend"] != "optimized" or result["phase"] != "steady":
            continue
        for phase in ("idle", "active"):
            observed = result["operations"][phase]
            if observed["requested_seconds"] < 300:
                misses.append(f"{phase}: short window; five-minute target remains unvalidated")
            target = TARGETS[phase + "_cpu_percent"]
            if observed["cpu_percent_one_core"] > target:
                misses.append(
                    f"{phase}: {observed['cpu_percent_one_core']:.3f}% CPU "
                    f"exceeds {target:g}% target"
                )
            if observed["rss_mib"] > TARGETS["steady_rss_mib"]:
                misses.append(f"{phase}: {observed['rss_mib']:.1f} MiB RSS exceeds 128 MiB target")
        if result["operations"]["idle_soak"]["requested_seconds"] < 1800:
            misses.append(
                "idle soak: short window; 30-minute retained-memory check remains unvalidated"
            )
        for phase in ("idle", "idle_soak"):
            if not result["operations"][phase].get("historical_files_unchanged", False):
                misses.append(f"{phase}: fixed input changed historical files")
    return misses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--baseline", type=Path, help="explicit legacy source checkout")
    parser.add_argument("--optimized", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skip-baseline", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--scale10", action="store_const", const=10, dest="scale")
    for name in COUNTS:
        parser.add_argument("--" + name, type=int)
    parser.add_argument("--idle-seconds", type=float, default=300)
    parser.add_argument("--active-seconds", type=float, default=300)
    parser.add_argument("--soak-seconds", type=float, default=1800)
    parser.add_argument("--cycles", type=int, default=50)
    parser.add_argument("--fixture-only", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        print(_dump(worker(json.loads(args.worker))))
        return
    durations = (args.idle_seconds, args.active_seconds, args.soak_seconds, args.cycles)
    if args.scale < 1 or min(durations) < 0:
        parser.error("scale must be positive and durations/cycles must be nonnegative")
    if args.baseline_only and (args.skip_baseline or args.baseline is None):
        parser.error("--baseline-only needs --baseline and cannot use --skip-baseline")
    if not args.fixture_only and not args.skip_baseline and args.baseline is None:
        parser.error("pass --baseline CHECKOUT or --skip-baseline; no implicit installed build")
    root = (args.work_dir or Path(tempfile.mkdtemp(prefix="codex-time-benchmark-"))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    fixture_dir = root / "fixture"
    if fixture_dir.exists():
        parser.error("work directory already contains a fixture; choose a fresh directory")
    counts = {
        name: getattr(args, name) if getattr(args, name) is not None else count * args.scale
        for name, count in COUNTS.items()
    }
    with Progress(args.plain) as progress:
        fixture = generate_fixture(fixture_dir, progress=progress, **counts)
        measurements = []
        if not args.fixture_only:
            backends = [] if args.baseline_only else [("optimized", args.optimized.resolve())]
            if not args.skip_baseline:
                backends.insert(0, ("baseline", args.baseline.resolve()))
            for backend, package in backends:
                progress.set(f"Preparing identical {backend} input")
                data = root / backend / "data"
                shutil.copytree(fixture_dir / "data", data)
                config = {
                    "backend": backend,
                    "data": str(data),
                    "state": str(root / backend / "state"),
                    "fixture_sha256": fixture["sha256"],
                    "counts": counts,
                    "home": str(fixture_dir / "home"),
                    "plain": args.plain,
                    "idle_seconds": args.idle_seconds,
                    "active_seconds": args.active_seconds,
                    "soak_seconds": args.soak_seconds,
                    "cycles": args.cycles,
                }
                for phase in ("cold", "steady"):
                    measurements.append(
                        _run_worker(
                            dict(config, phase=phase),
                            package,
                            progress,
                            root / f"{backend}-{phase}.json",
                        )
                    )
        report = {
            "fixture": fixture,
            "measurements": measurements,
            "targets": TARGETS,
            "misses_or_unvalidated": evaluate(measurements),
            "artifacts": str(root),
            "notes": [
                "CPU is per worker, expressed as percent of one core.",
                "RSS/HWM include worker Python memory; startup/backfill are separate.",
                "Logical I/O includes /proc measurement reads and progress writes.",
                "Synthetic workload excludes real sockets and OS notification delivery.",
            ],
        }
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        progress.set("Benchmark complete; measured results saved")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(("" if args.plain else "📊 ") + "Tracking resource benchmark")
        print(f"Fixture: {fixture['sha256']}; artifacts: {root}")
        print("Backend    Phase       CPU/core   RSS MiB   Peak MiB   Wall s   Operations")
        for row in measurements:
            for phase, metric in row["operations"].items():
                print(
                    f"{row['backend']:<10} {phase:<28} {metric['cpu_percent_one_core']:8.3f}% "
                    f"{metric['rss_mib']:9.2f} {metric['peak_rss_mib']:10.2f} "
                    f"{metric['wall_seconds']:8.2f} {metric['operations']:8}"
                )
        for finding in report["misses_or_unvalidated"]:
            print(("" if args.plain else "⚠️ ") + finding)


if __name__ == "__main__":
    main()
