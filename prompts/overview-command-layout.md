# Maintain the combined Codex Time overview

Review or extend the combined allowance/model report without changing its accounting or existing exports. Read the active plan and current source, preserve unrelated edits, run the defining tests, then verify documentation and the installed command.

## Paste-ready Cursor prompt

Work in `/home/kevin/coding/track-codex-sessions` on the existing branch. Read the applicable AGENTS instructions, [the active plan](../plans/overview-command-layout.md), [README](../README.md), [smoke checks](../docs/smoke-tests.md), and the current source/tests before editing. Capture `git status --short`; preserve pre-existing user changes. Do not create a worktree, commit, push or migrate data unless requested.

Keep `codex-time overview [day|week|month]` defaulting to today. It must show date/timezone and recorded duration, allowance balance, observed consumption, then ranked model totals with reasoning rows beneath each model. Resolve the date once and load the ledger once. Model and reasoning shares use all recorded work; model session counts independently union distinct contributing sessions. Allowance rates retain only their matched-work denominator, with exclusions, a concise confidence warning and separate reset cohorts. Keep unknown attribution visible, waits subtracted, concurrent roots additive and children excluded.

Support overview `--date`, `--details`, `--plain`, `--color`, `--json`, `--window-minutes`, `--limit-id` and `--max-gap-seconds`. Overview includes all directories/archive states; use dedicated reports for filtering. JSON has exactly `allowance`, `model_totals` and `reasoning`, each with the existing full report schema. Keep raw flags, uncertainty, matched model mixes and diagnostics behind --details. Preserve ASCII, NO_COLOR, piped output, long labels and tiny positive shares across terminal widths.

Advertise overview, allowance, model-time, projects, sessions, history, health and resume. Preserve no-argument picker behavior and daemon/import-history. Keep burn/models/day/list/report/status as silent hidden aliases with the same arguments, defaults, exports and exit codes. Update active documentation/callers to canonical names; retain historical verification evidence.

For any behavior change, add a focused failing test, observe the expected RED, implement the smallest GREEN change, and run the checks below. Maintain the active plan and matching README/smoke documentation in the same eventual change. Finish with fresh verification evidence and remaining risks.

## Atomic plan

- Read current composition, rendering, CLI and accounting tests; identify the exact behavior being changed.
- Add the defining failing test without weakening existing conservation/export assertions.
- Make the smallest implementation change, preserving one snapshot and distinct denominators.
- Update the active plan, relevant README examples, smoke checks and current callers.
- Run focused and full verification, review the diff, refresh the installed package and verify outside the checkout.

## Automated verification

Run from the checkout; no sudo is required:

```bash
.venv/bin/pytest -q tests/test_overview.py tests/test_command_layout.py
.venv/bin/pytest -q
.venv/bin/mypy src
.venv/bin/ruff check .
uv build
./scripts/smoke-test.sh
git diff --check
```

Check fixtures for exact total conservation, independent distinct session counts, unknown model/reasoning, waits, concurrent roots, child exclusion, missing readings and multiple reset cohorts. Alias comparisons must cover terminal/JSON/CSV output, defaults and exit codes. Fixture storage bytes must remain unchanged after report commands. Tests must establish behavior rather than only mirror implementation.

## Manual and installed verification

Use the grouped Action/Expected checks in [the smoke checklist](../docs/smoke-tests.md#combined-allowance-and-model-overview). Verify normal and narrow reports, long names, tiny positive shares, plain output, NO_COLOR, piped output, clean JSON, canonical help and legacy alias behavior.

For a presentation or CLI change, refresh the packaged executable without restarting the observer:

```bash
uv tool install --python 3.12 --force --reinstall-package codex-time "$PWD"
(cd /tmp && codex-time overview --plain && codex-time --help)
```

Verify installed module bytes match the reviewed source; an unchanged package version can otherwise reuse stale code. No data migration is needed. Use `./scripts/setup.sh` only when service installation/restart is intended. Report which manual checks were actually performed.

## Documentation and delivery

Keep [the overview plan](../plans/overview-command-layout.md), [README](../README.md), [smoke checks](../docs/smoke-tests.md), [allowance how-to](../docs/model-burn-tracking.md) and current script callers accurate. Review rollback by reverting only the intended task diff and reinstalling the prior package; stored data remains unchanged. Preserve historical plans, prompts and captured evidence.

Suggested commit: `feat: combine usage overview and clarify commands`. Include related implementation, tests, docs and plan updates together. Do not claim verification or commit work without fresh evidence and authorization.
