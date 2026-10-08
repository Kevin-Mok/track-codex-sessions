# Daily repo and session time

Add a readable terminal report for a calendar day's recorded Codex working time, grouped by directory with contributing session durations. Reuse existing accounting and keep JSON totals exact.

## Purpose and observable outcome

`codex-time day` shows today across all directories/archive states, with a day total, ranked directory totals/shares and nested session titles/IDs/durations. `--date YYYY-MM-DD`, `--cwd`, `--archive`, `--session`, `--json`, `--details`, `--plain` and `--color` support the existing reporting conventions.

## Context and scope

Loaded README, smoke docs, lessons, reporting, accounting, models and CLI fixtures; prompt saved at prompts/daily-repo-session-time.md. Initial git status was clean. Default mode has no Plan Mode switching tool; this living plan follows /home/kevin/linux-config/.agent/PLANS.md. No worktrees, dependency/config changes, commits, pushes, tracker data mutation or service restarts. Refresh only the existing codex-time package from its verified source checkout after checks. The user explicitly invoked compile-and-execute and confirmed terminal output.

## Assumptions and decisions

Directory means original recorded per-turn cwd; do not infer Git roots or merge nested cwd paths. Time means recorded wait-subtracted Codex work, not human attention. All archives contribute by default, children are excluded, simultaneous roots sum, local dates use the selected timezone. Sessions crossing directories appear once in each relevant directory with only that share of work. Ordering is descending exact duration then cwd/session ID. JSON preserves exact integer microseconds; existing report shape remains intact.

## Ordered implementation checklist

- [x] Inspect context, capture clean state, compile/save/read back prompt and confirm terminal format.
- [x] Write defining aggregation/CLI tests; observe expected RED.
- [x] Implement typed day projection and CLI; verify GREEN and conservation.
- [x] Write formatter tests; observe RED; implement hierarchy and narrow/plain output.
- [x] Update README and smoke checks with reproducible commands and expected results.
- [x] Run focused/full tests, mypy, ruff, build, isolated smoke and read-only real-data report.
- [x] Independently review implementation and reconcile evidence/handoff.

## Risks, edge cases and rollback

Preserve source ledgers, native records and existing report exports. Midnight/DST, wait intervals, overlaps, children, archived sessions, resumed cwd, unknown names, control characters and long paths must behave sensibly. Concurrent roots can exceed clock time; quality flags describe uncertainty. Rollback removes the new CLI projection/output and its docs/tests without changing stored data. The preflight tooling failures are recorded in docs/postmortem/2026-10-06-daily-report-preflight.md.

## Exact verification

RED/GREEN: uv run pytest tests/test_day_reporting.py tests/test_day_cli.py tests/test_day_output.py. Regression: uv run pytest; uv run mypy src; uv run ruff check .; uv run ruff format --check src/codex_time/reporting.py src/codex_time/cli.py src/codex_time/day_output.py tests/test_day_reporting.py tests/test_day_cli.py tests/test_day_output.py; uv build; ./scripts/smoke-test.sh. Render fixtures at 88/48 columns, plain and NO_COLOR; read a real date without writing tracking data. Compare day total_microseconds to report --all-dirs --archive all --from DATE --to DATE --json. New manual checks belong in docs/smoke-tests.md. No sudo required.

## Progress, evidence and review

Preflight: clean Git status; metaprompt artifact saved/read back. Terminal report confirmed. Accounting and display are separate units; focused agent review validated edge cases independently. Verification evidence is recorded below. Keep matching plan and implementation together if later committed.

RED: uv run pytest -q tests/test_day_reporting.py exited 1 (14 missing-daily_report failures); after projection implementation the same command exited 0 (14 passed). CLI RED exited 1 (7 failures: day absent from argparse choices). Formatter agent observed missing-output-module RED.

Integrated GREEN: focused tests exited 0 (30 passed); strict mypy exited 0 (17 source files). Formatter tests exercise 20/48/88 cells, metadata escaping, plain/NO_COLOR, empty and subsecond work. Read-only real-date rendering succeeded. Preflight postmortem coverage check exited 0, reviewed hash 73c25eb22a671d57918243d37548677a2bd0c44dcd86e2f91398b2b45286d0ec; canonical memory entry records no new reusable learning.

Final review found no blocking issues. Added genuine directory ties, positive CLI filters and many fractional intervals to close its nonblocking test gaps. Final `uv run pytest -q --tb=short`: exit 0, 163 passed in 13.00s. `./scripts/smoke-test.sh`: exit 0, 109 passed in 12.48s. `uv run mypy src`: exit 0, 17 source files; `uv run ruff check .`: exit 0; six-file scoped format check: exit 0; `uv build`: exit 0, wheel and source archive. Real single-snapshot day/report comparison: exit 0, 33,975,281,341 microseconds across six directories at observation; all nested sums matched and the in-memory ledger stayed unchanged. That is a point-in-time value while the independent observer continues working.

Installed CLI provenance direct_url.json identified this checkout. Refreshed only the existing package with `uv tool install --offline --python 3.12 --force --reinstall-package codex-time /home/kevin/coding/track-codex-sessions`: exit 0. No service restart or tracking-data write was performed. Installed-command verification follows below. The new lint preflight report records an extra blank line between imports, fixed with final Ruff GREEN; its required canonical-memory no-new-learning record and targeted coverage check accompany this task.

## Reproducible handoff

