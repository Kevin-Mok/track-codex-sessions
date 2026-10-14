# Commit and push the dirty worktree

Review every dirty path, validate the existing work, commit coherent groups in prerequisite order, and push the complete series once to `origin/main`. Preserve other worktrees and live tracker data.

## Scope and decisions

Initial status contains 15 modified and 18 untracked files, none staged. All are reviewable application, test, documentation or prompt sources. No tracked AGENTS.md or .agent/PLANS.md was discovered. Default collaboration mode is active; no Plan Mode switch is available. The latest explicit commit-plan-push request authorizes delivery of earlier assessment and implementation work despite historical no-commit notes.

Commit 1: `fix: clarify recorded daily working time` — heading, defining test, matching daily plan/postmortem, daily smoke guidance and README daily-format description.

Commit 2: `perf: cache session state and prune overview history` — resource diagnosis, private on-demand session state, stat-based ingestion, lightweight timing/health reads, conservative calendar filtering, regression tests, verification scripts, resource plan, README/smoke guidance, prompts and backlog. These share a living resource plan and CLI contract; keep them together so the plan describes the implementation present in the commit.

Include this delivery plan and matching status updates with both milestones. No secrets, generated output or runtime caches are eligible. Python application changes are not tracked configuration changes; refresh-config is inapplicable. No installation, daemon restart, v4 merge or history rewrite is planned. Source cache activation on the installed v4 remains separate.

## Checklist

- [x] Capture initial status, branch and upstream before writes.
- [x] Review source diffs, companions, history, instructions and applicable lessons.
- [x] Consult sandbox incident knowledge and record approved-route workaround.
- [x] Complete fresh pytest, Ruff, strict mypy, build and artifact checks.
- [x] Complete README gate and read-only cache review.
- [x] Stage inspected daily group and commit milestone 1.
- [x] Stage inspected resource group and commit milestone 2.
- [x] Review residuals and attempt one push of the complete series (rejected non-fast-forward).

## Risks and verification

Main uses ledger v3; installed token build uses v4. Exercise checkout behavior only with isolated inputs and use the schema-compatible performance verifier for installed data. Preserve conversation privacy: output only metadata/parity, never live status message bodies. Earlier RED evidence remains in daily/resource plans; no implementation is being authored during delivery. Run a synthetic status cold/warm/full-replay check and installed frozen future/DST month overview parity. Rollback is an ordinary future revert of selected commits; no destructive history operations.

## Review notes and evidence

README skill gate: review truthful opening/stack/installation/day-to-day flags against CLI sources, including status alias migration and v4 compatibility. Existing opening/stack order is preserved. Scoped approved shell reads pass; default sandbox startup remains unavailable. New incident: `docs/postmortem/2026-10-14-commit-push-sandbox.md`.

## Milestone 1 — fix: clarify recorded daily working time

Completed heading/test/day-plan review. Fresh full suite: 265 passed in 24.49s; Ruff passed; strict mypy passed (21 source files); offline wheel/sdist built; diff check passed. Empty-data CLI rendered the new heading and explicit no-work guidance. Synthetic status verifier passed full-replay equality and zero-byte unchanged scans. Independent cache review: no blockers, 35 focused tests passed. README gate `update_in_same_change`: existing daily-format and cache/performance documentation repairs match source; stage daily-format repair here and resource coverage with milestone 2. Resource commit and one upstream push remain. Canonical sandbox incident no-new-learning registration and targeted check passed; external pre-existing ledger edits preserved.

## Milestone 2 — perf: cache session state and prune overview history

Milestone 1 committed as `48a8137`. Resource implementation and companion sources reviewed; no unsafe/generated paths found. Fresh main checks remain 265 passing tests, clean Ruff/strict mypy, successful offline wheel/sdist. Runtime evidence: one-file cold/warm/unchanged/full status replay agrees; warm/unchanged opened=0 and bytes_read=0. Installed schema-v4 frozen month containing DST fallback passes exact complete JSON parity: before 18.5216s, after 17.0709s; installation_changed=false. Cache review independently passed 35 tests with no blockers. README gate complete; cache privacy/alias migration and v4 compatibility accurately documented. Historical before/after and RED evidence remain in matching implementation plans.

Warning: external canonical postmortem-memory ledger changed after this task's successful narrow registration/check. Later checks reported missing registration for this task's sandbox report and the CTO overview report; a subsequent read found invalid JSON at line 9455. Preserve external unrelated work and leave final-hash registration/CTO coverage verification outstanding until that ledger is valid and stable. No product validation failed. See the living sandbox report.

Completed repository work has no implementation blocker. Remaining operational follow-ups: integrate source session cache with compatible v4 before installation; daemon whole-history persistence remains separate. No installed package/service/data was changed in this delivery. Rollback through ordinary revert; no schema migration. Commit this milestone, inspect final residuals, then perform one push to configured `origin/main`. Push outcome is reported in the final handoff; it cannot be recorded in this commit before it occurs.

Exact automated checks: `.venv/bin/python -m pytest -q`, `.venv/bin/ruff check .`, `.venv/bin/mypy src`, `uv build --offline`, `git diff --check`. Direct/manual plan: source daily report on empty temporary data, status JSON/plain with private runtime storage, and the disposable status verifier; installed overview verifier against frozen inputs for day/week/DST month. Matching README, smoke tests, watcher docs, incident reports and prompts ship in milestone 2. Cursor continuation prompts: `prompts/codex-time-session-cache.md` and `prompts/cto-performance-handoff.md`.

