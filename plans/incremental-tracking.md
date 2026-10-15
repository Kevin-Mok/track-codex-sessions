# Execute incremental Codex tracking

This plan records the bounded tracker design, exact verification evidence and deployment gates. Use the current checkpoint below; earlier milestones retain their named build scopes. The operating guide contains reproduction and lossless recovery procedures.

## Current checkpoint — deployed v9 verification, October 15, 2026

V9 was explicitly approved and activated by the guarded helper at 2026-10-15 00:06:40 UTC, PID4027405/NRestarts0. Fresh backup and both historical audits pass; the actual300.131-second natural window measured0.716354% CPU/50.895MiBRSS with FDdelta0 and no restart. The previous production v7 result remains a measured miss. Its actual 300.018-second mixed workload measured **24.7118% CPU and 51.035 MiB RSS**; the CPU miss is preserved. Every original historical evidence record passed the independent audit. Root performed the explicitly approved final v9 install/restart; no commit or push was requested.

V8 fixes a reproduced level-triggered descriptor callback spin and coalesces source persistence. On the same sanitized history and event-rate configuration, five-root daemon CPU fell from **40.3398% to 0.4633%** across separate 300-second event windows. Physical writes fell from 139,784,192 to 2,433,024 bytes. Independently generated event streams contained 1,195 and 1,193 records. V8's final ingestion drain took 54.186 seconds and 0.04 daemon CPU seconds; it is accounted separately. Its 300-second idle window used 0.0300% CPU, 47.387 MiB RSS and no descriptor growth. These are isolated known-wheel measurements, not production acceptance.

V9 changes only foreground picker invalidation and drawing. Four cheap file-generation checks invalidate cached timing promptly; a one-second input tick redraws only when data, runtime state, input, size or minute deadline changes. This avoids stacking another minute of cache/display delay on the daemon cadence. The storage constructor and all other storage methods are AST-identical to v8; every other background package file is byte-identical. V8 measurements retain their original identity. Applicability to v9 background behavior is an equivalence inference, not a new v9 resource measurement.

- [x] Preserve deployed features, external commit 33ce9ed, original evidence, portable migration/rollback and bounded streaming.
- [x] Observe defining RED for real descriptor spin, poll-time wake retention, 122 warm scans, exact lifecycle/waits/counters and deferred-tail replay; implement minimum GREEN.
- [x] Complete matched v7/v8 event-bearing five-minute windows and separate tail drains; retain CPU misses and actual uncertainty.
- [x] Complete 25 measured real reconnect/open/close cycles after three warmups: all 150 root turns and exact 294,848,060 microseconds retained, children excluded, RSS +1.238 MiB and FD growth zero. This accelerated check is not minute-cadence CPU evidence.
- [x] Define picker cache/refresh RED; 31 focused tests GREEN. Final v9 source: 475 tests passed in 97.56 seconds, strict mypy (34 modules), Ruff, whitespace and wheel build passed.
- [x] Complete v8 1800.001-second fixed-input soak: 0.03056% CPU, 47.949 MiB final RSS, FD delta zero, exact evidence and graceful exit. Tenfold 300-second event windows: 0.5100% active / 0.0367% idle, 52.520 MiB RSS. Cold cost remains separate. The independent observer stopped after 300 seconds; its final history hash pair is unavailable and excluded. Deterministic unchanged-write tests and older core unchanged-file scopes remain separately labeled.
- [x] Verify final v9: 35 source/package files equal; all 71 CLI/native/legacy parity subprocesses and token/FX smoke pass. Actual packaged PTY refresh is 0.863 seconds without keypress; search/details/fake resume/stable ID/cwd/home/cooked terminal and clean quit pass. Short five-second active/idle socket/event smoke passes functional evidence only.
- [x] Prepare and verify the concrete v9 bundle at /home/kevin/.local/state/codex-time/deployments/incremental-v9-20261014. Exact candidate/source digest fc3aabd9…; wheel archive 3fd036a7…. At preparation, the prior wheel captured installed v7 and left production unchanged. Final v9 activation later followed explicit named-build approval.
- [x] Reconcile docs/metrics and final independent reviews: event/package review 9 verified / 0 incorrect / 1 unresolved; soak review 6 verified / 0 incorrect / 2 unresolved. The production measurement gate is now complete in its natural-load scope; the missing full-soak hash pair and unproven controlled production/catch-up scopes remain explicit. Canonical checks and refresh-config are recorded at each stage, preserving the then-running PID.
- [x] Explicitly approved guarded v9 activation; actual 300.131-second natural-load measurement 0.716354% CPU / 50.895 MiB RSS, same PID/start/hash, FD delta 0 and NRestarts 0. Both original and complete pre-v9 evidence audits pass, zero mismatches. Actual source/SQL catch-up and controlled production idle/five-root scope remain unproven; fixture targets pass separately.

