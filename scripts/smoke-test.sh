#!/usr/bin/env bash
# Exercise fixture daemon/UI/restart and native readers without touching real records.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
uv run pytest -q tests/test_runtime.py tests/test_native.py tests/test_cli.py tests/test_storage.py tests/test_model_usage.py tests/test_model_output.py tests/test_model_ingest.py tests/test_setup.py tests/test_burn.py tests/test_burn_output.py tests/test_quota_storage.py tests/test_day_reporting.py tests/test_day_cli.py tests/test_day_output.py tests/test_overview.py tests/test_command_layout.py
printf 'Smoke checks passed: isolated daemon/UI/restart, combined overview/command aliases, daily repo/session reporting, model usage/backfill, allowance replay, history idempotence, storage and native readers.\n'
