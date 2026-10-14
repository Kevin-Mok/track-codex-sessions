# Investigate Codex Time resource use

Determine why the background tracker consumes close to a CPU core and approximately 1.8 GiB RSS. Measure the live process, compare the installed implementation, and profile a safe read-only reproduction; provide evidence and practical recovery guidance.

## Scope and decisions

This request is an assessment of resource leakage. Investigation uses Linux process counters, service diagnostics, source review, and isolated profiling. It preserves Codex history, tracker records, and the running daemon while collecting evidence. Application fixes, installation, commits, and pushes are outside this assessment. Default collaboration mode is active; maintain this living plan because a Plan Mode switch is not exposed.

Relevant files: src/codex_time/daemon.py, ingest.py, storage.py, metadata.py, live.py; systemd/codex-time.service; tests/test_daemon.py. Findings live in docs/postmortem/2026-10-14-codex-time-resource-use.md.

## Checklist

- [x] Capture initial Git status and process/service baseline.
- [x] Consult debugging workflows, applicable lessons, feedback, and incident knowledge.
- [x] Sample current CPU, RSS, I/O and descriptor growth.
- [x] Compare installed source with checkout and independently review history retention.
- [x] Profile an isolated read-only path and distinguish observed overhead from an unproven leak.
- [x] Record findings, limitations, recovery guidance, and reviewed incident learning.
- [x] Verify final evidence and prepare exactly three direct verification commands.

## Protected dirty state and risks

Pre-existing modified README.md, docs/smoke-tests.md, plans/daily-repo-session-time.md, src/codex_time/day_output.py, tests/test_day_output.py; pre-existing untracked docs/postmortem/2026-10-06-daily-report-rerun-preflight.md. Do not stage, revert or rewrite these changes. Do not print conversation bodies. A full live ledger parse can itself consume substantial memory; bound profiling and output to metadata counts. No production writes are needed for diagnosis. No configuration changes are planned, so refresh-config is not applicable. Newly authored investigation documents can be removed independently if needed.

## Verification

- Live baseline: systemctl --user status codex-time.service --no-pager; ps -p 3886 -o pid,lstart,etimes,time,pcpu,rss,nlwp,comm.
- Current activity: sample /proc/3886/stat, status, io and fd at five-second intervals. Report CPU deltas, RSS, I/O deltas, descriptor counts, and time window.
- Profile installed code read-only against a copied/minimized in-memory historical structure; do not call Store.save on live data.
- Validate the report with the canonical postmortem helper check --postmortem /home/kevin/coding/track-codex-sessions/docs/postmortem/2026-10-14-codex-time-resource-use.md after recording learning.

## Progress and review

Baseline verifies excessive lifetime CPU and high process/service memory. Initial wrapper failure is covered by the approved-route workaround; an erroneous skill path was corrected using the catalog. An independent explorer is reviewing hot paths and retention. No fix or restart has been attempted; findings must distinguish supported inefficiency from a proven leak.

## Measured findings and revised assumptions

15-second CPU delta: 98.1%; top corroborates 99–100%. RSS was approximately 1.83 GiB and descriptors 8–9 during that interval. Logical I/O deltas were 247.7 MB read / 163.4 MB written. Read-only installed-code profiling against 5,449 sessions and 49,885 turns showed unchanged saves taking 2.160 / 1.942 / 1.700 seconds under cProfile, with writes disabled. Full serialization and projection comparison therefore exceed the nominal one-second loop budget for this dataset. All these commands exited 0. Health reported running with a fresh heartbeat.

Installed source differs from checkout and reports modification after PID startup, so the assumption that on-disk source exactly matches loaded bytecode is withdrawn. This does not invalidate process measurements or the independent current-package reproduction. Do not claim a complete attached-process root cause or lasting recovery without known-build restart/measurement. Restarting may temporarily release memory, but no restart was performed. Assessment is complete once documentation and incident coverage are checked; the underlying performance problem remains unresolved.

## Learning and workflow review

Recorded the current report alias/hash and new unresolved finding `local-observer-full-history-polling` in the canonical linux-config postmortem-memory sources.json and references/artifact-verification.md, preserving pre-existing edits. The initial targeted helper check passed (exit 0, no errors or changed/unregistered aliases). A final current-hash check follows after adding the automatic-review event to the report.

