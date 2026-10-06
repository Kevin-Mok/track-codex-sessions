# Model report preservation audit

Audit two timing differences after historical backfill before claiming that all pre-upgrade evidence stayed unchanged.

- Symptom: pre-upgrade completed-turn comparison exited 1 with AssertionError: 2.
- Impact: preservation assertion pending; no evidence of erased sessions, waits or model-report double counting. Need distinguish lifecycle reconciliation from unintended mutation.
- Evidence/root cause: among 42,331 old completed turns, one gained a recorded historical wait and one replaced a metadata_reconciled whole-second end with a precise rollout end (adding 0.583 seconds). These are the base app's existing evidence reconciliation rules, not lost timing. A diagnostic initially assumed every legacy turn serialized provenance and raised KeyError; validated ledger defaults and optional legacy provenance resolved that inspection issue.
- Lookup: search “rollout precise SQLite start end estimate” returned broad matches and the new pending-context join guidance; none specifically establishes these differences. Inspected existing ingestion/observer code and precise metadata reconciliation regressions, which support retaining the corrections.
- Resolution/status: verified audit. Validated pre-upgrade and current ledgers, asserted all IDs remain, every old wait/coverage span remains covered by current evidence, all completed starts/cwd remain equal, and the sole end change is an increasing precise replacement of a marked metadata estimate. Audit exited 0: no sessions/turns or wait/coverage evidence lost; v2 checkpoint has 4,734 incremental file offsets. Raw equality was too strict for lawful reconciliation; the revised evidence audit preserves the substantive requirement. No product change was required.

Follow-up: no new reusable learning beyond established precise rollout preference and additive wait evidence. Record actual audit scope in the ExecPlan; human accuracy limits remain unchanged.
