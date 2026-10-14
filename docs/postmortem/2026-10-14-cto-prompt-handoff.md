# Cto prompt handoff preflight

Preserve the compiled cto performance prompt and start its executor exactly once. This records a compiler-side preflight failure before any new task existed.

The prompt was saved and read back successfully at prompts/speed-up-cto.md. The first handoff script failed at `new TextEncoder()` with `ReferenceError: TextEncoder is not defined`: the functions.exec V8 environment does not expose that browser API. Evaluation stopped before the create_thread call, so no execution was launched and no duplicate task needs recovery. No application or live data was changed.

Resolution: validate that the short handoff contains only ASCII, then use its character count as its UTF-8 byte count. Keep the tool's 1,000-byte limit. Look up `TextEncoder is not defined functions exec V8` before retrying; record the actual creation result in the task handoff. A successful creation establishes started, not completed. This is a host-API preflight assumption, unrelated to the reported cto runtime.

The lookup returned unrelated Python scope/process/stdin findings; none directly establishes JavaScript TextEncoder availability. The actual ReferenceError and pre-call control flow establish this failure. The replacement ASCII-only check verified a 301-byte handoff, and the native create_thread tool returned success with thread ID `01a13bca-efaf-7231-b606-fcf1e7f99761`. It was called once. This proves fresh-context execution started; runtime improvement is not yet verified by this compiler conversation. Prompt read-back matched its saved 4,454 UTF-8 bytes (SHA-256 c0aefa12c30cd9954ec840da1ee20dd89f1db3730086d24c4bf5b7e12fe77198).

No new application learning: this was a host-API preflight assumption, resolved using supported JavaScript string/regex operations. Preserve it as a reviewed no-new-learning incident; do not attribute any cto performance result to it.
