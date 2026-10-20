# Fix reset jitter consumption

Public home paths in this plan are anonymized examples. Restore consumption matching when one reset deadline varies by up to ten seconds. Add a regression, widen the fixed cohort tolerance, verify reports and update the installed CLI without changing timing data.

## Context and scope

The actual project is track-codex-sessions, not the calling workbook directory. Initial Git status has only two unrelated untracked files: docs/postmortem/2026-10-15-overview-task-handoff.md and prompts/reduce-overview-startup.md; preserve both. Commit/push was not requested during implementation; the subsequent commit-session request authorizes scoped delivery. Source changes belong in burn.py, its tests, README, tracking/smoke docs and this plan/incident. No ledger, daemon, schema or FX changes.

## Evidence and decisions

The Oct 20 report showed reset cohorts 1793116748 and 1793116755, 1 matched point / 1.593248611 hours, 2 excluded gap points and 1063 falsely retired readings. Raw deadlines span 1793116748–1793116756 with coherent 0–3% usage. The existing fixed five-second anchor splits that evidence. Use ten seconds from the original cohort anchor, not transitive chaining. Keep larger reset boundaries, same-timestamp conflict handling, stale percentages and ten-minute gap checks. Model duration remains all recorded root work; consumption remains matched work only.

Postmortem lookup: query `quota reset jitter consumption`; local-quota-reset-chronological-replay applies to preserving real reset retirement and conflict safety, but its five-second assumption does not cover this live eight-second drift.

## Checklist

- [x] Capture initial state and diagnose live evidence.
- [x] Add failing tests for signed jitter, fixed-anchor limit and real resets.
- [x] Change fixed tolerance and synchronize user docs/manual check.
- [x] Run focused tests, attempt full suite, type/lint checks and independent review.
- [x] Verify real Oct 20 report and install minimal verified change.
- [x] Update evidence, postmortem knowledge and handoff (targeted knowledge check below).

## Risks and rollback

An actual reset differing by <=10 seconds is indistinguishable from drift; do not infer individual model costs. Missing readings can still leave unmatched work. Keep the original cohort anchor so drift cannot chain without bounds. Revert the single tolerance change to roll back source; preserve installed burn.py before activation. Cache identity includes Python source metadata, so corrected reports invalidate automatically. No service restart is needed for a reporting-only module.

## Verification

RED/GREEN: `.venv/bin/pytest -q tests/test_burn.py -k reset_jitter`. Regression: full pytest, mypy src and Ruff. Runtime: overview and allowance on 2026-10-20, JSON row reconciliation and installed/source byte match; retain gap/no-work/manual-reset exclusions. Manual check: one same-cycle row despite seconds of reset drift; rate uses matched hours, which may still differ from total model work.

## Progress and review

Implementation, activation and focused verification complete. The user authorized privacy cleanup; its exact candidate now passes the safety gate.

RED evidence: tests agent ran `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider tests/test_burn.py -k reset_jitter`: exit 1, six signed-jitter cases failed because two rows were emitted; three existing/boundary cases passed. Implemented the one-line ten-second tolerance; subsequent GREEN evidence follows.

Source runtime replay succeeded (exit 0): one cohort, 2 matched points / 3.322572249 working hours, 0.601943269 pts/h, 1 genuinely stale percentage reading and 1 gap-excluded point. Total model work was 12008.522096 seconds. The remaining exclusion is supported by a 1012.536-second gap from 18:04:12.004Z (2%) to 18:21:04.540Z (3%); another 791.376-second zero-delta gap adds no excluded points. Missing observations still withhold time where required. Live data continues to grow, so compare durations from the same snapshot.

Installed verification: `codex-time overview day --date 2026-10-20 --plain`, `codex-time allowance day --date 2026-10-20 --plain` and overview JSON all exited 0. Latest captured matched duration 3h24m12s versus 3h25m39s total model work. One row accounts for 2 matched + 1 genuine gap-excluded point. Only reporting burn.py was replaced after baseline-byte identity checks; rollback copy /tmp/codex-time-burn-before-reset-jitter.py. Independent review found no code issue; corrected the two stale plan/prompt tolerance references it identified.

## Final verification and delivery

