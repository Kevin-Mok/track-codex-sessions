# Incremental tracking resource redesign — October 14, 2026

This report explains the measured overhead, the incremental storage remedy, and its verification limits. Compare known builds on identical content-free fixtures, verify migration/recovery and reports, then activate a reviewed package with a preserved rollback path.

## Symptom and scope

Original assessment measured old PID3886 near one core and1.83GiB RSS, but inspected files postdated startup. A leak and exact loaded bytecode remain unproven. A known deployed-source baseline at6da806f and matching sanitized5449-session/49885-turn/285348-quota/195166-usage fixture measured96.857% idle CPU /1318.125MiB RSS over300.568seconds. Five active roots measured81.774% /1396.711MiB over310.661seconds. Unchanged serialization alone took1.445seconds.

## Diagnosis and remedy

Repeated whole-history models, exact identities and serialization dominate steady background work. Retain history in portable per-session snapshots and append-only evidence journals, store exact deduplication/source checkpoints/metadata signatures/native ownership in a disposable SQLite index, and process changed records with bounded caches/queues/pages. Layout v1 publishes last after verified original backups; snapshot and native recovery markers precede checkpoint commit. Reports remain on-demand. No raw conversation/auth/tool bodies are retained.

Chosen minimal mutable snapshots avoid appending complete active session histories repeatedly. Default60-second observation carries actual read/cadence uncertainty; gaps above75seconds are not bridged and90-second heartbeat freshness is coordinated. Known waits/lifecycle timestamps remain precise.

## Isolated verification and limitations

Earlier immutable corecf10253... measured five-minute idle0.019405% /43.461MiB, five-root active0.065291% /44.457MiB. Its1800-second idle soak left historical files unchanged, RSS delta0 and FD delta0. These measurements are earlier-core evidence, not proof of final installation. Intermediate packaged wheel at measured scale confirmed socket wait/unknown/reconnect, precise2.125-second wait, unchanged token journals and daemon56MiB steady RAM.

Original10x harness used history-sized os.walk filename lists and contaminated RSS with allocator retention; preserve original results and use streamed scandir instrumentation for final comparisons. Startup/native rebuild is substantial and separately measured; individual huge sessions/records and all-history reports can still allocate substantial memory. Boundary-preserving arbitrary middle rewrites remain an explicit limitation requiring full import reconciliation.

## Review regressions

An isolated older snapshot restore retained applied metadata signatures and lost metadata-only turns/names on replay. Defining RED demonstrated absence; clearing disposable row signatures/table cursors once per detected restore retained independent exact names and passed focused GREEN. Unknown socket cwd cannot overwrite newer precise rollout cwd. Deterministic bootstrap RED showed names replay at0/0.1/60.1seconds; retain bootstrap while its own index cursor remains pending.

The reviewer identified unbounded unfinished scan requeue; worker correction reserves continuation capacity and one total page budget. A filesystem stress reproducer found timestamp collisions in 194 of 500 same-size writes, all previously missed. Saved prefix/tail validation bounded to 512 bytes fixed 287 of 500 collisions with zero missed replacements in the repeat. The defining assertion was preserved. Event and active reconciliation validate boundaries; explicitly stat-only checks do not open unchanged files.

## Final isolated verification

Matched final-core 300-second windows measured 0.019920% idle / 0.145126% active CPU with 50.320 MiB active RSS at 1x. Tenfold history measured 0.020077% idle / 0.151436% active with 44.691 MiB RSS. The frozen byte-identical loop's 1,800-second idle soak showed zero RSS/descriptor growth and unchanged historical files. Fresh 100-cycle runs retained +0.199 MiB / +0.863 MiB with zero descriptor growth. Source hashes and complete process I/O/phase data are in ../benchmarks/2026-10-14-incremental-tracking.json. Earlier replayed active timestamps and filename-interning instrument artifacts remain labelled and are not used as active/daemon-growth evidence.

Cold allocator and pathlib filename arenas can persist after a bounded streaming migration. The final daemon runs preparation in a short-lived child before opening its long-lived index. Stop/cancel reaps that writer, including cancellation between fork and returned process handle. Cold cost remains real and is measured separately; the service harness includes reaped-child CPU rather than making it disappear. Parent-only post-start HWM does not prove child peak memory. Separate exact-wheel cold startup observed two tracker workers, 89.270 MiB sampled aggregate RSS, 96.824 MiB sum of observed HWMs, 45.62 CPU seconds and 108.110 seconds elapsed; the zero-length/one-second test mode is startup-only evidence. Standalone child time-v measured 48.684 MiB peak, 40.95 CPU seconds and 101.59 seconds elapsed.

