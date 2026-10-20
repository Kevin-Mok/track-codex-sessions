# Daily report readability preflight failures

Restore scoped command execution and identify the installed report source before changing its presentation. Approved execution bypasses the environment failure; the host sandbox remains unresolved.

## Symptom and impact

Default read-only command launches failed before execution with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. Initial discovery also assumed absent `.agent/PLANS.md`, `dot_config/shortcuts`, and `personal_context.py` paths; authoritative files were subsequently located. No application changes resulted from these attempts.

## Evidence and applicability

Memory query: `bwrap loopback Failed RTM_NEWADDR`; matching `ext-sandbox-loopback` and `local-sandbox-loopback-approved-route` are verified workarounds. Identical wrapper errors on harmless independent reads confirm applicability. Scoped `require_escalated` reads and `git status --short` then exited 0. Read the matching execution-environments reference. The canonical plan contract is `/home/example/linux-config/.agent/PLANS.md`; private helper discovery found `context_store.py`, whose topics/brief commands exited 0. Missing-path probes were corrected by file discovery.

## Current status and next steps

Command execution has a verified approved-route workaround; no host security settings were changed. The installed command's direct_url.json points to the existing `.worktrees/token-cost-reporting` checkout. It includes token/cost output absent from main. The user explicitly authorized this existing checkout and removal of the worktree restriction; preserve token/cost data and all pre-existing edits.

## Resolution, verification and follow-up

Approved-route inspection and the installed daily report exited 0. No new reusable incident learning: existing approved-route and source-provenance guidance apply. Keep normal sandbox repair separate. Canonical memory records this reviewed report with a no-new-learning decision; targeted coverage verification follows.
