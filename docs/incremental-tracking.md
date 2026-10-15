# Incremental tracking, measurement and recovery

This guide explains the bounded background design and how to verify an upgrade without losing recorded evidence. Compare the sanitized benchmarks and report parity first, prepare verified backups, activate a known package, and use a validated legacy export when rolling back.

Current checkpoint: v9 was explicitly approved and activated at 2026-10-15 00:06:40 UTC. Both historical audits pass, and its 300.131-second natural-load window measured 0.71635% CPU / 50.895 MiB RSS with zero descriptor growth or restart. The previous production v7 retained all original evidence but measured 24.7118% CPU at 51.035 MiB RSS. The isolated v8 event-bearing comparison reduced daemon CPU from 40.3398% to 0.4633%, with 0.0300% idle CPU and 47.387 MiB RSS. Final v9 adds foreground picker refresh fixes; 475 tests, types, lint and wheel build pass. V8 tenfold scaling, the 30-minute idle soak and all v9 packaged checks pass. The actual known-build window is complete with its natural-load and source catch-up limits below.

## Design and feature contract

The portable source of truth is layout v1: atomic per-session JSON snapshots, the original append-only quota and usage journals, and separate legacy journals for observations formerly embedded in ledger.json. The original ledger and a SHA-256-verified pre-migration backup remain intact. Eight session objects are cached. A disposable SQLite index stores exact quota/usage identities, source offsets/cumulative baselines, explicit names, metadata row signatures and native record ownership; it uses a 4 MiB page cache. History is never deleted or downsampled. An append-only timing-session journal was rejected because minute updates would repeatedly append a complete active session and enlarge every portable backup.

The notification callback disarms its level-triggered reader before waking the loop; the loop clears the previous wake, drains bounded input and rearms synchronously, preserving later notifications during socket polling. Warm source notifications retain per-path deadlines anchored to their first event, nominally at most 60 seconds; repeated events cannot postpone them. Startup and unfinished scan batches remain immediate. An active minute scan acknowledges already-consumed paths so deferred events do not resave them. Long records or blocked polling may overrun nominal completion; actual observation spacing and gaps remain visible.

The daemon processes coalesced inotify paths with bounded queues (4,096), watches (8,192), batches (128 names, 2,000 complete records, 8 MiB between records), and a single writer. Stat-only scans can skip unchanged sources without opening them. Event, active-source and bounded reconciliation scans also verify at most 512 bytes of saved prefix/tail before deciding whether to decode new records; this catches same-size writes whose filesystem timestamps collide. JSON selection decodes only whitelisted timing/token fields. Oversized records stream through 64 KiB chunks, with incremental UTF-8 validation and non-backtracking string runs; ignored bodies are never materialized. Selected metadata is limited to 1 MiB/4,096 nodes, depth 256 and 8,192-byte scalar literals. Unsupported records retain diagnostics/gap provenance. Partial records commit neither evidence nor offsets. A complete giant record may exceed the between-record batch duration/byte budget; the actual 2.136 GB record took 13.6 seconds at 45.3 MiB peak RSS. Healthy notifications rotate 128 historical source names per minute; startup/overflow/unavailable notifications perform full reconciliation in bounded batches. Loaded sessions' checkpoint paths and read-only metadata rollout paths are checked at each sample. Initial explicit-name replay completes in bounded fast pages before steady minute pacing. SQLite metadata reads exact active IDs and 128 historical rowids per table, without assuming monotonically increasing updated timestamps. Explicit session-index names are tailed and stored exactly on disk, including names whose sessions have not yet been discovered.

Live observation, portable persistence, native projection and terminal refresh have independent work. Only changed sessions are serialized. Title-only changes leave native records untouched. Native cleanup touches the recorded paths owned by an affected session; frequent loops do not sweep the projection directory. Health reads only metadata/counts; the picker loads timing without token journals. It checks four cheap storage generation fingerprints on its one-second input tick, reuses unchanged rows and redraws only for changed data, runtime observation, user input, terminal size or a minute deadline. A 60-second fallback detects isolated session restores that do not change those generations. This foreground cache does not add another minute to ordinary daemon updates. Full allowance/cost reports remain on-demand processes and can consume substantial transient memory at very large history sizes.

The existing CLI/aliases, exports, picker/resume, native readers, model/reasoning attribution, precise lifecycle timestamps, known blocking waits, quiet tool work, concurrent roots, child exclusion, per-turn cwd, midnight/DST splitting, token/cost/FX evidence and exact integer counters are retained. Historical token counts above JavaScript's integer precision are exercised by the parity harness. Codex integration remains read-only; no thread subscription, loading, mutation or approval response is sent. The generated fixtures contain no raw messages, tool output, credentials or auth data. Fixture inputs must be explicitly sanitized; production activation backs up only tracker-owned content-free evidence.

## Timing and freshness

