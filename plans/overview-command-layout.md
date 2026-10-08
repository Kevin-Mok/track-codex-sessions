# Combined overview and clearer commands

Implement a single readable allowance and model-work overview, then expose clearer report names while silently retaining legacy commands. Verify accounting, rendering, exports and the installed executable without migrating data.

## Purpose and observable outcome

`codex-time overview [day|week|month]` defaults to today and shows recorded work, allowance balance, observed consumption and model totals with reasoning rows beneath each model. Canonical commands are overview, allowance, model-time, projects, sessions, history, health and resume; daemon/import-history and the no-argument picker stay unchanged.

## Context and scope

Reuse burn_report and model_report. Add overview.py and overview_output.py, wire cli.py, add focused tests, update README, smoke checks and current repository callers. Preserve all pre-existing dirty work (captured git status and `/tmp/codex-overview-baseline.diff`, with file snapshots under `/tmp/codex-overview-baseline`): README, smoke docs/script, cli.py, day_output.py, model_output.py, day/model tests, lessons, daily and model presentation plans, prompts and postmortems. No accounting/schema, daemon lifecycle or tracked configuration changes. No worktree, commit or push requested.

## Assumptions and decisions

- The supplied plan is the binding specification; execute in the existing checkout. Default mode is active, so maintain this decision-complete ExecPlan without switching modes.
- Resolve date once in the selected timezone and load the ledger once. Build allowance, model totals and reasoning reports from that snapshot using existing accounting.
- JSON keys: allowance, model_totals, reasoning. Reuse each existing report's complete schema. Do not add CSV to overview; existing CSV contracts remain unchanged.
- Model totals compute distinct sessions independently. Reasoning percentages retain the overall work denominator. Unknown models/reasoning remain visible; unknown models have no rank.
- Overview includes every directory/archive state and has no filtering flags. Allowance window/limit/gap controls stay available. Allowance cohorts remain separate and matched mixes appear only in details.
- Hidden aliases preserve raw argparse command values and dispatch through a canonical lookup, avoiding changes to callers that inspect parser results. Help explicitly lists canonical names only; alias-specific help remains usable.
- No package version bump is needed; reinstall with `--reinstall-package codex-time` and inspect from outside the checkout.

## Ordered implementation

- [x] Capture status, read source, active plans, relevant lessons/preferences and canonical plan contract.
- [x] Add combined snapshot/accounting, grouped rendering and alias tests; observe expected RED.
- [x] Implement overview composition/renderer and canonical CLI names with hidden aliases.
- [x] Update README, smoke checks and current callers; retain historical evidence.
- [x] Run focused/full pytest, strict mypy, Ruff, package build and read-only data checks.
- [x] Perform an independent review; fix material findings with RED/GREEN tests.
- [x] Refresh installed package; verify outside checkout; reconcile final docs and evidence.

## Risks, edge cases and rollback

Keep matched allowance duration distinct from total recorded duration. Concurrent roots add, children add no work, waits subtract, unknown attribution stays in totals. Avoid summing reasoning session counts or per-row uncertainty. Preserve missing-reading behavior and separate reset cohorts. Render long names, tiny shares and subsecond work across widths 20–120, ASCII, NO_COLOR and piped output. Revert only this task's diff and reinstall the prior package to roll back; data remains unchanged.

## Automated and manual verification

RED/GREEN: `.venv/bin/pytest -q tests/test_overview.py tests/test_command_layout.py`. Regression: `.venv/bin/pytest -q`, `.venv/bin/mypy src`, `.venv/bin/ruff check .`, `uv build`, `./scripts/smoke-test.sh`, `git diff --check`. Literal fixtures verify totals, distinct sessions, waits, concurrent roots, children, missing allowance and multiple resets. CLI alias comparisons cover terminal/JSON/CSV/errors/defaults; hash fixture storage before/after reads. Capture normal/narrow output, long names, tiny positive shares, plain, NO_COLOR and clean JSON. Install: `uv tool install --python 3.12 --force --reinstall-package codex-time /home/kevin/coding/track-codex-sessions`; from `/tmp` run installed overview/aliases/help and compare installed module bytes with source. No sudo needed. Manual Action/Expected entries go into docs/smoke-tests.md.

## Progress, evidence and review

Setup: initial default sandbox commands failed before execution; approved route works. See docs/postmortem/2026-10-08-overview-command-environment.md. `.agent/PLANS.md` is absent here; canonical linux-config contract read. Existing report work is retained as the implementation base.

## Delivery notes

Suggested commit: `feat: combine usage overview and clarify commands`. Keep implementation, tests, documentation and this plan in the same eventual commit. Provide a concise Cursor handoff with exact checks under prompts/overview-command-layout.md.

RED: `.venv/bin/pytest -q tests/test_overview.py tests/test_command_layout.py` exited 1, 34 expected missing-feature failures and one existing picker pass after correcting schema/storage fixture setup. See fixture incident. Production implementation now added; GREEN pending.

Focused GREEN: `.venv/bin/pytest -q tests/test_overview.py tests/test_command_layout.py` passed 35 tests (exit 0). Independent docs work updated README, docs/smoke-tests.md, docs/model-burn-tracking.md, current scripts and Cursor prompt; shell syntax and relative links checked. Help test corrected to distinguish advertised commands from descriptive verbs. Broad verification and fresh review follow.

