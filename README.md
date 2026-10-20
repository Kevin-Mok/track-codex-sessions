# Codex Time

**Know where your Codex hours, tokens and allowance go.**

Codex Time is a local time tracker for developers running Codex across projects, models and reasoning levels. It turns session history into a clear picture of how long Codex worked, which models handled that work, how quickly recorded allowance was consumed, and what recorded tokens would cost at today's Standard API rates in USD and CAD—so it helps developers compare workloads with evidence instead of guesswork.

Tracking runs automatically in a separate user service, including quiet thinking and tool execution while subtracting detected blocking waits. A searchable terminal picker lets you find and resume sessions. Built around read-only integration, recoverable accounting and content-free timing and token evidence, the project keeps durable timing data free of conversation bodies. A separate private, disposable status cache stores the latest user and assistant messages for local watchers.

## Tech Stack And Why Chosen

Bash keeps installation, service checks and smoke checks reproducible through the repository scripts. Python 3.12 keeps the app easy to install and inspect. Curses provides a lightweight Linux session picker, Rich formats responsive overview, daily, model and allowance reports, websockets reads the existing Codex control socket, and Pydantic validates versioned JSON. SQLite supplies disposable exact indexes and ijson streams large migrations; portable JSON and evidence journals remain authoritative. The application separates ingestion, live observation, accounting, storage, reports and presentation; JSON remains the source of truth; the daemon caches eight sessions and retrieves historical evidence from disk. Decimal arithmetic preserves exact token-cost estimates, and a bounded background Bank of Canada check supplies cached CAD conversion.

See [smoke tests](docs/smoke-tests.md), the [implementation record](plans/codex-session-time-tracker.md), the [model-usage plan](plans/codex-model-usage-reports.md), the [overview plan](plans/overview-command-layout.md), the [token/cost guide](docs/token-cost-reporting.md), the [token/cost plan](plans/codex-token-cost-reporting.md), and the [Cursor handoff prompt](prompts/codex-token-cost-reporting.md). Sanitized fixtures, a real disposable Unix WebSocket server, an actual daemon process, a curses PTY, and native timetrace readers exercise the boundaries. Tests cover waits, concurrency, child exclusion, model switches, history, duplicates, schema drift, restart, Git rollback, midnight and DST.

## At a glance

- **Find your work:** search sessions across projects and resume one with Enter.
- **See where time went:** report working time by date, directory, session, model and reasoning level.
- **Watch your allowance:** see the latest recorded balance and observed percentage points consumed per working hour, with missing evidence made visible.
- **Compare API costs:** see tokens and Standard API estimates by actual model, root session and recorded directory, including descendants once.
- **Keep your data:** inspect versioned JSON locally or store it in a separate Git repository.

```text
codex-time                       searchable sessions → Enter to resume
codex-time overview              today → tokens/API cost → allowance → model work
codex-time projects              today → directories → sessions → model tokens/cost
codex-time history --all-dirs     working time by date, directory and session
codex-time model-time week       ranked working time by model and reasoning
codex-time allowance week        allowance balance and observed consumption rate
```

## From “where did my allowance go?” to a readable answer

Use `codex-time overview` for today's allowance and recorded model work in one report. The dedicated allowance report below shows the evidence used to calculate an observed consumption rate:

```bash
codex-time allowance day --date 2026-10-06 --plain
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

Setup rebuilds and installs the local packaged `codex-time` command with uv, including source edits under an unchanged package version, and enables `codex-time.service`. Its first versioned storage migration verifies a pre-migration backup, partitions timing by session, and builds disposable indexes and native projections in a short-lived worker before live tracking starts. This can take several minutes for a large history; `systemctl --user is-active codex-time.service` can say active before that scan finishes. `codex-time health` reports a fresh heartbeat once initialization is complete. Restart-on-failure keeps the service independent of the UI. Tracking stops at logout unless the user manager remains running; unobserved time retains uncertainty.

For isolated or alternate installations, pass **absolute** directory paths:

```bash
./scripts/setup.sh --codex-home /absolute/codex-home --data-dir /absolute/time-data --state-dir /absolute/runtime-state --socket /absolute/existing-control.sock
./scripts/check.sh --codex-home /absolute/codex-home --data-dir /absolute/time-data --state-dir /absolute/runtime-state --socket /absolute/existing-control.sock
```

The socket override must point to an already running Codex server. The tracker never starts a server or loads, subscribes to, archives, or modifies threads. Only a deliberate Enter in the picker launches `codex resume SESSION_ID` in that session’s recorded current working directory.

## Daily Use And CLI Commands

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
codex-time sessions --all-dirs --archive all --sort time --search tracker
codex-time sessions --json
codex-time history --all-dirs --archive all --from 2026-10-01 --to 2026-10-31
codex-time history --session SESSION_ID --all-dirs --json
codex-time --timezone America/Toronto history --cwd /absolute/project
codex-time health --json
```