## Milestone 3 — docs: record rejected delivery push

Milestone 2 committed as `c51d2f1`; both implementation commits survived one rejected `git push origin main` (exit 1, non-fast-forward). Repository status was clean immediately afterward. Remote delivery is outstanding because origin/main has newer history; preserve local commits and leave incoming integration to a subsequent reviewed pass. No force-push or automatic history operation. This follow-up adds only the push incident and matching delivery status; README remains accurate (gate `pass_no_change`). No application changes or repeated application tests are needed. New report: `docs/postmortem/2026-10-14-delivery-push-rejected.md`.

Canonical memory lookup for push rejection now succeeds, so the earlier invalid JSON was transient external drift. Safely register both task-created incident reports by current hash using narrow latest-byte insertion and check coverage. Do not repair unrelated missing CTO learning or rewrite external pre-existing edits. Final repository residual review follows this documentation commit; no second push is attempted under the one-push delivery contract.

Final learning verification: sandbox current hash `d483a74688533380d57fb175aab0a89f0993fbe8a85fcbe656f26e4d004f05bf` and push report hash `8a0eb7905ff7f2eb40639deaa36b30bbd9549e45b49816897cf7ea4852722e5b` narrowly registered in canonical memory, explicit no-new-learning decisions retained. Both targeted checks exit 0 with no errors/changed/unregistered aliases. CTO incident targeted check also now exits 0. External drift warning is historical; no outstanding task learning update remains. Unrelated external ledger edits stay outside this repository's commits. Final blocker is remote non-fast-forward rejection alone.

## Follow-up — merge origin and push

Latest user authorization: merge with origin; prior push objective persists. Initial worktree clean at `10f8c58`, upstream `origin/main`. Fetched `33ce9ed`, including v4 token reports, daily readability and v5 incremental durable layout/streaming ingestion. This supersedes the earlier main-v3 integration limitation once the combined tree passes checks. No live installation/service change is authorized or required.

- [x] Fetch origin and inspect divergence (three commits on each side).
- [x] Prepare normal no-commit merge and inventory ten conflicts.
- [x] Reconcile watcher cache/timing reads with incremental storage and token-aware reports.
- [x] Preserve incoming streaming ingestion/readability, both documentation sets and regression coverage.
- [x] Run merged full tests/types/lint/build and direct disposable report/cache parity.
- [x] Review README and merge diff; prepare merge commit with matching plan and incident.
- [ ] Push normally and verify final state.

Resolution decisions: incoming scanner's bounded streaming/checkpoint backend supersedes the simpler local stat-skip implementation. Projects now require token evidence and must load full report data; timing-only history/sessions/model-time retain journal-free reads. Picker keeps the incoming minute-cadence snapshot behavior. Status retains the private on-demand cache and sessions-array contract. Preserve incoming token-cost fields, exact accounting and calendar guards. New living incident: `docs/postmortem/2026-10-14-origin-merge-conflicts.md`. Default mode remains active; no mode-switch tool available. Rollback of future committed integration is a normal revert, without rewriting either parent.

## Milestone 4 — merge: integrate origin tracking improvements

All ten index conflicts resolved. Independent source review verifies incoming streaming/token/report behavior and local watcher privacy. New partitioned timing regression ensures malformed quota/token journals do not affect timing and isolated session restore is observed without a layout change. Projects deliberately keep full token evidence; only obsolete projects timing-only expectation and status health-alias expectation were adapted. Five retained aliases remain verified. Matching watcher docs, current handoff prompts, README, smoke procedure and resource follow-ups reflect merged v4/v5 compatibility. README gate `update_in_same_change`: retain recruiter hook/stack/install/options and combine watcher privacy/command coverage with incoming migration guidance.

Fresh checks: 484 tests passed (74.30s), Ruff passed, strict mypy passed (35 files), offline wheel/sdist built. Token smoke verifies 1,320,000 tokens, USD 2.91, CAD 3.9285; actual report/native/migration/restart parity passes with five aliases. Watcher cold/warm/full replay agrees; warm/unchanged open/read zero raw files/bytes. Staged whitespace and >3 MB checks pass. No remaining implementation blocker or worktree conflict; normal merge commit and one push are the remaining delivery steps. No production activation is performed. Imported pyproject/lock changes are package dependencies, installed only into this project's frozen venv; no machine/dotfile configuration change is made.

Atomic integration plan: fetch → map independent overlap → resolve contracts → focused restore regression → full checks and disposable runtime parity → docs/incident learning → merge commit → push. Cursor continuation: `prompts/incremental-tracking.md`, `prompts/codex-time-session-cache.md`, and `prompts/cto-performance-handoff.md`. Automated commands are recorded above; direct checks use `scripts/token-smoke.py --executable .venv/bin/codex-time --scenario verify`, `uv run python scripts/verify-parity.py --plain --json`, and `uv run python scripts/verify-session-status.py`. Working directory: repository root; no sudo. Suggested/selected subject: `merge: integrate origin tracking improvements`.

Canonical learning finalization: merge incident current SHA-256 `c3685c62f91eb400c78af8dba1597ebafb9a396dfd004ae76fe3db87135f049e` registered with explicit no-new-learning decision; targeted check passed exit 0. Four incoming main-path aliases added to exact previously reviewed hashes. Two incoming chronological incremental reports reviewed and registered as repeating existing indexed persistence/streaming/restore/tooling guidance; both targeted checks passed. External canonical text and unrelated edits preserved; no outstanding task learning update.
