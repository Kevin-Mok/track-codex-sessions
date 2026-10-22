# Concise CLI output handoff

Maintain readable Codex Time reports without changing accounting or machine exports. Read `plans/concise-cli-output.md`, inspect the touched renderers/tests, then verify compact normal/details/plain output before changing anything.

Human reports show totals, working thread/model rows and concise confidence/coverage caveats. History collapses zero-activity sessions into an explicit count by default; details/JSON retain the full selected list, while session search always keeps all results. `--details` adds full root IDs and compact input/cache/output breakdowns; complete diagnostics, child identities and pricing/FX dictionaries belong in JSON. Reuse the existing working-duration formatter to preserve fractions and consistent seconds. Preserve exact-directory/date/archive filters, missing-versus-zero distinctions, safe terminal metadata, width bounds, progress, aliases and JSON/CSV schemas. Keep edits small and dependency-free.

Automated plan: run `.venv/bin/python -m pytest`, `.venv/bin/mypy src`, and `.venv/bin/ruff check .`. Keep HOME/XDG unchanged. Offline setup/build tests need the populated default uv cache; disposable writer tests need approved access to the canonical lock directory, which is independent of --state-dir and XDG_STATE_HOME. Never override HOME to bypass that boundary. Run `scripts/token-smoke.py --executable .venv/bin/codex-time --scenario verify` for disposable replay/accounting checks.

Manual plan: inspect `projects day --date 2026-10-21 --cwd /absolute/project --details`, repeat at 40 columns with `--plain`, and compare `--json` for full evidence. Inspect sessions/history/health/status summaries and an empty filter. Replace the directory/date with recorded data. Commands require no sudo. Follow `docs/smoke-tests.md`; do not restart the daemon or edit personal history for presentation verification.

Documentation: keep README, token-cost guide, smoke checks and plan consistent. Suggested Conventional Commit: `fix: make CLI reports concise and readable`. No commit/push is authorized by this handoff alone. Rollback affects presentation plus the installed package; data requires no migration.
