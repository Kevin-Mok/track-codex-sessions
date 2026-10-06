# Model report installation cache

Ensure reinstalling the local app deploys its changed source rather than reusing a wheel cached under the same package version.

- Symptom: `scripts/setup.sh` exited 0 and restarted the service, but installed `codex-time models day --help` rejected models. Installed Python still reported ledger version 1 and no model_usage module.
- Impact: new feature had passed source tests but was not active in the installed command/service. Existing data remained v1; pre-upgrade backup was taken before setup.
- Evidence/root cause: setup uses `uv tool install --force` with unchanged pyproject/version. `--force` replaces entry points but does not invalidate a cached local wheel. Installed source differed from current source.
- Lookup: search “uv tool install local package stale cache reinstall” returned local-deployable-file-set-verification; reviewed its artifact-verification guidance. Applies to source/live byte comparisons, not uv cache invalidation; local uv help confirms --reinstall-package implies --refresh-package. Local `uv tool install --help` provides refresh/reinstall flags.
- Resolution/status: verified fix (runtime package installation). The real-uv disposable setup test first failed because a second installation printed old source, then passed after adding --reinstall-package codex-time. Real setup built a fresh local wheel (exit 0); installed models day --help now succeeds, installed ledger defaults to v2, and all 14 installed Python modules exactly match local source. Full suite 86 tests, mypy, ruff, build and smoke 32 tests pass. Initial service history backfill is separately verified in the ExecPlan.
- Follow-up: source tests alone do not establish installed runtime activation. Keep setup docs/tests aligned.
