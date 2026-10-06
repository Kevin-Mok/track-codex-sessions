# Maintain reproducible allowance tracking

Use this handoff to review or extend Codex Time's allowance-burn workflow while preserving the existing timing ledger. Read the linked plan, reproduce the defining fixtures, then compare the installed report with saved numeric evidence.

```text
Work in the track-codex-sessions checkout. Follow applicable AGENTS instructions.
Read plans/codex-model-burn-tracking.md, README.md, docs/model-burn-tracking.md,
and docs/smoke-tests.md. Preserve existing work and capture git status before
modifying tracked files if this directory has become a Git repository.

The user wants allowance percentage points per summed root working hour, with
reproducible workload comparisons using model + reasoning mixes. Quota is
account-wide: never apportion a mixed percentage drop to individual models.

Inspect models.py, ingest.py, burn.py, burn_output.py and cli.py. Ledger v3
keeps quota observations in memory; Store persists an append-only validated
quota-observations.jsonl journal. Include ledger and journal in snapshots and
fingerprints; migrate embedded v3 without losing evidence. Checkpoint v3 backfills once and stays
incremental. Preserve lifecycle timing, wait subtraction, latest-start turn
ownership, child exclusion, native projection identity, privacy and read-only
Codex observation. Manual reset changes start fresh baselines, retired resets
cannot return, jitter <=5 seconds shares a cohort, stale decreases cannot
inflate remaining quota, simultaneous conflicts break attribution. Calendar
boundaries and long gaps are not prorated. Missing evidence is unavailable.

Write defining regressions and observe RED before behavior changes. Run:
uv run pytest
uv run mypy src
uv run ruff check .
uv build
./scripts/smoke-test.sh

Verify installed command/service only after backing up the ledger with an
explicit fail-fast guard; prefer stdlib for backup or uv run for app imports.
Global --timezone precedes burn. Example:
codex-time burn week --date 2026-10-06 --json
Report numerator, exact working_microseconds, model/reasoning mix and excluded
points. Update docs and ExecPlan with implementation and fresh verification.
Do not auto-commit/push or create worktrees.
```

Suggested Conventional Commit: `feat: track Codex allowance burn`.
