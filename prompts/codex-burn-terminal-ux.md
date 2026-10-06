# Maintain readable terminal allowance reports

Use this handoff to continue the report UI without changing allowance accounting. Read the plan, run rendering checks at narrow and normal widths, then verify the installed entry point.

```text
Work in the track-codex-sessions checkout. Follow applicable AGENTS.md.
Read plans/codex-burn-terminal-ux.md, README.md, docs/model-burn-tracking.md
and docs/smoke-tests.md. Capture git status if Git metadata exists; preserve
existing work and do not create a worktree or commit/push automatically.

The user wants terminal reports with clear hierarchy, aligned numbers and
helpful icons like timetrace. burn_output.py uses Rich for width-aware output.
Keep allowance remaining and rate prominent, exact model/reasoning rows readable,
local timestamps, human durations and excluded consumption visible. Use --details
for technical flags/uncertainty/reset metadata; --plain produces ASCII; --color
supports auto/always/never and NO_COLOR overrides styling. JSON/CSV remain pure.
Do not confuse separate plan/bucket streams with sequential reset runs. Preserve
all accounting, metadata persistence and native-reader behavior.

For behavior changes, write defining tests and observe RED first. Run:
uv run pytest
uv run mypy src
uv run ruff check .
uv build
./scripts/smoke-test.sh
Inspect real PTY output at 40/80/120 columns, long/Unicode names, NO_COLOR,
pipes, --plain, --details and exports. Reinstall through scripts/setup.sh,
verify installed/source parity and scripts/check.sh service health. Update
matching docs, smoke checklist and ExecPlan with exact verification evidence.
```

Suggested Conventional Commit: `feat: improve allowance report readability`.
