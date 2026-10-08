# Codex Time

**Know where your Codex hours—and allowance—go.**

Codex Time is a local time tracker for developers running Codex across projects, models and reasoning levels. It turns session history into a clear picture of how long Codex worked, which models handled that work, and how quickly recorded allowance was consumed—so you can compare workloads with evidence instead of guesswork.

Tracking runs automatically in a separate user service, including quiet thinking and tool execution while subtracting detected blocking waits. A searchable terminal picker lets you find and resume sessions. Built around read-only integration, recoverable accounting and content-free timing data, the project shows how to make internal runtime evidence useful without saving conversation bodies.

## At a glance

- **Find your work:** search sessions across projects and resume one with Enter.
- **See where time went:** report working time by date, directory, session, model and reasoning level.
- **Watch your allowance:** see the latest recorded balance and observed percentage points consumed per working hour, with missing evidence made visible.
- **Keep your data:** inspect versioned JSON locally or store it in a separate Git repository.

## Tech stack and why chosen

Python 3.12 keeps the app easy to install and inspect. Curses provides a lightweight Linux session picker, Rich formats responsive allowance reports, websockets reads the existing Codex control socket, and Pydantic validates versioned JSON. The application separates ingestion, live observation, accounting, storage, reports and presentation; JSON remains the source of truth without a proprietary database.

See [smoke tests](docs/smoke-tests.md), the [implementation record](plans/codex-session-time-tracker.md), the [model-usage plan](plans/codex-model-usage-reports.md), and the [Cursor handoff prompt](prompts/codex-model-usage-reports.md). Sanitized fixtures, a real disposable Unix WebSocket server, an actual daemon process, a curses PTY, and native timetrace readers exercise the boundaries. Tests cover waits, concurrency, child exclusion, model switches, history, duplicates, schema drift, restart, Git rollback, midnight and DST.

```text
codex-time                  searchable sessions → Enter to resume
codex-time day              today → repo totals → session durations
codex-time report --all-dirs working time by date, directory and session
codex-time models week      ranked working-time usage by model and reasoning
codex-time burn week        observed allowance points per working hour
```

## From “where did my allowance go?” to a readable answer

Ask for today's tracked workload and the latest recorded weekly allowance balance:

```bash
codex-time burn day --date 2026-10-06 --plain
```

Actual local output captured October 6, 2026 (`--plain` keeps it color-free and easy to copy):

```text
Codex allowance
Tue, Oct 6, 2026  |  America/Toronto
Weekly allowance

58% remaining   42% used
###################-------------
Observed Oct 6, 2:08 PM EDT

0.85 pts / working hour
5 pts matched  |  5h 51m working

Model work
Model        Reasoning   Working        Share of work
gpt-6.1-sol  high         3h 07m   #####-----   53.4%
gpt-6.1-sol  xhigh        1h 29m   ###-------   25.5%
gpt-6-astra  high            34m   #---------    9.7%
gpt-6.1-sol  medium          24m   #---------    7.0%
gpt-6-astra  xhigh           11m   ----------    3.3%
gpt-6-astra  max              4m   ----------    1.1%

18 pts excluded across day boundaries.
Rough estimate | low confidence
Rounded readings can outweigh this rate.
Some working time is estimated.

pts = allowance percentage points; concurrent working hours add.
Model shares describe work, including tools and delegation.
More evidence: --details
```

Here, Sol at high and xhigh accounts for **78.9% of matched working time**. The **0.85 points/hour** rate comes from 5 matched allowance points over 5h 51m of summed root-session work; 18 points across day boundaries are shown separately. Model shares describe the workload, not each model's quota cost, and the rate is a rough observation rather than an hours-remaining forecast.

## Install

