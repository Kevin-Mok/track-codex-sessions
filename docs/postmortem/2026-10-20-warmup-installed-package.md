# Warmup emoji missing from the installed command

Update the installed package after changing source so `cto` and `codex-time`
use the verified report-loading emoji without requiring `uv run`.

- Symptom: from linux-config, `uv run codex-time overview` still printed
  `Reading overview report: 2s elapsed` without the emoji.
- Impact: the previous handoff verified source but left the user's executable stale.
- Evidence: `codex-time` resolves to `~/.local/bin/codex-time`, linked
  into `~/.local/share/uv/tools/codex-time/`. `cto` already maps to
  `codex-time overview`; it needs no alias change.
- Lookup: reviewed `local-uv-source-tool-reinstall` in canonical postmortem memory.
  Its unchanged-version local installation remedy applies here.
- Plan: reproduce with the installed CLI, reinstall with `--reinstall-package`,
  and verify installed progress, plain mode and JSON isolation.
- Environment: a read-only `uv tool list` attempt required cache access outside
  writable roots and failed. Installation requires normal sandbox escalation.
- Resolution: `uv tool install --python 3.12 --force --reinstall-package codex-time
  ~/coding/track-codex-sessions` rebuilt and installed the package successfully.
- Verification: installed `cli.py` matches source byte for byte. The actual installed
  executable passed overview/projects decorated progress, overview plain progress,
  and JSON parsing on disposable data with accelerated progress intervals.
- Status: verified fix for newly launched CLI processes. The running daemon was
  not restarted; no service configuration changed.
- Learning: verify the actual installed entry point before declaring CLI changes
  usable. Canonical memory updates are outside this workspace's writable roots.