No root commit/push is requested. Keep this plan with related implementation and documentation if later committed.

## Purpose and observable outcome

Preserve all deployed tracking, history, CLI/aliases, exports, session picker/resume, native timetrace readers, model/reasoning/allowance reports and token/cost/FX reporting. Preserve exact lifecycle timestamps and known waits, quiet tool work, concurrent roots, child exclusion, per-turn cwd, midnight/DST splitting, exact integer counters, renames/resumes and unknown/gap provenance. Keep Codex integration read-only and stored evidence content-free.

Provisional steady targets after warm-up: at most 0.5% of one CPU core idle, 2% with five observed roots, and 128 MiB background RSS. Validate five-minute idle/active windows, tenfold cold-history scaling, a 30-minute idle soak and repeated lifecycle/reconnect cycles. Separate startup/backfill from steady work; report actual uncertainty, measured misses and limits without deleting/downsampling history.

## Context, boundaries and protected state

- Repository: /home/kevin/coding/track-codex-sessions; implementation: .worktrees/incremental-tracking.
- At task start, the Python 3.12 uv tool installation pointed to .worktrees/token-cost-reporting; it loaded the durable v7 wheel at that milestone; final v9 is now deployed as recorded above. Feature ancestry includes 6da806f; later 0f5a5a6 is documentation-only. Main lacks deployed features and was not used as the installation source.
- Preserve deployed dirty burn.py/model_usage.py/work_period.py report-period filtering and its six defining tests. Installed-file comparisons grounded their inclusion; the deployed checkout and main remain intact.
- Git status checkpoints protect pre-existing and other-agent work. No staging, history rewriting, commit or push is authorized. Production deployment requires the explicit action approval described above.
- Read the [resource assessment](/home/kevin/coding/track-codex-sessions/docs/postmortem/2026-10-14-codex-time-resource-use.md) in the root checkout. The old live PID predates inspected source files, so its approximately 99% CPU / 1.83 GiB RSS observation is separate from the known-build baseline.
- Relevant code: incremental_storage, changes, reconciliation, bootstrap, cadence, recovery, daemon, ingestion, metadata, projection and report modules. Delivered scripts: benchmark, service-smoke, verify-parity, storage-recovery and deployment.
- Documentation/checkpoints: [README](../README.md), [smoke checks](../docs/smoke-tests.md), [operating guide](../docs/incremental-tracking.md), [review table](../.harness/incremental-tracking/checks.md) and [progress](../.harness/incremental-tracking/progress.md).

## Assumptions and settled decisions

1. Live sampling/display may lag 60 seconds. Keep precise lifecycle and known synchronous-wait timestamps. New socket evidence records sampled_waits_60s, cadence plus actual latency/spacing; reject continuous work across gaps over 75 seconds. Heartbeat freshness is 90 seconds.
2. Portable truth is layout v1: atomic per-session snapshots, original append-only quota/usage journals and separate formerly embedded evidence journals. Retain the original ledger and verified migration backup; publish the layout marker last.
3. Put exact deduplication, source checkpoints, metadata names/signatures and native ownership in disposable SQLite indexes. Cache eight sessions; use a 4 MiB SQLite cache. Session objects are batch-scoped. An append-only session journal was rejected because minute updates would repeatedly append complete active snapshots and enlarge backups.
4. Coalesce notifications and bound queues, watches, source batches and reconciliation pages. Preserve continuation fairness and single-writer behavior. Query exact active metadata IDs plus bounded historical rowids, and tail complete index-name lines using exact disk-backed pending titles.
5. Persist/project affected sessions only. Idle unchanged input causes no historical-data writes. Health and picker avoid duplicate token history; foreground reports remain separate processes.
6. Run cold migration/index/native rebuild in a short-lived child before the parent cached store. Terminate/reap it on stop/cancel before another writer can enter. This disposes cold filename/allocator retention; it does not eliminate cold CPU/I/O/peak cost. Both child and parent perform restart snapshot checks.
7. Use identical sanitized fixtures, immutable build hashes and fresh observation epochs after retained coverage. Stream inventories without os.walk filename arrays or pathlib interning. Synthetic store windows, actual socket windows, stress cycles and production observations have different scopes.
8. Prepare hashed final/prior wheels, captured unit/provenance and an isolated recovery environment. Recheck package/unit lineage after long backups. Rollback first validates a CURRENT-evidence legacy export and copies the valid FX cache into a fresh runtime; preserve original partitioned data and unrelated files.

