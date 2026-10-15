# Incremental tracking final handoff

Updated October 15, 2026 UTC. Implementation, approved deployment and the defined runtime checks are complete. This handoff preserves exact build scopes and remaining evidence limits so future work can resume without repeating installations or long benchmarks.

## Session commit delivery

User now requests commit-session; earlier no-commit statements are historical. All25eligible files are directly attributable to parent/delegated work in this logical session. The helper cannot detect wrapped writes, so its documented direct-write fallback is used. Scope thread:01a13b8f-7fe2-7a82-bd16-14b6dd49ff1e. Milestone subject:perf: reduce tracker wakeups and persistence; branch/upstream perf/incremental-tracking→origin/perf/incremental-tracking. Preserve main and external repositories. Fresh checks:63focused tests/strictmypy34/Ruff/diff pass; README recruiter gate pass_no_change. Implementation is verified; next delivery step is the focused commit and one push, with result reported in final output. Relevant plan and docs are included together.

## Current state

- Worktree: /home/kevin/coding/track-codex-sessions/.worktrees/incremental-tracking, branch perf/incremental-tracking. Preserve main, token-cost-reporting, external commit33ce9ed and unrelated linux-config changes. No root commit or push was requested/performed.
- User explicitly approved the exact v9 installation/restart after earlier named v6/v7 replies. Root ran the guarded v9 activation once; exit0, stage active. Do not reinstall/restart this completed deployment.
- Global executable: /home/kevin/.local/bin/codex-time. Service PID4027405/startticks44222560, started2026-10-15T00:06:40+00:00, NRestarts0.
- Canonical source/package digest: fc3aabd983bc36ef5296199f020ae111948635a9b1fb338de5978dbff0a22c82, all35files equal. Wheel archive3fd036a75c0ef4752a1e066bb66da3cbafdeb3bed4911354b3063a6a5f51941a.
- Durable active bundle: /home/kevin/.local/state/codex-time/deployments/incremental-v9-20261014. Fresh backup pre-activation-1792022769876499660 verifies5613sessions/52667turns/291709quota/201529usage and18378files. Exact installed-v7 rollback wheel SHA80ed4a605ced9e0d44311023477d402e0ea90b40c85b71a7b620b1db67144152.
- Rollback must export/verify CURRENT evidence and carry FX to a fresh runtime; original partitioned data/backups stay preserved. No production rollback is claimed. Unit and source lineage guards remain active.

## Design and defining fixes

Portable layoutv1 snapshots/original journals are authoritative. Exact dedup/checkpoints/signatures/names/native ownership live in disposable SQLite; eight-session cache/4MiB SQLite and bounded queues/pages/batches keep daemon work incremental. A reaped child isolates cold initialization. Ignored raw records stream in64KiB chunks with bounded metadata; actual2.136GB record was verified under256MiBAS at45.336MiB HWM/13.597s.

V8 corrects level-triggered descriptor spin by self-disarming before wake, clearing before bounded drain/rearm and retaining later notifications during polls. First-event-anchored deadlines coalesce warm persistence without postponement; startup/continuations stay immediate. Defining real-FD/one-shot wake/122-scan RED cases became GREEN. V7 metadata signature gates avoid historical model loads on unchanged input. V9 adds foreground-only generation invalidation and cached picker drawing; storage constructor/all other storage AST and background file bytes equal measuredv8.

## Automated/package verification

- Full final v9 source:475tests in97.56s; strictmypy34/Ruff/diff/wheel pass. Rawlog /tmp/codex-v9-final-pytest.log.
- Subsequent output-only skipped-cycle-note correction:14service-smoke checks in28.24s/Ruff/diff pass; package bytes unchanged. Do not claim476full-suite tests.
- /tmp/codex-time-final-parity-v9.json:71actualCLI subprocesses,12reports,6aliases, native154625000000ns, exact9007199254741001counter, six prior-reader current-data legacy reports and migration/restart/export parity pass.
- Token smoke:1320000tokens/USD2.91/CAD3.9285 atFX1.35; period/child/auto-review/replay/read-only pass.
- /tmp/codex-time-final-picker-v9.json:0.863-second automatic rename refresh without keypress, search/details/stable-ID fake resume/cwd/home/cooked terminal/terminal restoration/quit pass; same package before/after.
- /tmp/codex-time-final-service-v9-short.json:five-second functional socket/event run, all five tails and exact lifecycle/wait/token/reconnect evidence pass; not CPU acceptance.

## Resource evidence

All percentages are one CPU core. Targets are provisional idle0.5%/active2%/steadyRSS128MiB.

| Scope | CPU | RSS | Evidence |
| --- | --- | --- | --- |
| Known baseline1x idle | 96.857% |1318.125MiB | Retained original benchmark |
| V7 matched event control,300s |40.3398% |47.219MiB | /tmp/codex-time-final-service-v7-events.json |
| V8 event fixture1x,300s |0.4633% active/0.0300% idle |47.176/47.387MiB | /tmp/codex-time-final-service-v8-events.json |
| V8 event fixture10x,300s each |0.5100% active/0.0367% idle |52.520MiB | /tmp/codex-time-final-service-v8-10x-events.json |
| V8 fixed-input idle soak1800.001s |0.03056% |47.949MiB final | /tmp/codex-time-final-service-v8-soak.json |
| V9 actual natural window300.130819s |0.716354% |50.695→50.895MiB | /tmp/codex-live-resources-v9-window.json |

