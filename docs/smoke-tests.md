# Codex Time smoke tests

Verify automatic work accounting, daily repo/session reports, model working-time usage, token/API costs in USD/CAD and a combined allowance/model overview, allowance consumption, safe session resume and service recovery. First run the isolated smoke script, then inspect the installed service and perform the normal-session UI/report checks. All commands require no sudo; fixture checks never access existing timetrace records.

## Automated fixture checks

**Action:** ./scripts/smoke-test.sh

**Expected:** The real daemon continues counting after a real curses picker exits, survives restart, discards stale offsets after a simulated Git restore, and closes the original stable turn exactly once. Model fixtures conserve counted time through switches, waits, overlaps, missing metadata, legacy upgrade and backfill; reimports remain idempotent. Native timetrace lists two uniquely named records within one minute and reports exactly 30 seconds from an isolated HOME/config/store. Persistence checks cover locks, corrupt ledgers, atomic staging, cross-filesystem checkpoints and Toronto midnight/DST. Missing native reader or conflicting system-wide config is explicitly skipped.

**Action:** uv run pytest && uv run mypy src && uv run ruff check . && uv build

**Expected:** All tests pass, strict typing and lint pass, and wheel/source distribution build. Fixtures contain sanitized IDs/timestamps/directories; no real conversation content is copied into tests.

## Installed service and picker

**Action:** ./scripts/setup.sh

**Expected:** Packaged entry point is rebuilt from current local source and the user service starts. Repeat setup after a source-only change under the same package version: the installed command must expose the change, rather than reuse its cached wheel. Wait for the first historical scan to complete before the following health check; large histories can take several minutes.

**Action:** ./scripts/check.sh && codex-time health --json

**Expected:** Packaged entry point is installed and user service is active with a fresh heartbeat, no live-socket diagnostic when Codex is running, and discovered sessions. Large first histories can take several minutes; active systemd status alone does not prove import is finished. Older unsupported histories and unmatched terminal events can add explicit quality/diagnostic indicators.

**Action:** codex-time resume

**Expected:** In a project with Codex sessions, the same picker opens as with no arguments. Use `/`, `a`, `r`, `s`, and `d`. Search narrows by name/cwd/ID; all-directory toggle expands scope; archive filters cycle separately from working/waiting/idle runtime state; sorts change order; details display daily totals, original cwd and attributed model/reasoning per interval. The picker shows the latest observed model/reasoning. Long titles and paths leave timers visible. Unknown stale status stops extrapolation. Child agents show zero added time.

**Action:** Select a familiar session and press Enter. Exit Codex normally, then press `q` in the picker.

**Expected:** Codex resumes the selected stable ID in its recorded current directory. Terminal echo/cursor/settings work normally during Codex and after picker exit. Missing directory/executable errors offer a clear remedy. `codex-time health` still reports a running service after the picker closes. Tiny terminal behavior and argument/cwd/terminal restoration also have PTY tests.

## Timing and waits

**Action:** Start a normal root task containing a quiet tool lasting roughly 20 seconds. Watch `codex-time sessions --all-dirs` from another terminal.

**Expected:** Thinking and the quiet tool both accrue work; silence does not pause time. Ingestion and live display may lag by up to 60 seconds. Precise lifecycle completion stops recorded work and the next idle gap adds nothing.

**Action:** Let a normal task reach a blocking question or approval wait, leave it waiting for roughly 20 seconds, then answer/approve. Inspect details and report.

**Expected:** A sampled live wait pauses work and persists observed waits. A short wait visible only through the socket may fall entirely between minute samples; inspect the actual uncertainty rather than assuming one-second accuracy. A 60-second lifecycle with a 20-second known source wait retains exactly 40 seconds of counted work. Async questions alone do not pause active work, and unresolved historical approval waits remain labelled upper bounds. The automated controllable-clock case proves exactly 60 minus 20 equals 40 without depending on a real model’s timing.

**Action:** Run two independent five-minute root tasks concurrently, then inspect all-directory reports. Include a task using child agents.

**Expected:** Each root independently accrues roughly five minutes; total can exceed elapsed time. Children add zero additional work. Same-session overlaps and waits are merged before subtraction. Automated fixtures verify these rules without a real five-minute model run.

## Restart, resume and data isolation

**Action:** While a normal task runs, execute `systemctl --user restart codex-time.service`; inspect status after recovery.