## Historical foundation and v5 preparation checklist

- [x] Read instructions, assessment, feature docs and installation lineage; isolate implementation and protect dirty work.
- [x] Establish known-build baseline and deterministic sanitized fixtures with separate ingestion/observation/persistence/projection/startup/restart/window metrics.
- [x] Write defining RED regressions and implement changed-record snapshots/journals, exact disk indexes, bounded caches and recoverable migration/backups.
- [x] Implement coalesced events, bounded/fair queues and batches, reconciliation fallback and partial/truncated/replaced/deleted source handling.
- [x] Decouple observation, durability, projections, UI and historical repair; preserve deployed timing/report/native behavior.
- [x] Bound metadata/name replay; cover old active timestamps, child edges, rename precedence, restore replay and descriptor cleanup.
- [x] Preserve deployed report optimization; verify reports, exports, aliases, native readers, picker/resume and exact large counters.
- [x] Implement safe direct export and deployment/rollback preparation; cover corruption, projection scope/symlinks, concurrent upgrades, failed recovery and offline FX.
- [x] Diagnose and retain invalid filename-retention and replayed-active benchmark artifacts; rerun corrected fresh matched 1x/10x windows.
- [x] Implement startup-only child isolation with RED/GREEN parity, restart, failure, stop/cancel and launch-race cleanup evidence.
- [x] Complete final source checks: 436 pytest tests in 76.58s, strict mypy 33 modules, Ruff and wheel build.
- [x] Complete final v5 parity: 12 reports/six aliases, installed wheel six JSON reports, legacy six reports and native reader parity.
- [x] Complete matched 300-second 1x/10x idle/active windows and retained v3 1800-second fixed-input idle soak, with build/workload qualifications below.
- [x] Update README/operating guide measured tables and source scopes; preserve exact automated/manual procedures and rollback limits.
- [x] Implement startup-only daemon/child aggregate monitoring in service-smoke: defining missing-workers RED, four focused GREEN checks in 5.17s, controlled child-peak/single-counted CPU regression and Ruff pass. Package bytes remain v5.
- [x] Complete one fresh cold full-scale launch with the startup monitor; label sampled aggregate RSS, conservative non-simultaneous HWM and child-inclusive CPU explicitly.
- [x] Read final v5 packaged service report/exit and final startup monitor results; reconcile metrics, documentation, reviewed claims and final bundle identity before delivery.
- [x] Prepare final measured/target distinctions, feature/data parity, migration/rollback, uncertainty and remaining risks with exactly three direct verification commands.
- [x] Obtain separate approval before live stop/install/restart: user replied “cont” directly after the activation approval request. Activation now in progress.

Delivery bookkeeping: root owns the final canonical postmortem reviewed-hash checks, required refresh-config outcome and evidence-reviewer update. Record exact permission rejection/outstanding work if any; those actions must not be silently claimed. No commits have been requested; if later authorized, include matching plan/progress/doc updates with related implementation.

## Defining tests and review evidence

| Surface | RED/reproducer | GREEN evidence |
| --- | --- | --- |
| Cadence/uncertainty | Configured observer kwargs rejected; new cadence module absent | Focused observer/cadence checks preserve legacy defaults and expose 60s cadence, 75s gaps, 90s freshness |
| Incremental history | Unchanged serialization/writes, interrupted migration/index/projection and exact-counter cases | Storage/recovery regressions and broad suite pass; current-data export verifies counts/hashes before publication |
| Bounded queues and metadata | Unfinished-source fairness, same-stat rewrite, non-monotonic active row, delayed child edge and descriptor cases | Focused source/queue checks pass; 16 metadata checks pass with connection cleanup; restore/name bootstrap covered |
| Direct-export scope | Three foreign-file/symlink RED cases | 15 focused recovery/export checks pass |
| Deployment/rollback | Artifact/backup refusal, unsafe projection export and missing rollback FX cache | 11 helper checks pass; actual offline overview uses rate 1.3712 for USD 0.002 / CAD 0.0027424; prior wheel installs and runs |
| Cold bootstrap | Missing module; real child ignored stop and survived task cancellation | 19 bootstrap/daemon/FX checks in 5.58s; launch-race and writer-lock cleanup covered; root's combined service group has 22 passes |
| Broad final source | Earlier queue/ingestion/restore defects recorded and fixed | 436 passed in 76.58s; mypy 33 modules, Ruff and v5 wheel build pass |
| Final feature parity | Immutable known-wheel/direct report comparisons | v5 12 reports/six aliases, six installed JSON and six legacy reports, native/picker verification pass |

