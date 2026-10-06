# Burn report terminal readability

This incident records the reported readability defect in `codex-time burn` and the verified terminal presentation changes. Verification covers styled output, narrow terminals, machine exports and the installed command.

## Symptom and impact

On October 6, the user pasted `codex-time burn day` output and reported that it was ugly and difficult to read. The display placed an epoch reset timestamp, compact decimal hours, several exclusion counters, a comma-separated model mix and raw quality flags in dense unaligned text. Important values competed with technical metadata, and the text had no terminal-width-aware layout or meaningful visual hierarchy.

The underlying accounting was not reported as incorrect. The failure was the operator-facing presentation: remaining allowance, observed burn rate and workload composition were difficult to find and compare.

## Lookup and evidence

Read the canonical `postmortem-memory` skill before remediation. Searches for `terminal readability raw flags dense table` and `terminal readability` returned generic terminal or artifact findings, with no applicable reviewed remedy for this layout defect. The supplied command output and `src/codex_time/burn_output.py` establish the symptom directly: the renderer joined unbounded strings and displayed internal quality names by default.

The existing canonical preference for skimmable terminal completion output is relevant in spirit, but does not establish a tested report layout. Source inspection confirms that terminal presentation had not received the same verification as accounting and exports.

## Root cause and resolution

The renderer exposed report internals directly instead of arranging them for a person scanning a terminal. Replace that projection with Rich formatting: a prominent allowance-remaining bar and local reading time, readable burn rate and duration, aligned model/reasoning work-share rows, and short explanations for accuracy and excluded consumption. Technical reset, flag and rounding metadata now lives under `--details`.

Automatic terminal colors, `--color auto|always|never`, `NO_COLOR`, and an ASCII/color-free `--plain` fallback are supported. Monochrome bars distinguish filled and empty segments without depending on color; narrow layouts stack model information. JSON and CSV retain the same accounting data.

Independent review also caught parallel plan/bucket streams being labeled as sequential reset runs. A defining regression failed before correction: only successive resets in the same stream now receive run labels; parallel streams show their plan/bucket caption. This was an intentional RED check during implementation, not an unexpected failure.

## Verification fixture failure

After ten intentional missing-feature RED failures, the first renderer check passed nine tests but failed the assertion expecting ANSI color. The inherited process environment already set `NO_COLOR`; the implementation correctly suppressed color. This was a verifier fixture defect, not a production color-suppression defect.

Before remediation, searched canonical memory for `inherited environment NO_COLOR test fixture` and `fixture environment`. The matching general `ext-realistic-fixture-boundaries` guidance supports testing the real boundary, but supplies no specific color-environment remedy. The corrected test explicitly clears `NO_COLOR` before asserting forced ANSI output and retains a separate test proving `NO_COLOR` suppresses styling, including explicit color requests. The full focused file passed after this correction; production behavior was not weakened.

## Verification and status

Status: verified fix. The source gates passed: 28 focused burn/output tests, 126 full pytest tests, strict mypy across 16 modules, Ruff, package build and 72 smoke checks. The output suite covers narrow layouts, long exact model IDs, hostile metadata, empty states, details, monochrome distinction and export parity.

An actual 80-column PTY showed styled remaining allowance, rate, five aligned model rows, visible excluded points and no raw default flags. After `./scripts/setup.sh`, all 16 installed module files matched source bytes. Installed `COLUMNS=40 codex-time burn day --plain` contained only ASCII, no ANSI escapes and no line longer than 40 columns. Installed `NO_COLOR=1 codex-time burn day --color always` suppressed ANSI while retaining visual cues. The installed report reflected continuing live observation; personal allowance values are omitted from this public verification record.

`./scripts/check.sh` exited 0 with the installed service active/running, a fresh heartbeat at `2026-10-06T17:35:50.497728Z`, and no live diagnostic. Accounting, persistence and export semantics were unchanged. Emoji rendering still depends on terminal/font support; `--plain` is the fallback. User aesthetic acceptance remains separate from these objective checks.

## Learning record

Reviewed this complete report and registered its current hash in canonical postmortem memory. Finding `local-terminal-report-readable-projection` records the runtime-verified presentation remedy; `local-terminal-color-test-environment` records the code-verified fixture correction. The targeted helper check must pass for this exact report. README, the allowance guide and grouped smoke checks document the same display controls and verification paths.
