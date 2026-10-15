# Slow installed overview startup

Measure the installed command, remove repeated historical work, and verify exact report parity without changing durable tracking inputs.

## Symptom, impact and status

The user observed repeated progress through at least 23 seconds. The compatible fix is now installed and verified: unchanged reports can return in about0.6s, while authoritative fallback can still take about19s. Two pre-existing untracked files (the saved prompt and task-handoff incident) are preserved. Optional context discovery found no local `.agent/PLANS.md`; use the canonical linux-config contract. An initial skill read used an incorrect Ponytail path; the supplied catalog path resolved it. Neither failure affected product data.

## Lookup and applicability

Read the canonical postmortem-memory skill and searched `overview report slow historical validation cache`. Generic retrieval was not diagnostic; directly read October 14 overview and session-cache incidents. Historical validation/accounting costs are hypotheses until measured afresh. The separate watcher cache does not serve overview. Installed v4 compatibility must be checked before activation.

## Initial investigation plan

Capture four actual baseline invocations, separate loading/computation/rendering, add a defining RED reproducer at the measured seam, implement the minimum safe fix, verify frozen parity and activation, update incident learning. These stages are complete; evidence and remaining latency are recorded below.

## Diagnosis and selected implementation

Actual installed first/repeat completion: 21.559 / 20.879 / 22.096 / 23.183 seconds; first useful stdout 21.274 / 20.650 / 21.764 / 22.906 seconds. This is process-first, with no filesystem cache eviction. Wall phase probe: load 14.839s, compute 5.599s, render 0.011s. Profile (29.68s, diagnostic overhead only): 506,981 validations; load 16.67s, burn 7.85s, token report 4.85s, with 20.4 million conflict-range checks. Installed direct URL is the incremental-v9 wheel; Ledger.version=4 is the in-memory schema, while layout.json version1 is the partitioned v5 storage contract. The historical v3/v4 install warning remains useful but is not the current build identity.

Sources churn while reports run: a full report cache alone cannot remove miss cost. Reuse the existing daemon SQLite evidence index only in a read transaction whose published source stamp matches before/after, validating returned models and selecting only relevant token evidence. Retain full pre-period quota history. Missing/corrupt/stale/incompatible indexes fall back to authoritative journals. All-time initially stays on full loading because its bounds include every quota/token observation across all limits. Token coverage reconstruction additionally skips sessions proven outside the period. A versioned, validated, private atomic full report cache serves unchanged inputs; source/build/options/calendar/FX identities invalidate it and FX age is refreshed at read time.

TDD: current-index reader first failed the journal-open guard through the old Store.load path; token-period guard failed on old session reconstruction; full-report cache failed when repeated CLI read called forbidden Store.load. Reader/token focused GREEN: 18 passed. Cache worker focused GREEN: 33 passed. First Ruff passes found two >100-character lines; wrapped them. These are validation diagnostics, not changes to accounting contracts. No tests or deadlines weakened.

## Installed API compatibility discovery

The first temporary live overlay exited before reporting: installed Store lacks main's newer public `load_timing()` method. A follow-up overlay proved `_read_ledger` is also main-only. Direct inspection of the installed `Store.load` implementation establishes the shared public API `load(include_evidence=False)`; use it. The earlier claim of a shared private API was an unverified assumption and is withdrawn. No installation or durable input changed. Added an installed-API regression before correction and reran the actual overlay. This confirms why source-only tests are insufficient for activation.

## Broader validation

First full suite: 535 passed, one obsolete assertion failed (`test_cli_readonly_exports_and_all_date_rejection` expects no runtime directory). Overview now intentionally creates only its private disposable report cache; updated the assertion to permit that artifact while continuing to require identical durable ledger and no FX/other runtime writes. Full source Ruff and strict mypy passed (37 modules). A separate mapper follow-up could not launch because all four agent slots were occupied; existing reviewer covers the bounded read-only check. The verifier worker also recorded a rejected patch format before any file write; corrected with an update patch.

## Runtime permissions and verification harnesses

Normal runtime-cache access was confirmed with an approved execution: overlay first7.306s, repeats0.601/0.652/0.518s, all exit0. Earlier sandboxed runs had no permission to publish private home cache state; source churn was real during the original20s phase probe, but it was not established as the sole cause of those cache misses. The earlier all-misses explanation is corrected accordingly.

Token-smoke's first sandboxed invocation stopped at its synthetic writer lock in the read-only real home, before reaching the expected cache-hash mismatch. Inspecting captured fixture-only stderr identified Errno30; normal approved execution is the appropriate verification route. Its hash contract now permits only overview-report.json, validates its synthetic total, and continues checking every durable, FX and other runtime file. No HOME/CODEX_HOME override is used. The performance verifier's copied-data index preparation likewise encountered the real-home lock path; a nullcontext retry correctly failed Store.project's writer guard. The final helper retains real exclusive flock and `_locked` lifetime entirely inside its unique temporary fixture state; it does not bypass index validation or production locking. Small partitioned-fixture parity passed after that correction.

## Compatible package preparation

The original incremental-v9 wheel matches every installed Python/JSON module byte-for-byte. Prepared a wheel from those exact installed sources, changing only cli.py/token_reporting.py and adding overview_read.py/overview_cache.py. Preserve the other seven main-vs-installed differences and every dependency version. Initial sandboxed uv build failed on its read-only home cache before building; approved normal-cache build succeeded. Candidate installed only into a disposable Python3.12.3 environment with the exact11 existing dependency pins; live activation was pending at that stage and completed after verification below. Normal cross-filesystem uv hardlink warning used a successful copy fallback and did not affect correctness.