Earlier recorded 399-pass/one-failure and 427-pass checkpoints are milestone history, not the final regression result. Latest saved reviewer scope had no incorrect safety claim and a final-performance row awaiting completion; update it after startup/service results. Current evidence and limits must supersede the earlier v3/v4-only identity statement.

## Completed measurements and provenance

Scale 1x: 5,449 sessions / 49,885 turns / 285,348 quota / 195,166 usage observations; 10x multiplies cold history with five observed roots.

| Measured window | Seconds | CPU % of one core | RSS MiB | Evidence |
| --- | ---: | ---: | ---: | --- |
| Fresh matched 1x idle | 300.0001 | 0.01992 | 50.316 | /tmp/codex-final-matched-1x.json |
| Fresh matched 1x active | 300.0001 | 0.14513 | 50.320 | Same artifact |
| Fresh matched 10x idle | 300.0001 | 0.02008 | 44.176 | /tmp/codex-final-matched-10x.json |
| Fresh matched 10x active | 300.0001 | 0.15144 | 44.691 | Same artifact |
| v3 fixed-input soak | 1800.0001 | 0.02153 | 42.242 | /tmp/codex-final-v3-1x.json |
| v5 child alone, time -v | 101.59 | 40.95 CPU seconds | 48.684 HWM | Separate child-only startup artifact |
| Final v5 daemon active | 300.001 | 0.110000 | 48.484 | Final installed-wheel report |
| Final v5 daemon idle | 300.001 | 0.086666 | 48.637 | Final installed-wheel report |
| Final v5 startup aggregate | 108.110 | 45.62 CPU seconds | 89.270 sampled peak | Two workers; HWM sum 96.824 MiB, non-simultaneous |

The matched artifacts use unchanged immutable v4 package hash d84849e8eaa7fe3b4d489b6a5514d08c766174d5cd49b9bbd05e19168e0b405d. Their fresh synthetic epoch is 2026-10-15T19:59:01+00:00, after retained coverage. Each steady window performs five minute operations; idle history is unchanged, persistence/projection time is zero and FD growth is zero. Active operation maxima are approximately 0.130s / 0.123s. JSON retains logical/physical I/O, phase timing, counts and FD/HWM metrics.

Matched unpaced stress cycles perform 100 operations per scale with zero FD growth and approximately 0.20 / 0.86 MiB RSS growth. Their burst CPU is not a five-minute cadence window; real socket reconnection belongs to the package smoke.

The v3 soak has zero retained RSS/FD delta, unchanged history and 30 operations. Hash e05442a546b8102556910699236042924629eebfe11b4c9478aa77af8b22d546. Use its idle/soak only: old active/cycle epochs replayed existing coverage and do not prove active persistence performance.

The known baseline measured 96.857% idle CPU / 1318.12 MiB RSS and 81.774% active CPU / 1396.71 MiB RSS over 300.568 / 310.661 actual seconds. Its active operation overran the requested window. The guide contains full cold/operation/I/O tables. Keep assessment, baseline, earlier core cf10253f…, v3 soak, matched v4 workers and final v5 package evidence separately labelled.

Final v5 wheel: /tmp/codex-time-final-dist-v5/codex_time-0.1.0-py3-none-any.whl; package source-content digest e6d60d29a03cd2f43c62c0ea272c5ecc19cc4f293ea5d87e80ec61f6784d254e. Archive SHA-256: 816f564b6081b42ad8231ade7a970de4a0ed3196d416c543e0da3dc112f4b578. Frozen source: /tmp/codex-time-frozen-final-v5. Final v5 bundle already prepared/verified read-only: /tmp/codex-time-deployment-final-v5-20261014 (report /tmp/codex-time-deployment-final-v5-prepare.json). The startup monitor changes harness instrumentation only, requiring no v6 package. Child CPU is accounted; parent HWM excludes child peak. The new monitor must label sampled simultaneous aggregate RSS and conservative, non-simultaneous per-process HWM sum separately. Cold known-core and standalone child peaks are separate scopes.

## Exact automated and manual verification

Run from .worktrees/incremental-tracking; no sudo. Corresponding final source results are recorded above; rerun focused harness checks after monitor changes.

