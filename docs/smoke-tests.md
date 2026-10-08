# Codex Time smoke tests

Verify automatic work accounting, daily repo/session reports, model working-time usage, allowance burn tracking, safe session resume and service recovery. First run the isolated smoke script, then inspect the installed service and perform the normal-session UI/report checks. All commands require no sudo; fixture checks never access existing timetrace records.

## Automated fixture checks

**Action:** ./scripts/smoke-test.sh

**Expected:** The real daemon continues counting after a real curses picker exits, survives restart, discards stale offsets after a simulated Git restore, and closes the original stable turn exactly once. Model fixtures conserve counted time through switches, waits, overlaps, missing metadata, legacy upgrade and backfill; reimports remain idempotent. Native timetrace lists two uniquely named records within one minute and reports exactly 30 seconds from an isolated HOME/config/store. Persistence checks cover locks, corrupt ledgers, atomic staging, cross-filesystem checkpoints and Toronto midnight/DST. Missing native reader or conflicting system-wide config is explicitly skipped.

**Action:** uv run pytest && uv run mypy src && uv run ruff check . && uv build

**Expected:** All tests pass, strict typing and lint pass, and wheel/source distribution build. Fixtures contain sanitized IDs/timestamps/directories; no real conversation content is copied into tests.

## Installed service and picker

**Action:** ./scripts/setup.sh

**Expected:** Packaged entry point is rebuilt from current local source and the user service starts. Repeat setup after a source-only change under the same package version: the installed command must expose the change, rather than reuse its cached wheel. Wait for the first historical scan to complete before the following health check; large histories can take several minutes.

**Action:** ./scripts/check.sh && codex-time status --json

**Expected:** Packaged entry point is installed and user service is active with a fresh heartbeat, no live-socket diagnostic when Codex is running, and discovered sessions. Large first histories can take several minutes; active systemd status alone does not prove import is finished. Older unsupported histories and unmatched terminal events can add explicit quality/diagnostic indicators.

**Action:** In a project with Codex sessions, open `codex-time`. Use `/`, `a`, `r`, `s`, and `d`.

**Expected:** Search narrows by name/cwd/ID; all-directory toggle expands scope; archive filters cycle separately from working/waiting/idle runtime state; sorts change order; details display daily totals, original cwd and attributed model/reasoning per interval. The picker shows the latest observed model/reasoning. Long titles and paths leave timers visible. Unknown stale status stops extrapolation. Child agents show zero added time.

**Action:** Select a familiar session and press Enter. Exit Codex normally, then press `q` in the picker.

**Expected:** Codex resumes the selected stable ID in its recorded current directory. Terminal echo/cursor/settings work normally during Codex and after picker exit. Missing directory/executable errors offer a clear remedy. `codex-time status` still reports a running service after the picker closes. Tiny terminal behavior and argument/cwd/terminal restoration also have PTY tests.

## Timing and waits

**Action:** Start a normal root task containing a quiet tool lasting roughly 20 seconds. Watch `codex-time list --all-dirs` from another terminal.

**Expected:** Thinking and the quiet tool both accrue work; silence does not pause time. Completion stops work and the next idle gap adds nothing.

**Action:** Let a normal task reach a blocking question or approval wait, leave it waiting for roughly 20 seconds, then answer/approve. Inspect details and report.

**Expected:** Explicit live wait state pauses work and persists observed waits. A 60-second lifecycle with a 20-second detected wait reports roughly 40 seconds, within sampled uncertainty. Async questions alone do not pause active work. Historical approval waits remain labelled upper bounds. The automated controllable-clock case proves exactly 60 minus 20 equals 40 without depending on a real model’s timing.

**Action:** Run two independent five-minute root tasks concurrently, then inspect all-directory reports. Include a task using child agents.

**Expected:** Each root independently accrues roughly five minutes; total can exceed elapsed time. Children add zero additional work. Same-session overlaps and waits are merged before subtraction. Automated fixtures verify these rules without a real five-minute model run.

## Restart, resume and data isolation

**Action:** While a normal task runs, execute `systemctl --user restart codex-time.service`; inspect status after recovery.

**Expected:** Tracking resumes under the same session/turn IDs with an observation-gap indicator, without inventing a crash/end timestamp or duplicating closed work. Unknown outages do not inflate unfinished timers; a later completion reconciles to an explicit lifecycle upper bound. The automated smoke checks exercise a separate fixture daemon restart, leaving this service untouched.

**Action:** Resume/rename a normal session, including a resume in another cwd; inspect the picker/details.

**Expected:** Stable ID and lifetime time remain, explicit name changes appear, old work retains old cwd, and new work uses the new per-turn cwd. Renames/index updates and resumes/cwd changes have fixture coverage.

**Action:** systemctl --user stop codex-time.service && codex-time import-history && codex-time import-history && systemctl --user start codex-time.service

