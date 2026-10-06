# Model report subsecond conservation

Fix model-report arithmetic so splitting working intervals does not change their counted duration, including subsecond turns and picker totals.

- Symptom: independent review reproduced a 0.3-second turn split at 0.1 seconds producing model total_seconds 0.30000000000000004 versus base report 0.3.
- Impact: floating representation discrepancy violates conservation; no durable timing or native records change, but picker also summed split durations.
- Evidence/root cause: converting each split timedelta to a binary float before aggregation introduces order-dependent rounding. Exact decimal 0.1 + 0.2 also cannot equal 0.3 in binary-float summation.
- Lookup: postmortem-memory search “float duration exact microseconds conservation”; no directly applicable exact-duration finding. Reviewed source uses UTC datetime/timedelta with microsecond resolution.
- Resolution/status: verified fix (code). Two fractional RED regressions reproduced 0.30000000000000004 and 2.9999999999999996 versus unsplit totals. Integer-microsecond aggregation fixes total_seconds and supplies exact working_microseconds/total_microseconds fields; picker totals use original unsplit work. JSON/CSV export exact units. Focused regressions passed and full pytest passed 86 tests (exit 0); mypy, ruff, build and isolated smoke (32 tests) passed.
- Follow-up: retain timestamps/native projection identity; verify all regression checks and installation before final claims.

Additional review finding: rollout contexts can precede a SQLite-only timing fallback. Scan queued the model context, metadata created the stable turn afterward, and unchanged offsets meant it was never attached. Add a read-only pending-evidence reconciliation after metadata refresh and on every scan; verify with an actual SQLite fixture and repeat import. This is a second report-projection correctness defect, separate from numeric rounding, within the same review fix pass.

SQLite-only turn RED failed with an empty model_contexts list. `reconcile_contexts` after metadata refresh and on each scan now attaches available evidence; real SQLite import/reimport test passes with database bytes unchanged. Native projection bytes/filenames remain unchanged by model backfill. Human real-session checks are documented, not executed.
