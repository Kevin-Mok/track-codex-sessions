# Daily report readability

Make the daily report easier to scan while preserving its working time, directory shares, session information and token/cost data. Inspect the installed source, replace repeated blocks with aligned rows, and verify both ordinary and narrow terminals.

## Purpose and observable outcome

`codex-time day --date 2026-10-13` must retain all report entities and totals with substantially less repeated output. Target a concise total, ranked project rows and session rows, with models visible and full identity/evidence available through details/JSON. No accounting, pricing or ingestion changes.

## Context and protected state

Initial main status: modified README.md, docs/smoke-tests.md, plans/daily-repo-session-time.md, src/codex_time/day_output.py, tests/test_day_output.py; untracked docs/postmortem/2026-10-06-daily-report-rerun-preflight.md. Preserve all. Installed provenance points to `.worktrees/token-cost-reporting`, whose renderer includes cost data missing from main. User explicitly authorized use of this checkout on 2026-10-14; no new worktree, commits or pushes are requested. Default mode provides no Plan Mode switch, so this file records decisions inline.

## Assumptions and decisions

Retain Python/Rich and existing command aliases, filters and JSON schema. Avoid hiding sessions or dropping models to achieve brevity. Use single project summaries, aligned numeric columns at normal widths, stacked labeled metrics on narrow terminals. Full paths/IDs and detailed per-model costs remain available with --details, while default names/models and all totals remain visible. Keep uncertainty and excluded-cost notices concise and truthful. Final target/specific layout will be updated after source inspection.

## Ordered checklist

- [x] Capture initial dirty status, inspect actual installed report and identify provenance.
- [x] User authorized existing installed-source checkout and worktree-policy change; captured its dirty status.
- [x] Read active source/tests/docs and define compact-output tests; observe expected RED.
- [x] Implement compact renderer, preserving accounting/exports; no new display option needed.
- [x] Update README, smoke checks and a concise Cursor handoff prompt.
- [x] Run focused/full tests, type/lint checks, widths/plain/control-character checks and real report comparisons.
- [x] Update installed package from verified intended source, verify actual command and review diff.

## Risks and rollback

An installation from main would drop token/cost behavior: never do it. Disambiguate duplicate project names; wrap titles/model names and preserve visible durations. No truncation of requested content, no tracking-data changes or daemon restart. Revert only task-owned presentation changes and reinstall the intended source for rollback. Keep matching plan/docs with implementation if subsequently committed.

## Exact verification

Defining RED/GREEN: renderer tests with many projects/sessions, all values retained and bounded lines, wide and 20/48-column layouts; token/cost partial/unavailable and multi-model cases. Focused day CLI/reporting/token-output suites, full pytest, mypy src, Ruff lint/format. Actual installed CLI: selected day, --details and --plain; compare one frozen report JSON rendered before/after for line count and value conservation. No sudo.

## Progress and review

Preflight failures and reviewed-memory lookup: docs/postmortem/2026-10-14-report-readability-preflight.md. Installed report reproduced successfully: directory summary plus duplicate session headers; each session has title, ID, time, cost and repeated model-cost lines. Main checkout cannot safely replace that installed feature. Permission question is pending; read-only source inspection may continue.

Worktree initial status captured before edits: existing token-cost implementation modifies README, smoke docs/script, CLI/daemon/ingestion/model/reporting/storage/overview modules, lessons and four tests; untracked cost modules, pricing catalog, token tests/docs/plan/prompt/smoke script and two prior incidents. Preserve this complete feature. Scope of this task: day renderer/tests plus matching readability docs/plan/prompt; canonical worktree policy is delegated separately.

### Settled renderer design

Files: src/codex_time/day_output.py; tests/test_day_output.py and new tests/test_day_readability.py; README.md, docs/smoke-tests.md, prompts/daily-report-readability.md and this plan. The source renderer alone consumes DailyReport; exports/accounting and CLI options stay unchanged. At sufficient widths, use aligned Project/Time/Share/Tokens/USD/CAD summary and Session/Model/Time/Tokens/USD/CAD rows. Allow width up to160, fold labels without ellipsis, fall back to stacked labeled metrics when columns cannot fit. Show each full directory path once with its session group; disambiguate duplicate basenames using full paths in summary. All session titles and model names/cost breakdowns remain visible. Omit duplicated sole-model costs only when its displayed usage equals the parent session; show that model name on the label. Default full IDs move to --details, along with exact categories/children/quality/provenance. Retain concise partial/unavailable/excluded/FX notices and the Standard present-rate caveat. No new dependency or pagination, no dropped sessions.

