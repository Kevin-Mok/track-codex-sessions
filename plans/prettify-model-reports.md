# Prettify model usage reports

Make daily, weekly and monthly model rankings easy to scan. Add emoji cues, readable dates and durations, and compact shares; retain exact accounting and technical evidence in exports/details.

## Context and scope

Change src/codex_time/model_output.py and the models CLI flags in cli.py. Add tests/test_model_output.py; update presentation assertions in test_model_usage.py, README, docs/smoke-tests.md and the handoff prompt. Preserve pre-existing README, smoke docs, plans/daily-repo-session-time.md, day_output.py and test_day_output.py changes. No ledger/schema/accounting changes or daemon restart are needed. The subsequent commit-session request authorizes scoped commits and upstream pushes.

## Decisions

- Keep exact model IDs; show reasoning unless --model-only combines levels.
- Use Rich already installed in the project, responsive table/stacked rows, emoji headings, two-decimal percentages, and readable durations including tiny nonzero work.
- Support --details, --plain and --color auto|always|never consistently with day/burn. NO_COLOR and plain suppress color. JSON/CSV retain their schema and values.
- Show Unknown without a rank; keep it in totals. Show a short accuracy note when evidence is incomplete; move raw diagnostics behind details.
- Update canonical linux-config AGENTS and feedback as separately requested, then run refresh-config.

## Checklist

- [x] Capture initial status; read renderer, tests, lessons, plan and preferences.
- [x] Define output/CLI tests and observe expected RED.
- [x] Implement compact responsive renderer and CLI flags.
- [x] Update docs, reusable smoke checks and handoff prompt.
- [x] Run focused/full tests, mypy, ruff, build and independent review.
- [x] Reinstall the CLI without restarting the daemon; verify installed day/week and reasoning breakdown.
- [x] Refresh canonical config; verify installed instruction text and record final evidence.

## Verification

Run .venv/bin/pytest -q tests/test_model_output.py tests/test_model_usage.py for RED/GREEN. Run .venv/bin/pytest -q, .venv/bin/mypy src, .venv/bin/ruff check . and uv build. Verify installed codex-time models day, models day --model-only, models week --model-only and --plain/--details; capture 40/88 column renderings. JSON/CSV must still parse and preserve fixture microseconds. Manual checks live in docs/smoke-tests.md.

## Risks and rollback

Emoji width varies by terminal; use Rich cell measurement and stacked rows below 70 columns. Avoid rounding nonzero subsecond durations to zero. Never crown Unknown or infer efficiency from working-time share. Preserve dirty docs with targeted edits. Roll back the renderer/CLI additions and reinstall the previous package; recorded data is untouched. Config refresh can reconcile unrelated live/source configuration, so inspect its resulting diff and preserve user changes.

## Progress and review notes

Independent read-only review confirmed Unknown ranking, narrow Unicode width, plain/color safety, subsecond durations, and export invariance as required checks. The user additionally requested reasoning breakdown; existing no--model-only semantics provide it and will be documented prominently.

RED: .venv/bin/pytest -q tests/test_model_output.py tests/test_model_usage.py exited 1: 12 expected failures for absent emoji/readable rendering, missing presentation arguments and legacy duration output; 15 accounting tests passed.

Focused GREEN: 27 tests passed (exit 0). Long Unicode model names now select stacked layout; day/week/month CLI flags and export parity pass.

First broad verification passed: 177 pytest tests; strict mypy on 17 sources; Ruff; source/wheel build (all exit 0). Independent review found tiny positive shares rounded to zero in stacked layout. Defining RED: 2 failed/1 passed for 0.001 percent; shared percentage-label formatting fixes both layouts. refresh-config exited 0 with REFRESH COMPLETE; it snapshot live Codex config, applied chezmoi and regenerated/reloaded shortcuts.

Final source verification: .venv/bin/pytest -q passed 180 tests; .venv/bin/mypy src passed all 17 sources; .venv/bin/ruff check . passed; uv build produced wheel/source distributions; ./scripts/smoke-test.sh passed 126 isolated tests (all exit 0). Review tiny-share issue is covered by three GREEN cases. git diff --check passed. Installed live day report visibly breaks down medium/xhigh/high; week --model-only combines levels; 40-column plain view stacks full rows. Installed instruction bytes match canonical AGENTS; its CLI rule is active.

Installed verification exited 0: day/week/month JSON row microseconds conserve total; renderer and CLI installed bytes match source; --plain --details --color always is ASCII without ANSI and exposes timing details. Live day/week normal output inspected; no raw diagnostics in default view. uv tool install --python 3.12 --force --reinstall-package codex-time rebuilt and installed this source. No daemon restart, data migration, commits or pushes were performed. Handoff prompt: prompts/prettify-model-reports.md. No unresolved code-review findings; terminal/font emoji appearance remains environment-dependent.

## Session commit delivery

The user authorized $commit-session after implementation. Both scope-helper runs returned no recognized writes because inline Python edits are not detected; observed command writes plus the recorded pre-write statuses define scope. Split baseline-dirty README/smoke documents and canonical instruction/feedback/ledger hunks; leave unrelated daily-report and linux-config changes untouched. README gate repairs make the tracker opening purpose explicit, standardize the Tech Stack heading, move stack proof before At a glance, and label the existing daily CLI reference. Preserve the pre-existing daily-word stack edit. Focused presentation/accounting tests, typing, lint and both README gates are required before commit/push. Commit implementation, docs and this plan together.

Pre-commit verification: focused .venv/bin/pytest -q tests/test_model_output.py tests/test_model_usage.py passed 30 tests; strict mypy on 17 sources and focused Ruff passed. Both source and session-only staged README gates passed. Staged diff checks passed; only 11 tracker paths and six linux-config paths contain directly evidenced session content. All unrelated hunks remain in the working tree.
