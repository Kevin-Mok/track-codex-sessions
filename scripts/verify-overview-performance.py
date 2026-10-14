#!/usr/bin/env python3
"""Compare the installed build with a temporary, schema-compatible optimization.

Freeze copies of accounting inputs, run identical CLI reports before/after,
and require exact JSON parity. Never install or write live tracker records.
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
    repo = Path(__file__).resolve().parents[1]
    executable = Path(shutil.which("codex-time") or "")
    if not executable.is_file():
        parser.error("installed codex-time is required")
    python = executable.read_text().splitlines()[0].removeprefix("#!")
    prefix = "" if args.plain else "⏳ "

    def run(command: list[str], env: dict[str, str] | None = None) -> bytes:
        started = time.perf_counter()
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            process = subprocess.Popen(command, stdout=out, stderr=err, env=env)
            while True:
                try:
                    code = process.wait(timeout=5)
                    break
                except subprocess.TimeoutExpired:
                    print(f"{prefix}Report running: {time.perf_counter()-started:.0f}s elapsed",
                          flush=True)
            out.seek(0)
            if code:
                err.seek(0)
                # Do not print report data or raw diagnostics by default.
                raise RuntimeError(f"report exited {code}; no live records changed")
            return out.read()

    package = Path(run([python, "-c", "import codex_time; print(codex_time.__path__[0])"])
                   .decode().strip())
    with tempfile.TemporaryDirectory(prefix="cto-verification-") as temporary:
        temp = Path(temporary)
        baseline = temp / "before" / "codex_time"
        optimized = temp / "after" / "codex_time"
        shutil.copytree(package, baseline, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(baseline, optimized)
        shutil.copyfile(repo / "src/codex_time/work_period.py", optimized / "work_period.py")
        replacements = {
            "burn.py": [
                ("from codex_time.models import AttributedSegment, Ledger, QuotaObservation",
                 "from codex_time.models import AttributedSegment, Ledger, QuotaObservation\n"
                 "from codex_time.work_period import has_work_in_period"),
                ("            for session in ledger.sessions.values()\n            for span",
                 "            for session in ledger.sessions.values()\n"
                 "            if has_work_in_period(session, start, end)\n            for span"),
            ],
            "model_usage.py": [
                ("from codex_time.reporting import selected_sessions",
                 "from codex_time.reporting import selected_sessions\n"
                 "from codex_time.work_period import has_work_in_period"),
                ("    buckets: dict[tuple[str | None, str | None], Bucket] = {}",
                 "    zone = ZoneInfo(timezone_name)\n"
                 "    period_start = datetime.combine(start, datetime.min.time(), zone)"
                 ".astimezone(UTC)\n"
                 "    period_end = datetime.combine(end + timedelta(days=1), "
                 "datetime.min.time(), zone).astimezone(UTC)\n"
                 "    buckets: dict[tuple[str | None, str | None], Bucket] = {}"),
                ("        for span in attributed_segments(session):",
                 "        if not has_work_in_period(session, period_start, period_end):\n"
                 "            continue\n        for span in attributed_segments(session):"),
            ],
        }
        for filename, changes in replacements.items():
            path = optimized / filename
            source = path.read_text()
            if "from codex_time.work_period import has_work_in_period" in source:
                # After compatible activation, recover the full accounting baseline
                # by removing only this known conservative guard from its copy.
                guard = ("            if has_work_in_period(session, start, end)\n"
                         if filename == "burn.py" else
                         "        if not has_work_in_period(session, period_start, period_end):\n"
                         "            continue\n")
                if source.count(guard) != 1:
                    raise RuntimeError(f"installed {filename} filter differs; refusing patch")
                (baseline / filename).write_text(source.replace(guard, ""))
                continue
            old_import = "from datetime import UTC, date, datetime\n"
            if filename == "model_usage.py" and old_import in source:
                source = source.replace("from datetime import UTC, date, datetime\n",
                                        "from datetime import UTC, date, datetime, timedelta\n")
            for old, new in changes:
                if source.count(old) != 1:
                    raise RuntimeError(f"installed {filename} differs; refusing speculative patch")
                source = source.replace(old, new)
            path.write_text(source)
        data = temp / "data"
        state = temp / "state"
        data.mkdir()
        state.mkdir()
        inventory: dict[str, dict[str, object]] = {}
        for filename in ("ledger.json", "quota-observations.jsonl", "usage-observations.jsonl"):
            source = args.data_dir.expanduser().resolve() / filename
            if source.exists():
                shutil.copyfile(source, data / filename)
                frozen = (data / filename).read_bytes()
                inventory[filename] = {"bytes": len(frozen),
                                       "sha256": hashlib.sha256(frozen).hexdigest()}
        # Runtime FX is also a report input. Discover its canonical path via this build.
        runtime = Path(run([python, "-c", "from pathlib import Path; "
                            "from codex_time.storage import Store; "
                            f"print(Store(Path({str(args.data_dir)!r})).runtime)"])
                       .decode().strip())
        if (runtime / "fx-usd-cad.json").exists():
            shutil.copyfile(runtime / "fx-usd-cad.json", state / "fx-usd-cad.json")
        raw = json.loads((data / "ledger.json").read_bytes())
        print(json.dumps({"build": str(package), "ledger_version": raw["version"],
                          "sessions": len(raw["sessions"]),
                          "turns": sum(len(s["turns"]) for s in raw["sessions"].values()),
                          "inputs": inventory}), flush=True)
        frozen_now = datetime.now(UTC).isoformat()
        entry = (
            "from datetime import datetime; "
            "import importlib.util; "
            "spec=importlib.util.find_spec('codex_time.fx'); "
            "exec(\"from codex_time import fx\\nfx._now = lambda value=None: "
            f"value or datetime.fromisoformat('{frozen_now}')\") if spec else None; "
            "from codex_time.cli import main; raise SystemExit(main())"
        )
        reports: dict[str, object] = {}
        timings: dict[str, list[float]] = {}
        for label, location in (("before", baseline.parent), ("after", optimized.parent)):
            timings[label] = []
            env = {**os.environ, "PYTHONPATH": str(location), "PYTHONDONTWRITEBYTECODE": "1"}
            options = ["--data-dir", str(data), "--state-dir", str(state),
                       "--timezone", args.timezone, "overview", args.period, "--json"]
            if args.date:
                options += ["--date", args.date]
            for number in range(args.runs):
                started = time.perf_counter()
                output = run([python, "-c", entry, *options], env)
                elapsed = time.perf_counter() - started
                parsed = json.loads(output)
                if label in reports and reports[label] != parsed:
                    raise RuntimeError("same-input report changed between runs")
                reports[label] = parsed
                timings[label].append(elapsed)
                print(json.dumps({"phase": label, "run": number + 1, "seconds": elapsed}),
                      flush=True)
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
