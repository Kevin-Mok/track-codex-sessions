# Reproducible allowance burn tracking

Extend Codex Time to persist allowance observations automatically and reproduce quota percentage-point burn estimates from its existing counted root working time. Install once, inspect daily/week/month reports, and export the evidence for comparisons over time.

## Purpose and outcome

`codex-time burn day|week|month` reports matched allowance drops per summed root working hour and model/reasoning workload mixes. Quota is account-wide; never apportion a shared drop to a particular model or claim causal efficiency. Keep gap consumption visible. Existing `models` reports continue to measure working time.

## Context and boundaries

Relevant code: models.py, ingest.py, model_usage.py, cli.py, storage.py and daemon.py. Existing v2 stores lifecycle/model evidence; quota was only a private dated read-only analysis. Initial `git status --short` confirmed this directory is not a Git repository (expected preflight, same as existing plan). Preserve all existing files and data; no worktree/commit/push. Do not alter timing, child exclusion, native projection, socket requests or Codex source files.

## Settled assumptions and design

- Unit is allowance percentage points per summed counted root working hour, including parent tools/delegation. Concurrent roots sum, children add no denominator.
- Persist only at, limit_id, plan_type, bucket name, window_minutes, resets_at, used_percent and fixed provenance. Both primary/secondary buckets captured. No prompts, token detail, auth/account identity or payload bodies.
- Ledger v3 upgrades v1/v2 without changing timing. Checkpoint v3 invalidates previous offsets once for available quota history; sources disappearing retain evidence. Repeated observations deduplicate exactly, normal scans incremental.
- Default weekly quota window 10080 minutes, limit codex; configurable window/limit and max gap (600 seconds). Keep streams/plans/reset cohorts separate; jitter <=5 seconds grouped. Changed reset identity starts a baseline. Same-reset lower values are stale and do not create rebound usage. Account/allowance size equality cannot be inferred.
- Rows per local day/reset cohort use adjacent snapshot intervals, fully within requested period and local day. Never prorate a shared quota jump at a calendar boundary. Exclude long gaps, no-work intervals, and crossing boundaries explicitly. Include zero-drop work; no sampled readings means unavailable, not zero.
- Account-wide scope across all dirs/archive states only. Show workload mix per model/reasoning, summed working microseconds, quality, sample counts and latest selected-window reading. JSON/CSV are reproducible projections of same rows; CSV mix encoded JSON. No exhaustion forecast.

## Implementation checklist

- [x] Read relevant code/docs/lessons and capture workspace preflight.
- [x] Define ingestion, reset/gap/mix accounting, exports/calendar/restart tests; observe RED.
- [x] Implement validated quota observations, one-time backfill, incremental ingestion and report/CLI.
- [x] Document exact usage, reproducible exports and grouped Action/Expected checks; extend smoke script.
- [x] Run full tests, mypy, Ruff, build, isolated smoke; independent review.
- [x] Backup ledger, update installed entry point/service and verify real backfill, health and accounting conservation.
- [x] Record evidence, remaining limits and rollback.

## Risks and rollback

Delayed/integer quota readings, missing sources, external activity and mixed work prevent calibrated individual model rates. Quota buckets might be absent; never fabricate one. Manual resets with unchanged reset identity cannot safely be distinguished from stale readings and are excluded conservatively. Large imports may delay heartbeat. v3 is additive but older binaries cannot read it; keep pre-v3 backup outside data root and stop service before restoring. Runtime checkpoint hashes protect restoration. Native ~/.timetrace stays untouched; all native reader checks isolated.

## Verification

RED: `uv run pytest -q tests/test_burn.py` before implementation. GREEN plus `uv run pytest`, `uv run mypy src`, `uv run ruff check .`, `uv build`, `./scripts/smoke-test.sh`. Fixtures cover privacy, primary/secondary, legacy/checkpoint upgrade, archive/restart/idempotence, resets/jitter/stale/conflicts, gaps/no-work/zero drop, waits/overlaps/concurrency/children/model switches/Unknown, calendar boundaries/Toronto DST and exports. Installed verification: `./scripts/setup.sh`, `./scripts/check.sh`, `codex-time status --json`, `codex-time burn week --json`; compare real v2/v3 completed working intervals from backup and new ledger.

## Progress and review

Design follows user clarification (manual reset; allowance pp per working hour). Use TDD and smoke-test capture skills, and focused docs agent plus independent review per supplied AGENTS policy. Existing analysis is a dated artifact; new method specifies stricter calendar-boundary exclusion so historical outputs can differ slightly. No unnecessary approval/commit/worktree workflow from lower-priority skills. No tracked configuration changes in this source-only workspace; refresh-config does not apply.

RED evidence: `uv run pytest -q tests/test_burn.py` exited 1 with 10 expected missing-feature failures. First GREEN attempt exposed an invalid DST fixture assignment order (not an app defect); postmortem lookup found no direct Pydantic fixture remedy, retained ordered-boundary validation and corrected fixture to clear end before advancing start.

Independent review found and reproduced retired-cohort bridging, stale optimistic latest, and same-timestamp distinct reset conflicts. Each defining regression was observed RED before correction. Replay now retires old cohorts chronologically, groups by timestamp before retirement, breaks pairs at conflicts, and uses accepted latest readings. Fresh focused verification: 15 passed, mypy 16 modules and Ruff pass (all exit 0).

Final source gates (exit 0): `uv run pytest` 101 passed; `uv run mypy src` 16 source modules; `uv run ruff check .` clean; `uv build` wheel/sdist; `./scripts/smoke-test.sh` 47 passed with native readers isolated. Independent review reran all 15 burn tests and cleared the three counterexamples. Actual installed entry point exposes burn flags and all 16 installed Python files match source bytes.

