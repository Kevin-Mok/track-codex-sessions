#!/usr/bin/env python3
"""Compare installed and optimized reports on identical frozen accounting inputs.

Copy legacy or partitioned data and FX, prepare an isolated disposable index,
then compare complete JSON reports and first/repeated unprofiled timings.
Never install packages or write live tracker data.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

INPUT_NAMES = (
    "layout.json", "ledger.json", "quota-observations.jsonl", "usage-observations.jsonl",
    "legacy-quota-observations.jsonl", "legacy-usage-observations.jsonl",
)
TOKEN_GUARD_PARTS = (
    ("from datetime import UTC, date, datetime, timedelta\n",
     "from datetime import date, datetime\n"),
    ("from codex_time.work_period import has_work_in_period\n", ""),
    ("    start = datetime.combine(first, datetime.min.time(), zone).astimezone(UTC)\n"
     "    end = datetime.combine(last + timedelta(days=1), datetime.min.time(), zone)"
     ".astimezone(UTC)\n", ""),
    ("        if not has_work_in_period(session, start, end):\n            continue\n", ""),
)
CLI_IMPORT = "from codex_time.overview import overview_report\n"
CLI_CACHE_IMPORT = "from codex_time.overview_cache import cached_overview\n"
CLI_CALL = (
    "                overview_data = overview_report(\n"
    "                    store.load(),\n"
    "                    fx=read_fx(store.runtime),\n"
)
CLI_CACHE_CALL = (
    "                overview_data = cached_overview(\n"
    "                    store,\n"
)


def without_token_guard(source: str) -> str:
    """Recover the baseline by removing only this optimization's known timing guard."""
    if "from codex_time.work_period import has_work_in_period\n" not in source:
        return source
    for old, new in TOKEN_GUARD_PARTS:
        if source.count(old) != 1:
            raise RuntimeError("installed token guard differs; refusing speculative patch")
        source = source.replace(old, new)
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument("--period", choices=["day", "week", "month", "all"], default="day")
    parser.add_argument("--date")
    parser.add_argument("--timezone", default="America/Toronto")
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".codex-timetrace")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--details", action="store_true", help="include failure diagnostics")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    if args.period == "all" and args.date:
        parser.error("--date cannot be combined with all")
    repo = Path(__file__).resolve().parents[1]
    executable = Path(shutil.which("codex-time") or "")
    if not executable.is_file():
        parser.error("installed codex-time is required")
    python = executable.read_text().splitlines()[0].removeprefix("#!")
    prefix = "" if args.plain else "⏳ "

    def progress(message: str) -> None:
        print(prefix + message, flush=True)

    def run(command: list[str], env: dict[str, str] | None = None,
            activity: str = "Report") -> bytes:
        started = time.perf_counter()
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            process = subprocess.Popen(command, stdout=out, stderr=err, env=env)
            while True:
                try:
                    code = process.wait(timeout=5)
                    break
                except subprocess.TimeoutExpired:
                    progress(f"{activity} running: {time.perf_counter()-started:.0f}s elapsed")
            out.seek(0)
            if code:
                if args.details:
                    err.seek(0)
                    print(err.read().decode(errors="replace"), file=sys.stderr)
                raise RuntimeError(f"{activity.lower()} exited {code}")
            return out.read()

    package = Path(run([python, "-c", "import codex_time; print(codex_time.__path__[0])"])
                   .decode().strip())
    source_package = repo / "src/codex_time"
    for name in (
        "models.py", "overview.py", "periods.py", "burn.py", "model_usage.py", "fx.py",
        "pricing.py", "pricing-v1.json", "accounting.py", "work_period.py",
        "incremental_storage.py",
    ):
        if (package / name).read_bytes() != (source_package / name).read_bytes():
            raise RuntimeError(f"installed {name} differs; dependency compatibility is unproven")
    installed_tokens = (package / "token_reporting.py").read_text()
    tokens = (source_package / "token_reporting.py").read_text()
    if without_token_guard(installed_tokens) != without_token_guard(tokens):
        raise RuntimeError("installed token reporting differs beyond the known guard")
    run([python, "-c", "import inspect; from codex_time.storage import Store; "
         "from codex_time.incremental_storage import IndexedStore; "
         "assert 'include_evidence' in inspect.signature(Store.load).parameters; "
         "assert callable(Store._stat_key); assert callable(IndexedStore._stamp)"])
    with tempfile.TemporaryDirectory(prefix="cto-verification-") as temporary:
        temp = Path(temporary)
        baseline = temp / "before" / "codex_time"
        optimized = temp / "after" / "codex_time"
        shutil.copytree(package, baseline, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(baseline, optimized)
        for name in ("overview_cache.py", "overview_read.py", "token_reporting.py"):
            shutil.copyfile(source_package / name, optimized / name)
        (baseline / "token_reporting.py").write_text(without_token_guard(installed_tokens))
        cli_path = optimized / "cli.py"
        cli_source = cli_path.read_text()
        already_optimized = CLI_CACHE_IMPORT in cli_source
        if already_optimized:
            if cli_source.count(CLI_CACHE_IMPORT) != 1 or cli_source.count(CLI_CACHE_CALL) != 1:
                raise RuntimeError("installed cached overview call differs; refusing patch")
        else:
            for old, new in ((CLI_IMPORT, CLI_CACHE_IMPORT), (CLI_CALL, CLI_CACHE_CALL)):
                if cli_source.count(old) != 1:
                    raise RuntimeError(
                        "installed overview call differs; refusing speculative patch"
                    )
                cli_source = cli_source.replace(old, new)
            cli_path.write_text(cli_source)

        data, state = temp / "data", temp / "state"
        data.mkdir()
        state.mkdir()
        source_root = args.data_dir.expanduser().resolve()
        paths = [source_root / name for name in INPUT_NAMES]
        paths.extend(sorted((source_root / "sessions").glob("*.json")))
        progress("Freezing complete accounting inputs and runtime FX")
        copied = 0
        last_progress = time.perf_counter()
        for source in paths:
            if not source.exists():
                continue
            destination = data / source.relative_to(source_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Freeze journals at their initial length so ongoing appends cannot
            # extend copying indefinitely. Both builds read the same frozen prefix.
            with source.open("rb") as incoming, destination.open("wb") as outgoing:
                remaining = os.fstat(incoming.fileno()).st_size
                while remaining:
                    block = incoming.read(min(remaining, 1024 * 1024))
                    if not block:
                        raise RuntimeError("accounting source shrank while freezing inputs")
                    outgoing.write(block)
                    copied += len(block)
                    remaining -= len(block)
                    if time.perf_counter() - last_progress >= 5:
                        progress(f"Freezing inputs: {copied / 1024**2:.1f} MiB copied")
                        last_progress = time.perf_counter()
        if not (data / "layout.json").exists() and not (data / "ledger.json").exists():
            raise RuntimeError("data directory has neither a ledger nor a partitioned layout")
        runtime = Path(run([python, "-c", "from pathlib import Path; "
                            "from codex_time.storage import Store; "
                            f"print(Store(Path({str(source_root)!r})).runtime)"])
                       .decode().strip())
        if (runtime / "fx-usd-cad.json").exists():
            shutil.copyfile(runtime / "fx-usd-cad.json", state / "fx-usd-cad.json")

        env = {**os.environ, "PYTHONPATH": str(optimized.parent),
               "PYTHONDONTWRITEBYTECODE": "1", "CLI_PLAIN": "1" if args.plain else "0"}
        if (data / "layout.json").exists():
            progress("Preparing disposable evidence index on frozen copies")
            setup = f"""
import fcntl
from contextlib import contextmanager
from pathlib import Path
from codex_time.storage import Store
from codex_time.incremental_storage import IndexedStore
# Keep real locking and writer validation inside the isolated state directory;
# the normal real-home lock location can be read-only under Codex.
@contextmanager
def isolated_writer(self):
    with (self.runtime / 'frozen-writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self._locked = True
        try:
            yield
        finally:
            self._locked = False
            fcntl.flock(lock, fcntl.LOCK_UN)
Store.writer = isolated_writer
with IndexedStore(Path({str(data)!r}), Path({str(state)!r})):
    pass
"""
            run([python, "-c", setup], env, "Frozen-copy index preparation")

        inventory: dict[str, dict[str, object]] = {}
        session_digest = hashlib.sha256()
        session_count = session_bytes = turns = 0
        for path in sorted((data / "sessions").glob("*.json")):
            raw = path.read_bytes()
            session_digest.update(json.dumps([path.name, hashlib.sha256(raw).hexdigest()]).encode())
            session_count += 1
            session_bytes += len(raw)
            turns += len(json.loads(raw)["turns"])
        for name in (*INPUT_NAMES, "fx-usd-cad.json"):
            path = (state if name == "fx-usd-cad.json" else data) / name
            if not path.exists():
                continue
            digest = hashlib.sha256()
            with path.open("rb") as incoming:
                while block := incoming.read(1024 * 1024):
                    digest.update(block)
                    if time.perf_counter() - last_progress >= 5:
                        progress(f"Verifying frozen input inventory: {name}")
                        last_progress = time.perf_counter()
            inventory[name] = {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}
        layout = json.loads((data / "layout.json").read_bytes()) if (
            data / "layout.json").exists() else None
        if layout is None:
            ledger = json.loads((data / "ledger.json").read_bytes())
            session_count = len(ledger["sessions"])
            turns = sum(len(session["turns"]) for session in ledger["sessions"].values())
        else:
            inventory["sessions/*.json"] = {
                "files": session_count, "bytes": session_bytes,
                "sha256": session_digest.hexdigest(),
            }
        print(json.dumps({"build": str(package), "layout_version": layout["version"] if layout
                          else None, "sessions": session_count, "turns": turns,
                          "inputs": inventory}), flush=True)

        frozen_now = datetime.now(UTC).isoformat()
        entry = f"""
import importlib
from datetime import datetime
from codex_time import cli
frozen = datetime.fromisoformat({frozen_now!r})
class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)
for name in ('fx', 'overview', 'periods', 'burn', 'model_usage', 'token_reporting',
             'overview_cache'):
    try:
        module = importlib.import_module('codex_time.' + name)
    except ModuleNotFoundError:
        continue
    if hasattr(module, 'datetime'):
        module.datetime = Clock
from codex_time import fx
fx._now = lambda value=None: value or frozen
if __BASELINE__ and {already_optimized!r}:
    from codex_time.overview import overview_report
    cli.cached_overview = lambda store, **kwargs: overview_report(
        store.load(), fx=fx.read_fx(store.runtime), **kwargs)
raise SystemExit(cli.main())
"""
        reports: dict[str, object] = {}
        timings: dict[str, list[float]] = {}
        for label, location in (("before", baseline.parent), ("after", optimized.parent)):
            timings[label] = []
            report_env = {**env, "PYTHONPATH": str(location)}
            options = ["--data-dir", str(data), "--state-dir", str(state),
                       "--timezone", args.timezone, "overview", args.period, "--json"]
            if args.date:
                options += ["--date", args.date]
            for number in range(args.runs):
                progress(f"Running {label} report {number + 1}/{args.runs}")
                started = time.perf_counter()
                output = run([python, "-c", entry.replace("__BASELINE__", repr(label == "before")),
                              *options], report_env, f"{label.capitalize()} report")
                elapsed = time.perf_counter() - started
                parsed = json.loads(output)
                if label in reports and reports[label] != parsed:
                    raise RuntimeError("same-input report changed between runs")
                reports[label] = parsed
                timings[label].append(elapsed)
                print(json.dumps({"phase": label, "run": number + 1,
                                  "seconds": elapsed}), flush=True)
        if reports["before"] != reports["after"]:
            raise RuntimeError("optimized report differs from full computation")
        print(("" if args.plain else "✅ ") + "Exact full-report parity; temporary overlay only.")
        print(json.dumps({"seconds": timings, "installation_changed": False}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        prefix = "" if "--plain" in sys.argv else "⚠️ "
        print(f"{prefix}Verification failed: {error}. No live records changed.", file=sys.stderr)
        if "--details" in sys.argv:
            traceback.print_exc()
        raise SystemExit(2) from None
