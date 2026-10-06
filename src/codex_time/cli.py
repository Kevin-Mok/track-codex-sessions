"""The codex-time command; no subcommand opens the resume picker."""

import argparse
import asyncio
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from codex_time.burn import burn_report
from codex_time.burn_output import burn_csv, burn_table
from codex_time.daemon import import_history, observations, run_daemon, runtime_status
from codex_time.model_output import model_csv, model_table
from codex_time.model_usage import model_report
from codex_time.presentation import build_rows, duration, run_ui
from codex_time.reporting import report
from codex_time.storage import Store, StoreError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Read-only Codex session working-time tracker")
    result.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))),
    )
    result.add_argument("--data-dir", type=Path, default=Path.home() / ".codex-timetrace")
    result.add_argument("--state-dir", type=Path)
    result.add_argument("--socket", type=Path, help="existing Unix WebSocket control socket")
    result.add_argument("--timezone", default="America/Toronto")
    sub = result.add_subparsers(dest="command")
    sub.add_parser("daemon", help="track independently of the UI")
    sub.add_parser("import-history", help="idempotently reconcile historical lifecycle turns")
    status = sub.add_parser("status", help="show observer health and accuracy diagnostics")
    status.add_argument("--json", action="store_true")
    for name in ("list", "report"):
        command = sub.add_parser(name)
        command.add_argument("--all-dirs", action="store_true")
        command.add_argument("--archive", choices=["active", "archived", "all"], default="active")
        command.add_argument("--cwd", default=os.getcwd())
        command.add_argument("--json", action="store_true")
        if name == "list":
            command.add_argument("--search", default="")
            command.add_argument(
                "--sort", choices=["updated", "created", "time"], default="updated"
            )
        else:
            command.add_argument("--session")
            command.add_argument("--from", dest="start", type=date.fromisoformat)
            command.add_argument("--to", dest="end", type=date.fromisoformat)
    models = sub.add_parser("models", help="rank model working-time usage")
    periods = models.add_subparsers(dest="period", required=True)
    for period in ("day", "week", "month"):
        command = periods.add_parser(period, help=f"current calendar {period} working-time usage")
        command.add_argument("--date", type=date.fromisoformat, dest="selected_date")
        command.add_argument("--cwd", help="count only intervals in this directory")
        command.add_argument("--archive", choices=["active", "archived", "all"], default="all")
        command.add_argument("--model-only", action="store_true", help="combine reasoning levels")
        exports = command.add_mutually_exclusive_group()
        exports.add_argument("--json", action="store_true")
        exports.add_argument("--csv", action="store_true")
    burn = sub.add_parser("burn", help="estimate allowance burn for observed workloads")
    burn_periods = burn.add_subparsers(dest="period", required=True)
    for period in ("day", "week", "month"):
        command = burn_periods.add_parser(period)
        command.add_argument("--date", type=date.fromisoformat, dest="selected_date")
        command.add_argument("--window-minutes", type=int, default=10080)
        command.add_argument("--limit-id", default="codex")
        command.add_argument("--max-gap-seconds", type=int, default=600)
        command.add_argument("--details", action="store_true", help="show technical evidence")
        command.add_argument("--plain", action="store_true", help="ASCII output without color")
        command.add_argument(
            "--color",
            choices=["auto", "always", "never"],
            default="auto",
            help="terminal color (respects NO_COLOR)",
        )
        exports = command.add_mutually_exclusive_group()
        exports.add_argument("--json", action="store_true")
        exports.add_argument("--csv", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        ZoneInfo(args.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        print(f"Unknown timezone: {args.timezone}", file=sys.stderr)
        return 2
    try:
        store = Store(args.data_dir, args.state_dir)
        home = args.codex_home.expanduser().resolve()
        if args.command == "daemon":
            asyncio.run(run_daemon(store, home, args.socket))
        elif args.command == "import-history":
            ledger = import_history(store, home)
            print(f"Imported {len(ledger.sessions)} sessions; no duplicate intervals.")
            for message in ledger.diagnostics:
                print(message, file=sys.stderr)
        elif args.command == "status":
            status = runtime_status(store)
            ledger = store.load()
            status["sessions"] = len(ledger.sessions)
            status["diagnostics"] = ledger.diagnostics
            if args.json:
                print(json.dumps(status, indent=2))
            else:
                for key, value in status.items():
                    print(f"{key}: {value}")
        elif args.command == "report":
            if args.start and args.end and args.end < args.start:
                raise StoreError("report --to must be on or after --from")
            data = report(
                store.load(),
                cwd=args.cwd,
                all_directories=args.all_dirs,
                archive=args.archive,
                session_id=args.session,
                timezone_name=args.timezone,
                start=args.start,
                end=args.end,
            )
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                print(f"Working time ({args.timezone}): {duration(data['total_seconds'])}")
                print(f"Quality: {', '.join(str(q) for q in data['quality'])}")
                print(
                    json.dumps({k: data[k] for k in ("days", "directories", "sessions")}, indent=2)
                )
        elif args.command == "burn":
            burn_data = burn_report(
                store.load(),
                period=args.period,
                selected_date=args.selected_date,
                timezone_name=args.timezone,
                window_minutes=args.window_minutes,
                limit_id=args.limit_id,
                max_gap_seconds=args.max_gap_seconds,
            )
            if args.json:
                print(json.dumps(burn_data, indent=2))
            elif args.csv:
                print(burn_csv(burn_data), end="")
            else:
                use_color = args.color == "always" or (
                    args.color == "auto"
                    and sys.stdout.isatty()
                    and os.environ.get("TERM") != "dumb"
                )
                print(
                    burn_table(
                        burn_data,
                        width=shutil.get_terminal_size((88, 24)).columns,
                        color=use_color,
                        details=args.details,
                        plain=args.plain,
                    )
                )
        elif args.command == "models":
            model_data = model_report(
                store.load(),
                period=args.period,
                selected_date=args.selected_date,
                cwd=args.cwd,
                archive=args.archive,
                model_only=args.model_only,
                timezone_name=args.timezone,
            )
            if args.json:
                print(json.dumps(model_data, indent=2))
            elif args.csv:
                print(model_csv(model_data), end="")
            else:
                print(model_table(model_data))
        elif args.command == "list":
            rows = build_rows(
                store.load(),
                observations(store),
                cwd=args.cwd,
                timezone_name=args.timezone,
                all_directories=args.all_dirs,
                archive=args.archive,
                sort=args.sort,
                query=args.search,
            )
            if args.json:
                print(
                    json.dumps(
                        [
                            {
                                "id": r.id,
                                "title": r.title,
                                "cwd": r.cwd,
                                "state": r.state,
                                "archived": r.archived,
                                "today_seconds": r.today,
                                "total_seconds": r.total,
                                "quality": r.quality,
                                "model_id": r.model_id,
                                "reasoning_level": r.reasoning_level,
                            }
                            for r in rows
                        ],
                        indent=2,
                    )
                )
            else:
                for row in rows:
                    print(
                        f"{row.id}  {row.state:7}  {'archived' if row.archived else 'active':8}  "
                        f"today {duration(row.today)}  total {duration(row.total)}  "
                        f"model {row.model_id or 'Unknown'} / {row.reasoning_level or 'Unknown'}  "
                        f"{row.title}  {row.cwd}  [{row.quality}]"
                    )
        else:
            run_ui(lambda: (store.load(), observations(store)), args.timezone, os.getcwd(), home)
        return 0
    except (StoreError, OSError, ValueError) as error:
        print(f"codex-time: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
