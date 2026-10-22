# Consumption and model hours do not visibly reconcile

Investigate the six-second difference in the supplied report and make any corrected accounting or presentation verifiable with frozen evidence.

## Symptom and impact

The supplied consumption rows show 3h20m19s and 2h5m49s (5h26m8s combined). Model rows show 3h57m1s, 1h11m47s and 17m26s (5h26m14s combined). The report says the scopes differ but does not quantify the difference. The investigation below separates scope and display precision.

## Evidence and prior knowledge

Memory query `consumption matched hours reset model totals` found bounded reset jitter, integer-microsecond conservation, and chronological reset replay findings. The reset-jitter reference and original report establish that exact reset seconds and stale counts must be checked; they do not justify replacing matched hours with model totals.

Initial helper reads encountered absent files: the Ponytail skill is in the plugin cache, not ~/.agents/skills/ponytail; this checkout has no AGENTS.md or .agent/PLANS.md; burn_report is a function in burn.py, not a burn_report.py module; no scripts/generate_fixture.py exists. Read the correct skill/contract and use delegated file mapping before further source reads. No application behavior or data was changed by these failed reads.

## Status and next steps

Root cause confirmed: the report combines two legitimate time scopes without quantifying the difference, while independently truncating durations to whole seconds. A frozen source CLI report for October 22 has 19,898,558,219 total microseconds and 19,891,621,219 matched microseconds in two reset cohorts of one pro/primary stream. The difference is 6,937,000 microseconds. There are no gap-excluded points; two boundary-excluded points remain valid. These exact values describe the later snapshot, not the earlier pasted output.

Five defining RED cases failed as expected: wide/narrow reconciliation, reset-cohort aggregation, parallel-stream protection and fractional-duration explanation. Added presentation-only matched/outside totals for one stream and an overlap warning for parallel streams. Added a note explaining fractional seconds; calculations, schemas, rates and stored data are unchanged. Focused GREEN: 183 tests passed, mypy passed 39 files, Ruff passed. Preserve pre-existing dirty work and raw private session data.

## Verification environment anomaly

Focused GREEN passed 183 tests; mypy passed 39 source files and Ruff passed. Full pytest initially reached 11% (124 progress dots), then progressed slowly to 207 passes. A separate process listing misleadingly showed no worker: commands run in separate PID namespaces. Parent access to the agent-owned exec session returned Unknown process id 3938; the owning agent's write_stdin correctly reported it still running. A quiet log or cross-namespace pgrep alone does not prove failure. Actual source CLI normal, width-32 plain and details commands all exited 0, preserving matched evidence and showing the new reconciliation.

The installed postmortem workflow reference mentioned `search --compact`, but the canonical helper rejected that option (exit 2). Use the canonical helper's supported option-free search; the documentation/helper mismatch does not affect application behavior.

## Resolution and runtime verification

The installed overview renderer matched the repository's original HEAD module before activation. After focused GREEN and independent review, atomically replaced only that module with tested source, preserving /tmp/codex-hours-overview-output-before.py as rollback. No package reinstallation, daemon restart or accounting-data write occurred. Installed/source renderer byte equality passed. Actual installed normal, width-32 plain and details CLI commands all exited 0; plain output was ASCII with maximum 32 columns, and details retained matched model mixes. The later live output showed 5h43m45s matched of 5h43m52s recorded, with 6s outside matched windows and the explicit fractional-second note. Live totals continue growing; these values are not the initial frozen snapshot.

Follow-up: preserve separate allowance streams and exact JSON microseconds. At the implementation handoff no commit or push had been requested or performed; subsequent session-only delivery is recorded in the plan. Register this reviewed report under local-work-scope-reconciliation in canonical postmortem memory; helper-read/PID-namespace diagnostic mistakes introduce no separate verified production remedy.

## Full-suite verification stall

The full suite stopped advancing after 207 of 602 tests, near test_fx.py::test_network_failure_preserves_valid_rate_and_reports_age, for several minutes. Read-only investigation found immediate mocked responses and a six-second production timeout, so this pause is not an intentional wait. Host-level inspection confirmed the owned pytest process (PID 784183, exact repository cwd and command) still existed and waited in ep_poll. This corrected the misleading cross-namespace process listing. Sent SIGINT only to that confirmed owned process: pytest exited 2 after 612.15s, with 207 passed and one warning from test_daemon.py::test_unknown_runtime_cwd_does_not_overwrite_new_rollout_cwd that the executor did not finish joining threads within 300 seconds. This is an incomplete suite, not a pass.

A bounded diagnostic (`timeout 60s .venv/bin/pytest -vv -o faulthandler_timeout=20 tests/test_fx.py`, isolated HOME/state) collected 13 tests, passed the first two, then reproduced the stall during pytest_asyncio runner teardown of test_success_is_exact_and_runtime_only. Faulthandler showed selectors.select -> asyncio run_forever/run_until_complete -> _scoped_runner teardown. The diagnostic intentionally timed out at 60 seconds (exit 124). No full-suite retry or unrelated FX change was made; exact underlying executor/runner cause remains unresolved. A fresh final overview run passed all 26 tests (exit 0, 0.36s), including the latest assertions. Focused renderer/accounting coverage, type checks, lint and actual installed reports remain green. Retained logs: /tmp/codex-hours-full.log, /tmp/codex-hours-fx.log and /tmp/codex-hours-overview-final.log. Investigate async teardown separately before claiming full-suite health.

## Session-commit privacy gate

The first pre-commit privacy check returned exit 1 with one home_path finding. No commit was created. The session plan included absolute machine-home locations used for canonical policy and learning evidence. Replaced its two absolute home prefixes with home-relative paths and restaged only the owned plan/report. The same exact-candidate privacy check then passed (exit 0). No private rules, approvals or active hooks were changed. Use home-relative paths in public evidence documents and rerun privacy checks after edits. Scope, checks and runtime correction remain unchanged; final commit must repeat the gate immediately before creation.
