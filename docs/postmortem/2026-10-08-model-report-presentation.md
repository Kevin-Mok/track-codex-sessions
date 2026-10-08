# Model report presentation verification

The model report redesign uses focused output tests and live installation checks. This report tracks unexpected verification outcomes while preserving unrelated daily-report work.

## Evidence and status

- Preflight cat AGENTS.md failed because this project has no local file; file inventory confirmed the inherited canonical linux-config instruction owner. A read-only reviewer also guessed the wrong package path before using src/codex_time. No files changed from those failures.
- Lookup: terminal report unicode width long model matched local-terminal-report-readable-projection; normal/narrow rendered verification applies to this change.
- GREEN attempt: 24 tests passed, three long Unicode-name cases failed a contiguous-name assertion at widths 70/88/120. Reproducer shows Rich wraps the full name across table lines with other cells interleaved. No characters were lost, but multiline names are harder to scan.
- Resolution decision: retain the regression assertion by rendering long names as stacked rows even in wider terminals. Default short names remain a compact table. GREEN/full/installed verification passed as recorded below.
- Root cause: table layout interleaves wrapped long names with adjacent cells, making intact reconstruction/readability awkward. Remedy: select stacked layout for names too wide for an ordinary model column.
- Follow-up: verify width, exact exports, no metadata escapes, and installed command freshness. Host sandbox remains a separately known limitation; scoped approved execution is used.

Focused GREEN: 27 tests passed (exit 0) after the adaptive layout change. A later optional Fish function path probe was absent; executable_snapshot-codex-config is the actual helper. The missing probe performed no writes.

## Resolution and final verification

Long model names now use stacked rows, preserving complete names and readable adjacent values. Independent review also found tiny positive shares rounding to zero only in stacked layouts; a shared percentage formatter passed its defining RED-to-GREEN regression. Final full tests: 180 passed; 126 smoke tests passed; strict mypy on 17 sources, Ruff, build and diff whitespace checks passed (exit 0). Reinstalled renderer and CLI bytes match source; installed day/week/month exports conserve exact microseconds, plain/details flags passed, and live daily reasoning/weekly grouped views were inspected. No accounting, storage or daemon changes were needed.

Learning: existing local-terminal-report-readable-projection covers these findings; no new reusable postmortem guidance. Added the specific shared-percentage-formatting lesson to project tasks/lessons.md. Default sandbox remains unrepaired; approved scoped commands are a workaround.

## Commit workflow evidence

Scope helper returned an unsafe attribution result with no recognized writes for inline Python edits; the recorded pre-write baselines and successful observed writes provide the required direct-write fallback. README gate initially rejected the tracker opening purpose wording, lowercase Tech stack heading and absent CLI heading. Its case-sensitive matching and first-section check additionally require stack proof before At a glance. Safe source-grounded README repairs are included. An optional guessed checker Python path was absent; the shell script is the gate implementation. No work was changed by that read failure. Lookup README gate heading false missing Tech Stack found ext-missing-readme-gate-fallback; the actual gate script and existing documentation content establish applicability and the required bounded repairs.

Commit verification: both README gates passed after the bounded repair; 30 focused tests, strict mypy and focused Ruff passed (exit 0). Session-only candidates were separately reviewed before staging; unrelated dirty state stays excluded.
