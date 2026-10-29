# Overview usage across resets

Show observed allowance usage for the selected period across reset cycles, separately from the current-cycle balance. Preserve rate matching, exclusions and JSON schemas.

- [x] Diagnose: overview renders latest balance and separate reset rows, with no combined usage.
- [x] Add defining regression tests and observe RED: 4 expected failures, 1 guard test passed.
- [x] Sum matched, gap and no-work points for one allowance stream; exclude cross-day points explicitly. Count distinct reset identities, without guessing full-cycle expenditure or reset timing.
- [x] Clarify current balance; document and verify normal/plain/narrow output, missing readings and parallel streams.
- [x] Refresh installed command and verify actual overview.

Scope: overview_output.py, test_overview.py, README, smoke tests and incident documentation. No changes to journal data, collection or rate calculations. Rollback is reverting the renderer/documentation changes. Commit-session authorized after implementation verification.

Risk: rounded readings and missed reset intervals make this an observed partial total, not exact billed or full allowance consumption. Never add parallel streams. Preserve all-time snapshot behavior.

Verification: defining RED 4 expected failures; final overview/burn/command-layout suite 81 passed. Full suite 627 passed in 83.94 seconds with filesystem access for normal global lock creation; sandboxed run had read-only lock failures. Ruff passed; mypy passed 39 modules with a temporary cache; git diff --check passed. Source equals installed renderer after offline same-version uv reinstall. Installed live report: 7 observed points across 2 cycles, 5 matched + 2 unmatched, 66 cross-day points explicitly excluded. Normal, 32-column plain and details installed CLI all show synthetic 106 points across 2 cycles while current balance remains 8% used. Review found no accounting issues. README gate: update_in_same_change; README and grouped smoke expectations updated.

Manual plan: run overview for Oct 29 normally, with --plain at COLUMNS=32, and with --details. Expect combined observed usage across 2 cycles, distinct current balance, and explicit boundary uncertainty; live totals may grow. Automated plan: pytest tests/test_overview.py tests/test_burn.py tests/test_command_layout.py, full pytest, Ruff and mypy. No sudo is needed for usage.

Cursor prompt: Review src/codex_time/overview_output.py and tests/test_overview.py against this plan. Preserve cohort replay, current balance, JSON schemas, and parallel-stream guards; verify combined observed points include unmatched in-period deltas and exclude cross-day changes. Run the automated and manual checks above; keep documentation aligned.

Delivery milestone — `fix: show observed allowance usage across resets`: implementation, docs, regression coverage and installation complete. Fresh commit-session checks: 81 focused tests passed in 8.91 seconds; Ruff and mypy (39 modules) passed. Prior unchanged-source full suite: 627 passed. README gate passed. Scope helper returned unsafe because it did not detect cross-directory writes; use direct-write evidence and the captured clean tracked-file baseline. Leave the three pre-existing untracked documents untouched. Commit and upstream push are the remaining delivery steps. Canonical postmortem-ledger registration is shipped separately in linux-config with only the current report entry staged. Rollback: restore the renderer and reinstall the local package, retaining all journals.