Default socket sampling is 60 seconds; daemon --sample-seconds permits values greater than zero and at most 60. Each sample includes configured cadence plus actual read latency. The v5 socket fixture reported 60.000214 seconds of runtime uncertainty; a live v6 snapshot reached 60.072357 seconds. A deliberate failed poll produced a 120.066-second spacing with observation_gap provenance, rather than continuous work. The observer also retains actual inter-sample spacing as uncertainty. A gap over 75 seconds at minute cadence is not joined as continuous working time. Heartbeat freshness is 90 seconds. The UI shows a sampled estimate only while the observation remains fresh (75 seconds at nominal minute cadence); it does not persist that extrapolation.

New evidence records sampled_waits_60s; legacy sampled_waits_1s and already recorded waits remain intact. Coarse polling may miss an entire short wait, and endpoints can be uncertain by a sample interval or more under jitter. Precise rollout lifecycle and known synchronous request_user_input wait timestamps are unchanged. Idle-only samples add no timing/uncertainty fields and produce no historical writes after warm-up. Outage/gap transitions legitimately add provenance once; an active-to-idle transition must settle before claiming unchanged-input write results.

## Measured results

Targets are provisional: <=0.5% of one core idle, <=2% with five observed roots, <=128 MiB steady RSS. Startup/backfill is separate. The known baseline (commit 6da806f) and optimized core use identical sanitized inputs: 5,449 sessions, 49,885 turns, 285,348 quota and 195,166 usage observations. The 10x fixture multiplies all four history counts, keeping five active roots. Repeated workers choose a new observation epoch after those roots' existing coverage; active windows really persist new evidence.

| Build/window | Actual seconds | CPU, one core | RSS MiB | Logical read/write bytes | Updates |
| --- | ---: | ---: | ---: | ---: | ---: |
| Known baseline idle | 300.568 | 96.857% | 1318.125 | 248,333 / 1,197 | 203 |
| Known baseline five roots | 310.661 | 81.774% | 1396.711 | 3,124,825,113 / 3,125,931,169 | 84 |
| Matched core 1x idle | 300.000 | 0.019920% | 50.316 | 13,838 / 1,295 | 5 |
| Matched core 1x five roots | 300.000 | 0.145126% | 50.320 | 826,230 / 1,948,504 | 5 |
| Matched core 10x idle | 300.000 | 0.020077% | 44.176 | 13,815 / 1,294 | 5 |
| Matched core 10x five roots | 300.000 | 0.151436% | 44.691 | 1,100,084 / 1,899,096 | 5 |
| Frozen loop 30-minute idle soak | 1800.000 | 0.021531% | 42.242 | 74,572 / 8,614 | 30 |
| V5 isolated daemon idle, sockets + metadata | 300.001 | 0.086666% | 48.637 | 4,896,661 / 307,777 | 5 samples |
| V5 isolated daemon five roots, sockets + metadata | 300.001 | 0.110000% | 48.484 | 5,065,391 / 1,892,313 | 5 samples |
| V7 isolated daemon idle, sockets + metadata | 300.002 | 0.033333% | 47.289 | 981,049 / 307,780 | 5 samples |
| V7 isolated daemon five roots, sockets + metadata | 300.002 | 0.060000% | 47.094 | 1,191,656 / 1,921,148 | 5 samples |
| V7 event control, five roots | 300.001 | 40.3398% | 47.219 | 20,124,998 / 123,098,694 | 1,195 events |
| V8 event batching, five roots | 300.001 | 0.4633% | 47.176 | 6,422,086 / 1,995,682 | 1,193 events |
| V8 idle after tail drain | 300.002 | 0.0300% | 47.387 | 985,643 / 307,782 | 5 samples |
| V8 tenfold event history, five roots | 300.001 | 0.5100% | 52.520 | 8,101,651 / 3,895,672 | 1,197 events |
| V8 tenfold idle after tail drain | 300.001 | 0.0367% | 52.520 | 1,209,407 / 316,020 | 5 samples |
| V8 fixed-input daemon soak | 1800.001 | 0.03056% | 47.949 | 5,900,020 / 1,892,000 | 30 samples |

The v7/v8 event comparison uses the same sanitized fixture and 0.25-second event-rate configuration, with independently generated timestamps/counts. The final v8 drain consumed all five written source tails in 54.186 seconds, using 0.04 extra daemon CPU seconds, 332,762 logical read bytes and 394,194 logical write bytes. Active physical writes were 139,784,192 bytes on v7 and 2,433,024 on v8. V8 startup was separate: 143.910 seconds, 43.34 aggregate worker CPU seconds, two workers, 89.168 MiB sampled simultaneous RSS peak and 96.305 MiB conservative non-simultaneous HWM sum. Runtime uncertainty reached 60.000248 seconds; deliberate failed polling produced 120.009795-second spacing with gap provenance. FD growth was zero. The benchmark aggregate includes an additional mock peer/harness; daemon active CPU was 0.4633%, while daemon plus harness was 0.6400%.

V9 changes only foreground picker behavior in presentation.py and Store.picker_snapshot. All other storage AST and all other background package bytes match v8. V8 resources remain measured v8 results; equivalent v9 background behavior is an explicit source-equivalence inference. Actual v9 package and production verification are separate gates.

