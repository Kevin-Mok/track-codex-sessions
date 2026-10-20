# Clear consumption shipment privacy blockers

Make the public tracker candidate pass the required privacy gate, then ship the already verified consumption fix. Neutralize personal path examples and a transport URL without changing recorded metrics, recovery behavior or private policy contents.

## Scope and authorization

The user approved a separate cleanup after commit-session was blocked. The original tracker HEAD and index both had 35 findings; the prepared fix candidate had 34. The initial unrelated untracked files remain protected: docs/postmortem/2026-10-15-overview-task-handoff.md and prompts/reduce-overview-startup.md. Keep the consumption implementation in its own follow-up commit. Baseline cleanup changes 29 path-bearing docs/fixtures/benchmark files and one SSH URL in historical documentation. Linux-config adds three exact-byte sensitive_path approvals and this task's reviewed records/status; unrelated knowledge changes stay excluded.

## Decisions and evidence

Use /home/example for public examples, preserving example/user placeholders. Benchmark numbers and original evidence hashes are unchanged; only identifying path strings change. Replace the documented SSH transport URL with HTTPS. Recovery module/CLI/test filenames are public code, not data: independent review confirms empty content-scanner categories and no private-literal/path-glob match. Approve only their exact path/content hashes for sensitive_path, using the documented existing manifest. Any byte edit requires new review; explicit private policy still wins. Reuse the already configured external private policy through tracker-local Git config; both Git identities already have approval there. Do not alter identities or private policy bytes.

Postmortem lookup: privacy gate false positives approved public identities neutral aliases -> local-privacy-reviewed-content-approvals, verified_fix/runtime. Its exact-byte mechanism and private-rule precedence apply; no scanner logic change is needed.

## Ordered checklist

- [x] Capture current Git states, scope and failing whole-tree gate evidence.
- [x] Review recovery source and exact hashes independently; confirm existing identity approval.
- [x] Anonymize baseline paths/URL and add exact-byte manifest entries.
- [x] Run fixture/recovery/consumption tests, privacy-gate regressions and README checks.
- [x] Run required refresh-config and record actual result (unrelated MIME drift stops apply).
- [x] Prepare and review the exact privacy-cleanup candidate; keep the consumption tree separate.
- [x] Gate prerequisite commits and preserve hooks; prepare the final consumption milestone for one verified series push per repository.

## Verification and delivery

Run tracker day-output/readability/recovery plus burn/overview/cache tests; strict mypy and Ruff. Run canonical tests/test_pre_commit_privacy_gate.py and gate the actual tracker index using its configured private policy. Test approval integrity by comparing all three exact hashes to indexed blobs; the existing regression suite must continue rejecting altered blobs and explicit private prohibitions. Run both README gates and refresh-config. Verify installed overview still has one reset cohort and over three matched hours. Verify commits contain only reviewed eligible paths; retain unrelated work.

## Risks and rollback

These edits sanitize the current candidate, not already published Git history. No history rewrite is authorized. Existing local Git identity and external policy are reused; local policy path is not tracked. Exact-byte approvals can expire after future edits. No runtime data or recovery APIs change. Roll back only with a new ordinary commit when requested; do not discard user work. Full 544-test suite was previously stopped at six minutes/26%; do not claim full-suite coverage.

## Progress and review

Approved scope is being prepared; no cleanup or consumption commit has been created yet. Learning-only commit 57c5e0d is already pushed separately. Next steps: focused verification, exact safety-gate checks and normal scoped commits/pushes.

Candidate verification: the first cleanup gate narrowed the baseline failures to one email heuristic triggered by the new plan describing the SSH transport spelling. Neutralized that explanatory text; no identity or private policy bytes changed.

Source verification: exact cleanup candidate privacy gate PASS, exit 0. Tracker 120 focused tests pass, strict mypy checks 37 files, Ruff passes; canonical privacy gate has 45 passing regressions. Recovery sources remain byte-identical to reviewed hashes, and private-rule precedence is retained. refresh-config exited 1 due pre-existing MIME drift; no force/adoption was attempted and source-gate activation is verified independently. Historical postmortem redactions receive reviewed hash updates with no new engineering finding. Privacy cleanup milestone `chore: sanitize public tracker evidence` is ready for exact staged review; consumption milestone `fix: tolerate quota reset timestamp jitter` follows it. No push until the verified local series is complete.

Prerequisite committed: `cc5f2e3 chore: approve reviewed tracker recovery source` in Linux-config, gated successfully and not yet pushed (one final push after the verified series). Privacy-cleanup milestone `chore: sanitize public tracker evidence` has no remaining candidate blockers; next is the consumption commit and final pushes.

## Verified commit milestones

- `cc5f2e3 chore: approve reviewed tracker recovery source`: four scoped canonical files, gate passed; unrelated knowledge/notes preserved.
- `6413191 chore: sanitize public tracker evidence`: 31 scoped tracker files, gate passed; consumption logic remained excluded from this prerequisite.
- `fix: tolerate quota reset timestamp jitter`: final delivery milestone includes the one-line anchored tolerance, signed/boundary regression tests and matching docs/plans. All source work and scoped verification are complete; gate this exact candidate, then push the verified series once per repository and report its resulting hash.

Remaining limits: required refresh stopped on unrelated MIME drift with no adoption; full544 suite remains incomplete. No source-safety or attribution blocker remains. Both initial untracked tracker files and pre-existing Linux-config work stay out. Final verification uses the real installed overview/allowance and exact public candidate gate; no runtime data rewrite or recovery API change occurred.