Automatic approval rejected refresh-config before launch: this documentation/knowledge-only task does not require its broad forced persistent configuration and Git-config mutations. Complete safely without retrying or bypassing that action. No live configuration, application source, daemon or durable tracker record was changed by this task. Documentation additions to pre-existing dirty README/smoke files are append-only or a small anchored insertion; all original work is retained. No commit or push was requested or made.

## Final evidence

Canonical targeted coverage check passed for report SHA-256 `68bea4fe911cee6a1c8badc53104576e0a6612b451cfd3987ae0d7393e94a9a1` (exit 0, zero errors, no changed/missing/unregistered source). Final direct commands: systemctl user status, two top samples of the current service PID, and installed codex-time health JSON. The old PID 3886 remained running with approximately one-core CPU and 1.8 GiB RSS. Repository diff whitespace check was silent; all application edits remain the pre-existing daily-output work. Documentation-only assessment is complete. The performance issue and exact long-lived bytecode attribution remain unresolved; no fix, restart, commit or push occurred.

Final handoff verification commands (fish, any working directory, no sudo):

- systemctl --user status codex-time.service --no-pager
- top -b -d 1 -n 2 -p (systemctl --user show codex-time.service --property=MainPID --value)
- codex-time health --json

## 2026-10-14 follow-up: startup and session-state cache

This follow-up implements the user's three-phase cache request. It supersedes the earlier assessment-only scope for the files described below. Default mode remains active because a mode-switch tool is unavailable. No rollout, Codex database/configuration, installed package, service, or live tracker record will be changed. Work stays in this checkout; the separate dirty incremental-tracking worktree is protected.

### Phase 1: diagnosis before design

Real-data inventory: 5,487 active rollout JSONL files totaling **6,590,083,689 bytes (6.14 GiB)**; no archived files. Largest rollout: 2,136,497,768 bytes. Recursive discovery plus stat: **0.0691 s**. Live files continue growing, so counts describe the measured inventory.

The installed build uses ledger v4, while this checkout expects v3. Its session listing took **28.60 s**, 1,729,928 KiB maximum RSS. That build includes token reporting and is not a comparable before/after baseline. Checkout comparisons use an isolated `/tmp/codex-time-benchmark/data` snapshot of the real ledger/quota journal; only the ledger version marker is adapted from 4 to 3. It contains 5,485 sessions, 50,694 turns, 287,107 quota observations. Nothing is downgraded in production.

Measured before changing product code (first run = application cold start, later runs = warm filesystem; kernel caches were not evicted):

| Operation | First run | Warm runs |
| --- | ---: | ---: |
| Actual picker readiness, PTY, current directory | 10.182 s | 10.826 / 9.187 s |
| `sessions --all-dirs --json` | 12.460 s | 13.099 / 10.966 s |
| `health --json` (also old `status`) | 7.205 s | 7.171 s |

Top costs, recorded **before cache design**:

1. **Full ledger/journal loading: 8.523 s under cProfile**, including 6.817 s in 287,108 Pydantic JSON validations. Reads 46,064,710-byte live ledger and 59,234,943-byte quota journal; quota history is irrelevant to picker/session state and health. Hashing those files costs only 0.075 s.
2. **Rebuilding all session accounting rows: 3.489 s under cProfile**, 2.597 s in display segments (2.577 s in interval merging/subtraction). Required for historical totals, irrelevant to state watchers.
3. **Unchanged history serialization: 1.171 / 1.336 s** with all writes and projection disabled, plus **0.374 s** to serialize every session again for projection signatures. These operations exceed a one-second idle loop budget. Status/startup readers must bypass this path.

Directory traversal is not the leading cost. There are no startup tty/process lookups in current production code. Raw parse and unchanged-scan profiles are being collected separately.