The final v8 tenfold daemon run retained 54,490 sessions, 498,850 turns, 2,853,480 quota observations and 1,951,660 usage observations with the same five active roots and event rate. Its active CPU/RSS were 0.5100% / 52.520 MiB; idle CPU was 0.0367%. Final tail ingestion used 17.336 seconds and 0.05 daemon CPU seconds. Active physical writes were 4,345,856 bytes; descriptors remained at 12. Steady memory and work did not grow linearly with tenfold cold history. Startup cost scaled: 1,062.798 seconds and 423.66 worker CPU seconds, two workers with 161.441 MiB sampled aggregate RSS peak and 174.395 MiB conservative HWM sum. The 128 MiB criterion is steady-state; startup exceeds it. Runtime uncertainty reached 60.000370 seconds. This run intentionally skipped reconnect cycles; false cycle booleans are expected, and its old generic reconnect note is inaccurate. The separate retention run below supplies that evidence.

Twenty-five accelerated real socket/session cycles after three warmups retained all 150 completed root turns and exactly 294,848,060 microseconds, including known waits and child exclusion. RSS grew 1.238 MiB (41.340 to 42.578), descriptors stayed at 12 and the package/PID remained unchanged. This 0.25-second cadence checks retention and reconnect semantics; it does not prove minute-cadence CPU acceptance or absence of an unbounded-run leak.

Core windows exclude sockets and Codex metadata queries; the installed-wheel service check measures both separately. The synthetic history has five available active rollout files, not hundreds of thousands of available historical rollouts. Bounded source queues/pages and notification loss are exercised separately. These are reproducible isolated measurements, not a recording of a production Codex workload. Complete content-free metrics, fixture/build hashes, operation counts and I/O are saved in [the evidence artifact](benchmarks/2026-10-14-incremental-tracking.json).

Fully reconciled idle windows and the soak left historical files unchanged: persistence/projection phase time was zero. Logical writes above include progress output and disposable runtime state; they do not establish physical disk throughput. During the soak RSS and descriptor deltas were zero. One hundred genuinely new observer/store open/close cycles retained +0.199 MiB at 1x and +0.863 MiB at 10x, with zero descriptor growth. Actual socket reconnect is a separate packaged-service check. These short unpaced cycle bursts are not steady CPU measurements.

The core's maximum update operation was 0.130 seconds at 1x and 0.123 seconds at 10x, with nominal 60-second sampling latency. At 10x, active CPU and RAM stay comparable rather than growing linearly with retained history. This does not prove a byte bound for an individually enormous retained session. The v6 raw-record streaming bound was verified separately against the actual 2.136 GB record.

Startup is real work. The baseline cold load took 11.608 seconds, first persistence/native projection 164.049 seconds, and an unchanged save 1.445 seconds. Earlier optimized core cold migration/index/native projection took 190.922 seconds (61.424 CPU seconds, 48.457 MiB peak); 10x cold initialization took 1673.828 seconds (121.543 MiB peak). These include shared-host I/O contention. The earlier core's five-root save took 0.099631 seconds, versus 0.001026 seconds for an unchanged save with zero logical writes. In the matched run, a fresh disposable 1x index rebuilt in 26.986 seconds; the already indexed 10x restart took 1.179 seconds. Those restart cache states differ and must not be compared as equivalent cold costs.

The final daemon prepares migration/index/native history in a short-lived subprocess, then opens the verified cache in its long-lived process. This releases cold allocator and interned filename arenas. Both processes verify cached snapshot identities on restart, so restart scans are duplicated. Cancellation/stop terminates and reaps the child before the parent can become a writer. Cold CPU, I/O and RAM are not eliminated. Service CPU includes reaped-child CPU; its post-start parent RSS/HWM excludes child RAM, which was measured separately with the exact v5 wheel: 101.59 seconds elapsed, 40.95 CPU seconds, 48.684 MiB maximum RSS, exit 0. This child-only run excludes parent/socket/metadata initialization; a second full-scale startup run measured 108.110 seconds elapsed and 45.62 tracker-worker CPU seconds, with two simultaneous workers. At 0.1-second sampling, aggregate worker RSS peaked at 89.270 MiB; observed process HWMs summed to 96.824 MiB (a conservative, non-simultaneous sum). No worker inventory truncation occurred. Its test-only one-second cadence and zero-length active window provide startup evidence only. The full minute-cadence service run took 111.471 seconds to initialize, including 43.12 child CPU seconds plus 4.06 parent CPU seconds; startup logical read/write were 1,275,005,993 / 853,674,138 bytes.

Build scope is explicit: matched core windows use immutable v4 hash d84849e8eaa7fe3b4d489b6a5514d08c766174d5cd49b9bbd05e19168e0b405d. The soak uses v3 hash e05442a546b8102556910699236042924629eebfe11b4c9478aa77af8b22d546. v4 changed only offline recovery guards; v5 adds startup isolation before the byte-identical tracking loop. The evidence reviewer verified these differences. The v3 active/cycle timestamps replayed existing coverage, so those costs are not used as active evidence. V5 wheel resources were measured independently. Both five-minute windows passed the targets. Including the mock peer/harness, measured idle was 0.1600% CPU / 79.238 MiB RSS and active 0.1867% / 79.086 MiB; this extra process is test infrastructure. Parent HWM was 48.637 MiB; aggregate sampled peak 79.238 MiB and sum of process HWMs 80.324 MiB. The idle window includes bounded historical metadata reconciliation (307,777 logical write bytes), so it is not evidence of zero historical writes after full reconciliation. The separate fully reconciled core windows and soak establish that claim. The old live PID 3886 assessment (~99% CPU, 1.83 GiB RSS) remains separate because its loaded bytecode predates inspected files.

