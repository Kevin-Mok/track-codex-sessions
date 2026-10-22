# Reconcile consumption and model hours

Trace the reported six-second difference, reproduce any accounting or presentation defect, and make the report explain its time totals without changing valid allowance exclusions.

## Context and scope

- User example: consumption rows total 5h26m8s; model rows total 5h26m14s. These figures alone do not establish an accounting defect: matched allowance windows can omit work before/after observations.
- Inspect burn matching, model attribution, duration formatting, and their report callers/tests. Preserve account-wide rates, reset retirement, genuine gap exclusions, JSON/CSV contracts, and stored evidence.
- Initial protected dirty files: README.md, docs/smoke-tests.md, src/codex_time/cli.py, tasks/lessons.md, tests/test_cli_friendly_output.py, tests/test_overview_read.py. Existing untracked latency/handoff plans, prompts and postmortems are unrelated.
- Initially no commit or push was requested; the user subsequently authorized session-only commit and push. No configuration refresh, package reinstallation or service restart is needed. Reversibly activate only the corrected installed renderer after focused checks and review, preserving unrelated pending edits.

## Assumptions and decisions

- Diagnose before changing calculations. Never substitute total model work for matched work in the consumption denominator.
- Keep changes local to the actual cause and documentation. Use frozen/sanitized evidence to avoid live-time comparison drift.
- Canonical ExecPlan contract read from ~/linux-config/.agent/PLANS.md; this checkout has no local .agent/PLANS.md.

## Ordered work

- [x] Capture initial Git state, read feedback/lessons, and consult postmortem memory.
- [x] Trace all callers and reproduce the discrepancy with exact durations.
- [x] Write and observe a defining RED regression if behavior needs correction.
- [x] Apply the smallest correction and update usage/smoke documentation.
- [x] Run focused checks, type checks and lint; exercise source and installed CLI output and plain/details modes.
- [x] Observe the full-suite exit and record any failures.
- [x] Review final diff, reconcile documentation, and record handoff evidence.

## Risks and rollback

- Matched hours legitimately differ from all work; parallel quota streams can overlap. Never present their raw sum as unique work unless proved disjoint.
- Independent rounding can also create display-only discrepancies. Preserve exact integer accounting and distinguish it from display precision.
- Live sessions grow during verification. Compare one frozen report when checking conservation.
- Rollback only this session's hunks; preserve every pre-existing change.

## Verification and review

Automated checks (no sudo, repository root): `.venv/bin/pytest -q tests/test_overview.py tests/test_burn.py tests/test_burn_output.py tests/test_model_usage.py tests/test_model_output.py tests/test_overview_cache.py tests/test_cli_friendly_output.py tests/test_overview_read.py`; `.venv/bin/mypy src`; `.venv/bin/ruff check src tests`; then `.venv/bin/pytest -q`. Set HOME=/tmp/codex-hours-test-home and XDG_STATE_HOME=/tmp/codex-hours-test-state for test isolation.

Manual CLI checks (no sudo, repository root; first exercised with PYTHONPATH=src, then repeated against the installed renderer):

1. `codex-time overview day --date 2026-10-22`: matched and outside work appear under consumption; existing rates, reset rows and model/reasoning work remain.
2. `env COLUMNS=32 codex-time overview day --date 2026-10-22 --plain`: the same reconciliation wraps within 32 columns and uses ASCII.
3. `codex-time overview day --date 2026-10-22 --details`: reconciliation plus matched mixes and timing evidence remain available. Live work totals can grow between commands.

Docs: README usage paragraph, allowance guide and existing grouped overview smoke check updated together. [Cursor review prompt](../prompts/reconcile-consumption-hours.md). Suggested Conventional Commit: `fix: explain allowance and model time differences`.

Memory lookup: `consumption matched hours reset model totals` returned local-quota-reset-jitter-anchor (verified_fix/runtime), local-duration-microsecond-conservation (verified_fix/code), and local-quota-reset-chronological-replay (verified_fix/code). Read bounded-jitter reference and original report: relevant diagnostic precautions, no established remedy for this six-second difference.

### Diagnosis and RED

- `burn.py:WorkIndex.add` clips work to accepted same-day observation pairs; `model_usage.py:model_report` retains all work. Both sum integer microseconds. `_working_duration` truncates fractional seconds independently in model/reasoning rows.
- Source CLI frozen Oct22 JSON (`PYTHONPATH=src .venv/bin/python -c 'from codex_time.cli import main; raise SystemExit(main())' overview day --date 2026-10-22 --json`, exit 0) reports 19,898,558,219 total microseconds, 19,891,621,219 matched across two reset cohorts of the same pro/primary stream, leaving 6,937,000 microseconds outside matched windows. Two boundary-excluded points remain valid; no gap-excluded points.
- New defining renderer tests: matched versus total/outside work at wide and narrow widths, reset-cohort aggregation, parallel-stream protection, and fractional-second explanation. Tests agent observed all five expected assertion failures (exit 1, 21 deselected).
- Decision: presentation-only correction; keep all accounting, schemas and stored data unchanged. Aggregate matched work only for a single allowance stream; do not sum potentially overlapping streams. Explain fractional-second truncation explicitly.

