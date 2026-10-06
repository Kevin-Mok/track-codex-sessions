# Burn-report reset cohorts and latest allowance review

This report records two preactivation correctness defects found during review of reproducible allowance-burn reporting. Regression tests must establish that manual resets break attribution and stale readings cannot increase displayed remaining allowance.

## Symptom and impact

Independent review on 2026-10-06 found that grouping quota observations by reset identity before replay allowed an old cohort to return after a manual reset and bridge elapsed root work across that reset. The counterexample was A at 0 seconds/10% used, B at 100 seconds/0% and 200 seconds/1%, then stale A at 300 seconds/11%. The previous replay counted 400 summed root seconds from only 300 elapsed root seconds.

The latest-allowance selector also used the raw latest timestamp instead of accepted replay evidence: 10% → 11% → stale 10% in one cohort displayed 90% remaining rather than the supported 89%.

These were review findings before installation. No live ledger was damaged. Defining regressions `test_old_cohort_cannot_bridge_manual_reset_or_replace_latest` and `test_latest_does_not_report_stale_optimistic_remaining` were intentionally run RED; the implementation agent reports **2 failed** for these expected defects. Those deliberate RED results are evidence, not separate unexpected incidents.

## Lookup and diagnostic evidence

Before remediation, read the canonical postmortem-memory skill and searched `stale quota snapshot cohort reset bridge optimistic latest`. No directly applicable reset-cohort finding was returned. Existing snapshot-consistency and stale-display guidance establishes the need for accepted evidence but does not verify this report's remedy.

Inspected `src/codex_time/burn.py`: observations were collected independently by canonical reset cohort, and the latest field selected the raw newest reading. The regression sequences demonstrate that replay boundaries and latest selection must share the same accepted chronological evidence.

## Current status and next steps

Status: **verified_fix**; root-cause confidence: **confirmed**; verification scope: **code**. The second-pass same-timestamp reset ambiguity is also **verified_fix**; final frozen-tree source verification passed.

The correction retires a cohort when a distinct reset becomes active, ignores later stale returns to retired cohorts, and derives latest allowance from accepted non-stale observations. Reset-time jitter tolerance, conflict exclusion and explicit stale counts remain intact. Fresh `uv run pytest -q tests/test_burn.py` exited 0 with **14 passed**, including both review counterexamples, actual CLI checks and overlap tests. `uv run mypy src` passed **16 modules** and `uv run ruff check .` exited 0.

## Same-timestamp reset identity review

Second-pass review found that distinct reset identities recorded at the same timestamp were resolved by deterministic sort order even though the recorded evidence cannot establish their sequence. The new `same_timestamp_reset` regression intentionally failed RED: replay incorrectly attributed 2 percentage points where conflicting evidence requires 0. An earlier full suite passed 100 tests before this regression was added; that does not verify the new ambiguity.

Canonical lookup `same timestamp conflicting reset order evidence` found no directly applicable finding. Proposed correction groups a stream's timestamp observations before retirement, marks distinct same-timestamp reset identities as conflicting evidence, and breaks pair baselines instead of choosing a reset by sort order. The correction groups a stream's timestamp observations before retirement, records conflicting reset identities, and clears pair baselines. Fresh focused verification passed **15 tests**; final frozen-tree `uv run pytest` passed **101 tests**, mypy passed **16 modules**, Ruff and build passed, and `./scripts/smoke-test.sh` passed **47 checks**.

## Concurrent verification observation

A parallel smoke run observed the two intentionally RED review regressions while they were being added and returned two failures. This added no production defect; checks were switched to sequential execution with no test edits during verification. Canonical lookup `parallel test edits smoke running` found no direct matching finding. Final broad verification used the stable corrected tree and passed as recorded above; the concurrent run is not accepted as evidence of final health.

## Learning review

Reusable finding `local-quota-reset-chronological-replay` records reset retirement and accepted-latest selection. The parallel smoke observation adds no finding beyond running final checks against stable inputs. Canonical ledger registration records this report's current hash and alias.
