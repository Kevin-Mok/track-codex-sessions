# Continue CTO report optimization

Continue reducing the remaining overview costs while preserving the now-activated v4/token reporting change. Measure first, retain exact output parity, and use the compatible source build.

Work in `/home/kevin/coding/track-codex-sessions`; read `plans/codex-time-resource-investigation.md`, `docs/postmortem/2026-10-14-cto-overview-runtime.md`, and the initial/current dirty state. Preserve unrelated changes and the incremental-tracking worktree. No commit/push or incompatible installation is authorized.

Main remains ledger v3 and must not replace production v4. The fix is already installed from `.worktrees/token-cost-reporting`: `work_period.py` plus the conservative session guards in `model_usage.py`/`burn.py`. Preserve these uncommitted changes and verify source/build identity before further work. Keep complete retained-session waits, model contexts, ownership, uncertainty, allowance reset/conflict evidence, and token child/missing-evidence semantics. Avoid persistent caches or changes to live sources.

Automated checks: full pytest, strict mypy, Ruff, offline package build; the six tests in `tests/test_overview_performance.py` cover historical-session pruning, DST/cross-midnight/unfinished work, unrelated-turn waits and changed input. Run `scripts/verify-overview-performance.py` for exact full JSON parity on frozen actual inputs; also run week and future/DST month cases from smoke docs. Before claiming activation, repeat actual fish-resolved `codex-time overview` first plus three warm invocations, with schema-compatible safe installation only. Activation is complete; the verifier itself uses temporary copies and changes no installation. Actual post-install first/warm times are 22.202 / 23.363 / 24.376 / 23.239 seconds; frozen day-report parity isolates an ~8.2% gain. Full quota/token validation and token/allowance history computation remain targets.

Update matching README, smoke checks, plan, todo and living incident together. Suggested focused commit when explicitly requested: `perf: skip unrelated historical work in overview reports`. Rollback only these scoped source/doc changes; preserve all accounting history.
