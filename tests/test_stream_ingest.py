"""Public ingestion preserves timing after huge ignored fields with bounded RAM."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src"


def event(kind: str, at: str, **payload: object) -> bytes:
    return (json.dumps({"timestamp": at, "type": kind, "payload": payload}) + "\n").encode()


@pytest.fixture(scope="module")
def giant_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    home = tmp_path_factory.mktemp("stream-giant-source")
    path = home / "sessions" / "synthetic.jsonl"
    path.parent.mkdir()
    with path.open("wb") as output:
        output.write(
            event(
                "session_meta", "2026-10-14T12:00:00Z", id="synthetic", cwd="/fixture", source="cli"
            )
        )
        output.write(
            b'{"timestamp":"2026-10-14T12:00:00.125Z","type":"event_msg","payload":{"ignored":"'
        )
        chunk = b"x" * (1024 * 1024)
        for _ in range(384):
            output.write(chunk)
        # The actual lifecycle fields follow the giant ignored string in the
        # same record. Skipping the whole record would lose this turn.
        output.write(b'","type":"task_started","turn_id":"turn"}}\n')
        output.write(
            event("event_msg", "2026-10-14T12:00:02.375Z", type="task_complete", turn_id="turn")
        )
    return home


@pytest.mark.parametrize("api", ["scan", "scan_paths"])
def test_giant_ignored_body_keeps_later_lifecycle_under_memory_limit(
    giant_source: Path, tmp_path: Path, api: str
) -> None:
    code = """
import json,resource,sys
from pathlib import Path
from codex_time.ingest import RolloutReader
from codex_time.models import Ledger
from codex_time.storage import Store
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
home,output,api=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
ledger=Ledger();reader=RolloutReader(home)
try:
    if api=='scan':reader.scan(ledger)
    else:
        pending=[home/'sessions/synthetic.jsonl'];rounds=0
        while pending:
            pending=reader.scan_paths(ledger,pending,max_records=2,max_bytes=8*1024*1024)
            rounds+=1
            assert rounds<8
    turn=ledger.sessions['synthetic'].turns['turn']
    store=Store(output/'data',output/'state')
    with store.writer():store.save(ledger)
    payload=ledger.model_dump_json()
    assert 'x'*256 not in payload
    sizes=[p.stat().st_size for p in store.root.rglob('*') if p.is_file()]
    rows=Path('/proc/self/status').read_text().splitlines()
    peak=next(int(row.split()[1])/1024 for row in rows if row.startswith('VmHWM:'))
    print(json.dumps({'start':turn.start.isoformat(),'end':turn.end.isoformat(),
        'turns':len(ledger.sessions['synthetic'].turns),'proc_peak_rss_mib':peak,
        'largest_persisted_file_bytes':max(sizes),'ledger_bytes':len(payload)}))
except MemoryError:
    print(json.dumps({'error':'MemoryError on giant ignored record'}))
    raise SystemExit(42)