- Focused GREEN: `PYTHONDONTWRITEBYTECODE=1 HOME=/tmp/codex-consumption-test-home .venv/bin/pytest -q -p no:cacheprovider tests/test_burn.py tests/test_overview.py tests/test_overview_cache.py` — 85 passed, exit 0. Initial sandbox lock writes failed without isolated HOME and are recorded in the incident.
- `.venv/bin/mypy --cache-dir /tmp/consumption-mypy src` — 37 files, no issues, exit 0. `.venv/bin/ruff check --no-cache src tests` — passed, exit 0. `git diff --check` passed.
- Full 544-test suite reached 26% without displayed failures, then was deliberately interrupted at six minutes (exit 130). It is incomplete, not passing. Ruling: bound the unrelated broader run; all burn/overview/cache tests plus types, lint and actual installed CLI replay verify this reporting-only change. No further code change followed those checks.
- Independent review verified signed jitter, >10-second real reset preservation, original-anchor behavior, cache invalidation and schema preservation. Its stale documentation findings were repaired in the existing plan and prompt.
- Installed overview, allowance, allowance details and overview JSON exited 0. Details later showed 3h27m matched (ongoing work grows), 2 matched points, 1 genuine gap-excluded point, 2070 matched windows and only 1 stale reading. Source/installed burn.py byte equality confirmed.
- Delivered atomic plan, README/guide/smoke updates, repository lesson, incident and Cursor prompt at prompts/verify-reset-jitter-consumption.md. Suggested commit: `fix: tolerate quota reset timestamp jitter`. At the original implementation handoff, no commit or push had been requested/performed.
- No package rebuild, dependency change, daemon restart or configuration change. Installed rollback module is under /tmp as recorded above. Full-suite completion remains outside verified scope; rates remain low confidence and real resets within ten seconds are indistinguishable from jitter.

Canonical memory learning complete: sources.json and references/state-security.md append finding local-quota-reset-jitter-anchor and reviewed report hash 248455f7bbd2d130e3e5b1ff6c474f84c068dc862b5748961f11c9b5b0e085eb. Existing unrelated dirty knowledge entries preserved. `postmortem_memory.py check --postmortem /home/example/coding/track-codex-sessions/docs/postmortem/2026-10-20-consumption-reset-jitter.md` exited 0 with no errors, missing sources or unregistered aliases. The initial no-write marker assertion and subsequent successful repair are recorded in the incident.

## Session shipment checkpoint

The user invoked commit-session after implementation. Helper attribution is unavailable for wrapped tools; the recorded pre-write status and direct writes establish the scoped paths. Fresh focused checks again pass: 85 tests in 1.14s, mypy 37 files and Ruff clean. Both README gates report pass_no_change. The tracker privacy gate finds the same 35 failures in its unchanged HEAD and initial index, so it cannot safely ship this narrow change without separately authorized baseline cleanup. New delivery incident: docs/postmortem/2026-10-20-consumption-session-privacy-gate.md. No hooks or private policies are changed. The matching Linux-config learning milestone is independently scoped and privacy checked. Remaining tracker work is prepared but blocked; the user subsequently authorized baseline privacy remediation.

Exact isolated tracker candidate: 12 session-owned files; diff/check and README pass, privacy gate exits 1 with 34 remaining findings after neutralizing only owned documentation. The authorized cleanup subsequently cleared those findings; normal scoped commits and push are next. No pre-existing user file was staged into the candidate.

Authorized cleanup verification: 120 relevant tracker tests, mypy, Ruff and 45 shared-gate tests pass. The exact cleanup candidate now passes privacy checks using neutral public paths, three exact-byte public-source approvals and the unchanged existing identity policy. Two planned tracker commits preserve order: privacy prerequisite, then consumption fix. Full suite remains incomplete as previously recorded; refresh-config stopped on unrelated MIME drift without adoption.

## Final delivery milestone

The authorized prerequisite commits are `cc5f2e3` (shared exact-byte approvals/review records) and `6413191` (tracker privacy redaction). The final milestone is `fix: tolerate quota reset timestamp jitter`: defining signed/boundary tests, one-line implementation, truthful docs, smoke checks, reviewed incident and Cursor handoff are included together. Tracker120 tests, mypy37 files, Ruff and shared-gate45 tests passed; all14 affected report checks passed. Both root README gates pass. Gate the final exact tree, commit normally and push the complete verified series once per upstream. Source changes are complete; no remaining safety or scope blocker is known. The full suite and unrelated MIME refresh limitation remain explicit and are not represented as passing.