**Expected:** Comparing a reviewed data-store diff shows no duplicate records or model contexts. Version 1 and 2 ledger timing and wait evidence survive upgrade to version 3; available rollout history backfills model attribution once, and unavailable sources preserve work and saved attribution, with Unknown where evidence is missing. Historical reconciliation may add newly discovered waits or replace marked SQLite estimates with precise rollout times; prior evidence remains covered. Durable data contains only ledger/quota journal/projects/records; checkpoint/lock/staging files stay outside that repository; the content-free quota journal belongs with the ledger in durable snapshots. Existing ~/.timetrace is unaffected. Never run native editing/start/stop commands against tracker data.

**Action:** ./scripts/uninstall.sh

**Expected:** Only the service and installed app are removed. Recorded data remains available for reinstall. Uninstall lifecycle was checked in an isolated HOME with controlled service/tool executables; routine verification leaves the real installed service enabled.

## Daily repo and session time

**Action:** uv run codex-time day --date 2026-10-06

**Expected:** Human-readable date/timezone and a day total appear above directories ranked by duration, each with its full cwd, total and share. Sessions beneath each directory show title, stable ID and that day's duration in that directory. Archived sessions contribute by default, root concurrency adds, children add no separate time, and a session resumed elsewhere retains the original cwd for each portion. Use a date with recorded work; an empty day gives an explicit message.

**Action:** uv run codex-time day --date 2026-10-06 --json

**Expected:** Nested session total_microseconds sum to their directory total_microseconds; directory totals sum to the day total_microseconds. With matching date/timezone, that day total equals `report --all-dirs --archive all --from 2026-10-06 --to 2026-10-06 --json`. JSON seconds are derived once from integer counters. Reports leave ledger/native-record bytes untouched; the running observer may independently record new work.

**Action:** uv run codex-time day --date 2026-10-06 --cwd /absolute/project --archive active --details

**Expected:** Replace /absolute/project with a real project directory. Only original working intervals in that exact cwd contribute, even if a session later resumed elsewhere. Active means unarchived, independent of runtime state. Details show quality flags/diagnostics; `--session SESSION_ID` narrows to one stable identity. Global `--timezone` belongs before `day`; its timezone defines the calendar date, including 23/25-hour DST days.

**Action:** COLUMNS=48 uv run codex-time day --date 2026-10-06 --plain

**Expected:** Long paths/titles/IDs wrap, directory/session durations remain visible, and output is ASCII without ANSI color. `NO_COLOR=1` and piped automatic output also omit color; `--color always` enables color unless NO_COLOR/plain overrides it. Normal output shows helpful hierarchy and short accuracy notes; raw flags appear only with --details. After ./scripts/setup.sh, the installed `codex-time day` exposes the same view.

## Model working-time usage

**Action:** codex-time models day

**Expected:** The table labels values as working-time usage for today's America/Toronto date, across all directories and archive states. Known model/reasoning rows rank by descending duration with deterministic ties. Rows show exact model IDs, reasoning levels, percentages, distinct session counts and quality. Unknown model time is separate and unranked, included in total and percentage denominator.

**Action:** codex-time models week --date 2026-10-06

**Expected:** The containing calendar week starts Monday 2026-10-05 and ends before Monday 2026-10-12. A monthly report for the same date covers October's calendar boundaries; fixtures also exercise month/year changes and Toronto's 23/25-hour DST days.

**Action:** codex-time models month --date 2026-10-06 --model-only --csv

**Expected:** Reasoning levels combine into one row per model, with unioned distinct session counts. CSV carries the same working-time totals, percentages and quality as the equivalent terminal table. JSON exports carry the same rows; providing both --json and --csv is rejected.

**Action:** codex-time --timezone America/Toronto models day --date 2026-10-06 --cwd /absolute/project --archive all --json

**Expected:** Replace /absolute/project with the selected real project path. Rows include only counted intervals originally attributed to that cwd; the sum including Unknown equals the total from the matching session report below. Timezone selection applies to calendar boundaries.

**Action:** codex-time --timezone America/Toronto report --from 2026-10-06 --to 2026-10-06 --cwd /absolute/project --archive all --json

**Expected:** With the same project path, total_seconds and total_microseconds match the model report totals; summing working_microseconds across model rows exactly equals total_microseconds, even if sessions have since resumed in another directory. Use --all-dirs instead of --cwd for comparison to model reports without a cwd filter.

**Action:** Use one normal root session with two turns at different model/reasoning settings, then inspect its details and the containing day report.

**Expected:** Both recorded settings retain their own duration and quality. Changing only reasoning creates separate rows unless --model-only is selected. Missing fields stay Unknown; current session settings never relabel old turns. Sanitized fixtures additionally exercise within-turn timestamped changes, repeated/conflicting contexts and a switch during an overlapping wait.