**Expected:** Tracking resumes under the same session/turn IDs with an observation-gap indicator, without inventing a crash/end timestamp or duplicating closed work. Unknown outages do not inflate unfinished timers; a later completion reconciles to an explicit lifecycle upper bound. The automated smoke checks exercise a separate fixture daemon restart, leaving this service untouched.

**Action:** Resume/rename a normal session, including a resume in another cwd; inspect the picker/details.

**Expected:** Stable ID and lifetime time remain, explicit name changes appear, old work retains old cwd, and new work uses the new per-turn cwd. Renames/index updates and resumes/cwd changes have fixture coverage.

**Action:** systemctl --user stop codex-time.service && codex-time import-history && codex-time import-history && systemctl --user start codex-time.service

**Expected:** Comparing a reviewed data-store diff shows no duplicate records or model contexts. Version 1, 2 and 3 ledger timing and wait evidence survive upgrade to version 4; available rollout history backfills model attribution once, and unavailable sources preserve work and saved attribution, with Unknown where evidence is missing. Historical reconciliation may add newly discovered waits or replace marked SQLite estimates with precise rollout times; prior evidence remains covered. Preserve the complete durable data root, including the layout marker, per-session snapshots, original ledger, current/legacy evidence journals, verified migration backup, projects and records. Disposable index/checkpoint/lock/staging files remain outside that repository. Existing ~/.timetrace is unaffected. Never run native editing/start/stop commands against tracker data.

**Action:** ./scripts/uninstall.sh

**Expected:** Only the service and installed app are removed. Recorded data remains available for reinstall. Uninstall lifecycle was checked in an isolated HOME with controlled service/tool executables; routine verification leaves the real installed service enabled.

## Combined allowance and model overview

**Action:** codex-time overview

**Expected:** Today's readable date/timezone and recorded duration appear first, then tokens and estimated Standard API costs, allowance balance, observed consumption and model work. Model totals rank by duration, with reasoning rows directly beneath their model. Model and reasoning percentages share the overall recorded-work denominator. Model session counts independently count distinct contributing sessions; they do not sum reasoning-row counts. All directories and archive states contribute. Unknown model/reasoning remains visible, and unknown models are unranked. Missing readings give an explicit evidence warning while recorded model work remains available.

**Action:** codex-time overview week --date 2026-10-06 --details

**Expected:** The containing week starts Monday October 5. Matched allowance points/duration and exclusions remain distinct from all recorded model work. For one plan/bucket stream, “Matched work” combines its reset cohorts and “Outside matched windows” explains the rest of recorded work. Parallel allowance streams show an overlap warning instead of a misleading combined duration. Multiple reset cohorts stay separate with readable date/reset labels. A note explains that durations of at least one second omit fractional seconds, so displayed rows can differ slightly when added. Details show matched model mixes, uncertainty and concise human caveats. Raw flags, diagnostics, exact microseconds, complete pricing/FX metadata and child identities remain in --json. Confidence warnings remain visible without details.

**Action:** COLUMNS=40 codex-time overview day --date 2026-10-06 --plain

**Expected:** Long model IDs and reasoning labels wrap without hiding durations, percentages or session counts. Tiny positive shares remain visible. Output is ASCII and contains no ANSI escapes. Repeat at a normal terminal width to check the same accounting and hierarchy.

**Action:** NO_COLOR=1 codex-time overview --color always && codex-time overview | cat

**Expected:** Both outputs omit ANSI color. Explicit --color always enables color when neither NO_COLOR nor --plain is present. Piped automatic output stays readable.

**Action:** codex-time overview week --date 2026-10-06 --json | python3 -c 'import json, sys; data = json.load(sys.stdin); assert set(data) == {"allowance", "model_totals", "reasoning", "token_usage"}; assert data["model_totals"]["total_microseconds"] == data["reasoning"]["total_microseconds"]; print("Overview JSON and totals OK")'

**Expected:** Clean JSON parses with the four descriptive keys and equal exact model/reasoning totals. Each value retains its existing report schema. Compare allowance with `allowance week --date 2026-10-06 --json`, model_totals with `model-time week --date 2026-10-06 --model-only --json`, and reasoning with the same model-time command without --model-only. The allowance matched-work denominator can be smaller than the model-work total. Overview accepts allowance window/limit/gap controls and leaves stored data unchanged; fixtures verify this with stable durable-storage hashes (overview may create its disposable runtime cache).