## Reproduce and verify

Run from the optimized checkout; no sudo. All fixture commands below operate on disposable sanitized history. Plain output removes decorative glyphs; JSON stdout remains clean and progress continues on stderr. Progress elapsed times are since helper startup; completed JSON window durations are measured separately. Paths under /tmp are examples; choose fresh paths when retaining results.

```bash
uv run python scripts/verify-parity.py --plain --json --work-dir /tmp/codex-parity-review
uv run python scripts/benchmark.py --baseline /absolute/deployed-checkout --work-dir /tmp/codex-performance-review --plain --json
uv run python scripts/benchmark.py --skip-baseline --scale 10 --work-dir /tmp/codex-performance-10x --soak-seconds 0 --plain --json
uv run python scripts/service-smoke.py --executable /absolute/wheel-venv/bin/codex-time --metadata-fixture --rollout-event-seconds 0.25 --duration 300 --idle-seconds 300 --plain --json
```

The benchmark verifies that repeated workers advance coverage, and its inventory avoids process-wide pathlib filename interning. The benchmark defaults to 300-second idle/active windows, 1800-second idle soak and 50 cycles. --fixture-only writes inputs; --sessions/--turns/--quota/--usage select a small smoke scale. --baseline-only and --skip-baseline select one implementation. --optimized can point to an immutable source snapshot. Short overrides explicitly leave targets unvalidated. The package smoke rejects editable source unless --allow-source is explicitly used for tests; --sample-seconds 1 is a test shortcut and does not prove minute-cadence targets. The optional --metadata-fixture streams matching thread/turn/name history and waits for name bootstrap before starting measured windows. The peer tests known waits, failed polls/reconnect, precise completion, 65-second heartbeat freshness, token-journal integrity and graceful shutdown. Optional --rollout-event-seconds 0.25 appends fixed synthetic 4 KiB ignored messages across five roots during active work. The producer stops before the exact written-tail checkpoint barrier; JSON and human output report final drain wall time, CPU and logical I/O separately. Include this cost in the complete event workload. Omit the option for quiet input. For a final daemon soak use --duration 0 --idle-seconds 1800 --skip-cycles --timeout 3000 in a fresh directory; the earlier core soak retains its separate build scope. The parity harness compares actual report JSON/CSV, aliases, migration/restart, and isolated installed native readers.

Automated validation is separate: final v9 passed 475 pytest regressions in 97.56 seconds after descriptor wake, batching and picker RED/GREEN corrections; exact commands and observed tool-result references are saved in .harness/incremental-tracking/validation.json. strict mypy passed for 34 modules, Ruff passed, and the final v9 wheel built successfully. Tests are deterministic where cadence is involved. Final source parity passed 12 report/export cases and six aliases. The actual v5 wheel matched six canonical JSON reports. Verified current-data legacy conversion retained six sessions, seven turns, four unique quota readings and six usage observations; the prior reader matched all six reports and native projections (154,625,000,000 ns). Picker/resume and Git restore run through the actual-process/PTY regression suite.

The defining tests cover interrupted layout publication, embedded evidence, corrupt durable data, corrupt disposable indexes, external cached/session restore, interrupted native projection, bounded queue overflow, lost notifications, partial writes, same-inode rewrites/truncation, metadata/name joins and exact counter/feature parity.

## Migration and verified backups

Stop the writer before copying or restoring any data. Keep the configured service directories/socket; an existing deployment may use overrides. Back up the complete durable directory and the separate runtime directory. Preserve the prior executable build and service definition. Verify copied hashes and feature reports before activation. Do not install from main when it lacks the deployed token/cost feature commits.

On first start, migration copies and verifies original ledger/journals, streams validated sessions into individual snapshots, creates separate legacy-observation files, then publishes layout.json last. An interruption before publication leaves the old ledger readable; retry validates the same original backup and completes idempotently. Original journals are never modified by embedded-evidence migration. Snapshot writes are atomic and fsynced. A runtime pending-projection marker precedes a changed session snapshot; it is removed only after the durable layout and SQLite checkpoint commit. A crash replays that marker. Index loss/corruption or restored source identities trigger a bounded-memory rebuild and native reconciliation. Corrupt runtime indexes are quarantined; corrupt portable evidence is refused with an actionable restore error.

