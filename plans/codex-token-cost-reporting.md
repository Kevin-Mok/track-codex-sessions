# Codex token usage and API cost reporting

Extend overview and projects with durable token usage, exact present-rate Standard API estimates in USD/CAD, and historical attribution. Implement ingestion and pricing first, integrate read-only reports, then verify migration, terminal output, installation and documentation.

## Purpose and observable outcome

`cto` (`codex-time overview`) and `codex-time projects [day|week|month|all]` show token and estimated API cost totals, with model, root-session and recorded-directory detail. Actual descendants contribute once; forks exclude inherited tokens; child elapsed time is never added to root time. Today remains the default and weeks start Monday. All-time rejects --date and uses latest allowance without a consumption rate.

## Context and scope

Read models, ingestion, storage, daemon, reporting, overview and CLI; reuse their single-writer architecture and duration accounting. Relevant prior plan: overview-command-layout.md. Local .agent/PLANS.md absent; canonical /home/kevin/linux-config/.agent/PLANS.md contract applies. User provided the binding implementation specification in chat. User subsequently requested a new worktree based on HEAD. Current workspace: /home/kevin/coding/track-codex-sessions/.worktrees/token-cost-reporting, branch feat/token-cost-reporting, base 66d221d66c5fac5ed4f7eab7df963a99866c65f7. No commit or push requested.

## Assumptions and decisions

- Execute the supplied approved plan in Default mode (mode changes require developer instruction); maintain this decision-complete record.
- Preserve pre-existing README.md, docs/smoke-tests.md, plans/daily-repo-session-time.md, day_output.py, test_day_output.py and the untracked daily-report preflight incident. Baseline bytes/diff/status saved under /tmp/codex-token-cost-baseline.
- Ingestion owns models/ingest/storage; pricing owns standalone pricing/FX modules; primary owns composition, report rendering, CLI and daemon integration. Independent final review checks the combined diff.
- UsageObservation preserves whitelisted cumulative/last counters, derived nullable delta, observation time, historical cwd/model, stable session/turn identity and diagnostics. All report totals come from these same observations.
- User correction: exclude exact `codex-auto-review` from token/cost totals and breakdowns. Keep its durable evidence and existing duration accounting; other unknown models remain visible and unpriced. Excluded-only coverage must not be misreported as missing usage or priced zero.
- Unknown/missing counters remain distinguishable from zero. Cost is a known priced subtotal whenever evidence or prices are incomplete. No guessed internal model aliases.
- FX is runtime-only, read-only for reports, refreshed asynchronously by daemon with bounded timeouts and 1h failure/24h success scheduling.
- Ruling: preserve existing duration-only report APIs and add period/usage fields additively; user-facing projects/overview gain richer output while legacy aliases retain the same dispatch.

## Ordered implementation

- [x] Capture initial state; read source, canonical plan contract and relevant preferences/lessons.
- [x] Define and observe RED ingestion/replay/attribution fixtures.
- [x] Implement validated v4 usage storage and idempotent historical backfill with progress.
- [x] Verify official rates; implement Decimal pricing and runtime FX with mocked RED/GREEN tests.
- [x] Define and observe RED period/report/CLI fixtures; integrate directory/root/model aggregation and responsive output.
- [x] Integrate background FX refresh and verify nonblocking scheduling.
- [x] Update README, smoke script/docs and paste-ready Cursor handoff prompt.
- [x] Independent review; resolve important findings with defining tests.
- [x] Fresh full tests/typecheck/lint/build/smoke; reinstall and verify installed CLI outside checkout.
- [x] Record evidence, migration/rollback, limitations and final handoff.

## Risks, edge cases and rollback

Repeated cumulative snapshots must add zero; missing history/resets/compaction/forks may only establish a lower bound. Attribute observations by event order, never current SQLite model. Keep unknown models, usage-only sessions and orphan children visible. Price cache subsets and reasoning exactly once; long-context tiers need request evidence. Preserve quotas and timing during migration. Reports must not mutate ledger/checkpoint/FX files or fetch the network. Old executable cannot read v4: stop writer, restore full pre-migration data/runtime backup and reinstall prior package to roll back; never downgrade only the version tag. Baseline user edits must remain.

## Exact verification

