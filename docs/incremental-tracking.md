# Incremental tracking, measurement and recovery

This guide explains the bounded background design and how to verify an upgrade without losing recorded evidence. Compare the sanitized benchmarks and report parity first, prepare verified backups, activate a known package, and use a validated legacy export when rolling back.

## Design and feature contract

The portable source of truth is layout v1: atomic per-session JSON snapshots, the original append-only quota and usage journals, and separate legacy journals for observations formerly embedded in ledger.json. The original ledger and a SHA-256-verified pre-migration backup remain intact. Eight session objects are cached. A disposable SQLite index stores exact quota/usage identities, source offsets/cumulative baselines, explicit names, metadata row signatures and native record ownership; it uses a 4 MiB page cache. History is never deleted or downsampled. An append-only timing-session journal was rejected because minute updates would repeatedly append a complete active session and enlarge every portable backup.

The daemon processes coalesced inotify paths with bounded queues (4,096), watches (8,192), batches (128 names, 2,000 complete records, 8 MiB between records), and a single writer. Stat-only scans can skip unchanged sources without opening them. Event, active-source and bounded reconciliation scans also verify at most 512 bytes of saved prefix/tail before deciding whether to decode new records; this catches same-size writes whose filesystem timestamps collide. JSON selection decodes only whitelisted timing/token fields. Oversized records stream through 64 KiB chunks, with incremental UTF-8 validation and non-backtracking string runs; ignored bodies are never materialized. Selected metadata is limited to 1 MiB/4,096 nodes, depth 256 and 8,192-byte scalar literals. Unsupported records retain diagnostics/gap provenance. Partial records commit neither evidence nor offsets. A complete giant record may exceed the between-record batch duration/byte budget; the actual 2.136 GB record took 13.6 seconds at 45.3 MiB peak RSS. Healthy notifications rotate 128 historical source names per minute; startup/overflow/unavailable notifications perform full reconciliation in bounded batches. Loaded sessions' checkpoint paths and read-only metadata rollout paths are checked at each sample. Initial explicit-name replay completes in bounded fast pages before steady minute pacing. SQLite metadata reads exact active IDs and 128 historical rowids per table, without assuming monotonically increasing updated timestamps. Explicit session-index names are tailed and stored exactly on disk, including names whose sessions have not yet been discovered.

Live observation, portable persistence, native projection and terminal refresh have independent work. Only changed sessions are serialized. Title-only changes leave native records untouched. Native cleanup touches the recorded paths owned by an affected session; frequent loops do not sweep the projection directory. Health reads only metadata/counts; the picker loads timing without token journals and caches its snapshot for a minute. Full allowance/cost reports remain on-demand processes and can consume substantial transient memory at very large history sizes.

The existing CLI/aliases, exports, picker/resume, native readers, model/reasoning attribution, precise lifecycle timestamps, known blocking waits, quiet tool work, concurrent roots, child exclusion, per-turn cwd, midnight/DST splitting, token/cost/FX evidence and exact integer counters are retained. Historical token counts above JavaScript's integer precision are exercised by the parity harness. Codex integration remains read-only; no thread subscription, loading, mutation or approval response is sent. The generated fixtures contain no raw messages, tool output, credentials or auth data. Fixture inputs must be explicitly sanitized; production activation backs up only tracker-owned content-free evidence.

## Timing and freshness

Default socket sampling is 60 seconds; daemon --sample-seconds permits values greater than zero and at most 60. Each sample includes configured cadence plus actual read latency. The final wheel reported 60.000214 seconds of runtime uncertainty. A deliberate failed poll produced a 120.066-second spacing with observation_gap provenance, rather than continuous work. The observer also retains actual inter-sample spacing as uncertainty. A gap over 75 seconds at minute cadence is not joined as continuous working time. Heartbeat freshness is 90 seconds. The UI shows a sampled estimate only while the observation remains fresh (75 seconds at nominal minute cadence); it does not persist that extrapolation.

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
| Final v5 daemon idle, sockets + metadata | 300.001 | 0.086666% | 48.637 | 4,896,661 / 307,777 | 5 samples |
| Final v5 daemon five roots, sockets + metadata | 300.001 | 0.110000% | 48.484 | 5,065,391 / 1,892,313 | 5 samples |