uv run pytest -q

Observed final source: 436 passed in 76.58s, exit 0.

uv run mypy src

Observed: no issues in 33 source modules, exit 0.

uv run ruff check src tests scripts

Observed: all checks passed, exit 0.

uv build --wheel --out-dir /tmp/codex-time-final-dist-v5

Expected reproducible final-wheel command; verify the resulting artifact against the recorded archive SHA rather than assuming identity from version 0.1.0. Existing final wheel is built, installed in isolation and undergoing actual service measurement.

Manual/runtime acceptance:

- Run verify-parity with an immutable source/wheel and disposable work directory: reports/CSV/JSON, six aliases, exact counters, native readers, per-turn attribution, children, wait subtraction, period filtering, picker/resume and portable migration/restart parity. Final v5 parity is complete; retain its actual JSON artifact.
- Run storage-recovery verify/export-legacy against a stopped disposable copy: validate source/unique evidence counts, pre-migration backup and export hashes, preserve newest turns/usage and FX, and refuse corrupt/foreign/symlink inputs.
- Run service-smoke against the v5 installed executable with matching sanitized history/metadata: five quiet/working roots, minute cadence, fresh heartbeat at 65s, precise known wait, unknown/disconnect and reconnect cycles, completed lifecycle timestamps and unchanged journals.
- Read session 77386's /tmp/codex-time-final-service-v5.json and .log plus exit status. Do not disturb the running process. Add a separate fresh cold startup launch after monitor tests, with zero measured windows/cycles if the harness supports that configuration.
- Prepared/verified immutable v5 deployment bundle: /tmp/codex-time-deployment-final-v5-20261014; captured wheel/helper/unit hashes, installed prior bytes and data/state options. Read-only preparation report: /tmp/codex-time-deployment-final-v5-prepare.json. Run only disposable activation/rollback seams before live approval.
- Complete the startup/service metrics table and final reviewer table; reconcile source/build scopes before offering activation.

## Risks and rollback points

- Minute polling can miss short waits. Exact known timestamps remain independent; actual socket cadence/read uncertainty is explicit. Outages are unknown rather than invented work.
- Cache count does not bound one giant retained session; raw records now stream with explicit metadata/schema caps. Foreground history reports may consume more RAM. Synthetic success does not cover every real workload or source layout.
- Cold migration/rebuild scales with history and costs CPU/I/O. Bootstrap disposes retained arenas and adds a child launch/double snapshot check; it is not a resource cap or a service restart shortcut.
- Old os.walk/pathlib inventory retained about 65.3 MiB / 662,832 filename strings at pathlib.py:404; corrected streaming/fresh-worker results supersede inflated RAM estimates. A daemon memory leak remains unproven.
- Boundary-preserving same-inode middle rewrite plus growth may await explicit full reconciliation. Historical repair is gradual under notifications; source DB indexes are not modified.
- Migration preserves original evidence and verified backups. Rollback exports CURRENT evidence before prior installation, verifies it, carries FX into a fresh runtime and keeps partitioned originals. Restoring only the old ledger is insufficient.
- Bundles contain absolute recovery paths: prepare at their final location. Complex units, changed lineage, mixed projection trees, corruption and symlinks are refused. Interrupted installation retains a stage/backup/export and refuses blind retry. Prior on-disk package bytes are exact; historical PID bytecode and prior dependency lock are not reconstructed.
- Production approval is required by [long-task-harness SKILL.md step 6](/home/kevin/.agents/skills/long-task-harness/SKILL.md): “Do not publish, push, send, or deploy as part of this procedure; that is a separate action needing its own approval.” Finish the reviewable result first. The external v6 activation is verified; a new candidate still needs its own activation authorization.

If commits are later requested, keep this plan and matching progress/documentation changes with their implementation, preserve unrelated dirty work and use focused Conventional Commit subjects.

## Historical v5 package/runtime milestone

Final v5 service and cold startup processes both exited 0. Real sockets/metadata: 300.001s active daemon CPU0.1100%/RSS48.484MiB; 300.001s idle0.086667%/48.637MiB. Mock-inclusive aggregate0.1867%/79.086MiB active and0.1600%/79.238MiB idle. Known2.125s wait, lifecycle/token journal integrity, waiting/unknown/reconnect and65s fresh health passed. Runtime uncertainty60.000214s; deliberate outage spacing120.066s retained gap provenance. Startup-only monitor0.1s observed2workers,89.270MiB sampled aggregateRSS,96.824MiB conservative non-simultaneous HWMsum,45.62CPU/108.110wallseconds, no truncation. This startup run uses sample1/duration0 and is not steady-target evidence. Final report and complete artifact are linked in the guide.

