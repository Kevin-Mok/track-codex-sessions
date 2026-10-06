#!/usr/bin/env bash
# Verify the installed entry point and user service without changing either.
set -euo pipefail
arguments=()
while (( $# )); do
  case "$1" in
    --data-dir|--codex-home|--state-dir|--socket)
      if (( $# < 2 )); then echo "Missing value for $1" >&2; exit 2; fi
      arguments+=("$1" "$2"); shift 2 ;;
    -h|--help)
      echo 'Usage: scripts/check.sh [--data-dir PATH] [--codex-home PATH] [--state-dir PATH] [--socket PATH]'
      echo 'Use the same options as setup.sh. Checks the installed command and active user service.'
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
command -v uv >/dev/null || { echo 'uv is required to locate the installed application.' >&2; exit 1; }
executable="$(uv tool dir --bin)/codex-time"
[[ -x "$executable" ]] || { echo "Entry point missing: $executable. Run scripts/setup.sh." >&2; exit 1; }
"$executable" --help >/dev/null
systemctl --user is-active codex-time.service
"$executable" "${arguments[@]}" status