Reader inventory: `ingest.RolloutReader.scan/_scan_file` is the only raw rollout reader. It discovers both active/archived roots; cold ingestion parses every complete JSONL record, while resumed ingestion seeks to offsets but still opens/hashes the first 256 bytes of every file every poll. Historical accounting needs lifecycle, model/cwd context, waits and quota records across the full file on rebuild; appended records suffice thereafter. It discards message bodies. A tail alone cannot recover a last message or start event arbitrarily far back.

`daemon.import_history` deliberately creates a fresh reader (full reconciliation). `run_daemon` restores checkpoints only when the ledger fingerprint matches. Normal CLI `sessions`, picker and `health/status` do **not** reparse raw rollouts: they call `Store.load`, which reads the complete ledger and quota journal. Picker repeats that on each loop. Metadata refresh separately rereads SQLite rows and session_index.jsonl; live observation uses metadata-only socket RPCs with includeTurns=False. Outside watchers currently have no reusable compact state contract.

### Protected state and failure lookup

Initial dirty status: README.md, docs/smoke-tests.md, plans/daily-repo-session-time.md, src/codex_time/day_output.py, tasks/lessons.md, tests/test_day_output.py; untracked existing daily-report/resource postmortems, this investigation plan and tasks/todo.md. Preserve these bytes except scoped append/update in the requested plan/todo/README/smoke surfaces.

Living incident: [session cache investigation](../docs/postmortem/2026-10-14-codex-time-session-cache.md). Postmortem lookup `bwrap loopback Failed RTM_NEWADDR` matches ext-sandbox-loopback; approved execution works. `local-observer full history polling` matches local-observer-full-history-polling; fresh serialization profile independently corroborates it. Diagnostic harness failures (missing module entry point, incompatible live v4 data) are recorded there; corrected console entry point and isolated fixture resolve the measurement setup.

### Phase 2: design and atomic implementation plan

The supplied user design authorizes implementation after numerical diagnosis. Keep native/default execution mode and implement directly, with a bounded cache-module worker and independent final review. Python 3.12, stdlib filesystem/flock/JSON, existing Pydantic models and atomic writer; no dependency changes.

- **Private cache**: `session-status.json` under Store.runtime, versioned and bound to resolved Codex home. Map entries by absolute rollout path; store device/inode, size, nanosecond mtime, complete-line byte offset and compact state (session ID, cwd, rollout path, mid_turn/idle, last user/assistant message, last update, nullable tty). Private directory/file permissions; never include text in ledger, checkpoints, projections, logs or benchmark output.
- **Freshness**: stat discovered files on every normal status request. Exact identity/size/mtime hit opens no rollout; growth on same identity seeks to the last complete offset; shrink, same-size rewrite or different device/inode rebuilds that file. Missing/new files prune/add entries. In-place growth is assumed append-only as specified; arbitrary same-inode prefix rewrites with growth are outside that source contract. Partial final lines are retried from the last complete offset. Reject corrupt/schema/home/offset-invalid caches and rebuild, reporting ongoing progress on stderr.
- **Readers/writers**: status takes a dedicated cache lock, refreshes metadata/changed files, and publishes with same-filesystem temporary write + fsync + rename via existing atomic_json. Concurrent direct file readers get an entire old/new snapshot. `status --json` retains health keys and exposes `sessions` plus freshness, cache path and scan counters; `health` stays the observer-health command. Zero raw opens on a fresh hit, regardless of daemon availability. Daemon refreshes the same cache; status works independently. Tty is nullable and mapped only from exact process evidence, never cwd guesses.
- **Startup**: introduce `Store.load_timing()` for content-free timing data without quota journal, cache it by ledger stat in the Store instance, use it for picker/sessions/history/projects/model-time. Health obtains count/diagnostics without constructing historical models. Historical allowance/overview/daemon/import keep full load where needed. New status bypasses all historical load, accounting and serialization.
- **Existing scanner**: add size/mtime identity cache-hit skip to FileState. Preserve inode-based move/wait semantics, partial-line handling, idempotent full import and checkpoint/ledger hash coupling. No raw source mutations.

Ordered tasks and acceptance:

- [x] Record baseline, source inventory, protected files and top three measured costs before design.
- [x] Task 1 — `session_status.py`, `tests/test_session_status.py`: defining RED then GREEN for fresh hit without raw open, incremental append, truncate/replace, new/delete, corrupt/version/home-invalid cache, partial UTF-8 lines, lifecycle/message state, atomic concurrent visibility and nullable tty. Public `session_status(home: Path, runtime: Path, progress: Callable[[str], None] | None = None) -> dict[str, object]` returns JSON-ready sessions, freshness, cache path and scan counters.
- [x] Task 2 — `storage.py`, `ingest.py`, `cli.py`, `daemon.py`, focused tests: RED then GREEN for no quota/history load on lightweight paths and no raw open on unchanged scanner restart. Wire real status with JSON/plain modes, progress to stderr, preserve health compatibility; daemon updates compact cache.
- [x] Task 3 — watcher docs, README/smoke append, todo checkbox/follow-ups, reusable read-only benchmark/parity script and Cursor handoff prompt. Repeat cold/warm picker and unchanged status measurements; compare cache with forced full replay on a stable read-only snapshot, suppressing messages.
- [x] Final verification — full pytest, Ruff, strict mypy, build, diff review and independent evidence review. Record remaining limits and activation state; no install/restart/commit/push requested.

Risks/review focus: concurrent append between stat/read; partial lines and malformed JSON; stale/corrupt/home-mismatched cache; live files disappearing or unreadable during discovery; tty unknown for shared backend; cache contains private text and must remain outside durable data. Preserve stale state only with explicit freshness failure. Test real byte offsets and consumer-visible states, rather than source-text assertions.

Rollback: remove the disposable session-status cache and revert only task-owned source/doc hunks. Durable accounting schema and rollouts remain unchanged. In-place source checkout is used to preserve requested active plan/todo and unrelated dirty work; other worktrees are read-only.

### Implementation evidence and refinements

Raw scan finished: **120.113 s** full lifecycle parse under cProfile, **0.453 / 0.496 s** unchanged scans. Source profiles are saved in /tmp only; no message bodies emitted. Watcher cold builds pay a one-time raw replay; warm calls must prove zero raw opens.

Task 2 RED: three initial fast-read regressions failed for expected missing load_timing, unchanged raw open and short-prefix replay. After implementation, 20 focused ingestion/storage/fast-read tests pass. A pre-existing in-place-grown replacement regression initially failed; preserving a stable <=256-byte prefix check on **changed ingestion files only** restores compatibility. Compact state cache still seeks directly to appended bytes under the explicit append-only contract. This bounded ingestion identity check is a deliberate correctness exception to append-only byte reads; unchanged files open zero times.

Refinement: refresh the compact state cache on demand through `status`, independently of daemon health. Do not add a second cold full-rollout pass to daemon initialization; that would worsen the measured startup. The daemon's existing incremental ingestion now skips unchanged files. External watchers call status for current freshness, rather than assuming a file-only snapshot updates while no status client runs. No extra writer is introduced into the daemon loop.

Task 2 CLI RED: six cases failed because health/status and timing commands invoked Store.load; lightweight branches now use summary or timing-only snapshots. Existing full writer/allowance paths retain complete journal validation.

### Phase 3 results and review

| Operation | Before | After |
| --- | ---: | ---: |
| Picker first-process readiness | 10.182 s | 3.362 s |
| Picker warm readiness | 10.826 / 9.187 s | 3.683 / 4.035 s |
| All-directory session listing, first run | 12.460 s | 4.813 s |
| All-directory listing, warm runs | 13.099 / 10.966 s | 4.463 / 4.196 s |
| Health, first run | 7.205 s | 0.841 s |
| Health, warm runs | 7.171 s | 0.837 / 0.806 s |
| State check, unchanged | No equivalent compact contract; full rollout ingestion 120.113 s profiled | 2.528 s wall; 0 opens / 0 bytes |

New status benchmark on frozen **5,490 rollout paths / 6,598,370,855 bytes**: cold empty-cache build **75.567520 s**, warm **2.426398 s**, unchanged **2.528083 s**, independent full replay **61.959201 s**. Every field for every path matched cold, warm, unchanged and full replay. New files accrued during the task explain the inventory difference. Cold cache build and full replay include source reads, compact-cache publication, CLI JSON export and process/import overhead. The old full-ingestion number uses cProfile and constructs accounting, so it is not a like-for-like speedup denominator; warm versus same-code full replay is about 24.5x faster. Cache file size was 67,258,900 bytes; it contains only the latest message pair per path, not full histories.