Broad GREEN: full pytest 220 passed, strict mypy 19 sources, Ruff and package build passed (all exit 0). Smoke script 166 passed (exit 0). Compatibility probe: eight default/argument checks and eight export/output/exit checks against pre-overview CLI in commit 4097f54 matched, with unchanged fixture storage bytes. Source snapshot inventory clarified in environment incident; prior task commits landed during setup, and this task made no commits.

Fresh independent review: 40 focused tests passed and probes verified six alias defaults plus Unicode reasoning across 11 widths. No Critical/Important defects. Reviewer noted old status/list recommendations in empty/non-TTY guidance. Ruling: complete canonical user guidance too — these are actionable command recommendations that should match advertised names — cost if wrong: only text and associated guidance-test expectations change; alias contracts/exports remain.

Review declined behavior rulings: below-20-column terminals retain existing minimum width (supported verification begins at 20; cost: extreme-width terminals can overflow). Existing accounting algorithms remain unchanged, as explicitly required (cost: existing accounting limits remain).

Review guidance fix: four defining tests failed as expected with old status/list recommendations (exit 1); replace only actionable guidance with health/sessions, retaining legacy dispatch/export contracts. GREEN pending.

Final guidance GREEN: `.venv/bin/pytest -q tests/test_overview.py tests/test_command_layout.py tests/test_burn_output.py tests/test_day_output.py` passed 68 cases (exit 0). Final full suite passed 224, strict mypy all 19 source files and Ruff/whitespace passed. Final `uv build` produced wheel/source distributions (exit 0). Final `./scripts/smoke-test.sh` passed 170 tests (exit 0).

Installed refresh: `uv tool install --python 3.12 --force --reinstall-package codex-time /home/kevin/coding/track-codex-sessions` exited 0. `python3 /tmp/verify-codex-overview-installed.py` from `/tmp` exited 0: seven changed installed module bytes match source, day/week/month overview JSON equals dedicated reports, six aliases preserve outputs/exports, 20/32/88-column ASCII and NO_COLOR/piped checks pass, fixture hashes remain unchanged, and live today output shows grouped model/reasoning shares and distinct counts. No observer restart was needed.

Documentation gate: README `update_in_same_change` repairs canonical command/flag coverage while retaining recruiter hook, stack rationale, install and daily use. 51 runnable bash examples parse after excluding shell operators. Handoff includes atomic plan, exact automated/manual checks, docs, rollback and Conventional Commit suggestion. No new Critical/Important findings remain; reviewer guidance cleanup is completed, not deferred.

Canonical incident learning: registered current hashes for environment, fixture and static-verification reports as explicit no-new-learning decisions in `/home/kevin/linux-config/dot_agents/skills/postmortem-memory/sources.json`. All three targeted `check --postmortem` commands exited 0 with no errors. Exactly three records were appended; every prior report/finding/metadata entry was preserved. The specific narrow Rule-title trap is recorded in local lessons. Required `fish -lc refresh-config` exited 0 with REFRESH COMPLETE. It snapshot live Codex config, applied chezmoi, regenerated shortcuts and sourced them. Existing unrelated configuration work was retained; only canonical incident registrations belong to this task.

Completion: implementation, tests, current documentation/callers, plan, handoff prompt, installation and required incident learning/refresh are verified. No integration workflow was requested; keep the reviewed changes in the existing checkout. Final review limits remain the existing 20-column minimum and existing accounting semantics. Rollback is task-scoped source/doc restoration followed by package reinstall; stored data is unchanged.

## Authorized session commit delivery

The user invoked `$commit-session` after verified implementation. Session ID: 01a11c7f-ad7c-79a3-a8e1-ee424338de20. Scope helper in both repositories returned unsafe/no recognized successful writes (inline Python commands are not detected); directly observed writes and captured pre-write status/snapshots establish eligible scope. Include current overview implementation/tests/docs/this plan and companion canonical records; exclude daily-report heading/test/docs additions, its untouched plan, and its preflight incident. Stage mixed files from reviewed temporary content, leaving working-tree bytes unchanged. README gates for both repos pass_no_change; fresh 68 focused tests, strict mypy (19 sources) and Ruff pass. Validate an exported staged tree before committing so excluded baseline edits cannot hide a regression.

Delivery uses `feat: combine usage overview and clarify commands` on tracker main -> origin/main and a separate `docs: record overview verification incidents` commit for exactly three canonical memory records on linux-config main -> origin/main. Push each configured upstream after its reviewed local commit; no history rewriting. Reusable final smoke command is `./scripts/smoke-test.sh` from this checkout (no sudo), expecting all tests and the smoke success message.

Commit verification: exported exact staged tracker content passed 68 focused tests, strict mypy on 19 sources, Ruff and the README gate (all exit 0), excluding the pre-existing heading/test and doc hunks. Staged canonical memory contains exactly 27 added lines for three records; checks against its committed guidance passed for all three report hashes. Required refresh-config exited 0 with REFRESH COMPLETE after preserving the original ledger escaping. Staged diffs and rollback were reviewed; both upstream targets are confirmed.
