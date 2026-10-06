# Codex Time continuation prompt

Use this prompt to review or extend the installed tracker without changing Codex threads or existing timetrace data. Read the plan and source, reproduce the requested behavior in isolated fixtures, then verify the implementation and documentation together.

```text
Work in the track-codex-sessions checkout. Read the applicable AGENTS.md instructions, plans/codex-session-time-tracker.md, README.md and docs/smoke-tests.md. Preserve existing work and capture git status before a modifying command if a repository has since been initialized. Do not use worktrees, commit/push automatically, or operate on existing ~/.timetrace records.

The app is implemented in typed Python 3.12 modules under src/codex_time. JSON is durable truth; the user service runs independently of curses. Preserve read-only observation: only initialize/initialized, thread/loaded/list, and thread/read(includeTurns=false) may be sent by the observer. Enter-to-resume is the sole deliberate launch path. Keep conversation bodies, tool output and credentials out of persistence.

For each requested behavior change, write a defining failing fixture/reproducer first, observe RED, implement minimum GREEN and run regression checks. Merge same-session work and wait unions, preserve per-turn cwd, exclude additional child-agent totals, and never extrapolate stale unfinished tasks. Historical approvals remain uncertain upper bounds. Update the ExecPlan, README and relevant grouped smoke checks with code.

Verification: uv run pytest; uv run mypy src; uv run ruff check .; uv build; ./scripts/smoke-test.sh. Native readers must use disposable HOME/config/store only. For installation verification use scripts/setup.sh and scripts/check.sh; no sudo. Uninstall preserves recorded data. Check runtime heartbeat as well as systemd active status after a large initial import.

Review the simplest robust change and exact evidence, then hand off any manual checks and remaining accuracy limits. If later authorized to commit, include related plan/docs in the implementation commit, inspect staged diffs, and use: feat: track Codex session working time.
```