**Action:** codex-time --help && uv run pytest -q tests/test_command_layout.py

**Expected:** Help advertises overview, allowance, model-time, projects, sessions, history, health and resume, plus unchanged daemon/import-history. Legacy names are absent from top-level help but silently accept the same arguments/defaults, terminal output, exports and exit codes. Alias comparisons pass, and no-argument/resume picker behavior stays the same.

**Action:** uv tool install --python 3.12 --force --reinstall-package codex-time "$PWD" && (cd /tmp && codex-time overview --plain && codex-time --help)

**Expected:** Run from the checkout to refresh the installed package without restarting the observer. From outside the checkout, the installed executable exposes the overview and canonical command help, including a same-version source update. Package refresh alone does not migrate history; the next upgraded daemon start may perform the versioned migration after verifying its backup. No sudo is required.

## Daily repo and session time

**Action:** uv run codex-time projects --date 2026-10-06

**Expected:** A "Recorded Codex working time" heading, human-readable date/timezone and a day total appear above directories ranked by duration, each with its full cwd, total and share. Sessions beneath each directory show title, model, that day's duration in that directory, tokens and USD/CAD costs; full stable IDs appear with --details. Archived sessions contribute by default, root concurrency adds, children add no separate time, and a session resumed elsewhere retains the original cwd for each portion. Use a date with recorded work; an empty day gives an explicit message.

**Action:** uv run codex-time projects --plain

**Expected:** The "Directory shares" summary aligns Project, Time, Share, Tokens, USD and CAD when columns fit, then "Session details" retains every session and model. Each full directory path appears with its group; sole-model costs are not repeated when they equal session totals. Output is ASCII. An asterisk means known priced subtotal; unavailable/unpriced amounts never appear as free usage.

**Action:** uv run codex-time projects --date 2026-10-06 --json

**Expected:** Nested session total_microseconds sum to their directory total_microseconds; directory totals sum to the day total_microseconds. With matching date/timezone, that day total equals `history --all-dirs --archive all --from 2026-10-06 --to 2026-10-06 --json`. JSON seconds are derived once from integer counters. Reports leave ledger/native-record bytes untouched; the running observer may independently record new work.

**Action:** uv run codex-time projects --date 2026-10-06 --cwd /absolute/project --archive active --details

**Expected:** Replace /absolute/project with a real project directory. Only original working intervals in that exact cwd contribute, even if a session later resumed elsewhere. Active means unarchived, independent of runtime state. Details show each title once per directory, full session IDs, compact input/cached/output categories, nonzero reasoning/cache-write subsets, child-agent counts and one FX/catalog footer. Raw diagnostic/flag lists, exact costs and full pricing dictionaries stay in --json; missing usage remains a concise warning. `--session SESSION_ID` narrows to one stable identity. Global `--timezone` belongs before `projects`; its timezone defines the calendar date, including 23/25-hour DST days.

**Action:** COLUMNS=48 uv run codex-time projects --date 2026-10-06 --plain

**Expected:** Labels and metrics stack at 48 columns; complete paths/titles wrap, directory/session durations and token/cost values remain visible, and output is ASCII without ANSI color. Full IDs remain available with --details. At 120 columns, metrics align and long titles fold without ellipsis. `NO_COLOR=1` and piped automatic output also omit color; `--color always` enables color unless NO_COLOR/plain overrides it. Normal and detailed output show helpful hierarchy and short accuracy notes; raw flags stay in JSON. After the documented package refresh, installed `codex-time projects` exposes the same view.

**Action:** codex-time sessions --all-dirs --details && codex-time history --all-dirs --details && codex-time health --details && codex-time status --plain

**Expected:** Sessions show every matching title, time, state and model; details add full IDs/paths. History has readable daily/directory/session totals rather than a JSON dump; without details it shows working sessions and the count of sessions with no work in the selected range. Details/JSON keep that full list. Dates/counts use singular labels for one item, and positive subsecond work remains visible. Health gives observer/heartbeat/notice summaries and optional runtime paths. Status shows the latest 20 entries and an explicit omitted count/JSON hint when needed. Plain output is ASCII. No human view prints raw quality lists or metadata dictionaries; matching --json retains machine fields.

**Action:** Run a slow projects/overview report in a terminal, then repeat with --json redirected to a file.

**Expected:** Interactive human output updates one elapsed-status line and clears it before printing the report. JSON/redirected progress remains periodic newline messages on stderr and JSON stdout parses cleanly. Fast reports print no loading noise. Interrupted or failed reads clear the interactive progress line.

