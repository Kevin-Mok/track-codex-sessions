#!/usr/bin/env python3
"""Benchmark status cold/warm and prove incremental state equals a full replay.

Rollouts are cloned/copied into temporary storage to freeze live appends. Only
counts/timings are printed; temporary snapshots and private messages are removed.
"""

import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--plain", action="store_true", help="ASCII progress and output")
    args = parser.parse_args()
    started = last = time.monotonic()

    def progress(message: str, *, force: bool = False) -> None:
        nonlocal last
        now = time.monotonic()
        if force or now - last >= 1:
            print(f"{'' if args.plain else '⏳ '}{message} ({now - started:.0f}s elapsed)",
                  file=sys.stderr, flush=True)
            last = now

    repo = Path(__file__).resolve().parent.parent
    env = dict(os.environ, PYTHONPATH=str(repo / "src"))
    try:
        with tempfile.TemporaryDirectory(prefix="codex-time-status-") as temporary:
            root = Path(temporary)
            home = root / "snapshot"
            files = total = 0
            progress("Freezing read-only rollout snapshot", force=True)
            for directory in ("sessions", "archived_sessions"):
                for source in sorted((args.codex_home / directory).rglob("*.jsonl")):
                    destination = home / directory / source.relative_to(args.codex_home / directory)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with source.open("rb") as original, destination.open("wb") as target:
                        try:
                            # Linux FICLONE; fall back to bounded copy on other filesystems.
                            fcntl.ioctl(target.fileno(), 0x40049409, original.fileno())
                        except OSError:
                            remaining = os.fstat(original.fileno()).st_size
                            while remaining:
                                block = original.read(min(1024 * 1024, remaining))
                                if not block:
                                    break
                                target.write(block)
                                remaining -= len(block)
                                progress(f"Copying snapshot: {files} files")
                    destination.chmod(0o400)
                    files += 1
                    total += destination.stat().st_size
                    progress(f"Freezing snapshot: {files} files")

            def status(state_name: str) -> tuple[dict[str, object], float]:
                command = [sys.executable, "-c",
                           "from codex_time.cli import main; raise SystemExit(main())",
                           "--codex-home", str(home), "--data-dir", str(root / "unused-data"),
                           "--state-dir", str(root / state_name), "status", "--json"]
                if args.plain:
                    command.append("--plain")
                began = time.perf_counter()
                result = subprocess.run(command, env=env, stdout=subprocess.PIPE, check=True)
                return json.loads(result.stdout), time.perf_counter() - began

            progress("Building cold cache", force=True)
            cold, cold_seconds = status("incremental")
            warm, warm_seconds = status("incremental")
            again, unchanged_seconds = status("incremental")
            progress("Comparing with independent full replay", force=True)
            replay, replay_seconds = status("full-replay")
            if not all(result["fresh"] for result in (cold, warm, again, replay)):
                raise ValueError("snapshot unexpectedly changed or could not be read")
            if not (
                cold["sessions"] == warm["sessions"] == again["sessions"] == replay["sessions"]
            ):
                raise ValueError("cached session state differs from full replay")
            if any(result["scan"]["opened"] or result["scan"]["bytes_read"]  # type: ignore[index]
                   for result in (warm, again)):
                raise ValueError("unchanged status read raw rollout bytes")
            prefix = "" if args.plain else "✅ "
            print(f"{prefix}Full replay matches cached session state")
            print(json.dumps({
                "rollout_files": files, "rollout_bytes": total,
                "sessions": len(cold["sessions"]),  # type: ignore[arg-type]
                "cold_status_seconds": round(cold_seconds, 6),
                "warm_status_seconds": round(warm_seconds, 6),
                "unchanged_status_seconds": round(unchanged_seconds, 6),
                "full_replay_seconds": round(replay_seconds, 6),
                "warm_scan": warm["scan"], "unchanged_scan": again["scan"],
            }, indent=2))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"{'' if args.plain else '⚠️ '}Status verification failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
