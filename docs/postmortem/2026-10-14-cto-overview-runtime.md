# CTO overview runtime investigation

Measure the installed overview command, isolate its costs, and verify a small safe optimization without changing durable history or unrelated work.

## Symptom and scope

User reports roughly 22 seconds per `cto` invocation. Live fish mapping confirms `codex-time overview`, executable `/home/example/.local/bin/codex-time`. Installed package expects ledger v4 with token reporting; main expects v3. Live activation must preserve v4 and token output. No commit, push, daemon stop, rollout edit or incompatible installation authorized.

## Workflow failures and lookup

Sandbox command wrapper failed before launch with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`; approved elevated execution succeeds. Known prior investigation records `ext-sandbox-loopback`; applies to command transport, not application performance. Initial optional AGENTS and guessed skill paths did not exist; corrected to catalog paths. Profiling helper named `profile.py` shadowed Python stdlib profile, causing circular import before any data access; rename the temporary helper before retry. No product failure or data modification resulted.

Lookup `overview slow` returned unrelated findings; none establishes an overview remedy. Existing investigation's full-history validation finding is applicable as a hypothesis; fresh numerical profiling required. Preserve separate dirty incremental-tracking worktree.

## Current status and next steps

Baseline four actual direct overview runs in progress. Profile read-only installed loader/computation/rendering, record dataset identity, write a defining regression before implementing, compare stable full computation outputs. Learning update and targeted canonical coverage check required once report finalizes.

## Diagnosis and implementation

Actual live runs 23.286, 24.892, 28.063, 26.100 seconds. Wall phase timings: load 14.204s, compute 8.837s. Profile confirms 485,213 historical validations and repeated interval construction; render only 0.0153s. Validation batching microbenchmark did not improve runtime and was rejected. The smallest selected fix skips sessions proven to have no selected-period work before allowance/model reconstruction. Full retained-session accounting remains unchanged. Defining five tests failed as expected, then 58 focused regressions passed.

Ruff initially found a new 101-character line; wrap that line without behavioral change. All experiments and measurements preserve live records and the separate dirty worktrees. Installed-build comparison is temporary and schema-compatible; activation remains pending.

## Verification setup refinements

Independent review identified a missing timedelta import in the temporary installed-v4 overlay; corrected both the reusable harness and task-owned temporary copy before optimized execution. Final helper metadata inspection initially used the wrong sources.json key (sources instead of reports); corrected without any knowledge-store write. New changed-input test initially moved start past end and correctly hit assignment validation; construct a valid future interval by moving end first. Title update transport became unavailable after the initial successful native rename; preserve the existing native title. These are harness/workflow faults, not product or live-record failures.

## Compatible activation decision

Read-only source-identity review confirmed clean token-cost-reporting worktree: all 26 Python modules and pricing-v1.json match installed build byte for byte; both use ledger v4. Thus compatible activation is safe within the saved prompt authorization. Copied only work_period helper, two report guards and six regressions into that worktree; no incremental-tracking changes. An initial test command used a wrong relative environment path from main and exited 127 before tests; corrected to absolute test executable with compatible worktree cwd. Run its complete tests/lint/types/build before normal uv tool reinstall. Do not restart daemon or modify durable inputs.

Compatible-v4 full suite initially failed existing daemon restart/stale-checkpoint runtime test with a 12-second timeout (330 passed, one failure, 44.35s). No installation performed. Report-only changes do not touch daemon/startup; independent read-only analysis will check the actual failed stage and targeted reproduction before proceeding. Tests overlapped main verification/system observer load; contention is a hypothesis, not an established root cause. Retain the test without weakening its deadline.

## Independent runtime-test retry setup

A focused retry from token-cost-reporting used relative `PYTHONPATH=src` and failed after 9.56 seconds at the UI readiness wait, earlier than the original restart timeout. This retry is inconclusive: the fixture launches its UI subprocess with a disposable temporary working directory, so the relative source path no longer identifies the intended v4 checkout. No product source or live service was changed. Retry with absolute source PYTHONPATH; preserve original deadlines and distinguish its result from the setup failure.

Absolute-source full-suite retry: daemon runtime regression passes, but existing setup rebuild test fails (330 passed) because inherited absolute PYTHONPATH forces subprocesses to import the worktree instead of their deliberately isolated installed test build. Verified default root-venv subprocess imports main/v3; absolute override imports compatible v4. Neither environment is suitable for every test. Use a dedicated compatible-worktree virtual environment with frozen/offline dependency sync and no PYTHONPATH override; this corrects test isolation without changing tests or deadlines. Installation remains pending.

## Resolution and verified outcome

Dedicated v4 virtual environment, with no PYTHONPATH override: **331 passed in 34.87s**. Main: **265 passed in 30.48s**. Both Ruff, strict mypy (21/27 files), package builds and diff whitespace checks pass. Original cross-build/override test failures are setup evidence, not a failing report regression. No deadlines/tests were weakened. Independent review found no accounting defect and the temporary overlay import issue was corrected before optimized runs.

Compatible installation completed through normal `uv tool install --python 3.12 --force --reinstall-package codex-time` with offline resolution. The first invocation omitted interpreter pinning and uv selected a different interpreter; immediately reinstalled with the original 3.12 family before measurements. Final Python **3.12.3**, ledger **v4**, Pydantic **2.14.1**, websockets **16.1.1**. Normal uv tool resolution refreshed dependencies, so live wall comparisons cannot isolate the filter alone. Installed helper/modules/pricing match the v4 source worktree: **28 files, zero differences**. Service not restarted; durable tracker files and raw Codex sources were never written by task commands.

Frozen original installed-build day comparison (same interpreter/dependencies/data/clock): 5,497 sessions, 50,981 turns; ledger 46,375,195 bytes, quotas 59,374,398 bytes, usage 158,569,274 bytes. Before first/warm **23.674 / 24.978 / 24.576 / 23.775s**; filtered **22.120 / 22.821 / 22.370 / 22.121s**. Warm means **24.443 → 22.437s**, **8.2% reduction**. Every field of all four report sections matches full historical computation. These are process-first/warm-filesystem measurements, not evicted filesystem-cache measurements.

Actual user command after compatible installation: first **22.202s**, warm **23.363 / 24.376 / 23.239s**, all exit 0. Prior actual command first **23.286s**, warm **24.892 / 28.063 / 26.100s**, all exit 0. Live history grew and other verification/system activity varied; quote this range as observed runtime, not isolated causal gain. The report retains allowance, token_usage, model_totals and reasoning.

Activated-build frozen parity also passes selected week (**24.829 vs 24.986s**, effectively no speed gain within measurement noise) and future/DST month (**23.271 vs 22.229s**, ASCII verifier output). The conservative eligibility helper does not guarantee an improvement when most sessions intersect the period. All-period functionality passes the complete v4 suite. No persistent cache is added, so changed inputs are read afresh; the sixth defining regression proves new work appears immediately.

Shell/import separation after activation: fish startup **0.417 / 0.438 / 0.488s**; Python startup **0.029 / 0.028 / 0.031s**; CLI import **0.473 / 0.332 / 0.389s**. Direct overview measurements exclude interactive shell startup. Rendering remains around 15ms; complete quota/token validation, token segmentation and allowance conflict processing remain the main follow-ups. This is a modest report improvement, not resolution of background daemon resource use.

README/smoke/todo/plan and Cursor continuation prompt updated. Preserve all main pre-existing dirt and separate incremental-tracking work. Compatible token worktree holds only two report edits, the new helper and six regressions; no commit or push requested/performed. Rollback is the original compatible v4 sources plus normal pinned-Python installation, never a v3 data downgrade. Canonical learning coverage is tracked in the investigation plan after current-hash registration.