## Model working-time usage

**Action:** codex-time model-time day

**Expected:** The table labels values as working-time usage for today's America/Toronto date, across all directories and archive states. Known model/reasoning rows rank by descending duration with deterministic ties. Rows show exact model IDs, reasoning levels, readable durations, percentages and distinct session counts. Emoji headings, readable dates and share bars appear by default; a concise accuracy note replaces raw flags/diagnostics. Use this command without --model-only to see the reasoning-level breakdown. Unknown model time is separate and unranked, included in total and percentage denominator.

**Action:** codex-time model-time day --model-only && codex-time model-time week --model-only

**Expected:** One row per model combines reasoning levels and omits the reasoning column. The top known model has a trophy; Unknown stays unranked. Times use labels such as 2h 4m 15s and short work stays visible, including 39s or 0.25s. Shares are percentages of working time, including tools, rather than token consumption.

**Action:** COLUMNS=40 codex-time model-time day --plain --details

**Expected:** The narrow stacked layout keeps model IDs, reasoning, time, share and sessions readable. Output is ASCII without ANSI escapes; details reveal sampling uncertainty with its non-additive caveat, human timing notes and a diagnostic count. Raw flags/diagnostics remain in JSON/CSV. NO_COLOR also suppresses color even with --color always. Exports remain clean and retain exact accounting and quality evidence.

**Action:** codex-time model-time week --date 2026-10-06

**Expected:** The containing calendar week starts Monday 2026-10-05 and ends before Monday 2026-10-12. A monthly report for the same date covers October's calendar boundaries; fixtures also exercise month/year changes and Toronto's 23/25-hour DST days.

**Action:** codex-time model-time month --date 2026-10-06 --model-only --csv

**Expected:** Reasoning levels combine into one row per model, with unioned distinct session counts. CSV carries the same working-time totals, percentages and quality as the equivalent terminal table. JSON exports carry the same rows; providing both --json and --csv is rejected.

**Action:** codex-time --timezone America/Toronto model-time day --date 2026-10-06 --cwd /absolute/project --archive all --json

**Expected:** Replace /absolute/project with the selected real project path. Rows include only counted intervals originally attributed to that cwd; the sum including Unknown equals the total from the matching session report below. Timezone selection applies to calendar boundaries.

**Action:** codex-time --timezone America/Toronto history --from 2026-10-06 --to 2026-10-06 --cwd /absolute/project --archive all --json

**Expected:** With the same project path, total_seconds and total_microseconds match the model report totals; summing working_microseconds across model rows exactly equals total_microseconds, even if sessions have since resumed in another directory. Use --all-dirs instead of --cwd for comparison to model reports without a cwd filter.

**Action:** Use one normal root session with two turns at different model/reasoning settings, then inspect its details and the containing model-time day report.

**Expected:** Both recorded settings retain their own duration and quality. Changing only reasoning creates separate rows unless --model-only is selected. Missing fields stay Unknown; current session settings never relabel old turns. Sanitized fixtures additionally exercise within-turn timestamped changes, repeated/conflicting contexts and a switch during an overlapping wait.

**Action:** Inspect model reports after the blocking-wait and concurrent-root checks above; restart the service and inspect again.

**Expected:** Detected wait time contributes to no model bucket; quiet tools and thinking do. Two five-minute roots contribute roughly 600 seconds combined and children add zero. Latest-starting-turn ownership partitions same-session overlaps without double counting. Restart, rename, archive moves and repeated import retain attribution and totals; uncertainty/observation-gap flags remain visible. These checks establish usage accounting, not efficiency or output quality.

## Allowance balance and consumption

**Action:** codex-time allowance week --date 2026-10-06

**Expected:** The installed command reports allowance percentage points per summed root working hour, defaulting to the weekly `codex` window. The formatted view has a prominent remaining-allowance bar, readable burn rate and matched duration, local timestamps, and aligned exact model/reasoning work shares. Short notes expose excluded consumption and low confidence; raw flags and epoch metadata do not crowd the default view. Weeks start Monday and timezone boundaries match the selected date. No usable evidence is shown explicitly and is not represented as zero consumption.

**Action:** codex-time allowance day && COLUMNS=48 codex-time allowance day && codex-time allowance day --details

