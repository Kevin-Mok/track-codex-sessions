# Token reporting verification handoff

Use this prompt to review or continue the implemented token-cost feature. Read the active plan, preserve unrelated work, reproduce the fixtures and installed CLI checks, then address any observed failure before updating evidence.

```text
Work in /home/kevin/coding/track-codex-sessions/.worktrees/token-cost-reporting
on feat/token-cost-reporting (based on HEAD 66d221d). Read applicable AGENTS instructions,
plans/codex-token-cost-reporting.md, docs/token-cost-reporting.md and current source.
Capture git status --short before edits. Preserve the original checkout’s pre-existing
daily-report work; only this task’s changes belong in this worktree.

Verify overview/projects [day|week|month|all] tokens and Standard API estimates by
recorded directory, root session and actual model. Children count once; forks
exclude inherited usage; working-time accounting stays unchanged. Check v3->v4
backfill, duplicate/reset/partial/restored-prefix evidence, missing parent/child
coverage, orphan/model/cwd attribution, exact USD/CAD Decimal values, request-sized
long-context rules, cached FX scheduling/failures and report read-only behavior.
Exclude exact model codex-auto-review from token/cost totals and breakdowns, while
retaining durable evidence and existing working time. Other unknown models remain
visible/unpriced. Unknown or unavailable usage must never look like priced zero. All-time shows the
latest eligible allowance snapshot independently of the latest activity date.

Run fresh, without sudo:
.venv/bin/pytest -q
.venv/bin/mypy src
.venv/bin/ruff check .
uv build
./scripts/smoke-test.sh
git diff --check

Verify the installed executable after the documented package refresh:
./scripts/token-smoke.py --scenario verify
./scripts/token-smoke.py --scenario normal
./scripts/token-smoke.py --scenario narrow
./scripts/token-smoke.py --scenario overview
./scripts/token-smoke.py --scenario filtered
./scripts/token-smoke.py --scenario json
./scripts/token-smoke.py --scenario missing

Keep docs/smoke-tests.md, README and the active plan aligned. For any new bug,
observe a defining RED test before fixing it; follow canonical postmortem memory.
Read-only reports never fetch FX or migrate data. Before live writer migration,
save a complete data/runtime backup and preserve the service's existing options.
Rollback requires the matching v3 backup and prior executable, not a version-tag edit.
The user requested this worktree; no commit or push is requested. Suggested eventual atomic commit:
feat: report session token usage and estimated API costs
Include matching implementation, tests, docs and plan in that commit. Handoff needs
fresh evidence plus 5–10 smoke commands with an expected-output block after each.
```