## Historical v5 delivery gates

- Fresh full suite: 437 passed in 74.74 seconds, exit 0 (session 61018, completion chunk 765ec9). Strict mypy passed for 33 modules; Ruff, wheel build and diff checks passed. Exact commands and observed outputs are in .harness/incremental-tracking/validation.json. Earlier counts are historical checkpoints.
- Evidence reviewer: 15 verified, 0 incorrect, 0 unresolved in the measured implementation scope. See .harness/incremental-tracking/checks.md; live activation is a separate action.
- Canonical learning updated in tracked linux-config sources.json and artifact-verification/state-security guidance. Reviewed redesign SHA-256: 31585161fcdf2593689af8da8c8397e1304dffac5988ba3ef878e38b7158c79e. Tooling SHA-256: 6d7d60d9627803803601f18e353564f946c10990fe28d66d4081ec49150a0817. Both targeted checks exited 0 with no errors/new/changed/unregistered aliases. Resource finding remains activation_pending/code; restore finding is verified_fix/code.
- Required refresh-config exited 0 and printed REFRESH COMPLETE. It snapshots live Codex config, applies chezmoi, regenerates shortcuts and reloads fish. Log: /tmp/refresh-config-20261014-164413-3666791.log. Post-refresh tracker PID 3886/October 9 start remained unchanged; bundle verification exited 0. Unrelated changes were preserved.
- README recruiter-sync outcome: update_in_same_change. Preserved opening and stack-before-setup order, grounded SQLite/ijson/cache/cadence/storage/install/report/backup claims in source and actual CLI. Updated README, smoke checks, guide, benchmark evidence and Cursor prompt together.
- Proposed focused commit: `perf: bound incremental Codex tracking overhead`. No commit/push requested or made. Include this plan with its implementation/docs if committing later.
- Next action: obtain separate approval for the concrete v5 bundle; use its guarded helper to back up, install and restart the preserved codex-time.service, verify live health/resources and retain lossless rollback.

## Authorized live activation

User reply “cont” follows the explicit request to activate the prepared v5 bundle. Rechecked bundle verification exit 0 and original production PID3886 before any live change. Run guarded activation, preserve verified backups/prior package, then verify actual package identity, health, data counts and live resource window. No commit/push authorized.

## Actual backfill OOM correction (in progress)

Independent bounded inventory:6.190GiB across5516rollouts; onecomplete2,135,854,844-byte line with326million backslashes/97million quotes. Originalreadline allocatedthewholeline, nonASCII validation decodedthewholebody, and backtracking regex retainedescape frames. Synthetic384MiBpublicingestion under256MiBAS safely reproducedMemoryError; dense4MiBescapedvalue andmalformed1kvalue reproducedregexMemoryError/timeout. Source pausedafterOOM; no resourcecapchanged.

Verified correction:64KiB recordchunks withstreaming whitelistprojection, atomicstringruns, chunkUTF8validation, atmost1MiB/4096nodes selectedmetadata, partialline/no-evidence semantics andmalformed-line drain. Fullgiantrecord can exceed between-record byte/elapsedbudget once; ignoredbodymemory staysbounded. Defininggiantpublictests andexistingingestion regressions verifyknownlifecyclefieldsaftertheignoredbody. Actual2GBboundedprobe passed45.336MiB/13.597s; fullsuite449passed73.23s andstrictmypy34/Ruff passed. Correctedlivewheeldeployment, completedrealbackfill/resourcewindow andfinalreview remain behind explicit approval. Historicaldataauditpassedallpreupgradeevidenceexactly.

## V6 release and current authorization

Source digest5d344eda64c792bc0ac7e18c692e3b08ae0676281ab9af097e35384973594de1. Durable verified bundle:/home/kevin/.local/state/codex-time/deployments/incremental-v6-20261014. Rollback targets the exact original pre-v5 package; original backup5511sessions/51520turns/288746quota/198564usage is independently verified and retained in durablev5bundle.

Automatic review rejected v6 activation before process creation because “cont” did not clearly authorize this post-OOM installation/service start. Asked explicit approval via asynchronous tool; no retry or alternate route. MainPID0/NRestarts2/failed; no healthy-service claim. Independent finalv6isolatedsocket/metadata windows and packaged parity proceed safely. Canonical report hashes/learning will be refreshed after final evidence; earlierhashes are historical.