**Expected:** The remaining allowance, burn rate and working duration stay readable. Model IDs and reasoning levels wrap when needed without losing values; labels remain distinguishable without color. `--details` adds readable reset dates, matched windows, uncertainty and rounding sensitivity. Human caveats replace raw flags, epoch timestamps and unbounded diagnostics; JSON/CSV retain full evidence.

**Action:** NO_COLOR=1 codex-time allowance day && codex-time allowance day --color never && codex-time allowance day | cat && codex-time allowance day --plain

**Expected:** `NO_COLOR`, explicit `never` and automatic pipe output contain no ANSI color escapes. Plain mode uses ASCII and no color while retaining report values. Default interactive output has helpful visual cues, and `--color always` can explicitly enable color for capture.

**Action:** codex-time allowance week --date 2026-10-06 --json && codex-time allowance week --date 2026-10-06 --csv

**Expected:** JSON, CSV and the formatted view contain the same rows/totals, with display rounding only; `--details`, `--plain` and color choices do not change exports. The recomputed points/hour agrees with the export. JSON includes exact working microseconds and model/reasoning mix; mixed workloads remain descriptive rather than individual model quota estimates. `--json --csv` is rejected.

**Action:** codex-time --timezone America/Toronto allowance day --date 2026-10-06 --window-minutes 10080 --limit-id codex --max-gap-seconds 600

**Expected:** Matching rows retain the same qualifying evidence. Adjacent pairs crossing local dates are exposed as boundary exclusions instead of apportioned drops; long gaps and changes without root work appear separately. Fixtures exercise midnight, month/year changes and Toronto DST. Changing maximum gap can change selected evidence and must be recorded when comparing results.

**Action:** With the service running during normal Codex use, record an export, restart the service, and export the same completed historical period again. If manually resetting allowance as part of ordinary use, inspect the report after subsequent readings arrive.

**Expected:** New readings are collected automatically, completed history is not duplicated by restart, and old evidence survives missing source files. A recorded reset identity change starts a fresh baseline, never a consumption jump. Fixtures verify ten-second reset jitter, stale lower readings, duplicate history, v1/v2 ledger preservation/backfill, append-only quota migration, journal restore/fingerprints and incremental checkpoints; this check does not require performing a real reset.

**Action:** codex-time allowance day

**Expected:** Run after the concurrent-root, child and blocking-wait checks above. The denominator uses counted wait-subtracted root work, with simultaneous roots summed and children adding no separate hours. The numerator remains account-wide: child or external activity can affect it. Excluded changes remain visible and prevent an unsupported account-exhaustion forecast. Native timetrace working-time records and existing `~/.timetrace` are unaffected.

**Action:** codex-time overview day --date 2026-10-20 --details

**Expected:** Quota readings with reset deadlines within ten seconds of the original cohort anchor stay in one row per stream/day. The Oct 20 progression accounts for all three observed points in one row (two matched, one excluded across a genuine 17-minute observation gap), instead of retiring frequent readings or creating a sparse duplicate reset row. Matched work can still differ from total model work when readings are missing. Reset changes beyond ten seconds start a fresh baseline; the tolerance never chains through intermediate readings.

**Action:** Before publishing, run the configured shared privacy gate against the exact index candidate, retaining the external private identity policy and existing hooks.

**Expected:** Neutral public home-path/HTTPS examples pass. The three reviewed recovery CLI/module/test files pass only for their exact path/full-content hashes and sensitive-path category; altered bytes require review. Explicit private prohibitions still reject content even when a public approval exists. This cleanup changes the current tree and does not rewrite already published history.

## Recorded evidence

Implementation verification and exact fresh counts are maintained in [the base ExecPlan](../plans/codex-session-time-tracker.md) and [the model-usage ExecPlan](../plans/codex-model-usage-reports.md), and [the allowance-tracking ExecPlan](../plans/codex-model-burn-tracking.md). Terminal presentation checks are recorded in [the readability plan](../plans/codex-burn-terminal-ux.md). Daily directory/session verification is recorded in [the daily-report plan](../plans/daily-repo-session-time.md). Combined overview and command compatibility verification is recorded in [the overview plan](../plans/overview-command-layout.md); minute-cadence, final packaged parity and portable recovery evidence is recorded in [the incremental-tracking plan](../plans/incremental-tracking.md). The checks above describe expected outcomes; their execution evidence belongs in those plans. Human-controlled approval timing, model switches and five-minute real-model checks are manual checks and must not be claimed as executed without evidence.