Core windows exclude sockets and Codex metadata queries; the installed-wheel service check measures both separately. The synthetic history has five available active rollout files, not hundreds of thousands of available historical rollouts. Bounded source queues/pages and notification loss are exercised separately. These are reproducible isolated measurements, not a recording of a production Codex workload. Complete content-free metrics, fixture/build hashes, operation counts and I/O are saved in [the evidence artifact](benchmarks/2026-10-14-incremental-tracking.json).

Fully reconciled idle windows and the soak left historical files unchanged: persistence/projection phase time was zero. Logical writes above include progress output and disposable runtime state; they do not establish physical disk throughput. During the soak RSS and descriptor deltas were zero. One hundred genuinely new observer/store open/close cycles retained +0.199 MiB at 1x and +0.863 MiB at 10x, with zero descriptor growth. Actual socket reconnect is a separate packaged-service check. These short unpaced cycle bursts are not steady CPU measurements.

The core's maximum update operation was 0.130 seconds at 1x and 0.123 seconds at 10x, with nominal 60-second sampling latency. At 10x, active CPU and RAM stay comparable rather than growing linearly with retained history. This does not prove a byte bound for an individually enormous retained session. The v6 raw-record streaming bound was verified separately against the actual 2.136 GB record.

Startup is real work. The baseline cold load took 11.608 seconds, first persistence/native projection 164.049 seconds, and an unchanged save 1.445 seconds. Earlier optimized core cold migration/index/native projection took 190.922 seconds (61.424 CPU seconds, 48.457 MiB peak); 10x cold initialization took 1673.828 seconds (121.543 MiB peak). These include shared-host I/O contention. The earlier core's five-root save took 0.099631 seconds, versus 0.001026 seconds for an unchanged save with zero logical writes. In the matched run, a fresh disposable 1x index rebuilt in 26.986 seconds; the already indexed 10x restart took 1.179 seconds. Those restart cache states differ and must not be compared as equivalent cold costs.

The final daemon prepares migration/index/native history in a short-lived subprocess, then opens the verified cache in its long-lived process. This releases cold allocator and interned filename arenas. Both processes verify cached snapshot identities on restart, so restart scans are duplicated. Cancellation/stop terminates and reaps the child before the parent can become a writer. Cold CPU, I/O and RAM are not eliminated. Service CPU includes reaped-child CPU; its post-start parent RSS/HWM excludes child RAM, which was measured separately with the exact final wheel: 101.59 seconds elapsed, 40.95 CPU seconds, 48.684 MiB maximum RSS, exit 0. This child-only run excludes parent/socket/metadata initialization; a second full-scale startup run measured 108.110 seconds elapsed and 45.62 tracker-worker CPU seconds, with two simultaneous workers. At 0.1-second sampling, aggregate worker RSS peaked at 89.270 MiB; observed process HWMs summed to 96.824 MiB (a conservative, non-simultaneous sum). No worker inventory truncation occurred. Its test-only one-second cadence and zero-length active window provide startup evidence only. The full minute-cadence service run took 111.471 seconds to initialize, including 43.12 child CPU seconds plus 4.06 parent CPU seconds; startup logical read/write were 1,275,005,993 / 853,674,138 bytes.

Build scope is explicit: matched core windows use immutable v4 hash d84849e8eaa7fe3b4d489b6a5514d08c766174d5cd49b9bbd05e19168e0b405d. The soak uses v3 hash e05442a546b8102556910699236042924629eebfe11b4c9478aa77af8b22d546. v4 changed only offline recovery guards; v5 adds startup isolation before the byte-identical tracking loop. The evidence reviewer verified these differences. The v3 active/cycle timestamps replayed existing coverage, so those costs are not used as active evidence. Final v5 wheel resources are measured independently. Both five-minute windows passed the targets. Including the mock peer/harness, measured idle was 0.1600% CPU / 79.238 MiB RSS and active 0.1867% / 79.086 MiB; this extra process is test infrastructure. Parent HWM was 48.637 MiB; aggregate sampled peak 79.238 MiB and sum of process HWMs 80.324 MiB. The idle window includes bounded historical metadata reconciliation (307,777 logical write bytes), so it is not evidence of zero historical writes after full reconciliation. The separate fully reconciled core windows and soak establish that claim. The old live PID 3886 assessment (~99% CPU, 1.83 GiB RSS) remains separate because its loaded bytecode predates inspected files.

