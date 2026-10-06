# Allowance history ledger observation latency

This report records runtime observation latency after adding quota history to the timing ledger. Preserve timing observation cadence by separating large history storage from the hot ledger path, then verify the installed observer before claiming activation.

## Symptom and impact

Runtime verification on 2026-10-06 found approximately **268,000 quota observations** embedded in an **84.6 MB ledger**. Measured operations were **4.01 seconds to read**, **1.06 seconds for an incremental scan**, and **1.07 seconds for serialization**, before the additional atomic pretty-write. The observer showed stale heartbeat risk and could introduce sampling gaps. Allowance tracking activation was pending until the hot-path storage correction and fresh runtime verification below; prior 101-test source verification was code-scope evidence only.

The native timetrace reader and existing native records were unaffected. No precision or service-health claim is based solely on passing source tests.

## Lookup and diagnostic evidence

Read the canonical postmortem-memory skill and searched `large ledger serialization heartbeat gap atomic write observation daemon`. No directly applicable quota-history hot-ledger finding was returned. The measured read/scan/serialize latencies and quota history size establish that embedding all snapshots in the repeatedly loaded and saved timing ledger does not fit the observer's cadence.

## Current status and next steps

Status: **verified_fix**; root-cause confidence: **confirmed**; verification scope: **runtime**.

Quota observations now persist in a separate validated append-only journal with a cached deduplication index, keeping accumulated history out of timing-ledger save/load. Storage regressions cover migration, idempotence, restart, duplicate union, corrupt persisted data, crash retention and restored-journal fingerprints. Reader caching and report filtering keep incremental observation work bounded.

Final fresh source gates exited 0: **114 pytest tests**, **16 mypy modules**, Ruff, build, and **60 smoke checks**. Installed source matched all **16 modules**. Actual migration retained **268,207 pre-migration quota observations** in a journal containing **268,213 observations**: **6 new observations, 0 lost, 0 duplicates**. The timing ledger returned to **37,695,231 bytes**.

Measured steady incremental scan: **0.691886 seconds**. Timing serialization: **0.580391 seconds** for a compact **25,026,016-byte** representation. Ten heartbeat samples over ten seconds observed **5 distinct heartbeats**, maximum age **2.129663 seconds**, and no live diagnostic. The service was active/running, and installed day/week JSON plus month CSV commands succeeded with matched numerator/denominator/model-mix conservation. These observations establish healthy live cadence for the measured run, not a guarantee of all future load.

## Learning review

Final review: finding `local-history-journal-observer-hot-path` records the verified history/hot-path storage boundary, migration conservation and live cadence scope. Canonical registration tracks the final report hash and alias. Unit tests remain insufficient to establish runtime cadence without installed observation evidence.