Install preflight used system Python for an app import and failed before backup; the shell continued setup. Recovery immediately captured the still-v2 on-disk ledger via stdlib in a fail-fast shell before the daemon first v3 save. Snapshot: `/home/kevin/.local/state/codex-time/072d8e0b6245b3179be51bde/allowance-install-ledger-v2-snapshot.json`, mode 0600, SHA256 `8da48a2ffd72a92c60511c0cb4c54018564b5b1e8bffa9ed1c4f77866ebebb0e`. Setup exit 0, service active; fresh heartbeat pending full scan. Postmortems track the incident, fixture and preactivation review fixes. Cursor handoff is [the prompt](../prompts/codex-model-burn-tracking.md).


## Runtime-driven revision

Installed backfill found 268,112 quota readings, much larger than the seven-day probe. Embedding all readings grew the ledger to 84.6 MB compact JSON; measured load 4.01s, incremental scan 1.06s, serialization 1.07s before pretty atomic writes. A stale heartbeat showed this can interfere with normal live sampling. Revise persistence before completion: in-memory Ledger keeps quota observations, but durable `quota-observations.jsonl` appends validated new readings under the same writer lock, while ledger.json retains timing/model state only. Fingerprints must include both sources; corrupt journal fails closed without truncation. Preserve embedded v3 evidence during migration, v1/v2 compatibility and native records. Cache reader dedup keys for the same ledger object rather than rebuild them each poll. Store/reader defining regressions precede fixes; full gates and installation health must rerun. Update data Git/snapshot/rollback docs to include the quota journal. Focused storage agent owns that boundary independently.

- [x] Verify append-only migration, journal validation/dedup/fingerprint and native preservation.
- [x] Recheck normal incremental cost, final gates, installation and live health after persistence revision.

Storage milestone: 12 defining journal cases pass; independent storage implementation verification full 114 tests, mypy 16 modules, Ruff exit 0. Migration journals already durable embedded observations before removing them from ledger.json (crash-safe ordering); new readings follow ledger save → journal append/fsync → runtime checkpoint. Journal fingerprints cache unchanged file hashes and detect external replacements, including same-size/restored-mtime content. Reader cached-index regression observed RED then passed; 16 burn tests now pass.


## Final verification and delivery

All final source commands exited 0: `uv run pytest` **114 passed**; `uv run mypy src` 16 modules; `uv run ruff check .` clean; `uv build` wheel/sdist; `./scripts/smoke-test.sh` **60 passed**, native-reader checks isolated from existing ~/.timetrace. Independent review verified reset/stale/conflict accounting, and parent inspected journal migration/append/fingerprint/native boundaries.

Final installation: fail-fast stop/backup/setup completed exit 0. Additional embedded-v3 pre-journal snapshot at `/home/kevin/.local/state/codex-time/072d8e0b6245b3179be51bde/pre-quota-journal-20261006T171158Z.json`, mode 0600, SHA256 `0ecf944c43b5e35af9898a764b2bb3de6ea06cf6f8a0a2129adc4caa2da6d749`. All 16 installed modules match source. Actual installed `burn day/week --date 2026-10-06 --json` and `burn month --date 2026-10-06 --csv` succeeded. Saved exports recomputed matched_points/working_hours exactly and model-mix microseconds conserve the selected denominator. Live-account values are omitted from this public record; installed output explicitly identified overnight consumption as boundary-excluded.

Migration audit: **268,207** pre-migration readings all retained in **268,213** journal rows (six new observations); **zero lost, zero duplicates**. Timing ledger reduced from 112,899,883 pretty-JSON bytes to 37,695,231 bytes; journal appends independently. Measured steady incremental scan **0.692s**, timing serialization **0.580s** (compact 25,026,016 bytes). Ten runtime heartbeat observations over ten seconds saw five distinct beats with maximum age **2.130s**, live diagnostic None. `./scripts/check.sh` exited 0, active service and running fresh heartbeat.

Preservation audit: all **42,472** completed pre-upgrade turns retain IDs, exact start/end, coverage and model contexts. Every existing wait retained; one additional historical wait was contained within an existing larger wait, so merged waits and counted working time remain identical. No changes to native record identity, existing ~/.timetrace, Codex sources, socket mutation policy or credentials.

Remaining limits: model mixes describe parent workloads, not individual model quota cost. Rounded/delayed/shared quota, unknown capacity/account changes, missing sources and observation gaps prevent calibrated reasoning costs or exhaustion forecasts. Same-reset declines remain conservatively stale; reset identity changes are baselines. Conflict flags denote unquantifiable evidence without inventing consumption. Root session hours sum concurrent work; child quota remains part of shared allowance. Reports read saved evidence and do not query an account.

Rollback: stop service, preserve ledger and quota journal together, restore the matching backup/version, reinstall prior app as needed. Older v2 binaries require the captured v2 ledger; a current-version data restore includes its matching quota journal and causes safe offset invalidation. No Git repository exists here; no commit/push/worktree performed. Keep this plan/docs with code if later committed. Suggested subject: `feat: track Codex allowance burn`.

Incident closeout: six living postmortems and canonical postmortem-memory records finalized; each targeted helper check exited 0 with no stale hashes/missing sources/contract errors. New fixture, reset-replay, guarded backup recovery and history-journal hot-path findings retain the appropriate code/workaround/runtime evidence scope. Canonical unrelated dirty work preserved.
