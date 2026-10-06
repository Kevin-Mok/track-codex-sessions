# Track Codex allowance burn

Track observed allowance percentage changes alongside existing Codex working time. Keep the observer running, inspect daily or longer reports, and save exports to compare workloads with similar model and reasoning mixes. Each report shows matched consumption and excluded changes so the estimate can be reproduced without assigning shared quota usage to an individual model.

## Automatic collection

Codex Time already tracks root-session working time, including thinking, tools and delegated work, while subtracting detected blocking waits. The user service also collects numeric allowance readings from rollout `token_count.rate_limits` events. It observes existing local Codex files; it does not query an account, change a plan, reset allowance or start sessions.

Update the installed command and service from this checkout, then wait for a fresh heartbeat after historical import:

```bash
./scripts/setup.sh
./scripts/check.sh
codex-time status --json
```

Ledger version 3 preserves existing timing, waits and model attribution from version 1 or 2. Old ingestion offsets are invalidated once to backfill available allowance history; subsequent collection is incremental. Missing source files retain previously saved work and readings. Reimport and restart deduplicate evidence.

To force a reconciliation, stop the single writer first:

```bash
systemctl --user stop codex-time.service
codex-time import-history
systemctl --user start codex-time.service
```

Allowance readings are only available when Codex records them. A running service does not guarantee continuous quota observations. Empty reports indicate missing selected-window evidence, rather than zero consumption.

## Report and export

```bash
codex-time burn day
codex-time burn week --date 2026-10-06
codex-time burn month --date 2026-10-06
codex-time --timezone America/Toronto burn day --date 2026-10-06
codex-time burn week --date 2026-10-06 --json > burn-2026-10-05.json
codex-time burn week --date 2026-10-06 --csv > burn-2026-10-05.csv
codex-time burn week --date 2026-10-06 --window-minutes 10080 --limit-id codex --max-gap-seconds 600
```

The default selects the current calendar period in America/Toronto. Weeks begin Monday; months use calendar boundaries. `--date YYYY-MM-DD` selects the containing period and the global `--timezone` changes its boundaries. Global options precede `burn`; `--json` and `--csv` are mutually exclusive. The formatted terminal view and both exports use the same report data.

`--window-minutes` selects the recorded allowance window, defaulting to 10,080 minutes (weekly). `--limit-id` defaults to `codex`. These selectors do not create missing readings or infer a different allowance window. `--max-gap-seconds` defaults to 600; keep the same value when comparing exports because it changes which observations qualify.

Reports include all root sessions, directories and archive states. There is no directory or archive filter: the numerator is account-wide allowance, so narrowing its working-time denominator to one project would distort the rate.

## Read the terminal report

The report leads with remaining allowance and a usage bar, followed by the observed burn rate and matched working duration. Model IDs and reasoning levels have separate, aligned work-share rows. Dates and reading times use the selected local timezone. Short notes explain low confidence and excluded consumption; a model's share is its share of working time, not an individual quota cost.

```bash
codex-time burn day --details
codex-time burn day --plain
codex-time burn day --color never
NO_COLOR=1 codex-time burn day
codex-time burn week --plain > burn-week.txt
```

Use `--details` for raw quality flags, reset metadata and rounding sensitivity. `--color auto|always|never` defaults to `auto`, which colors an interactive terminal and omits ANSI colors when output is piped. `NO_COLOR` disables color. Use `--plain` for an ASCII, color-free report in terminals with limited Unicode support. The layout adapts to available width; long model labels wrap instead of hiding their rates. These display options do not change observations, calculations, JSON or CSV exports.

## Reproduce a rate

Rows describe a local date and reset cohort. JSON exposes `matched_points`, `working_microseconds`, `working_hours` and `points_per_working_hour`, with a model/reasoning `mix` and separate `excluded_gap_points`, `excluded_no_work_points` and `excluded_boundary_points`. The report also retains limit/window/plan/reset identifiers and the latest selected snapshot. For each row:

1. Read the matched allowance percentage-point increase and summed root working hours.
2. Calculate **points per working hour = matched percentage points / summed root working hours**. For example, a rise from 20% to 24% matched to two root working hours gives 2 points/hour. This is a four-point increase, not a 20% relative increase.
3. Inspect the accompanying model/reasoning mix, excluded gap/no-work/boundary points, confidence indicator and timing quality before using the rate.

The denominator uses existing counted intervals clipped to the same observation windows. Two roots each working for one wall-clock hour contribute two working hours. Children add no separate denominator time; their allowance consumption can still appear in the shared readings. The model/reasoning mix describes the parent workload, including tools and delegation.

An adjacent observation pair qualifies only if it belongs to the same selected limit/window/reset cohort, has no more than the configured gap, has counted root work, and can be assigned to the report's local-date boundary. The report exposes excluded increases separately; a pair crossing dates belongs to the ending date as a boundary exclusion. It does not guess when a drop happened inside a gap or distribute it between dates. Detected waits contribute no working time.

A materially changed reset identity starts a fresh baseline. Reset timestamp jitter within five seconds stays in the same cohort. Readings from a retired reset cohort cannot bridge a newer reset or replace the latest accepted reading. Conflicting readings at the same timestamp break attribution and add a quality flag; the next unambiguous reading establishes a fresh baseline. Lower readings within the same reset cohort are treated as stale and skipped, so a later rebound is not counted twice. Manual resets are never consumption. A reset without distinguishable recorded evidence cannot be reconstructed reliably.

## Compare workloads over time

Save exports for multiple dates using the same timezone, limit, allowance window and maximum gap. Compare rows with similar dominant model/reasoning mixes, allowance capacity and task conditions. Keep separate reset cohorts visible. A weekly report supplies daily rows for checking whether a broad average is driven by one day or a large excluded gap.

For a planning estimate, use a range from sufficiently observed comparable rows and retain their excluded changes alongside it. The command reads saved ledger evidence; it does not perform a fresh account query. Re-run the same command after new evidence arrives or use a consistent stopped-service ledger snapshot for an unchanged historical export. Do not silently discard excluded consumption when estimating account-wide exhaustion.

All rates are low-confidence workload observations. Rounded percentage readings, delayed updates, unknown allowance capacity, external/cloud activity, caching, speed settings and task differences can affect them. Mixed simultaneous models cannot be separated causally from one shared quota drop; these reports do not produce individual model prices, calibrated reasoning-level costs, efficiency rankings or a dependable hours-remaining forecast.

This workflow uses explicit adjacent-reading selection and exposes excluded consumption. Comparisons made with different sampling methods may produce different rates; use the same selectors and method for repeatable comparisons.

## Privacy and recovery

The append-only `quota-observations.jsonl` journal saves allowlisted allowance metadata: numeric usage/window/reset values, observation timestamps and primary/secondary bucket identity and fixed provenance needed for deduplication, plus limit and plan labels. Prompts, answers, tool output, raw quota payloads, authentication and credentials are not persisted. Existing session titles and directory paths remain personal metadata; review the data store before sharing it.

Back up the durable store with the service stopped before upgrading, including both `ledger.json` and `quota-observations.jsonl` when present. The journal keeps quota history out of full timing-ledger rewrites; embedded v3 quota evidence migrates without loss. Invalid durable journal lines block writes with a restore-backup error rather than being silently discarded. Version 3 remains readable by this version; an older app may require its matching pre-upgrade ledger backup. Never replace or mechanically merge the live ledger or journal while the writer runs. Restore them together from the same snapshot; ingestion fingerprints cover both. Native timetrace records continue to represent working time; allowance readings do not add native records.

The implementation and verification records are in [the tracking ExecPlan](../plans/codex-model-burn-tracking.md) and [the terminal presentation plan](../plans/codex-burn-terminal-ux.md). See the grouped [smoke checks](smoke-tests.md#allowance-burn-tracking) for reproducible installed-command, export and reset checks.
