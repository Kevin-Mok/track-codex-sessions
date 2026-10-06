# Readable allowance reports in the terminal

Make `codex-time burn` useful at a glance: show remaining allowance, an understandable burn rate and model work shares, then offer technical evidence on request. Verify both styled terminals and plain redirected output before updating the installed command.

## Context, intent and boundaries

Kevin rejected the current terminal output as unreadable and asked for prettified output with helpful emotes like timetrace. Audience/context is the owner inspecting allowance from a Linux shell. Tone: compact, friendly, purposeful icons and restrained color. The feature already works; this task improves the human terminal surface. Files: burn_output.py, cli.py, pyproject.toml/uv.lock, output tests, README, guide and smoke checklist. All timing/accounting/persistence and JSON/CSV values stay intact. Preflight confirmed there is still no Git metadata here; preserve prior implementation and data, no worktree/commit/push.

## Decisions

Use Rich for terminal-cell-aware wrapping, alignment and restrained ANSI colors rather than maintaining custom Unicode-width/layout code. Default output: clear title/date/timezone, remaining allowance and bar with local observation time, per-date/reset workload sections with headline rate and matched points/working duration, model/reasoning rows, visible excluded consumption and concise accuracy note. Keep low confidence explicit. Rates are pp per summed root working hour and model shares describe work, not quota allocation. Multi-reset periods retain separate rows and human-readable cycle labels.

Add --details for raw quality/reset/provenance selectors/rounding/timing evidence; --color auto|always|never defaults to TTY auto and respects NO_COLOR; --plain is ASCII/color-free with the same essential numbers. JSON/CSV bypass styling entirely. Escape/sanitize metadata before terminal rendering. Narrow terminals stack model details; long IDs wrap, rates remain visible. Empty and missing-latest states provide clear guidance. Existing user intent supplies design context; no further design approval is needed for this reversible presentation change.

## Checklist

- [x] Inspect current renderer, CLI, tests, active plan and UI guidance; capture initial workspace state.
- [x] Write defining output/CLI tests and observe RED.
- [x] Implement responsive formatting, icons, colors and progressive disclosure.
- [x] Update docs/smoke checks and record the reported UX defect/learning.
- [x] Run tests, type/lint/build/smoke checks; inspect 40/80/120-column terminal output and export parity.
- [x] Reinstall entry point, verify real output and service health, record final evidence.

## Risks and verification

Emoji width varies by terminal/font; Rich handles standard cell widths, --plain supplies a reliable ASCII fallback. Color cannot be the only signal. Long model names and metadata control codes must not distort the terminal. Never combine distinct allowance reset rows into an invented aggregate rate. Default accuracy notes must retain substantial excluded consumption and low confidence even when raw diagnostics move behind --details.

RED: uv run pytest -q tests/test_burn_output.py. GREEN: focused tests, then uv run pytest, uv run mypy src, uv run ruff check ., uv build and ./scripts/smoke-test.sh. Use real PTYs at 40/80/120 columns for visual inspection and NO_COLOR/pipe checks. Reinstall with ./scripts/setup.sh; no ledger/schema changes, then ./scripts/check.sh and installed burn day/week/month. Rollback affects renderer/CLI/dependency only; data formats unchanged. Match plan/doc changes with any future implementation commit. Suggested subject: feat: improve allowance report readability.

## Progress and review

Polish skill applied with terminal-specific constraints: visual hierarchy, aligned columns, readable copy, progressive disclosure and width-aware layout. Rich official Console/Tables docs inspected for wrapping, color and plain output APIs. User-provided screenshot text is the reproducer; dedicated docs agent owns living incident and canonical reviewed learning.

RED: 10 defining output tests failed for missing readable summary/display controls before implementation. GREEN: 27 focused burn/output tests passed; strict mypy 16 modules and Ruff pass. One fixture initially inherited NO_COLOR and incorrectly expected ANSI; explicit environment isolation corrected it, and a separate test proves NO_COLOR overrides requested styling. Monochrome bars now distinguish filled segments from dotted remainder; ASCII mode uses readable separators.

Final source gates exit 0: 126 pytest tests, mypy 16 modules, Ruff, wheel/sdist build, 72 isolated smoke checks. Real 80-column PTY with TERM=xterm-256color and NO_COLOR removed showed ANSI emphasis, readable local time, remaining allowance, burn rate, aligned model work rows and explicit excluded consumption. Pure output inspected at 40/80 and independent review at 40/80/120; automated width checks cover 32/40/80/120, Unicode long IDs and ASCII/control sanitization. Reviewer caught a parallel-stream label ambiguity; defining regression observed RED before showing plan/bucket captions instead of sequential Run labels for distinct streams. JSON export remains identical with display flags and --color always; plain/details remain ASCII without ANSI.


## Final installed verification

`./scripts/setup.sh` exited 0 and installed Rich 14.3.4 with its locked dependencies. Installed help exposes --details, --plain and --color. All 16 installed Python modules match source bytes. `COLUMNS=40 codex-time burn day --plain` produced only ASCII, no ANSI, and no line wider than 40 columns. `NO_COLOR=1 codex-time burn day --color always` retained icons/structure with no ANSI and no raw quality flags. Actual output showed remaining allowance, current rate, aligned model/reasoning rows, and explicitly excluded consumption. `./scripts/check.sh` exited 0 with service active/running, fresh 2026-10-06T17:35:50.497728Z heartbeat and no live diagnostic.

Final code gates: **126 tests, mypy 16 files, Ruff, build, 72 smoke checks**, all exit 0. No accounting/storage/schema changes; no data migration required. No Git commit/push/worktree. Source pyproject/lock changed in this non-Git workspace; no tracked linux-config configuration changed, so refresh-config does not apply. Existing user work was preserved. Remaining platform limit: emoji appearance depends on terminal/font; --plain is verified ASCII fallback. Independent reviewer found no remaining material issue after the stream-label correction. Handoff: [maintenance prompt](../prompts/codex-burn-terminal-ux.md). Reported issue and validation correction: [living postmortem](../docs/postmortem/2026-10-06-burn-terminal-readability.md).

Final learning closeout: UX postmortem and canonical readable-projection/color-test-environment findings updated with reviewed hashes; targeted check exited 0 with no errors. Durable terminal readability preference appended to canonical feedback log.