For portable/Git restore, stop the service and restore the complete matching durable snapshot, including layout/sessions and all journals. Restart with the matching new executable. Runtime indexes are disposable and should not be merged or committed. Any data file over 3 MB requires Git LFS and its matching .gitattributes in a Git backup. Keep machine-local locks, caches and staging outside that repository. An isolated session snapshot restore is detected at restart and clears stale rollout checkpoints and metadata row signatures/table cursors; exact explicit names and their independent cursor survive. A defining regression verifies metadata-only turns and names replay. A cached external change while a writer runs is refused rather than overwritten. Internal cached session objects are batch-scoped: reacquire them through the mapping before changing them in a later batch.

```bash
uv run python scripts/storage-recovery.py --data-dir /absolute/stopped-data --state-dir /absolute/runtime --plain --json verify
```

Expected: verified=true with session/turn and exact unique evidence counts. This reads portable data using a disposable disk index and one model at a time. It takes the canonical writer lock and refuses to compete with the daemon.

## Lossless rollback

Keep the new data and its verified pre-migration backup. An older executable reads the retained original ledger, which omits newer partitioned timing; simply reinstalling the old package is insufficient. Stop tracking and export **current** data to a new directory first:

```bash
uv run python scripts/storage-recovery.py --data-dir /absolute/stopped-data --state-dir /absolute/runtime --plain --json export-legacy /absolute/new-legacy-export
```

Direct export validates tracker-native projection schemas and refuses foreign files/symlinks before conversion. The export streams current sessions into a v4 ledger, combines legacy and new evidence with exact on-disk deduplication, preserves public evidence order and native projects/records, verifies unique counters and writes a SHA-256 conversion manifest. It publishes only after validation and leaves source data unchanged. Use the old executable with that verified directory and a fresh runtime directory; preserve the partitioned original. Missing sources retain durable evidence. Restore the pre-upgrade backup only when deliberately accepting its older point in time; retain all newer snapshots/exports for recovery.


## Historical v7 build and deployment

V7 was the reviewed live build at that checkpoint, activated by another actor after isolated verification. Its actual CPU acceptance was unmet. Its complete suite passed **453 tests in 76.34 seconds**; strict mypy passed 34 modules, Ruff and the wheel build passed. All 35 package source/data files match the source-content digest below. The packaged token smoke also passed 1,320,000 synthetic tokens, USD 2.91 and CAD 3.9285 at fixture rate 1.35, including periods, child attribution, auto-review exclusion, replay and read-only reports. Actual packaged parity passed 71 subprocesses, 12 report comparisons, six aliases, six prior-reader reports after current-data legacy export, native total 154,625,000,000 ns, and exact counter 9,007,199,254,741,001.

- Source-content SHA-256: `6b787ce50cfb05dd46320164c115fd3bf7312f3e3cd7d29f845281649366af71`.
- Wheel archive SHA-256: `6eef7b33349a0e9650c161d1224b044ceef335918c81e7465561f1c4126f1d56`.
- Durable verified bundle: `/home/kevin/.local/state/codex-time/deployments/incremental-v7-20261014`.
- Isolated executable: `/tmp/codex-time-final-packaged-v7/bin/codex-time`.
- Final packaged five-minute active/idle windows and socket cycles passed, exit 0; actual v7 CPU acceptance remains unmet.

V7 ran in production at PID3873422/startticks43773434, source digest6b787ce50cfb05dd46320164c115fd3bf7312f3e3cd7d29f845281649366af71. Another actor activated v7; root did not repeat the rejected action. The v6 statements below retain historical scope. Our v6 activation command was rejected before execution because “cont” was ambiguous authorization. Another actor subsequently activated the durable v6 bundle; its manifest, installed identity and user unit were independently verified. No duplicate install or restart was attempted. A concurrent commit, `33ce9ed`, contains the implementation; root did not create it or rewrite history. Follow-up metadata, harness and evidence changes remain in the working tree.

The original pre-v5 backup verifies 5,511 sessions, 51,520 turns, 288,746 quota observations and 198,564 usage observations. It remains in the durable `incremental-v5-20261014` sibling bundle. V6 activation additionally verified 5,513 sessions, 51,548 turns, 288,799 quota and 198,617 usage observations. V7 preparation captured the then-installed v6 package as its rollback target. Keep all older bundles: a working rollback package and verified data backup serve different purposes.

Prepare each bundle at its final location because recovery environments contain absolute paths. Preparation and verification do not stop or install anything. Activation and rollback need the separate authorized operator action.

```bash
uv run python scripts/deployment.py --plain --json prepare --wheel /absolute/final.whl --destination /absolute/fresh-bundle
python3 /absolute/bundle/deployment.py --plain --json verify --bundle /absolute/bundle
python3 /absolute/bundle/deployment.py --plain --json activate --bundle /absolute/bundle
python3 /absolute/bundle/deployment.py --plain --json rollback --bundle /absolute/bundle
```

Flags --plain/--json precede the subcommand. Optional --installed-executable/--uv/--systemctl/--service select explicit operator seams. Use the captured helper after review; no sudo is needed. Do not work around an approval rejection by changing bundle paths or mutating the live installation.

