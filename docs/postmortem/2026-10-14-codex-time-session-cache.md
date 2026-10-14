# Slow startup and repeated session-state scans

Measure startup and repeated rollout reads, add incremental session-state caching, and verify unchanged checks against full parsing. This report also tracks diagnostic environment failures during the work.

## Symptom, impact and current status

Startup loads historical tracking data even for lightweight health/status requests. Outside watchers have no compact session-state contract and reparse raw rollouts. Initial diagnosis began before product edits; source fixes and verification are now complete (see final evidence below). Raw Codex files and the running service remain untouched.

Diagnostic shell initialization initially failed with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. Approved escalated read-only execution works. A batched context read also confirmed this repository has no local AGENTS.md or .agent/PLANS.md; use the supplied canonical instructions and linux-config ExecPlan contract. Neither failure changed application state.

## Evidence and lookup

Initial Git status preserved README.md, docs/smoke-tests.md, plans/daily-repo-session-time.md, src/codex_time/day_output.py, tasks/lessons.md, tests/test_day_output.py and existing untracked investigation/todo/postmortem documents.

Read-only inventory: 5,487 active rollout files, 6,590,083,689 bytes; no archived rollouts. Walking and statting took 0.0691 seconds. Live files can grow during measurement.

Postmortem-memory queries: `bwrap loopback Failed RTM_NEWADDR` and `local-observer full history polling`. Known approved-route workaround applies to the reproduced pre-command sandbox failure. The prior resource report identifies unchanged whole-history serialization as unresolved; current profiling will establish its applicability independently. Missing optional instruction files are context discovery, with canonical paths now resolved.

## Next steps

Finish baseline profiling before designing the cache. Add executable regressions before implementation, then repeat measurements, review the diff, and update this report with root cause, resolution and evidence. No service restart or install is authorized by this report.

Baseline harness initially used `python -m codex_time`, but the project exposes only its installed console entry point, with no __main__.py. It failed before reading data. Corrected the harness to `.venv/bin/codex-time`; this is a harness error, not product behavior.

The corrected checkout startup exposed pre-existing schema drift: live ledger.json is version 4 while this checkout accepts version 3. Pydantic reports only the version literal mismatch (input suppressed); production files are intact. Benchmark the installed build unchanged and a clearly labeled isolated v3-compatible snapshot for checkout before/after comparisons. Do not downgrade or overwrite the live ledger. Query `codex-time invalid ledger schema version` returned no applicable migration remedy.

Focused GREEN run exposed an existing regression contract: ingestion detects an in-place rewrite that grows on the same inode. Pure size/inode append detection missed its new session (19 passed, test_replaced_rollout_does_not_skip_new_session failed). Keep a bounded stable prefix verification on changed ingestion files, capped to the original prefix length so appending to a short file does not replay history. Unchanged ingestion files still open zero times. The separate state-cache design assumes the specified append-only source contract and detects truncation, same-size rewrite and inode replacement.

Intermediate validation found two formatting diagnostics (long CLI line and test import order), now corrected. Mypy ran before the delegated module existed; integration validation will run after it is complete. Incident-ledger format inspection initially assumed a sources key; the documented schema uses reports/findings, now confirmed. These are tooling/integration diagnostics, with no live-state changes.

The old status CLI test omitted --codex-home because status previously only read health. With actual session state it unintentionally scanned the real home into its isolated test cache. Interrupted only this task-owned pytest and corrected its fixture to pass an empty temporary Codex home. Real rollouts were read-only; no live state was written. Cache integration checks are rerun on isolated inputs.

The first broad suite also exposed a fixture assertion pinned to rollout checkpoint v3. The scanner now emits v4 with stat metadata and accepts old v3 checkpoints; updated only the expected checkpoint version (durable ledger version remains v3). Integrated cache/CLI tests pass: 33 in 17.26 seconds.

Independent review found an empty-first rollout prefix edge case and conflicting tty evidence. Each was reproduced RED before correction. Extended tty conflict evidence requires preserving all candidate ttys until the final join. Plain-progress separators also require ASCII. The first complete suite finished 252 passed / 3 failed: old hidden-status help/alias assumptions and another checkpoint-v3 assertion; these are updated to the explicitly documented status-array/checkpoint-v4 contracts without relaxing accounting assertions. No production activation has occurred.

## Resolution and root cause

Source fixes are verified; installed-build activation is pending. Full allowance-history validation dominated lightweight startup, accounting rows added more cost, and unchanged ingestion still opened every rollout. There was no compact watcher contract. Added a private, atomic, versioned path-keyed session-state cache with stat hits, incremental complete-line offsets, source identity/schema validation and conservative tty evidence. Lightweight timing readers omit the quota journal and reuse a validated unchanged ledger. Health reads only summary fields. State checks bypass ledger loading, historical accounting and serialization. The daemon's separate whole-history save/projection overhead remains unresolved in this task.

## Final evidence

Baseline inventory: 5,487 rollouts / 6.59 GB. Real-data snapshot picker first startup 10.182 → 3.362 seconds; warm 10.826/9.187 → 3.683/4.035 seconds. All-directory listing 12.460 → 4.813 seconds; health 7.205 → 0.841 seconds. Full cProfile raw lifecycle ingest 120.113 seconds, JSON loads 55.167 seconds, binary readline 21.167 seconds; unchanged ingestion previously opened all 5,487 files in 0.453/0.496 seconds.

Frozen-input status verification: 5,490 paths / 6,598,370,855 bytes, cold build 75.567520 seconds, warm 2.426398 seconds, unchanged 2.528083 seconds, full replay 61.959201 seconds. Every session field matched all passes; warm/unchanged opened zero rollouts and read zero bytes. Temporary copies were removed. Live cache was then populated independently: 5,492 paths / 6,602,574,057 bytes, 59.291858 seconds; the next successful check took 3.351300 seconds and consumed only 13,780 appended bytes across two files. This is not an unchanged-data comparison. Cache path: ~/.local/state/codex-time/072d8e0b6245b3179be51bde/session-status.json.

Full pytest: 259 passed in 34.03 seconds. Final health/error display adjustment: 35 focused tests passed in 12.26 seconds. Ruff passed; strict mypy passed for 20 source files; wheel/sdist build passed; whitespace check passed. Independent code review findings (empty-prefix ingestion, cross-source/intra-source tty ambiguity, ASCII progress) each have observed RED and GREEN regressions. Raw sources, live tracker ledger/journals, service and installed package were not modified. Existing unrelated dirty work remains.

## Follow-up and limits

Do not install this v3-ledger checkout over the installed v4/token-reporting build. Integrate its changes safely first. The source status command is independent of ledger schema and works on live inputs; startup comparisons use an isolated real ledger snapshot with only the version marker adapted. Kernel caches were not evicted; cProfile and system load affect timing. The compact full-message cache is 67.3 MB at this scale; a metadata-only projection could reduce warm validation/export cost. Snapshot transitions cannot enumerate intermediate completions within an hourly interval. The on-demand cache is refreshed by status, not by the daemon. No commit or push was requested/performed.
