# Daily report rerun preflight failures

Resume the requested daily-report workflow through approved scoped execution after the shell sandbox fails. Discover instruction files before reading them, then preserve and verify the existing implementation.

## Symptom, impact and evidence

The first read exited 1 before its command body ran: `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. The approved retry exited 0 and captured the pre-existing dirty state. A later context read exited 1 because it assumed a root AGENTS.md existed; inventory showed none in this checkout. The interrupted reads were repeated using discovered paths and exited 0. The read-only reviewer independently made the same root AGENTS.md assumption; its command exited 1, read lessons successfully, and changed no files. The parent supplied prompt/repository guidance and independently inspected the reviewed sources. No product or tracking data changed.

## Lookup and applicability

Canonical postmortem-memory search `bwrap loopback Failed RTM_NEWADDR` found `local-sandbox-loopback-approved-route` (verified_workaround). Its execution-environments reference applies to this identical wrapper startup error; command bodies had not run, and approved execution produced the expected reads. The existing daily-report-preflight report also records path assumptions. The first retry preceded lookup because the failing wrapper prevented skill retrieval; subsequent work used the retrieved guidance.

## Cause, resolution and verification

Sandbox failure occurs at loopback initialization; underlying host policy remains uninvestigated. Approved bounded execution is a verified workaround, not a host repair. The AGENTS.md read was a path assumption; inventory-driven reads fixed context retrieval. Both recovery reads exited 0. Preserve the existing feature work and use its plan for fresh verification. No additional reusable finding is needed: these symptoms and remedies are already covered.

## Learning and next steps

Register this report with a reviewed hash and explicit no-new-learning decision in canonical memory; run the targeted check. Continue read-only feature verification and update its living plan. Do not commit, push, restart services, or mutate recorded ledgers/native data.

## Canonical learning registration guard

The first registration script intentionally refused its write because the existing sources.json bytes differed from a sorted-key JSON serialization; its assertion failed before mutation. The subsequent required coverage check exited 1 and correctly identified this report as new. Canonical memory contains pre-existing dirty edits, so preserve its byte layout with a narrow insertion instead of reserializing unrelated entries. Search `sources.json formatting preserve unrelated dirty` found no directly applicable result in the inspected matches. The guard preserved the original ledger bytes. The replacement approach inserts only this reviewed report entry and parses the resulting JSON before writing; it retains every original byte outside the inserted record. This is a local serialization-assumption correction, with no new reusable learning beyond preserving unrelated work. Required targeted coverage evidence is recorded separately in the living task plan.
