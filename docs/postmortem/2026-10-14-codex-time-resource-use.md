# Codex Time daemon resource use — October 14, 2026

This investigation checks whether the long-running local tracker is consuming excessive CPU or leaking resources. Capture current process evidence, compare installed code with the checkout, and profile retained history before recommending recovery.

## Symptom and impact

The user reports sustained CPU use since October 9 and provides a screenshot with approximately 1.8 GB process memory. Live inspection confirms PID 3886 started October 9 at 17:16:34 EDT, averaged 96.5% of one CPU core, and accumulated 4 days 15 hours of CPU in approximately 4 days 19 hours elapsed. RSS was 1,913,544 KiB at the initial inspection. The user service reported 2.2 GiB cgroup memory, a 2.4 GiB peak, and about 36 MiB swap. CPU and memory are excessive for background observation; a memory leak is not yet established.

## Status and next steps

Assessment complete; the resource issue remains unresolved. Sustained high CPU is reproduced, and size-dependent serialization overhead is demonstrated. A constant-input memory leak has not been established. No restart, installation, or application source change was performed by this task. Next engineering work should make timing persistence/projections incremental, avoid opening unchanged historical rollout files each poll, and measure memory with a fixed input before changing retention. Preserve durable observations; do not delete history to reduce memory.

## Prior knowledge lookup

- Query: `codex-time high CPU memory`. The first query returned broad matches. A narrower query, `daemon historical retention serialization`, found `local-history-journal-observer-hot-path` in `references/artifact-verification.md`. Its October 6 journal migration reduced an 84.6 MB timing ledger and verified that historical workload, with an explicit future-load limitation. The present installation already has separate journals; repeating that migration is not a remedy for complete timing/session serialization or in-memory history retention. `ext-process-memory-accounting` applies to measurement labels: use current process `/proc` VmRSS/VmHWM, rather than inherited runner high-water metrics. The tracker has direct RSS and systemd measurements.
- Query: `bwrap loopback Failed RTM_NEWADDR`. Matching reference: `references/execution-environments.md#local-sandbox-loopback-approved-route`. Applicable because the initial read failed before shell startup with exactly that error. Reviewed elevated read-only execution succeeded; this is an execution workaround, not a host sandbox repair.

## Investigation tooling failures

The default shell wrapper failed with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` before the first command ran. The approved execution route successfully read instructions and captured Git status. One skill read used a nonexistent Agents-root path; the skill catalog provides its actual plugin-cache location, which was subsequently read successfully. Both failures are unrelated to daemon behavior. No host policy or installed skill copy was modified.

## Protected work

Initial Git status: modified README.md, docs/smoke-tests.md, plans/daily-repo-session-time.md, src/codex_time/day_output.py, tests/test_day_output.py; untracked docs/postmortem/2026-10-06-daily-report-rerun-preflight.md. Preserve all of these changes. Independent source review is read-only.

## Evidence and limits

`ps -eo pid,ppid,lstart,etimes,time,pcpu,pmem,rss,vsz,nlwp,comm,args --sort=-rss` and `systemctl --user status codex-time --no-pager` establish lifetime CPU and current memory. The screenshot CPU figure is an instantaneous sample; it does not contradict lifetime average CPU. Sustained sampling and profiling are outstanding. A short stable-RSS observation cannot rule out slow leakage, and a restart cannot by itself fix historical-work scaling.

## Current activity and dataset

A 15-second `/proc/3886` sample measured 98.1% of one core. Samples at 5/10/15 seconds showed RSS 1,913,856 / 1,913,936 / 1,913,940 KiB and 8 / 9 / 9 open descriptors. Relative to the start, the final sample recorded 247,714,854 logical bytes read and 163,352,704 logical bytes written. These are process I/O counters, not physical disk throughput. This window does not show runaway descriptor growth or sustained monotonic RSS growth beyond allocation fluctuations. `top -b -d 1 -n 2 -p 3886` independently showed 100.0% then 99.0% CPU. `codex-time health --json` returned daemon running, PID 3886, 5,449 sessions and a fresh heartbeat; health does not certify resource efficiency.

A read-only atomic ledger snapshot contained 5,449 sessions, 49,885 turns, at most 859 turns in one session, and 10,320 coverage intervals. Its parse took 3.70 seconds. The quota journal had 285,348 lines (56.2 MiB), and the usage journal had 195,166 lines (149.4 MiB). The approximately 45 MB timing ledger and 6.4 MB checkpoint remain substantial, separately from the historical journals.

## Reproduction and profile

Used the installed package's Python interpreter to load only the durable metadata ledger. Created a temporary Store root, disabled its writes and fingerprint disk access, populated unchanged projection signatures, and set observation offsets to the ends of the lists. Three calls to the real `Store.save(ledger)` took 2.160, 1.942 and 1.700 seconds under cProfile despite unchanged input and zero data writes. Across those calls, full ledger model serialization used 2.934 seconds, JSON encoding 1.449 seconds, and projection comparison 1.096 seconds. This is a lower-surface reproduction of expensive repeated historical processing, not a CPU profile attached to PID 3886; profiling instrumentation also adds overhead.

Installed `daemon.py` calls rollout scan, observer application, Store.save and full runtime checkpoint persistence on every iteration. Its one-second budget leaves a minimum 10 ms delay once that work exceeds the budget. Installed `storage.py` dumps all timing sessions for save comparison and dumps each session again for projection comparison. Existing caches avoid some writes but do not avoid this serialization. Both checkout and installed readers retain all quota objects plus deduplication identities; the installed version also retains usage history and its indexes. This supports historical-data scaling as a cause of resource use, rather than proving abandoned-object leakage.

The independent read-only synthetic review found 100,000 quota objects using approximately 107.6 MiB for models, another 26.7 MiB for ingestion JSON keys and 13.9 MiB for storage tuple keys. These allocation measurements use tracemalloc and are not actual PID RSS attribution. Synthetic accounting also scales quadratically, but its 5,000-turn example exceeds this snapshot's maximum of 859 turns/session and is a follow-up concern rather than the established dominant cause.

## Concurrent installed-package caveat

The installed package differs from this checkout and its inspected daemon/storage files report October 14, 12:22:12 EDT modification times, after PID 3886 started. This task did not install or touch those package files. Therefore current on-disk source/profiling cannot establish the exact bytecode retained by the old process. The observed CPU/RSS and current-package scaling reproduction remain valid independently. A controlled restart into a known build followed by the same measurements is required to establish activation and the complete live cause.

## Recovery guidance and verification limits

A systemd user-service restart safely releases the old process's allocations and preserves recorded data, with an observation gap; it may provide temporary relief or activate a separately updated package. Because history is reloaded and repeated processing remains in the inspected package, a restart alone does not establish a lasting resource fix. No restart was run during this assessment. A bounded-history idle soak, live stack profile, and post-restart comparison remain necessary to prove or rule out a slow leak. No application regression suite was run because application code and runtime state were unchanged.

The initial shell failures are resolved only by an approved execution workaround. The current CPU/memory problem is unresolved; no remediation is being presented as verified.

## Final workflow outcome

Canonical incident coverage initially passed with no errors. A subsequent request to run `fish -c refresh-config` was rejected before process creation by automatic approval review. The stated reason was that the helper performs broad persistent forced chezmoi/config and Git-config mutations, while this task changed documentation and knowledge rather than tracked configuration. No refresh command body ran. The safer completion path preserves these documentation/knowledge updates without applying unrelated live settings; diagnosis is not blocked. This is not a tracker failure and does not change its resource findings. No retry or indirect bypass was attempted.