Atomic change: typed daily projection + CLI + renderer + defining/regression tests + README/smoke updates + this plan + saved prompt and tooling reports. Preserve the complete set in the same commit if a later commit is requested. Suggested subject: `feat: add daily repo and session time report`.

Paste-ready Cursor prompt:

```text
Read plans/daily-repo-session-time.md and prompts/daily-repo-session-time.md. Maintain codex-time day as a read-only daily directory/session projection of the existing segments(), with exact nested microsecond conservation, original cwd attribution, root concurrency and child exclusion. Preserve existing report JSON. Run the plan's automated tests and docs/smoke-tests.md daily-report checks; record actual evidence and keep plan/docs in the same change. Do not commit, push, restart the observer or alter tracking data without authorization.
```

Automated checks: the exact commands above plus focused `uv run pytest -q tests/test_day_reporting.py tests/test_day_cli.py tests/test_day_output.py` (37 checks). Manual checks: `codex-time day`, `codex-time day --date 2026-10-06 --plain`, `COLUMNS=48 codex-time day --date 2026-10-06 --plain`, and filtered `--cwd /absolute/project --details` / `--session SESSION_ID`. All require no sudo. Inspect visible dates, totals, shares, full paths, stable IDs and readable durations; exact conservation uses JSON microseconds and a consistent ledger snapshot. Human attention, subjective acceptance and independently ongoing observer writes are outside these checks.

Docs updated: README daily-use section and command overview; docs/smoke-tests.md daily reporting group; scripts/smoke-test.sh includes the 37 day tests. Rollback removes the added projection/CLI/renderer/tests/docs and reinstalls the previous source version without altering the data schema or records.

Installed verification: from /tmp, /home/kevin/.local/bin/codex-time day --date 2026-10-06 --session 01a113bd-6b4c-74d1-86c2-080fe3ce0b90 --plain exited 0 and displayed the current session under its recorded directory. Installed cli.py/reporting.py/day_output.py bytes equal checkout bytes; systemctl --user is-active codex-time.service returned active. Both targeted postmortem-memory checks exited 0 with no errors; the lint report reviewed hash is 7102a6e7ac8317bf057f67a1f4272b7d79ce7d99df3dedf4b9d40c9546d758eb. All checklist work is verified. Remaining limitation: recorded Codex work is evidence-based, concurrent roots can exceed elapsed time, and terminal duration displays omit fractional seconds except subsecond-only values; JSON remains exact. No tracked configuration files changed, so refresh-config is not required.

## Session delivery: 2026-10-08

The user explicitly requested `$commit-session`, authorizing a scoped commit and upstream push of this conversation's changes. Session ID: `01a113bd-6b4c-74d1-86c2-080fe3ce0b90`; branch `main`, upstream `origin/main` at Kevin-Mok/track-codex-sessions. The original pre-write status was clean; current pre-commit status was captured before edits/staging.

The installed scope helper exited 0 with `status: unsafe`: its parser did not recognize wrapped successful repo writes, so it found no first-write/baseline metadata. Direct action evidence in this conversation and its matching log establishes the original implementation, tests, prompt, plan and two initial incident reports. The formatter agent's scoped edits were independently verified. Use the required direct-write fallback for those 13 files and the directly observed README gate repairs.

Leave another conversation's rerun incident and changes unstaged: Rich daily wording in the README stack paragraph; recorded-work heading and its assertion; the smoke Expected heading/evidence link; and the plan's Requested rerun section. Keep these working-tree bytes intact by staging the original session's content through the index. The rerun report was not created by a write in this conversation's log. Canonical-memory changes in linux-config are outside this repository's commit scope.

Fresh working-tree checks: `uv run pytest -q --tb=short tests/test_day_reporting.py tests/test_day_cli.py tests/test_day_output.py` exited 0 (37 passed); `uv run mypy src` exited 0 (17 source files); `uv run ruff check .` exited 0. README gate outcome `update_in_same_change`: clarify whole-second rounding versus visible subsecond work, and document that uninstall has no configurable options. Both source-supported repairs are included. Repo-specific stack, hook/order, install/use and CLI flags otherwise pass. Every candidate is below 3 MB, so Git LFS is not needed. Build/cache/data output remains excluded.

Exact staged-snapshot check: `UV_PROJECT_ENVIRONMENT=/home/kevin/coding/track-codex-sessions/.venv UV_OFFLINE=true uv run pytest -q --tb=short tests/test_day_reporting.py tests/test_day_cli.py tests/test_day_output.py` from the temporary index checkout exited 0 (37 passed in 0.52s). Staged README gate is `pass_no_change` after the two repairs. Staged implementation/docs were reviewed and `git diff --cached --check` now exits 0. A separator blank line found during plan splitting was corrected only in the index version; its resolved incident and local engineering lesson are included. Canonical-memory targeted check exited 0 for reviewed hash d208cd15b9f6f0ab72ca5c10459cee56e21968b7f529efd5caff30a46318cec8, with a narrow no-new-learning insertion preserving unrelated entries. The final staged set has the original 13 session files plus this delivery incident and tasks/lessons.md. Commit subject: `feat: add daily repo and session time report`. Commit and one normal push to origin/main are authorized; final command evidence is reported to the user. The atomic implementation and its matching plan/docs stay together. This feature remains a read-only projection with no storage migration; rollback is a revert of the feature commit and a rebuild, preserving recorded data.
