#!/usr/bin/env python3
"""Compare deployed and optimized CLI reports on disposable content-free history.

The default fixture covers exact timestamps, waits, concurrent roots, children,
renames, cwd changes, midnight/DST, model/reasoning evidence, token counters and
cached FX. Use --fixture with a sanitized benchmark directory containing data/
and home/. Inputs are copied; production stores and services are never opened.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = (ROOT.parent / "token-cost-reporting" if ROOT.parent.name == ".worktrees"
                    else ROOT / ".worktrees" / "token-cost-reporting")
AT = datetime(2026, 10, 14, 15, tzinfo=UTC)
LARGE_COUNTER = 9_007_199_254_741_001
ALIASES = {"burn": "allowance", "models": "model-time", "day": "projects",
           "list": "sessions", "report": "history"}


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def stamp(seconds: float, base: datetime = AT) -> str:
    return (base + timedelta(seconds=seconds)).isoformat()


def generate_fixture(destination: Path) -> dict[str, object]:
    """Hand-checked evidence, including integers beyond JavaScript precision."""
    data, home = destination / "data", destination / "home"
    data.mkdir(parents=True)
    (home / "sessions").mkdir(parents=True)
    sessions: dict[str, object] = {}
    definitions: list[
        tuple[str, str, bool, bool, list[tuple[str, float, float, str, str | None, datetime]]]
    ] = [
        ("alpha", "/fixture/a", False, False,
         [("t1", .125, 60.875, "/fixture/a", "medium", AT),
          ("t2", 61.125, 100.875, "/fixture/b", None, AT)]),
        ("beta", "/fixture/a", False, False,
         [("b1", 25.25, 80.75, "/fixture/a", "low", AT)]),
        ("child", "/fixture/a", False, True,
         [("c1", 5.1, 110.2, "/fixture/a", "high", AT)]),
        ("midnight", "/fixture/c", True, False,
         [("m1", .25, 2.75, "/fixture/c", "medium",
           datetime(2026, 10, 15, 3, 59, 59, tzinfo=UTC))]),
        ("dst", "/fixture/c", True, False,
         [("d1", .125, 2.625, "/fixture/c", "medium",
           datetime(2026, 11, 1, 5, 59, 59, tzinfo=UTC))]),
        ("review", "/fixture/a", False, False,
         [("r1", 120.125, 124.25, "/fixture/a", "high", AT)]),
    ]
    for sid, cwd, archived, child, turns in definitions:
        records = []
        values: dict[str, object] = {}
        first = stamp(turns[0][1], turns[0][5])
        records.append({"timestamp": first, "type": "session_meta", "payload": {
            "id": sid, "cwd": cwd, "source": "subagent" if child else "cli",
            **({"parent_thread_id": "alpha"} if child else {}),
        }})
        for tid, start, end, directory, effort, base in turns:
            began, ended = stamp(start, base), stamp(end, base)
            model = "codex-auto-review" if sid == "review" else "gpt-4.1"
            contexts = [] if effort is None else [{
                "at": began, "model_id": model, "reasoning_level": effort,
            }]
            if sid == "alpha" and tid == "t1":
                contexts.append({"at": stamp(30), "model_id": model, "reasoning_level": "high"})
            waits = ([{"start": stamp(10.25), "end": stamp(20.75)}]
                     if sid == "alpha" and tid == "t1" else [])
            values[tid] = {"id": tid, "cwd": directory, "start": began, "end": ended,
                           "model_contexts": contexts, "waits": waits,
                           "coverage": [{"start": began, "end": ended}],
                           "quality": [], "sampling_uncertainty_seconds": 1,
                           "outcome": "task_complete", "provenance": ["rollout"]}
            records.append({"timestamp": began, "type": "event_msg",
                            "payload": {"type": "task_started", "turn_id": tid}})
            records.append({"timestamp": began, "type": "turn_context", "payload": {
                "turn_id": tid, "cwd": directory,
                **({"model": model, "effort": effort} if effort is not None else {}),
            }})
            for context in contexts[1:]:
                records.append({"timestamp": context["at"], "type": "turn_context", "payload": {
                    "turn_id": tid, "cwd": directory, "model": model, "effort": "high",
                }})
            for wait in waits:
                records.extend([
                    {"timestamp": wait["start"], "type": "response_item", "payload": {
                        "type": "function_call", "name": "request_user_input", "call_id": "w1",
                    }},
                    {"timestamp": wait["end"], "type": "response_item", "payload": {
                        "type": "function_call_output", "call_id": "w1",
                    }},
                ])
            records.append({"timestamp": ended, "type": "event_msg",
                            "payload": {"type": "task_complete", "turn_id": tid}})
        sessions[sid] = {"id": sid, "cwd": cwd, "title": f"Synthetic {sid}",
                         "created": first, "updated": ended, "archived": archived,
                         "is_child": child, "parent_id": "alpha" if child else None,
                         "turns": values, "quality": []}
        rollout_dir = home / ("archived_sessions" if archived else "sessions")
        rollout_dir.mkdir(exist_ok=True)
        records.sort(key=lambda record: str(record["timestamp"]))
        (rollout_dir / f"{sid}.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in records)
        )
    usage: list[dict[str, object]] = []
    for i, sid in enumerate(("alpha", "beta", "child", "review", "midnight", "dst")):
        amount = LARGE_COUNTER if sid == "alpha" else 100 + i
        counts = {"input_tokens": amount, "cached_input_tokens": 20,
                  "cache_write_input_tokens": 0, "output_tokens": 17,
                  "reasoning_output_tokens": 6, "total_tokens": amount + 17}
        usage.append({"id": f"fixture-usage-{sid}", "session_id": sid,
                      "at": stamp(45 + i), "cwd": "/fixture/a",
                      "model_id": "codex-auto-review" if sid == "review" else "gpt-4.1",
                      "cumulative": counts, "last_usage": counts, "delta": counts,
                      "request_input_tokens": amount, "diagnostics": []})
    quota = [{"at": stamp(second), "limit_id": "codex", "plan_type": "fixture",
              "bucket": "secondary", "window_minutes": 10080,
              "resets_at": 2_000_000_000, "used_percent": percentage}
             for second, percentage in ((0, 10.0), (40, 11.0), (80, 12.0), (130, 13.0))]
    dump(data / "ledger.json", {"version": 4, "sessions": sessions,
                                "quota_observations": quota, "usage_observations": usage,
                                "diagnostics": []})
    (home / "session_index.jsonl").write_text(json.dumps({
        "id": "alpha", "thread_name": "Renamed synthetic root",
    }) + "\n")
    manifest = {"counts": {"sessions": 6, "turns": 7, "usage": 6, "quota": 4},
                "content_free": True, "selected_date": "2026-10-14"}
    dump(destination / "fixture.json", manifest)
    return manifest


def normalize(value: object) -> object:
    """Ignore only elapsed FX cache age, which changes between fresh processes."""
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items() if key != "check_age_seconds"}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def worker(work: Path) -> int:
    from codex_time.incremental_storage import IndexedStore
    from codex_time.ingest import RolloutReader
    from codex_time.metadata import refresh_metadata

    peak_cache, batches = 0, 0
    with IndexedStore(work / "data", work / "state", cache_size=2) as indexed:
        reader = RolloutReader(work / "home", backend=indexed)
        paths = reader.source_paths()
        while batch := list(itertools.islice(paths, 128)):
            pending = batch
            while pending:
                pending = reader.scan_paths(indexed.ledger, pending, max_records=3)
                indexed.flush()
                peak_cache = max(peak_cache, indexed.cached_sessions)
                batches += 1
        refresh_metadata(work / "home", indexed.ledger, row_changed=indexed.row_changed)
        reader.reconcile_contexts(indexed.ledger)
        indexed.flush()
        latest = indexed.previous_usage("alpha", datetime(2100, 1, 1, tzinfo=UTC))
        result = {"backup_verified": indexed.verify_backup(), "batches": batches,
                  "peak_cached_sessions": peak_cache, "cache_limit": 2,
                  "large_counter": (latest.delta.input_tokens
                                    if latest is not None and latest.delta is not None else None)}
    print(json.dumps(result))
    return 0


class Runner:
    def __init__(self, plain: bool) -> None:
        self.plain = plain

    def say(self, message: str) -> None:
        print(("" if self.plain else "🔎 ") + message, file=sys.stderr, flush=True)

    def run(self, command: list[str], *, phase: str, env: dict[str, str], cwd: Path) -> str:
        self.say(phase)
        started = time.monotonic()
        with subprocess.Popen(command, cwd=cwd, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=5)
                    break
                except subprocess.TimeoutExpired:
                    self.say(f"{phase}: {time.monotonic() - started:.0f}s elapsed")
            if process.returncode:
                diagnostic = stderr[-4000:]
                if self.plain:
                    diagnostic = diagnostic.encode("ascii", "replace").decode()
                raise ValueError(f"{phase} failed (exit {process.returncode}): {diagnostic}")
        return stdout

    def env(self, checkout: Path) -> dict[str, str]:
        return dict(os.environ, PYTHONPATH=str(checkout / "src"), NO_COLOR="1", TERM="dumb")

    def cli(self, checkout: Path, work: Path, arguments: list[str]) -> object:
        command = [sys.executable, "-c",
                   "from codex_time.cli import main; raise SystemExit(main())",
                   "--codex-home", str(work / "home"), "--data-dir", str(work / "data"),
                   "--state-dir", str(work / "state"), *arguments]
        output = self.run(command, phase=f"{work.name}: {' '.join(arguments)}",
                          env=self.env(checkout), cwd=work)
        return normalize(json.loads(output)) if "--json" in arguments else output


def code_hash(checkout: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((checkout / "src").rglob("*")):
        if path.is_file() and path.suffix in (".py", ".json"):
            digest.update(str(path.relative_to(checkout)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def projections(data: Path) -> dict[str, object]:
    return {str(path.relative_to(data)): json.loads(path.read_bytes())
            for directory in ("records", "projects")
            for path in sorted((data / directory).rglob("*.json"))}


def copy_home(source: Path, destination: Path) -> None:
    """Copy only rollout/metadata inputs; auth and machine configuration stay out."""
    destination.mkdir(parents=True)

    def ignore(directory: str, names: list[str]) -> list[str]:
        return [name for name in names if (Path(directory) / name).is_symlink()
                or ((Path(directory) / name).is_file() and not name.endswith(".jsonl"))]

    for name in ("sessions", "archived_sessions"):
        directory = source / name
        if directory.is_dir() and not directory.is_symlink():
            shutil.copytree(directory, destination / name, ignore=ignore)
    index = source / "session_index.jsonl"
    if index.is_file() and not index.is_symlink():
        shutil.copyfile(index, destination / index.name)
    for pattern in ("state_*.sqlite*", "thread_history_*.sqlite*"):
        for path in source.glob(pattern):
            if path.is_file() and not path.is_symlink():
                shutil.copyfile(path, destination / path.name)


def native_reader(runner: Runner, baseline: Path, optimized: Path) -> dict[str, object]:
    executable = shutil.which("timetrace")
    if executable is None:
        return {"status": "skipped", "reason": "timetrace is not installed"}
    if any(Path("/etc/timetrace", name).exists() for name in ("config.yml", "config.yaml")):
        return {"status": "skipped", "reason": "system config prevents assured isolation"}
    dates = sorted({path.parent.name for path in
                    (baseline / "data" / "records").glob("*/*.json")})
    if not dates:
        return {"status": "skipped", "reason": "fixture has no closed native records"}
    first, last = dates[0], dates[-1]
    values = []
    for work in (baseline, optimized):
        native_home = work / "native-home"
        dump(native_home / "unused.json", {})
        config = native_home / ".timetrace"
        config.mkdir()
        (config / "config.yml").write_text("store: " + str(work / "data") + "\n")
        env = dict(os.environ, HOME=str(native_home), TZ="America/Toronto", NO_COLOR="1")
        listed = runner.run([executable, "list", "records", first],
                            phase=f"{work.name}: native list reader", env=env, cwd=native_home)
        output = native_home / "report.json"
        runner.run([executable, "report", "--start", first, "--end", last,
                    "--output", "json", "--file", str(output)],
                   phase=f"{work.name}: native report reader", env=env, cwd=native_home)
        values.append((listed, json.loads(output.read_bytes())))
    return {"status": "passed" if values[0] == values[1] else "failed",
            "list_equal": values[0][0] == values[1][0],
            "report_equal": values[0][1] == values[1][1],
            "reported_nanoseconds": sum(item["total"] for item in values[1][1].values()),
            "date_range": {"from": first, "to": last}}


def run(args: argparse.Namespace, work: Path, runner: Runner) -> dict[str, Any]:
    fixture = args.fixture
    if fixture is None:
        fixture = work / "fixture"
        manifest = generate_fixture(fixture)
    else:
        manifest = json.loads((fixture / "fixture.json").read_bytes()) if (
            fixture / "fixture.json"
        ).exists() else {"content_free": "user-supplied; not independently certified"}
    baseline, optimized = work / "baseline", work / "optimized"
    for destination in (baseline, optimized):
        runner.say(f"Copying sanitized input to {destination.name}")
        shutil.copytree(fixture / "data", destination / "data")
        copy_home(fixture / "home", destination / "home")
        dump(destination / "state" / "fx-usd-cad.json", {
            "version": 1, "rate": "1.375", "observation_date": "2026-10-14",
            "last_attempt": "2026-10-14T00:00:00+00:00",
            "last_success": "2026-10-14T00:00:00+00:00",
        })
    runner.cli(args.baseline, baseline, ["import-history"])
    migration = json.loads(runner.run(
        [sys.executable, str(Path(__file__).resolve()), "--worker", str(optimized)],
        phase="optimized: migrate and reconcile bounded batches",
        env=runner.env(args.optimized), cwd=optimized,
    ))
    date = args.date
    commands = {
        "history": ["history", "--all-dirs", "--archive", "all", "--json"],
        "sessions": ["sessions", "--all-dirs", "--archive", "all", "--json"],
        "model-time": ["model-time", "day", "--date", date, "--json"],
        "allowance": ["allowance", "day", "--date", date, "--json"],
        "overview": ["overview", "all", "--json"],
        "projects": ["projects", "all", "--json"],
        "cwd-history": ["history", "--all-dirs", "--cwd", "/fixture/a", "--json"],
        "child-history": ["history", "--session", "child", "--all-dirs", "--json"],
        "midnight-projects": ["projects", "day", "--date", date, "--json"],
        "dst-projects": ["projects", "day", "--date", "2026-11-01", "--json"],
        "model-csv": ["model-time", "day", "--date", date, "--csv"],
        "allowance-csv": ["allowance", "day", "--date", date, "--csv"],
    }
    old = {name: runner.cli(args.baseline, baseline, command) for name, command in commands.items()}
    new = {name: runner.cli(args.optimized, optimized, command)
           for name, command in commands.items()}
    reports = {name: old[name] == new[name] for name in commands}
    aliases = {}
    for alias, canonical in ALIASES.items():
        command = commands.get(canonical, [canonical, "--json"])
        aliases[alias] = all(
            runner.cli(checkout, destination, [alias, *command[1:]]) == (
                old[canonical] if destination == baseline and canonical in old else
                new[canonical] if canonical in new else
                runner.cli(checkout, destination, command)
            ) for checkout, destination in ((args.baseline, baseline), (args.optimized, optimized))
        )
    runner.run([sys.executable, str(Path(__file__).resolve()), "--worker", str(optimized)],
               phase="optimized: restart and repeat reconciliation",
               env=runner.env(args.optimized), cwd=optimized)
    restart = {"reports_unchanged": all(
        runner.cli(args.optimized, optimized, command) == new[name]
        for name, command in commands.items()
    )}
    native = {"projection_equal": projections(baseline / "data") == projections(optimized / "data"),
              **native_reader(runner, baseline, optimized)}
    assertions: dict[str, bool] = {}
    gaps = ["Interactive session picker/resume is covered by separate runtime smoke checks."]
    if args.fixture is None:
        history = new["history"]
        child = new["child-history"]
        assert isinstance(history, dict) and isinstance(child, dict)
        assertions["precise_wait_subtraction"] = history["total_seconds"] == 154.625
        assertions["child_excluded"] = child["total_seconds"] == 0
        assertions["exact_large_counter"] = migration["large_counter"] == LARGE_COUNTER
        rows = new["sessions"]
        assert isinstance(rows, list)
        assertions["rename_preserved"] = any(
            row["id"] == "alpha" and row["title"] == "Renamed synthetic root"
            for row in rows
        )
    else:
        gaps.append("Supplied fixture: hand-checked default edge-case assertions were not run.")
    if native["status"] == "skipped":
        gaps.append("Native reader skipped: " + str(native["reason"]))
    passed = (all(reports.values()) and all(aliases.values()) and all(assertions.values())
              and bool(migration["backup_verified"]) and bool(restart["reports_unchanged"])
              and bool(native["projection_equal"]) and native["status"] != "failed")
    result: dict[str, Any] = {
        "passed": passed, "fixture": manifest, "reports": reports, "aliases": aliases,
        "assertions": assertions, "migration": migration, "restart": restart, "native": native,
        "normalized_clock_fields": ["check_age_seconds"], "gaps": gaps,
        "baseline": {"checkout": str(args.baseline), "source_sha256": code_hash(args.baseline)},
        "optimized": {"checkout": str(args.optimized), "source_sha256": code_hash(args.optimized)},
        "work_dir": str(work),
    }
    dump(work / "parity-result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--optimized", type=Path, default=ROOT)
    parser.add_argument("--fixture", type=Path, help="sanitized directory with data/ and home/")
    parser.add_argument("--work-dir", type=Path,
                        help="retain disposable data and parity-result.json")
    parser.add_argument("--date", default="2026-10-14")
    parser.add_argument("--plain", action="store_true", help="ASCII progress and summary")
    parser.add_argument("--json", action="store_true", help="only result JSON on stdout")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return worker(args.worker)
    runner = Runner(args.plain)
    try:
        for name in ("baseline", "optimized"):
            checkout = getattr(args, name).resolve()
            setattr(args, name, checkout)
            if not (checkout / "src" / "codex_time" / "cli.py").is_file():
                raise ValueError(f"{name} checkout is missing codex_time CLI source")
        if args.fixture:
            args.fixture = args.fixture.resolve()
            if not all((args.fixture / name).is_dir() for name in ("data", "home")):
                raise ValueError("supplied fixture must contain data/ and home/")
        if args.work_dir:
            args.work_dir.mkdir(parents=True, exist_ok=True)
            result = run(args, args.work_dir.resolve(), runner)
        else:
            with tempfile.TemporaryDirectory(prefix="codex-time-parity-") as temporary:
                result = run(args, Path(temporary), runner)
                result["work_dir"] = "temporary artifacts removed"
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(("" if args.plain else "✅ " if result["passed"] else "⚠️ ")
                  + ("CLI parity passed" if result["passed"] else "CLI parity failed"))
            for gap in result["gaps"]:
                print(("" if args.plain else "ℹ️ ") + gap)
        return 0 if result["passed"] else 1
    except (OSError, ValueError, KeyError) as error:
        runner.say(f"Parity check failed: {error}")
        if args.json:
            print(json.dumps({"passed": False, "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
