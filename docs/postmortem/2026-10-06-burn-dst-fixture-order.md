# Burn-report DST fixture assignment order

This report records a test-fixture setup failure while adding reproducible quota-burn tracking. Correcting the fixture must preserve the production timestamp-order validation and then verify the intended DST behavior.

## Symptom and impact

On 2026-10-06, `test_toronto_dst_uses_elapsed_time_and_unknown_mix` failed during fixture setup with Pydantic validation error `turn end precedes start`. The test moved `Turn.start` from October 6 to November 1 while its original October 6 `end` remained set. The intended burn-report DST assertion was never reached; this was an unexpected fixture failure, not the feature's deliberate TDD RED.

## Lookup and diagnostic evidence

Before fixture remediation, read the canonical postmortem-memory skill and searched `pydantic validate_assignment fixture end precedes start`, then narrowed to `pydantic assignment`. No Pydantic assignment-specific finding matched. Reviewed `references/api-contracts-fixtures.md#local-malformed-persistence-fixture` and the existing fixture-precondition guidance: both apply to failures before the intended assertion, but neither establishes this fix.

`src/codex_time/models.py` enables `validate_assignment=True` on the shared model. `Turn.ordered` rejects a non-null end before start. The fixture's sequential start/end update transiently violates this invariant even though its desired final dates are ordered. Production validation is behaving correctly.

## Current status and next steps

Status: **verified_fix** for the DST fixture; root-cause confidence: **confirmed**; verification scope: **code**. Final frozen-tree source verification passed.

The fixture repair clears its optional end before changing start, then assigns the new end. The timestamp validator and the DST/Unknown-mix assertions remain intact. The main implementation agent reports `uv run pytest -q tests/test_burn.py` exited 0 with **10 passed**, and `uv run mypy src` passed **16 modules**. A fresh focused rerun after review corrections passed **14 tests**; `uv run mypy src` passed **16 modules**, and `uv run ruff check .` exited 0. Final frozen-tree verification: `uv run pytest` **101 passed**, `uv run mypy src` **16 modules passed**, `uv run ruff check .` passed, `uv build` passed, and `./scripts/smoke-test.sh` **47 checks passed**.

## Secondary style-gate finding

The first Ruff check found E501 at `src/codex_time/burn_output.py:24`: 102 characters exceeded the configured 100-character limit. Before remediation, canonical memory search `ruff E501 line too long` found no applicable line-length finding. The minimum correction splits the f-string across source lines without changing rendered output; `uv run ruff check .` subsequently exited 0. This routine formatting oversight adds no reusable finding beyond running the repository gate.

## Timestamp-spelling fixture correction

An intermediate latest-reading assertion compared an ISO string ending `+00:00` with Pydantic's canonical `Z` serialization for the same instant. The fixture now compares parsed datetimes; it preserves the intended instant assertion. Canonical lookup `ISO datetime Z +00:00 spelling test comparison` found no directly applicable finding. This serialization-spelling oversight adds no finding beyond comparing semantic timestamps when spelling is not the contract.

## Learning review

Interim review: focused fixture verification passed. Existing setup-boundary guidance is applicable; reusable assignment-order finding `local-validated-fixture-assignment-order` records the verified correction. The style-gate symptom has an explicit no-new-learning decision. Canonical ledger registration tracks this report's current hash and alias. No app source, live ledger or installed service was changed by this incident-recording task.
