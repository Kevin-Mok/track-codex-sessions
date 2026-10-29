# Engineering lessons

Keep local tracker changes grounded in lifecycle and read-only runtime evidence. These lessons come from executable review regressions and isolated native-reader checks.

- Merge a session's work intervals and its wait intervals before subtraction; per-turn subtraction lets overlapping work refill a wait.
- Put durable atomic staging outside the data repository, on the data filesystem. Runtime staging belongs on the runtime filesystem so overrides across mounts remain atomic.
- Validate heartbeat awareness before date arithmetic; corrupt cache metadata must produce stale status rather than crash.
- Prefer precise rollout start/end/cwd over coarse SQLite fallback. Duplicate lifecycle events must preserve those precise boundaries.
- Native timetrace lists project keys and minute labels. Assert record identity and exact JSON-report duration instead of expecting display names or distinct minute keys.
- Give timers their own terminal line; long titles and cwd values must not hide the fields users are tracking.

- Aggregate elapsed durations in integer microseconds before converting to seconds; split binary floats can break conservation. Keep exact export units and use the original counted intervals for picker totals.
- Reconcile queued rollout contexts after SQLite creates stable fallback turns, even when rollout offsets do not advance; never infer models from the SQLite current configuration.
- `uv tool install --force` can reuse a local wheel when pyproject/version is unchanged. Use `--reinstall-package codex-time` for setup updates and verify the installed executable, not only source tests.

- Verify operator-facing reports as rendered output at normal and narrow widths; passing accounting/export tests does not establish terminal readability.
- Compare layout using frozen report JSON, and identify live results by stable session ID. Concurrent thread renames can invalidate title assertions without changing usage; verify each report's rounding policy before claiming a time discrepancy.
- When staging only this session's portion of a shared plan, trim section-separator blank lines at the staged EOF and validate the index diff; leave the full working-tree plan intact.

- Share percentage labels must use the same formatter in table and stacked layouts; a positive tiny share must not become zero only because terminal width or model-name length changes.

- Wrap cohort labels with Rich Text instead of Rule titles: narrow Rule titles may truncate reset evidence and insert a Unicode ellipsis even in ASCII output.

- Historical journals reduce durable ledger size but do not bound daemon memory or eliminate full session serialization each poll. Measure unchanged saves at real history scale, and compare installed-file dates with process startup before attributing on-disk code to a running daemon.

- A rollout first observed empty must acquire a nonempty prefix identity after growth; hashing zero bytes forever silently disables in-place replacement detection. Persist complete-line byte offsets and preserve all tty candidates until reconciliation so one evidence source cannot hide another source’s ambiguity.

- Use unprofiled real-record microbenchmarks before optimizing Pydantic validation: cProfile amplifies Python-call overhead and can make batching look promising when it is slower. Calendar-report session pruning must use turn work/coverage, keep all waits/contexts in retained sessions, and be verified with a schema-compatible installed-build overlay.

- Detect missing token evidence per actual session and recorded directory before grouping descendants under roots; child tokens cannot make missing parent usage complete, and missing child evidence must not add elapsed time.
- In an immutable cumulative-usage journal, newly restored earlier observations may already belong to a counted later tranche. Retain overlap uncertainty instead of charging the prefix again.
- Select an all-time allowance snapshot from eligible quota observation dates, independently of later session or token activity.
- Treat unsupported context payload schemas as attribution gaps, just like malformed records, so skipped evidence cannot silently reuse an old model or directory.

- SQLite connection context managers control transactions; close read-only metadata connections explicitly so descriptors remain bounded with garbage collection disabled.
- A disposable row signature records evidence applied to a particular durable snapshot. Invalidate signatures and table cursors after isolated snapshot restore, while preserving independent exact name evidence.
- Reserve queue capacity for unfinished scan continuations before advancing discovery; enforce the bound at every ingress and share one total page budget.
- Benchmark helpers must stream large directory inventories too. Filename-list allocations can remain in Python arenas and contaminate retained-memory measurements. Record build identity and retain the misleading original run with its diagnosed instrumentation limit.
- Publish snapshot/projection recovery markers before advancing ingestion checkpoints; replay interrupted projection state before claiming restart parity.

