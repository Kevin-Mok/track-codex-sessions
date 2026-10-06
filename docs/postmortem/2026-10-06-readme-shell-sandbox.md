# README editing shell sandbox failure

Record why the normal shell could not start during README work and how scoped commands continued.

- Symptom: three initial read-only commands failed before execution with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`.
- Impact: repository reads and status capture required the approved elevated execution route; no files changed during failed launches.
- Lookup: queried `bwrap loopback Failed RTM_NEWADDR`; reviewed `ext-sandbox-loopback` in canonical postmortem memory. Applicable because independent harmless commands returned the identical pre-execution error.
- Resolution: scoped `require_escalated` commands successfully read repository status and documentation. Initial status was clean.
- Status: verified workaround; the default sandbox remains unrepaired. This is runner startup failure, not a tracker defect.
- Verification: elevated `git status --short` exited 0, as did subsequent README/source reads.
- Follow-up: reuse the established sandbox-startup guidance; no new engineering lesson. Register this report in canonical memory.