Defining suites: tests/test_token_ingest.py, tests/test_token_pricing.py, tests/test_fx.py, tests/test_token_reports.py (names reconciled as authored). Cover duplicate/reset/fork/nested/orphan/model/cwd/unfinished/midnight/DST/missing evidence, cache and long-context tiers, FX failures and aggregation conservation. Hash stored fixture data before/after report reads. Capture normal/narrow/plain/NO_COLOR rendering.

Run from repository without sudo: `.venv/bin/pytest -q`, `.venv/bin/mypy src`, `.venv/bin/ruff check .`, `uv build`, `./scripts/smoke-test.sh`, `git diff --check`. Refresh package using `uv tool install --python 3.12 --force --reinstall-package codex-time /home/kevin/coding/track-codex-sessions/.worktrees/token-cost-reporting`; verify installed modules and isolated fixture CLI from /tmp. Document reusable manual checks in docs/smoke-tests.md, each with Action and Expected.

## Progress, evidence and review notes

Initial reads: default sandbox failed before process execution with bwrap loopback RTM_NEWADDR; scoped approved execution succeeds. Optional local .agent discovery also failed because directory is absent. Living incident: docs/postmortem/2026-10-08-token-cost-environment.md. Postmortem-memory lookup matched ext-sandbox-loopback; observed evidence meets its applicability. Host sandbox remains unrepaired; repository work can continue through approved execution. No implementation verification claimed yet.


Implementation milestones (no commits requested): ingestion v4 and append-only usage journal; verified dated pricing/FX; report and daemon integration; docs/smoke handoff. RED evidence: initial report suite 13 expected missing-feature failures; daemon integration 3 expected failures/1 prior pass; ingestion initial 9 RED→GREEN; pricing/FX initial 11+12 RED→GREEN. Focused GREEN: reporting compatibility 97, daemon/FX 16, ingestion/storage 74, pricing/FX 28. Additional exact large-money aggregation and unpriced-row rendering defining tests went RED→GREEN.

Independent fresh review found four Important issues, no Critical/Minor: restored-prefix overlap, missing actual parent/child usage coverage, all-time latest quota date, and unsupported context payload attribution. Five defining cases failed as expected, then passed in a 43-case focused suite after fixes. Ruling: earlier restored evidence may overlap an immutable later tranche, so preserve it with null delta/earlier_history_overlap rather than double charging; previous tranche attribution is not redistributed. Cost if insufficient: conservative undercount for previously unavailable nonoverlapping earlier history; explicit uncertainty remains and complete-source reconstruction can use a separate fresh store.

Ruling: missing usage coverage follows actual contributing session/directory before root grouping; child elapsed duration remains excluded. Missing child evidence alone does not create new duration-only rows; aggregate details name unavailable session IDs. A broad run exposed 4 legacy shape regressions (296 passed), now fixed; affected 62 tests and integrated mypy 25/Ruff pass. Child-only actual token records still create visible zero-duration rows. Ruling: child --session selects that child's own observations; root --session includes its entire descendant family; documented explicitly.

Review declined checks: documentation completeness was deferred while docs were being written; primary reviewed README, smoke docs and token guide afterward. Catalog arithmetic and handling reviewed independently; source rates verified by pricing agent and primary via official OpenAI pricing, model and prompt-cache pages. No remaining intentional review deferrals. Price IDs remain exact, and local catalog contains verification date 2026-10-08.

Reusable isolated script scripts/token-smoke.py passes with 1,320,000 tokens, USD 2.91 and CAD 3.9285 at 1.35; all four periods, child attribution, legacy alias, repeat import and data/runtime hash preservation verified. Normal and 32-column output captured; unpriced positive rows explicitly say USD unpriced. JSON decimal strings retain trailing zeros; smoke compares Decimal numeric values. Package build produced wheel and sdist. At this earlier milestone the final full suite, installed package verification and live activation were pending; their completed evidence follows.

README gate: update_in_same_change. Preserved recruiter hook/stack-before-setup order and pre-existing daily report edits; added period flags, exact price/FX limits, v4 backfill, both-journal backup/rollback and smoke CLI options. Smoke-test-capture applied to shared docs/smoke-tests.md. Related guide/prompt: docs/token-cost-reporting.md and prompts/codex-token-cost-reporting.md.


