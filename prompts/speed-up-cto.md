# Reduce cto runtime

Work in /home/example/coding/track-codex-sessions. The user reports that `cto` takes about 22 seconds on every run and wants that time reduced. Diagnose the actual command, implement the smallest safe performance improvement, and verify the result against real data.

## Known context

- Tracked shortcut mapping `/home/example/linux-config/aliases/key_aliases.tmpl:1129` defines `cto "codex-time overview"`. Confirm the live fish mapping and executable path before benchmarking; do not time interactive shell startup as application runtime without distinguishing them.
- Prior work added an on-demand session-status cache and timing-only readers. It did not optimize `overview`, which still needs allowance/model data. Do not assume those earlier picker/status improvements fixed this command.
- Earlier inspection found an installed v4/token-reporting build and live ledger, while the current main checkout accepted ledger v3. Recheck this before selecting implementation and comparison inputs. Never downgrade live data or replace a newer installation with an incompatible checkout. The dirty `.worktrees/incremental-tracking` checkout belongs to separate work; inspect its scope and preserve it rather than overwriting or bundling its changes.
- The workspace has substantial uncommitted prior work. Capture current Git status and preserve all unrelated files/hunks. Existing performance results are historical evidence, not measurements of this reported 22-second run.

## Context files

Read `plans/codex-time-resource-investigation.md`, `tasks/todo.md`, `tasks/lessons.md`, and relevant README usage before changes. Inspect `src/codex_time/cli.py`, `overview.py`, `burn.py`, `model_usage.py`, and `storage.py` as the call graph warrants. Existing watcher-cache details are in `docs/session-status.md`; its latest-message cache is not automatically a suitable overview cache.

## Work

1. Resolve the real `cto` invocation and reproduce the delay. Measure first-run and at least three repeated warm runs with the same command/data. Record dataset sizes and relevant build/schema identity. Separate shell/import overhead, history/journal loading and validation, accounting/report computation, filesystem/process work and rendering. Profile enough to rank the top costs with numbers before designing a fix. Avoid printing conversation bodies or modifying live records during profiling.
2. Choose and explain a targeted optimization from that evidence. Consider avoiding unnecessary data, incremental reads, reusable projections or validated result caching only where justified. Preserve report totals, date/timezone semantics, allowance evidence/reset behavior, CLI options and output formats. Any cache must invalidate correctly when its inputs, options or applicable time boundaries change, recover from corruption/version drift, and publish atomically. Do not trade correctness or fresh results for a lower timing number.
3. Add the defining regression/reproducer first and observe the expected failure. Implement and verify in small steps, including unchanged repeated calls and changed relevant inputs. Run appropriate accounting/report regressions and the project's required checks. Compare optimized output with a full uncached computation on identical stable inputs.
4. Repeat the actual first/warm measurements and report observed before/after timings and the remaining bottleneck. Verify the installed/user-facing command when safe and schema-compatible; otherwise distinguish checkout results from live activation and state the exact remaining integration requirement. Do not claim that `cto` is faster based only on a different source command or incompatible snapshot.
5. Update the active investigation plan with diagnosis, decisions and evidence; keep usage/smoke docs and follow-ups aligned. Deliver code/tests, a concise result, and reproducible direct verification commands under the applicable repository rules.

## Boundaries

Raw rollouts and other files under ~/.codex are read-only except codex-time's own disposable caches. Ask before changing those sources. Preserve durable tracker ledger/journals and unrelated service/process state. Do not delete history, stop other processes, commit, push, or perform an incompatible install. Continue with safe diagnosis and implementation; ask only when an unresolved choice materially affects correctness or authorization. Verify the outcome before claiming success.