"""
    environment = dict(os.environ, PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(giant_source), str(tmp_path), api],
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["start"] == "2026-10-14T12:00:00.125000+00:00"
    assert report["end"] == "2026-10-14T12:00:02.375000+00:00"
    assert report["turns"] == 1
    assert report["proc_peak_rss_mib"] <= 128
    assert report["largest_persisted_file_bytes"] < 16384
    assert report["ledger_bytes"] < 16384


def test_partial_large_record_replays_after_newline_and_reader_restart(tmp_path: Path) -> None:
    from codex_time.ingest import RolloutReader
    from codex_time.models import Ledger

    path = tmp_path / "sessions" / "partial.jsonl"
    path.parent.mkdir()
    meta = event(
        "session_meta", "2026-10-14T12:00:00Z", id="synthetic", cwd="/fixture", source="cli"
    )
    with path.open("wb") as output:
        output.write(meta)
        output.write(
            b'{"timestamp":"2026-10-14T12:00:00.125Z","type":"event_msg","payload":{"ignored":"'
        )
        for _ in range(4):
            output.write(b"x" * (1024 * 1024))
        output.write(b'","type":"task_started","turn_id":"turn"}}')
    ledger = Ledger()
    first = RolloutReader(tmp_path)
    first.scan_paths(ledger, [path])
    assert ledger.sessions["synthetic"].turns == {}
    checkpoint = json.loads(json.dumps(first.checkpoints))
    state = next(iter(checkpoint["files"].values()))
    assert state["offset"] == len(meta)
    assert "x" * 256 not in json.dumps(checkpoint)
    with path.open("ab") as output:
        output.write(b"\n")
        output.write(
            event("event_msg", "2026-10-14T12:00:02.375Z", type="task_complete", turn_id="turn")
        )
    restarted = RolloutReader(tmp_path, checkpoint)
    restarted.scan_paths(ledger, [path])
    turn = ledger.sessions["synthetic"].turns["turn"]
    assert turn.start == datetime.fromisoformat("2026-10-14T12:00:00.125+00:00")
    assert turn.end == datetime.fromisoformat("2026-10-14T12:00:02.375+00:00")
    restarted.scan(ledger)
    assert len(ledger.sessions["synthetic"].turns) == 1


@pytest.mark.parametrize("token", ["😃".encode(), b"\\uD83D\\uDE03", b'\\"', b"\\\\", b"\\n"])
def test_utf8_and_json_escapes_cross_chunk_before_selected_context(
    tmp_path: Path, token: bytes
) -> None:
    from codex_time.ingest import RolloutReader
    from codex_time.models import Ledger

    path = tmp_path / "sessions" / "boundary.jsonl"
    path.parent.mkdir()
    prefix = b'{"timestamp":"2026-10-14T12:00:01Z","type":"turn_context","payload":{"ignored":"'
    # First token byte is the final byte of the initial64KiB prefix. Subsequent
    # UTF8/escape bytes must be validated after the stream fills its next chunk.
    padding = 65535 - len(prefix)
    suffix = (
        b'","turn_id":"turn","cwd":"'
        + "/fixture/😃".encode()
        + b'","model":"gpt-6.1-sol","effort":"high"}}\n'
    )
    path.write_bytes(
        event("session_meta", "2026-10-14T12:00:00Z", id="synthetic", cwd="/fixture", source="cli")
        + event("event_msg", "2026-10-14T12:00:00.125Z", type="task_started", turn_id="turn")
        + prefix
        + b"x" * padding
        + token
        + b"y" * 512
        + suffix
        + event("event_msg", "2026-10-14T12:00:02.375Z", type="task_complete", turn_id="turn")
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    turn = ledger.sessions["synthetic"].turns["turn"]
    assert turn.cwd == "/fixture/😃"
    assert turn.start == datetime.fromisoformat("2026-10-14T12:00:00.125+00:00")
    assert turn.end == datetime.fromisoformat("2026-10-14T12:00:02.375+00:00")
    assert [(context.model_id, context.reasoning_level) for context in turn.model_contexts] == [
        ("gpt-6.1-sol", "high")
    ]
    assert ledger.diagnostics == []


@pytest.mark.parametrize("bad", [b"\\q", b"\xf0\x28\x8c\xbc"])
def test_invalid_ignored_string_crossing_chunk_does_not_consume_next_record(
    tmp_path: Path, bad: bytes
) -> None:
    from codex_time.ingest import RolloutReader
    from codex_time.models import Ledger

    path = tmp_path / "sessions" / "invalid-boundary.jsonl"
    path.parent.mkdir()
    prefix = b'{"timestamp":"2026-10-14T12:00:01Z","type":"turn_context","payload":{"ignored":"'
    path.write_bytes(
        event("session_meta", "2026-10-14T12:00:00Z", id="synthetic", cwd="/fixture", source="cli")
        + event("event_msg", "2026-10-14T12:00:00.125Z", type="task_started", turn_id="turn")
        + prefix
        + b"x" * (65535 - len(prefix))
        + bad
        + b"y" * 512
        + b'","turn_id":"turn","cwd":"/must-not-apply","model":"wrong"}}\n'
        + event("event_msg", "2026-10-14T12:00:02.375Z", type="task_complete", turn_id="turn")
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    turn = ledger.sessions["synthetic"].turns["turn"]
    assert turn.end == datetime.fromisoformat("2026-10-14T12:00:02.375+00:00")
    assert turn.cwd == "/fixture"
    assert turn.model_contexts == []
    assert "malformed rollout record skipped" in ledger.diagnostics