## Reproduce and verify

Run from the optimized checkout; no sudo. All fixture commands below operate on disposable sanitized history. Plain output removes decorative glyphs; JSON stdout remains clean and progress continues on stderr. Paths under /tmp are examples; choose fresh paths when retaining results.

```bash
uv run python scripts/verify-parity.py --plain --json --work-dir /tmp/codex-parity-review
uv run python scripts/benchmark.py --baseline /absolute/deployed-checkout --work-dir /tmp/codex-performance-review --plain --json
uv run python scripts/benchmark.py --skip-baseline --scale 10 --work-dir /tmp/codex-performance-10x --soak-seconds 0 --plain --json
uv run python scripts/service-smoke.py --executable /absolute/wheel-venv/bin/codex-time --metadata-fixture --duration 300 --idle-seconds 300 --plain --json
```

The benchmark verifies that repeated workers advance coverage, and its inventory avoids process-wide pathlib filename interning. The benchmark defaults to 300-second idle/active windows, 1800-second idle soak and 50 cycles. --fixture-only writes inputs; --sessions/--turns/--quota/--usage select a small smoke scale. --baseline-only and --skip-baseline select one implementation. --optimized can point to an immutable source snapshot. Short overrides explicitly leave targets unvalidated. The package smoke rejects editable source unless --allow-source is explicitly used for tests; --sample-seconds 1 is a test shortcut and does not prove minute-cadence targets. The optional --metadata-fixture streams matching thread/turn/name history and waits for name bootstrap before starting measured windows. The peer tests known waits, failed polls/reconnect, precise completion, 65-second heartbeat freshness, token-journal integrity and graceful shutdown. The parity harness compares actual report JSON/CSV, aliases, migration/restart, and isolated installed native readers.

Automated validation is separate: 449 pytest regressions passed in 73.23 seconds after the v6 streaming correction; exact commands and observed tool-result references are saved in .harness/incremental-tracking/validation.json. strict mypy passed for 34 modules, Ruff passed, and the v6 wheel built successfully. Tests are deterministic where cadence is involved. Final source parity passed 12 report/export cases and six aliases. The actual v5 wheel matched six canonical JSON reports. Verified current-data legacy conversion retained six sessions, seven turns, four unique quota readings and six usage observations; the prior reader matched all six reports and native projections (154,625,000,000 ns). Picker/resume and Git restore run through the actual-process/PTY regression suite.

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


## Prepared activation and rollback

The corrected immutable v6 bundle is `/home/kevin/.local/state/codex-time/deployments/incremental-v6-20261014`. It contains verified final/prior wheels, the preserved unit and an isolated recovery environment. Its rollback wheel is the exact original pre-v5 installed package, rather than the intermediate OOM-prone v5 build. The original verified pre-upgrade backup remains in the durable `incremental-v5-20261014` sibling bundle. Recovery paths were verified at these durable locations. V5 was activated and failed during real backfill; the service is paused. V6 activation awaits explicit approval after automatic review rejected the ambiguous continuation. Prepare bundles at their final location because recovery environments contain absolute paths.

```bash
uv run python scripts/deployment.py --plain --json prepare --wheel /absolute/final.whl --destination /absolute/fresh-bundle
python3 /absolute/bundle/deployment.py --plain --json verify --bundle /absolute/bundle
python3 /absolute/bundle/deployment.py --plain --json activate --bundle /absolute/bundle
python3 /absolute/bundle/deployment.py --plain --json rollback --bundle /absolute/bundle
```

`prepare` reads the live installation/unit and writes only the selected bundle. Optional --installed-executable/--uv/--systemctl/--service select explicit operator seams; flags --plain/--json precede the subcommand. `activate` and `rollback` require a separate live-deployment decision. Use the captured helper after review. No sudo is needed.

Activation checks artifacts, installed bytes and the unchanged service, stops its writer, verifies curated portable/runtime backups and data counters, checks lineage again immediately before installing, then restarts the preserved unit. Rollback verifies expected upgraded bytes, stops the writer, validates projection scope, exports CURRENT evidence and checks conversion hashes/counts, carries the valid FX cache into a fresh runtime, and installs the previous wheel. One owned systemd drop-in selects that validated export/runtime while retaining literal original daemon options. Partitioned originals, backups and unrelated files remain intact.