## Public source checkout

**Action:** Follow the README clone instructions in a fresh directory, then run `uv sync --python 3.12`, `uv run codex-time --help`, and `./scripts/smoke-test.sh`. Run setup only when you intend to install and enable the user service.

**Expected:** The public checkout has source, tests, scripts and matching implementation plans; help and isolated smoke checks work without personal ledgers or allowance-history artifacts. Setup is a separate deliberate installation step. Virtual environments, build output and local usage records are absent from Git history.

## Background daemon resources

Check both freshness and resource use; a running service or fresh heartbeat does not establish an efficient observer. See [the October 14 assessment](postmortem/2026-10-14-codex-time-resource-use.md) for measured history-processing overhead and limits.

**Action:** From any directory, run `systemctl --user status codex-time.service --no-pager`, then `top -b -d 1 -n 2 -p (systemctl --user show codex-time.service --property=MainPID --value)` in fish, and `codex-time health --json`. No sudo is needed.

**Expected:** The status and health PID agree for a running tracker; health has a fresh heartbeat. The second top sample shows current CPU and RSS. Sustained near-100% CPU indicates expensive work even when health is running. Repeat comparable observations with no new activity to investigate growth; one high RSS reading is insufficient to establish a leak. A restart preserves recorded history but requires a fresh post-start resource measurement before claiming recovery.

## Cached session state for outside watchers

Run from the source checkout until this version is installed; no sudo is needed. These commands read Codex files and write only disposable private state. See [the watcher contract](session-status.md).

**Action:** uv run codex-time status --json

**Expected:** A version-1 JSON object contains observer-health keys and a sessions array with tty/cwd/rollout path, lifecycle state, last user/assistant text and source update time. Stdout contains only JSON; a long first replay reports elapsed progress on stderr. A second call with unchanged sources has scan.opened=0 and scan.bytes_read=0. Concurrent live appends can produce fresh=false/exit 2; retry, rather than treating stale state as completion.

**Action:** uv run codex-time status --plain

**Expected:** ASCII human output shows freshness, session count, cache path and up to 20 recent lifecycle states. No conversation body is printed. Tty is null/dash where exact process evidence is unavailable. The daemon may be stopped; raw terminal events still determine mid_turn/idle.

**Action:** uv run python scripts/verify-session-status.py

**Expected:** Private temporary rollout clones/copies produce cold/warm/unchanged timing metrics; warm/unchanged scans open zero raw files and read zero bytes. Every cached session field equals an independent full replay. Source rollouts, durable tracker data and the installed service remain unchanged. Progress is ongoing during large scans, and temporary message-bearing copies are removed at exit.

## Overview performance and exact accounting parity

Use the source repository root; no sudo is needed. The verifier copies the complete legacy or partitioned layout, quota, token and FX inputs into temporary storage, preserves the installed schema/token build, prepares its disposable index there, and removes copies on exit. Its output contains sizes/hashes/timings only.

**Action:** python3 scripts/verify-overview-performance.py

**Expected:** Four first/repeated CLI runs per build report seconds, with ongoing elapsed progress. Every optimized JSON field matches full historical computation; unchanged optimized runs reuse the report cache. The success message explicitly says temporary overlay only; live installation, daemon, rollouts and durable data remain unchanged. Timing is measured, not a guaranteed threshold.

**Action:** python3 scripts/verify-overview-performance.py --period week --date 2026-10-14 --runs 1

**Expected:** Exact parity for the selected weekly bounds, including allowance reset/conflict evidence, reasoning, uncertainty and token fields supported by the installed build. Source drift produces a refusal rather than a guessed patch.

**Action:** python3 scripts/verify-overview-performance.py --period month --date 2026-11-01 --timezone America/Toronto --runs 1 --plain

**Expected:** Full-report parity across the month containing the DST fallback, including an empty/future period when no work exists. Human progress/success output is ASCII. Each verifier invocation takes new frozen copies. Report cache identities include input/build/options and local-date boundaries; the verifier uses a fixed clock for exact FX metadata parity.

**Action:** After refreshing the installed package, run `codex-time overview`, then `codex-time overview --plain`, then `codex-time overview --json` from another directory without `uv run` or changing report options. Repeat after ordinary new work or new quota/token evidence; also select another date or timezone.

