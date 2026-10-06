# Model usage time reports

Extend the tracker with model and reasoning attribution from rollout turn contexts, then rank working-time usage for calendar days, Monday weeks and months. Preserve existing timing and native records and verify totals with sanitized fixtures and the installed service.

## Purpose and observable outcome

`codex-time models day|week|month` reports model + reasoning working-time usage, descending known-model ranks and unranked Unknown time. JSON/CSV and the picker expose the same evidence. Defaults cover all directories/archive states in America/Toronto.

## Current context and scope boundaries

Read README, base plan, smoke tests, lessons, models, accounting, reporting, ingestion, storage, daemon, CLI and presentation. Initial `git status --short` returned 128: this workspace has no Git repository, as the base plan documents. Preserve all existing files; no Git initialization, worktrees, commits or pushes. No conversation bodies, SQLite current-model fallback, new mutating RPCs or existing native timetrace access.

## Assumptions and settled decisions

- Active Default mode cannot be switched; maintain this ExecPlan using the existing contract at /home/kevin/linux-config/.agent/PLANS.md.
- Keep timestamped content-free model evidence on each stable turn. Deduplicate identical timestamped evidence; collapse repeated settings in the attribution timeline while retaining timestamps to detect conflicting copies; resolve equal-timestamp conflicts to Unknown with a content-free diagnostic.
- First context applies at the turn start; later changed contexts apply at their recorded timestamps. Missing fields remain Unknown. Unmatched context IDs are retained in disposable checkpoints until a matching lifecycle or metadata turn exists; contexts without a resolvable ID are diagnosed.
- Use existing wait-subtracted segments and latest-starting owner. Model splitting is a report projection and does not change native record identity or timing.
- Upgrade validated ledger v1 to v2 on load, retaining waits/coverage. Rollout checkpoint v2 invalidates v1 once; reread available history without clearing ledger evidence. Subsequent scans remain incremental.
- Installation and user-service restart are requested; preserve data and existing native records. Human real-session waits remain manual checks.

## Ordered implementation checklist

- [x] Inspect workspace, context, preferences and required skills.
- [x] Write defining ingestion/migration tests, observe RED, implement context evidence and checkpoint upgrade.
- [x] Write defining attribution/accounting/calendar tests, observe RED, implement model report projection.
- [x] Write defining CLI/picker tests, observe RED, implement table/JSON/CSV and model display.
- [x] Update README, smoke docs/script and paste-ready handoff prompt.
- [x] Run full pytest, mypy, ruff, build, isolated smoke tests and independent review.
- [x] Reinstall and verify installed command, fresh user-service heartbeat/backfill; reconcile base plan evidence.

## Risks, protected state and rollback

Missing histories leave old work Unknown; never erase timing. Conflicting source evidence stays Unknown. Sampling flags/uncertainty remain visible; usage includes tools and delegated work and does not measure efficiency. Current installed service owns live data until setup restarts it. Legacy clients cannot read v2; rollback requires the old package plus a pre-upgrade ledger backup, or keeping the upgraded package. Native projections must remain unchanged by model attribution.

## Exact automated and manual verification

Observe RED with focused pytest tests before implementation. Cover mixed models/effort, within-turn changes including waits, repeated contexts/reimports/restart/archive moves, legacy/backfill/missing history, overlap ownership, concurrent roots/child exclusion, unknown/conflict, filtering, calendar year/month/Monday boundaries and Toronto DST, JSON/CSV/table equivalence and long metadata timers. Run `uv run pytest`, `uv run mypy src`, `uv run ruff check .`, `uv build`, `./scripts/smoke-test.sh`. Then `./scripts/setup.sh`, installed `codex-time models day --json`, `./scripts/check.sh` after initial backfill, and installed status JSON. Native checks use disposable HOME/config only. Human Action/Expected checks remain in docs/smoke-tests.md.

## Progress, evidence and review notes

Preflight: ingestion produces per-turn context evidence; model attribution consumes existing segments; reports and details consume attribution. Preserve timing and native identity by keeping model splits out of accounting.segments. Source intent is the supplied execution prompt; save a concise implementation handoff under prompts/.

Ingestion RED: `uv run pytest -q tests/test_model_ingest.py` failed 3 tests for absent model_contexts and v1 upgrade (exit 1). Ruling: retain repeated settings at distinct timestamps as evidence, while report timelines collapse them — removing these timestamps could hide conflicting source copies; storage cost is small per turn.