| Command | Purpose |
| --- | --- |
| `overview [day\|week\|month\|all]` | Tokens/API cost, allowance and model work; defaults to today |
| `allowance day\|week\|month` | Allowance balance and observed consumption rate |
| `model-time day\|week\|month` | Model and reasoning working-time rankings |
| `projects [day\|week\|month\|all]` | Directory/session/model tokens, costs and durations |
| `sessions` | Search and list sessions |
| `history` | Working-time report over an inclusive date range |
| `status --json` | Cached per-session lifecycle state and latest messages for local watchers |
| `health` | Tracker health and accuracy diagnostics |
| `resume` | Open the session picker |

`codex-time` without arguments also opens the picker. `daemon` defaults to 60-second live sampling and display refresh; `daemon --sample-seconds N` permits intervals greater than zero and at most 60. `health --plain` prints ASCII status; `health --json` preserves clean machine output. `import-history` remains an explicit full reconciliation. Existing scripts can keep using the silent aliases `burn` → `allowance`, `models` → `model-time`, `day` → `projects`, `list` → `sessions`, and `report` → `history`. Their existing arguments, defaults, report fields and exit codes are preserved; overview/projects JSON adds token and pricing fields; top-level help advertises the canonical names. `status` now returns per-session state alongside observer-health fields; its `sessions` value is an array. Use `health` for the previous numeric session-count contract. See [the watcher guide](docs/session-status.md) for freshness, lifecycle semantics, privacy and the cache format.

Global options precede the subcommand: `--codex-home`, `--data-dir`, `--state-dir`, `--socket`, and `--timezone`. The `sessions` and `history` commands select the current directory and unarchived sessions by default; directory reports count only intervals attributed to that directory, including a session that has since resumed elsewhere. Date endpoints are inclusive. `--timezone` changes display/report dates; native record directories always use America/Toronto.

### Combined allowance and model work

Start with a single report for today, or choose a calendar week, month or all recorded history:

```bash
codex-time overview
codex-time overview week --date 2026-10-06
codex-time overview month --details
codex-time overview all
codex-time overview --plain
codex-time overview --json
codex-time --timezone America/Toronto overview day --date 2026-10-06
codex-time overview week --window-minutes 10080 --limit-id codex --max-gap-seconds 600
```

The report shows a readable date/timezone and recorded working duration, followed by token totals and estimated API costs by model, allowance balance, observed consumption and ranked model working-time totals. Reasoning rows sit beneath each model. Model and reasoning shares use **all recorded work in the selected period**, including Unknown attribution; each model's session count is the distinct union of its contributing sessions. Reasoning-row session counts can overlap and must not be added together.

Allowance rates use **only work matched to qualifying allowance readings**. The report shows matched percentage points and duration, excluded consumption, and a short confidence warning; the matched duration can differ from the recorded-work total. Missing readings stay explicit, and separate reset cohorts retain their own readable date/reset labels. Model shares describe work, including tools and delegation, rather than each model's quota cost.

Overview skips historical work proven outside the selected period, including token-coverage reconstruction. On partitioned storage it can read validated evidence from the daemon’s existing SQLite index in a read-only transaction when the published source identity matches; missing, stale, corrupt or incompatible indexes fall back to the authoritative journals. All pre-period quota history is retained for reset/conflict accounting. All-time and legacy-storage cache misses use full loading.