### GREEN and review in progress

- Tests agent: focused 183 tests passed, mypy passed across 39 source files, Ruff passed. Fresh final overview run passed 26 tests after the latest assertions. Full suite was attempted and remains incomplete as documented below.
- Frozen source rendering at widths 88 and 32: matched 5h31m31s of 5h31m38s recorded; outside 6s, with explicit fractional-second explanation. Width-32 plain output is ASCII; exact 6.937s difference remains in source JSON.
- Independent read-only review confirmed single-stream reset cohorts are disjoint under chronological retirement and parallel-stream sum is suppressed. Corrected README/guide scope to day/week/month with available readings; all-time retains only its latest allowance snapshot.
- No new dependencies, durable storage writes, calculation changes, migrations or service restart. Installed renderer matched the unmodified HEAD version (SHA256 6a1b65c2bafe7d9a86b8bf4316a021b5d43011f51e8c8ed78e3974cc4dee054d). Atomic replacement of that module alone passed sandbox approval and byte equality with tested source. Original is /tmp/codex-hours-overview-output-before.py. Installed CLI verification passed; unrelated pending source edits were not installed.

### Installed runtime and learning evidence

- Installed normal/plain/details commands each exited 0. Normal/details maximum width 81 columns; width-32 plain maximum width 32 and ASCII-only. Details retained matched model mixes. Later live sample: 5h43m45s matched of 5h43m52s recorded; outside 6s with fractional-second caveat. Exact live durations grow between snapshots.
- Installed renderer bytes equal tested source. Rollback: restore only the saved original renderer module from /tmp/codex-hours-overview-output-before.py; keep other installed files and durable data untouched.
- Canonical learning updated directly in ~/linux-config/dot_agents/skills/postmortem-memory/sources.json and references/artifact-verification.md, preserving pre-existing dirty state. Finding local-work-scope-reconciliation is verified_fix/runtime for the focused and actual CLI scope. Initial reviewed report SHA256 48f8d52e33b1cae56577471ac6c6f69446b91e0ba26e4637f594385eaee20ee8; targeted check exited 0 with no errors or missing aliases. Refresh the registered hash after final report updates.
- Full suite stalled after 207/602 passes; host inspection confirmed the owned process. After SIGINT it exited 2 at 612.15s, with one daemon-test warning about executor threads not joining within 300 seconds. A bounded FX-only diagnostic passed two tests then reproduced a pytest_asyncio runner teardown stall (faulthandler captured selectors/asyncio runner stack; intentional timeout exit 124). No broad retry or unrelated production fix. This limits full-suite confidence; exact underlying runner/executor cause remains unresolved. See the [living report](../docs/postmortem/2026-10-22-consumption-hours-reconciliation.md) and /tmp/codex-hours-full.log and /tmp/codex-hours-fx.log.
- Separate sandbox PID namespaces explain the initial misleading process listing. The canonical memory helper lacks --compact despite the installed reference advertising it; option-free search works. Neither diagnostic issue is an application accounting defect.
- README gate outcome: update_in_same_change; the existing recruiter hook, stack rationale, setup and usage remain intact, and the overview paragraph now matches the renderer. Smoke check updated in place. No tracked configuration changed, so refresh-config is inapplicable.

### Final handoff

- User-facing correction is implemented, independently reviewed, documented and active in the usual installed command. No accounting discrepancy was introduced or hidden; the report now quantifies differing time scopes and explains display precision.
- Final reviewed report SHA256 2e3dc517f698ee7fd7abe36a90c44f0f8a86b31d675b47f2f9107cd0e10e625d registered under local-work-scope-reconciliation. Targeted canonical memory check passed (exit 0, no errors/changed/new/missing/unregistered aliases). Unrelated canonical knowledge added concurrently was preserved.
- Final overview regression: 26 passed, exit 0; focused suite: 183 passed, exit 0; mypy and Ruff clean. Final installed/source byte equality and Git diff whitespace checks passed. Full suite remains incomplete with the documented reproduced async teardown stall; no full-suite pass is claimed.
- This session changed overview_output.py, test_overview.py, the allowance guide, in-scope README/smoke paragraphs, two appended lessons, this plan, its Cursor prompt, the living incident, and the required canonical learning entry/reference. Existing latency work remains intact and unstaged. No commit/push performed.

### Delivery milestone: fix: explain allowance and model time differences