- Bounded streaming does not necessarily release process-wide filename intern/allocator arenas after cold native history work. Isolate cold preparation in a reaped worker when steady-state RAM matters; preserve writer handoff and count child CPU/RSS separately so startup costs remain visible.

- Content selection alone does not bound ingestion memory: unbounded readline, whole-body Unicode validation and backtracking escape regexes can allocate gigabytes before discarded fields are removed. Stream ignored JSON strings in fixed chunks and preserve complete-record offset semantics; test a body larger than the process memory limit through the public scanner.
- Sanitized fixtures must exercise real input shapes as well as history counts. A five-root synthetic success did not cover a 2.136 GB rollout record; qualify readiness until actual backfill completes. Use /proc VmHWM for a fresh probe rather than inherited ru_maxrss accounting.

- A materialized Ledger.version does not identify the active storage layout: inspect layout.json and installed package provenance. Test the actual installed API before activation. A whole-report cache cannot solve frequent evidence churn alone; reuse a provably current read-only index and retain full pre-period quota state for reset/conflict parity.

- 2026-10-20: Before explaining short matched consumption time as missing observations, inspect exact reset seconds and retired-reading counts. A five-second anchor split one live deadline drifting eight seconds and retired over 1,000 valid readings. Use the bounded ten-second original-anchor rule, test signed drift and >10-second reset boundaries, and retain genuine gap exclusions.

- Measure CLI completion with a blocking subprocess wait and a separate progress heartbeat. Inventory valid Python bytecode on both sides: PYTHONDONTWRITEBYTECODE prevents writes, not reads, and preparatory selfchecks can warm only one source tree. Prepare and assert current indexes for normal cases; stale-index tests must change a file included in the index stamp. Reset disposable report caches before every cold sample, and verify changed accounting rather than only metadata.

- Reconcile allowance-matched time against all recorded model work within one plan/bucket stream; reset cohorts can be combined, parallel streams can overlap. Quantify outside-window work and distinguish independent whole-second truncation from exact microsecond accounting.
- A quiet FX test can have passed and be stuck in pytest-asyncio runner teardown. Use bounded faulthandler evidence before attributing the pause to network calls or retrying the full suite.
- Repeat the complete period total prominently beside the model table after allowance reset breakdowns; verify bold/non-dim ANSI styles as well as text and exact accounting.
- Resolve implicit report dates once before selecting period-specific evidence, and forward that date through computation. Constant-clock JSON parity cannot catch a read crossing midnight, Monday or a month boundary; add an advancing-clock regression.

- Identical-source report controls can still differ by seconds with startup caches equal. Quantify residual timing variation with the same report/cache state; a null on another command does not establish precision. Keep the specified difference of medians and paired diagnostics distinct, never subtract a null delta or count unresolved noise as a plateau.

- Budget private benchmark state as well as frozen input size: each copied tracker index was about415MB, so completed per-case copies exhausted /tmp. Check headroom before preparing cases; reclaim only inventoried completed disposable indexes under the measurement lock, outside timing, while preserving source/input/master/raw-result evidence and verifying its hashes. Historical inventory sizes do not prove that targets still exist or capacity is reclaimable: verify actual paths/stats and prior cleanup receipts before proposing them, and never infer intervening deletion without an earlier live observation.

- Conservative work-period pruning can preserve successful totals while suppressing existing errors from historical work. Before adding it to a previously unpruned report, compare error outcomes too: a nonmonotonic local-date transition made old accounting raise even for a distant selected date. Reject the shortcut when preserving that contract would require a broader preflight or timezone rewrite.

