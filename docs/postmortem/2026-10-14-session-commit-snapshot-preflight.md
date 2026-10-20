# Session commit exported-snapshot Git probe

Keep Git metadata checks anchored to the actual checkout while validating source from an exported snapshot. The failed probe did not stage, commit or change files.

## Symptom, impact and evidence

During prerequisite commit review, `git diff --cached --name-only` was accidentally run from `/tmp/codex-token-prerequisite-snapshot`, an exported checkout with no .git metadata. Git printed usage instead of an index listing. Independent README/source checks and the later Python ledger probe continued successfully, so the compound shell command ended0; its embedded Git failure is recorded separately. No repository or installed state changed.

## Lookup and applicability

Canonical query: `git diff cached outside repository exported snapshot`. The exported directory intentionally omits Git metadata; source/test checks belong there, Git status/index checks belong in the real authorized checkout. Existing path/working-directory and command-result guidance applies; no new reusable learning.

## Resolution and verification

Use `/home/example/coding/track-codex-sessions/.worktrees/token-cost-reporting` for index checks. The isolated prerequisite source snapshot independently passed306tests; mypy/lint/build are checked separately. Confirm actual-index listing and whitespace checks from the real checkout before staging. Keep all working-tree bytes and any original staging intact.

## Snapshot-probe verification

The corrected actual-checkout index listing and whitespace checks exited0, with no previously staged work. Exact prerequisite source passed306tests,mypy26source files,Ruff andbuild. The isolated index was reviewed and committed as625e824; current readability remained unstaged until its own reviewed commit boundary. No code remediation needed for this probe.

## Policy push rejection and ordinary merge

Symptom: initial `git push origin main` for policy commitd827816 exited1(non-fast-forward). No commit was lost and no history was rewritten. The remote had advanced independently: fetch identified origin/maineddd552,12remote-only commits across19files. Canonical lookup matched local-git-fetch-before-ancestry; applicability is concurrent remote progress requiring fresh ancestry rather than a force push.

Resolution: create the clean authorized `.worktrees/session-policy-push` checkout on chore/session-policy-push from locald827816. Ordinary `--no-commit --no-ff` merge of origin/main completed without conflicts and preserves both histories. Source overlap in README and helper-agent guidance merged cleanly. All dirty main working-tree and index bytes remain protected. Merge checks and exact push results belong to plans/allow-worktree-discretion.md and the delivery handoff; no rebase,reset,amend or force push is used.

## Current status and follow-up

Snapshot probe corrected; remote divergence reconciled in the clean merge candidate. Complete merge verification and normal configured-upstream push. Keep the active dirty main checkout intact, even if its branch cannot fast-forward without touching unrelated work. Canonical memory records no new reusable learning: existing scoped working-directory and fetch-before-ancestry guidance applies. Normal execution sandbox remains unchanged.