Existing layout assertions are updated for intended aligned rows and IDs-in-details; all safety/value conservation assertions remain. Focused new tests are delegated to an independent worker; source changes wait for its observed RED. Canonical worktree policy is an independent delegated task. The reviewed preflight report is registered at hash 85a4a7e47b515defbe57c7da588786af58956bb22c41ad308f9f15f23525f80f; canonical targeted check exited0, no new learning.

### RED/GREEN and initial real-data comparison

Updated layout contracts failed as expected for default full IDs and missing aligned labels. Independent worker tests observed seven expected failures against original renderer (120 versus65line fixture budget, missing aligned headers, ignored120/160width, duplicate sole-model costs, split model values and default IDs). Initial GREEN: 43 day-output/CLI/token-report tests passed;16 independent readability tests passed. One real frozen JSON snapshot: before401/341/340lines at48/88/120columns; after219/121/121lines. All14directories and29distinct sessions remain. One review-driven defining test caught an uncertain model with no countable tokens displayed as0.00*: expected RED observed; mark this evidence unavailable instead, preserving true observed zero and known partial money. Model names now use parentheses beside sole-model session titles; full multi-model rows remain.

### Fresh regression and installation evidence

Full `uv run --offline pytest -q --tb=short`: exit0,324passed in33.65s. `uv run --offline mypy src`: exit0,no issues in26source files. Direct `uv run --offline ruff check .`: exit0,All checks passed after documented source/test lint corrections. Three-file format check: exit0. `uv build --offline`: exit0,both distributions built. Frozen snapshot checks20/48/88/120/160columns retained every full path/session/model/duration/cost value, ASCII and width bounds, without mutating input. Final line counts409/219/123/121/121, respectively; original88-column341lines ->123(64%less). Independent readability suite17passed. Installed update `uv tool install --offline --python 3.12 --force --reinstall-package codex-time /home/example/coding/track-codex-sessions/.worktrees/token-cost-reporting`: exit0; source provenance preserved; no daemon restart/data mutation. Actual installed default/details/narrow reads are in progress.

### Final review and delivery

Independent reviewer verified compactness, complete entity/value retention, safe metadata/folding, details, no report mutation and docs. Two optional/missing-evidence findings corrected through expected RED then GREEN: top-level uncertain usage with no countable tokens now says USD/CAD unavailable; model usage remains visible when optional parent session usage is absent. Latest full pytest: exit0,325passed in35.69s. Latest focused day/output/CLI/token suites before final optional-parent case:61passed; independent final renderer suites31passed. Final Ruff,mypy26source files and three-file formatting: exit0. Isolated smoke: exit0,253passed plus token replay/conservation success. Earlier build produced both archives; final source is re-built by verified tool reinstall.

Final `uv tool install --offline --python 3.12 --force --reinstall-package codex-time /home/example/coding/track-codex-sessions/.worktrees/token-cost-reporting` exited0 after both review fixes. Installed day_output.py byte-matches final source; direct_url identifies this checkout. Actual installed daily command after final reinstall exited0,123lines with default88column fallback. Earlier actual installed --details --cwd /home/example/linux-config --plain exited0,432lines retaining IDs/categories; narrow COLUMNS=48 --plain exited0,219ASCII lines. Latest changes only affect uncertain-header and optional-parent evidence; source/installed byte identity and regression tests prove those fixes are active. All14directories/29sessions and totals remain. No observer restart, no tracking-data write, no commit/push.

Canonical worktree rule and append-only preference are updated/deployed separately under linux-config; source/live AGENTS bytes match. Final `fish -c refresh-config` exited0 with REFRESH COMPLETE after both tasks' memory updates. Canonical incident checks exited0 for hashes85a4a7e47b515defbe57c7da588786af58956bb22c41ad308f9f15f23525f80f ande40cefc9a010f2f19179f6ea3167e69de2c85c8584b8b4b92c6624c07f0a6ab5. Relevant policy/doctor tests30passed; a proven pre-existing push-policy wording mismatch and doctor7errors/1warning remain in the policy plan, with zero added findings. These do not affect report verification.

