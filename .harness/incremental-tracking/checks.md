# Evidence review: incremental Codex tracking

This record preserves independent review tables and named build scopes. Final isolated checks, approved deployment, actual natural-load CPU window and both historical audits pass. Controlled production/catch-up and interrupted-observer limits remain visible.

## Final deployed v9 review

Independent final review: **8 verified, 0 incorrect, 1 unresolved**. Source, runtime and raw evidence were independently read after the deployment wording repairs.

| Claim | Verdict | Primary evidence |
| --- | --- | --- |
| Actual v9 five-minute observation completed | Verified | live_resource_window_v9: 300.130819s, 2.15 CPU seconds, 0.716354% |
| RSS/FD/process/package remained stable | Verified | 50.695 to 50.895 MiB, FD12 to FD12, one worker; PID4027405/start44222560/digestfc3a…/NRestarts0 equal |
| Actual uncertainty/freshness are accurate | Verified | Max uncertainty60.081909s, heartbeat age48.413036s |
| Approved activation/current-backup preservation pass | Verified | Active bundle; global installed-v9 audit, all18378hashes, exact pre-v9 evidence retained |
| Original pre-v5 evidence survives | Verified | Original-baseline audit, zero mismatches; matching worktree models |
| Natural workload/catch-up limits stay explicit | Verified | Per-sample backlog and unknown states; steady_state_claim=false |
| Controlled fixtures and production observations stay separate | Verified | README, guide, plan and metrics named build scopes |
| Historical/current deployment wording is correct | Verified | V7 chapter explicitly historical; preparation-time statements qualified; v9 completed milestone |
| Controlled production idle/five-root performance and complete source/SQL catch-up are established | Unresolved; not claimed | Actual natural window establishes neither; controlled fixture targets pass separately |

The missing independent full-soak history hash pair is an additional explicit evidence limit, not an immutable-history claim. No incorrect current claim remains. Earlier reviews below retain their checkpoint scopes.

## Earlier v9 package and event review

Independent reviewer: **9 verified, 0 incorrect, 1 unresolved**. Exact raw artifacts are retained in the metrics JSON.

| Claim | Verdict | Evidence and scope |
| --- | --- | --- |
| Actual v7 CPU remains a measured miss | Verified | 300.018 seconds, 24.7118% CPU / 51.035 MiB; not controlled five-root/idle |
| Event-bearing v8 resource improvement | Verified | Same fixture/rate, separate 300-second streams: v7 40.3398% → v8 0.4633% daemon CPU; 1195/1193 messages |
| Complete event tail cost is separate | Verified | All five tails, 54.186 seconds / 0.04 daemon CPU seconds before idle |
| Tenfold steady resources do not scale linearly | Verified | 0.5100% active / 0.0367% idle / 52.520 MiB; cold peak 161.441 MiB explicitly separate |
| Real reconnect retention | Verified | 25 measured cycles, 150 root turns, exact 294848060 microseconds, RSS +1.238 MiB / FD delta 0 |
| Final v9 regressions/package parity | Verified | 475 tests / 97.56 seconds; 71 CLI subprocesses, 12 reports, six aliases, native and current-data legacy parity |
| Final v9 PTY and short socket behavior | Verified | 0.863-second automatic rename; search/details/fake resume/terminal restoration; short functional socket pass |
| V8 measured versus v9 inferred background scope | Verified | All other storage AST and all other background package files equal; v9 changes foreground only |
| Concrete bundle/recovery gate | Verified | V9 prepare/verify pass; exact v7 rollback captured; production unchanged |
| All production gates complete | Unresolved | Named v9 activation approval, actual known-build CPU window and post-activation audit pending |

## Final soak review

Independent reviewer: **6 verified, 0 incorrect, 2 unresolved**. Root clarified the reviewed RSS baseline precision; no new run or metric substitution.

| Claim | Verdict | Evidence and scope |
| --- | --- | --- |
| Full packaged v8 fixed-input soak completed | Verified | 1800.001 seconds, exit 0, exact saved/raw report match |
| Idle resource targets met | Verified | 0.03056% CPU, final RSS 47.949 MiB, FD12 / delta0; 46.523 MiB is post-startup, not recorded idle-start RSS |
| Wait/lifecycle/token evidence retained | Verified | All evidence booleans pass; reconnect intentionally skipped |
| Independent observer only partial | Verified | 300.010726 seconds and initial hashes; no final pair; exact termination cause unknown |
| Full-soak historical files unchanged | Unresolved | No final independent hash pair; counters cannot identify historical writes. No such claim is made. |
| Build/test execution scopes distinct | Verified | Measured v8, source-equivalent v9; full475 before output-only final14 harness checks |
| Prepared candidate is not production acceptance | Verified | Named v9 approval remains separate; root did not install/restart |
| Actual v9 CPU and post-activation parity complete | Unresolved | Await authorization and fresh actual measurements/audit |