Unchanged reports reuse a private, disposable `overview-report.json` under the selected runtime directory. File identities cover every session snapshot, journal, layout, FX and package/pricing source; calendar date, timezone and allowance options also participate. New evidence or restored files invalidates the cache immediately. JSON, plain, details and color views share the same accounting cache; FX age/stale metadata is refreshed on each hit. Reports whose inputs change during computation are returned without publishing a cache entry. Removing only this runtime cache forces a rebuild; never edit tracking history to refresh a report. Continuously changing inputs can still require several seconds of fresh computation.

Run `python3 scripts/verify-overview-performance.py` for frozen-input, exact full-JSON parity and first/repeated timings against the installed build. It freezes the actual legacy or partitioned layout, prepares an index only on temporary copies, and uses a compatible package overlay. It never activates an installation, restarts a daemon or changes live data. The merged checkout supports legacy v4 ledgers and the v5 incremental layout; use the documented stopped-writer migration and rollback workflow for a storage upgrade.

`overview` uses all directories and archive states. Use `projects`, `model-time`, `sessions` or `history` for filtered reports. `--date YYYY-MM-DD` selects the containing period, weeks start Monday, and the selected global `--timezone` defines boundaries. Allowance defaults are the `codex` limit, its 10,080-minute weekly window and a maximum 600-second observation gap.

`--details` reveals technical flags, uncertainty, matched model mixes and diagnostics. `--plain` is ASCII without color; `--color auto|always|never` respects `NO_COLOR`, and automatic output omits color when piped. `--json` emits a clean object with `token_usage`, `allowance`, `model_totals` and `reasoning`, each containing the full existing report schema. Overview has no CSV export; the dedicated reports retain their existing JSON/CSV contracts. The token section exports exact integer categories, Decimal USD/CAD strings, coverage, hierarchy, the versioned price catalog and one cached FX snapshot. All sections use one loaded ledger snapshot, and report commands leave recorded data unchanged.

### Daily repo and session time

See the day's total working time, then each repo/directory with its share of the day and the sessions that contributed. Directories and sessions rank by working duration, so the largest blocks appear first.

```bash
codex-time projects
codex-time projects --date 2026-10-06
codex-time projects --date 2026-10-06 --cwd /absolute/project
codex-time projects --session SESSION_ID --details
codex-time projects --plain
codex-time projects --json
```

From a source checkout, use `uv run codex-time projects`; run `./scripts/setup.sh` to update the installed command. Today uses the selected `--timezone` (America/Toronto by default). Unlike `sessions` and `history`, `projects` includes **all directories and archive states** by default; `--archive active|archived|all` narrows that scope. `--cwd` selects an exact recorded working directory, rather than inferring Git roots or combining subdirectories.

The compact directory table puts working time, share, tokens and estimated USD/CAD costs side by side. Session rows follow in the same order, with each model visible. A sole model shares its session row when the totals agree; multiple models keep their own cost rows. An asterisk marks a known priced subtotal, and unavailable or unpriced evidence is labelled explicitly.

Each session group shows the full directory path once. Rows retain every session title, model and duration **in that directory on that day**; `--details` adds full stable IDs, token categories, child contributions and provenance. Duplicate directory names use their full paths in the summary. A session resumed elsewhere can appear under both directories, with each portion counted once. Empty days say that no work was recorded. Wide terminals use aligned numeric columns (up to 160 columns). Narrow terminals stack labelled metrics and wrap complete paths and titles without hiding time or costs.

The same wait-subtracted root-session accounting powers the existing reports: concurrent roots add, child agents add no separate time, and local midnight/DST determine the day's boundaries. These values measure recorded Codex work rather than exact human attention. `--details` exposes quality flags and diagnostics; `--plain` is ASCII and color-free. `--color auto|always|never`, `NO_COLOR` and piped output follow the allowance report's conventions. JSON carries exact `total_microseconds` at day, directory and session levels; their sums conserve the total. Whole-second durations round down for display; positive subsecond work remains visible, such as `0.25s`.

### Model working-time usage

Rank daily, weekly or monthly usage by exact model ID and reasoning level:

```bash
codex-time model-time day                    # split by model and reasoning level
codex-time model-time day --model-only       # combine reasoning levels per model
codex-time model-time week --model-only
codex-time model-time day --details          # timing evidence and diagnostics
codex-time model-time day --plain            # ASCII without color
codex-time model-time week --date 2026-10-06
codex-time model-time month --date 2026-10-06 --cwd /absolute/project --archive active
codex-time model-time week --model-only --json
codex-time model-time month --date 2026-10-06 --csv
codex-time --timezone America/Toronto model-time day --date 2026-10-06
```

These commands default to the current calendar period in America/Toronto, across all directories and archive states. Weeks begin Monday; months use calendar boundaries. `--date YYYY-MM-DD` selects the containing period. `--cwd PATH` filters the original directory of each counted interval; `--archive active|archived|all` defaults to `all`. `--model-only` combines reasoning levels. The default terminal table and mutually exclusive `--json`/`--csv` exports share the same totals and rows.

Known model/reasoning rows rank by descending working duration with deterministic ties. Each row includes rank, exact model ID, reasoning level, readable duration, percentage and distinct contributing session count. Emoji cues, share bars and readable dates make the default view easy to scan; narrow terminals and long names use stacked rows. `--model-only` omits the redundant reasoning column. Quality indicators and raw diagnostics appear with `--details`, while a short accuracy note remains visible by default. `--plain` produces ASCII without color; `--color auto|always|never` respects `NO_COLOR`, and automatic color is disabled when piped. Unknown model time appears separately without a rank and remains in the total and percentage denominator. The sum of all rows equals the existing root-session report total with matching dates, timezone, directory and archive filters. Concurrent roots count independently; children add no model-report time.

Attribution comes from recorded rollout `turn_context.model` and `turn_context.effort`, tied to stable session/turn IDs. The first context applies from that turn's start; later changes split counted time at their recorded timestamps. Reimported context evidence is deduplicated; repeated settings do not split usage. Distinct observation timestamps remain available to detect conflicting evidence. Missing fields stay Unknown, and unresolved conflicts stay Unknown with a content-free diagnostic. Current SQLite settings never supply historical model attribution. This measures working-time usage, including tools and delegated work; it does not measure model efficiency or output quality.

Exports include exact integer `working_microseconds` per row and `total_microseconds` for conservation checks. The matching session report also includes `total_microseconds`. Seconds fields are converted once from these counters; use integer units when aggregating in software to avoid binary floating-point artifacts. Sampling uncertainty is conservative per contributing turn and is not additive across model rows.

Historical import happens automatically. To force a complete reconciliation, stop the single writer first:

```bash
systemctl --user stop codex-time.service
codex-time import-history
systemctl --user start codex-time.service
```

Repeating import or restarting cannot add duplicate turns or records. Session identity survives renames and resumes; per-turn cwd stays with the original work. Concurrent root-session totals may exceed elapsed clock time. Child agents appear as excluded and contribute no additional totals.

### Token costs, currencies and history

`cto` already runs `codex-time overview`; its report now includes token usage. Use `codex-time projects week`, `projects month` or `projects all` for directory → root session → actual model totals. Both commands default to today, use the selected timezone and Monday weeks, and reject `all --date`. All-time overview shows the latest recorded allowance snapshot without an all-time consumption rate.

```bash
codex-time projects all --plain
codex-time projects week --date 2026-10-06 --cwd /absolute/project --archive all
codex-time projects month --session SESSION_ID --details
codex-time overview all --json
./scripts/token-smoke.py --scenario verify
```

Replace `SESSION_ID` and `/absolute/project` with real values. Directory filters use each observation's recorded cwd; root-session filters include descendants. Selecting a child ID selects its own observations. Archive filtering follows the root, with orphan children kept visible. Child tokens add consumption once; child elapsed time adds no extra work. Unfinished sessions with tokens remain visible even with zero recorded duration.