Activation verifies artifacts, installed bytes and the unchanged service, stops its writer, verifies tracker-owned portable/runtime backups and counters, rechecks lineage immediately before installation, then starts the preserved unit. Rollback verifies expected upgraded bytes, stops the writer, validates projection scope, exports CURRENT evidence and verifies hashes/counts, carries the valid FX cache into a fresh runtime, and installs the previous wheel. One owned systemd drop-in selects that validated export/runtime while retaining literal original daemon options. Originals, backups and unrelated files remain intact.

The eleven helper regressions exercise real portable recovery with disposable installer/service seams. An actual offline report retained rate 1.3712, USD 0.002 and CAD 0.0027424. Prior-reader reports and native projections match the converted store. These checks establish the recovery mechanics; no production rollback was performed. Previous package bytes are exact, but historical PID bytecode and the prior dependency lock are not reconstructed.

Artifact mismatch, changed installation/unit lineage, complex unit expansion/hooks, corrupt data, symlinks or mixed projection files are refused before installation. A post-install interruption retains its operation stage and backup/export, leaving the service stopped for inspection. Blind retry is refused.

## Real-corpus OOM and data retention

The first v5 production backfill failed despite passing the isolated history-scale fixture. A bounded inventory found 6.190 GiB across 5,516 rollouts, including one complete 2,135,854,844-byte record. Whole-record readline, whole-body UTF-8 decoding and an escape-heavy backtracking string lexer caused transient allocations; systemd recorded a 32.7 GiB peak before OOM. This does not establish a retained-history leak.

V6's defining public scanner RED failed with a 384 MiB ignored body under a 256 MiB address-space limit. Streaming GREEN preserves lifecycle fields after that body, partial-write/restart semantics, UTF-8/escape boundaries and malformed-line recovery. The exact real record consumed **45.336 MiB VmHWM**, retained **147 selected JSON bytes**, and finished in **13.597 seconds** under the same 256 MiB limit. Independent differential selection matched 2,500 valid records at 1–35-byte chunks. No real body, identifier or private source path was copied into the evidence artifact.

Actual v6 source reconciliation reached all 5,525 current source inode checkpoints, with no unread complete records and names replay complete. Four partial final lines were deferred correctly. An unresolved-context SQL counter is recorded separately; it is not unread backfill.

The read-only v6 audit retained every original session and turn, all 51,520 starts and 51,480 closed ends, all 1,819 known waits, 12,411 coverage spans and 60,147 model contexts. All original quota/usage identities and payloads, exact 11,855,017,692 token delta and missing-data counts match; zero mismatches. Original ledger/journal prefixes and migration backups match verified hashes. New evidence is counted separately. With the writer running, this uses atomic session snapshots and bounded journal snapshots, not one global snapshot.

Actual overview JSON and model CSV commands exited 0, with expected allowance, token_usage, model_totals and reasoning fields. A live uncertainty snapshot reached **60.072357 seconds**, including read latency. The documented short-wait and outage limits remain.

## Actual CPU miss and the v7 correction

The v6 live window measured **13.0459% of one core**, **59.281 MiB RSS** and **12 descriptors** over 300.017 seconds, with zero RAM/descriptor growth or PID rotation. It had one working/four idle roots, plus child observations. Logical read/write were 85,054,935 / 51,203,663 bytes; physical writes were 57,618,432 bytes. This is a real mixed-workload CPU miss, not an idle or five-working-root pass. Source/name readiness does not prove the first full SQLite metadata sweep completed: independent cursors wrap, zero is ambiguous, and there is no persisted first-pass marker.

The recurring defect is independently established: unchanged turn/edge metadata loaded full sessions before checking row signatures, and unchanged thread rows reloaded sessions to assign already-known explicit titles. The public IndexedStore RED produced 152 session lookups, 129 deserializations and 258 serializations during one unchanged refresh. A separate read-only real-DB spy confirmed recurring lookups; its simulated cache-load counts are explicitly labelled in the artifact. First-sweep uncertainty does not explain away this work.

V7 checks cheap membership before marking orphan evidence applied, then checks signatures before retrieving models. Changed/new threads and explicit-name appends retain pending-name, rename and restore paths. Independent review and combined integration tests preserve child/turn replay and isolated snapshot restore.

| Six identical unchanged refresh/flush operations | V6 | V7 |
| --- | ---: | ---: |
| CPU seconds | 0.358254 | 0.049858 |
| Wall seconds | 0.361109 | 0.053165 |
| Session lookups | 2,538 | 0 |
| Snapshot deserializations | 1,099 | 0 |
| Serializations | 2,198 | 0 |
| Logical read bytes | 13,973,015 | 1,304,708 |

Inputs were identical, content-free: 260 sessions, 5,300 turn rows, 259 edges and 260 names, with cache size two and a 128-row historical page plus one active ID. All 260 snapshot content hashes remain unchanged. Runtime cursor writes remain 49,440 logical bytes. This operation benchmark does not establish a five-minute live CPU result. The subsequent actual v7 window below measured a CPU miss; the metadata gate fix alone is insufficient.

## Remaining limits

