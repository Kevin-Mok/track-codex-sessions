# Reduce codex-time overview startup time

Make the actual installed `codex-time overview` substantially faster. Measure its bottleneck, implement the smallest effective improvement (caching or another method), and verify speed and report correctness end to end.

## User evidence and scope

The user ran `codex-time overview` from `~/linux-config` on Ubuntu. It repeatedly printed `Reading overview report` with elapsed times of 2, 4, 6, 9, 11, 14, 17, 19, 21 and 23 seconds. The eventual completion time was not supplied. The user considers this delay unacceptable and explicitly requests implementation through this fresh execution task.

Work in `/home/kevin/coding/track-codex-sessions`. Preserve existing reports, accounting, privacy and durable data. Keep Ponytail full mode: reuse existing machinery, avoid new dependencies and speculative features, and finish the smallest complete fix. No commit or push was requested.

## Required context

Follow `/home/kevin/linux-config/dot_codex/AGENTS.md` and applicable local instructions under normal permissions. Read these referenced files before selecting an approach:

- `README.md`, `tasks/lessons.md`, `plans/codex-time-resource-investigation.md`.
- `docs/postmortem/2026-10-14-cto-overview-runtime.md` and `docs/postmortem/2026-10-14-codex-time-session-cache.md`.
- `src/codex_time/cli.py`, `src/codex_time/overview.py`, `src/codex_time/overview_output.py` and their actual storage/report dependencies.
- `tests/test_overview_performance.py`, `scripts/verify-overview-performance.py`, `docs/session-status.md`, `docs/smoke-tests.md`.

Historical evidence, to recheck: the earlier overview optimization improved frozen warm timings only about 8%, leaving runs around 22–24 seconds; import/rendering were small costs relative to historical validation and accounting. The session-status cache serves another command. Source main and the installed token-aware build previously used different ledger schemas (v3 versus v4). These are investigation leads, not current-state guarantees or reasons to repeat completed work.

## Execution and acceptance

1. Identify the invoked executable, interpreter, installed source/build, data schema and suitable existing checkout. Preserve unrelated changes and separate worktrees. Reconcile the existing plan with this request.
2. Measure actual command completion and time to useful output: first invocation and at least three repeated invocations on the same representative inputs. Separate import, loading, computation and rendering costs. Use unprofiled wall timings for conclusions; profile only to locate costs. Do not label the first process run a cold filesystem-cache run without evidence.
3. Add a defining failing regression or executable reproducer at the measured seam before implementation. Choose the simplest approach that removes substantial repeated work; consider existing disposable storage/index/cache mechanisms before introducing another cache. Do not merely suppress progress or defer the same blocking work.
4. If caching is chosen, validate its format and all semantic input dependencies, avoid expensive full rereads merely to check freshness, and handle missing/corrupt/incompatible caches and concurrent publication safely. New/changed work, quota/token/FX evidence, report options and time-sensitive boundaries must remain correct. Use isolated copies for mutation tests; never edit live tracking inputs or conversation history.
5. Implement and verify exact full-report parity on frozen inputs, focused regressions and relevant broader checks. Exercise default, JSON and plain output, relevant periods/filters, changed-input freshness and cache recovery if applicable. Extend existing verification helpers only as needed; verify their build assumptions first.
6. Verify the improvement through the actual installed command when compatible activation is permitted. Preserve token reporting and existing data schemas; never install an incompatible checkout over live data. Record any blocked activation and distinguish source/temporary-overlay speed from user-visible installed speed.
7. Update the relevant plan, user docs/smoke checks and required incident learning with fresh evidence. Report comparable before/after timings, build/input identity, correctness checks, remaining costs, activation status and rollback. Aim for near-immediate repeated reports where feasible; report actual measured results and limitations rather than inventing a latency guarantee.

Complete the implementation and verification, not just recommendations. Report this saved prompt path and the three highest-value direct verification commands required by repository guidance. Do not recompile this prompt or invoke metaprompt-run again.
