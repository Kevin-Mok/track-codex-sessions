# Overview task handoff byte-check failure

Record a compiler-side task-launch failure and verify a safe retry. The saved performance prompt and application data are unaffected.

## Symptom, impact and evidence

The first launch wrapper failed with `ReferenceError: TextEncoder is not defined` in `functions.exec`. The failing byte-count expression preceded `mcp__codex_tui__create_thread`, so no execution task was created and no duplicate launch occurred. Prompt save/readback had already succeeded.

## Lookup and diagnosis

Read the canonical postmortem-memory skill before remediation. Search query `TextEncoder is not defined` returned unrelated Python scope, graphical recovery and API boundary findings; the Python scope section applies to another host and is not a remedy here. Narrow query `TextEncoder` returned no matches. The documented V8 runtime has no Node environment, and the observed reference error confirms this global is unavailable. An existing unregistered report at `/home/kevin/linux-config/docs/postmortem/2026-10-15-metaprompt-handoff-byte-count.md` independently records the same missing global and ASCII-only workaround; it belongs to another task and was not edited.

## Resolution and verification

Rejected non-ASCII handoff characters explicitly, then used string length for the exact UTF-8 byte count. The complete handoff measured 319 bytes, below the 1,000-byte limit. One actual `create_thread` call succeeded with `isError: false` and returned `01a140a9-4ad4-7683-9a9d-7e1d5f943fea`, titled “Speed up overview startup”. The earlier failed wrapper never reached task creation.

The launch workaround is verified at runtime; overview performance remains unverified and belongs to that fresh task. No product implementation or live tracker data changed in this compiler task.

The initial learning scan passed the report file to `--root`, which accepts directories and returned exit 1 without reading any reports. Correct the scan to use the containing `docs/postmortem/` directory and select this report from its results; this is a helper invocation error, not another application failure.

## Learning decision and follow-up

No new reusable guidance: the runtime contract already excludes Node APIs, and the same workaround is documented in the independently existing report above. Register this report's final reviewed hash and alias in the canonical `sources.json` with that explicit decision; run the targeted coverage check. Non-ASCII handoffs require an available UTF-8 encoder or Python byte count. Do not infer application performance success from task creation.
