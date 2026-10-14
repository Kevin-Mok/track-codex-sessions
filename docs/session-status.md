# Session state for outside watchers

Use `codex-time status --json` to check sessions without rebuilding accounting history. The first call builds a private cache; later calls stat rollouts and read only changed files. Check freshness and lifecycle state before acting, and retain your own previous snapshot if you need completion transitions.

## Run from this checkout

No sudo is needed. Use `uv run codex-time status --json` until this source is installed; the existing installed command may still implement the old health-only alias. Global directory options go before `status`:

```bash
uv run codex-time status --json
uv run codex-time --codex-home /absolute/codex-home --state-dir /absolute/private-state status --json
uv run codex-time status --plain
```

The command observes source files read-only and writes only its own runtime cache/lock/staging files. It works with the daemon stopped, without loading a timing ledger or quota journal, launching Codex, or polling the control socket. Long rebuilds and lock waits show elapsed progress on stderr. Stdout with `--json` contains exactly one JSON object. `--plain` makes human output/progress ASCII; `NO_COLOR` does not remove normal emojis.

`status` was previously a hidden alias for `health`. It retains the top-level observer-health fields (`daemon`, `heartbeat`, `pid`, `live_diagnostic`, `data_dir`, `state_dir`), but `sessions` is now an array. Use `health --json` when you need the previous numeric session count and accuracy diagnostics.

## JSON contract, version 1

Each `sessions` element contains:

| Field | Meaning |
| --- | --- |
| `session_id` | Stable ID from session metadata, or null if none was readable |
| `rollout_path` | Absolute source path; cache identity key |
| `cwd` | Latest session metadata/turn-context directory, or null |
| `tty` | Exact process evidence such as `/dev/pts/17`, otherwise null |
| `status` | `mid_turn` after an unmatched task start, otherwise `idle` |
| `last_user_message` | Latest user text, or null |
| `last_assistant_message` | Latest assistant text, including commentary, or null |
| `last_updated` | Latest valid source event timestamp, normalized to UTC, or null |

Only text message blocks and explicit user/agent message events are retained; reasoning, tool results and inter-agent communication records are excluded. Message strings are complete and may contain newlines or terminal controls: treat them as data and escape them before rendering. Never execute message content.

Lifecycle events determine `status`: `task_started` opens a turn; matching `task_complete`/`turn_aborted` closes it. Assistant commentary or a final answer alone does not prove completion. `idle` means there is no unmatched known start; older files without lifecycle evidence also start idle. It does not establish that a process exited or that a session was loaded. A lost terminal event can leave `mid_turn` until later evidence arrives. Tty may be unavailable for a shared backend or inaccessible/exited process; the command never guesses by cwd.

Top-level `fresh: true` means the discovered sources were readable and stable during their bounded reads. A partially written final JSONL record remains pending; the snapshot describes complete records only. Malformed complete records are skipped. Changes after a file was checked are visible on the next invocation. `fresh: false` returns exit status 2 and may retain prior per-file state when a source was unavailable; retry before drawing conclusions. Other failures return 2 with an actionable stderr message. Successful empty history returns an empty array and exit status 0.

`checked_at` is the UTC observation time, not a source event time. `scan` reports `files`, `opened`, `bytes_read`, `cache_hits`, and `rebuilt`. With unchanged rollouts, `opened` and `bytes_read` are zero, even after restarting the command. Source discovery/stat and exact tty lookup still occur. `version`, `home`, and `cache_path` identify the output/cache contract and source root. Preserve unknown future fields and reject unsupported versions in strict consumers.

For an hourly completion watcher, compare the previous successful snapshot with the current one: a `mid_turn` → `idle` transition is completion evidence. Do not treat missing/deleted entries or `fresh: false` as completion. Several turns may start/finish between checks; this snapshot is not a completion-event journal. Record `last_updated` and the last assistant message if useful, but do not use a changed message alone to infer a terminal event.

## Cache location, privacy and recovery

The default path is `$XDG_STATE_HOME/codex-time/<data-root-hash>/session-status.json`, with `~/.local/state` as the default state base. `--state-dir` overrides its directory. The command reports the exact `cache_path`. The runtime directory is 0700 and newly published cache/lock files are 0600. Latest message text can contain sensitive information; keep the cache out of shared Git repositories and public backups. Durable timing ledgers, accounting projections and observer checkpoints remain content-free.

The disk cache is `{version: 1, home: <resolved Codex home>, files: {...}}`. Each absolute-path entry stores `dev`, `ino`, `size`, `mtime_ns`, complete-line `offset`, `current_turn`, and `state` with the fields above. It contains no full conversation history. Source size/mtime equality plus device/inode identity is a hit. Growth seeks to the saved byte offset; truncation, same-size rewrite or inode replacement rebuilds only that file. Arbitrary same-inode rewrites that also grow are outside the append-only source contract. The accounting ingester separately verifies up to 256 prefix bytes on changed files to preserve its older in-place-rewrite detection.

New paths are added; deleted paths are removed after a complete successful traversal. Archive moves change path identity, so the compact cache rebuilds the moved file. A corrupt, unsupported-version, home-mismatched or invalid-offset cache is disposable and rebuilt. Writers serialize through a separate cache lock and publish a same-filesystem temporary file with fsync and rename. Concurrent file readers see an entire old or new JSON document.

Refresh is **on demand**: the daemon does not publish this file. Prefer the command for watchers; a direct file read alone does not establish current freshness. There is no TTL that forces unchanged history to be reparsed. Removing only this disposable cache forces a rebuild on the next command; never delete or edit raw rollouts to refresh it.

## Reproduce performance and parity safely

From the repository root, run the reusable verifier below. It clones/copies rollouts into temporary storage, builds a cold cache, runs two unchanged checks, and compares every session field with an independent full replay. It prints only counts/timings and removes temporary message-bearing artifacts. Allow free disk space comparable to the rollout tree when filesystem cloning is unavailable. Large histories take minutes; progress continues on stderr.

```bash
uv run python scripts/verify-session-status.py
```

Expected: `Full replay matches cached session state`, zero `opened`/`bytes_read` in warm and unchanged scans, and per-phase durations. The verifier changes no live source, tracker record, service or installation. Measured diagnosis, baseline limitations and before/after evidence are in [the investigation plan](../plans/codex-time-resource-investigation.md).

## Merged storage compatibility

The merged checkout preserves v4 token evidence and v5 incremental storage. History, sessions and model-time read timing without quota/token journals. Projects and overview load token evidence for their cost reports. The picker retains its 60-second snapshot cadence. Legacy timing reads invalidate on ledger identity/stat changes; partitioned timing reads reread sessions so an isolated restore is visible even when layout revision stays unchanged. Status remains independent of either durable layout and refreshes its private message cache only on demand.