Amounts are labelled **Estimated API token cost — Standard**. The bundled [versioned catalog](src/codex_time/pricing-v1.json) records exact model IDs, official source URLs and verification dates (October 8, 2026). One present-rate card applies to all selected history; this is not invoice reconstruction. Cached input and cache writes are input subsets, reasoning is already in output, and long-context tiers require proven request input size. The exact internal model `codex-auto-review` is excluded from token/cost totals and model breakdowns; its stored evidence and working-time accounting are retained. Other unknown models, missing billing evidence and counters after uncertain resets remain explicit. Incomplete coverage shows a **known priced subtotal**, with unpriced tokens and diagnostic reasons under `--details`. Tool fees, hosting, taxes, regional uplifts and other non-token charges are excluded.

CAD uses one cached Bank of Canada USD→CAD observation for the entire report. The daemon checks asynchronously with bounded timeouts, waits at least one hour after an attempt and 24 hours after a successful check, and retains the last valid rate on failure. Reports show the observation date and age. Without a valid rate, USD remains available and CAD is unavailable. Report commands never fetch rates or write data; slow report reads emit periodic elapsed-time status on stderr, keeping JSON stdout clean. Overview and projects loading messages start with ⏳ unless `--plain` is selected. After refreshing the installed package, run `codex-time overview` directly from any directory; `uv run` is unnecessary and does not update an older installed package.

The v4 ledger keeps content-free usage in `usage-observations.jsonl`. The next daemon start ignores v3 rollout offsets and backfills available historical tokens; repeated imports do not add duplicates. Progress goes to stderr/service logs. Preserve a full data-directory and runtime-state backup before upgrading, then use the normal `./scripts/setup.sh` package refresh; custom installations must pass their existing path/socket options. Read [migration and rollback details](docs/token-cost-reporting.md) before restoring older data or executables. The isolated smoke script accepts `--executable PATH` and `--scenario verify|normal|narrow|overview|filtered|json|missing`; it creates temporary synthetic history, never touches personal records, and uses no network.

### Allowance balance and consumption

The observer automatically saves allowance readings from available rollout history and subsequent events. Inspect account-wide consumption alongside the root workload that was active between readings:

```bash
codex-time allowance day
codex-time allowance week --date 2026-10-06
codex-time allowance day --details
codex-time allowance day --plain
codex-time allowance month --date 2026-10-06 --csv
codex-time --timezone America/Toronto allowance week --date 2026-10-06 --json
codex-time allowance week --window-minutes 10080 --limit-id codex --max-gap-seconds 600
```

Defaults are the current calendar period in America/Toronto, Monday weeks, the `codex` limit, its 10,080-minute weekly window, and a maximum 600-second observation gap. `--date` selects the containing period; `--json` and `--csv` are mutually exclusive. All directories and archive states contribute; concurrent roots sum and children add no working hours.

The terminal view puts remaining allowance and observed burn rate first, with a usage bar, readable working durations, local timestamps, and aligned model/reasoning work shares. Short accuracy notes explain excluded consumption. `--details` adds reset identifiers, raw quality flags and rounding sensitivity. `--color auto|always|never` controls terminal colors; automatic mode respects `NO_COLOR` and omits ANSI colors when piped. `--plain` provides an ASCII, color-free view. JSON and CSV retain the same full report data.

Manual reset identity changes start fresh baselines; ten-second reset jitter stays within a cohort, and stale lower readings are skipped. Percentage increases across long gaps, dates or intervals without counted root work are exposed as exclusions. Missing readings yield insufficient evidence, rather than a zero burn rate. The quota is shared across activity, so a model mix describes the workload rather than assigning the account's consumption to individual models.

See [reproducible allowance tracking](docs/model-burn-tracking.md), [its implementation record](plans/codex-model-burn-tracking.md), and [the maintenance handoff](prompts/codex-model-burn-tracking.md) for collection, export, calculation and comparison steps. These are low-confidence workload estimates; missing or external consumption and coarse percentage readings limit forecasts.

## Accuracy and recovery

Work begins at `task_started` and ends at completion, failure or interruption. Completed history merges overlapping work and blocking waits. Persisted blocking `request_user_input` calls are matched to answer/output timestamps; asynchronous questions do not pause work. Live polling pauses explicit `waitingOnApproval` and `waitingOnUserInput` states, regardless of quiet thinking or tool execution.