Reproduction: /tmp/codex-time-baseline.py measured old checkout against the isolated real-data ledger/quota snapshot; /tmp/codex-time-picker-benchmark.py measured actual curses readiness before/after with the same directory/data. `scripts/verify-session-status.py` is the delivered reusable frozen-input verifier; it read raw sources only and cleaned all temporary copies. No kernel cache eviction was attempted. Filesystem state, concurrent system load and cProfile overhead limit comparisons; installed v4's 28.60-second list is separately labeled, never used as the checkout denominator.

Fresh checks after implementation/review: `.venv/bin/pytest -q` **259 passed in 34.03s**, strict `.venv/bin/mypy src` **20 source files**, `.venv/bin/ruff check .` **all passed**, `uv build --offline` **wheel and sdist built**, `git diff --check` **silent exit 0**. A final targeted run covers the small human health/error decoration change. Automated cases cover cache hit/no source open, append exact bytes, truncation, same-size rewrite, inode replacement, new/delete/archive, malformed/corrupt/schema/home/offset-invalid cache, partial UTF-8, source race/unavailability, private modes, concurrent publication, process tty conflicts and checkpoint compatibility.

Independent review found empty-first ingestion fingerprint and tty ambiguity bugs plus non-ASCII plain progress. Each has a defining observed RED and a focused GREEN regression. Final tty reconciliation retains all candidates, including ambiguity within one evidence source, and emits null unless the union is a singleton. The reviewer’s final message reflected a pre-fix snapshot; parent tests validate the completed fixes. No material review finding remains outstanding. Private cache directory remains 0700; an external chmod of an existing cache file is not repaired on a read-only hit, but a subsequent publication creates mode0600.

README gate: `update_in_same_change` repaired only the new command/alias and message-privacy coverage, preserving its existing hook/stack/proof/setup order and unrelated changes. Watcher docs, smoke checks, completed todo and [Cursor continuation prompt](../prompts/codex-time-session-cache.md) describe the final behavior. No code/configuration install, service restart, commit or push was requested/performed. No configuration was changed; refresh-config is not applicable.

Follow-ups/limitations: installed production ledger/build is v4 while this checkout is v3; do not install this checkout over live v4 data. Status itself bypasses the ledger and works with real live sources. Picker startup improvement is verified on the isolated real-data snapshot, not activated in the installed service. Frequent whole-history daemon persistence/projection remains the separate protected incremental-tracking worktree’s scope. A metadata-only watcher projection could reduce the 67.3 MB full-message cache/export; a completion-event journal would be needed to enumerate intermediate turns between hourly snapshots.

Final live verification populated only codex-time's own private runtime cache: first scan 5,492 paths, 6,602,574,057 bytes in 59.291858 s; next check 3.351300 s read only 13,780 new bytes from two changed files (5,490 hits). Source command works independently of live ledger v4. Frozen unchanged-input figures above remain the performance comparison. Final display-targeted tests: 35 passed in 12.26s; final Ruff/mypy clean. No remaining implementation blocker; installed integration and daemon serialization are explicit follow-ups.

Canonical learning was updated directly in linux-config's postmortem-memory sources.json and references/artifact-verification.md under `local-rollout-session-status-cache` (activation_pending, code scope); the prior full-history daemon finding remains unresolved. Current report SHA-256: e510fd05420e3cc88724c32f081d9ccacfc944e008275190733b68f0d5cfb203. Targeted `check --postmortem /home/kevin/coding/track-codex-sessions/docs/postmortem/2026-10-14-codex-time-session-cache.md` passed exit 0 with zero errors, changed sources or unregistered aliases. All edits preserved canonical knowledge's unrelated dirty entries. Final package build after the display changes also passed.

