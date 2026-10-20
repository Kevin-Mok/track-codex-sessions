# Consumption undercount from reset timestamp jitter

Investigate why allowance consumption showed 1h35 matched work while model work exceeded three hours. Trace the saved quota evidence, reproduce the cohort split and verify a bounded tolerance correction.

## Symptom and impact

Oct 20 overview displayed two identically labelled reset rows: one point matched over 1.593248611 hours and two points excluded across gaps. The first row discarded 1063 readings as retired. Total model work was 11862.707096 seconds at investigation time; the scopes legitimately differ, but the cohort split was erroneous.

## Evidence and diagnosis

Weekly pro/primary deadlines were 1793116748, 1793116751, 1793116752, 1793116755 and 1793116756, spanning eight seconds. Thousands of frequent readings followed a coherent 0–3% progression. The fixed five-second anchor in burn.py split the +7-second reading, retired the main cohort and discarded its subsequent evidence. A +8-second reading prolonged the wrong cohort. The sparse new cohort then produced a false gap exclusion.

Memory lookup `quota reset jitter consumption` found local-quota-reset-chronological-replay (verified_fix/code). Its chronological retirement safeguard is applicable to real resets; widening bounded timestamp jitter must retain it. No prior remedy establishes that five seconds covers this observed drift.

## Status and next steps

Confirmed cause; six signed-jitter regression cases observed RED (two rows instead of one); three boundary/existing cases passed. Implemented ten-second fixed-anchor tolerance; GREEN and installed verification subsequently passed; see resolution below. Preserve >10-second reset boundaries, conflict handling and gap exclusions. Do not replace matched work with all model work. No raw private session data is included here.

## Environment note

The calling workbook workspace exposes an empty .git directory; the first git-status command failed there. The actual tracker repository has readable Git metadata and two unrelated untracked files, recorded in the plan. No workbook files were changed.

Runtime verification initially used `python -m codex_time`, but this package has no __main__.py. It exited 1 without running the report; the subsequent JSON read also failed on the empty redirected file. Use the actual CLI entry point; this invocation error does not indicate an accounting defect.

Source runtime replay (exit 0) now emits one row: 2 points matched over 3.322572249 hours, 1 point excluded across a real 1012.536-second gap, and only 1 stale reading. That gap runs 18:04:12.004Z (2%) to 18:21:04.540Z (3%); preserving it is correct. Total model work at replay was 12008.522096 seconds. The old duplicate-cohort exclusion was misleading; genuine missing-reading exclusions remain.

Focused verification initially hit two sandbox-only failures: test_quota_ingestion_upgrade_privacy_archive_restart_incremental and test_actual_cli_json_csv_and_table_replay_same_saved_ledger could not create ~/.local/state/codex-time/locks inside Store.writer (Errno 30, read-only filesystem). Setting HOME=/tmp/codex-consumption-test-home isolated the test lock directory. The same focused suite passed all 85 tests; mypy and Ruff passed. This is a test environment constraint, not a change to production storage.

Activation: installed burn.py matched the original source SHA256 44a7ba0784d90ca7583d9d6acfa87a1decd0888dad87b909627255726ef6506c before replacing only that module with tested source. Original retained at /tmp/codex-time-burn-before-reset-jitter.py. No daemon restart, data rewrite or dependency change. Installed overview, allowance and JSON all exited 0. JSON has one cohort, 2 matched + 1 genuinely gap-excluded point, 3.412598611 matched hours vs 3.427554167 total model hours, and one stale reading; live durations continue growing. Cache invalidation was observed through corrected installed output.

## Resolution and final verification

Widened only the cohort anchor tolerance from five to ten seconds. Six new signed-jitter cases now pass; ±11-second new resets, retired returns, conflicts and genuine gaps remain protected. Focused GREEN: 85 tests passed, mypy found no issues in 37 source files, Ruff passed, and independent review found no remaining code issue. Installed reporting module matches source; actual overview, allowance, allowance-details and JSON exit 0 and reconcile the three used points into two matched and one genuinely gap-excluded point. Matching now includes over three hours rather than 1h35.

The unrelated full 544-test suite was deliberately interrupted after six minutes at 26%, with no failures displayed (exit 130, incomplete). This is not a full-suite pass. The focused accounting/report/cache regressions and actual installed replay establish the fix's verified scope. No data migration, service restart, package rebuild, configuration change, commit or push was performed. The original installed module remains at /tmp/codex-time-burn-before-reset-jitter.py for rollback.

Follow-up: retain the ten-second fixed-anchor boundary tests; inspect reset seconds/stale counts before attributing a future mismatch solely to missing observations. A real reset within ten seconds is observationally ambiguous; larger jitter still creates a separate cohort. Genuine missing readings and low-confidence account-wide rates remain limitations. Register this reviewed report and bounded-jitter guidance in canonical postmortem memory and run its targeted check.

Knowledge-registration verification: the first append helper asserted that its text marker was unique, but nested report fields also matched the unanchored marker. It exited before writing any knowledge bytes; targeted coverage correctly reported this new report unregistered. Use a line-anchored top-level array marker, preserve existing dirty entries, and rerun the targeted coverage check. This metadata-script failure did not affect the installed consumption fix.