The eleven helper regressions exercise real portable recovery with disposable installer/service seams. An actual offline CLI report returned USD 0.002 and CAD 0.0027424 using the preserved 1.3712 FX rate. The reconstructed prior wheel installed and ran actual health/overview commands successfully. Tests do not claim production activation or exact reconstruction of the historical PID's bytecode or prior dependency lock.

Artifact mismatch, concurrent upgrade, complex unit expansion/hooks, corrupt data, symlinks or mixed projection files are refused before installation. Post-install interruption retains an operation stage, backup/export and a stopped service for inspection; blind automatic retry is refused. Review the stage and retained artifacts before a recovery action.

## Remaining limits and deployment status

- Cold migration/native rebuild can be slow and produce substantial one-time I/O; 10x cost is measured separately.
- An individually large retained session can cause transient allocations; the eight-session cache is not a byte cap. All-history reports can materialize large evidence lists. Raw JSONL records now stream in bounded chunks; explicit selected-metadata/schema limits are documented above.
- Arbitrary same-inode middle overwrite plus growth retaining both saved boundaries cannot be distinguished immediately from append without rereading old bytes. Normal inode replacement, shrinkage, same-size changes and changed prefix/tail are covered; explicit import-history forces full reconciliation for unusual manual edits.
- Historical source/metadata reconciliation is gradual with reliable notifications. Current observed IDs are prioritized; explicit import-history remains the immediate full historical path. Query CPU depends on Codex's source ID indexes, which the tracker never modifies.
- V5 real backfill failed on a giant record despite passing the isolated history-scale fixture. V6 fixes the demonstrated allocation path and passes the exact record probe; complete corrected live backfill, parity and a five-minute resource window remain open. No restart or resource cap alone is counted as the optimization.

The original 10x run showed 116.7–127.0 MiB retained RSS and a 179.1 MiB high-water mark. Measurement instrumentation used os.walk filename lists across roughly 500,000 native files, leaving allocator arenas resident. Restart before that traversal used 42.7 MiB. The benchmark now streams scandir entries without a history-sized filename list; corrected matched steady windows are reported above. The original artifacts remain evidence rather than being discarded.

Deployment lineage changed during implementation: commit 0f5a5a6 adds documentation only, while installed dirty burn.py/model_usage.py/work_period.py conservatively filter report periods. Those exact product changes and six existing defining tests were carried into this build without modifying the deployed checkout. This preserves its current report optimization.

V5 added the direct-export projection guard and startup bootstrap isolation. V6 additionally changes ingestion to stream giant records. The earlier soak/scale results therefore describe their recorded immutable builds; they are not a v6 full-corpus or soak measurement. The unchanged idle path and final executable are checked separately. Ordinary-string inventory removes instrumentation filename interning; older inflated results are retained and labelled.

## Real-corpus deployment qualification

V5 activation made a verified stopped-writer backup: 5,511 sessions, 51,520 turns, 288,746 quota observations and 198,564 usage observations. A read-only audit after the OOM retained every historical start/end, all 1,819 known waits, 12,411 coverage spans, 60,147 model contexts and exact token counters, with zero missing or changed observation payloads. New evidence is counted separately. The original ledger/journal hashes match their verified backup prefixes.

Real source inventory found 6.190 GiB across 5,516 rollouts and one complete 2,135,854,844-byte record. V5's unbounded readline, whole-body UTF-8 validation and escape-heavy backtracking lexer caused transient allocation; systemd recorded a 32.7 GiB peak before OOM. No retained-memory leak is established. V6's defining public-scanner tests first failed under bounded memory, then passed with streaming. The exact real record consumed 45.336 MiB VmHWM under a 256 MiB address-space limit, retaining 147 metadata bytes in 13.597 seconds. Independent differential selection matched 2,500 valid records at 1–35-byte chunk sizes, with malformed/partial UTF-8 resynchronization checks.

V6 source-content SHA-256: `5d344eda64c792bc0ac7e18c692e3b08ae0676281ab9af097e35384973594de1`. Corrected live readiness remains unverified until activation, completed backfill, post-fix historical parity and measured stable resources. See the living postmortem and plan for the current approval gate.
