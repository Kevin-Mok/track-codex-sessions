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
