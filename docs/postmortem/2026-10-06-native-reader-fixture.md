# Native reader fixture expected a display name instead of a project key

The isolated native reader successfully loaded tracker records, but its list output displays project keys. Verify key/tag identity and exported duration totals instead of assuming a display-name column.

## Symptom and impact

On 2026-10-06, the daemon/UI/restart integration test passed; the initial native compatibility test failed because `/fixture` was absent from `timetrace list records`. The native command exited 0 with two record rows. Only a disposable isolated HOME and store were accessed; existing ~/.timetrace was never used.

## Lookup and applicability

Query: `native reader project display fixture`. Existing API-contract/fixture guidance requires fixtures to match actual consumer schemas. Inspect actual list/report output before changing assertions. The native format itself loaded correctly; the test assumed that list showed the name rather than the key.

## Status and next steps

Inspect sanitized native output and report JSON. Assert actual fixture project key, session/turn tags and exact summed duration, plus unchanged JSON record bytes. Rerun compatibility and retain the isolated HOME/config boundary.

## Resolution and verification

Actual native output shows the fixture project key and both session/turn tags. Native JSON report exports two records totaling 30,000,000,000 nanoseconds (30 seconds). Assertions now check those identities, exact duration and unchanged durable JSON bytes. `uv run pytest tests/test_observer.py tests/test_live.py tests/test_native.py` passed 19 checks (exit 0), including the native reader. Status: resolved; the test assumption was corrected without weakening duration or isolation checks. Existing records remain untouched.