Event fixtures use identical sanitized history/rate configuration with independently generated timestamps/counts1195/1193/1197, not byte-identical streams. V8 final tail drains54.186s/.04CPU seconds at1x and17.336s/.05CPU seconds at10x are separate. Active physical writes fell139784192→2433024B in the matched event comparison. Tenfold cold startup took1062.798s/423.66workerCPU seconds, sampled aggregate RSS161.441MiB, conservative non-simultaneousHWMsum174.395MiB; startup is separate and exceeds the steady bound.

The actual v9 window00:12:45–00:17:45UTC retains same PID/start/hash, no restarts, FD12→12 and one worker. Logical read/write76317654/8874478B, physical write11915264B. It contains fouridle/twoworking root snapshots and intermittent sixunknown snapshots, with37children excluded from root timing. Sources5629→5637, indexed5624→5635, unread3–11/final3, two unresolved model-context sources. No full source/SQL catch-up or controlled production idle/five-root claim. Actual uncertainty max60.081909s, heartbeat age max48.413s. Connection outages remain unknown; final health is fresh/diagnosticnull. Natural v7 window24.7118% and v9 window are different workloads, not a controlled pair.

The first v9 all-current-tail barrier attempt was intentionally stopped; its incomplete artifacts remain. Allowed minute batching makes continuously changing tails unsuitable as an initial-backfill equality gate. The separate fixed natural window requires bootstrap reaped/service age>90/fresh heartbeat and reports backlog per sample.

The independent v8 soak observer stopped after300.011s with initial hashes only. No final pair/1790s independent claim/full-soak immutable-history proof. The main daemon resource soak completed1800.001s. Older fully reconciled core unchanged-history results and deterministic idle-write tests stay separate.

Twenty-five measured accelerated real reconnect/open/close cycles after three warmups retain all150rootturns and exact294848060microseconds;29connections/28unknown-recovery transitions, RSS+1.238MiB/FDdelta0/samePID/hash. This checks retention, not minute CPU or unbounded leak absence.

## Data preservation and actual reports

Both /tmp/codex-live-data-parity-v9.json (originalpre-v5 baseline, matching worktree models) and /tmp/codex-live-data-parity-v9-current.json (complete pre-v9 layoutv1, actual installed interpreter) pass with zero mismatches. Current audit verifies every18378backup hash and all5613sessions/52667starts/52627closedends/1823waits/12487coverage spans/61273contexts/291709quota/201529usage identities and payloads. Exact12115020693token delta survives. New evidence and title changes stay distinct. Reads are per-session atomic/journal byte snapshots, not globally atomic live counts.

Actual global overview all --plain exits0 with token/cost/FX/model work and explicit unpriced/missing-evidence notice. Actual fish top spot check shows52120KiBRES and0.0% instantaneousCPU twice; it is not the five-minute measurement. Actual health has fresh heartbeat/PID4027405/60s/inotify, no diagnostic at final runtime check.

## Documentation, review and learning

README, docs/incremental-tracking.md, docs/smoke-tests.md, docs/benchmarks/2026-10-14-incremental-tracking.json, atomic plan and prompts/incremental-tracking.md are updated together. Original compiled prompt is prompts/minimize-codex-tracking-overhead.md. Root README recruiter gate: update_in_same_change, corrected claims while preserving hook and stack-before-setup order.

Final independent review:8verified/0incorrect/1unresolved. Remaining unproven scope is controlled production idle/five-root performance and complete source/SQL catch-up; controlled fixtures pass. Missing full-soak hash pair is explicitly unclaimed. See checks.md for retained review stages.

Canonical learning records final live runtime status and the explicit active-tail readiness workaround. Latest redesign hash991d1ebebc9682640308c8bcdf603997870bb4ea17e44408372b97f48f4c398b; tooling hashb38d34a074e5ace8a1206d017fc7349e69e681b7d9fc2cb554f762c467b372b6. Both targeted checks exit0 with no errors/changed/new/unregistered aliases. Required refresh-config exits0, REFRESH COMPLETE: /tmp/codex-time-required-refresh-v9-live-final.log. Unrelated linux-config work remains preserved.

## Remaining limits and next action

Nominal60s sampling can miss short waits; exact lifecycle/known waits are preserved. Native outages are unknown. Cold startup scales, foreground all-history reports may use more RAM, and eight cached giant sessions are not a byte bound. A general leak absence is not proved. Native terminal/clipboard control is unavailable, so wrapped selection/paste in the Codex UI remains unverified; actual commands ran in fish.

No further implementation or deployment is required for the measured task. Final handoff: show design, scoped before/after table, parity/recovery and limits, link plan/Cursor prompt, and exactly three actual direct verification commands (top, health, overview). No commit/push unless requested; if later committing, include related plans with implementation/docs and preserve unrelated work.
