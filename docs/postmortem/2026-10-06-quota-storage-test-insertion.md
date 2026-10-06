# Quota storage test insertion failure

A test-only patch inserted additional functions into the middle of an existing test. Restore the original function body, run the intended RED test, and verify the complete suite before delivery.

## Symptom and impact

`uv run pytest tests/test_quota_storage.py::test_embedded_duplicate_observations_load_as_exact_union -q` exited 4 during collection with `IndentationError: unexpected indent` at line 178. No application or user data changed; the previous 31 focused storage/burn tests passed.

## Evidence and current status

The patch matched the first `store.save(ledger)` inside a test instead of its end. Its remaining indented statements appeared after another top-level test. Diagnosis is confirmed by the file contents. The original body has been restored; no product-code remedy was required for the collection failure.

The misplaced function body has been restored. The full suite subsequently passed 114 tests in 12.21 seconds and mypy passed 16 source files. Ruff reported an unused journal line-number variable and an unsorted test import block. The import order was corrected, and the intentionally used-after-loop diagnostic counter now has an underscore prefix. Fresh `uv run ruff check .` and `uv run mypy src` both exit 0; the latter checks 16 source files. No unresolved syntax or style failures remain.

## Lookup and next steps

Read the canonical postmortem-memory skill before remediation. Search for test insertion/indentation failures, record applicability, restore the misplaced test body, rerun the intended defining test, then run the complete suite and typed/lint checks. Record verification and reviewed source knowledge during this task.

Lookup query `patch test insertion indentation collect` returned `ext-python-integration-syntax`. Its reference guidance applies: inspect the assembled block and restore enclosing indentation before rerunning import collection. The exact offending suffix was visible after another top-level test. The subsequent embedded-duplicate test then failed for its intended assertion and passed after exact-dedup implementation. Ruff style diagnostics are direct, actionable evidence; use the recorded journal line number in the restore error and sort imports.

## Resolution and follow-up

Restore complete function boundaries when adding adjacent tests, and review the resulting assembled block. Existing `ext-python-integration-syntax` guidance covers the cause and remedy; no additional reusable finding is necessary. The product storage tests now cover append/restart idempotence, corruption refusal, legacy embedded migration, crash preservation, native identities, privacy fields, fingerprint restores and cache reuse. All failures and remedies here are code-scope evidence; installation is a separate parent-task verification.
