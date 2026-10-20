# Commit and push sandbox startup failure

Deliver the reviewed dirty worktree using scoped approved execution while preserving all existing changes. This report records the command-runner failure and its verified workaround.

## Symptom and impact

Two initial read-only commands exited 1 before their bodies ran with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. No repository changes occurred. Approved execution then read the required skills and captured the initial Git status, branch `main`, and upstream `origin/main`, all with exit status 0.

## Lookup and applicability

Query: `bwrap loopback Failed RTM_NEWADDR`. Canonical memory returned `local-sandbox-loopback-approved-route` and `ext-sandbox-loopback`, both verified workarounds. The execution-environments reference applies: identical errors affected independent harmless reads before startup, and scoped approved reads produced their expected output. Skill retrieval required the alternate route before lookup could execute.

## Resolution and limits

Scoped `require_escalated` execution restores command access for this delivery. The host sandbox remains unresolved; no host-policy change is attempted. Product behavior, tracking data, installed package and services are unaffected. Continue checks, stage only reviewed files, commit in prerequisite order, and push once.

## Learning

No new reusable learning: this repeats the existing approved-route workaround. Register this report's reviewed hash in canonical postmortem memory and run the targeted coverage check. Delivery evidence belongs in `plans/commit-plan-push.md`.

## External learning-ledger drift during delivery

Initial narrow registration succeeded and targeted coverage passed with 227 findings, no errors, report hash `024ba5ec41e8e2262e5366c019dfe5a150ebacdf0546f96a10ff2d4948548d2c`. A subsequent read-only coverage pass observed 222 findings and reported this incident and the existing CTO overview incident as unregistered; resource/cache/prompt incident checks still passed. A following metadata read failed JSON parsing at line 9455, character 529533. This task made no intervening canonical writes. These changed observations establish external ledger drift, without attributing ownership or cause.

Preserve `/home/example/linux-config/dot_agents/skills/postmortem-memory/sources.json` and its unrelated dirty changes; do not reserialize or reconstruct it during this delivery. Canonical learning is currently incomplete: re-register this report's final hash and restore/verify the CTO report's reviewed coverage once the external ledger is valid and stable. The existing no-new-learning sandbox decision still applies; this is a documentation dependency warning, not an application regression. Main's tests, builds and runtime parity remain green.

A later lookup succeeded after external ledger validity returned. The registration guard intentionally refused to insert a duplicate alias when the original sandbox record reappeared; no write occurred. Targeted checks then identified that record's old hash and the new push report's absent registration. Update only the sandbox record's hash (its findings list is empty) and insert the new no-new-learning push record, preserving all other text.
