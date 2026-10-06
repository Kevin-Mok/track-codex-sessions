# Burn installation backup preflight environment

This report records a failed backup preflight during installation of allowance-burn tracking. Establish the actual backup and ledger state before accepting installation verification, and make operational preconditions fail closed.

## Symptom and impact

On 2026-10-06, installation preflight used system `python` to import `codex_time.storage` while deriving the ledger backup path. The application is managed in its uv environment, so the command failed with `ModuleNotFoundError`. The shell sequence lacked fail-fast handling and continued into setup: setup succeeded and restarted the user service even though the intended pre-install backup had not been proven successful.

No successful original pre-install backup is claimed. Restart could have initiated a history scan and ledger upgrade, so the implementation agent checked the actual version and secured a standard-library-derived backup before the first upgrade save. Backup recovery and final installed-service verification completed as recorded below.

## Lookup and diagnostic evidence

Read the canonical postmortem-memory skill and searched `ModuleNotFoundError system python uv environment shell fail fast backup`. No directly applicable finding was returned; narrowed lookup `ModuleNotFoundError` also returned no match. Diagnostic evidence establishes that this path derivation must avoid unmanaged application imports or explicitly use the managed interpreter. The failed import and subsequent setup output distinguish an operational precondition failure from an application installation failure.

## Current status and next steps

Status: **verified_workaround** for backup recovery; root-cause confidence: **confirmed**; verification scope: **workaround**. Installed-service activation is separately **runtime verified** after the journal correction; the original unchecked preflight attempt remains a historical failure.

The recovery command used standard-library `hashlib` and `set -e`, and secured the actual on-disk version-2 ledger before the daemon's first version-3 save. Backup: `/home/kevin/.local/state/codex-time/072d8e0b6245b3179be51bde/allowance-install-ledger-v2-snapshot.json`, mode **0600**, **37,678,191 bytes**, SHA-256 `8da48a2ffd72a92c60511c0cb4c54018564b5b1e8bffa9ed1c4f77866ebebb0e`. Timing rollback data is available; this is a recovery copy made after restart but before ledger upgrade, not a successful original pre-install backup. The subsequent journal installation used a checked pre-migration backup: `/home/kevin/.local/state/codex-time/072d8e0b6245b3179be51bde/pre-quota-journal-20261006T171158Z.json`, version **3**, **112,899,883 bytes**, mode **0600**, SHA-256 `0ecf944c43b5e35af9898a764b2bb3de6ea06cf6f8a0a2129adc4caa2da6d749`. All pre-migration quota observations survived. Future setup must require checked backup success before continuing.

## Final installation verification

Fresh source gates exited 0: **114 pytest tests**, **16 mypy modules**, Ruff, build, and **60 smoke checks**. Installed source matched all **16 modules**. Installed day/week JSON and month CSV commands succeeded, and matched numerator/denominator/model-mix totals recomputed correctly. The user service was active/running with no live diagnostic. Ten heartbeat samples over ten seconds observed **5 distinct heartbeats**, maximum age **2.129663 seconds**, and no live diagnostic. Backup and journal preservation scope is recorded in the observation-latency incident.

## Learning review

Final review: finding `local-managed-backup-preflight` records the verified recovery and its limit. Canonical registration tracks the final report hash and alias. The original unchecked preflight path is not retroactively repaired by successful recovery; managed interpreter selection and checked preconditions remain the prevention rule.
