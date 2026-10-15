#!/usr/bin/env python3
"""Run the actual executable against five content-free disposable Unix peers.

Clone a sanitized benchmark fixture or generate a tiny one, launch an isolated
daemon, measure steady runtime, then verify waits, reconnects, lifecycle evidence,
and health freshness. No production service, package, socket, or data is changed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import shutil
import signal
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import ijson
from websockets.asyncio.server import ServerConnection, unix_serve


def dump(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    if path.exists():
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                result.update(block)
    return result.hexdigest()


def resources(pid: int) -> dict[str, Any]:
    root = Path("/proc") / str(pid)
    status = {}
    for line in (root / "status").read_text().splitlines():
        if line.startswith(("VmRSS:", "VmHWM:")):
            key, value = line.split(":", 1)
            status[key] = int(value.split()[0]) / 1024
    fields = (root / "stat").read_text().rsplit(")", 1)[1].split()
    io = {}
    for line in (root / "io").read_text().splitlines():
        key, value = line.split(":", 1)
        io[key] = int(value)
    clock_ticks = os.sysconf("SC_CLK_TCK")
    self_cpu = (int(fields[11]) + int(fields[12])) / clock_ticks
    child_cpu = (int(fields[13]) + int(fields[14])) / clock_ticks
    return {
        "cpu_seconds": self_cpu + child_cpu,
        "self_cpu_seconds": self_cpu,
        "children_cpu_seconds": child_cpu,
        "start_ticks": int(fields[19]),
        "rss_mib": status["VmRSS"],
        "peak_rss_mib": status["VmHWM"],
        "fds": len(os.listdir(root / "fd")),
        "logical_io": io,
    }


def worker_snapshot(pid: int, limit: int = 32) -> tuple[dict[int, dict[str, Any]], bool]:
    """Read each parent before discovering its currently unreaped children."""
    pending = [pid]
    seen: set[int] = set()
    result = {}
    truncated = False
    while pending:
        current = pending.pop(0)
        if current in seen:
            continue
        seen.add(current)
        try:
            result[current] = resources(current)
            path = Path(f"/proc/{current}/task/{current}/children")
            with path.open("rb") as source:
                children = source.read(4096)
            truncated |= len(children) == 4096
            for child in children.split():
                if len(seen) + len(pending) >= limit:
                    truncated = True
                    break
                if child.isdigit():
                    pending.append(int(child))
        except (OSError, ValueError, KeyError):
            # Exiting/zombie children may disappear between the three /proc reads.
            # Their CPU reaches their parent's waited-child counter after reaping.
            continue
    return result, truncated


async def startup_workers(
    pid: int, done: asyncio.Event, *, interval: float = 0.1, limit: int = 32
) -> dict[str, Any]:
    """Monitor only startup; retain a fixed-size process/HWM inventory."""
    samples = 0
    simultaneous = 0
    peak_rss = 0.0
    total_cpu = 0.0
    hwm: dict[tuple[int, int], float] = {}
    truncated = False
    while True:
        snapshot, clipped = worker_snapshot(pid, limit)
        truncated |= clipped
        samples += 1
        simultaneous = max(simultaneous, len(snapshot))
        peak_rss = max(peak_rss, sum(row["rss_mib"] for row in snapshot.values()))
        # Add only live tree nodes, not retained observations of dead children.
        # Parent cpu_seconds already includes descendants it has waited for.
        # Parent-before-children reads avoid counting a reaped child again; a
        # race can undercount one sample, so keep the cumulative maximum.
        total_cpu = max(total_cpu, sum(row["cpu_seconds"] for row in snapshot.values()))
        for child, row in snapshot.items():
            identity = (child, row["start_ticks"])
            if identity in hwm or len(hwm) < limit * 4:
                hwm[identity] = max(hwm.get(identity, 0.0), row["peak_rss_mib"])
            else:
                truncated = True
        if done.is_set():
            break
        try:
            await asyncio.wait_for(done.wait(), interval)
        except TimeoutError:
            pass
    return {
        "sample_interval_seconds": interval,
        "sample_count": samples,
        "max_simultaneous_workers": simultaneous,
        "peak_sampled_aggregate_rss_mib": peak_rss,
        "observed_process_hwm_sum_mib": sum(hwm.values()),
        "hwm_scope": "conservative sum of observed process HWMs; non-simultaneous",
        "cumulative_cpu_seconds": total_cpu,
        "cpu_scope": "live tree CPU plus reaped descendants once, via parent counters",
        "rss_scope": "sampled daemon and bootstrap descendants; excludes mock peer/harness",
        "worker_limit": limit,
        "inventory_limit": limit * 4,
        "truncated": truncated,
        "observed_processes": len(hwm),
    }


def read_checkpoint(state: Path) -> dict[str, Any]:
    try:
        return json.loads((state / "checkpoint.json").read_text())
    except (OSError, ValueError):
        return {}


def selected_sessions(data: Path) -> dict[str, Any]:
    selected = {}
    if (data / "layout.json").exists():
        paths = (data / "sessions").glob("*.json")
        sessions = (json.loads(path.read_text()) for path in paths)
    else:

        def legacy():
            with (data / "ledger.json").open("rb") as source:
                for _sid, value in ijson.kvitems(source, "sessions", use_float=True):
                    yield value

        sessions = legacy()
    for session in sessions:
        if session.get("is_child") or session.get("parent_id"):
            continue
        if any(turn.get("end") is None for turn in session["turns"].values()):
            selected[session["id"]] = session
        if len(selected) == 5:
            break
    if len(selected) != 5:
        raise ValueError("sanitized fixture must contain five open root sessions")
    return selected


def session(data: Path, sid: str) -> dict[str, Any]:
    name = hashlib.sha256(sid.encode()).hexdigest()[:24] + ".json"
    return json.loads((data / "sessions" / name).read_text())


def make_fixture(root: Path) -> None:
    data, home = root / "data", root / "home"
    data.mkdir()
    (home / "sessions").mkdir(parents=True)
    now = datetime.now(UTC)
    sessions = {}
    for index in range(5):
        sid = f"s{index:06d}"
        start = (now - timedelta(seconds=20)).isoformat()
        sessions[sid] = {
            "id": sid,
            "cwd": "/fixture/project",
            "created": start,
            "updated": start,
            "turns": {
                "closed": {
                    "id": "closed",
                    "cwd": "/fixture/project",
                    "start": (now - timedelta(seconds=100)).isoformat(),
                    "end": (now - timedelta(seconds=90)).isoformat(),
                },
                "live": {"id": "live", "cwd": "/fixture/project", "start": start},
            },
        }
        records = [
            {
                "timestamp": start,
                "type": "session_meta",
                "payload": {"id": sid, "cwd": "/fixture/project", "source": "cli"},
            },
            {
                "timestamp": start,
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "live"},
            },
        ]
        (home / "sessions" / f"{sid}.jsonl").write_text(
            "".join(dump(record) + "\n" for record in records)
        )
    (data / "ledger.json").write_text(dump({"version": 4, "sessions": sessions}) + "\n")
    for name in ("quota-observations.jsonl", "usage-observations.jsonl"):
        (data / name).write_text("")


def make_metadata(data: Path, home: Path) -> dict[str, int]:
    """Stream equivalent read-only Codex metadata without retaining its history."""
    counts = {"threads": 0, "turns": 0, "names": 0}
    with (
        closing(sqlite3.connect(home / "state_1.sqlite")) as threads,
        closing(sqlite3.connect(home / "thread_history_1.sqlite")) as turns,
        (home / "session_index.jsonl").open("w") as names,
    ):
        threads.execute("CREATE TABLE threads(id TEXT PRIMARY KEY,cwd,created_at,updated_at,name)")
        turns.execute("CREATE TABLE thread_turns(thread_id,turn_id,status,started_at,completed_at)")
        turns.execute("CREATE INDEX thread_turns_session ON thread_turns(thread_id)")
        with (data / "ledger.json").open("rb") as source:
            for sid, item in ijson.kvitems(source, "sessions"):
                title = item.get("title") or f"Synthetic session {sid}"
                threads.execute(
                    "INSERT INTO threads VALUES (?,?,?,?,?)",
                    (
                        sid,
                        item["cwd"],
                        instant(item["created"]).timestamp(),
                        instant(item["updated"]).timestamp(),
                        title,
                    ),
                )
                counts["threads"] += 1
                for tid, turn in item["turns"].items():
                    end = instant(turn["end"]).timestamp() if turn.get("end") else None
                    turns.execute(
                        "INSERT INTO thread_turns VALUES (?,?,?,?,?)",
                        (
                            sid,
                            tid,
                            "completed" if end is not None else "started",
                            instant(turn["start"]).timestamp(),
                            end,
                        ),
                    )
                    counts["turns"] += 1
                names.write(dump({"id": sid, "thread_name": title}) + "\n")
                counts["names"] += 1
        threads.commit()
        turns.commit()
    return counts


class RolloutEvents:
    """Append fixed synthetic ignored messages; retain five counters/offsets."""

    def __init__(self, home: Path, roots: list[str], interval: float) -> None:
        if not math.isfinite(interval) or interval < 0:
            raise ValueError("rollout event interval must be finite and nonnegative")
        if len(roots) != 5:
            raise ValueError("rollout event workload requires five original roots")
        self.paths = [home / "sessions" / f"{sid}.jsonl" for sid in roots]
        self.interval = interval
        self.counts = [0] * len(roots)
        self.events_written = 0
        self.bytes_written = 0
        self.tail_offsets: dict[str, int] = {}
        self.body = "x" * 4096

    async def run(self) -> None:
        if not self.interval:
            return
        while True:
            slot = self.events_written % len(self.paths)
            record = (
                dump(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": self.body}],
                        },
                    }
                )
                + "\n"
            ).encode()
            # No await occurs within a write: cancellation leaves complete lines
            # and every count below follows a successful close/flush.
            with self.paths[slot].open("ab") as output:
                written = output.write(record)
                offset = output.tell()
                stamp = os.fstat(output.fileno())
            if written != len(record):
                raise OSError("synthetic rollout record was not completely written")
            self.tail_offsets[f"{stamp.st_dev}:{stamp.st_ino}"] = offset
            self.counts[slot] += 1
            self.events_written += 1
            self.bytes_written += written
            await asyncio.sleep(self.interval)

    def report(self) -> dict[str, Any]:
        return {
            "enabled": self.interval > 0,
            "interval_seconds": self.interval,
            "payload_bytes": len(self.body),
            "roots": len(self.paths),
            "per_root_event_counts": list(self.counts),
            "events_written": self.events_written,
            "bytes_written": self.bytes_written,
        }


class Smoke:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.root = args.work_dir.resolve()
        self.data, self.home, self.state = (self.root / name for name in ("data", "home", "state"))
        self.phase = "Preparing disposable packaged daemon"
        self.began = time.monotonic()
        self.state_name = "working"
        self.drop_once = False
        self.calls: Counter[str] = Counter()
        self.connections = 0
        self.last_poll: float | None = None
        self.max_poll_interval = 0.0
        self.daemon: asyncio.subprocess.Process | None = None
        self.rollout_events: RolloutEvents | None = None

    def say(self, message: str) -> None:
        print(("" if self.args.plain else "⏱️ ") + message, file=sys.stderr, flush=True)

    async def progress(self) -> None:
        while True:
            await asyncio.sleep(15)
            events = self.rollout_events
            suffix = (
                f"; synthetic rollout records={events.events_written}"
                if events and events.interval
                else ""
            )
            self.say(f"{self.phase}: {time.monotonic() - self.began:.0f}s elapsed{suffix}")

    def rollout_tails_consumed(self, events: RolloutEvents) -> bool:
        with closing(
            sqlite3.connect((self.state / "index.sqlite").as_uri() + "?mode=ro", uri=True)
        ) as db:
            for identity, offset in events.tail_offsets.items():
                row = db.execute(
                    "SELECT json_extract(body,'$.offset') FROM checkpoints WHERE id=?", (identity,)
                ).fetchone()
                if row is None or row[0] is None or int(row[0]) < offset:
                    return False
        return True

    def daemon_exit_error(self) -> RuntimeError:
        assert self.daemon is not None
        code = self.daemon.returncode
        name = signal.Signals(-code).name if code is not None and code < 0 else "none"
        return RuntimeError(
            f"daemon exited unexpectedly: returncode={code}; signal={name}; "
            f"daemon_log={self.root / 'daemon.log'}"
        )

    async def daemon_resources(self) -> dict[str, Any]:
        assert self.daemon is not None
        if self.daemon.returncode is not None:
            raise self.daemon_exit_error()
        try:
            return resources(self.daemon.pid)
        except (OSError, ValueError, KeyError) as exc:
            # A child can exit after the returncode check or between /proc reads.
            # Reap that child before reporting its exact status; retain failure
            # if a live process's resource files cannot be sampled.
            try:
                await asyncio.wait_for(asyncio.shield(self.daemon.wait()), timeout=1)
            except TimeoutError:
                raise RuntimeError(
                    f"daemon resource probe failed: {type(exc).__name__}; "
                    f"daemon_log={self.root / 'daemon.log'}"
                ) from exc
            raise self.daemon_exit_error() from exc

    async def resource_snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            "daemon": await self.daemon_resources(),
            "mock_server_and_harness": resources(os.getpid()),
        }

    async def until(self, predicate: Callable[[], bool], *, timeout: float) -> None:
        async with asyncio.timeout(timeout):
            while not predicate():
                if self.daemon is not None and self.daemon.returncode is not None:
                    raise self.daemon_exit_error()
                await asyncio.sleep(min(0.1, self.args.sample_seconds / 10))

    def states_are(self, expected: str) -> bool:
        observations = read_checkpoint(self.state).get("observations", {})
        return len(observations) == 5 and all(
            o.get("state") == expected for o in observations.values()
        )

    async def handler(self, ws: ServerConnection) -> None:
        self.connections += 1
        async for raw in ws:
            request = json.loads(raw)
            method = request["method"]
            self.calls[method] += 1
            if method == "initialized":
                continue
            if self.drop_once:
                self.drop_once = False
                await ws.close()
                return
            if method == "initialize":
                result = {}
            elif method == "thread/loaded/list":
                now = time.monotonic()
                if self.last_poll is not None:
                    self.max_poll_interval = max(self.max_poll_interval, now - self.last_poll)
                self.last_poll = now
                result = {"data": list(self.original), "nextCursor": None}
            elif method == "thread/read":
                if request["params"].get("includeTurns") is not False:
                    raise RuntimeError("observer requested conversation bodies")
                sid = request["params"]["threadId"]
                result = {
                    "thread": {
                        "id": sid,
                        "cwd": self.original[sid]["cwd"],
                        "status": {
                            "type": "idle" if self.state_name == "idle" else "active",
                            "activeFlags": ["waitingOnUserInput"]
                            if self.state_name == "waiting"
                            else [],
                        },
                    }
                }
            else:
                raise RuntimeError("observer used RPC outside its read-only allowlist")
            await ws.send(dump({"id": request["id"], "result": result}))

    async def cli(self, *options: str, state: Path | None = None) -> dict[str, Any]:
        command = [
            str(self.args.executable),
            "--codex-home",
            str(self.home),
            "--data-dir",
            str(self.data),
            "--state-dir",
            str(state or self.state),
            *options,
        ]
        process = await asyncio.create_subprocess_exec(
            *command, env=self.env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _stderr = await process.communicate()
        if process.returncode:
            raise RuntimeError(f"packaged command failed with exit {process.returncode}")
        return json.loads(stdout)

    async def window(self, seconds: float, label: str) -> dict[str, Any]:
        assert self.daemon is not None
        self.phase = f"{label}: {seconds:g}s actual Unix-socket window"
        self.say(self.phase)
        before = await self.resource_snapshot()
        peak = sum(value["rss_mib"] for value in before.values())
        began = time.monotonic()
        while time.monotonic() - began < seconds:
            await asyncio.sleep(min(1.0, seconds - (time.monotonic() - began)))
            current = await self.resource_snapshot()
            peak = max(peak, sum(value["rss_mib"] for value in current.values()))
        wall = time.monotonic() - began
        after = await self.resource_snapshot()
        detail = {}
        for name, value in after.items():
            detail[name] = {
                **value,
                "cpu_seconds": value["cpu_seconds"] - before[name]["cpu_seconds"],
                "fd_change": value["fds"] - before[name]["fds"],
                "logical_io": {
                    key: amount - before[name]["logical_io"][key]
                    for key, amount in value["logical_io"].items()
                },
            }
        cpu = sum(value["cpu_seconds"] for value in detail.values())
        return {
            "requested_seconds": seconds,
            "wall_seconds": wall,
            "processes": detail,
            "aggregate": {
                "cpu_seconds": cpu,
                "cpu_percent_one_core": cpu / wall * 100,
                "rss_mib": sum(value["rss_mib"] for value in after.values()),
                "peak_sampled_rss_mib": peak,
                "peak_rss_mib": sum(value["peak_rss_mib"] for value in after.values()),
                "fds": sum(value["fds"] for value in after.values()),
                "logical_io": {
                    key: sum(v["logical_io"][key] for v in detail.values())
                    for key in after["daemon"]["logical_io"]
                },
            },
        }

    async def run(self) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        if any((self.root / name).exists() for name in ("data", "home", "state", "daemon.log")):
            raise ValueError("choose a fresh work directory; existing work is preserved")
        if self.args.fixture:
            fixture = self.args.fixture.resolve()
            manifest = json.loads((fixture / "fixture.json").read_text())
            if manifest.get("content_free") is not True:
                raise ValueError("only a sanitized benchmark fixture is supported")
            await asyncio.to_thread(shutil.copytree, fixture / "data", self.data)
            await asyncio.to_thread(shutil.copytree, fixture / "home", self.home)
        else:
            make_fixture(self.root)
        metadata_counts = None
        if self.args.metadata_fixture:
            metadata_counts = await asyncio.to_thread(make_metadata, self.data, self.home)
        self.original = selected_sessions(self.data)
        self.turn_ids = {
            sid: next(tid for tid, turn in item["turns"].items() if turn.get("end") is None)
            for sid, item in self.original.items()
        }
        self.env = dict(os.environ, NO_COLOR="1")
        self.env.pop("PYTHONPATH", None)
        first_line = self.args.executable.read_text().splitlines()[0]
        if not first_line.startswith("#!/"):
            raise ValueError(
                "pass the packaged Python codex-time entrypoint with an absolute shebang"
            )
        python = first_line[2:]
        build_code = (
            "import codex_time,pathlib,hashlib,json;"
            "p=pathlib.Path(codex_time.__file__).resolve().parent;"
            "h=hashlib.sha256();"
            "[(h.update(str(f.relative_to(p)).encode()),h.update(f.read_bytes())) "
            "for f in sorted(p.rglob('*')) if f.is_file() and f.suffix in ('.py','.json')];"
            "print(json.dumps({'package_path':str(p),'sha256':h.hexdigest()}))"
        )
        build_process = await asyncio.create_subprocess_exec(
            python, "-c", build_code, env=self.env, stdout=asyncio.subprocess.PIPE
        )
        build_raw, _ = await build_process.communicate()
        if build_process.returncode:
            raise RuntimeError("could not inspect the packaged executable's Python environment")
        build = json.loads(build_raw)
        build["installed_package"] = "site-packages" in Path(build["package_path"]).parts
        if not build["installed_package"] and not self.args.allow_source:
            raise ValueError(
                "executable loads an editable source package; install a wheel or use --allow-source"
            )
        self.state.mkdir()
        now = datetime.now(UTC)
        (self.state / "fx-usd-cad.json").write_text(
            dump({"version": 1, "last_success": now.isoformat(), "last_attempt": now.isoformat()})
        )
        wait_start = now - timedelta(seconds=7.5)
        wait_end = wait_start + timedelta(seconds=2.125)
        first_sid = next(iter(self.original))
        source = self.home / "sessions" / f"{first_sid}.jsonl"
        with source.open("a") as output:
            for stamp, kind in [(wait_start, "function_call"), (wait_end, "function_call_output")]:
                payload = {"type": kind, "call_id": "precise-smoke-wait"}
                if kind == "function_call":
                    payload["name"] = "functions.request_user_input"
                output.write(
                    dump(
                        {
                            "timestamp": stamp.isoformat(),
                            "type": "response_item",
                            "payload": payload,
                        }
                    )
                    + "\n"
                )
        journals = {
            name: digest(self.data / name)
            for name in ("quota-observations.jsonl", "usage-observations.jsonl")
        }
        socket = self.root / "observer.sock"
        startup_at = time.monotonic()
        result: dict[str, Any] = {
            "build": build,
            "executable": str(self.args.executable),
            "sample_seconds": self.args.sample_seconds,
            "observed_roots": 5,
            "work_dir": str(self.root),
            "metadata_fixture": metadata_counts,
        }
        async with unix_serve(self.handler, str(socket)), asyncio.timeout(self.args.timeout):
            with (self.root / "daemon.log").open("w") as log:
                self.daemon = await asyncio.create_subprocess_exec(
                    str(self.args.executable),
                    "--codex-home",
                    str(self.home),
                    "--data-dir",
                    str(self.data),
                    "--state-dir",
                    str(self.state),
                    "--socket",
                    str(socket),
                    "daemon",
                    "--sample-seconds",
                    str(self.args.sample_seconds),
                    env=self.env,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=log,
                )
                startup_done = asyncio.Event()
                startup_monitor = asyncio.create_task(
                    startup_workers(self.daemon.pid, startup_done)
                )
                try:
                    await self.until(
                        lambda: self.states_are("working"), timeout=self.args.startup_timeout
                    )
                    if metadata_counts is not None:

                        def names_ready() -> bool:
                            with closing(
                                sqlite3.connect(
                                    (self.state / "index.sqlite").as_uri() + "?mode=ro", uri=True
                                )
                            ) as db:
                                row = db.execute(
                                    "SELECT value FROM meta WHERE key='metadata'"
                                ).fetchone()
                                return bool(
                                    row and json.loads(row[0])["index"].get("pending") is False
                                )

                        await self.until(names_ready, timeout=self.args.startup_timeout)
                    startup_done.set()
                    worker_resources = await startup_monitor
                    daemon_resources = await self.daemon_resources()
                    worker_resources["cumulative_cpu_seconds"] = max(
                        worker_resources["cumulative_cpu_seconds"], daemon_resources["cpu_seconds"]
                    )
                    result["startup"] = {
                        "wall_seconds": time.monotonic() - startup_at,
                        "daemon": daemon_resources,
                        "workers": worker_resources,
                    }
                    events = RolloutEvents(
                        self.home, list(self.original), self.args.rollout_event_seconds
                    )
                    self.rollout_events = events
                    producer = asyncio.create_task(events.run()) if events.interval else None
                    try:
                        label = (
                            "Five roots with rollout events"
                            if producer
                            else "Five quiet roots working"
                        )
                        result["active"] = await self.window(self.args.duration, label)
                    finally:
                        if producer is not None:
                            producer.cancel()
                            try:
                                await producer
                            except asyncio.CancelledError:
                                pass
                    result["rollout_events"] = events.report()
                    if producer is not None:
                        self.phase = "Waiting for final synthetic rollout ingestion"
                        self.say(self.phase)
                        before = await self.resource_snapshot()
                        draining_at = time.monotonic()
                        await self.until(
                            lambda: self.rollout_tails_consumed(events),
                            timeout=2 * self.args.sample_seconds + 10,
                        )
                        after = await self.resource_snapshot()
                        result["active_tail_drain"] = {
                            "wall_seconds": time.monotonic() - draining_at,
                            "cpu_seconds_by_process": {
                                name: row["cpu_seconds"] - before[name]["cpu_seconds"]
                                for name, row in after.items()
                            },
                            "daemon_logical_io_delta": {
                                key: value - before["daemon"]["logical_io"][key]
                                for key, value in after["daemon"]["logical_io"].items()
                            },
                        }
                        result["rollout_events"]["tail_sources_consumed"] = len(events.tail_offsets)
                    if self.args.idle_seconds:
                        self.state_name = "idle"
                        await self.until(
                            lambda: self.states_are("idle"),
                            timeout=2 * self.args.sample_seconds + 10,
                        )
                        result["idle"] = await self.window(
                            self.args.idle_seconds, "Five idle roots"
                        )
                        self.state_name = "working"
                    cycles = {
                        "waiting_observed": False,
                        "unknown_observed": False,
                        "reconnected": False,
                    }
                    if not self.args.skip_cycles:
                        self.phase = "Known wait and real socket reconnect"
                        self.say(self.phase)
                        self.state_name = "waiting"
                        await self.until(
                            lambda: self.states_are("waiting"),
                            timeout=2 * self.args.sample_seconds + 10,
                        )
                        cycles["waiting_observed"] = True
                        self.state_name = "working"
                        self.drop_once = True
                        await self.until(
                            lambda: self.states_are("unknown"),
                            timeout=2 * self.args.sample_seconds + 10,
                        )
                        cycles["unknown_observed"] = True
                        await self.until(
                            lambda: self.states_are("working"),
                            timeout=2 * self.args.sample_seconds + 10,
                        )
                        cycles["reconnected"] = self.connections >= 2
                    result["cycles"] = cycles
                    observations = read_checkpoint(self.state)["observations"]
                    result["runtime_uncertainty_seconds"] = max(
                        o["uncertainty_seconds"] for o in observations.values()
                    )
                    probe = self.root / "health-probe"
                    probe.mkdir()
                    (probe / "checkpoint.json").write_text(
                        dump(
                            {
                                **read_checkpoint(self.state),
                                "heartbeat": (
                                    datetime.now(UTC) - timedelta(seconds=65)
                                ).isoformat(),
                            }
                        )
                    )
                    result["health_at_65_seconds"] = await self.cli("health", "--json", state=probe)
                    completion = datetime.now(UTC).isoformat()
                    for sid, tid in self.turn_ids.items():
                        with (self.home / "sessions" / f"{sid}.jsonl").open("a") as output:
                            output.write(
                                dump(
                                    {
                                        "timestamp": completion,
                                        "type": "event_msg",
                                        "payload": {"type": "task_complete", "turn_id": tid},
                                    }
                                )
                                + "\n"
                            )
                    await self.until(
                        lambda: all(
                            session(self.data, sid)["turns"][tid].get("end") is not None
                            and instant(session(self.data, sid)["turns"][tid]["end"])
                            == instant(completion)
                            for sid, tid in self.turn_ids.items()
                        ),
                        timeout=2 * self.args.sample_seconds + 10,
                    )
                    result["completion_timestamp"] = completion
                finally:
                    startup_done.set()
                    await startup_monitor
                    if self.daemon.returncode is None:
                        self.daemon.terminate()
                        await asyncio.wait_for(self.daemon.wait(), timeout=10)
                result["daemon_exit_status"] = self.daemon.returncode
        final = {sid: session(self.data, sid) for sid in self.original}
        precise = final[first_sid]["turns"][self.turn_ids[first_sid]]["waits"]
        known_wait_preserved = any(
            instant(span["start"]) == wait_start and instant(span["end"]) == wait_end
            for span in precise
        )
        lifecycle = all(
            instant(final[sid]["turns"][tid]["start"]) == instant(turn["start"])
            and (
                turn.get("end") is None
                or instant(final[sid]["turns"][tid]["end"]) == instant(turn["end"])
            )
            and final[sid]["turns"][tid]["cwd"] == turn["cwd"]
            for sid, item in self.original.items()
            for tid, turn in item["turns"].items()
        )
        result["evidence"] = {
            "precise_wait_seconds": 2.125 if known_wait_preserved else None,
            "lifecycle_preserved": lifecycle,
            "token_journals_unchanged": all(
                digest(self.data / name) == value for name, value in journals.items()
            ),
            "sampling_quality": final[first_sid]["turns"][self.turn_ids[first_sid]]["quality"],
        }
        result["rpc_counts"] = dict(self.calls)
        result["connections"] = self.connections
        result["max_poll_interval_seconds"] = self.max_poll_interval
        misses = []
        if self.args.duration < 300:
            misses.append("active window shorter than five-minute acceptance requirement")
        if self.args.sample_seconds != 60:
            misses.append("test sampling override; minute cadence performance remains unvalidated")
        if not build["installed_package"]:
            misses.append(
                "editable source executable; installed-wheel evidence remains unvalidated"
            )
        aggregate = result["active"]["aggregate"]
        if aggregate["cpu_percent_one_core"] > 2:
            misses.append("aggregate active CPU exceeded 2% of one core")
        if aggregate["rss_mib"] > 128:
            misses.append("aggregate active RSS exceeded 128 MiB")
        if (
            not lifecycle
            or not known_wait_preserved
            or not result["evidence"]["token_journals_unchanged"]
        ):
            raise RuntimeError("packaged daemon failed precise evidence preservation")
        if result["daemon_exit_status"] != 0:
            raise RuntimeError("packaged daemon failed graceful shutdown")
        result["unvalidated_or_misses"] = misses
        result["notes"] = [
            "Aggregate includes daemon and mock-server harness process.",
            "Startup/backfill resources are separate from the active window.",
            "OS notification ingestion is exercised.",
            (
                "Reconnect cycles skipped (--skip-cycles)."
                if self.args.skip_cycles
                else "Actual Unix reconnect cycles are exercised."
            ),
            "The health freshness probe uses a separate disposable runtime directory.",
        ]
        (self.root / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        return result


async def run(args: argparse.Namespace) -> dict[str, Any]:
    smoke = Smoke(args)
    smoke.say(smoke.phase)
    progress = asyncio.create_task(smoke.progress())
    try:
        return await smoke.run()
    finally:
        progress.cancel()
        try:
            await progress
        except asyncio.CancelledError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument(
        "--fixture", type=Path, help="original sanitized benchmark fixture directory"
    )
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--duration", type=float, default=300)
    parser.add_argument("--idle-seconds", type=float, default=0)
    parser.add_argument(
        "--rollout-event-seconds",
        type=float,
        default=0,
        help="append ignored 4KiB synthetic messages at this active-work interval (0 disables)",
    )
    parser.add_argument("--sample-seconds", type=float, default=60)
    parser.add_argument("--startup-timeout", type=float, default=600)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--skip-cycles", action="store_true")
    parser.add_argument("--allow-source", action="store_true", help="test-only editable executable")
    parser.add_argument(
        "--metadata-fixture",
        action="store_true",
        help="stream matching thread/turn/name history into the synthetic Codex home",
    )
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    args.executable = args.executable.expanduser().absolute()
    args.work_dir = args.work_dir or Path(tempfile.mkdtemp(prefix="codex-service-smoke-"))
    if not math.isfinite(args.rollout_event_seconds) or args.rollout_event_seconds < 0:
        parser.error("rollout event interval must be finite and nonnegative (0 disables)")
    if not 0 < args.sample_seconds <= 60 or min(args.duration, args.idle_seconds) < 0:
        parser.error("sampling must be in (0,60] seconds and windows nonnegative")
    try:
        report = asyncio.run(run(args))
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(("" if args.plain else "❌ ") + f"Service smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(("" if args.plain else "✅ ") + "Packaged service smoke completed")
        measured = report["active"]["aggregate"]
        print(f"Active CPU: {measured['cpu_percent_one_core']:.3f}% of one core")
        print(f"Aggregate RSS: {measured['rss_mib']:.2f} MiB")
        print(f"Actual sampling uncertainty: {report['runtime_uncertainty_seconds']:.3f}s")
        if report["rollout_events"]["enabled"]:
            events = report["rollout_events"]
            print(
                f"Synthetic rollout events: {events['events_written']} records, "
                f"{events['bytes_written']} bytes"
            )
            drain = report["active_tail_drain"]
            cpu = drain["cpu_seconds_by_process"]
            io = drain["daemon_logical_io_delta"]
            print(
                ("" if args.plain else "⏳ ")
                + f"Post-active drain: {drain['wall_seconds']:.3f}s wall (outside active window)"
            )
            print(
                f"  Daemon CPU: {cpu['daemon']:.3f}s; "
                f"harness CPU: {cpu['mock_server_and_harness']:.3f}s"
            )
            print(f"  Logical I/O: read {io['rchar']} B, write {io['wchar']} B (daemon)")
        print(f"Evidence: lifecycle and 2.125s precise wait preserved; artifacts: {args.work_dir}")
        for finding in report["unvalidated_or_misses"]:
            print(("" if args.plain else "⚠️ ") + finding)


if __name__ == "__main__":
    main()
