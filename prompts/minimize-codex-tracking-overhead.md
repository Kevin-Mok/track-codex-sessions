Reduce Codex Time’s background CPU, memory and disk overhead as far as practical while preserving every currently deployed feature.

User decisions:
- Internal architecture and storage may be redesigned.
- Live sampling and display updates may lag by up to 60 seconds.
- Preserve precise recorded lifecycle timestamps and existing known waits. Coarser socket sampling may miss short waits; expose its actual uncertainty rather than claiming one-second accuracy.
- Preserve all historical data, CLI commands/aliases, exports, session picker/resume, native timetrace integration, model/reasoning reports, allowance tracking and deployed token/cost/FX reporting.

Grounding:
Work from /home/kevin/coding/track-codex-sessions and follow active repository instructions. Read docs/postmortem/2026-10-14-codex-time-resource-use.md.

The installed package’s direct_url.json points to .worktrees/token-cost-reporting, which contains newer uncommitted functionality absent from main. Inspect both checkouts and installation lineage before choosing an implementation location. Preserve unrelated changes and avoid installing an older feature set.

The assessment measured approximately 98–100% of one CPU core and 1.83 GiB RSS. Its snapshot contained 5,449 sessions, 49,885 turns, 285,348 quota observations and 195,166 usage observations. Unchanged saves took 1.7–2.2 seconds under cProfile with writes disabled. Inspected package files postdated the old PID’s startup: remeasure a known build rather than assuming on-disk source matches loaded bytecode. A memory leak remains unproven.

Implementation requirements:
1. Establish reproducible before/after benchmarks using identical sanitized inputs. Measure ingestion, observation, persistence and projection separately. Include idle, active, cold start, restart and increasing history sizes. Report aggregate background-worker CPU, RSS/peak RSS, logical I/O, operation counts and update latency. Separate startup/backfill costs from steady state.

2. Make steady-state work proportional to changed records and currently observed sessions. Remove repeated full-ledger/session serialization, unchanged-rollout reads and complete projection directory sweeps from the frequent loop. Unchanged idle input should produce no historical-data writes.

3. Keep a bounded daemon working set. Store historical evidence and exact deduplication/index state on disk; use bounded caches and lazy report queries. Avoid retaining duplicate full-history models, serialized keys and signatures. Compare a minimal incremental design with an append-only content-free journal plus a disposable indexed store; implement the simplest design meeting the acceptance criteria.

4. Prefer change-triggered ingestion with a 60-second fallback where events are unavailable. Coalesce frequent file events, bound queues and processing batches, and prevent overlapping scans. Avoid decoding irrelevant message/tool bodies. Handle missed notifications through bounded reconciliation.

5. Decouple live observation, durable timing evidence, native projections, UI refresh and historical reconciliation. Update affected records only. Coordinate heartbeat freshness, stale-state handling, observation-gap thresholds and sampling uncertainty with the new cadence. Slower polling must neither mark a healthy daemon stale nor invent continuous work across an outage.

6. Preserve wait subtraction, quiet tool work, concurrent roots, child exclusion, model/reasoning attribution, token/cost coverage and exact counters, renames/resumes, per-turn cwd, midnight/DST splitting and unknown/gap provenance. Preserve read-only Codex integration. Save no raw conversation, tool output, credentials or auth data.

7. Any storage migration must be versioned, idempotent and recoverable after interruption, with verified pre-migration backups. Preserve the documented portable/Git backup and restore workflow, machine-readable interfaces and native readers. Handle truncation/replacement, archive moves, partial JSONL writes, deleted sources, corruption and Git restore without lost evidence or duplication. Do not delete or downsample history to meet resource targets.

8. Write defining RED tests before behavior changes, implement GREEN, then run focused and relevant broader regressions. Use deterministic clocks for minute-cadence tests. Add a reusable benchmark/smoke harness with readable ongoing progress, plain mode and clean machine output.

Acceptance:
- After warm-up, target ≤0.5% of one CPU core idle, ≤2% during up to five concurrent observed root sessions, and ≤128 MiB steady-state background RSS at the measured history scale.
- Measure CPU over five-minute idle and active windows.
- At ten times the cold-history size with the same active workload, steady-state work and RAM must not grow linearly with history.
- Run a 30-minute fixed-input idle soak and repeated session/open/close/reconnect cycles to check retained memory and descriptors.
- Test event storms, notification loss, restart/migration interruption and report parity.
- Optimize further where measurements justify it. These targets are provisional: report measured misses and tradeoffs instead of silently weakening them or removing functionality.

Delivery:
Update the implementation plan, README, smoke checks and migration/rollback documentation. Verify the packaged executable and a known-build service, not only source tests. Prepare deployment and rollback concretely, then follow active authorization policy for installation/restart.

Provide the chosen design, feature/data parity evidence, before/after benchmark table, migration/rollback results, actual timing uncertainty, remaining risks and exactly three direct verification commands with expected outputs. Distinguish measured results from targets. A restart, longer sleep or systemd resource cap alone does not complete this task.
