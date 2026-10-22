# Review consumption-hour reconciliation

Review the presentation correction using the execution plan and frozen/runtime evidence. Check the time scopes first, then run the focused checks and inspect actual terminal output without changing live tracking data.

Read `plans/reconcile-consumption-hours.md` and inspect only this task's changes in `src/codex_time/overview_output.py`, `tests/test_overview.py`, `README.md`, `docs/model-burn-tracking.md` and `docs/smoke-tests.md`. Preserve pre-existing latency-related edits. Confirm that single-stream reset cohorts reconcile matched work against recorded work, parallel streams are never added, missing/all-time allowance reports remain sensible, and fractional-second truncation is explained. Keep all accounting, JSON/CSV schemas and stored data unchanged. Run the exact automated and manual checks in the plan; report concrete failures and remaining installation limits. Do not commit, push, install packages or restart services unless requested.
