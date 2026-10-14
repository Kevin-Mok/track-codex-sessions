# Token-cost development verification

Track unexpected fixture and lint failures encountered while implementing token-cost reporting, distinguish them from intentional test-first failures, and record the focused corrections with fresh verification. The recorded development failures are resolved by the final source verification; installed live backfill remains a separate check in the active plan.

## Symptom and impact

- The pricing agent's first test collection used `request` as a parametrized argument. Pytest reserves that name, so collection failed before reaching the intended pricing assertion. The agent changed the argument to `request_tokens` and then observed the intended RED result. That subsequent deliberate failing test is expected test-first evidence; the collection failure is the incident recorded here.
- The ingestion agent's first Ruff run found 15 issues in new implementation/test code: import order, line wrapping, and underscore-related naming. The ingestion agent corrected those findings and reports a passing focused Ruff run. A lint failure does not establish a runtime accounting defect, and a passing pricing test cannot resolve ingestion lint findings.
- The parent's first integrated mypy run reported seven errors involving variable-name reuse in `reporting.py` and TypedDict update keyword arguments in `overview.py`. After corrections, `mypy src` passed all 25 source files.
- The parent's first integrated Ruff run reported 44 findings. Scoped formatting and import corrections reduced these to eight line-length and loop-lambda binding findings; the remaining corrections were applied, and the full Ruff check now exits 0.
- A pricing-agent inspection guessed `token_usage.py`; that read exited 2 because the actual module is `token_reporting.py`. This is a continuation of the known path-discovery slip, not an accounting failure. The finalized environment report is unchanged.
- The new smoke script first compared exact exported amount strings with `"2.91"`. The actual USD string was `"2.910"`, and CAD was `"3.92850"`; inspection confirmed correct numeric values. The assertion rejected equivalent Decimal representations. The correction compares Decimal values while preserving the exact export strings, and the smoke rerun now passes.
- The first full pytest regression run reported 296 passed and four failures in `test_day_reporting`. A coverage fix had created zero-duration child-only rows even when the child had no token evidence, changing legacy directory/session output shapes and positive-duration filtering. This unexpected broad regression is separate from the deliberate review RED tests.

## Lookup and applicability

Canonical postmortem-memory was consulted before this follow-up record. Queries `pytest reserved request parameter fixture` and `ruff import order line too long unused naming` returned general fixture, transport, and boundary findings but no exact matching reusable finding for pytest's reserved parametrization name or these Ruff rules. A focused inspection of finding text for `ruff`, `lint`, and `test collection` confirmed that the available findings describe other contracts.

`local-validated-fixture-assignment-order` supports the broader discipline of reaching the intended assertion with a valid fixture, but its Pydantic assignment-order remedy is not applicable to pytest argument naming. No unrelated remedy is being presented as a verified fix here. The corrections should preserve intended assertions and existing lint configuration. The additional guessed-module read matches the already inspected `local-discover-paths-before-reads` guidance: inventory actual paths before targeted reads.

Queries `Decimal numeric representation string equality fixture assertion` and `exact decimal numeric serialization trailing zeros` found no exact Decimal-specific finding. The inspected `ext-xml-boolean-semantics` guidance provides an analogous verifier principle: change an overly narrow representation assertion only after independent semantic evidence confirms the export. Its XML-specific remedy is not applied to JSON. Here `Decimal("2.91") == Decimal("2.910")` and `Decimal("2.910") * Decimal("1.35") == Decimal("3.92850")` pass, supporting a numeric Decimal assertion without rounding or altering exports.

Query `report grouping zero duration child rows aggregate missing coverage conservation` returned missing-source ledger and duration-conservation findings, but no direct remedy for legacy report row membership. Their specific fixes do not apply. Preserve established duration-only row membership while exposing uncertain usage through aggregate diagnostics/IDs; actual usage-only rows still belong in token reports.

## Cause and current status

The collection failure was caused by a reserved pytest fixture name in newly authored parametrization; the naming correction allowed the expected defining test to run. The pricing agent subsequently reports 28 focused tests passing, with its owned mypy and Ruff checks green. This establishes the focused correction without implying full-feature acceptance.

The first ingestion lint pass identified ordinary coding-style violations introduced in the new files; the ingestion agent reports its owned Ruff check green after correction. It also reports 74 focused tests and mypy over four owned modules passing. The integrated mypy findings are resolved by the passing 25-source-file check. The parent now reports integrated mypy, Ruff, and `git diff --check` all exit 0. The integrated typing and lint corrections are resolved at code-check scope. No lint rules or tests should be weakened to make the checks pass.