Fresh complete validation after startup isolation: 436 tests passed in 76.58 seconds, strict mypy passed for 33 modules, Ruff passed, and final v5 wheel built. Final known-wheel/socket/metadata windows exited 0: daemon idle 0.086667% / 48.637 MiB, active 0.1100% / 48.484 MiB; mock-inclusive aggregate 0.1600% / 79.238 MiB idle and 0.1867% / 79.086 MiB active. Known 2.125-second wait, lifecycle timestamps, exact token journals, reconnect/unknown provenance and 65-second freshness passed. Runtime uncertainty was 60.000214 seconds; failed-poll spacing 120.066 seconds was not bridged. Final source/wheel/legacy/native report parity passed. Migration interruptions, backup verification, projection recovery, external restore, exact counters and conservative rollback/FX have defining regressions.

## Current status and follow-up

Status: v5 production backfill failed; v6 correction is verified in code and against the actual failing record, with activation awaiting explicit approval after automatic review rejected “cont” as ambiguous. The service is paused. Prior synthetic performance evidence remains scoped to its fixtures and cannot establish real-corpus readiness. Preserve original and newly partitioned evidence; rollback must export CURRENT snapshots before selecting the prior reader.

Limits: individual huge sessions/JSONL records and on-demand all-history reports can allocate transient history; cold native rebuild is costly; boundary-preserving arbitrary middle edits require explicit full import. No production fix or memory leak is claimed before live activation/measurement. Canonical reviewed hashes, evidence scope and targeted check outcomes are recorded in the plan at finalization.

Final verification milestone: full `uv run pytest -q` completed 437 passed in 74.74 seconds, exit 0 (root session61018/chunk765ec9). Fresh strict mypy33, Ruff and diff whitespace checks passed; exact result references are in .harness/incremental-tracking/validation.json. No prior259-test log is reused as final evidence.

## Unexpected live startup restart under investigation

After approved activation, systemd reports NRestarts=1 and the live PID changed from3755683 to3760672. A resource monitor correctly refused the missing oldPID. Currenthealth is running at60-second sampling with source backfill incomplete. Do not claim a stable live resource window yet. Reading the exact journal traceback before remediation. Canonical lookup `proc missing process PID systemd restart memory observer` returned observer full-history and process-memory-accounting guidance: livePIDidentity and loaded-build checks apply; none proves this restart rootcause. Preserve data/backups and investigate actual failure.

The journal confirms OOM kill (status9/KILL, one-GiB service peak) after3m25.921s CPU during initial rollout backfill. Paused the service to prevent repeated kills while diagnosing. No resource cap changed. Canonical lookup `large JSONL record readline memory OOM bounded parser` matched bounded-json-nesting (recursion handling only, not proven applicable to allocation) and history-index/process-accounting guidance; fresh bounded diagnosis required. Independent actual-data audit nevertheless verifies every pre-upgrade session/turn, exact lifecycle timestamps, knownwaits/coverage/modelcontexts and all quota/usage identities/payloads retained with zero mismatches. Evidence /tmp/codex-live-data-parity-v5.json.

## Actual oversized-record cause and defining correction

A bounded inventory found 5,516 rollouts totaling 6.190 GiB, including one complete 2,135,854,844-byte JSONL record. It contains about 326 million backslashes and 97 million quotes. Whole-record readline and UTF-8 decoding allocated the body before selection; the previous backtracking string regex added pathological escape frames. The restarted service reached a journal-recorded 32.7 GiB peak before OOM. This demonstrates transient parsing allocations; it does not prove a retained-history leak.

Defining RED: public ingestion of a 384 MiB ignored string under a 256 MiB address-space limit failed with MemoryError. An escape-heavy 4 MiB selector record also exhausted memory, and a malformed 1,000-character string timed out. The correction uses 64 KiB reads, incremental UTF-8 validation and a structural whitelist projection; disjoint possessive string runs avoid backtracking. Ignored bodies are never materialized or persisted. Selected metadata is capped at 1 MiB/4,096 nodes, depth 256 and 8,192-byte scalar literals. Unsupported records receive existing diagnostics/gap provenance rather than fabricated timing. Partial final records commit no evidence or offset; malformed complete records drain through their newline before resuming. One complete giant record can exceed the between-record batch time/byte budget while retaining bounded body memory.

GREEN: ten public streaming ingestion tests cover lifecycle fields after the ignored body, exact timestamps, partial-write restart, UTF-8/escape boundaries and malformed-line recovery. The exact real 2.136 GB record streamed under a 256 MiB address-space limit in 13.597 seconds (13.573 CPU seconds), at 45.336 MiB VmHWM; it retained 147 selected JSON bytes. No real body, identifier or source path was copied into evidence. The complete suite passed 449 tests in 73.23 seconds, strict mypy passed 34 modules and Ruff passed. The corrected source-content digest is 5d344eda64c792bc0ac7e18c692e3b08ae0676281ab9af097e35384973594de1.

The durable v6 bundle at /home/example/.local/state/codex-time/deployments/incremental-v6-20261014 passed verification. Its rollback wheel is the exact original pre-v5 package, rather than the OOM-prone intermediate build; the original verified backup also remains in the durable v5 bundle. Live v6 backfill, post-fix data parity and a stable five-minute resource window remain open until activation is authorized and observed.