These values describe evidence rather than exact human-attention measurements:

| Indicator | Meaning |
| --- | --- |
| `historical_upper_bound` | Lifecycle duration minus known waits; historical approval timestamps are unavailable |
| `sampled_waits_60s` | New live boundaries sampled about once per minute; numeric uncertainty includes actual spacing and read latency |
| `sampled_waits_1s` | Retained legacy evidence or explicitly configured one-second sampling |
| `unfinished_observed_only`, `unfinished` | Only bounded observed working coverage contributes; no invented end timestamp |
| `observation_gap` | Socket outage, long polling gap or daemon restart affected observation |
| `live_sample_estimate` | UI extends a fresh sample for display only, up to 75 seconds with minute sampling; durable records use closed evidence |
| `metadata_cwd_estimate`, `metadata_reconciled` | Read-only SQLite fallback provided directory/timing evidence |
| `no_lifecycle_events` | Old or unsupported history cannot safely supply turn durations |
| `child_excluded` | Parent already includes this child’s work |

The earlier whole-history implementation imposed substantial steady CPU and memory overhead even with a fresh heartbeat; see the [October 14 resource assessment](docs/postmortem/2026-10-14-codex-time-resource-use.md) and [resource smoke check](docs/smoke-tests.md#background-daemon-resources). A restart alone does not establish a lasting fix.

Historical approval waits may make completed totals too large. Polling can miss waits shorter than its sampling interval, and large imports/slow I/O can increase gaps. Unknown or stale unfinished turns never accumulate indefinitely. Later terminal events can replace incomplete observed coverage with an explicitly uncertain lifecycle upper bound, so totals can increase after recovery. Quality flags remain visible in the list, details, reports and ledger. No total is advertised as exact.

Diagnostics omit payload bodies. Malformed complete JSONL lines are skipped visibly, partial final writes wait for completion, archive moves keep identity, and unsupported database schemas retain usable rollout evidence. A corrupt durable ledger, session snapshot, layout marker or quota/usage journal blocks writes; restore a valid backup after stopping the service. Version 1, 2 and 3 ledgers upgrade automatically to version 4 while preserving recorded timing/waits and model evidence; old ingestion offsets are invalidated once so available history backfills model metadata, numeric allowance readings and token evidence. Missing source files retain recorded work and saved model/quota evidence; work without model evidence stays Unknown. Later scans remain incremental. Runtime caches are disposable; source identities invalidate stale offsets after a Git restore. Restart checks individual session snapshots, replays interrupted native projections and rebuilds indexes/projections when needed. Stop tracking before restoring files. A healthy minute daemon remains fresh for 90 seconds; observation gaps above 75 seconds are never bridged as continuous work. Short waits can be missed; neither polling nor the 60-second label promises one-second accuracy.

Integration is verified with installed Codex 0.160.1 schemas. Codex storage is internal and may change. The socket adapter uses [documented app-server initialization and thread lookup](https://learn.chatgpt.com/docs/app-server); it restricts itself to initialize, initialized, thread/loaded/list and thread/read with includeTurns=false. It sends no approval responses.

## Data and Git

Default durable store: `~/.codex-timetrace`. Existing `~/.timetrace` is preserved.

```text
~/.codex-timetrace/
  layout.json                 v1 format marker and durable revision
  sessions/<session-hash>.json current versioned timing, contexts, waits and quality
  ledger.json                 retained original pre-migration ledger
  migration-backup-v1/         verified original ledger/journals + SHA-256 manifest
  legacy-*-observations.jsonl  separately migrated embedded legacy evidence
  quota-observations.jsonl     append-only validated allowance readings
  usage-observations.jsonl     append-only exact token evidence
  projects/<cwd-hash>.json     native timetrace projects
  records/YYYY-MM-DD/          deterministic codex-time-<interval-hash>.json files
```

Closed segments use RFC3339 timestamps and native `start`, `end`, `project:{key}`, `is_billable:false`, and session/turn tags. Filenames include stable identity and exact boundaries, so simultaneous sessions and multiple intervals in a minute cannot collide. Records split at Toronto midnight; elapsed seconds use UTC through DST.

Checkpoints and heartbeat live under `$XDG_STATE_HOME/codex-time/<data-root-hash>` (default `~/.local/state`). A per-data-root writer lock lives under `~/.local/state/codex-time/locks`. Atomic durable writes stage beside the data root; runtime staging stays in runtime storage. None of these files belongs in the data repository. Model attribution stores only model IDs, reasoning levels, timestamps and provenance. Allowance tracking stores only allowlisted usage/window/reset numbers, timestamps, limit/plan labels and source identity/provenance; raw quota payloads are omitted. The durable timing ledger and observer checkpoints contain no conversation bodies, answers, tool output, auth data or credentials. The separate `session-status.json` cache contains the latest user/assistant message text and lives in private runtime storage (directory 0700, file 0600); keep it out of backups or Git intended for sharing. Run `status` to refresh it; the daemon does not maintain that on-demand snapshot. Explicit session names and directory paths remain personal metadata; review them before sharing.

Use a separate Git repository inside the data root. Stop the daemon for a consistent snapshot, review and back up the **entire durable directory**, including `layout.json`, `sessions/`, both evidence journals, separate legacy journals, verified migration backups, `projects/` and `records/`. Use Git LFS for every file over 3 MB and commit its matching `.gitattributes`. Git restore/pull also requires stopping the service first and restoring the complete matching snapshot. Never merge JSON ledgers mechanically while tracking is running. The app does not initialize repositories, commit, push or synchronize code or data.

Native timetrace **list/report readers** are compatible with an explicitly configured separate store. Native list displays project keys and minute labels even when distinct records occur within a minute. Minute-key editing/deleting and native single-timer start/stop commands are unsupported for tracker data: they cannot address its unique filenames and can conflict with projections. [Native storage source](https://github.com/dominikbraun/timetrace/blob/v0.14.3/fs/fs.go) documents reader behavior. The reusable compatibility check runs only in a disposable HOME and config, never against your existing records.

## Resource use and recoverable upgrades

The daemon ingests coalesced file changes, persists only changed sessions, keeps exact observation identities on disk, and updates only affected native records. Healthy inotify uses bounded historical reconciliation; unavailable notifications use a 60-second fallback. Currently loaded source paths are checked with each live sample. Unchanged idle input produces no historical-data writes after warm-up. Reports load evidence on demand; all-history token/allowance reports may still consume substantial transient memory. Health and picker reads avoid observation journals, and the picker refreshes its timing snapshot once a minute.

See [performance evidence and limitations](docs/incremental-tracking.md), [the implementation plan](plans/incremental-tracking.md), and [the maintenance prompt](prompts/incremental-tracking.md). The provisional steady targets are <=0.5% of one core idle, <=2% for five observed roots and <=128 MiB RSS; matched five-minute core runs measured about 0.020% idle CPU and 0.15% active CPU at both history sizes, using 44–50 MiB RSS. The v5 isolated installed wheel measured 0.087% idle / 0.110% active CPU and about 49 MiB daemon RSS with disposable sockets and metadata. Real backfill then exposed a 2.136 GB record that exhausted memory. V6 streams that exact record at 45.3 MiB peak RSS; full live readiness awaits corrected backfill and resource verification. Startup costs and measurement scopes are reported separately in the guide. The reusable [benchmark](scripts/benchmark.py), [CLI/native parity check](scripts/verify-parity.py), [packaged daemon/socket check](scripts/service-smoke.py) and [portable verification/export helper](scripts/storage-recovery.py) use sanitized fixtures or explicitly selected content-free stores, support plain/JSON output, and never send approval responses.

The [deployment helper](scripts/deployment.py) prepares hash-verified current/prior wheels and stopped-writer backup/recovery steps; its prepare/verify actions do not change production. Read the [migration, deployment and rollback procedure](docs/incremental-tracking.md) before upgrading. The old `ledger.json` becomes a retained snapshot after migration. Export current evidence with `storage-recovery.py export-legacy` before activating an older executable; opening that old file directly would omit post-migration timing from its view.

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
