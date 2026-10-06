# Publish Codex Time on GitHub

Publish the reviewed application as a public GitHub repository. Verify the complete source, keep personal usage records local, make installation instructions portable, and push the initial main branch.

## Context and scope

The user explicitly authorized Git initialization and public GitHub publication after the session commit could not proceed without a repository. Initial preflight confirmed no Git metadata; `git init -b main` succeeded and `git status --short` captured all source paths as untracked before content edits. The active GitHub account is Kevin-Mok, and the requested project name is inferred from its directory: track-codex-sessions. No repository of that name appeared in the authenticated account inventory.

The initial commit includes the existing app, tests, packaging, scripts, service template, implementation plans, prompts and public documentation. Personal one-off allowance analysis and its numeric evidence/plan remain intact locally, excluded through .git/info/exclude. Existing cache/build/virtualenv exclusions remain effective. No changes to runtime data, Codex, the installed service or unrelated linux-config work belong in this commit.

## Decisions and risks

The commit-session helper returned unsafe because it found no earlier Git baseline or direct writes in its parsed session. The user's subsequent explicit initialization/publication authorization establishes scope for the reviewed initial application snapshot. No previous history is invented. Public documentation must not link to private local analysis. Preserve historical verification outcomes while removing live allowance readings. No license is selected on the user's behalf.

Review staged paths and content before committing; never stage credentials or runtime ledgers. Publication is public and the user explicitly requested it. Rollback before pushing is to leave the local repository unpushed; after publication, corrective changes use a new commit without rewriting history. This Python CLI has no web deployment target.

## Checklist

- [x] Confirm no Git repository, initialize main and capture initial status.
- [x] Confirm GitHub account and destination availability; review publication scope.
- [x] Run full application tests, typing, lint, build and isolated smoke checks.
- [x] Repair portable README setup, stack ordering and quota-journal layout; remove links to private analysis.
- [x] Finish independent privacy review, update related review records and inspect the staged diff.
- [x] Create the public GitHub destination and configure origin.
- [x] Verify the staged source in a disposable clean checkout before delivery.

## Verification evidence

Fresh checks all exited 0: `uv run pytest` (126 passed), `uv run mypy src` (16 source files), `uv run ruff check .`, `uv build` (wheel and sdist), `./scripts/smoke-test.sh` (72 passed, isolated native readers). README review found the original fixed home-directory install command, missing quota journal in its storage tree, and command overview ahead of stack rationale; all are corrected. The reusable publication check is recorded in docs/smoke-tests.md.

No application behavior changed during publication, so defining RED tests are not applicable; existing behavior tests ran fresh. Final remote checks use `gh repo view --json visibility,url,defaultBranchRef` and `git ls-remote origin refs/heads/main`, comparing the remote hash with local HEAD. Match this plan to the initial implementation commit; report final push results in the delivery response.

Independent review found no credential patterns or real session UUIDs in publication files. The 72-file staged inventory excludes personal analysis, runtime ledgers, caches and builds. `git diff --cached --check` passed. A fresh staged checkout installed all locked dependencies with `uv sync --frozen --python 3.12`, ran CLI help and passed 72 smoke checks (exit 0). README gate: update_in_same_change, repairs verified against CLI help and storage.py. No application or tracked configuration content changed during publication; installed service and configuration synchronization were unnecessary.

`gh repo create Kevin-Mok/track-codex-sessions --public --source=. --remote=origin` succeeded. `gh repo view` confirmed PUBLIC at https://github.com/Kevin-Mok/track-codex-sessions; origin uses the authenticated account's SSH protocol. Final delivery after this prepared snapshot is committed: `git push -u origin main`, verify public default branch and matching local/remote hashes, then report actual results. Those post-commit observations belong in the delivery response rather than a self-referential commit record.
