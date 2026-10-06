#!/usr/bin/env bash
# Install the local application and user daemon. No sudo is required.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
arguments=()
while (( $# )); do
  case "$1" in
    --data-dir|--codex-home|--state-dir|--socket)
      if (( $# < 2 )); then echo "Missing value for $1" >&2; exit 2; fi
      arguments+=("$1" "$2"); shift 2 ;;
    -h|--help)
      echo 'Usage: scripts/setup.sh [--data-dir PATH] [--codex-home PATH] [--state-dir PATH] [--socket PATH]'
      echo 'Installs with uv and enables the systemd user service. No sudo. Recorded data is preserved.'
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
command -v uv >/dev/null || { echo 'Install uv before running setup.' >&2; exit 1; }
command -v systemctl >/dev/null || { echo 'A systemd user manager is required.' >&2; exit 1; }
systemctl --user show-environment >/dev/null
# Refresh the local wheel even when source changes leave pyproject/version unchanged.
uv tool install --python 3.12 --force --reinstall-package codex-time "$repo_dir"
bin_dir="$(uv tool dir --bin)"
executable="$bin_dir/codex-time"
[[ -x "$executable" ]] || { echo "Installed entry point missing: $executable" >&2; exit 1; }
# systemd command quoting differs from shell quoting; no shell runs ExecStart.
quote_systemd() {
  local value="$1"
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || { echo 'Paths must not contain newlines.' >&2; exit 2; }
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//%/%%}"
  value="${value//\$/\$\$}"
  printf '"%s"' "$value"
}
exec_start="$(quote_systemd "$executable")"
for argument in "${arguments[@]}"; do exec_start+=" $(quote_systemd "$argument")"; done
exec_start+=' daemon'
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$unit_dir"
unit_path="$unit_dir/codex-time.service"
unit_tmp="$(mktemp "$unit_dir/.codex-time.XXXXXX")"
trap 'rm -f -- "$unit_tmp"' EXIT
while IFS= read -r line; do
  if [[ "$line" == 'ExecStart=@EXEC_START@' ]]; then
    printf 'ExecStart=%s\n' "$exec_start"
  else
    printf '%s\n' "$line"
  fi
done < "$repo_dir/systemd/codex-time.service" > "$unit_tmp"
mv -- "$unit_tmp" "$unit_path"
systemctl --user daemon-reload
systemctl --user enable --now codex-time.service
systemctl --user restart codex-time.service
"$executable" --help >/dev/null
systemctl --user is-active codex-time.service
printf 'Installed %s\nUser service: %s\n' "$executable" "$unit_path"
printf 'Run scripts/check.sh with the same directory/socket options to inspect tracking.\n'