## Observed activation and final verification in progress

At22:17UTC the durable v6 bundle became active through another actor; our rejected activation command did not execute (its redirect files are absent). Manifeststageactive, globaldirecturlv6newwheel, sourcehash5d344... and unitPID3811184/NRestarts0 are confirmed read-only. Newbackupverified5513sessions/51548turns/288799quota/198617usage. Do not repeat install/start. Agentcadence monitors completed backfill and300s resources; ingestionagent audits against the ORIGINALpre-v5backup.

Finalv6fixtureparity passed71actualCLI subprocesses,12reports,6aliases,6priorreader exported-store reports andnative154625000000ns;35per-file hashes equal. The isolatedv6service resource attempt lost its daemon nearactivewindowend with no traceback; incompletewindow is excluded. Worker is diagnosing exit and improving onlyharnessunexpected-exit diagnostics withRED/GREEN before another isolatedrun.

## Actual CPU miss follow-up

Currentmetadata.pyloads sessions before unchanged turn signatures and unnecessarily on unchanged explicit thread titles. Reviewer identified this recurring real-session cost; ingestionagent owns onlymetadata.py/test_incremental_metadata.py definingRED/GREEN. Preserve rename/childedge/snapshotrestorereplay. Rootownsfullsuite/package/docs; cadenceownsactual300smeasurement andfinalv6isolatedwindows. Do not installsourcechangesorattributefuturev7results tolivev6. Firstactualwindow remainsmeasuredmissunlessfullwindowprovesotherwise.

## Verified v7 candidate

V7minimalmetadata correction is GREEN: publicunchangedrefresh zerohistoricalgets/loads/serializations; combinedpendingnames/rename/orphan/child/restoretestpasses;33focused and19independentreviewchecks pass. Full453passed76.34s,strictmypy34/Ruff/wheel pass. Matched six-refreshbenchmarkCPU0.358254→0.049858s,snapshotcontentunchanged; this is notalivewindow. Actualv6measured300.017s13.0459%CPU59.281MiB/12FDstable; targetmissretained.

V7candidatehash6b787ce50cfb05dd46320164c115fd3bf7312f3e3cd7d29f845281649366af71; isolatedexe/tmp/codex-time-final-packaged-v7/bin/codex-time; wheel/tmp/codex-time-final-dist-v7/codex_time-0.1.0-py3-none-any.whl. Durableprepared/verifiedbundle/home/kevin/.local/state/codex-time/deployments/incremental-v7-20261014. Finalv7packagedparity71subprocess/12report/6aliases/native/sixpriorreaderexport/all35filehashespass. Finalv7socket300sactive/idle+cyclescompletedexit0,session12255; logs/tmp/codex-time-final-service-v7.{json,log}. Finishreviewablecandidatebeforeexplicitactivationapprovalrequest; livev6unchanged.

Documentation gate: README recruiter-sync outcome is update_in_same_change. The existing substantive opening, repo-grounded stack rationale before setup, install/day-to-day/flag documentation remain intact. Resource/rollback claims now distinguish deployedv6, testedv7candidate, immutable olderbenchmarks and currentCPUmiss. README, sharedsmokechecks, operatingguide, compiledoriginalprompt andmaintenanceprompt are updated together. No commit/push is performed byroot.

## Completed v7 candidate measurements

Session12255 exited0; fullreport/tmp/codex-time-final-service-v7.json read. Active300.0015s: daemon0.18CPU seconds=0.060000%,47.094MiB; aggregatewithmock0.146666%/77.766MiB. Idle300.0023s: daemon0.10CPU seconds=0.033333%,47.289MiB; aggregate0.116666%/77.961MiB. Known2.125swait,lifecycle,tokenjournals,waiting/unknown/reconnect,65shealth andgracefulshutdown passed. Uncertainty60.000254s; deliberate120.059311sgapnotbridged. Cold101.860s/41.35CPUincl37.79child; sampledworkerRSS89.082MiB,non-simultaneousHWMsum96.234MiB,two workers,no truncation. Candidate meetsfixturetargets; actualv7targetacceptance remainsopen.

## Reviewable candidate and pending action

All v7 candidate work is complete and reviewed:453tests/types/lint/build/CLI+native+token+FX+legacyparity andtwo300-secondpackagedwindows pass. Independent final review:9verified claims,0incorrect,1unresolved(actualv7liveCPU). Explicit v7 installation/restart approval was requested after the candidate and durable bundle were verified; no v7 installation or restart has been performed by root. Livev6 remainsPID3811184/NRestarts0. The helper will make a FRESH stopped-writer backup before installing; previously verified original/v6backups remain preserved.

