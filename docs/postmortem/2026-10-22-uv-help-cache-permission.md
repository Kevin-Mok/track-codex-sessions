# uv help lookup blocked by cache permissions

The installed CLI provides command help without accessing uv's build cache.

- Symptom: `uv run codex-time projects --help` exited 2 while opening `/home/example/.cache/uv/sdists-v9/.git`: read-only file system.
- Impact: source-checkout help could not run in this sandbox; no application behavior changed.
- Cause: the cache path is outside the workspace's writable roots.
- Resolution: `codex-time projects --help` exited 0 and confirmed period, date and exact-directory options. Status: verified workaround; uv itself was not repaired.
- Lookup: searched canonical postmortem memory for `uv cache Read-only file system`; broad unrelated results did not establish an applicable remedy. The direct error and successful installed CLI are the evidence.
- Learning: no new product defect. Canonical reviewed-hash/alias registration is recorded with the concise CLI task's verification in `plans/concise-cli-output.md`; installed skill copies are not edited.
- Next step: use the installed CLI for usage guidance. Later package/build verification used approved access to the ordinary cache rather than changing cache or application behavior.
