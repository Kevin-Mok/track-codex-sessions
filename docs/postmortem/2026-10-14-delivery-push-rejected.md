# Delivery push rejected by newer remote history

Preserve the verified local commits and record why the requested upstream push did not complete. Review incoming history before any future integration; never force-push to bypass this rejection.

## Symptom, impact and evidence

The single planned `git push origin main` exited 1. Git reported `main -> main (non-fast-forward)` and said the local tip was behind its remote counterpart. Destination: `https://github.com/Kevin-Mok/track-codex-sessions.git`. Local commits `48a8137` (daily wording) and `c51d2f1` (cache and overview performance) remain intact. Fresh `git status --short` was empty after the rejected push. No application, installation, service or tracker data was changed by the push.

## Lookup and applicability

Canonical postmortem-memory query `git push non-fast-forward rejected` succeeded. Reviewed `references/paths-ownership.md#local-git-fetch-before-ancestry`: fetch the authorized branch before ancestry checks, distinguish valid non-ancestor exit 1 from missing-object errors, and review protected state before a normal merge. It applies to a future integration investigation. No fetch, ancestry probe, merge or history rewrite is performed here; the explicit skill requires one push attempt and reporting rejection while preserving local commits.

## Status and next steps

Delivery remains local. Preserve the reviewed commits; a future integration pass must fetch and inspect `origin/main`, resolve any overlap without discarding work, validate the resulting tree, and push normally. No force-push, amend, rebase, reset, squash or automatic retry occurred. This documentation follow-up is committed locally with the delivery plan.

## Learning

No new reusable learning: standard non-fast-forward protection, already covered by fetch-before-ancestry guidance. Register this report with an explicit no-new-learning decision in canonical memory and run its targeted coverage check. Application verification remains 265 passing tests, clean Ruff and strict mypy, successful wheel/sdist build, synthetic cache full-replay parity, and installed schema-compatible full overview parity.
