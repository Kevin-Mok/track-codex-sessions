# Continue session-cache work

Read the current investigation plan and watcher contract, reproduce the completed cache behavior, and preserve the user's unrelated dirty work. Use the plan's evidence and follow-ups to decide whether any additional change is necessary.

You are working in /home/kevin/coding/track-codex-sessions. Read plans/codex-time-resource-investigation.md, docs/session-status.md, tasks/todo.md and relevant lessons before editing. The merged checkout supports legacy v4 token evidence and the v5 incremental layout. Verify the actual installed build/layout before any activation, and use the stopped-writer migration/rollback guide; do not downgrade production data. The separate dirty incremental-tracking worktree belongs to other work.

The delivered on-demand `status --json` cache stores compact private session state by rollout path, skips unchanged raw files, appends from byte offsets, handles replacement/corruption and publishes atomically. Timing-only CLI paths skip quota history and reuse an unchanged validated ledger in the picker. Full historical persistence/projection costs remain a separate follow-up.

Verify using full pytest, strict mypy, Ruff and a package build. Direct manual checks are `uv run codex-time status --json`, `uv run codex-time status --plain`, and `uv run python scripts/verify-session-status.py`. The last command freezes temporary source copies and compares cached state against a fresh full replay without printing messages. Do not modify any raw rollout or other ~/.codex file; ask first if that becomes necessary. Do not restart/install/commit/push unless requested. Keep docs, smoke checks and the active plan aligned with any related implementation.

Suggested commit subject when a commit is requested: `perf: cache session state and trim startup reads`.
