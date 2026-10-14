"""Private, disposable session-state cache; raw rollouts are always read-only.

Unlike the content-free accounting ledger, this cache contains message text. Keep
it in private runtime storage and out of ledger/checkpoint/projection payloads.
"""

from __future__ import annotations

import fcntl
import json
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from codex_time.storage import atomic_json

CACHE_VERSION: Literal[1] = 1


class _State(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    session_id: str | None
    cwd: str | None
    rollout_path: str
    tty: str | None
    status: Literal["mid_turn", "idle"]
    last_user_message: str | None
    last_assistant_message: str | None
    last_updated: str | None


class _Entry(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    dev: int = Field(ge=0)
    ino: int = Field(ge=0)
    size: int = Field(ge=0)
    mtime_ns: int
    offset: int = Field(ge=0)
    current_turn: str | None
    state: _State

    @model_validator(mode="after")
    def valid_offset(self) -> _Entry:
        if self.offset > self.size:
            raise ValueError("offset exceeds recorded file size")
        if self.state.last_updated is not None:
            at = datetime.fromisoformat(self.state.last_updated)
            if at.tzinfo is None:
                raise ValueError("update timestamp must include timezone")
        return self


class _Cache(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    version: Literal[1]
    home: str
    files: dict[str, _Entry]


class _Progress:
    def __init__(self, callback: Callable[[str], None] | None) -> None:
        self.callback = callback
        self.started = self.last = time.monotonic()

    def pulse(self, activity: str) -> None:
        now = time.monotonic()
        if self.callback is not None and now - self.last >= 1:
            self.callback(f"{activity}; {now - self.started:.0f}s elapsed")
            self.last = now


def _load(path: Path, home: Path) -> tuple[_Cache, bool]:
    try:
        cache = _Cache.model_validate_json(path.read_bytes())
        if cache.home != str(home) or any(
            key != entry.state.rollout_path or not Path(key).is_absolute()
            for key, entry in cache.files.items()
        ):
            raise ValueError("cache source identity mismatch")
        return cache, True
    except (OSError, ValueError, ValidationError):
        return _Cache(version=CACHE_VERSION, home=str(home), files={}), False


def _stamp(stat: os.stat_result) -> tuple[int, int, int, int]:
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def _entry_stamp(entry: _Entry) -> tuple[int, int, int, int]:
    return entry.dev, entry.ino, entry.size, entry.mtime_ns


def _new_entry(path: Path, stat: os.stat_result) -> _Entry:
    return _Entry(
        dev=stat.st_dev, ino=stat.st_ino, size=stat.st_size, mtime_ns=stat.st_mtime_ns,
        offset=0, current_turn=None,
        state=_State(
            session_id=None, cwd=None, rollout_path=str(path), tty=None, status="idle",
            last_user_message=None, last_assistant_message=None, last_updated=None,
        ),
    )


def _text(content: object) -> str | None:
    if not isinstance(content, list):
        return None
    parts = [
        block["text"] for block in content
        if isinstance(block, dict) and block.get("type") in ("input_text", "output_text", "text")
        and isinstance(block.get("text"), str)
    ]
    return "\n".join(parts) if parts else None


def _event(record: object, entry: _Entry) -> None:
    if not isinstance(record, dict) or not isinstance(record.get("payload"), dict):
        return
    payload = record["payload"]
    state = entry.state
    at = record.get("timestamp")
    try:
        if isinstance(at, str):
            parsed = datetime.fromisoformat(at.replace("Z", "+00:00"))
            normalized = parsed.astimezone(UTC).isoformat() if parsed.tzinfo else None
        elif isinstance(at, (int, float)) and not isinstance(at, bool):
            normalized = datetime.fromtimestamp(at, UTC).isoformat()
        else:
            normalized = None
        if normalized is not None and (
            state.last_updated is None or normalized > state.last_updated
        ):
            state.last_updated = normalized
    except (ValueError, OverflowError, OSError):
        pass  # Bad timestamps never erase the last valid update.
    kind, event = record.get("type"), payload.get("type")
    if kind == "session_meta":
        if isinstance(payload.get("id"), str):
            state.session_id = payload["id"]
        if isinstance(payload.get("cwd"), str):
            state.cwd = payload["cwd"]
    elif kind == "turn_context" and isinstance(payload.get("cwd"), str):
        state.cwd = payload["cwd"]
    elif kind == "event_msg":
        tid = payload.get("turn_id")
        if event == "task_started":
            entry.current_turn = tid if isinstance(tid, str) else None
            state.status = "mid_turn"
        elif event in ("task_complete", "turn_aborted") and (
            not isinstance(tid, str) or entry.current_turn in (None, tid)
        ):
            entry.current_turn = None
            state.status = "idle"
            if isinstance(payload.get("last_agent_message"), str):
                state.last_assistant_message = payload["last_agent_message"]
        elif event in ("user_message", "agent_message") and isinstance(payload.get("message"), str):
            if event == "user_message":
                state.last_user_message = payload["message"]
            else:
                state.last_assistant_message = payload["message"]
    elif kind == "response_item" and event == "message":
        text = _text(payload.get("content"))
        if text is not None:
            if payload.get("role") == "user":
                state.last_user_message = text
            elif payload.get("role") == "assistant":
                state.last_assistant_message = text
        # Commentary and even a final-channel message are not lifecycle terminals.


def _replay(
    path: Path, old: _Entry | None, counts: dict[str, int], pulse: _Progress,
) -> tuple[_Entry, bool]:
    with path.open("rb") as source:
        counts["opened"] += 1
        initial = os.fstat(source.fileno())
        # Identity changes, shrink and same-size rewrites invalidate all old state.
        growing = (
            old is not None and (old.dev, old.ino) == (initial.st_dev, initial.st_ino)
            and initial.st_size > old.size
        )
        if growing and old is not None:
            entry = old.model_copy(deep=True)
        else:
            entry = _new_entry(path, initial)
            counts["rebuilt"] += 1
        source.seek(entry.offset)
        while remaining := initial.st_size - source.tell():
            raw = source.readline(remaining)
            if not raw:
                break
            counts["bytes_read"] += len(raw)
            pulse.pulse(f"Reading session state; {counts['opened']} files opened")
            if not raw.endswith(b"\n"):
                break  # Retry the entire partial line, including split UTF-8, after growth.
            entry.offset = source.tell()
            try:
                _event(json.loads(raw), entry)
            except (ValueError, TypeError, OverflowError):
                continue  # Invalid complete records cannot hide later lifecycle records.
        entry.dev, entry.ino, entry.size, entry.mtime_ns = _stamp(initial)
        # Bound the read to initial size. A concurrent append/replacement is retried next time.
        unchanged = _stamp(initial) == _stamp(os.fstat(source.fileno()))
        unchanged = unchanged and _stamp(initial) == _stamp(path.stat())
        return entry, unchanged


def _tty_evidence(proc: Path = Path("/proc")) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Join a tty only through an exact open rollout fd or explicit resume SID.

    A backend holding many rollouts but no tty gives no attribution evidence.
    Conflicting process evidence is deliberately unresolved.
    """
    paths: dict[str, set[str]] = {}
    ids: dict[str, set[str]] = {}
    try:
        processes = list(proc.iterdir())
    except OSError:
        return {}, {}
    for process in processes:
        if not process.name.isdecimal():
            continue
        try:
            if not (process / "comm").read_text().strip().startswith("codex"):
                continue
            fds = list((process / "fd").iterdir())
            links: list[str] = []
            for fd in fds:
                try:
                    links.append(os.readlink(fd))
                except OSError:
                    continue
            ttys = {
                destination for fd in ("0", "1", "2")
                if (destination := _fd_target(process / "fd" / fd)) is not None
                and (destination.startswith("/dev/pts/") or (
                    destination.startswith("/dev/tty") and destination[8:].isdigit()
                ))
            }
            if not ttys:
                continue
            for target in links:
                if target.endswith(".jsonl") and Path(target).is_absolute():
                    paths.setdefault(str(Path(target).resolve()), set()).update(ttys)
            argv = (process / "cmdline").read_bytes().decode(errors="replace").split("\0")
            if "resume" in argv:
                index = argv.index("resume") + 1
                if index < len(argv) and argv[index] and not argv[index].startswith("-"):
                    ids.setdefault(argv[index], set()).update(ttys)
        except OSError:
            continue  # Processes can exit or become inaccessible during discovery.
    return paths, ids


def _fd_target(path: Path) -> str | None:
    try:
        return os.readlink(path)
    except OSError:
        return None


def _discover(home: Path, pulse: _Progress) -> tuple[list[Path], bool]:
    paths: set[Path] = set()
    complete = True

    def unavailable(error: OSError) -> None:
        nonlocal complete
        complete = False

    for directory in ("sessions", "archived_sessions"):
        root = home / directory
        try:
            root.stat()
        except FileNotFoundError:
            continue
        except OSError:
            complete = False
            continue
        # pathlib.rglob suppresses PermissionError and would prune unreadable subtrees.
        for current, _, files in os.walk(root, onerror=unavailable):
            pulse.pulse("Discovering session rollouts")
            for name in files:
                if name.endswith(".jsonl"):
                    try:
                        paths.add((Path(current) / name).resolve())
                    except OSError:
                        complete = False
    return sorted(paths), complete


def session_status(
    home: Path, runtime: Path, progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Refresh changed rollouts, then return a compact JSON-ready snapshot.

    Every call stats discovered files; exact cache hits open no raw rollout.
    `fresh=False` means a source changed while reading or could not be checked.
    Previous valid state is retained on transient I/O failure and retried later.
    """
    home, runtime = home.expanduser().resolve(), runtime.expanduser().resolve()
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime.chmod(0o700)
    cache_path = runtime / "session-status.json"
    pulse = _Progress(progress)
    lock_fd = os.open(runtime / "session-status.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(lock_fd, "a") as lock:
        os.fchmod(lock.fileno(), 0o600)
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                pulse.pulse("Waiting for session state cache")
                time.sleep(0.05)
        cache, valid = _load(cache_path, home)
        counts = {"files": 0, "opened": 0, "bytes_read": 0, "cache_hits": 0, "rebuilt": 0}
        seen: set[str] = set()
        paths, fresh = _discover(home, pulse)
        dirty = not valid
        for path in paths:
            key = str(path)
            seen.add(key)
            counts["files"] += 1
            pulse.pulse(f"Checking session state; {counts['files']} files")
            old = cache.files.get(key)
            try:
                stat = path.stat()
                if old is not None and _entry_stamp(old) == _stamp(stat):
                    counts["cache_hits"] += 1
                    continue
                entry, unchanged = _replay(path, old, counts, pulse)
                cache.files[key] = entry
                fresh = fresh and unchanged
                dirty = True
            except OSError:
                fresh = False
        # Never prune on an incomplete directory traversal; retain explicit stale state.
        if fresh:
            for key in set(cache.files) - seen:
                del cache.files[key]
                dirty = True
        by_path, by_id = _tty_evidence()
        for key, entry in cache.files.items():
            evidence = by_path.get(key, set()) | by_id.get(entry.state.session_id or "", set())
            tty = next(iter(evidence)) if len(evidence) == 1 else None
            if tty != entry.state.tty:
                entry.state.tty, dirty = tty, True
        if dirty:
            atomic_json(
                cache_path, cache.model_dump(mode="json"), runtime / ".session-status-stage"
            )
        return {
            "sessions": [
                cache.files[key].state.model_dump(mode="json") for key in sorted(cache.files)
            ],
            "fresh": fresh, "cache_path": str(cache_path), "scan": counts,
            "version": CACHE_VERSION, "home": str(home),
            "checked_at": datetime.now(UTC).isoformat(),
        }