The smoke assertion failure is a verifier precision/representation mismatch, not an implementation money bug. Status: **verified_fix** at verifier/code scope after the smoke rerun passed exact totals of 1,320,000 tokens, USD 2.91, and CAD 3.9285, together with replay and read-only checks. The five independent-review defining RED failures were intentional; their corrected focused run passed 43 checks and is exempt from unexpected-failure incident recording.

The four broad regressions are caused by representing missing child usage evidence as new zero-duration report rows. The correction keeps unavailable orphan/child-only coverage in aggregate diagnostics and identifiers unless a root bucket already exists; actual token usage without duration remains visible. Status: **verified_fix**, with confirmed cause and code-level verification: 62 affected checks passed before the complete 302-test source run passed. The executable regression was the existing full-source pytest run, and the legacy assertions remain intact.

## Verification and remaining scope

The responsible implementation agents and parent reported these final source results from the repository, without sudo:

| Check | Result |
| --- | --- |
| `.venv/bin/pytest -q` | 302 passed in 37.12 seconds, exit 0. |
| `.venv/bin/mypy src` | Passed all 26 source files, exit 0. |
| `.venv/bin/ruff check .` | Passed, exit 0. |
| `git diff --check` | Passed, exit 0. |
| `./scripts/smoke-test.sh` | 248 tests passed in 36.81 seconds, plus token smoke verification of exact 1,320,000 tokens, USD 2.91, CAD 3.9285, conservation, replay, and read-only reports. |
| `uv build` | Source distribution and wheel built, exit 0. |

Focused evidence preceded that final run: ingestion 74 tests with owned typing/lint checks; pricing 28 tests with owned typing/lint checks; parent report checks 97; background-FX checks 16; and the corrected legacy day/report coverage checks 62. These focused counts overlap and are not summed. The five review defining failures followed by 43 passing focused checks, and two progress-module RED failures followed by GREEN plus 25 passing compatibility checks, were deliberate test-first evidence rather than unexpected incidents.

A complete v3 data/runtime backup was saved at `/home/kevin/.local/state/codex-time/token-reporting-backups/20261008T200217Z`. Package reinstallation and service startup exited 0, and installed verification found 27 Python/catalog files matching source. **Live backfill completion is not established by this report.** The active token-cost plan owns the continuing installed-service, backfill, runtime, and acceptance checks.

## Learning review

Decision: **no new reusable learning**. The guessed-path read repeats `local-discover-paths-before-reads`. The conventional fixture naming, typing/lint corrections, representation-aware assertion, and compatibility regression are fully recorded here, but do not justify widening unrelated existing finding remedies. The semantic verifier principle from `ext-xml-boolean-semantics` was applied only by analogy and independently checked with Decimal arithmetic; its XML-specific scope remains unchanged.

Register this report's current SHA-256 and physical alias in the canonical `/home/kevin/linux-config/dot_agents/skills/postmortem-memory/sources.json`, preserving all prior reports/findings. The handoff records the final targeted `check --postmortem` result and required `refresh-config` result. No installed skill copy is edited directly, and source verification is not promoted to live-backfill verification.


## Worktree follow-up: verification path typo

After moving the implementation into `.worktrees/token-cost-reporting`, the focused command named nonexistent `tests/test_overview_output.py` and exited 4 without running tests. `rg --files tests` confirms overview rendering coverage resides in `tests/test_overview.py`. Lookup query `pytest file or directory not found discover paths before reads` was checked before retry; the existing `local-discover-paths-before-reads` finding applies because the guessed file path, rather than implementation behavior, caused the failure. Correct the command to use the discovered path and retain every test assertion. Status: **verified_fix** at verification-command scope. The corrected command `.venv/bin/pytest -q tests/test_token_reports.py tests/test_fx.py tests/test_day_output.py tests/test_overview.py` passed 67 in 1.38 seconds, exit 0. No accounting impact. This repeats the existing path-discovery lesson; no new reusable learning.


The worktree follow-up Ruff run found one E501 line-length violation in the new smoke status string (mypy passed 26 files). This matches the already recorded lint/line-wrapping symptom and remedy; split the literal without changing its emitted text. Status: **verified_fix** at lint scope; `.venv/bin/ruff check .` and `git diff --check` exit 0 after splitting the string. The full worktree suite also passes 306 in 37.23 seconds, and both wheel and source distribution build successfully. No runtime behavior defect.


A final inspection guessed `src/codex_time/health.py` in a multi-file rg command; rg exited 2 because that path is absent, before the chained status command ran. The existing CLI path supplied valid health references. The previously inspected `local-discover-paths-before-reads` finding applies again: inventory files before naming them, and use the known `cli.py` health branch. No remedial retry of the missing path is needed. Status: **verified_workaround** at inspection scope; the independent installed `codex-time health --json` had already succeeded with a fresh 2026-10-08T20:20:09.938344+00:00 heartbeat. No application failure or new reusable learning.