Ingestion GREEN: model/ingestion/storage suites passed 20 tests (exit 0). Report/CLI/picker RED: all 14 tests failed on missing model_usage module, models subcommand and SessionRow model fields (exit 1).

Report/CLI/picker focused GREEN: 25 tests passed, exit 0. First full pytest: 81 passed, exit 0. Strict mypy: 14 source files, exit 0. First ruff check found 49 style-only findings; formatter/import sorting reduced to one long output string, now split. Independent review delegated read-only. Docs and smoke runner updated by bounded docs agent, syntax check passed.

Independent review found two important defects: split float accumulation (0.3 versus 0.30000000000000004) and contexts queued before SQLite-only timing never attaching. Defining regressions failed as expected: 2 fractional tests and 1 SQLite import test (exit 1). Fix pass aggregates exact microseconds before converting seconds, exposes additive integer export fields, preserves unsplit picker totals, and reconciles pending contexts after metadata refresh. Ruling: exact conservation uses integer microseconds; decimal seconds remain compatible convenience fields — binary float row sums cannot be literally exact for arbitrary decimals; clients aggregating floats must use the exact units.

Installation first attempt: setup exited 0 but installed command still rejected models and exposed ledger v1 (stale cached wheel). Defining isolated real-uv setup test RED: second install printed old source after source-only edit (exit 1). Changed setup to refresh/reinstall only codex-time, preserving other tool dependencies; verify fresh installed runtime after GREEN. Pre-upgrade ledger backup saved with mode 0600 in runtime/pre-model-usage-ledger-v1.json.

Final automated command `uv run pytest && uv run mypy src && uv run ruff check . && uv build && ./scripts/smoke-test.sh` passed: 86 tests, strict typing across 14 sources, lint, both distributions, and 32 isolated smoke tests (exit 0). New fixture verifies native projection byte/filename invariance after model backfill. Independent review had no other material findings; both important findings have RED→GREEN regressions. Setup fresh rebuild test passed, real installation rebuilt wheel, installed models help and v2 schema passed, and all 14 installed source modules matched byte-for-byte. No tracked configuration changed; no refresh-config required. Canonical postmortem-memory reports/hashes/aliases and three applicable findings/guidance updated; targeted checks for all reports passed.

Installed/runtime verification passed (exit 0): `./scripts/setup.sh` rebuilt the local wheel, `./scripts/check.sh` reported active service + running heartbeat with live_diagnostic None. Snapshot: 4,730 sessions / 42,380 turns, 42,237 turns with recorded model contexts. v2 checkpoints retain file offsets for incremental scanning. Content-free diagnostics retain unmatched old lifecycle/model IDs; such work remains Unknown rather than fabricated.

One installed-ledger snapshot proved model/base report total_seconds and total_microseconds match for all three selected periods, including exact row-unit sums for day, week and month. Installed week JSON and month CSV exports passed calendar-boundary and exact-unit-sum checks. Live totals continue changing normally. Tests verify JSON/CSV/table parity on a stable fixture.

Preservation audit passed across all pre-upgrade IDs and 42,331 old completed turns: no IDs or wait/coverage evidence lost; completed starts/cwd unchanged. One existing metadata end estimate was precisely reconciled (+0.583s) and one completed turn gained a recorded historical wait. v2 checkpoint holds 4,734 incremental file offsets. Initial raw-equality assertion rejected these lawful corrections; validated evidence containment and marked metadata replacement proved preservation. Native projection invariance has a dedicated sanitized regression, and native readers only ran with disposable HOME/config/store. Human normal-session switches, approval waits and five-minute runs remain documented, not claimed as executed. No deferred code-review findings. Plans, README, smoke checks, reusable setup and handoff prompt reflect the implementation; no commits/pushes requested.

Rollback: stop service before using the content-free pre-upgrade ledger backup at `/home/kevin/.local/state/codex-time/072d8e0b6245b3179be51bde/pre-model-usage-ledger-v1.json` with an older package. Retain current v2 data when reinstalling this package. No sudo needed. Exact automated/manual test instructions and Conventional Commit suggestion are in the saved handoff prompt.

Audit incident and reviewed hash/alias registered with explicit no-new-learning decision; targeted check passed. Final user service remains enabled and running, with fresh heartbeat and no live socket diagnostic.