**Action:** Inspect model reports after the blocking-wait and concurrent-root checks above; restart the service and inspect again.

**Expected:** Detected wait time contributes to no model bucket; quiet tools and thinking do. Two five-minute roots contribute roughly 600 seconds combined and children add zero. Latest-starting-turn ownership partitions same-session overlaps without double counting. Restart, rename, archive moves and repeated import retain attribution and totals; uncertainty/observation-gap flags remain visible. These checks establish usage accounting, not efficiency or output quality.

## Allowance burn tracking

**Action:** codex-time burn week --date 2026-10-06

**Expected:** The installed command reports allowance percentage points per summed root working hour, defaulting to the weekly `codex` window. The formatted view has a prominent remaining-allowance bar, readable burn rate and matched duration, local timestamps, and aligned exact model/reasoning work shares. Short notes expose excluded consumption and low confidence; raw flags and epoch metadata do not crowd the default view. Weeks start Monday and timezone boundaries match the selected date. No usable evidence is shown explicitly and is not represented as zero consumption.

**Action:** Run `codex-time burn day` in a normal terminal, then resize to about 48 columns and repeat. Run `codex-time burn day --details`.

**Expected:** The remaining allowance, burn rate and working duration stay readable. Model IDs and reasoning levels wrap when needed without losing values; labels remain distinguishable without color. `--details` exposes reset metadata, raw quality flags and rounding sensitivity below the readable summary.

**Action:** Run `NO_COLOR=1 codex-time burn day`, `codex-time burn day --color never`, `codex-time burn day | cat`, and `codex-time burn day --plain`.

**Expected:** `NO_COLOR`, explicit `never` and automatic pipe output contain no ANSI color escapes. Plain mode uses ASCII and no color while retaining report values. Default interactive output has helpful visual cues, and `--color always` can explicitly enable color for capture.

**Action:** codex-time burn week --date 2026-10-06 --json && codex-time burn week --date 2026-10-06 --csv

**Expected:** JSON, CSV and the formatted view contain the same rows/totals, with display rounding only; `--details`, `--plain` and color choices do not change exports. The recomputed points/hour agrees with the export. JSON includes exact working microseconds and model/reasoning mix; mixed workloads remain descriptive rather than individual model quota estimates. `--json --csv` is rejected.

**Action:** codex-time --timezone America/Toronto burn day --date 2026-10-06 --window-minutes 10080 --limit-id codex --max-gap-seconds 600

**Expected:** Matching rows retain the same qualifying evidence. Adjacent pairs crossing local dates are exposed as boundary exclusions instead of apportioned drops; long gaps and changes without root work appear separately. Fixtures exercise midnight, month/year changes and Toronto DST. Changing maximum gap can change selected evidence and must be recorded when comparing results.

**Action:** With the service running during normal Codex use, record an export, restart the service, and export the same completed historical period again. If manually resetting allowance as part of ordinary use, inspect the report after subsequent readings arrive.

**Expected:** New readings are collected automatically, completed history is not duplicated by restart, and old evidence survives missing source files. A recorded reset identity change starts a fresh baseline, never a consumption jump. Fixtures verify five-second reset jitter, stale lower readings, duplicate history, v1/v2 ledger preservation/backfill, append-only quota migration, journal restore/fingerprints and incremental checkpoints; this check does not require performing a real reset.

**Action:** Inspect burn reports for dates covered by the concurrent-root, child and blocking-wait checks above.

**Expected:** The denominator uses counted wait-subtracted root work, with simultaneous roots summed and children adding no separate hours. The numerator remains account-wide: child or external activity can affect it. Excluded changes remain visible and prevent an unsupported account-exhaustion forecast. Native timetrace working-time records and existing `~/.timetrace` are unaffected.

## Recorded evidence

Implementation verification and exact fresh counts are maintained in [the base ExecPlan](../plans/codex-session-time-tracker.md) and [the model-usage ExecPlan](../plans/codex-model-usage-reports.md), and [the allowance-tracking ExecPlan](../plans/codex-model-burn-tracking.md). Terminal presentation checks are recorded in [the readability plan](../plans/codex-burn-terminal-ux.md). The checks above describe expected outcomes; their execution evidence belongs in those plans. Human-controlled approval timing, model switches and five-minute real-model checks are manual checks and must not be claimed as executed without evidence.

## Public source checkout

**Action:** Follow the README clone instructions in a fresh directory, then run `uv sync --python 3.12`, `uv run codex-time --help`, and `./scripts/smoke-test.sh`. Run setup only when you intend to install and enable the user service.

**Expected:** The public checkout has source, tests, scripts and matching implementation plans; help and isolated smoke checks work without personal ledgers or allowance-history artifacts. Setup is a separate deliberate installation step. Virtual environments, build output and local usage records are absent from Git history.
