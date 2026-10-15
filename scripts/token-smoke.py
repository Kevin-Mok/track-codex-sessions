#!/usr/bin/env python3
"""Show and verify token reports using disposable history, without network access."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path

STAMP = "2026-10-06T16:00:00+00:00"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", default=shutil.which("codex-time"))
    parser.add_argument(
        "--scenario",
        default="verify",
        choices=[
            "verify",
            "normal",
            "narrow",
            "overview",
            "filtered",
            "json",
            "missing",
        ],
    )
    args = parser.parse_args()
    if not args.executable:
        parser.error("install codex-time or pass --executable .venv/bin/codex-time")
    executable = str(Path(args.executable).expanduser().resolve())
    with tempfile.TemporaryDirectory(prefix="codex-token-smoke-") as temporary:
        root = Path(temporary)
        home, data, state = root / "codex", root / "data", root / "state"
        rollouts = home / "sessions"
        rollouts.mkdir(parents=True)
        state.mkdir()

        def record(kind: str, payload: dict[str, object], stamp: str = STAMP) -> str:
            return json.dumps({"timestamp": stamp, "type": kind, "payload": payload}) + "\n"

        def rollout(
            sid: str,
            cwd: str,
            amount: int,
            parent: str | None = None,
            *,
            model_id: str | None = None,
        ) -> None:
            model = model_id or ("internal-unpriced" if args.scenario == "missing" else "gpt-4.1")
            counts = {
                "input_tokens": amount,
                "cached_input_tokens": amount // 4,
                "cache_write_input_tokens": 0,
                "output_tokens": amount // 10,
                "reasoning_output_tokens": amount // 20,
                "total_tokens": amount * 11 // 10,
            }
            meta: dict[str, object] = {"id": sid, "cwd": cwd, "source": "cli"}
            if parent:
                meta["parent_thread_id"] = parent
            (rollouts / f"{sid}.jsonl").write_text(
                record("session_meta", meta)
                + record("event_msg", {"type": "task_started", "turn_id": sid})
                + record("turn_context", {"turn_id": sid, "cwd": cwd, "model": model})
                + record(
                    "event_msg",
                    {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": counts,
                            "last_token_usage": counts,
                        },
                    },
                    "2026-10-06T16:00:30+00:00",
                )
                + record(
                    "event_msg",
                    {"type": "task_complete", "turn_id": sid},
                    "2026-10-06T16:01:00+00:00",
                )
            )

        rollout("smoke-root", "/fixture/project", 1_000_000)
        rollout("smoke-child", "/fixture/subagent", 200_000, "smoke-root")
        rollout(
            "smoke-review", "/fixture/project", 100_000, "smoke-root", model_id="codex-auto-review"
        )
        if args.scenario != "missing":
            (state / "fx-usd-cad.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "rate": "1.35",
                        "observation_date": "2026-10-06",
                        "last_success": STAMP,
                        "last_attempt": STAMP,
                    }
                )
            )
        base = [
            executable,
            "--codex-home",
            str(home),
            "--data-dir",
            str(data),
            "--state-dir",
            str(state),
        ]
        env = dict(os.environ, NO_COLOR="1")
        env.pop("PYTHONPATH", None)

        def run(*options: str, width: int = 88) -> str:
            result = subprocess.run(
                base + list(options),
                check=True,
                capture_output=True,
                text=True,
                cwd=root,
                env=dict(env, COLUMNS=str(width)),
            )
            return result.stdout

        run("import-history")

        def hashes() -> dict[str, str]:
            return {
                str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for directory in (data, state)
                for p in directory.rglob("*")
                if p.is_file() and p != state / "overview-report.json"
            }

        def check_cache() -> None:
            cache = state / "overview-report.json"
            if cache.exists():
                value = json.loads(cache.read_bytes())
                assert value["version"] == 1
                tokens = value["report"]["token_usage"]["usage"]["tokens"]
                assert tokens["total_tokens"] == 1_320_000

        before = hashes()
        if args.scenario == "verify":
            for period in ("day", "week", "month", "all"):
                dates = [] if period == "all" else ["--date", "2026-10-06"]
                project = json.loads(run("projects", period, *dates, "--json"))
                overview = json.loads(run("overview", period, *dates, "--json"))
                assert project["usage"] == overview["token_usage"]["usage"]
                assert project["usage"]["tokens"]["total_tokens"] == 1_320_000
                assert project["total_seconds"] == 60
                assert project["usage"]["cost_complete"]
                assert project["excluded_models"] == ["codex-auto-review"]
                assert all(row["model_id"] != "codex-auto-review" for row in project["models"])
                assert Decimal(project["usage"]["usd"]) == Decimal("2.91")
                assert Decimal(project["usage"]["cad"]) == Decimal("3.9285")
            assert json.loads(run("day", "all", "--json"))["usage"] == project["usage"]
            run("overview", "all", "--plain")
            run("projects", "all", "--plain", "--details", width=32)
            assert before == hashes(), "report mutated fixture storage"
            check_cache()
            run("import-history")
            assert json.loads(run("projects", "all", "--json"))["usage"] == project["usage"]
            prefix = "" if os.environ.get("CLI_PLAIN") == "1" else "✅ "
            print(prefix + "Token smoke passed: 1,320,000 tokens; USD 2.91; CAD 3.9285 at 1.35.")
            print(
                "Periods, child attribution, auto-review exclusion, replay "
                "and read-only reports passed."
            )
            return
        options = {
            "normal": ["projects", "day", "--date", "2026-10-06", "--plain"],
            "narrow": ["projects", "all", "--plain"],
            "overview": ["overview", "all", "--plain"],
            "filtered": [
                "projects",
                "week",
                "--date",
                "2026-10-06",
                "--cwd",
                "/fixture/subagent",
                "--session",
                "smoke-root",
                "--archive",
                "all",
                "--plain",
            ],
            "json": ["overview", "all", "--json"],
            "missing": ["projects", "all", "--plain"],
        }
        print(run(*options[args.scenario], width=32 if args.scenario == "narrow" else 88), end="")
        assert before == hashes(), "report mutated fixture storage"
        check_cache()


if __name__ == "__main__":
    main()
