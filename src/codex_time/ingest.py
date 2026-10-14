"""Incremental, content-free lifecycle ingestion from Codex rollout JSONL."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import cast

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
from codex_time.token_ingest import UsageState, observe


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
    offset: int = Field(default=0, ge=0)
    prefix: str = ""
    session_id: str = ""
    cwd: str = ""
    current_turn: str = ""
    contexts: dict[str, list[ModelContext]] = Field(default_factory=dict)
    pending: dict[str, PendingWait] = Field(default_factory=dict)
    usage: UsageState = Field(default_factory=UsageState)


class RolloutReader:
    """Offsets are inode based so archive moves retain pending call correlations.

    Checkpoints contain identifiers and timing only and belong in runtime storage.
    Losing checkpoints is safe: re-reading reconstructs the same durable ledger.
    """

    def __init__(
        self,
        home: Path,
        checkpoints: dict[str, object] | None = None,
        *,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        self.home = home
        self.progress = progress
        self._progress_at = 0.0
        self._scan_started = 0.0
        self._records = 0
        self._paths = 0
        self._usage_ids: set[str] = set()
        self._usage_ledger: Ledger | None = None
        self._usage_count = 0
        self._usage_sessions: dict[str, list[UsageObservation]] = {}
        self._files: dict[str, FileState] = {}
        self._invalid_checkpoint = False
        self._quota_keys: set[str] = set()
        self._quota_ledger: Ledger | None = None
        self._quota_count = 0
        if checkpoints:
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
        return {
            "version": 4,
            "files": {key: value.model_dump(mode="json") for key, value in self._files.items()},
        }

    def scan(self, ledger: Ledger) -> None:
        self._scan_started = monotonic()
        self._records = self._paths = 0
        if self._usage_ledger is not ledger or self._usage_count != len(ledger.usage_observations):
            self._usage_ids = {u.id for u in ledger.usage_observations}
            self._usage_sessions = {}
            for observation in ledger.usage_observations:
                self._usage_sessions.setdefault(observation.session_id, []).append(observation)
            self._usage_ledger = ledger
            self._usage_count = len(ledger.usage_observations)
        self._progress(force=True)
        if self._quota_ledger is not ledger or self._quota_count != len(ledger.quota_observations):
            self._quota_keys = {q.model_dump_json() for q in ledger.quota_observations}
            self._quota_ledger = ledger
            self._quota_count = len(ledger.quota_observations)
        if self._invalid_checkpoint:
            diagnostic(ledger, "invalid rollout checkpoint; rereading safely")
            self._invalid_checkpoint = False
        for directory in ("sessions", "archived_sessions"):
            root = self.home / directory
            for path in sorted(root.rglob("*.jsonl")):
                self._paths += 1
                self._progress()
                self._scan_file(path, ledger, archived=directory == "archived_sessions")
        self.reconcile_contexts(ledger)
        self._progress(force=True)

    def _progress(self, *, force: bool = False) -> None:
        now = monotonic()
        if self.progress is not None and (force or now - self._progress_at >= 2):
            self.progress(
                f"Reading rollout history: {self._paths:,} files, {self._records:,} records "
                f"({now - self._scan_started:.0f}s elapsed)"
            )
            self._progress_at = now

    def reconcile_contexts(self, ledger: Ledger) -> None:
        """Join queued rollout evidence to stable turns supplied by metadata later."""
        for state in self._files.values():
            session = ledger.sessions.get(state.session_id)
            if session is None:
                continue
            for tid in list(state.contexts):
                turn = session.turns.get(tid)
                if turn is not None:
                    for context in state.contexts.pop(tid):
                        add_context(turn, context, ledger)

    def _scan_file(self, path: Path, ledger: Ledger, *, archived: bool) -> None:
        try:
            stat = path.stat()
            key = f"{stat.st_dev}:{stat.st_ino}"
            state = self._files.setdefault(key, FileState())
            if stat.st_size < state.offset or (
                state.session_id and state.session_id not in ledger.sessions
            ):
                state = self._files[key] = FileState()
            with path.open("rb") as stream:
                prefix = hashlib.sha256(stream.read(256)).hexdigest()
                if state.prefix and prefix != state.prefix:
                    state = self._files[key] = FileState()
                state.prefix = prefix
                stream.seek(state.offset)
                while raw := stream.readline():
                    # A partial final line may be a perfectly valid JSON prefix.
                    if not raw.endswith(b"\n"):
                        break
                    state.offset = stream.tell()
                    self._records += 1
                    self._progress(force=self._records % 1000 == 0)
                    try:
                        record = json.loads(raw)
                        if not isinstance(record, dict):
                            raise ValueError("expected object")
                        self._event(cast(dict[str, object], record), state, ledger)
                    except (ValueError, TypeError, OverflowError):
                        state.usage.gap = True
                        diagnostic(ledger, "malformed rollout record skipped")
            session = ledger.sessions.get(state.session_id)
            if session:
                session.archived = archived
                if not session.turns and "no_lifecycle_events" not in session.quality:
                    session.quality.append("no_lifecycle_events")
        except OSError:
            diagnostic(ledger, "rollout unavailable; will retry")

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
                    previous = max(
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
                if observation is not None and observation.id not in self._usage_ids:
                    if any(
                        prior.at > observation.at
                        for prior in self._usage_sessions.get(state.session_id, [])
                    ):
                        # A later durable tranche may already contain this restored
                        # prefix. Keep its evidence but do not charge it again. The
                        # immutable journal cannot safely redistribute old deltas.
                        observation.delta = None
                        observation.request_input_tokens = None
                        observation.diagnostics.append("earlier_history_overlap")
                    ledger.usage_observations.append(observation)
                    self._usage_ids.add(observation.id)
                    self._usage_sessions.setdefault(observation.session_id, []).append(observation)
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
            key = observation.model_dump_json()
            if key not in self._quota_keys:
                self._quota_keys.add(key)
                ledger.quota_observations.append(observation)
                self._quota_count += 1


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
