# Atomic staging crossed the durable data boundary

A storage regression check caught temporary staging directories inside the Git-ready data root. Place all atomic-write staging beside the data root and rerun persistence checks before installing the daemon.

## Symptom, impact and evidence

On 2026-10-06, `uv run pytest tests/test_storage.py tests/test_observer.py tests/test_cli.py` failed one of 11 checks. `test_unique_native_records_idempotent_and_no_runtime_data` saw a .codex-time-stage directory inside its disposable data store. Only test fixtures were affected; no production store had been installed.

## Lookup and root cause

The canonical memory query `atomic staging directory data root` and paths-ownership boundary guidance apply: check resolved paths and artifact boundaries. The destination-relative parent.parent strategy moved ledger staging outside the root, but record files nested under records/day placed staging inside it. Confidence: confirmed by the failed directory inventory assertion.

## Status and next steps

Fix in progress: Store will own one staging directory beside its root and pass that location to every atomic write. Then rerun the failed check, full persistence suite and clean-data inventory. No data rollback needed; temporary fixture stores are disposable.

## Resolution and verification

Store now owns an external staging directory beside the data root for durable writes and a staging directory on the runtime filesystem for checkpoints. The original clean-data inventory assertion passes; storage/observer/CLI suite passed 11 checks (exit 0), and the separate-mount regression verifies /tmp data with /dev/shm runtime. Status: resolved, verified_fix at code/fixture scope. No existing data was altered by this incident. Canonical review records the reviewed report hash and scope; the broader storage lesson appears in the independent-review report and local lessons.
