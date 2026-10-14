# Incremental tracking execution tooling — October 14, 2026

Record execution-tool failures separately from tracker regressions. Use the approved scoped execution route, verify each command result, and keep the optimization evidence independent of tooling limitations.

## Current activation approval gate

The v6 activation command was rejected before process creation by automatic approval review: installing a package and starting the service after a production OOM required clearer authorization than the available “cont” reply. No v6 installation or restart occurred. An explicit approval question is pending; the service remains paused (MainPID=0, NRestarts=2). Do not route around the rejection. Continue read-only review and documentation until approval arrives.

Lookup `deployment activation authorization ambiguous approval rejection` found generic activation/readiness findings, with no exact remedy beyond the active approval policy. The rejection itself is the applicable evidence; a passing build does not supply deployment authorization. This is an approval gate, not a code regression.

A v6 fixture inventory used an unmatched shell glob and exited 2; a text search of the empty redirected v5 log exited 1. Neither changed files or supplied measurement evidence. The existing inventory/path guidance applies: read the primary JSON fixture provenance and enumerate the known parent directory before selecting a fixture. The isolated v6 environment installed successfully from the verified wheel with cached dependencies; the cross-filesystem hardlink warning fell back to copying as documented.

## Symptom, impact and evidence

The first shell read failed before process creation: `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. Approved elevated reads succeeded with exit 0. The ingestion agent observed the same wrapper failure. No host policy was changed. Two exploratory commands named absent `.agent/PLANS.md` and `src/codex_time/tui.py`; file inventory confirms neither exists. The correct UI module is presentation.py. These misses changed no data.

## Prior knowledge and resolution

Query `bwrap loopback Failed RTM_NEWADDR` matched `local-sandbox-loopback-approved-route` in canonical postmortem-memory execution-environments guidance. Exact pre-startup symptom makes its approved-route workaround applicable; successful reads verify only the workaround, not sandbox repair. Use file inventory for further paths. Status: verified workaround; host wrapper cause unresolved.

## Learning

Canonical reviewed-hash registration and targeted checks are part of finalization, with actual outcomes in the plan; no independent new tracker-learning claim. The known wrapper finding covers this incident. Preserve unrelated canonical ledger edits.

A storage regression invocation named nonexistent test_usage_storage.py and exited 4 without running tests. Inventory identifies test_token_storage.py. A new defining title-only update test exposed a projection rewrite (one extra record modification); the implementation now compares the prior timing signature and skips native writes for title-only changes. RED/GREEN evidence follows in the plan.

## Integration regression investigation

First integrated daemon run: 3 failures / 24 passes. The cadence helper requires a datetime; runtime_status passed None for missing/non-string heartbeat, causing AttributeError (two existing regressions). Preserve its fail-stale guard. The real daemon flow timed out waiting for first recorded work; inspect isolated subprocess/data state before changing behavior. Production remains unchanged.

Subprocess stderr exposed the daemon timeout cause: runtime_save was called through a separate Store object without its writer-lock flag. Use the IndexedStore-owned locked Store. FX test doubles now accept the new sampling keyword and explicitly select one-second test cadence; production defaults remain 60 seconds. A speculative `python -m codex_time` invocation failed because no __main__ exists; use the packaged codex-time entry point. Old pytest temporary directories had already been removed; a dedicated --basetemp preserved runtime evidence.

A packaged-service smoke prototype compared RFC3339 text spellings (`+00:00` versus Pydantic `Z`) and timed out although completion was durably recorded. The peer harness now compares aware datetime values, preserving microseconds; its focused real socket tests pass. Canonical query `ISO datetime Z +00:00 spelling test comparison` had no exact ranked match; the local prior burn-DST fixture incident documents the same comparison pitfall.

Review also found idle-only samples inflating uncertainty/quality and rewriting history despite adding no work/wait span. A deterministic RED test with idle samples at0/60/120seconds reproduced the exact mutation. Ignore previous idle/unknown state after checking outages; only recorded working/waiting intervals add uncertainty. The recovery-export defining test exposed legacy/main journal ordering differences; preserve embedded/legacy-first order to match the public loader.

The new health-output defining test initially omitted its test-only sys import (NameError, no production impact). After correcting that test setup, it failed for the intended missing decorated/plain behavior and passed after implementation.

The10x benchmark worker showed116–127MiBRSS after a42.7MiBrestart. Inspection identified measurement instrumentation: os.walk retained/sorted ~500,000 native filenames, leaving Python allocator arenas resident before timed windows. A defining RED guard forbids os.walk name-list retention; streaming scandir with an order-independent SHA-256 accumulation fixes this artifact. Preserve the original measurements and rerun steady windows; do not attribute instrumentation memory to a daemon leak. The new test initially named a nonexistent loader helper, corrected before its intendedRED.

## Final review and verification incidents

A full regression run found one same-inode, same-size rewrite failure (399 passed, one failed, 83.67 seconds): the newly written turn was absent. The ingestion worker is investigating timestamp/signature collisions before any retry fix. No production data changed. Reviewer reproduction also confirmed that an isolated older snapshot restore retained metadata row signatures, preventing a metadata-only turn and name from replaying. A defining RED test reproduced it; invalidate disposable row signatures and table cursors on detected restore while retaining independent exact names. Focused GREEN verification is in progress.

Read-only lookup `restored snapshot stale metadata row signature` returned `ext-snapshot-consistency-durability` (transaction revision advice) and broader backup findings; no exact existing remedy covers this snapshot/signature mismatch. The executable disposable reproducer is the evidence for the new fix.

The reviewer initially named nonexistent test_metadata_incremental.py; actual inventory gives test_incremental_metadata.py. Root similarly looked for sources.json under references instead of the catalogued skill root. Corrected paths change no data. Two final benchmark subprocesses launched with detached Popen were terminated when the command session ended, leaving empty result files. Keep the supervising process alive and await every child; these empty attempts are not measurements. Ruff flagged an unused metadata_stamps assignment and formatting in a new test; the obsolete assignment was removed and the test formatted before subsequent checks.

Status: live activation pending. Keep this report current through final review; record actual final tests and source/package identities rather than upgrading earlier build evidence.

Deployment-helper tests also refused before install when an adapter mistook export-legacy stdout for conversion-manifest.json. Inspecting the actual recovery return shape fixed the seam. A test-only unsupported ledger.sources marker was replaced with real post-upgrade Session/Turn evidence; the helper must preserve that evidence, not unrecognised fields. Lookup ext-boundary-error-contracts applies to adapter shape checking. Source/package/service mutations remain confined to disposable fixtures.

## Final instrument and exporter correction

The first streamed inventory still caused a10x worker to retain112.7MiB after a42.5MiB restart, despite steady tracker work using fixed pages. Per-file pathlib parsing/relative paths remained in the instrument and interned unique historical filename components. A defining RED forbids per-file Path construction; ordinary ephemeral filename strings now retain the same metadata digest. Re-run tenfold windows with the corrected harness, retaining both prior artifacts. The first disposable profiler probe accidentally called resources instead of the actual snapshot helper (AttributeError before traversal); inventory of function definitions corrected it.

Final review found direct export-legacy bypassed the deployment projection guard. Three defining RED cases showed foreign text/JSON and symlink targets copied. The core exporter now applies the same strict native-schema/regular-file guard before conversion;15export/deployment regressions pass. Only offline recovery.py changed after the frozenv3 performance build; all daemon modules remain byte-identical. Finalv4 release wheel/service and deployment bundle are measured/prepared independently.

Completed broad verification:427passed in101.23seconds after exporter correction; updated benchmark7focused regressions pass. Strict types and Ruff pass before final metrics documentation. Old prior-wheel health probe used unsupported --plain; correcting to health --json verified historical interface. No live mutation occurred.

The isolated profiler completed: old inventory RSS18.38→159.61MiB under tracing; retained allocations65.3MiB across662832strings at Python3.12 pathlib.py:404 confirm filename interning rather than daemon models. Ordinary-string traversal is verified by defining RED/GREEN. A separate defining RED found repeated warmed benchmark workers reused old fixed observation timestamps and produced no new coverage. Seed each run after existing coverage of only its five active roots;8focused benchmark tests pass. Matched final1x/10x windows now use that same corrected harness and genuinely new active evidence (supervisor49424). The1x run copies the content-free portable fixture into its own directory, preserving the concurrently running soak store.

## Final startup and measurement checks

The child-CPU defining test intentionally failed with missing children_cpu_seconds, then passed after adding reaped-child accounting. Startup isolation defining tests cover launch cancellation, real stop/cancel and failure preservation. The final complete suite passed 436 tests; strict types, Ruff and wheel build passed. The final bundle prepared and verified without production changes. A late external child-memory sample found no child because startup had already completed; it contributes no peak-memory evidence. A separate exact-wheel cold-bootstrap measurement supplies the child scope instead. All historical failed diagnostic attempts above remain excluded from acceptance measurements.


### Final checkpoint rewrite: rejected patch shape (2026-10-14)

A delegated plan/progress rewrite used Delete and Add operations for the same path in one apply_patch invocation. The tool rejected it with `invalid patch: multiple operations target .../plans/incremental-tracking.md` before applying changes. Immediate reads confirmed both original documents remained intact; source, data and service state were unaffected.

Lookup: `apply_patch invalid patch multiple operations target same path` matched the confirmed `ext-patch-operation-contract` finding. Its editing-shell-transport reference explicitly requires one supported operation per path and recommends Update for existing-file rewrites. Applicable evidence is the rejected invocation plus unchanged full document reads. Resolution in progress: replace each file using one Update operation, then re-read the saved checkpoint. This is an existing learned pattern; no new finding is needed. Parent owns the final canonical reviewed-hash refresh.

Resolution: both existing documents were rewritten with one supported Update operation per path. Saved reads verified the execution-plan/progress headings, all local Markdown links and whitespace; source/service files were untouched. The final v5 wheel still matches SHA-256 e6d60d29a03cd2f43c62c0ea272c5ecc19cc4f293ea5d87e80ec61f6784d254e. This closes the patch-shape failure as a verified application of ext-patch-operation-contract; canonical hash refresh remains with the root task.

Checkpoint validation correction: the resolution append above ran before its preceding validator result was inspected. The validator actually found the assessment relative link missing from the isolated worktree, so the all-links-passed claim was premature. The assessment belongs to the root checkout; fix that grounded reference, then rerun validation. No source or service mutation occurred. Existing optional-path-discovery and check-exit-status guidance applies; root canonical review should use this corrected final record.

Final checkpoint resolution verified: both documents now pass local-link and whitespace checks. The original assessment lives in the root checkout and the link points there. A subsequent archive-hash assertion exposed a label mix-up: e6d60d29... is package source content, not wheel bytes. Labels are corrected; actual v5 archive SHA-256 is 816f564b6081b42ad8231ade7a970de4a0ed3196d416c543e0da3dc112f4b578, freshly verified exit0. No package or service was changed. Existing patch/path/identity guidance covers these fixes; final canonical hash refresh remains root-owned.

Final verification milestone: full `uv run pytest -q` completed 437 passed in 74.74 seconds, exit 0 (root session61018/chunk765ec9). Fresh strict mypy33, Ruff and diff whitespace checks passed; exact result references are in .harness/incremental-tracking/validation.json. No prior259-test log is reused as final evidence.


### Live metric PID rotation refusal (2026-10-14 21:48 UTC)

The read-only live resource monitor refused at 21:48:45 UTC before starting any measured window: known daemon PID3755683 was absent from worker_snapshot. Explicit /proc reads then confirmed /proc/3755683 no longer existed (FileNotFoundError errno2); runtime checkpoint instead named PID3760672 with heartbeat21:48:16 UTC. This was process identity rotation, not /proc permission denial. No production mutation or source write was performed by the measurement worker. Its /tmp/codex-live-resources-v5.log contains the refusal; no steady JSON result was claimed.

Readiness before refusal: 21:47:15 UTC showed2936 checkpoints,5515 current JSONL source filenames, pending_sources1 and explicit-name pendingFalse; initial source backfill was not complete. Earlier21:44 read showed1979 checkpoints. Only aggregate counts/states were recorded, with1working/32idle observed; raw rollouts, messages and IDs were not copied.

Canonical lookup query `proc pid io permission denied process metrics systemd user` returned no directly matching service-metric permission finding. The local-browser-source-process-identity reference's diagnostic of comparing the actual live owner/PID applies to identity resolution; its browser-specific remedy does not. Diagnosis is grounded in missing /proc files plus the changed checkpoint PID. Root is checking service health/journal independently; rotation cause remains unresolved here. Next measurement must resolve and explicitly record unit/checkpoint PID agreement and a stable process start identity before waiting for warm-up, then restart the entire window if identity changes. It must not silently combine processes or label backfill as steady. Final canonical reviewed-hash refresh remains root-owned.

Live OOM investigation lookup (2026-10-14): operator journal confirms PID3755683 died status9/oom-kill, service memory peak approximately1.0GiB, then restarted as3760672. Measurement worker did not stop/restart it. Root stopped tracking while investigating; no new controlled restart is authorized until a fix. Canonical query `OOM kill JSONL readline giant line bounded memory` matched local-incremental-observer-history-index (activation_pending), whose explicit huge individual record/session limitation applies, and local-bounded-json-nesting (related parser-boundary guidance, not proof of this OOM). The artifact-verification reference was read before diagnostics. Source _scan_file currently calls unbounded stream.readline before its8MiB between-record budget; this is a hypothesis, not yet the cause. A fixed-buffer binary file/line-size inventory will record aggregate sizes only, no bodies or session IDs. Root separately investigates session/cache/index/metadata and cgroup accounting.

Streaming implementation first checks flagged a reused char variable inferred asint before an optional peek assignment, and one102-character synthetic testline. The compiler/linter evidence is local and exact; no production data or installed package changed. Correct the variable name and wrap the generated test program, then rerun types/lint.

Streaming integration first regression group:47passed/1failed. The no-body-decoding guard accepts bytes/str; new selected-metadata calls supplied bytearray, causing its boundary instrumentation to mark a record malformed and the next token tranche unknown. Prior ext-boundary-error-contracts lookup applies to preserving adapter input shape; keep the original test and convert only bounded selected metadata to bytes before json.loads. Source bodies remain skipped. Stream fixture also has one overlength generated-code line, assigned to its owning worker.