README gate: update_in_same_change; compact table/ID/detail/narrow-width expectations repaired while preserving prior token-cost docs and recruiter hook/stack order. Setup flags grounded in scripts/setup.sh; report flags in CLI; no new flag added. Source diff versus saved pre-task bytes confirms scoped presentation changes only; git diff --check exited0. No unsafe/unrelated file was staged. This existing branch is feat/token-cost-reporting. Preserve both related readability docs/plan and pre-existing token-cost feature together in any later requested delivery; do not install from main, which lacks token-cost support. Suggested commit: `fix: make daily work reports easier to scan`.

Manual verification (any cwd,no sudo): `codex-time day --date 2026-10-13`; `codex-time day --date 2026-10-13 --cwd /home/example/linux-config --details --plain`; `env COLUMNS=48 codex-time day --date 2026-10-13 --plain`. Expected: aligned default full entity list; expanded stable identity/categories/provenance; narrow ASCII labelled metrics. Exact automated/manual plan and rollback are above; paste-ready handoff is prompts/daily-report-readability.md. Native TUI selection/paste cannot be exercised through available native computer APIs (disabled); commands remain single raw fish-compatible lines and no rendering settings were changed.

Final evidence-reviewer follow-up: installed renderer byte equality and saved actual output verified independently; final installed output exactly matches the frozen123line render, narrow artifact stays within48columns and filtered details retain all10full session IDs/categories/provenance. All renderer acceptance items verified; no outstanding defect.

## Authorized session commit workflow

User invoked commit-session, then explicitly approved including the earlier token-cost prerequisite before the report fix. Scope helper for thread01a13b29-5f2b-7603-b710-f16be6b09294 returnedunsafe/no successful writes recognized; direct observed-write evidence and saved pre-write bytes establish this session. Current-session files: renderer/test changes, new readability tests/plan/prompt/two incidents, scoped README/smoke updates; separate canonical worktree-policy changes are committed independently in linux-config. Existing token feature prerequisite is now explicitly authorized, not inferred session ownership. No unrelated main-checkout changes are included. Prepare prerequisite snapshot, inspect staged bytes and verify; commit with its token plan, then commit readability with this plan and its docs. Branch feat/token-cost-reporting has no upstream; keep local commits unless a target is configured explicitly.

### Commit milestones and current delivery status

1. `feat: report token usage and estimated API costs` created625e824: explicitly authorized39-file prerequisite, with matching token plan/docs; exact isolated snapshot306tests/type/lint/build and independent review passed. Direct disposable normal/missing/JSON installed-CLI scenarios exited0.
2. `fix: make daily work reports easier to scan` is the reviewed current-session follow-up: renderer,31defining renderer tests(18new readability cases plus13existing/output cases), README/smoke docs, prompt, this plan and3session incidents. Before staging, focused renderer/CLI/token suites passed62; Ruff and mypy26source files passed. Source matches prior325-test/full253-smoke proof; no behavior edits during commit separation. README gatepass_no_change after this task's earlier repairs. No unrelated report-checkout changes remain after this explicit prerequisite + session series.
3. Canonical worktree policy committed separately asd827816 (`docs: allow flexible worktree use`),9scoped files only. Initial origin/main push rejected because12remote commits advanced concurrently; clean authorized merge checkout reconciles both histories without altering dirtymain. Final remote result belongs in the policyplan/handoff.

Commit scope uses direct observed-write fallback because session_scope returnedunsafe/no detected successful writes through this execution transport. Pre-existing main-checkout daily-heading work is excluded. All earlier policy/audit/pstack modifications inlinux-config remain excluded unless already independently upstream; canonical merge preserves both remote and local history. Current reportbranchfeat/token-cost-reporting has no upstream, so thetwo report commits remain local percommit-session. Required status links: thisplan and linux-config/plans/allow-worktree-discretion.md. The new workflow incident is docs/postmortem/2026-10-14-session-commit-snapshot-preflight.md, reviewedhash8523eab582fc22eb4981b6ea57aa0ec40cf6ff23c12ead454de88b3f77b0781f; canonical targetedcheck exited0. No secrets, generated artifacts or files over3MB enter thesecommits. Rollback remains normalrevert inreverse dependencyorder; installed tool/data untouched by commit operations.
