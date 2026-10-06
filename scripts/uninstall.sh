#!/usr/bin/env bash
# Remove the installed application and service, preserving all recorded data.
set -euo pipefail
if (( $# )); then
  case "$1" in
    -h|--help)
      echo 'Usage: scripts/uninstall.sh'
      echo 'Stops and removes the user service and uv tool. All data and runtime state remain on disk.'
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
fi
unit_path="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/codex-time.service"
if [[ -f "$unit_path" ]]; then
  systemctl --user disable --now codex-time.service
  rm -- "$unit_path"
  systemctl --user daemon-reload
fi
if command -v uv >/dev/null; then
  installed_tools="$(uv tool list)"
  if [[ "$installed_tools" == codex-time\ * || "$installed_tools" == *$'\n'codex-time\ * ]]; then
    uv tool uninstall codex-time
  fi
fi
echo 'Uninstalled codex-time. Recorded data and runtime state were preserved.'