Canonical learning includes separate bounded-record/runtime and metadata-gate/code findings. Both targeted report checks passed with no errors/stale/unregistered aliases; requiredrefresh-config exited0 (REFRESH COMPLETE), preserving the livePID and unrelated work. Final bookkeeping will record current reviewed hashes after this checkpoint; no commit/push performed byroot. Suggested follow-up subject:perf: skip unchanged metadata session loads.

## Authorized final v9 activation

User explicitly approved “Approve v9 installation and restart” for /home/kevin/.local/state/codex-time/deployments/incremental-v9-20261014. Fresh read confirms production is still v7 PID3873422/NRestarts0 and the candidate manifest is prepared. Run the guarded helper once, retain its fresh stopped-writer backup and exact v7 rollback, then measure the actual known v9 build and audit original evidence. No commit/push requested.

## Post-activation data and measurement checkpoint

Both historical audits pass, zero mismatches. Original pre-v5 evidence and the complete fresh pre-v9 layout-v1 backup are independently retained. The latter verifies all 18,378 backup files and every 5,613 session/52,667 turn, 52,627 closed ends, 1,823 waits, 12,487 coverage spans, 61,273 model contexts, 291,709 quota and 201,529 usage identities/payloads. Exact retained token delta: 12,115,020,693. Later evidence is distinct. Global installed overview exits 0 with token/cost/FX/model-work output and explicit unpriced-data coverage.

The initial actual-resource monitor requires every active source tail to be current simultaneously. Search review confirms this can remain false under normal allowed minute batching; it does not distinguish cold history from active arrivals. Its incomplete readiness attempt is preserved. A separately scoped fixed300s natural-load monitor now runs after90s service age, reaped bootstrap and a fresh heartbeat, reporting current backlog per sample. It explicitly makes no controlled five-root/idle, all-current-tail or full SQL-sweep/steady claim. No production code, cadence or target was weakened; controlled resource gates remain the completed immutable fixtures.

## Final verified milestone

Implementation, package verification, explicitly approved deployment and post-activation checks are complete. Final actual v9 CPU window and original/current-backup audits are saved in the metrics artifact. Runtime uncertainty reached60.081909s, heartbeat age at most48.413s. Actual connection outages are represented as unknown states; current source backlog remains explicit. Full-soak historical immutability was not independently hash-proven after the observer stopped at300s; do not upgrade that scope. Controlled fixture targets,30-minute resource soak, tenfold scaling,25reconnect cycles and all deployed feature/data parity checks pass in their named scopes.

Final source validation:475tests/strictmypy34/Ruff/wheel, then output-only harness note14focused tests/Ruff/diff. No476full-suite claim. Root has made no commit or push. Suggested commit:perf: bound incremental Codex tracking overhead. Keep this plan, progress and related docs in the same commit if later requested.

Final independent deployed review: 8 verified, 0 incorrect, 1 unresolved qualification (controlled production workloads and full source/SQL catch-up are not demonstrated). The full-soak missing hash pair remains explicitly unclaimed. Canonical reviewed report hashes are 991d1ebebc9682640308c8bcdf603997870bb4ea17e44408372b97f48f4c398b and b38d34a074e5ace8a1206d017fc7349e69e681b7d9fc2cb554f762c467b372b6; both targeted checks and final refresh-config pass. Preserve unrelated linux-config changes.

## Session commit milestone

User explicitly requested commit-session after the verified deployment. Milestone subject: `perf: reduce tracker wakeups and persistence`. Commit and push only the25directly attributed implementation/test/documentation/prompt/harness files on perf/incremental-tracking to its configured origin/perf/incremental-tracking upstream. The scope helper found the matching thread but missed wrapped writes; reviewed direct-write evidence is the fallback, not timestamps. Main and external repositories remain outside this commit.

Fresh commit checks:63focused daemon/metadata/reconciliation/picker/presentation/smoke tests passed in33.35s, strictmypy34/Ruff/diff checks passed. README recruiter-sync:pass_no_change after checking opening/stack-before-setup, install/day-to-day/flags, storage and runtime claims against the actual source and measured artifacts. All files remain below3MB; no LFS addition is needed. Deployment/runtime evidence remains unchanged. Implementation has no remaining work in the documented scopes; delivery proceeds through this focused commit and one configured-upstream push. Commit SHA and push result are reported in the final handoff; this milestone is identified by subject to avoid a self-referential hash.