## Verified parity and activation

Real frozen snapshot:5,825sessions/53,818turns; session snapshots42,790,467bytes, quota61,097,944bytes, usage165,285,595bytes. Day before17.771/18.579/17.269/17.520s, after6.919/0.565/0.716/0.666s; every JSON field equal. Repeated means17.789→0.649s,96.4% reduction. Selected week and Toronto November DST month also pass exact full-report parity (19.377→9.692s and18.524→7.372s on concurrent runs; these extra timings establish parity, not an isolated performance comparison). No kernel cache eviction or fixed latency guarantee is claimed.

Final source suite536passed; strict mypy37modules; Ruff source/tests/two changed helpers passed. Synthetic packaged token/accounting smoke passed with exact amounts and durable/FX/other-state hash protection. Independent review verified the cache/read/accounting design and full frozen day evidence; its obsolete token-smoke contract finding was repaired.

Activated through normal offline uv tool installation with pinned Python3.12.3 and all11 existing dependency versions. Only cli.py/token_reporting.py change, and overview_read.py/overview_cache.py are added; all other installed source/pricing modules are preserved. Candidate wheel SHA256 d58e648533e766aafc74f0f84b9c02e0b270407cd2c5215b3d593ae4a5044050. Private permanent rollback bundle: `/home/kevin/.local/state/codex-time/deployments/overview-20261015-d58e648533e7/` contains original/candidate wheels, dependency pins, before/after source hashes and guarded rollback.py. It refuses changed artifacts or a later unrelated installed build. Rollback reuses normal pinned offline uv installation and changes no data layout. Actual installed measurements and service continuity checks follow; installation alone is not the performance verification.

## Operational limits and follow-up

Whole reports are cached only for unchanged inputs; active source updates and stale/missing daemon indexes can require fresh computation or full loading. An uncached indexed default report costs about7s at this history scale; authoritative fallback can still take about19s. All-time cache misses intentionally retain full historical loading. This task adds no daemon/resource remedy, TTL/stale-result behavior, new dependency or schema migration. The source changes, README/smoke/plan and required incident learning stay uncommitted because no commit/push was requested.

Native title transport became unavailable on the phase-update attempt (`127.0.0.1` MCP transport send error); the existing objective title remains correct. This matches the prior overview incident's transport limitation and does not block verification. No retry or another thread rename was attempted.

## Actual installed outcome

The real `/home/kevin/.local/bin/codex-time overview` completed in **19.483 /18.733 /7.728 /0.622s**, all exit0. First useful stdout:19.268/18.444/7.635/0.545s. The last cached call emitted no progress because it completed promptly. These live runs expose the remaining authoritative-reader fallback cost; do not represent every cold/live call as7s or promise subsecond responses when inputs/index freshness force recomputation. The rigorous frozen same-input comparison above isolates the improvement; this live series proves activation with its natural variability.

All37 candidate Python/JSON source hashes match the installed package; all11 dependency versions match, as does the final wheel hash. Actual plain output is ASCII (exit0); actual JSON parses with all four sections (exit0). Actual installed synthetic token smoke passes. Service PID4027405 and start timestamp2026-10-14 20:06:40EDT match before activation: no daemon restart. Durable inputs, rollouts and conversations were never written by task commands; ongoing daemon changes are independent.

Rollback helper help and deliberate corrupt-artifact refusal on an isolated copy pass. A real rollback was not executed because it would remove the verified improvement. Terminal selection/copy/paste was not visually checked: native terminal APIs are unavailable here, and no rendering setting changed. Final handoff uses simple raw fish-compatible command lines.

## Reviewed incident learning

Register the final report hash and alias under `local-overview-indexed-report-cache` in the canonical linux-config postmortem-memory ledger and artifact-verification guidance. Status is verified_fix with runtime scope, bounded to source-matched indexed reads and unchanged-input report reuse; authoritative fallback latency remains explicit. Preserve the already dirty canonical sources.json and unrelated guidance. The targeted final-hash check result is recorded in the linked investigation plan after registration, avoiding a self-referential report hash.

Canonical learning write initially stopped before mutation at a formatting guard: pre-existing dirty records mix sorted and insertion-order keys. Preserve original dictionary order and UTF-8 formatting rather than reformatting unrelated records; structural preservation checks remain in force.

Final independent reviewer confirmed all37 installed source/pricing hashes, candidate-wheel/constraints hashes and11 dependency pins. Its sandbox could not connect to the user systemd bus (`Operation not permitted`) or see host PID4027405 under /proc; those namespace-limited checks do not contradict the successful normal-permission host continuity check. No service mutation or blind retry occurred. The final reviewer retains that evidence-scope limitation explicitly.

## Commit delivery verification

The user subsequently confirmed the faster runtime and requested committing the speedup. Fresh restricted focused tests hit11 known home-lock permission failures (89passed); the normal-permission rerun passed all100 in2.38s. Ruff and strict mypy37modules passed. This is the same fixture-lock environment limit diagnosed above, not an accounting regression. The current work-log delivery milestone supersedes the original no-commit authorization. The native title checkpoint again encountered the already recorded unavailable transport; no further retry was made.