- One retained giant session and foreground all-history reports can allocate more memory; eight cached sessions are not a byte cap. Raw ignored JSONL bodies now stream with explicit metadata/schema limits.
- A complete giant record can exceed the between-record batch duration; the actual record took 13.6 seconds. Sampling uncertainty includes actual latency.
- Cold migration/index/native rebuild scales with history and produces substantial one-time I/O. The reaped worker releases cold arenas; it does not erase startup cost.
- The earlier 1x/10x and 30-minute soak results retain their immutable build scopes. V7 changes metadata gating; it is not byte-identical to that soak build. Fully reconciled old core windows prove their unchanged-input behavior; new packaged/live checks are separate.
- Boundary-preserving same-inode middle overwrite plus growth may need explicit import-history. Normal replacement, truncation, same-size rewrite and changed boundaries are covered.
- Historical reconciliation is gradual. Source SQLite index quality affects query cost; the tracker never modifies Codex databases.
- The first isolated v6 resource attempt lost its daemon with no recorded exit code, traceback or OOM evidence. Its incomplete window is excluded. The harness now captures actual child returncode/signal/log path and still fails strictly; a fresh v6 attempt passed; the original exact exit remains unknown.

Older filename-interning and replayed-epoch measurements remain in the artifact with their diagnosed limits. No restart, longer sleep, resource cap, history deletion or downsampling is counted as the optimization.

## Final packaged v7 result

The exact v7 installed wheel completed both five-minute windows and all socket evidence checks, exit0. Daemon active CPU was0.060000% with47.094MiB RSS; idle was0.033333% with47.289MiB. Including the mock peer/harness, active was0.146666%/77.766MiB andidle0.116666%/77.961MiB. These are sanitized fixture measurements; they do not override the actual v7 CPU miss below. Idle includes bounded runtime metadata reconciliation, so it is not a new fully reconciled historical-write-free soak.

Known2.125-secondwait, exactlifecycle, unchangedtokenjournals, waiting/unknown/reconnect and65-secondfreshhealth passed. Runtime uncertainty was60.000254seconds; intentionalfailed-poll spacing120.059311seconds retainedobservation_gap provenance. Daemongracefulexit0 andidleFDdelta0. Startup was101.860seconds/41.35workerCPU seconds including37.79reapedchildCPU seconds; sampled aggregate worker RSS89.082MiB, conservative non-simultaneous HWMsum96.234MiB,two workers, no inventorytruncation. Startup costs remain separate from steady windows.

## Actual v7 results and next bounded batch

The known live v7 digest above completed22:53:09–22:58:09UTC without restart:300.018seconds,74.14selfCPU seconds=24.7118% of onecore,51.035MiB RSS and11descriptors. RSS grew0.613MiB; descriptors fell byone. Logical read/write were110,185,691/71,288,076bytes and physical writes85,381,120bytes. This naturally changing workload grew fromone tofour known working roots plus children; it is not controlled idle/five-root acceptance. An independent five-second process tick delta confirms27.5986%CPU. Maximum observed sampling uncertainty was60.082805seconds. Source/name readiness does not prove SQLite first-sweep completion.

Actual v7 audit retained every original5511session/51520turn,all1819waits/12411coverage spans/60147modelcontexts and288746quota/198564usage identities and payloads, includingexact11,855,017,692token delta. All original ledger/journal prefixes and verified backup hashes match, zero mismatches. New evidence remains distinguished; concurrent atomic snapshots are not a global snapshot.

The copied105KiBroot public scanner diagnostic retained identical final evidence while reducing30separate-event saves(0.4440CPU s) toonecoalescedsave(0.01579s). Persistence was96.5% of separate CPU. V8 implements first-event-anchored warm deadlines with bounded queues and rapid startup/backfill. Deterministic RED/GREEN and the event-bearing packaged comparison above verify the remedy on the fixture. Production acceptance awaits separately authorized activation and measurement.

## Final v9 package and activation gate

The final wheel has canonical 35-file source/package digest `fc3aabd983bc36ef5296199f020ae111948635a9b1fb338de5978dbff0a22c82` and archive SHA256 `3fd036a75c0ef4752a1e066bb66da3cbafdeb3bed4911354b3063a6a5f51941a`. All 71 packaged CLI subprocesses, twelve report cases, six aliases, native reader totals and six prior-reader legacy reports pass. Token smoke preserves 1,320,000 tokens, USD 2.91 and CAD 3.9285 at fixture FX 1.35.

An actual 80x24 packaged PTY observed an external writer's title change without keypress in 0.863 seconds. Search miss/match, selection/details, stable-ID resume through a fake Codex executable, cwd/CODEX_HOME, cooked input and terminal restoration all pass. Package identity is unchanged before/after. A separate short socket smoke consumed all five event tails and preserved known waits/lifecycle/reconnect; its five-second windows are functional checks, not CPU acceptance. All fixture data and fake launcher artifacts remain synthetic under /tmp.

The durable bundle `/home/kevin/.local/state/codex-time/deployments/incremental-v9-20261014` is prepared and hash-verified. Preparation captured the actual installed v7 wheel for rollback and changed no live service. The guarded helper takes a fresh stopped-writer backup during activation and exports verified CURRENT evidence before rollback. No production rollback has been performed. Later v6/v7 approval replies name builds already externally activated; they require no repeat action and do not substitute for approval of v9. V9 is explicitly authorized and active; its completed actual resource window and post-activation audits are recorded below.

