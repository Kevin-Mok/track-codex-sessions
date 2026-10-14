#!/usr/bin/env python3
"""Verify a portable data store or export current history for an older executable.

Stop its writer before use. Verification reads content-free evidence; export
writes a new destination and leaves source history and backups intact. No sudo.
"""

import argparse
import json
import sys
from pathlib import Path

from codex_time.progress import report_progress
from codex_time.recovery import export_legacy, verify_portable
from codex_time.storage import Store, StoreError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    export = sub.add_parser("export-legacy")
    export.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        label = ("" if args.plain else "🔎 ") + "Checking portable history"
        with report_progress(label):
            if args.command == "verify":
                with Store(args.data_dir, args.state_dir).writer():
                    result = verify_portable(args.data_dir)
            else:
                result = export_legacy(Store(args.data_dir, args.state_dir), args.destination)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(("" if args.plain else "✅ ") + "Portable history verified")
            for name, value in result.items():
                print(f"{name}: {value}")
        return 0
    except (StoreError, OSError, ValueError) as exc:
        print(("" if args.plain else "⚠️ ") + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
