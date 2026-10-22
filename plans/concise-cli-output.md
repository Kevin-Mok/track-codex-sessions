# Concise CLI output

Make human reports easy to scan with totals first, readable thread/model rows and concise warnings. Implement compact formatting without changing accounting or exports, verify normal/narrow/plain output, then ship the matching code, tests and documentation.

## Scope and decisions

- Keep Python/Rich, existing commands/aliases, exact-directory/date/archive filters, all JSON/CSV schemas and tracking data.
- Default output shows working sessions/models and useful caveats. History collapses zero-activity sessions into an explicit count; details/JSON retain every selected session. Session search lists every result.
- `--details` adds stable IDs and compact input/cache/output/reasoning breakdowns. Full diagnostics, child identities, exact amounts and pricing/FX dictionaries remain in JSON.
- Use emoji headings by default, safe metadata wrapping, ASCII `--plain` and useful empty states. Slow human terminal reports update one progress line; redirected/JSON reports retain periodic stderr lines.
- Reuse the existing working-duration formatter for consistent seconds and positive subsecond work. No dependency, accounting, storage or migration changes.

## Protected baseline and commit scope

The first pre-write status had only two unrelated untracked files: `docs/postmortem/2026-10-15-overview-task-handoff.md` and `prompts/reduce-overview-startup.md`. Leave both untouched and uncommitted. All other candidate changes have directly observed session edits, including the earlier uv-cache incident.

The scope helper returned `unsafe` because it recognized no successful writes through the tool transport. Use the recorded pre-write baseline and successful parent/worker edits as the direct-write fallback. Do not infer ownership from timestamps. The eligible candidate contains 29 files: presentation/CLI/progress code, tests, README/smoke/token documentation, a lesson, this plan, the handoff prompt and two session incidents.

## Atomic implementation plan

- [x] Write presentation tests and observe expected RED for compact details, safe width/plain output, retained values and unchanged input/exports.
- [x] Simplify shared token/provenance formatting, projects and overview; centralize short timing and diagnostic notes.
- [x] Make sessions/history/health/status/import output readable; shorten allowance/model evidence.
- [x] Verify progress cleanup, redirected output, zero-activity history, singular labels and subsecond durations with defining RED/GREEN tests.
- [x] Run focused/full tests, typing, lint, build, real/synthetic rendering and installed replay checks.
- [x] Update README, smoke checklist, token guide, lesson and Cursor handoff; review and refresh the installed CLI.
- [x] Prepare the reviewed session candidate for one commit and configured-upstream push, with the staged privacy gate immediately before commit.

## Verification evidence

- Full stable-source suite: 572 tests passed in 88.14 seconds. Strict mypy checked 39 source files; Ruff and offline wheel/sdist build passed.
- Fresh commit checks: 108 focused presentation/CLI tests passed; Ruff, mypy and the README gate passed. No source changes followed the full suite.
- Fresh disposable display commands passed through the installed CLI: normal 26 lines, narrow 45 lines at 32 columns, and overview 27 lines. Synthetic usage/cost totals matched across views. Staged bytes match the reviewed working tree; 29 files are eligible, with no files over 3 MB and no baseline exclusions staged.
- Frozen same-data comparison at 120 columns: detailed projects output shrank from 171 to 31 lines with the same usage, time, model rows, stable identity and coverage caveats. Only aggregate layout findings are public; identifying snapshots stay outside the repository.
- Final installed rendering: 31 lines at 120 columns; 54 ASCII lines at 40 columns, all within width; 21 history lines with explicit zero-activity omission counts. All 11 changed installed modules byte-match the verified source.
- Synthetic installed replay: 1,320,000 tokens, USD 2.91/CAD 3.9285; periods, descendants, auto-review exclusion, idempotence and unchanged fixture storage all passed.
- Source/renderer tests cover 20/40/48/88/120 columns, Unicode/control sanitation, NO_COLOR/plain, empty data, missing pricing/FX and input immutability. Actual PTY checks confirmed one-line progress cleanup on success/error.
- Independent reviews found no accounting/export regressions. The stdout-redirection finding has defining RED/GREEN coverage in the final suite. Public docs were sanitized before staging.

## Reproduce the display checks

From this repository root, no sudo is required. Use `python3 scripts/token-smoke.py --scenario normal`, `--scenario narrow` and `--scenario overview` to inspect disposable reports through the installed CLI. These use synthetic history, do not access personal records and require no network. The isolated writer still uses the canonical lock directory, so restricted runners need approved lock access. Keep HOME/XDG unchanged and use the populated default cache for offline setup/build tests.

For real data, select `codex-time projects day --date YYYY-MM-DD --cwd /absolute/project --details`; replace the date/path with recorded data. Repeat at 40 columns with `--plain`, and inspect JSON for complete evidence. Live titles can change independently, so compare frozen layouts and identify live results by stable ID.

## Risks, rollback and review notes

Human wording intentionally changes; scripts should use JSON/CSV. Missing evidence must never look like zero/free usage. Roll back only these presentation changes and reinstall the preceding source if necessary; no history migration or daemon restart is required. The service and personal tracking data were left untouched.

Native command-selection/paste was not exercised because native computer APIs are unavailable; no renderer settings changed. The two resolved preflight incidents retain generic evidence and are reviewed in the canonical incident ledger; installed skill copies were not edited.

## Authorized delivery milestone

1. `fix: make CLI reports concise and readable`: implementation, tests, public documentation and installed verification are complete. Commit/push are now explicitly authorized by commit-session. Deliver this focused milestone on `main` to `origin/main`, with the two baseline exclusions left dirty. Keep this plan and all matching docs in the same commit. Report the resulting hash and actual push result in the handoff.

The session candidate has no remaining implementation blockers. Preserve Git hooks; the exact staged candidate must pass the shared privacy gate immediately before the commit. A failed push leaves the local commit intact and does not authorize rewriting history. The [Cursor handoff](../prompts/concise-cli-output.md) contains the continuation/test constraints.
