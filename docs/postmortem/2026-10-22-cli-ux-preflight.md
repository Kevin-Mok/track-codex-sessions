# CLI presentation verification preflight

Record the authoring and environment issues encountered while verifying concise reports. Inspect documented helper paths, use the normal populated build cache with approved lock access, and distinguish live metadata changes from report regressions.

## Symptoms and impact

- A guessed optional helper filename exited 2 because it did not exist. Reading the documented entry point resolved the lookup; application data was unaffected.
- One overview patch was rejected before any write because its context omitted an f-string prefix. Re-reading the exact source line fixed the patch; there was no partial change.
- Restricted subprocess checks could not access the default uv cache or create the canonical writer lock. A temporary offline cache also lacked hatchling, so setup/build could not resolve their existing build dependency.
- One full-suite attempt returned incomplete output and was stopped with exit 130. It is not passing evidence. An early isolated run overrode HOME and is likewise excluded from final verification evidence.
- A live-output assertion used a title from a frozen snapshot and assumed identical formatting despite different rounding policies. The thread had been renamed independently; its stable ID and recorded usage remained the same.

## Diagnosis and resolution

The helper-path issue came from guessing instead of inspecting the documented entry point. Patch rejection was an exact-context authoring mistake. Existing inspect-before-edit/path-discovery guidance covers both; no new product defect was found.

Writer locking deliberately uses `Path.home() / '.local/state/codex-time/locks'` regardless of XDG_STATE_HOME or --state-dir. Restricted runners therefore need approved access to that path even when fixture history/state are temporary. Preserve HOME/XDG. Use the populated default uv cache for offline setup/build; changing application storage code is unnecessary.

The approved disposable replay passed without personal-data access or fixture-storage mutation. Final verification uses unchanged HOME/XDG and ordinary cache/lock access. Raw quality assertions in human-output tests were updated for the intentional readable-caveat contract, while raw evidence remains asserted in JSON. Ruff findings and one stale exact-wording assertion were corrected before the final run.

Compare layout using frozen JSON and identify live results by stable ID. The history polish reuses the established duration formatter for consistent seconds and visible fractions. It also collapses zero-activity rows into a count while details/JSON preserve the full selection.

## Verification and status

Status: verified environment workaround and completed presentation changes. Fresh final pytest passed 572 tests in 88.14 seconds; mypy checked 39 source files; Ruff and offline wheel/sdist build passed. Final installed/source bytes match all 11 changed modules. Synthetic token replay verified 1,320,000 tokens and USD 2.91/CAD 3.9285, all periods, descendant attribution, auto-review exclusion and idempotence.

No accounting/storage fix, migration or daemon restart was needed. The active plan records installed display checks and commit validation. Canonical hash/alias registration has an explicit no-new-learning decision; installed skill copies are not edited. Retain this resolved incident with its implementation and plan.
