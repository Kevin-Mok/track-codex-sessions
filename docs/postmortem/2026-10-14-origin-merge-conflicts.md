# Origin merge overlap

Combine the local watcher/cache work with incoming token reports and incremental tracking, preserving both histories. Resolve the overlapping sources, verify the combined behavior, and commit a normal merge before pushing.

## Symptom and impact

`git merge --no-commit --no-ff origin/main` stopped with ten conflicts. The clean local tip is `10f8c58`; fetched origin is `33ce9ed`, following token reporting `625e824` and daily readability `6da806f`. Conflict paths: README.md, docs/smoke-tests.md, src/codex_time/{cli,day_output,ingest,model_usage,storage,work_period}.py, tasks/lessons.md, tests/test_overview_performance.py. Local commits remain intact; no live installation, service or tracker data is changed.

## Lookup and applicability

Previously reviewed canonical fetch-before-ancestry guidance applies. Fetch succeeded before merge; the local tree was clean and both commit lists were inspected. Conflicts reflect overlapping independently authored features rather than lost data. No history rewrite or blanket side selection is appropriate.

## Resolution plan

Adopt incoming incremental ingestion/storage and token-aware reporting, integrate the local status command/cache and timing-reader contract, preserve recorded-time heading/readability and both documentation sets. Run full tests, lint, types, build, disposable token/report and watcher parity, plus independent review. Keep merge and matching plan/docs together. Current status: conflict resolution in progress. Canonical incident registration follows final evidence.

## Integration validation refinements

The first lint snapshot reported the newly combined daily-heading expression at 106 characters; the expression was wrapped into a named heading without behavioral change. The incoming parity harness still counted status as a sixth health alias; its mapping and assertion now preserve the five remaining aliases, with standalone status compatibility covered by the existing command-layout regression. The new token-bearing projects path intentionally loads full evidence, so projects was removed from the old timing-only test parameterization; incoming token CLI tests retain that evidence requirement. Strict mypy passed for 35 source files and wheel/sdist build passed. Full pytest/runtime verification remains in progress.

Initial full suite: 483 passed, one stale alias assertion failed in `tests/test_parity_harness.py::test_real_cli_parity_survives_migration_restart_and_aliases` (76.25s). The assertion expected status in aliases even though the delivered watcher contract intentionally repurposes it. Preserve report parity assertions; remove only that obsolete alias expectation and rerun the suite. The independent merge reviewer verified ingestion/model/overview paths are byte-identical to origin, projects retain token evidence, timing reads respect isolated partition restores, the private cache is unchanged, and the daily renderer differs only in heading. Remaining acceptance: fresh green checks, resolved Git index, merge commit and push.

Disposable token smoke passes (1,320,000 tokens, USD 2.91, CAD 3.9285 at 1.35); merged report parity passes all five retained aliases and report/native/migration checks. Watcher verification's first wrapper selected system Python; its child inherited that interpreter and could not import incoming ijson. Correctly launching the same verifier with the locked `.venv/bin/python` passed full replay with one session, zero warm/unchanged opens and bytes. No source/dependency change was required; this was an interpreter-selection harness fault. The dependency had already been installed by frozen offline uv sync. A fresh final full validation set follows.

Lookup `status health alias test contract` returned unrelated broad findings, so no inferred remedy was taken from them; the command-layout and existing cache incident document the actual migration contract. Interpreter lookup uses the actual subprocess/missing-dependency symptom; applicability requires the locked child interpreter rather than production installation.

## Final resolution and verification

All ten conflict paths are resolved and the index has no unmerged entries. Incoming streaming ingestion, model/overview accounting and work-period helper match origin. Integrated storage preserves v4/token evidence and the v5 partitioned layout; legacy timing reads cache by ledger stat, partitioned timing reads observe isolated restores, and the picker keeps its minute cadence. Daily token/readability output retains the recorded-time heading. Watcher status stays private and independent.

Fresh final checks: `.venv/bin/python -m pytest -q` — 484 passed in 74.30s; `.venv/bin/ruff check .` passed; `.venv/bin/mypy src` passed (35 files); `uv build --offline` built wheel/sdist; staged diff whitespace passed. Disposable token smoke: 1,320,000 tokens, USD 2.91/CAD 3.9285. Disposable CLI parity: passed=true for reports, migration/restart/native data and five retained aliases. Watcher full replay matched, with zero warm/unchanged raw opens and bytes. Independent evidence review found no source blocker. No live installation, service, Codex source or tracker-data modification occurred.

A read-only search guessed nonexistent optional dot_agents/AGENTS.md, then followed root routing to dot_codex/AGENTS.md; a no-match optional file search returned exit 1. These discovery outcomes made no changes and repeat prior optional-path discovery guidance.

No new reusable learning: overlapping feature merges require preserving public evidence contracts and validating the combined tree; interpreter/optional-path faults repeat existing environment lessons. Register the reviewed hash with that decision and check coverage. Merge commit and normal push follow; delivery outcome is recorded in the calling task.
