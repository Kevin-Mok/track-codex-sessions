# Daily report workflow preflight failures

Two read-only preflight commands failed before feature work. Approved execution and source-discovered helper paths allow work to continue without changing host policy.

## Symptom and impact

The first two default-runner reads exited 1 with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`, before their command bodies ran. A later private-context lookup exited 2 because the guessed helper filename did not exist. No product or tracking data changed.

## Evidence and lookup

`git status --short` through approved execution exited 0 with empty output before the first write. Identical scoped reads then succeeded with exit 0. Search query `bwrap loopback Failed RTM_NEWADDR` matched `local-sandbox-loopback-approved-route`; its reference applies to the identical pre-start failure and recommends an approved route. Search `personal_context.py missing helper` returned no direct finding. Source inventory and store-format.md identify the real helper as context_store.py.

## Cause, resolution and status

Sandbox cause is supported at the wrapper initialization boundary; underlying host policy remains uninvestigated. Approved scoped command execution is a verified workaround. Helper failure came from assuming a filename before reading its routing reference; use the documented actual path. The documented context_store.py topics and brief --topic design commands both exited 0; no private evidence was copied into repo artifacts.

## Next steps and learning

Continue feature work through approved scoped execution. The documented helper is verified; retain the sandbox limitation. Register this report in canonical postmortem memory, linking the existing sandbox workaround and recording the helper discovery lesson. This is tooling evidence, not a product fix.