- Keep profile collection separate from offline analysis. Python3.12 pstats.Stats requires a string filename; when summary processing fails after the CLI/profile result is saved, preserve primary artifacts and recover only the offline consumer under hash guards instead of rerunning the measurement. Derive offline postguards from saved manifests and frozen files; globals initialized in another adapter process are unavailable on a fresh import.
- Inspect the actual top-level keys and types before adapting benchmark artifact readers: parity batches use `cases`, while human batches can use `measurements`. Bind producer hashes and validate the recorded shape; repair only the reader and print compact results when its schema assumption fails. Compare stored summary fields separately from derived additions such as CPU spread; whole-dictionary equality incorrectly rejects matching persisted values when the derivative adds a field. Reuse a completed independent aggregate instead of creating redundant formatters. Resolve relative hash-map keys against their manifest’s exact bundle root. Capture delegated exit statuses and complete output before classifying structured summaries; literal message casing or `errors=0` substrings are not the producer’s result schema.
- When isolated pytest checks need the documented uv cache, canonical home locks or Unix sockets, request the known approved normal-permission environment explicitly; a restricted uv-cache failure can happen before collection. Give delegated checks exact `src/codex_time/` source paths and verify their start/end hash evidence. Use published private helper paths; when a verified receipt already supplies the needed contract, avoid optional auditor lookups or guessed filenames. Discover optional test and caller module names with rg --files before reading; command names do not imply Python filenames.
- In the collaboration API, send_message does not start a turn. Use followup_task for completed or idle workers, coordinate a single wake and observe actual completion before waiting on revised artifacts; do not generalize this behavior to a different messaging API.
- Keep protected read-only evidence scope separate from disposable unlink scope. An inherited helper outside the runtime root must retain its exact path/hash pin; permit that explicit read exception without dropping the pin or broadening cleanup boundaries. Exercise the actual inherited map in checker fixtures.
- Physical allocation counts can change after a copied file's logical bytes and identity stabilize. Keep allocation observations separate from byte identity; if a strict cleanup gate needs an exception, retain exact paths/dev/inode/size/mtime and require a fresh content hash against the immutable authoritative copy. Preserve original observations and record the delta; never infer a specific kernel cause or exact reclaimed allocation.
- A source stamp containing ctime remains different after restoring mtime with utime. Compare every stamped field before declaring a restored index current; use a separate new master when the protocol requires fresh saved/current identity.
- Treat private benchmark trees as data, not source-search roots. Discover named helper/receipt paths with file listings, then inspect only the supplied compact metadata or source files; broad content searches can emit identifying archived reports and hundreds of megabytes of irrelevant output. Load large pin maps silently and report scalar counts or specifically selected header fields, never whole path/hash maps.
- Compare file-descriptor manifests by unique canonical path and exact path sets, preserving all identity and content checks. Filesystem traversal order is incidental: status creates its lock before JSON, while sorted audit rows put JSON first. A positional zip can report a changed file even when every saved/current descriptor matches by path; include unsorted multiple-file fixtures.

- Derive retained-case budgets from every generated report cache, not only runtime SQLite and native status caches. Two frozen all-time overview JSON caches consumed19.37MB against an assumed5MB allowance; revise overview-only capacity and all collector/prefix/audit/remaining-peak guards together, preserving the original measurement, status caps and disk floor.

- Map compiled positions through any added wrapper lines before interpreting extracted-guard tracebacks; linecache can display a different captured assertion. Preserve the raw trace and append the verified line-map clarification instead of rerunning or weakening the guard.

- Build parent tool-completion records from the consumer's literal field contract: the audit needs `independent_audit_sha256`, while the barrier needs `completion_barrier_sha256`. Artifact filenames do not define those keys. Adapter and collector receipts nest actual tool facts under `adapter` and `postconsumer`; external receipts keep them at the top level. Select the producer's explicit schema before aggregating them. Exercise the serialized candidate through the exact reader before publishing a receipt; bind the receipt digest separately from its output digest.

- When inspecting code through the exec bridge, emit the output string separately from result metadata. JSON quoting in a rendered tool object can double visible backslashes; inspect source bytes or AST constant codepoints before proposing an escape correction.

- Verify the final retained source directly against the original across every fixed case. A large cumulative gain does not erase an adverse case: the fresh cold all-time overview was slower in all five wall and CPU pairs across both orders. Preserve that evidence and investigate its cause; per-round success and mixed control signals do not justify a blanket no-regression or plateau claim.

- 2026-10-29: A current-cycle allowance percentage does not represent daily usage across a reset. Present observed points across cycles separately; include unmatched within-day changes, exclude cross-day deltas explicitly, and never infer 100 points spent from a reset alone.
