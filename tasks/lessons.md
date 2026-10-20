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
