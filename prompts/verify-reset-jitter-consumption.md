# Verify reset jitter consumption

Review the bounded reset-timestamp tolerance fix in track-codex-sessions. Read plans/fix-reset-jitter-consumption.md and the dated incident, then inspect burn.py and test_burn.py. Confirm ±10 seconds stays in one anchored cohort; ±11 seconds, manual resets, stale returns, conflicts and gaps remain separate. Run pytest, mypy and Ruff, then compare installed overview/allowance for Oct 20 with JSON. Do not change persisted observations or replace matched work with total model duration. Preserve unrelated work; no commit or push is authorized by this prompt.
