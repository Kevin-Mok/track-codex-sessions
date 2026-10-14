# Token reporting environment preflight

Record the execution-environment and inspection issues found while starting token-cost reporting, their scoped workarounds, and remaining limits. Repository work continues through approved execution after discovering the current file layout; application verification is recorded in the active token-cost plan.

## Symptom and impact

Two independent harmless default commands failed before shell startup with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. No repository code ran in either attempt.

A root `ls .agent` and an ingestion agent's `rg` inspection then failed because this repository has no `.agent` directory. The chained optional reads did not complete. The pricing agent's reads of guessed `runtime.py` and `config.py` paths also exited 2 because those files do not exist in the current package layout. These were source-discovery errors, not application failures; the failed reads modified no implementation or user data.

## Evidence and lookup

- Query `bwrap loopback Failed RTM_NEWADDR` matched canonical postmortem-memory guidance `references/execution-environments.md#ext-sandbox-loopback`, status `verified_workaround`. Identical pre-execution errors across harmless commands establish applicability. Approved `require_escalated` status and source-read commands then exited 0.
- Query `nonexistent optional path` matched `references/paths-ownership.md#local-discover-paths-before-reads`, status `verified_workaround`. The current repository inventory, absence of `.agent`, and missing guessed Python modules establish applicability. Test optional-path existence and inventory actual package paths before targeted reads.
- The canonical ExecPlan contract exists at `/home/kevin/linux-config/.agent/PLANS.md`; the parent task read it after establishing the local directory was absent.
- Official pricing research used the available HTML source when a proposed Markdown or web-rendered JSON representation was unavailable. That source-format fallback supplies no evidence of a product defect.
- `git status --short` was captured before changes in both repositories. The feature repository baseline is retained in `/tmp/codex-token-cost-baseline`; pre-existing changes in the canonical skill ledger and other linux-config files were preserved.

## Cause, resolution and status

The runner cannot initialize its restricted loopback namespace. This is independent of token reporting; the exact host policy behind the restriction remains outside this task. Approved scoped execution is a **verified workaround** with workaround-level evidence, not a repair to the default sandbox.

Inspection commands assumed optional paths and module names before inventorying the current checkout. Source discovery now checks existence and uses actual files. This is an inspection-workflow correction; it does not change application behavior.

## Verification and follow-up

Approved repository status, source reads, canonical guidance lookups, and ledger inspection exited 0. Continue scoped necessary commands through the approved route and preserve existing work. The token-cost implementation plan owns application tests and installation checks; these environment checks do not establish feature correctness.

Canonical learning decision: **no new reusable learning**. The incident repeats `ext-sandbox-loopback` and `local-discover-paths-before-reads`, so existing reference guidance remains unchanged. The current SHA-256 and this physical alias are registered in `/home/kevin/linux-config/dot_agents/skills/postmortem-memory/sources.json`. Its targeted `check --postmortem` completed with exit 0, no changed or new reports, no errors, and no missing sources or aliases. Verification compares every prior ledger report and finding with the captured pre-edit ledger: one report was added, none removed or modified, and other sections were preserved. The canonical ledger is the only learning writer; installed skill copies are not edited directly.

The required `fish -c 'refresh-config'` completed with exit 0 and `REFRESH COMPLETE` (log `/tmp/refresh-config-20261008-154230-2214137.log`). It snapshots live configuration, applies chezmoi, and regenerates/reloads shortcuts; no manual installed-copy edit was made. The final report hash is rechecked after this verification record.