Final source verification: `.venv/bin/pytest -q` passed 302 in 37.12s; `.venv/bin/mypy src` passed 26 source files; `.venv/bin/ruff check .` and `git diff --check` exited 0. `./scripts/smoke-test.sh` passed 248 tests in 36.81s plus isolated CLI conservation/replay/read-only check; `uv build` produced both distributions (exit 0). The added progress module passed two defining RED→GREEN cases and 25 CLI compatibility tests; slow reports emit periodic stderr status while fast/piped fixtures retain clean stdout. All four documentation files have valid local Markdown targets.

Installed verification: complete live v3 data and runtime backup saved at /home/kevin/.local/state/codex-time/token-reporting-backups/20261008T200217Z after stopping the writer. `uv tool install --python 3.12 --force --reinstall-package codex-time /home/kevin/coding/track-codex-sessions` and existing-service start exited 0. From /tmp, installed 27 module/catalog bytes matched source and all seven token-smoke scenarios (verify, normal, narrow, overview, filtered, json, missing) passed. Captures: /tmp/token-cost-installed-<scenario>.txt. Final live service backfill scanned 5,105 rollout files/1,158,967 records in 120 seconds with ongoing progress. A fresh v4 heartbeat and installed live report subsequently confirmed activation: 222,024,153 today tokens, USD known priced subtotal 77.6014216, 65,974,203 unpriced tokens, 563 uncertain observations and 30 unavailable sessions. These were point-in-time totals before the later auto-review exclusion. CAD was unavailable after a bounded FX timeout; no valid rate was fabricated.

Preservation check: untouched plans/daily-repo-session-time.md, tests/test_day_output.py and the original untracked daily-report preflight incident match captured baseline bytes. Shared README/smoke/day_output retained the baseline additions and task-specific changes together; nothing staged. At that milestone the working branch was unchanged and no commit/push was performed; the later requested worktree transfer is recorded below.


## Requested worktree and exclusion follow-up

Created `.worktrees/token-cost-reporting` from current HEAD 66d221d on `feat/token-cost-reporting`. Clean HEAD baseline: `.venv/bin/pytest -q` passed 224 in 30.81s. The independent .venv was installed with `uv sync --python 3.12`. All dirty bytes were backed up at `/tmp/token-cost-worktree-transfer`; transferred 39 task files while removing the original daily-report hunks from the three shared files. Restored the original checkout exactly to its saved status and baseline bytes. Existing `.worktrees/ctp-session-insights` was untouched. No commit or push.

The exclusion tests failed as expected in this worktree (2 failures), followed by two additional RED cases for excluded-only terminal labels and blank TimeoutError diagnostics (4 defining failures total). Implementation excludes the exact model during read-only projection before pricing/aggregation, retains evidence for coverage, exports `excluded_models`, and keeps duration-only roots. Empty exception text now falls back to its exception class. Corrected focused command passed 67 in 1.38s. The reusable CLI fixture now includes an auto-review child while expected tokens and costs remain unchanged. A guessed renderer-test filename caused a collection failure; its living verification incident records the inventory and corrected command.

At the follow-up milestone, fresh full worktree checks, reinstallation, installed/live exclusion verification and final handoff were pending; completed evidence follows.

Fresh worktree checks after the user corrections: `.venv/bin/pytest -q` passed 306 in 37.23s; `.venv/bin/mypy src` passed 26 source files; `.venv/bin/ruff check .`, `git diff --check` and `uv build` exited 0. Independent focused follow-up review found no Critical/Important/Minor issues; it verified exact-name exclusion, retained other unpriced models, unchanged time/evidence, excluded-only labels and timeout diagnostics, with 7 focused checks and disposable CLI smoke passing. Broader unchanged functionality remains covered by the primary full suite. Installed refresh from this worktree subsequently completed, as recorded below.


## Completed verification and handoff

The requested worktree holds 39 task files, all below 3 MB, with no staged files, commits or pushes. Original-checkout status and all six protected baseline file bytes match the initial capture exactly. Local documentation targets are valid. Final README gate: **pass_no_change** after the related usage/pricing/migration/exclusion updates; recruiter hook and repo-grounded stack rationale precede setup, and report options match fresh local help. Relevant plan/docs remain in the same intended atomic change.

