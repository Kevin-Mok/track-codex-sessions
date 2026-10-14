"""Disposable status cache behavior, using only synthetic rollout files."""

import importlib
import importlib.util
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest


def line(kind: str, second: int = 0, **payload: object) -> bytes:
    return (json.dumps({
        "timestamp": f"2026-10-06T12:00:{second:02d}Z",
        "type": kind,
        "payload": payload,
    }, ensure_ascii=False) + "\n").encode()


def base(sid: str = "s1", cwd: str = "/a") -> bytes:
    return line("session_meta", id=sid, cwd=cwd) + line(
        "event_msg", 1, type="task_started", turn_id="t1"
    )


def rollout(home: Path, content: bytes, name: str = "one") -> Path:
    path = home / "sessions" / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def status(home: Path, runtime: Path) -> dict[str, object]:
    assert importlib.util.find_spec("codex_time.session_status") is not None, (
        "the persistent per-session status cache is not implemented"
    )
    result = importlib.import_module("codex_time.session_status").session_status(home, runtime)
    return cast(dict[str, object], result)


def sessions(result: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], result["sessions"])


def scan(result: dict[str, object]) -> dict[str, int]:
    return cast(dict[str, int], result["scan"])


def test_latest_text_and_lifecycle_ignore_tools_and_commentary(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    path = rollout(home, base() + line(
        "response_item", 2, type="message", role="user",
        content=[{"type": "input_text", "text": "last user\nfull text"}],
    ) + line(
        "response_item", 3, type="message", role="assistant", channel="commentary",
        content=[{"type": "output_text", "text": "still working"}],
    ) + line("response_item", 4, type="function_call_output", output="SECRET tool output"))
    result = status(home, runtime)
    assert result["fresh"] is True
    assert sessions(result) == [{
        "session_id": "s1", "cwd": "/a", "rollout_path": str(path), "tty": None,
        "status": "mid_turn", "last_user_message": "last user\nfull text",
        "last_assistant_message": "still working", "last_updated": "2026-10-06T12:00:04+00:00",
    }]
    assert "SECRET" not in json.dumps(result)
    assert scan(result) == {"files": 1, "opened": 1, "bytes_read": path.stat().st_size,
                            "cache_hits": 0, "rebuilt": 1}
    with path.open("ab") as out:
        out.write(line("event_msg", 5, type="agent_message", message="final answer"))
        out.write(line("event_msg", 6, type="task_complete", turn_id="t1"))
    state = sessions(status(home, runtime))[0]
    assert state["status"] == "idle"
    assert state["last_assistant_message"] == "final answer"


def test_hit_never_opens_rollouts_or_rewrites_cache(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    rollout(home, base())
    first = status(home, runtime)
    cache = Path(str(first["cache_path"]))
    original = cache.stat().st_mtime_ns
    real_open = Path.open

    def guarded_open(path: Path, *args: object, **kwargs: object) -> object:
        assert path.suffix != ".jsonl", "a cache hit opened a raw rollout"
        return real_open(path, *args, **kwargs)  # type: ignore[call-overload]

    with patch.object(Path, "open", guarded_open):
        second = status(home, runtime)
    assert sessions(second) == sessions(first)
    assert scan(second) == {"files": 1, "opened": 0, "bytes_read": 0,
                            "cache_hits": 1, "rebuilt": 0}
    assert cache.stat().st_mtime_ns == original


def test_append_reads_only_added_bytes_and_matches_forced_replay(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    path = rollout(home, base())
    status(home, runtime)
    appended = line("turn_context", 2, cwd="/b") + line(
        "event_msg", 3, type="user_message", message="next question"
    ) + line("event_msg", 4, type="task_complete", turn_id="t1")
    with path.open("ab") as out:
        out.write(appended)
    result = status(home, runtime)
    assert scan(result)["bytes_read"] == len(appended)
    assert scan(result)["rebuilt"] == 0
    assert sessions(result)[0]["cwd"] == "/b"
    assert sessions(result)[0]["last_user_message"] == "next question"
    assert sessions(result) == sessions(status(home, tmp_path / "replay"))


@pytest.mark.parametrize("change", ["truncate", "same_size_rewrite", "replace"])
def test_rewritten_and_replaced_files_rebuild(tmp_path: Path, change: str) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    old = base() + line("event_msg", 2, type="agent_message", message="old answer")
    path = rollout(home, old)
    status(home, runtime)
    before = path.stat()
    rewritten = base("s2", "/b")
    if change == "same_size_rewrite":
        rewritten += line("event_msg", 2, type="agent_message", message="new answer")
        assert len(rewritten) == len(old)
        path.write_bytes(rewritten)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000))
    elif change == "replace":
        replacement = path.with_suffix(".replacement")
        replacement.write_bytes(rewritten)
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(path)
    else:
        path.write_bytes(rewritten)
    result = status(home, runtime)
    assert sessions(result)[0]["session_id"] == "s2"
    assert sessions(result)[0]["last_assistant_message"] == (
        "new answer" if change == "same_size_rewrite" else None
    )
    assert scan(result)["bytes_read"] == len(rewritten)
    assert scan(result)["rebuilt"] == 1


def test_new_deleted_and_archived_rollouts_are_discovered_and_sorted(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    first = rollout(home, base(), "z")
    status(home, runtime)
    other = rollout(home, base("s2"), "a")
    result = status(home, runtime)
    assert [item["rollout_path"] for item in sessions(result)] == [str(other), str(first)]
    assert scan(result)["opened"] == 1
    first.unlink()
    archive = home / "archived_sessions"
    archive.mkdir()
    archived = other.rename(archive / other.name)
    result = status(home, runtime)
    assert [item["rollout_path"] for item in sessions(result)] == [str(archived)]
    cache = json.loads(Path(str(result["cache_path"])).read_text())
    assert list(cache["files"]) == [str(archived)]


@pytest.mark.parametrize("invalid", ["json", "version", "home", "offset", "state"])
def test_invalid_cache_rebuilds_safely(tmp_path: Path, invalid: str) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    path = rollout(home, base())
    first = status(home, runtime)
    cache_path = Path(str(first["cache_path"]))
    cache = json.loads(cache_path.read_text())
    if invalid == "version":
        cache["version"] = -1
    elif invalid == "home":
        cache["home"] = "/somewhere/else"
    elif invalid == "offset":
        cache["files"][str(path)]["offset"] = path.stat().st_size + 1
    elif invalid == "state":
        cache["files"][str(path)]["state"]["status"] = "unknown-state"
    cache_path.write_text("not JSON" if invalid == "json" else json.dumps(cache))
    result = status(home, runtime)
    assert result["fresh"] is True
    assert sessions(result) == sessions(first)
    assert scan(result)["rebuilt"] == 1
    assert scan(result)["bytes_read"] == path.stat().st_size


def test_partial_utf8_line_restarts_from_complete_offset(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    tail = line("event_msg", 2, type="agent_message", message="hello 🌍")
    cut = tail.index("🌍".encode()) + 2
    content = base()
    path = rollout(home, content + tail[:cut])
    first = status(home, runtime)
    assert sessions(first)[0]["last_assistant_message"] is None
    assert scan(status(home, runtime))["opened"] == 0
    with path.open("ab") as out:
        out.write(tail[cut:])
    result = status(home, runtime)
    assert sessions(result)[0]["last_assistant_message"] == "hello 🌍"
    assert scan(result)["bytes_read"] == len(tail)
    assert sessions(result) == sessions(status(home, tmp_path / "replay"))


def test_malformed_records_do_not_hide_valid_following_state(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    rollout(home, base() + b"invalid JSON\n[]\n" + line(
        "response_item", 2, type="message", role="developer",
        content=[{"type": "input_text", "text": "SECRET instructions"}],
    ) + line("event_msg", 3, type="task_complete", turn_id="t1"))
    result = status(home, runtime)
    assert result["fresh"] is True
    assert sessions(result)[0]["status"] == "idle"
    assert "SECRET" not in json.dumps(result)


def test_terminal_for_other_turn_cannot_end_current_turn(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    rollout(home, base() + line("event_msg", 2, type="task_started", turn_id="t2") + line(
        "event_msg", 3, type="task_complete", turn_id="t1"
    ))
    assert sessions(status(home, runtime))[0]["status"] == "mid_turn"


def test_private_permissions_and_atomic_concurrent_visibility(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    path = rollout(home, base())
    runtime.mkdir(mode=0o777)
    first = status(home, runtime)
    cache_path = Path(str(first["cache_path"]))
    assert runtime.stat().st_mode & 0o777 == 0o700
    assert cache_path.stat().st_mode & 0o777 == 0o600
    assert (runtime / "session-status.lock").stat().st_mode & 0o777 == 0o600
    with path.open("ab") as out:
        out.write(line("event_msg", 2, type="task_complete", turn_id="t1"))
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(status, home, runtime) for _ in range(4)]
        # Direct readers do not take the writer lock and must always see whole JSON.
        for _ in range(100):
            assert isinstance(json.loads(cache_path.read_text())["files"], dict)
        results = [future.result() for future in futures]
    assert all(sessions(result)[0]["status"] == "idle" for result in results)
    assert sum(scan(result)["opened"] for result in results) == 1


def test_exact_tty_evidence_from_rollout_fd_or_resume_id(tmp_path: Path) -> None:
    # A fixture proc tree makes evidence checks independent of the test runner's tty.
    module = importlib.import_module("codex_time.session_status")
    proc = tmp_path / "proc"
    path = rollout(tmp_path / "home", base())
    for pid, comm, args, links in [
        ("11", "codex", b"codex\0", {"0": "/dev/pts/5", "6": str(path)}),
        ("12", "codex", b"codex\0resume\0s2\0", {"0": "/dev/pts/6"}),
        ("13", "codex", b"codex\0", {"0": "/dev/null", "6": str(path)}),
        ("14", "python", b"python\0resume\0s3\0", {"0": "/dev/pts/7"}),
    ]:
        root = proc / pid
        (root / "fd").mkdir(parents=True)
        (root / "comm").write_text(comm + "\n")
        (root / "cmdline").write_bytes(args)
        for fd, destination in links.items():
            (root / "fd" / fd).symlink_to(destination)
    by_path, by_id = module._tty_evidence(proc)
    assert by_path == {str(path): {"/dev/pts/5"}}
    assert by_id == {"s2": {"/dev/pts/6"}}


def test_corrupt_empty_cache_is_repaired_even_without_rollouts(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    home.mkdir()
    runtime.mkdir()
    cache = runtime / "session-status.json"
    cache.write_text("bad JSON")
    result = status(home, runtime)
    assert result["fresh"] is True
    assert sessions(result) == []
    assert json.loads(cache.read_text())["version"] == 1


def test_append_during_read_is_bounded_and_explicitly_stale(tmp_path: Path) -> None:
    module = importlib.import_module("codex_time.session_status")
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    content = base()
    path = rollout(home, content)
    appended = line("event_msg", 2, type="task_complete", turn_id="t1")
    original_event = module._event
    changed = False

    def append_after_first_record(record: object, entry: object) -> None:
        nonlocal changed
        original_event(record, entry)
        if not changed:
            with path.open("ab") as out:
                out.write(appended)
            changed = True

    with patch.object(module, "_event", append_after_first_record):
        result = status(home, runtime)
    assert result["fresh"] is False
    assert scan(result)["bytes_read"] == len(content)
    assert sessions(result)[0]["status"] == "mid_turn"
    next_result = status(home, runtime)
    assert next_result["fresh"] is True
    assert scan(next_result)["bytes_read"] == len(appended)
    assert sessions(next_result)[0]["status"] == "idle"


def test_unavailable_changed_file_keeps_explicit_stale_state(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    path = rollout(home, base())
    before = status(home, runtime)
    with path.open("ab") as out:
        out.write(line("event_msg", 2, type="task_complete", turn_id="t1"))
    original_open = Path.open

    def unavailable(path_: Path, *args: object, **kwargs: object) -> object:
        if path_ == path:
            raise PermissionError("synthetic unreadable rollout")
        return original_open(path_, *args, **kwargs)  # type: ignore[call-overload]

    with patch.object(Path, "open", unavailable):
        result = status(home, runtime)
    assert result["fresh"] is False
    assert sessions(result) == sessions(before)
    assert sessions(status(home, runtime))[0]["status"] == "idle"


def test_long_scan_reports_ongoing_progress_without_message_contents(tmp_path: Path) -> None:
    module = importlib.import_module("codex_time.session_status")
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    rollout(home, base() + line("event_msg", 2, type="agent_message", message="SECRET"))
    messages: list[str] = []
    ticks = iter(range(100))
    with patch.object(module.time, "monotonic", lambda: next(ticks)):
        result = module.session_status(home, runtime, messages.append)
    assert result["fresh"] is True
    assert len(messages) >= 2
    assert all("elapsed" in message and "SECRET" not in message for message in messages)


def test_unreadable_rollout_directory_retains_prior_state_as_stale(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("directory permission behavior requires an unprivileged account")
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    path = rollout(home, base())
    first = status(home, runtime)
    path.parent.chmod(0)
    try:
        result = status(home, runtime)
    finally:
        path.parent.chmod(0o700)
    assert result["fresh"] is False
    assert sessions(result) == sessions(first)
    assert status(home, runtime)["fresh"] is True


def test_conflicting_tty_evidence_across_path_and_id_stays_unknown(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    path = rollout(home, base())
    with patch("codex_time.session_status._tty_evidence", return_value=(
        {str(path): {"/dev/pts/5"}}, {"s1": {"/dev/pts/6"}},
    )):
        assert sessions(status(home, runtime))[0]["tty"] is None


def test_progress_callback_contains_only_ascii(tmp_path: Path) -> None:
    home, runtime = tmp_path / "home", tmp_path / "runtime"
    rollout(home, base())
    module = importlib.import_module("codex_time.session_status")
    messages: list[str] = []
    with patch.object(module.time, "monotonic", side_effect=range(1000)):
        module.session_status(home, runtime, messages.append)
    assert messages and all(message.isascii() for message in messages)


def test_ambiguous_fd_evidence_cannot_be_overridden_by_resume_id(tmp_path: Path) -> None:
    module = importlib.import_module("codex_time.session_status")
    home, runtime, proc = tmp_path / "home", tmp_path / "runtime", tmp_path / "proc"
    path = rollout(home, base())
    for pid, tty, argv in [
        ("11", "/dev/pts/5", b"codex\0"),
        ("12", "/dev/pts/6", b"codex\0resume\0s1\0"),
    ]:
        root = proc / pid
        (root / "fd").mkdir(parents=True)
        (root / "comm").write_text("codex\n")
        (root / "cmdline").write_bytes(argv)
        (root / "fd/0").symlink_to(tty)
        (root / "fd/7").symlink_to(path)
    original = module._tty_evidence
    with patch.object(module, "_tty_evidence", lambda: original(proc)):
        assert sessions(status(home, runtime))[0]["tty"] is None