**Expected:** All modes retain token costs, allowance and model/reasoning totals. Unchanged inputs reuse private runtime accounting; changed evidence/options produce fresh totals. Long computations keep elapsed progress on stderr, and JSON stdout stays parseable. Overview and projects loading messages show `⏳ Reading ... report: Ns elapsed` about every two seconds; `--plain` omits the emoji, while `NO_COLOR` retains it. Fast reports finish silently without loading messages. Live source churn can prevent cache publication and require fresh computation. The existing daemon keeps running; reports never acquire its writer lock or rebuild/migrate its index.

## Token usage and estimated API costs

Run these from the repository root without sudo after package refresh. `token-smoke.py` uses the installed CLI by default; use `--executable .venv/bin/codex-time` for source verification. Its values are synthetic expected examples, not personal usage.

**Action:** ./scripts/token-smoke.py --scenario verify

**Expected:** `✅ Token smoke passed: 1,320,000 tokens; USD 2.91; CAD 3.9285 at 1.35.` (`CLI_PLAIN=1` omits the glyph). The next line confirms periods, child attribution, auto-review exclusion, replay and read-only reports. All-time/day/week/month and legacy day exports reconcile, repeated import preserves totals, and report reads leave durable data, FX and other runtime hashes unchanged; only the validated disposable overview cache may be created or replaced.

**Action:** ./scripts/token-smoke.py --scenario normal

**Expected:** Day total `1m 0s`; `1.32M tokens | USD 2.91 / CAD 3.93`; both directory rows keep `smoke-root` as the root-session ID, and `gpt-4.1` appears beneath session rows. Child-directory time is zero. The synthetic `codex-auto-review` child is excluded from token/cost totals and model rows, with an explicit exclusion note. The synthetic FX observation date is October 6, 2026; age varies with the current date.

**Action:** ./scripts/token-smoke.py --scenario narrow

**Expected:** A 32-column ASCII layout wraps directory/session/model, token and USD/CAD values without hiding them or emitting color escapes.

**Action:** ./scripts/token-smoke.py --scenario overview

**Expected:** `All recorded history`, `Estimated API token cost - Standard`, the model token subtotal and `Latest allowance snapshot`. No all-time consumption rate appears; this fixture has no allowance readings.

**Action:** ./scripts/token-smoke.py --scenario filtered

**Expected:** Only `/fixture/subagent` contributes: `220k tokens`, `USD 0.48 / CAD 0.65`, root ID `smoke-root`, and `0s` additional work. Week selection, exact cwd, root-session and archive filters remain available.

**Action:** ./scripts/token-smoke.py --scenario json

**Expected:** Clean JSON contains `token_usage.usage.tokens.total_tokens: 1320000`, exact USD/CAD strings numerically equal to `2.91`/`3.9285`, typed coverage, model hierarchy, dated pricing and FX metadata. Decimal strings may retain trailing zeros.

**Action:** ./scripts/token-smoke.py --scenario missing

**Expected:** The internal model remains visible with `1.32M tokens`, `USD unpriced`, `CAD unavailable`, and a `Known priced subtotal` warning. No guessed model alias or exchange rate is used.

**Action:** codex-time projects all --date 2026-10-06

**Expected:** Exit status 2 and `--date cannot be combined with all`; reports never start a network request or modify stored data.

Migration, billing limits, conservative restored-prefix behavior and rollback are documented in [the token-cost guide](token-cost-reporting.md); exact execution evidence is maintained in [the token-cost plan](../plans/codex-token-cost-reporting.md).

## Incremental storage and minute-cadence upgrade

**Action:** Run `uv run python scripts/verify-parity.py --plain --json` in the incremental-tracking checkout.

**Expected:** JSON reports `passed: true`; twelve actual CLI JSON/CSV/report comparisons and five retained aliases pass, including exact large token counters, waits, child exclusion, per-turn cwd, model/reasoning, FX and DST. Migration backup verifies and restart reports remain unchanged. With an installed, isolated native reader, list/report totals match exactly: the default six-session/seven-turn fixture reports 154,625,000,000 native nanoseconds. Missing native readers or conflicting system configuration are explicitly skipped, and interactive picker/resume coverage remains a separate runtime smoke check. Source fixtures remain unchanged; auth/config files are excluded. Only volatile FX `check_age_seconds` is normalized. Add `--work-dir /absolute/fresh-directory` to retain JSON evidence and portable fixture data.