`./scripts/smoke-test.sh` passed 252 tests in 35.23s, exit 0, followed by exact CLI conservation/replay/read-only verification including auto-review exclusion. Installation from this worktree and existing-service restart exited 0; no service path/socket options changed. From /tmp, all 27 installed module/catalog files match source bytes and seven installed scenarios (verify, normal, narrow, overview, filtered, json, missing) pass. Captures: /tmp/token-cost-worktree-installed-<scenario>.txt. Expected synthetic totals remain 1,320,000 tokens, USD 2.91 and CAD 3.9285 at 1.35. JSON keeps exact monetary strings; 32-column ASCII rendering keeps all values visible.

Fresh installed live reports agree on 166,998,219 today tokens and USD known priced subtotal 90.2730716, with exact auto-review exclusion metadata and no excluded token-model rows at any report level. Token totals reconcile across models, directories and root sessions. Live heartbeat 2026-10-08T20:20:09.938344+00:00 proves v4 observer activation after restart. These are point-in-time values while tracking continues. CAD remains unavailable because the first bounded FX refresh timed out and no valid rate is cached; retries obey the hourly schedule, and the new diagnostic fallback applies to future empty timeout messages. Incomplete historical billing/context evidence remains a conservative subtotal, not a complete invoice.

Rollback: stop the writer, restore matched data/runtime from `/home/kevin/.local/state/codex-time/token-reporting-backups/20261008T200217Z`, reinstall the prior executable and restart with existing options. Do not downgrade the version tag or discard one journal. Backfill has already completed; ordinary v4 restarts retain valid checkpoints. Restored-prefix attribution remains intentionally conservative as documented above.

Reproduce automated validation with `.venv/bin/pytest -q`, `.venv/bin/mypy src`, `.venv/bin/ruff check .`, `uv build`, `./scripts/smoke-test.sh`, and `git diff --check`. Manual installed scenarios are the seven copy-paste commands in docs/smoke-tests.md; each has its own Action/Expected description. Cursor continuation prompt: prompts/codex-token-cost-reporting.md. Suggested later authorized atomic commit: `feat: report session token usage and estimated API costs`; include all implementation, tests, related docs and this plan. No remaining implementation work; stale/missing FX and uncertain source evidence remain explicit operating limitations.

Final incident-memory check: current verification report SHA-256 `52d3e3ccc496aafc997c39e907ce4cf32557f449bf77ea8226bfdd224d1c0059` registered in canonical sources.json with explicit no-new-learning decision; targeted check exits 0 with no errors, changed/new records, missing sources or unregistered aliases. Required refresh-config exits 0 (REFRESH COMPLETE), log /tmp/refresh-config-20261008-162250-2307672.log. Environment report alias remains registered. No installed skill copy edited. Final worktree base/branch reconfirmed as 66d221d / feat/token-cost-reporting, service active.

## Session delivery: token-cost prerequisite

On2026-10-14 the user explicitly authorized committing this pre-existing token-cost feature as the prerequisite for the current session's readability fix. The active branch is feat/token-cost-reporting; no upstream is configured, so retain verified local commits and report the missing push target. Prepare the original token-cost renderer/README/smoke bytes from /tmp/codex-day-readability-baseline, with the other existing token feature files. Do not include current readability tests/docs/plan until the next commit. The complete current working tree passed325tests,mypy26source files,Ruff and253smoke checks; the isolated prerequisite snapshot will be checked independently before its commit. Commit milestone subject: `feat: report token usage and estimated API costs`. Then commit readability with its matching plan/docs. No history rewrite or daemon restart.

Prerequisite commit verification: exact exported39-file candidate passed `uv run --offline --no-sync pytest -q --tb=short` with306tests in36.95seconds; isolated mypy passed26source files, Ruff passed and uv build produced both distributions. Independent39-file review found no Critical/Important issues, no secrets/generated files and no readability artifacts; largest file30,819bytes. Renderer/README/smoke bytes match pre-readability captures. Independent probe conserved1,320,000tokens and DecimalUSD2.910/CAD3.92850, excluded auto-review, retained root attribution and left ledger unchanged. README recruiter gate is pass_no_change: hook/stack before setup, options grounded in CLI/setup/smoke sources. Rollback is normal revert of this prerequisite and dependent readability commit; never downgrade livev4data. Remaining: create prerequisite commit, then commit the verified readability follow-up; no configured report-branch upstream.