Requires Linux, Python 3.12, [uv](https://docs.astral.sh/uv/), an existing Codex installation, and a systemd user manager. No sudo is needed.

```bash
git clone https://github.com/Kevin-Mok/track-codex-sessions.git
cd track-codex-sessions
./scripts/setup.sh
./scripts/check.sh
codex-time
```

Setup rebuilds and installs the local packaged `codex-time` command with uv, including source edits under an unchanged package version, and enables `codex-time.service`. Its first scan may take several minutes for a large history; `systemctl --user is-active codex-time.service` can say active before that scan finishes. `codex-time status` reports a fresh heartbeat once initialization is complete. Restart-on-failure keeps the service independent of the UI. Tracking stops at logout unless the user manager remains running; unobserved time retains uncertainty.

For isolated or alternate installations, pass **absolute** directory paths:

```bash
./scripts/setup.sh --codex-home /absolute/codex-home --data-dir /absolute/time-data --state-dir /absolute/runtime-state --socket /absolute/existing-control.sock
./scripts/check.sh --codex-home /absolute/codex-home --data-dir /absolute/time-data --state-dir /absolute/runtime-state --socket /absolute/existing-control.sock
```

The socket override must point to an already running Codex server. The tracker never starts a server or loads, subscribes to, archives, or modifies threads. Only a deliberate Enter in the picker launches `codex resume SESSION_ID` in that session’s recorded current working directory.

## Daily use

Open `codex-time` from a project directory. The picker initially shows unarchived sessions in that directory with title, cwd, runtime state, latest observed model/reasoning level, today/lifetime work and quality flags. Details show attributed model information; timers keep their own visible line even with long names or paths. A content-free shortened session ID is used when there is no explicit name.

| Key | Action |
| --- | --- |
| Up/Down or j/k | Select a session; scroll details |
| / | Search titles, directories and stable IDs; Enter finishes search |
| a | Toggle current/all directories |
| r | Cycle Active / Archived / All archive filters |
| s | Cycle Updated / Created / Time sorting |
| d | Open/back from interval and daily-total details |
| Enter | Resume the selected session; return to the picker when Codex exits |
| Esc | Leave details or clear search |
| q | Close the picker; tracking continues |

“Active” in the archive filter means unarchived. Runtime working/waiting/idle/unknown is separate. A stale or unavailable socket is shown as unknown, never interpreted from output silence or CPU use. Missing cwd or Codex launch failures appear as actionable notices; terminal settings are restored before launch and on UI exit.

```bash
codex-time list --all-dirs --archive all --sort time --search tracker
codex-time list --json
codex-time report --all-dirs --archive all --from 2026-10-01 --to 2026-10-31
codex-time report --session SESSION_ID --all-dirs --json
codex-time --timezone America/Toronto report --cwd /absolute/project
codex-time status --json
```

Global options precede the subcommand: `--codex-home`, `--data-dir`, `--state-dir`, `--socket`, and `--timezone`. No subcommand opens the UI. The `list` and `report` commands select the current directory and unarchived sessions by default; directory reports count only intervals attributed to that directory, including a session that has since resumed elsewhere. Date endpoints are inclusive. `--timezone` changes display/report dates; native record directories always use America/Toronto.

### Daily repo and session time

See the day's total working time, then each repo/directory with its share of the day and the sessions that contributed. Directories and sessions rank by working duration, so the largest blocks appear first.

```bash
codex-time day
codex-time day --date 2026-10-06
codex-time day --date 2026-10-06 --cwd /absolute/project
codex-time day --session SESSION_ID --details
codex-time day --plain
codex-time day --json
```

From a source checkout, use `uv run codex-time day`; run `./scripts/setup.sh` to update the installed command. Today uses the selected `--timezone` (America/Toronto by default). Unlike `list` and `report`, `day` includes **all directories and archive states** by default; `--archive active|archived|all` narrows that scope. `--cwd` selects an exact recorded working directory, rather than inferring Git roots or combining subdirectories.

A directory-share summary at the top shows progress bars, percentages and working durations before the session details.

Each directory shows its full path, total duration and percentage of the selected day's work. Its indented sessions show title, stable ID and duration **in that directory on that day**. A session resumed elsewhere can appear under both directories, with each portion counted once. Empty days say that no work was recorded. Long paths and titles wrap while time values remain visible in narrow terminals.

The same wait-subtracted root-session accounting powers the existing reports: concurrent roots add, child agents add no separate time, and local midnight/DST determine the day's boundaries. These values measure recorded Codex work rather than exact human attention. `--details` exposes quality flags and diagnostics; `--plain` is ASCII and color-free. `--color auto|always|never`, `NO_COLOR` and piped output follow the allowance report's conventions. JSON carries exact `total_microseconds` at day, directory and session levels; their sums conserve the total. Whole-second durations round down for display; positive subsecond work remains visible, such as `0.25s`.

### Model working-time usage

Rank daily, weekly or monthly usage by exact model ID and reasoning level:

```bash
codex-time models day
codex-time models week --date 2026-10-06
codex-time models month --date 2026-10-06 --cwd /absolute/project --archive active
codex-time models week --model-only --json
codex-time models month --date 2026-10-06 --csv
codex-time --timezone America/Toronto models day --date 2026-10-06
```

These commands default to the current calendar period in America/Toronto, across all directories and archive states. Weeks begin Monday; months use calendar boundaries. `--date YYYY-MM-DD` selects the containing period. `--cwd PATH` filters the original directory of each counted interval; `--archive active|archived|all` defaults to `all`. `--model-only` combines reasoning levels. The default terminal table and mutually exclusive `--json`/`--csv` exports share the same totals and rows.

Known model/reasoning rows rank by descending working duration with deterministic ties. Each row includes rank, exact model ID, reasoning level, duration, percentage, distinct contributing session count and quality indicators. Unknown model time appears separately without a rank and remains in the total and percentage denominator. The sum of all rows equals the existing root-session report total with matching dates, timezone, directory and archive filters. Concurrent roots count independently; children add no model-report time.

Attribution comes from recorded rollout `turn_context.model` and `turn_context.effort`, tied to stable session/turn IDs. The first context applies from that turn's start; later changes split counted time at their recorded timestamps. Reimported context evidence is deduplicated; repeated settings do not split usage. Distinct observation timestamps remain available to detect conflicting evidence. Missing fields stay Unknown, and unresolved conflicts stay Unknown with a content-free diagnostic. Current SQLite settings never supply historical model attribution. This measures working-time usage, including tools and delegated work; it does not measure model efficiency or output quality.

Exports include exact integer `working_microseconds` per row and `total_microseconds` for conservation checks. The matching session report also includes `total_microseconds`. Seconds fields are converted once from these counters; use integer units when aggregating in software to avoid binary floating-point artifacts. Sampling uncertainty is conservative per contributing turn and is not additive across model rows.

Historical import happens automatically. To force a complete reconciliation, stop the single writer first:

```bash
systemctl --user stop codex-time.service
codex-time import-history
systemctl --user start codex-time.service
```

Repeating import or restarting cannot add duplicate turns or records. Session identity survives renames and resumes; per-turn cwd stays with the original work. Concurrent root-session totals may exceed elapsed clock time. Child agents appear as excluded and contribute no additional totals.

### Allowance burn tracking

The observer automatically saves allowance readings from available rollout history and subsequent events. Inspect account-wide consumption alongside the root workload that was active between readings:

```bash
codex-time burn day
codex-time burn week --date 2026-10-06
codex-time burn day --details
codex-time burn day --plain
codex-time burn month --date 2026-10-06 --csv
codex-time --timezone America/Toronto burn week --date 2026-10-06 --json
codex-time burn week --window-minutes 10080 --limit-id codex --max-gap-seconds 600
```

Defaults are the current calendar period in America/Toronto, Monday weeks, the `codex` limit, its 10,080-minute weekly window, and a maximum 600-second observation gap. `--date` selects the containing period; `--json` and `--csv` are mutually exclusive. All directories and archive states contribute; concurrent roots sum and children add no working hours.

The terminal view puts remaining allowance and observed burn rate first, with a usage bar, readable working durations, local timestamps, and aligned model/reasoning work shares. Short accuracy notes explain excluded consumption. `--details` adds reset identifiers, raw quality flags and rounding sensitivity. `--color auto|always|never` controls terminal colors; automatic mode respects `NO_COLOR` and omits ANSI colors when piped. `--plain` provides an ASCII, color-free view. JSON and CSV retain the same full report data.

Manual reset identity changes start fresh baselines; five-second reset jitter stays within a cohort, and stale lower readings are skipped. Percentage increases across long gaps, dates or intervals without counted root work are exposed as exclusions. Missing readings yield insufficient evidence, rather than a zero burn rate. The quota is shared across activity, so a model mix describes the workload rather than assigning the account's consumption to individual models.

See [reproducible allowance tracking](docs/model-burn-tracking.md), [its implementation record](plans/codex-model-burn-tracking.md), and [the maintenance handoff](prompts/codex-model-burn-tracking.md) for collection, export, calculation and comparison steps. These are low-confidence workload estimates; missing or external consumption and coarse percentage readings limit forecasts.

## Accuracy and recovery

Work begins at `task_started` and ends at completion, failure or interruption. Completed history merges overlapping work and blocking waits. Persisted blocking `request_user_input` calls are matched to answer/output timestamps; asynchronous questions do not pause work. Live polling pauses explicit `waitingOnApproval` and `waitingOnUserInput` states, regardless of quiet thinking or tool execution.

These values describe evidence rather than exact human-attention measurements:

| Indicator | Meaning |
| --- | --- |
| `historical_upper_bound` | Lifecycle duration minus known waits; historical approval timestamps are unavailable |
| `sampled_waits_1s` | Live wait boundaries sampled about once per second; numeric uncertainty includes observed sample spacing and read latency |
| `unfinished_observed_only`, `unfinished` | Only bounded observed working coverage contributes; no invented end timestamp |
| `observation_gap` | Socket outage, long polling gap or daemon restart affected observation |
| `live_sample_estimate` | UI adds at most a fresh three-second display estimate; durable records use closed evidence |
| `metadata_cwd_estimate`, `metadata_reconciled` | Read-only SQLite fallback provided directory/timing evidence |
| `no_lifecycle_events` | Old or unsupported history cannot safely supply turn durations |
| `child_excluded` | Parent already includes this child’s work |

Historical approval waits may make completed totals too large. Polling can miss waits shorter than its sampling interval, and large imports/slow I/O can increase gaps. Unknown or stale unfinished turns never accumulate indefinitely. Later terminal events can replace incomplete observed coverage with an explicitly uncertain lifecycle upper bound, so totals can increase after recovery. Quality flags remain visible in the list, details, reports and ledger. No total is advertised as exact.

Diagnostics omit payload bodies. Malformed complete JSONL lines are skipped visibly, partial final writes wait for completion, archive moves keep identity, and unsupported database schemas retain usable rollout evidence. A corrupt durable ledger or quota journal blocks writes; restore a valid backup after stopping the service. Version 1 and 2 ledgers upgrade automatically to version 3 while preserving recorded timing/waits and model evidence; old ingestion offsets are invalidated once so available history backfills model metadata and numeric allowance readings. Missing source files retain recorded work and saved model/quota evidence; work without model evidence stays Unknown. Later scans remain incremental. Runtime caches are disposable; a ledger fingerprint invalidates stale offsets after a Git restore. Restart rebuilds native projections from the valid ledger.

Integration is verified with installed Codex 0.160.1 schemas. Codex storage is internal and may change. The socket adapter uses [documented app-server initialization and thread lookup](https://learn.chatgpt.com/docs/app-server); it restricts itself to initialize, initialized, thread/loaded/list and thread/read with includeTurns=false. It sends no approval responses.

## Data and Git

Default durable store: `~/.codex-timetrace`. Existing `~/.timetrace` is preserved.

```text
~/.codex-timetrace/
  ledger.json                 versioned sessions, turns, model contexts, waits and quality
  quota-observations.jsonl     append-only validated allowance readings
  projects/<cwd-hash>.json     native timetrace projects
  records/YYYY-MM-DD/          deterministic codex-time-<interval-hash>.json files
```

Closed segments use RFC3339 timestamps and native `start`, `end`, `project:{key}`, `is_billable:false`, and session/turn tags. Filenames include stable identity and exact boundaries, so simultaneous sessions and multiple intervals in a minute cannot collide. Records split at Toronto midnight; elapsed seconds use UTC through DST.

Checkpoints and heartbeat live under `$XDG_STATE_HOME/codex-time/<data-root-hash>` (default `~/.local/state`). A per-data-root writer lock lives under `~/.local/state/codex-time/locks`. Atomic durable writes stage beside the data root; runtime staging stays in runtime storage. None of these files belongs in the data repository. Model attribution stores only model IDs, reasoning levels, timestamps and provenance. Allowance tracking stores only allowlisted usage/window/reset numbers, timestamps, limit/plan labels and source identity/provenance; raw quota payloads are omitted. No conversation bodies, answers, tool output, auth data or credentials are persisted. Explicit session names and directory paths remain personal metadata; review them before sharing.

Use a separate Git repository inside the data root. Stop the daemon for a consistent snapshot, review `ledger.json`, `quota-observations.jsonl`, `projects/` and `records/`, then commit with your own workflow and restart. Git restore/pull also requires stopping the service first and restoring the ledger and quota journal together. Never merge JSON ledgers mechanically while tracking is running. The app does not initialize repositories, commit, push or synchronize code or data.

Native timetrace **list/report readers** are compatible with an explicitly configured separate store. Native list displays project keys and minute labels even when distinct records occur within a minute. Minute-key editing/deleting and native single-timer start/stop commands are unsupported for tracker data: they cannot address its unique filenames and can conflict with projections. [Native storage source](https://github.com/dominikbraun/timetrace/blob/v0.14.3/fs/fs.go) documents reader behavior. The reusable compatibility check runs only in a disposable HOME and config, never against your existing records.

## Development and verification

```bash
uv sync --python 3.12
uv run pytest
uv run mypy src
uv run ruff check .
uv build
./scripts/smoke-test.sh
```

The smoke script needs no sudo and changes only temporary fixtures. Native-reader verification is skipped if timetrace is missing or a system-wide config prevents assured isolation. See [Action/Expected checks](docs/smoke-tests.md) for human approval and silent-tool tests using normal Codex sessions.

## Rollback

```bash
./scripts/uninstall.sh
```

Uninstall has no configurable options; `--help` shows its summary. It stops/disables the user service, removes its unit and uv-installed app, and preserves recorded data and runtime state. A reinstall of this version can read the existing ledger. Older versions cannot read v3; rolling back to them requires their matching pre-upgrade ledger backup while the service is stopped. Stopping `codex-time.service` alone pauses observation without changing Codex. Keep matching plans and documentation with implementation changes.