**Recorded validation:** Final source parity passed all twelve comparisons and six aliases. The final wheel's six canonical JSON reports also matched the source reports. Its migrated fixture verified six sessions, seven turns, four unique quota readings and six unique usage observations; exporting it to the portable legacy layout preserved all six old-executable reports and native projections. Migration backup and restart checks passed. Performance-window evidence is recorded separately in the incremental-tracking plan.

**Action:** Build a wheel, install it into a fresh disposable virtual environment, and run `uv run python scripts/service-smoke.py --executable /absolute/venv/bin/codex-time --metadata-fixture --duration 300 --idle-seconds 300 --plain --json`. Add `--fixture /absolute/benchmark/fixture` to exercise measured history scale. --metadata-fixture generates matching read-only thread/turn/name history and excludes initial name bootstrap from steady windows.

**Expected:** The helper confirms installed wheel provenance, then observes five roots through working, waiting, unknown and real reconnect states. Precise lifecycle completion and 2.125-second known wait survive. A 65-second heartbeat remains running; uncertainty is at least 60 seconds, with outage provenance for missed polls. Five-minute active/idle CPU and RSS appear separately from startup and peer/harness resources. No descriptor growth, disallowed RPC or token-journal mutation occurs.

**Action:** Run `uv run python scripts/benchmark.py --baseline /absolute/deployed-checkout --work-dir /tmp/fresh-codex-benchmark --plain --json`, then repeat in another fresh directory with `--skip-baseline --scale 10 --soak-seconds 0`.

**Expected:** Progress continues on stderr and JSON stdout stays clean. Exact fixture/source hashes and history counts, ingestion/observation/persistence/projection timings, 300-second idle/active windows, 1,800-second fixed-input soak and repeated cycles are reported. Idle historical-file identities remain unchanged. Targets or misses are explicit; short runs cannot claim five-minute or soak validation. Tenfold history uses the same five active roots.

**Action:** With a fixture writer stopped, run `uv run python scripts/storage-recovery.py --data-dir /absolute/fixture-data --state-dir /absolute/fixture-state --plain --json verify`, then `export-legacy /absolute/fresh-legacy-export` with the same options.

**Expected:** Portable sessions/turns and exact unique quota/usage identities validate using disk indexes. Export publishes a new v4 ledger and combined journals only after count/hash checks, preserves current post-migration evidence and native records, and leaves its source intact. Old-executable reports match the new data. An existing destination or corrupt durable evidence is refused. Runtime index corruption is quarantined/rebuilt; isolated older session restores replay metadata rather than trusting stale signatures.

**Action:** Run `python3 /absolute/bundle/deployment.py --plain --json verify --bundle /absolute/bundle` against the prepared deployment manifest before requesting live activation.

**Expected:** Final/prior wheels, installed lineage, service definition and hashes are concrete. Activation and rollback use verified stopped-writer backups and current-data legacy conversion. Preparation does not change service state; activation requires the separate decision. After a failed rollout, verify whether the service is paused before declaring it healthy. No raw Codex source/config/auth files enter the bundle. Isolated rollback checks retain new timing, unrelated original files and valid cached FX; an offline actual report uses the same rate. Changed installation/unit hashes and corrupt/mixed backup artifacts refuse install.

**Action:** Against the installed corrected wheel, run the packaged service check above at minute cadence, then inspect actual service health and initial backfill before recording a five-minute production resource window. Include a disposable rollout whose ignored body exceeds the memory limit, with lifecycle fields after that body; append its newline only after the initial scan.

**Expected:** Ignored bodies stream without whole-record allocation; no raw body is stored. Exact lifecycle fields appear only after newline completion, once. The source checkpoint reaches the complete record boundary, backfill finishes without restart/OOM, and CPU/RSS measurements identify build and workload. A synthetic five-root pass alone does not establish production readiness. Explicit unsupported-metadata diagnostics and actual sampling uncertainty remain visible.

## Merged watcher and incremental-report contract

**Action:** From the repository root, run `uv run python scripts/verify-parity.py --plain --json`, then `uv run python scripts/verify-session-status.py` on disposable/frozen source copies as described above. No sudo is needed.

**Expected:** Report parity covers the v4-to-v5 migration and five aliases (burn, models, day, list, report). Status is a standalone watcher command with a sessions array; health retains the numeric count. Watcher cold/warm/full replay agrees and unchanged scans read zero raw bytes. Projects preserve token/USD/CAD evidence, while history/sessions/model-time skip evidence journals. Historical six-alias evidence above describes the pre-watcher build.
