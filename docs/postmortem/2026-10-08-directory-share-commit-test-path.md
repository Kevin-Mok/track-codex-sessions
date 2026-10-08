# Directory-share commit verification test path

A focused commit check named a nonexistent test file. Verify test paths from the repository inventory before invoking pytest.

- Symptom: `uv run pytest -q tests/test_day_output.py tests/test_day_report.py` exited 4 with `file or directory not found: tests/test_day_report.py`; no tests ran.
- Impact: verification did not run; no application behavior or existing user changes were altered.
- Evidence: `rg --files tests` lists `tests/test_day_reporting.py` and `tests/test_day_cli.py`.
- Lookup: searched reviewed incident knowledge for `pytest file or directory not found`; matched `ext-optional-path-discovery` (verified workaround); the actual test inventory confirms its path-discovery guidance applies.
- Cause: the verification command inferred the report-test filename instead of reading the file inventory.
- Resolution: run the renderer, reporting and CLI suites using their actual paths.
- Status: resolved; corrected command passed 40 tests in 0.40s.
- Verification: `uv run pytest -q tests/test_day_output.py tests/test_day_reporting.py tests/test_day_cli.py` exited 0.
- Learning: no new architectural finding; registration under `/home/kevin/linux-config/dot_agents/skills/postmortem-memory/` remains outside this side conversation's repository mutation scope. The targeted read-only `check --postmortem` exited 1 and reported this new report as unregistered; external hash/alias registration is outstanding.
- Final verification: the exact staged snapshot passed the same 40 tests in 0.45s; mypy passed all 17 source files, and focused Ruff lint passed.