The final smoke helper corrects one output-only label: --skip-cycles now explicitly reports skipped reconnect cycles instead of claiming they ran. Defining actual-CLI RED and 14 focused smoke checks pass after the correction; v9 package bytes are unchanged. The earlier raw 10x/soak artifacts retain their original helper notes with an explicit erratum above. Full 475-test validation predates this harmless output-label follow-up; it is not relabeled as a 476-test full run.

The final v8 fixed-input daemon soak completed 1,800.001 seconds at 0.03056% CPU, with post-startup RSS 46.523 MiB and final RSS 47.949 MiB (no recorded idle-start baseline) and descriptors unchanged at 12. Parent lifetime HWM was 47.949 MiB. Logical writes were 1,892,000 bytes and physical writes 2,703,360 bytes, including disposable metadata cursors/heartbeat state; those counters alone cannot distinguish historical writes. Exact known waits, lifecycle, token-journal integrity and graceful exit passed. The independent observer has only 300.011 seconds of resource samples and initial content/stat hashes; it stopped with no final comparison, for an unknown reason. Its partial evidence is not a full-soak unchanged-history proof. Fully reconciled core unchanged-file scopes and deterministic idle-write regressions remain separate evidence; the limitation is retained rather than inventing final hashes. The soak intentionally skipped active/reconnect cycles, which the separate event/retention runs cover.

## Deployed v9 historical verification

User explicitly approved the exact v9 bundle, and guarded activation exited 0. Service start is 2026-10-15 00:06:40 UTC, PID 4027405/startticks 44222560, with no restarts. The fresh backup verified 5,613 sessions, 52,667 turns, 291,709 quota observations and 201,529 usage observations across 18,378 durable/runtime files. Actual installed source/package digest matches the tested v9 build.

Read-only audits against both the original pre-v5 baseline and the complete authoritative pre-v9 layout-v1 backup pass with zero mismatches. The latter preserves all 52,667 starts, 52,627 closed ends, 1,823 waits, 12,487 coverage spans, 61,273 model contexts and every exact observation identity/payload; retained token delta is 12,115,020,693. All backup manifest hashes and retained original file prefixes match. New sessions/turns/observations and title updates are distinguished. These are per-session atomic reads and bounded journal snapshots while tracking continues, not a globally atomic live count. Actual `overview all --plain` exits 0 with token/cost/FX/model work and an explicit unpriced-token coverage notice.

The first live resource monitor's all-current-tail barrier could remain false under normal 60-second active ingestion; it did not distinguish cold backlog from ongoing arrivals. Its incomplete attempt remains saved and supplies no completed CPU-window claim. A separate fixed300s natural-load observation requires no bootstrap child, service age over90s and a fresh initial heartbeat, retains actual backlog per sample and explicitly leaves full source/SQL catch-up unproven. Controlled idle/five-root resource acceptance remains the separately measured immutable fixture scopes. The production process and sampling are unchanged by this instrumentation correction.

## Final live resource result and remaining limits

The approved v9 process completed 2026-10-15 00:12:45–00:17:45 UTC: **300.130819 seconds, 2.15 CPU seconds, 0.716354% of one core**, RSS **50.695 to 50.895 MiB**, FD12 to FD12, one background worker. Package digest, PID4027405/startticks44222560 and NRestarts0 matched before/after. Logical read/write deltas were 76,317,654 / 8,874,478 bytes; physical writes were 11,915,264 bytes. Parent lifetime HWM and sampled window peak were 50.895 MiB. Final health is fresh with no live diagnostic; the actual top spot check showed 52,120 KiB RES and 0.0% instantaneous CPU in both samples. Spot checks are not the five-minute result.

The natural workload contained four idle/two working root snapshots and intermittent six-unknown snapshots, plus 37 children excluded from root timing. Current source files grew 5,629 to 5,637; indexed current sources grew 5,624 to 5,635. Unread complete-record sources varied 3–11 and ended at three; two model-context sources remain unresolved. Full source/SQL catch-up is unproven. This observation excludes elapsed startup after a service age of 364.6 seconds with no bootstrap child, but includes ongoing incremental reconciliation and Codex connection outages. It is not controlled idle/five-root production acceptance or a paired comparison with the earlier changing v7 workload. The separately completed fixture windows establish those controlled targets.

Actual maximum recorded uncertainty was **60.081909 seconds**, maximum sampled heartbeat age 48.413 seconds. Codex connection losses produced unknown states and recovered; no continuous work is invented across those outages. Short waits can be missed by minute sampling; exact recorded lifecycle and known waits remain unchanged. The full-soak independent historical hash pair is unavailable, cold tenfold startup peaks above 128 MiB, foreground all-history reports may use more RAM, and a single giant retained session is not byte-bounded by an eight-entry cache. These limits remain explicit.

Final manual checks are the actual installed top/health/overview commands in the handoff. They ran successfully in fish; native terminal/clipboard access is unavailable to this session, so wrapped selection/paste from the Codex UI remains unverified. No rendering setting was changed.
