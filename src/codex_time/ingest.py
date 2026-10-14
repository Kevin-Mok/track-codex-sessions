"""Incremental, content-free lifecycle ingestion from Codex rollout JSONL."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import BinaryIO, Protocol, cast

from pydantic import Field, ValidationError

from codex_time.models import (
    Ledger,
    Model,
    ModelContext,
    QuotaObservation,
    Session,
    Span,
    Turn,
    UsageObservation,
)
from codex_time.record_stream import CHUNK_BYTES, IncompleteRecord, read_large_record
from codex_time.token_ingest import UsageState, observe

_SPACE = re.compile(rb"[ \t\r\n]*")
# JSON string chunks are disjoint. Possessive repeats avoid retaining one
# backtracking frame per escape or repartitioning a malformed long chunk.
_STRING = re.compile(rb'"(?:[^"\\\x00-\x1f]++|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*+"')
_NUMBER = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_TOKEN_KEYS = dict.fromkeys((
    "input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens",
    "reasoning_output_tokens", "total_tokens",
))
_BUCKET_KEYS = dict.fromkeys(("window_minutes", "resets_at", "used_percent"))
_PAYLOAD_KEYS: dict[str, object] = dict.fromkeys((
    "id", "cwd", "source", "parent_thread_id", "forked_from_id", "type", "turn_id",
    "model", "effort", "name", "call_id",
))
_PAYLOAD_KEYS.update({
    "info": {"total_token_usage": _TOKEN_KEYS, "last_token_usage": _TOKEN_KEYS},
    "rate_limits": {"limit_id": None, "plan_type": None,
                    "primary": _BUCKET_KEYS, "secondary": _BUCKET_KEYS},
})


class _RecordSelector:
    """Validate JSON structure while materializing only whitelisted fields.

    Strings in messages, tool arguments and tool output are traversed as JSON
    tokens and never decoded into Python values. This uses structural parsing,
    so keywords inside those strings cannot be mistaken for lifecycle evidence.
    """

    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.pos = 0

    def space(self) -> None:
        match = _SPACE.match(self.raw, self.pos)
        assert match is not None
        self.pos = match.end()

    def string(self) -> tuple[int, int]:
        start = self.pos
        match = _STRING.match(self.raw, start)
        if match is None:
            raise ValueError("invalid JSON string")
        self.pos = match.end()
        return start, self.pos

    def value(self, selector: dict[str, object] | None = None) -> object:
        self.space()
        if self.pos >= len(self.raw):
            raise ValueError("missing JSON value")
        token = self.raw[self.pos]
        if token == ord("{"):
            result: dict[str, object] = {}
            self.pos += 1
            self.space()
            if self.raw[self.pos:self.pos + 1] == b"}":
                self.pos += 1
                return result
            while True:
                self.space()
                start, end = self.string()
                key = cast(str, json.loads(self.raw[start:end])) if selector is not None else ""
                self.space()
                if self.raw[self.pos:self.pos + 1] != b":":
                    raise ValueError("missing JSON colon")
                self.pos += 1
                self.space()
                start = self.pos
                child = selector.get(key) if selector is not None else None
                selected = selector is not None and key in selector
                nested = child if isinstance(child, dict) else None
                value = self.value(cast(dict[str, object], nested))
                if selected:
                    result[key] = (
                        value if nested is not None else json.loads(self.raw[start:self.pos])
                    )
                self.space()
                char = self.raw[self.pos:self.pos + 1]
                self.pos += 1
                if char == b"}":
                    return result
                if char != b",":
                    raise ValueError("invalid JSON object delimiter")
        if token == ord("["):
            self.pos += 1
            self.space()
            if self.raw[self.pos:self.pos + 1] == b"]":
                self.pos += 1
                return []
            while True:
                self.value()
                self.space()
                char = self.raw[self.pos:self.pos + 1]
                self.pos += 1
                if char == b"]":
                    return []
                if char != b",":
                    raise ValueError("invalid JSON array delimiter")
        if token == ord('"'):
            self.string()
            return ""
        for literal in (b"true", b"false", b"null", b"NaN", b"Infinity", b"-Infinity"):
            if self.raw.startswith(literal, self.pos):
                self.pos += len(literal)
                return None if literal == b"null" else False
        match = _NUMBER.match(self.raw, self.pos)
        if match is None:
            raise ValueError("invalid JSON value")
        self.pos = match.end()
        return 0


def content_free_record(raw: bytes) -> dict[str, object]:
    if not raw.isascii():
        # Validate source encoding, including ignored strings, as json.loads
        # previously did. No decoded conversation values are retained.
        raw.decode("utf-8")
    parser = _RecordSelector(raw)
    parser.space()
    if raw[parser.pos:parser.pos + 1] != b"{":
        raise ValueError("expected JSON object")
    result = parser.value({"timestamp": None, "type": None, "payload": _PAYLOAD_KEYS})
    parser.space()
    if parser.pos != len(raw):
        raise ValueError("trailing JSON input")
    return cast(dict[str, object], result)


def diagnostic(ledger: Ledger, message: str) -> None:
    """Keep bounded diagnostics; never include raw input or exception text."""
    if message not in ledger.diagnostics:
        ledger.diagnostics.append(message)
        del ledger.diagnostics[:-200]


def timestamp(value: object) -> datetime:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, UTC)
    if isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is not None:
            return result.astimezone(UTC)
    raise ValueError("unsupported timestamp")


def ancestry(payload: dict[str, object]) -> tuple[str | None, bool]:
    """A fork is a root session; only actual subagent ancestry excludes totals."""
    parent = payload.get("parent_thread_id")
    source = payload.get("source")
    if isinstance(source, str):
        try:
            source = json.loads(source)
        except (ValueError, TypeError):
            return str(parent) if parent else None, bool(parent) or "subagent" in source.lower()
    child = bool(parent)
    if isinstance(source, dict) and "subagent" in source:
        child = True
        sub = source["subagent"]
        if isinstance(sub, dict):
            spawn = sub.get("thread_spawn")
            if isinstance(spawn, dict):
                parent = spawn.get("parent_thread_id", parent)
    return str(parent) if parent else None, child


class PendingWait(Model):
    turn_id: str
    start: str


class FileState(Model):
    path: str = ""
    offset: int = Field(default=0, ge=0)
    prefix: str = ""
    prefix_size: int = Field(default=0, ge=0, le=256)
    tail_digest: str = ""
    session_id: str = ""
    cwd: str = ""
    current_turn: str = ""
    contexts: dict[str, list[ModelContext]] = Field(default_factory=dict)
    pending: dict[str, PendingWait] = Field(default_factory=dict)
    usage: UsageState = Field(default_factory=UsageState)
    size: int = -1
    mtime_ns: int = -1
    ctime_ns: int = -1
    archived: bool = False


class IngestBackend(Protocol):
    """Exact historical indexes and rollout checkpoints, without history in RAM."""

    def has_usage(self, identity: str) -> bool: ...
    def previous_usage(self, sid: str, at: datetime) -> UsageObservation | None: ...
    def has_later_usage(self, sid: str, at: datetime) -> bool: ...
    def append_usage(self, observation: UsageObservation) -> None: ...
    def append_quota(self, observation: QuotaObservation) -> None: ...
    def checkpoint_get(self, inode: str) -> FileState | None: ...
    def checkpoint_put(self, inode: str, state: FileState) -> None: ...
    def checkpoint_keys(self) -> Iterator[str]: ...
    def checkpoint_pending_keys(self) -> Iterator[str]: ...


class RolloutReader:
    """Offsets are inode based so archive moves retain pending call correlations.

    Checkpoints contain identifiers and timing only and belong in runtime storage.
    Losing checkpoints is safe: re-reading reconstructs the same durable ledger.

    Same-size rewrites, shrinkage and changes at the consumed boundary trigger
    idempotent rereads. Normal append checks at most 256 bytes at each boundary.
    An arbitrary same-inode middle overwrite followed by growth that preserves
    both boundaries cannot be distinguished immediately from a pure append
    without rereading the old prefix. Explicit history import rereads all input;
    the frequent daemon path does not claim to detect this adversarial case.
    """

    def __init__(
        self,
        home: Path,
        checkpoints: dict[str, object] | None = None,
        *,
        progress: Callable[[str], None] | None = None,
        backend: IngestBackend | None = None,
    ) -> None:
        self.home = home
        self.progress = progress
        self.backend = backend
        self._progress_at = 0.0
        self._scan_started = 0.0
        self._records = 0
        self._paths = 0
        self._bytes = 0
        self._max_records: int | None = None
        self._max_bytes: int | None = None
        self._changed_keys: set[str] = set()
        self._usage_ids: set[str] = set()
        self._usage_ledger: Ledger | None = None
        self._usage_count = 0
        self._usage_sessions: dict[str, list[UsageObservation]] = {}
        self._files: dict[str, FileState] = {}
        self._invalid_checkpoint = False
        self._quota_keys: set[str] = set()
        self._quota_ledger: Ledger | None = None
        self._quota_count = 0
        if checkpoints and backend is None:
            files = checkpoints.get("files", {})
            if checkpoints.get("version") == 4 and isinstance(files, dict):
                for key, value in files.items():
                    try:
                        self._files[str(key)] = FileState.model_validate(value)
                    except ValidationError:
                        self._invalid_checkpoint = True
            else:
                self._invalid_checkpoint = True

    @property
    def checkpoints(self) -> dict[str, object]:
        if self.backend is not None:
            # Disk checkpoints are committed after their corresponding evidence;
            # never duplicate all checkpoint state into the runtime heartbeat.
            return {"version": 4, "disk_backed": True}
        return {
            "version": 4,
            "files": {key: value.model_dump(mode="json") for key, value in self._files.items()},
        }

    def scan(self, ledger: Ledger, *, verify: bool = False) -> list[Path]:
        """Reconcile source names, using stat-only skips unless explicitly verified."""
        return self.scan_paths(
            ledger, self.source_paths(),
            max_records=2000 if self.backend is not None else None,
            max_bytes=8 * 1024 * 1024 if self.backend is not None else None,
            verify=verify,
        )

    def source_paths(self) -> Iterator[Path]:
        """Lazy fallback discovery; callers may consume bounded name batches."""
        return (
            path
            for directory in ("sessions", "archived_sessions")
            for path in (self.home / directory).rglob("*.jsonl")
        )

    def scan_paths(
        self,
        ledger: Ledger,
        paths: Iterable[Path],
        *,
        max_records: int | None = 2000,
        max_bytes: int | None = 8 * 1024 * 1024,
        verify: bool = True,
    ) -> list[Path]:
        """Read a coalesced batch; return paths whose complete records remain.

        Limits apply between complete records so partial JSONL never advances an
        offset. Checkpoints are staged through the backend, which must commit
        them only after the matching durable evidence and session snapshots.

        Verified event, active and bounded fallback pages check at most 512
        boundary bytes even when inode timestamps collide. Unchanged records
        are never decoded. ``verify=False`` provides an explicit stat-only skip
        for callers whose source-change detection is already authoritative.
        """
        self._scan_started = monotonic()
        self._records = self._paths = 0
        self._bytes = 0
        self._max_records, self._max_bytes = max_records, max_bytes
        self._changed_keys.clear()
        if self.backend is None and (
            self._usage_ledger is not ledger or self._usage_count != len(ledger.usage_observations)
        ):
            self._usage_ids = {u.id for u in ledger.usage_observations}
            self._usage_sessions = {}
            for observation in ledger.usage_observations:
                self._usage_sessions.setdefault(observation.session_id, []).append(observation)
            self._usage_ledger = ledger
            self._usage_count = len(ledger.usage_observations)
        self._progress(force=True)
        if self.backend is None and (
            self._quota_ledger is not ledger or self._quota_count != len(ledger.quota_observations)
        ):
            self._quota_keys = {q.model_dump_json() for q in ledger.quota_observations}
            self._quota_ledger = ledger
            self._quota_count = len(ledger.quota_observations)
        if self._invalid_checkpoint:
            diagnostic(ledger, "invalid rollout checkpoint; rereading safely")
            self._invalid_checkpoint = False
        unfinished = []
        for path in paths:
            self._paths += 1
            self._progress()
            if self._scan_file(
                path, ledger, archived=path.is_relative_to(self.home / "archived_sessions"),
                verify=verify,
            ):
                unfinished.append(path)
        self.reconcile_contexts(
            ledger, keys=self._changed_keys if self.backend is not None else None
        )
        self._progress(force=True)
        return unfinished

    def _limited(self) -> bool:
        return (
            self._max_records is not None and self._records >= self._max_records
        ) or (self._max_bytes is not None and self._bytes >= self._max_bytes)

    def _progress(self, *, force: bool = False) -> None:
        now = monotonic()
        if self.progress is not None and (force or now - self._progress_at >= 2):
            self.progress(
                f"Reading rollout history: {self._paths:,} files, {self._records:,} records "
                f"({now - self._scan_started:.0f}s elapsed)"
            )
            self._progress_at = now

    def reconcile_contexts(self, ledger: Ledger, *, keys: Iterable[str] | None = None) -> None:
        """Join queued rollout evidence to stable turns supplied by metadata later."""
        states = (
            ((key, self.backend.checkpoint_get(key))
             for key in (keys if keys is not None else self.backend.checkpoint_pending_keys()))
            if self.backend is not None else self._files.items()
        )
        for key, state in states:
            if state is None:
                continue
            session = ledger.sessions.get(state.session_id)
            if session is None:
                continue
            changed = False
            for tid in list(state.contexts):
                turn = session.turns.get(tid)
                if turn is not None:
                    for context in state.contexts.pop(tid):
                        add_context(turn, context, ledger)
                    changed = True
            if changed and self.backend is not None:
                self.backend.checkpoint_put(key, state)

    def _scan_file(self, path: Path, ledger: Ledger, *, archived: bool, verify: bool) -> bool:
        try:
            stat = path.stat()
            key = f"{stat.st_dev}:{stat.st_ino}"
            state = (
                self.backend.checkpoint_get(key) or FileState()
                if self.backend is not None else self._files.setdefault(key, FileState())
            )
            unchanged = (state.size, state.mtime_ns, state.ctime_ns) == (
                stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns
            )
            if unchanged and verify:
                if self._limited():
                    return True
                # Unbuffered verification avoids a buffered reader's implicit
                # 4 KiB prefetch: unchanged input costs at most 512 logical bytes.
                with path.open("rb", buffering=0) as stream:
                    prefix = hashlib.sha256(stream.read(state.prefix_size)).hexdigest()
                    unchanged = (
                        bool(state.tail_digest)
                        and (state.prefix_size > 0 or state.offset == 0)
                        and prefix == state.prefix
                        and boundary_digest(stream, state.offset) == state.tail_digest
                    )
            if unchanged and (not state.session_id or state.session_id in ledger.sessions):
                moved = state.path != str(path)
                state.path = str(path)
                if state.archived != archived or moved:
                    if state.session_id:
                        ledger.sessions[state.session_id].archived = archived
                    state.archived = archived
                    if self.backend is not None:
                        self.backend.checkpoint_put(key, state)
                return False
            if self._limited():
                return True
            reset = stat.st_size < state.offset or (
                state.size >= 0 and stat.st_size <= state.size
            ) or (
                state.session_id and state.session_id not in ledger.sessions
            ) or (state.offset > 0 and (not state.tail_digest or not state.prefix_size))
            unfinished = False
            with path.open("rb") as stream:
                if not reset and state.prefix:
                    prefix = hashlib.sha256(stream.read(state.prefix_size)).hexdigest()
                    reset = prefix != state.prefix
                if not reset and state.offset:
                    reset = boundary_digest(stream, state.offset) != state.tail_digest
                if reset:
                    if state.offset or state.session_id:
                        diagnostic(ledger, "rollout identity changed; rereading safely")
                    state = FileState()
                if not state.prefix:
                    stream.seek(0)
                    raw_prefix = stream.read(256)
                    state.prefix = hashlib.sha256(raw_prefix).hexdigest()
                    state.prefix_size = len(raw_prefix)
                stream.seek(state.offset)
                while not self._limited():
                    record_start = stream.tell()
                    raw = stream.readline(CHUNK_BYTES)
                    if not raw:
                        break
                    record = None
                    try:
                        record = (
                            content_free_record(raw)
                            if raw.endswith(b"\n")
                            else read_large_record(
                                stream, raw,
                                {"timestamp": None, "type": None, "payload": _PAYLOAD_KEYS},
                                progress=self._progress,
                            )
                        )
                    except IncompleteRecord:
                        # No evidence/offset is committed before a full newline.
                        break
                    except (ValueError, TypeError, OverflowError, RecursionError):
                        pass
                    state.offset = stream.tell()
                    self._records += 1
                    self._bytes += state.offset - record_start
                    self._progress(force=self._records % 1000 == 0)
                    try:
                        if record is None:
                            raise ValueError("malformed or oversized selected metadata")
                        self._event(record, state, ledger)
                    except (ValueError, TypeError, OverflowError, RecursionError):
                        state.usage.gap = True
                        diagnostic(ledger, "malformed rollout record skipped")
                unfinished = self._limited() and state.offset < stat.st_size
                state.tail_digest = boundary_digest(stream, state.offset)
            session = ledger.sessions.get(state.session_id)
            if session:
                session.archived = archived
                if not session.turns and "no_lifecycle_events" not in session.quality:
                    session.quality.append("no_lifecycle_events")
            if not unfinished:
                state.size, state.mtime_ns, state.ctime_ns = (
                    stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns
                )
            state.archived = archived
            state.path = str(path)
            if self.backend is not None:
                self.backend.checkpoint_put(key, state)
                self._changed_keys.add(key)
            else:
                self._files[key] = state
            return unfinished
        except OSError:
            diagnostic(ledger, "rollout unavailable; will retry")
            return False

    def _event(self, record: dict[str, object], state: FileState, ledger: Ledger) -> None:
        kind = record.get("type")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            if kind in ("session_meta", "event_msg", "turn_context", "response_item"):
                state.usage.gap = True
                diagnostic(ledger, "unsupported rollout payload schema; record skipped")
            return
        at = timestamp(record.get("timestamp"))
        if kind == "session_meta":
            sid, cwd = payload.get("id"), payload.get("cwd")
            if not isinstance(sid, str) or not isinstance(cwd, str):
                raise ValueError("unsupported session metadata")
            state.session_id, state.cwd = sid, cwd
            state.usage.created = at
            state.usage.forked = bool(payload.get("forked_from_id"))
            state.usage.directories_seen = [cwd]
            parent, child = ancestry(payload)
            state.usage.child = child
            meta_session = ledger.sessions.setdefault(
                sid,
                Session(id=sid, cwd=cwd, created=at, updated=at, parent_id=parent, is_child=child),
            )
            meta_session.is_child = meta_session.is_child or child
            if parent:
                meta_session.parent_id = parent
            return
        if kind == "event_msg" and payload.get("type") == "token_count":
            self._quota(payload.get("rate_limits"), at, ledger)
            if state.session_id:
                if state.usage.cumulative is None:
                    # A shortened/replaced rollout can begin after already durable
                    # evidence. Seed only from earlier observations of this session;
                    # never treat its later cumulative total as wholly new work.
                    previous = self.backend.previous_usage(state.session_id, at) if (
                        self.backend is not None
                    ) else max(
                        (
                            u
                            for u in self._usage_sessions.get(state.session_id, [])
                            if u.at < at and u.cumulative is not None
                        ),
                        key=lambda u: u.at,
                        default=None,
                    )
                    if previous is not None:
                        state.usage.cumulative = previous.cumulative
                        state.usage.model_changed |= previous.model_id != state.usage.model_id
                        state.usage.cwd_changed |= previous.cwd != state.cwd
                observation = observe(
                    payload.get("info"),
                    session_id=state.session_id,
                    cwd=state.cwd,
                    at=at,
                    state=state.usage,
                )
                known = observation is not None and (
                    self.backend.has_usage(observation.id) if self.backend is not None
                    else observation.id in self._usage_ids
                )
                if observation is not None and not known:
                    later = self.backend.has_later_usage(state.session_id, observation.at) if (
                        self.backend is not None
                    ) else any(
                        prior.at > observation.at
                        for prior in self._usage_sessions.get(state.session_id, [])
                    )
                    if later:
                        # A later durable tranche may already contain this restored
                        # prefix. Keep its evidence but do not charge it again. The
                        # immutable journal cannot safely redistribute old deltas.
                        observation.delta = None
                        observation.request_input_tokens = None
                        observation.diagnostics.append("earlier_history_overlap")
                    if self.backend is not None:
                        self.backend.append_usage(observation)
                    else:
                        ledger.usage_observations.append(observation)
                        self._usage_ids.add(observation.id)
                        self._usage_sessions.setdefault(observation.session_id, []).append(
                            observation
                        )
                        self._usage_count += 1
            else:
                diagnostic(ledger, "token usage without session metadata; attribution unavailable")
            return
        session = ledger.sessions.get(state.session_id)
        if session is None:
            diagnostic(ledger, "rollout event without session metadata skipped")
            return
        session.updated = max(session.updated, at)
        event = payload.get("type")
        tid = payload.get("turn_id")
        if kind == "turn_context":
            cwd = payload.get("cwd")
            if isinstance(cwd, str):
                state.usage.cwd_known = True
                if any(old != cwd for old in state.usage.directories_seen):
                    state.usage.cwd_changed = True
                if cwd not in state.usage.directories_seen:
                    state.usage.directories_seen.append(cwd)
                state.cwd = cwd
                session.cwd = cwd
                turn = session.turns.get(tid if isinstance(tid, str) else state.current_turn)
                if turn is not None:
                    turn.cwd = cwd
                    if "metadata_cwd_estimate" in turn.quality:
                        turn.quality.remove("metadata_cwd_estimate")
            context = ModelContext(
                at=at,
                model_id=payload.get("model")
                if isinstance(payload.get("model"), str) and payload.get("model")
                else None,
                reasoning_level=payload.get("effort")
                if isinstance(payload.get("effort"), str) and payload.get("effort")
                else None,
            )
            if any(old != context.model_id for old in state.usage.models_seen):
                state.usage.model_changed = True
            if context.model_id not in state.usage.models_seen:
                state.usage.models_seen.append(context.model_id)
            state.usage.model_id = context.model_id
            state.usage.context_at = at
            context_id = tid if isinstance(tid, str) else state.current_turn
            state.usage.turn_id = context_id or None
            if not context_id:
                diagnostic(ledger, "model context without stable turn ID skipped")
            elif context_id in session.turns:
                add_context(session.turns[context_id], context, ledger)
            else:
                pending_contexts = state.contexts.setdefault(context_id, [])
                if context not in pending_contexts:
                    pending_contexts.append(context)
            return
        if kind == "event_msg" and event == "task_started":
            if not isinstance(tid, str):
                diagnostic(ledger, "task start without stable turn ID skipped")
                return
            state.current_turn = tid
            state.usage.turn_id = tid
            if "no_lifecycle_events" in session.quality:
                session.quality.remove("no_lifecycle_events")
            turn = session.turns.setdefault(tid, Turn(id=tid, cwd=state.cwd, start=at))
            if "rollout" not in turn.provenance:
                turn.provenance.append("rollout")
            if "metadata_start_estimate" in turn.quality:
                # SQLite projects whole-second timestamps. A subsecond task may
                # have a rounded end before its precise start; discard that
                # provisional end atomically until the terminal record arrives.
                values = turn.model_dump()
                values["start"] = at
                if turn.end is not None and turn.end < at:
                    if "metadata_reconciled" not in turn.quality:
                        diagnostic(ledger, "precise task start conflicts with terminal; skipped")
                        return
                    values["end"] = None
                values["quality"] = [
                    flag for flag in turn.quality if flag != "metadata_start_estimate"
                ]
                session.turns[tid] = Turn.model_validate(values)
            for context in state.contexts.pop(tid, []):
                add_context(session.turns[tid], context, ledger)
        elif kind == "event_msg" and event in ("task_complete", "turn_aborted"):
            turn = session.turns.get(tid if isinstance(tid, str) else state.current_turn)
            if turn is None:
                diagnostic(ledger, "terminal event without matching task start skipped")
            elif at >= turn.start:
                if "rollout" not in turn.provenance:
                    turn.provenance.append("rollout")
                if turn.end is None or "metadata_reconciled" in turn.quality:
                    turn.end = at
                    turn.outcome = str(event)
                    turn.quality = [
                        flag
                        for flag in turn.quality
                        if flag not in ("metadata_reconciled", "metadata_end_estimate")
                    ]
                if turn.id == state.current_turn:
                    state.current_turn = ""
            else:
                diagnostic(ledger, "terminal timestamp precedes task start; skipped")
        elif kind == "response_item" and event == "function_call":
            # Async questions permit continued work and are deliberately excluded.
            if payload.get("name") not in ("functions.request_user_input", "request_user_input"):
                return
            call_id = payload.get("call_id")
            if isinstance(call_id, str) and state.current_turn:
                state.pending[call_id] = PendingWait(
                    turn_id=state.current_turn, start=at.isoformat()
                )
        elif (kind == "response_item" and event == "function_call_output") or (
            kind == "event_msg" and event == "verified_answer"
        ):
            call_id = payload.get("call_id")
            pending = state.pending.pop(call_id, None) if isinstance(call_id, str) else None
            if pending:
                turn = session.turns.get(pending.turn_id)
                start = timestamp(pending.start)
                if turn is not None and at >= start:
                    span = Span(start=start, end=at)
                    if span not in turn.waits:
                        turn.waits.append(span)

    def _quota(self, raw: object, at: datetime, ledger: Ledger) -> None:
        """Whitelist allowance metadata; shared readings are not session costs."""
        if raw is None:
            return
        if not isinstance(raw, dict):
            diagnostic(ledger, "unsupported quota metadata skipped")
            return
        for bucket in ("primary", "secondary"):
            value = raw.get(bucket)
            if value is None:
                continue
            if not isinstance(value, dict):
                diagnostic(ledger, "invalid quota observation skipped")
                continue
            try:
                observation = QuotaObservation.model_validate(
                    {
                        "at": at,
                        "limit_id": raw.get("limit_id"),
                        "plan_type": raw.get("plan_type"),
                        "bucket": bucket,
                        "window_minutes": value.get("window_minutes"),
                        "resets_at": value.get("resets_at"),
                        "used_percent": value.get("used_percent"),
                    }
                )
            except ValidationError:
                diagnostic(ledger, "invalid quota observation skipped")
                continue
            if self.backend is not None:
                self.backend.append_quota(observation)
                continue
            key = observation.model_dump_json()
            if key not in self._quota_keys:
                self._quota_keys.add(key)
                ledger.quota_observations.append(observation)
                self._quota_count += 1


def boundary_digest(stream: BinaryIO, offset: int) -> str:
    """Hash at most 256 consumed bytes; no source body enters checkpoint data."""
    size = min(offset, 256)
    stream.seek(offset - size)
    return hashlib.sha256(stream.read(size)).hexdigest()


def add_context(turn: Turn, context: ModelContext, ledger: Ledger) -> None:
    """Retain distinct timestamped evidence; reimport never duplicates it."""
    if context in turn.model_contexts:
        return
    if any(
        c.at == context.at
        and (c.model_id, c.reasoning_level) != (context.model_id, context.reasoning_level)
        for c in turn.model_contexts
    ):
        if "model_context_conflict" not in turn.quality:
            turn.quality.append("model_context_conflict")
        diagnostic(ledger, "conflicting model context; attribution unknown")
    turn.model_contexts.append(context)
    turn.model_contexts.sort(key=lambda c: (c.at, c.model_id or "", c.reasoning_level or ""))
