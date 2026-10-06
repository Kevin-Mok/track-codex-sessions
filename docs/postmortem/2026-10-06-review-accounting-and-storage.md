# Independent review found accounting and persistence edge cases

Review caught overlapping-wait accounting, malformed status metadata and atomic writes across different filesystems. Add executable regression cases, fix the boundaries and verify each case before enabling the daemon.

## Symptom and impact

Pre-installation review on 2026-10-06 reproduced three bugs only in disposable fixtures. Same-session turns spanning 0–60 and 30–90 with a wait at 20–40 totaled 80 seconds instead of 70. A naive heartbeat raised TypeError in status. Runtime checkpoints on /dev/shm with a data store on /tmp raised EXDEV. No production records had been created.

## Evidence, lookup and root cause

Defining tests reproduced the exact failures before fixes. Lookup queries: `overlapping intervals waits accounting`, `atomic staging directory data root`, `timezone naive datetime heartbeat`. Existing state/security and artifact-boundary guidance applies to validation and staging; no prior remedy proves session accounting. Root causes: wait subtraction was per turn rather than across the session union; heartbeat parsing accepted naive timestamps; one staging directory was reused across filesystem boundaries. Confidence: confirmed.

## Status and next steps

In progress: subtract the merged session wait set from all work pieces; require aware heartbeat timestamps; stage runtime writes on the runtime filesystem, with durable staging beside the data root. Rerun targeted RED reproducers and the full suite, then native-reader and service smoke tests.

## Follow-up and rollback

Tests remain as regression specifications. No existing data rollback is needed. Rebuildable native projections must always derive from the valid JSON ledger. Preserve recording and source timestamps through later reconciliation.

## Resolution and verification

All three review reproducers pass after the fixes: 70-second session union, safe stopped_or_stale status and cross-filesystem atomic runtime checkpoint. The focused accounting/storage/status/observer suite passed 21 checks (exit 0). Subsequent integration also preserves observation-gap provenance on restart, records numeric sample/read-latency uncertainty, and replaces coarse SQLite fallback with precise rollout timestamps without duplicate-start drift. Adapter source-priority checks observed RED then GREEN.

A further intentional PTY reproducer showed that a 200-character title plus long cwd hid timers at 80 columns. The picker now separates title/state, timers/quality and cwd into three lines; the original PTY reproducer and all eight presentation tests pass. Completed UI bug has the same pre-installation review scope and no production data impact. Automated actual-daemon/UI/restart and isolated native checks passed; final full-suite evidence is in the ExecPlan.

Status: resolved, verified_fix at code/fixture scope. Installed service activation is separately verified in the plan. Lessons are recorded in tasks/lessons.md; no crash times or user wait answers are fabricated.
