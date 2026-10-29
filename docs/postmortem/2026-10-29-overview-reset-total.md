# Overview hides usage before an allowance reset

Track diagnosis and verification of a combined observed-usage summary across allowance resets.

## Symptom and impact

The October 29 overview showed 99% remaining / 1% used after a manual reset, with prior-cycle consumption listed separately. No period usage total explained the reset. Source investigation confirms reset cohorts survive; presentation omits the combined total.

## Evidence and applicability

User output has two reset identities, matched points 4 + 1, one gap-excluded point and 66 cross-day points. Existing renderer displays the latest accepted reading as its balance. Postmortem lookup query `codex-time allowance reset consumption` found local-quota-reset-chronological-replay and local-quota-reset-jitter-anchor: those protect cohort accounting; they do not supply the missing combined presentation. Keep their safety rules unchanged.

Initial investigation also hit unavailable Git metadata in the workbook workspace, an older postmortem helper rejecting --compact, and absent optional instruction paths. Read-only diagnostics located the actual CLI checkout and used the older helper without that flag. No data was modified by these unsuccessful reads.

## Status and next steps

Implement a tested presentation-only summary for a single allowance stream. Include observed unmatched points, explicitly exclude cross-day deltas, and label current-cycle balance. Verify installation separately. No inference that a reset means 100 points consumed.

## Validation in progress

Defining RED: 4 expected failures and 1 parallel-stream guard passed. Implemented renderer: fresh overview 33 passed; overview plus burn 57 passed. Ruff reported a two-character line-length excess, now wrapped. Mypy attempted a read-only cache path and failed to open its metadata database; retry with a writable temporary cache. A 90-second full-suite run timed out with failure markers but no summary; rerun fail-fast to identify failures instead of assuming the known teardown issue.

The focused integration retry exposed read-only sandbox writes to the global writer-lock directory (`~/.local/state/codex-time/locks`), in two existing burn integration tests and the synthetic CLI fixture setup. This is a filesystem restriction, not a renderer assertion failure. Ruff now passes; mypy with a temporary cache passes all 39 source modules. Retry the fixture under an isolated writable XDG state directory and test integration under normal approved filesystem permissions.

## Resolution and final verification

The renderer now labels Current cycle balance and combines observed matched, gap and no-work points for the selected day/week/month across distinct reset cohorts. Cross-day deltas remain excluded with an explicit partial-total warning; missing reset observations are not filled with invented consumption. Parallel streams and all-time snapshot behavior are unchanged, as are journal data and JSON schemas.

Final focused suite: 81 passed. Full suite with normal approved filesystem access: 627 passed in 83.94 seconds, exit 0. Ruff passed; mypy passed all 39 source files using a writable temporary cache; diff hygiene passed. The earlier read-only global-lock failures disappeared under approved filesystem access.

Offline uv reinstall succeeded. Installed renderer equals tested source. Live installed October 29 report showed 7 points across 2 cycles (5 matched + 2 unmatched), current balance 2% used, and 66 cross-day points explicitly excluded. Three installed CLI fixture runs (normal, 32-column plain, details) showed 106 points across 2 cycles while current balance remained 8% used. No history was rewritten, observer restarted, commit created or push performed. Remaining risk: rounded or absent readings prevent an exact consumption total.

Learning decision: no new general remedy beyond the reviewed separation of allowance snapshots, reset cohorts and matched work. The presentation-specific regression and local lesson capture this missing period total. The reviewed hash is registered in the canonical postmortem ledger; its targeted check is the final memory verification.
