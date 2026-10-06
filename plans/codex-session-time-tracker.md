# Codex session time tracker

Build a read-only local Codex work-time tracker. Ingest lifecycle history, sample explicit live waits, save content-free JSON, and expose reports and a curses resume picker through an independently running service.

## Purpose and observable outcome

`codex-time` opens a searchable live session list; its daemon counts thinking and tools, subtracts detectable blocking waits, excludes child-agent totals, and survives UI exits and restarts. Reports split by America/Toronto dates and per-turn cwd. Data in ~/.codex-timetrace remains independent of ~/.timetrace and suitable for its own Git repository.

## Context and boundaries

Initial inspection 2026-10-06: this directory is empty and not a Git repository; no dirty files exist. Python 3.12, uv, Codex and timetrace are available. Supplied prompt is the specification. Do not use worktrees, alter Codex threads, persist conversation bodies, touch existing timetrace records, or commit/push automatically. Codex internal adapters must fail visibly for unsupported schemas. Runtime state belongs in XDG_STATE_HOME, separately keyed by data root.

## Settled assumptions and decisions

- Default-mode execution is required by the active harness; Plan Mode cannot be switched with available tools. Maintain this atomic plan instead.
- Pydantic validates versioned JSON at persistence boundaries; typed models define interfaces for parallel work.
- Ledger turns are keyed by session+turn ID. Rebuild native records deterministically after atomic ledger changes, permitting recovery after interruption between writes.
- Completed lifecycle turns are historical upper bounds unless completely observed; unfinished turns count only sampled working coverage. Observation gaps never extend a live timer beyond fresh evidence. Later terminal events reconcile into explicitly uncertain upper bounds.
- Loaded thread reads have includeTurns=false; optional metadata reconciliation uses read-only SQLite, never mutating thread RPCs. No approval response is sent by the observer.
- Explicit names only; synthesized first-prompt SQLite titles are ignored. Content-free fallback is the shortened stable ID.
- No repo initialization/commit is needed for implementation. Installation and service activation are authorized by the specification; preserve recorded data on uninstall.

## Ordered checklist

- [x] Inspect empty workspace, policies, dependencies and protected state.
- [x] Define models and failing accounting/persistence tests; implement interval merging/subtraction, reporting and atomic storage.
- [x] Define failing adapter tests; implement incremental rollouts, schema-detected metadata and existing-socket read-only polling.
- [x] Define failing presentation tests; implement CLI, curses picker, resume and service/setup/check/uninstall scripts.
- [x] Integrate daemon with bounded live coverage, history import and restart recovery.
- [x] Write README, smoke checks and handoff prompt; test native timetrace with isolated config.
- [x] Run pytest, mypy, ruff, build, installed entry point and service verification; perform independent review and final reconciliation.

## Risks, edge cases and rollback

Historical approvals have no reliable timestamps; label upper bounds. Polls approximate wait edges by up to the sampling period and RPC latency; outages increase uncertainty. Preserve readable source ledger rather than inventing crash timestamps. Missing/partial/malformed rollouts and unsupported DB schemas must surface diagnostic codes without copying payloads. Archive moves and duplicate import must be idempotent. Merge waits and same-session work overlaps; split midnight using actual UTC elapsed seconds through DST. Data corruption stops writes instead of repairing silently. Uninstall stops/removes only the user service and app executable, preserving all durable data.

## Exact verification

Write tests before implementation and observe expected missing-behavior RED. Run `uv run pytest`, `uv run mypy src`, `uv run ruff check .`, `uv build`. Use sanitized fixture JSONL and SQLite, real disposable Unix WebSocket server, controllable timestamps, isolated data/state roots. Run `scripts/smoke-test.sh`; it exercises history idempotence, daemon tracking while UI is absent, restart recovery and native readers using an isolated HOME/TIMETRACE_CONFIG. Install with `scripts/setup.sh`, verify `scripts/check.sh` and systemctl --user status, and use an isolated curses PTY smoke check. Manual UI Action/Expected checks live in docs/smoke-tests.md.

## Progress and evidence

Initial inspection: no Git repository, no pre-existing files. Interface preflight: adapters produce sanitized Session/Turn models; accounting consumes them and live Observations; storage owns writes; presentation reads snapshots. Full CLI integration follows those interfaces.

## Review notes

No commits requested. Keep this plan with related implementation if later committed. Independent review will check read-only RPC allowlist, child ancestry exclusion, wait/outage accounting, title privacy, native record types and resume argument/cwd handling.


Milestone evidence: defining accounting/storage/observer/CLI/adapter/presentation RED tests preceded code. All focused suites pass. Independent review reproduced and resolved session-union wait subtraction, naive heartbeat handling and cross-filesystem runtime staging; regression cases passed. Installed service initial history scanned ~5.5GiB, yielding 4,715 sessions / 42,268 turns, and scripts/check.sh reports active + running heartbeat with read-only socket observation. Real fixture daemon/picker/restart and stale-checkpoint recovery passed. Native isolated reader lists both within-minute records and JSON export proves 30,000,000,000ns (30 sec), with original records byte-for-byte unchanged. Remaining final suite/reinstall checks are pending; human approval and five-minute real model checks are documented, not claimed as executed.


Final base-app reconciliation during model-report delivery (2026-10-06): full suite 86 tests, mypy across 14 source files, ruff, source/wheel build and 32 isolated smoke tests passed (exit 0). Actual daemon/UI exit/restart and isolated native readers were exercised again; new model backfill preserves native projection bytes/identity. Reinstalled current packaged sources and verified all 14 modules match; installed command supports model reports and service has a running heartbeat, live_diagnostic None. Model-report plan records v2 backfill, preservation and period-conservation evidence. Human approval/wait and five-minute real-session checks remain manual documented checks, not claimed as executed. No automatic Git initialization, commit or push.