## Historical v7 review

The following table retains the previous review; its final/current wording belongs to that historical checkpoint. Use the v9/soak tables above for the live task state.

| Claim | Verdict | Primary evidence and scope |
| --- | --- | --- |
| Deployed reports/features and exact package files preserved | Verified | V7:71actualCLI subprocesses,12reports,6aliases,sixprior-readerexportreports; all35packagefiles equal source6b787ce5… |
| Historical evidence/index state is disk-backed and bounded | Verified | Source/storage regressions; eight-sessioncache/4MiBSQLite; prior matched1x/10x steadyRAM50.32/44.69MiB |
| Fully reconciled unchanged input avoids historical writes | Verified within prior build scope | Matchedcoreidle andv3 1800ssoak: historyunchanged,persistence/projectionzero,RSS/FDdelta0; notav7soakclaim |
| Giant ignored records stream safely without whole-body retention | Verified | Actual2,135,854,844bytes consumed45.336MiB/13.597s/147selectedbytes under256MiBAS; independent2500differentialchunkcases plus publicresource/partial/malformedtests |
| Actual v6 backfill and historical retention pass | Verified |5525sourceinodes/completeboundaries consumed,namescomplete; original5511sessions/51520turns/1819waits/allquota+usage/model+coverage+exactcounters retained,zero mismatches; concurrentwriter caveat |
| Migration/interruption/current-data legacy recovery retains tested evidence | Verified | DefiningRED/GREEN storage/recovery/deployment regressions; SHA/countverifiedbackups; sixoldreaderreports/native154625000000ns andofflineFX match; no productionrollbackclaim |
| Timing precision and actual coarse uncertainty are exposed | Verified | Packagedknownwait2.125s/lifecycle exact;65shealthfresh;60.000281s fixtureuncertainty,livev6snapshot60.072357s; intentional120.0678sgapnotbridged |
| Final automated/build validation passes | Verified | Rawlog453passed76.34s; strictmypy34,Ruff,wheel; validation.json |
| V7 metadata gates avoid no-op model work while preserving replay | Verified in code/operation benchmark | PublicRED152gets/129loads/258serializations→allzero; matchedsixrefreshCPU0.358254→0.049858s; independent19tests cover names/orphans/child/restore |
| Actual v6 CPU exceeds target despite bounded RAM | Verified measured miss |300.017s,13.0459%CPU/59.281MiB/12FD; oneworking/fouridleroots pluschildren; stableRAM/FD/PID; SQLitefirstsweepunproven, recurringcostindependentlyconfirmed |
| Final v7 packaged active/idle and socket evidence pass | Verified | session12255 exit0; exact6b787… package,300sactive0.0600%/47.094MiB,idle0.0333%/47.289MiB; allwait/lifecycle/journal/reconnect/health checks pass |
| Corrected v7 live CPU/resource acceptance passes | Open | Measured v7 miss:300.018s/24.7118%CPU/51.035MiB, stable identity; actual historical audit passes, zero mismatches. CPU gate remains unmet |
| Documentation accurately separates targets/builds/current deployment | Verified after repairs | Reviewer re-read guide/README/plan/artifactscope: historicalv3/v4/v5scopes,v6mixedmiss,v7candidate,firstsweepuncertainty andnonidenticalv7soakall explicit |

Current consolidation:12 verified claims,1 open acceptance gate. The final independent10-claim review reports9verified,0incorrect,1unresolved, with only actualv7liveCPU open. Independent metadata review found no code/data-regression blocker. Source/name readiness does not prove a historicalSQLite full sweep; cursor0 is ambiguous, and independentcursors need tracked complete traversal against stableidentity/highwater.

The earlier15-claim isolatedv5 review and subsequentstreaming/metadata reviews are retained through the plan/postmortem/evidence artifact. Productionv5OOM invalidated its readiness inference. The firstisolatedv6exit lost exactstatus and remains a forensiclimit; its incompletewindow isexcluded. A freshv6repeatpassed300sactive/idle/cycles; strictchild-exit diagnostics nowretaincode/signal/logpath.

Persistent primary evidence:[metrics](../../docs/benchmarks/2026-10-14-incremental-tracking.json),[automated validation](validation.json),[operating guide](../../docs/incremental-tracking.md). No currentreviewclaim treats a restart, resourcecap,historydeletion ordownsampling as optimization.

## V7 live follow-up review

Independent reviewer verified the24.7118%actualCPU miss and rejected claims that every flush serializes all cached sessions or that observation runs on every wake. Frequent events can trigger complete affected-session persistence; copied-store profiling confirms amplification, but exclusive live attribution remains unresolved. The bounded first-event deadline is a testable design, not a verified remedy. Current review:3verified,2incorrect claims corrected above,1unresolved attribution. Actual CPU acceptance remains unmet.
