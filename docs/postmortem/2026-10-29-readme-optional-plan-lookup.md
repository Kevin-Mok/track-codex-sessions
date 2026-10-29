# Optional plan instructions absent during README edit

The README edit encountered a missing optional plan-policy file. This report records the failed lookup and the decision to keep this small documentation change on an inline plan.

- Symptom and evidence: reading `.agent/PLANS.md` returned “No such file or directory” with exit status 2.
- Impact: no product or user data changed; the lookup did not block README work.
- Lookup: searched postmortem memory for `missing optional .agent/PLANS.md`. The documented `--compact` flag was rejected by this installed helper (exit 2); retrying without it succeeded. Finding `ext-optional-path-discovery` applies: inventory optional paths before reading. No product remedy was needed.
- Root cause: assumed the canonical instructions' referenced plan file existed in this checkout.
- Resolution: use the inline scope: add README setup, add a prioritized usage guide, verify commands and links. No implementation plan is needed for this small prose change.
- Verification: setup/check help, installed CLI help and uv shell-update help all exited 0. The new guide uses existing CLI commands. Documentation diff validation passed.
- Learning: check optional policy-file existence before reading. Canonical learning-store updates remain outstanding in `/home/kevin/linux-config/dot_agents/skills/postmortem-memory/` because that directory is outside the writable workspace; no installed skill copy was edited. The targeted read-only helper check reported this report as new/unregistered (exit 1), as expected until registration is permitted.
- Status: lookup resolved; canonical learning update pending.

## Delivery permission boundary

During the authorized commit workflow, the first `git add` could not create `.git/index.lock` because Git metadata is mounted read-only in the default sandbox. No files were staged by that failed call. The scoped approval route allowed the same stage operation to succeed. This is a verified permission workaround, not a repository repair; subsequent Git writes use that route. The canonical privacy scanner passed the exact staged candidates. No lock was removed and no history was rewritten.