Direct handoff checks (repository root, no sudo): source `status --json` summarized to freshness/count/scan metrics; source `status --plain` for recent readable states; `scripts/verify-session-status.py` for frozen full replay and zero-byte unchanged checks. Expected-output examples are in the final handoff; [smoke tests](../docs/smoke-tests.md#cached-session-state-for-outside-watchers) and [watcher docs](../docs/session-status.md) contain the durable procedure. Suggested commit, when requested: `perf: cache session state and trim startup reads`.

## 2026-10-14 follow-up: reduce actual CTO runtime

Authorized saved prompt: `prompts/speed-up-cto.md`. Default mode remains active (no Plan Mode switch exposed). Preserve initial dirty files and all separate worktrees. No commit/push or incompatible install. Main is ledger v3; installed command is v4/token-aware. Use main for compatible shared source improvements and a temporary installed-build overlay for real-data parity; activate only if safe and compatible.

- [x] Measure actual installed first plus three warm invocations; rank profiled costs and count data.
- [x] Add defining RED performance regression at the measured seam; implement minimal safe GREEN change.
- [x] Verify accounting, output parity, changed inputs, full checks and repeat measurements.
- [x] Align README/smoke/todo and incident learning; state activation scope and deliver three direct commands.

Incident: `docs/postmortem/2026-10-14-cto-overview-runtime.md`. Preliminary hypotheses: quota-journal validation; repeated historical accounting; filesystem/import overhead. Existing cache optimization does not establish CTO improvement. Rollback is task-owned source/doc hunks only; no durable-data writes required.

### CTO diagnosis and chosen change

Live first/warm wall times: 23.286 / 24.892 / 28.063 / 26.100 s. Unprofiled loading 14.204 s, report computation 8.837 s. cProfile: loading 19.977 s (485,213 model validations, 197,517 usage records plus 287,695 quota records); report 16.970 s, of which segmentation 7.564 s, allowance 8.033 s, token report 4.512 s and two model reports 4.120 s. Profiling distorts Python call overhead, so rankings are supported by separate wall timings. Rendering 0.0153 s. No external process lookup or network FX refresh occurs in the report.

Rejected batched journal validation: real 20,000-row microbenchmark 0.113 s individual, 0.178 s batch-Python, 0.130 s batch-JSON. A defining RED for that candidate existed, but was replaced with the selected optimization's defining RED before implementation. Never claim cProfile overhead alone establishes a faster implementation.

Chosen minimal change: conservative session eligibility by closed turn/unfinished coverage intersection with selected UTC calendar bounds. Skip unrelated historical accounting in allowance and model reports; retained sessions keep every turn, wait, context and overlap owner. No persistent cache, data schema, options or output-format changes. Token report and full journal loading remain bottlenecks. Five defining tests observed RED (old work reconstruction/missing filter), then 58 focused report/accounting tests passed. Installed verification uses temporary copies of its v4 build, freezes ledger/quota/usage/FX inputs and clock, preserves token and all-period functionality, and compares entire JSON reports. Does not activate source changes.

### CTO frozen-input results and compatible-build integration

Stable v4 snapshot: 5,497 sessions / 50,981 turns; ledger 46,375,195 bytes, quota journal 59,374,398 bytes, token journal 158,569,274 bytes. All full JSON fields (including tokens and FX metadata with a fixed clock) match before/after for four runs. Before 23.674 / 24.978 / 24.576 / 23.775 s; optimized 22.120 / 22.821 / 22.370 / 22.121 s. Warm average 24.443 → 22.437 s (~8.2% faster); first-process 23.674 → 22.120 s (~6.6%). Kernel cache was not evicted. Largest remaining costs are complete journal validation, token-report historical segmentation, and historical allowance conflict processing. No claim of a subsecond report.

Independent source identity review found clean `.worktrees/token-cost-reporting`, all 26 Python modules and pricing data byte-identical to installed v4. Added only the helper, two report guards and six regressions there. Its Ruff, strict mypy (27 files), and package build pass. Full v4 suite initially had 330 passes and one existing daemon runtime timeout; installation waits for investigation and fresh complete validation. Main full 264-test run passed before adding the sixth changed-input test; final complete run pending.

Atomic integration sequence: verify known v4 source → copy scoped fix/test → full v4 checks → normal compatible uv tool reinstall without service restart → actual installed first/three warm timings → update docs/incident learning. Rollback uses original v4 sources from commit `0f5a5a6` and normal reinstall; never install main/v3 or change ledger/journals. No history rewrite or commit requested.

### CTO final verification and handoff

Compatible v4 activation is complete; the earlier “installation pending” entries are chronological investigation evidence. Normal offline uv tool install was pinned to Python 3.12 after correcting an initially unpinned interpreter selection. Current Python 3.12.3, ledger v4, Pydantic 2.14.1; all 28 installed source/catalog files match the compatible worktree. No service restart, durable-data/source-rollout writes, commit or push. Normal dependency resolution also refreshed packages; only the original frozen comparison isolates the ~8.2% filter improvement.

Actual installed first/warm **22.202 / 23.363 / 24.376 / 23.239s**, all exit 0; initial direct first/warm **23.286 / 24.892 / 28.063 / 26.100s**. Live history and load changed; don't present that range as a controlled causal speedup. Installed JSON retains allowance/token/model/reasoning sections. Correct test environments: main own venv **265 passed (30.48s)**; compatible v4 own venv without inherited PYTHONPATH **331 passed (34.87s)**. Ruff/mypy/build/diff clean for both. Frozen post-activation week and future/DST month whole-report parity pass. Week timings ~24.8/25.0s demonstrate no benefit where most sessions overlap the selected period.

Readme-recruiter-sync outcome `update_in_same_change`: preserve existing hook/hero/stack/navigation/proof/setup order and unrelated edits, insert accurate performance verifier and schema-compatible-install guidance only. Smoke docs now include day, week and future/DST month verification; todo marks compatible activation complete and keeps further validation/token/allowance work separate. No tracked configuration setting changed, so refresh-config is not applicable.

Canonical learning: report SHA-256 `14f3de636fc9be249ed3ce043b51ec17fbbaa284d6a129abd140d45e98acbdb1`; finding `local-calendar-report-history-work`, verified runtime scope, directly maintained in linux-config sources.json and artifact-verification.md while preserving pre-existing edits. Targeted check passed exit 0 with zero errors, changed/missing sources or unregistered aliases.

Atomic plan completed: diagnose → defining RED → conservative filter GREEN → original-build frozen parity → compatible build checks/install → actual installed repeat timings → docs/learning. Remaining bottlenecks are explicit follow-ups, not blockers for this change. Main and compatible worktree source edits remain uncommitted by instruction. Suggested commit if requested: `perf: skip unrelated historical work in overview reports`. [Paste-ready Cursor continuation prompt](../prompts/cto-performance-handoff.md) contains the exact automated/manual plan and documentation/rollback constraints.

Final direct commands (repository root, no sudo): `codex-time overview --plain`; `codex-time overview week --date 2026-10-14 --plain`; `python3 scripts/verify-overview-performance.py --runs 1`. First two exercise actual installed human output; the verifier proves complete JSON parity against full historical computation using temporary same-schema copies, including after activation.

Final installed human checks exited 0: day `--plain` output 2,071 characters, week `--date 2026-10-14 --plain` 2,548 characters; both ASCII and contain Recorded work, Allowance and Model work. Observed headings: “Wed, Oct 14, 2026” and “Oct 12 - Oct 18, 2026”. Periodic report progress remained visible on stderr. Fresh final Ruff/strict mypy/build and main/v4 diff checks passed; canonical incident coverage recheck passed without changes. No outstanding blocker. Original saved prompt was executed once and left unchanged; no metaprompt-run or prompt recompilation occurred.

## Merged origin integration follow-up

The later merge request integrates origin's token-cost reporting and streaming/incremental storage with the local private watcher cache. Main now supports legacy v4 and the v5 partitioned layout; earlier v3 compatibility warnings describe the pre-merge checkout. Projects retain token evidence; history/sessions/model-time use timing-only reads. Partitioned snapshots observe isolated restores; the picker keeps origin's 60-second cadence. See `plans/commit-plan-push.md` milestone 4 for 484-test, lint/type/build and disposable report/watcher parity evidence. No live installation or service change occurs in this merge task.