- User invoked commit-session after the implementation handoff. Target is this repository's main branch and configured origin/main upstream; there were no pre-existing staged changes.
- Scope helper ran successfully but returned unsafe with no recognized writes/baseline because it did not recognize the tool-wrapped edits. Used the original pre-write status plus directly observed apply_patch operations as the supported fallback, without timestamp inference.
- Candidate scope: overview_output.py, test_overview.py, docs/model-burn-tracking.md, this plan, the Cursor prompt and living postmortem; only the allowance reconciliation paragraph in README, its existing overview smoke expectation, and two new lessons from baseline-dirty files. Preserve all latency-related hunks and existing untracked files. Canonical knowledge remains outside this repository's commit scope.
- Fresh commit checks: 26 overview tests passed, mypy passed 39 source files, Ruff passed; README gate pass_no_change. Prior 183-test focused/runtime evidence and incomplete full-suite warning remain applicable. No redundant full-suite retry.
- Delivery-reviewed incident SHA256 eef1742eca9df5cfeb07322c538aa03897fe67b633af8f41bd8af184fe6f194d registered in canonical learning; targeted check exited 0 with no errors. Earlier hashes above preserve the implementation milestones.
- Repository-local scope/privacy scripts are absent. Used canonical scope helper with --repo-root and canonical privacy gate with explicit --repo pointing here; retain active Git hooks and configured private rules. Review exact staged blobs and run the privacy gate immediately before committing.
- Initial privacy gate refused one home_path finding in this plan; no commit was created. Replaced absolute machine-home paths with home-relative documentation paths. Memory lookup privacy gate home_path public documentation found local-privacy-reviewed-content-approvals: relevant fail-closed/content-bound approval guidance, but no approval bypass is needed because the documentation can be sanitized. Preserve private rules and rerun the gate on the corrected staged bytes.
- Corrected exact-candidate privacy check passed (exit 0). Public plan paths are home-relative, private rules/approvals/hooks are untouched, and the final commit command repeats the gate on its final staged candidate.
- Implementation is complete; remaining delivery step is the scoped Conventional Commit followed by one ordinary push to origin/main. Report the resulting hash and push result in Codex output. No history rewriting or unrelated staging.

### Follow-up: emphasize the full total after resets

- User screenshot confirms the combined roughly 7h20m total is dim and easy to miss after reset rows. Existing top-of-report total is offscreen; add the full recorded total in bold cyan immediately under Model work and make the combined matched-time summary bold.
- Keep all calculations and quota rows unchanged. Scope: renderer, one actual ANSI-style regression, matching usage/smoke documentation and this living plan/report. Preserve all unrelated baseline dirties.
- [x] Observe RED for a multi-reset report whose model section lacks a prominent full total.
- [x] Apply minimal emphasis correction and run focused source checks.
- [x] Activate only the installed renderer after source checks; record final evidence and remaining full-suite limit.

- Previous milestone 06c35ff was committed and pushed to origin/main. This follow-up is an uncommitted display correction; preserve existing latency work and the prior committed evidence.
- RED: new multi-reset ANSI regression failed because Total recorded work was missing beside the model rows. GREEN: 55 focused output tests passed, mypy passed 39 modules. Initial Ruff B020 identified a loop variable reusing the headline label; renamed it and reran all focused checks (55 passed, mypy/Ruff clean). No new accounting logic or dependencies.
- Matching README, allowance guide, existing smoke expectation, review prompt and one lesson updated. Installed module replacement is reversible using /tmp/codex-hours-emphasis-overview-output-before.py. Retain the earlier documented full-suite async teardown limitation.
- Actual installed color/plain/details commands exited 0. With NO_COLOR explicitly unset for the color probe, ANSI decoding confirmed Matched work is bold and Total recorded work is bold cyan beside the model rows; neither is dim. Initial probe inherited NO_COLOR and correctly had no ANSI, so the diagnostic was corrected without changing app behavior. Plain output was ASCII and at most 32 columns; details retained matched mixes. Installed bytes equal tested source. README gate pass_no_change and Git whitespace check passed.
- Follow-up remains uncommitted; no new commit/push was requested on this turn. Suggested follow-up subject: fix: emphasize total recorded work after resets. Same three manual CLI checks above apply; use env -u NO_COLOR for an explicit colored diagnostic. Live total at verification was 7h29m44s, naturally later than the screenshot.
- Exact follow-up automated check: .venv/bin/pytest -q tests/test_overview.py tests/test_model_output.py tests/test_burn_output.py (55 passed), followed by .venv/bin/mypy src (39 modules, clean) and .venv/bin/ruff check src tests (clean), using the isolated HOME/state described above. Canonical reviewed follow-up hash c0279cb6c07d2137fc271f7c79d5e76cb7bd7d649ffc491e2489f62f4cfe7839; targeted memory check exited 0 with no errors.

### Delivery milestone: fix: emphasize total recorded work after resets

- User subsequently requested commit-session for this follow-up. Current main and origin/main both point to 06c35ff; no staged changes existed. Scope helper again reported unsafe/no recognized wrapped writes, so use the recorded baseline and directly observed edits.
- Include renderer, ANSI regression, allowance guide, living report, plan and review prompt; isolate only the new headline README paragraph, its overview smoke expectation and the period-total lesson. Exclude all pre-existing latency work, newer implicit-date edits from another task, and external canonical knowledge.
- Fresh checks passed: 55 focused tests, mypy across 39 modules, Ruff, README gate pass_no_change. Prior installed ANSI/plain/details verification remains valid. Preserve the recorded incomplete full-suite limitation.
- Review the nine-file staged candidate and run the canonical privacy gate with explicit --repo immediately before the scoped Conventional Commit. Next delivery step is one ordinary push to configured origin/main; report the resulting hash and push status without rewriting history.
