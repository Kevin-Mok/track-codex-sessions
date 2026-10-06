import json
from pathlib import Path

import pytest

from codex_time.models import Ledger


def line(kind: str, second: int, **payload: object) -> str:
    return (
        json.dumps(
            {"timestamp": f"2026-10-06T12:00:{second:02d}Z", "type": kind, "payload": payload}
        )
        + "\n"
    )


def rollout(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "sessions" / "one.jsonl"
    p.parent.mkdir()
    p.write_text("".join(lines))
    return p


def base() -> list[str]:
    return [
        line("session_meta", 0, id="s1", cwd="/a", source="cli"),
        line("event_msg", 0, type="task_started", turn_id="t1"),
    ]


def test_lifecycle_import_is_idempotent_and_preserves_turn_cwd(tmp_path: Path) -> None:
    from codex_time.ingest import RolloutReader

    rollout(
        tmp_path,
        base()
        + [
            line("turn_context", 1, turn_id="t1", cwd="/a"),
            line("event_msg", 20, type="task_complete", turn_id="t1"),
            line("event_msg", 30, type="task_started", turn_id="t2"),
            line("turn_context", 31, turn_id="t2", cwd="/b"),
            line("event_msg", 50, type="turn_aborted", turn_id="t2"),
        ],
    )
    ledger = Ledger()
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)
    RolloutReader(tmp_path, json.loads(json.dumps(reader.checkpoints))).scan(ledger)
    RolloutReader(tmp_path).scan(ledger)
    assert len(ledger.sessions["s1"].turns) == 2
    assert ledger.sessions["s1"].turns["t1"].cwd == "/a"
    assert ledger.sessions["s1"].turns["t2"].cwd == "/b"
    assert ledger.sessions["s1"].turns["t2"].outcome == "turn_aborted"
    assert ledger.sessions["s1"].title == ""


def test_blocking_waits_close_across_restart_but_async_questions_do_not(tmp_path: Path) -> None:
    from codex_time.ingest import RolloutReader

    p = rollout(
        tmp_path,
        base()
        + [
            line(
                "response_item",
                10,
                type="function_call",
                name="functions.request_user_input",
                call_id="c1",
                arguments="SECRET",
            )
        ],
    )
    ledger = Ledger()
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)
    assert "SECRET" not in json.dumps(reader.checkpoints)
    with p.open("a") as f:
        f.write(
            line("response_item", 30, type="function_call_output", call_id="c1", output="SECRET")
        )
        f.write(
            line(
                "response_item",
                35,
                type="function_call",
                name="functions.request_user_input_async",
                call_id="c2",
            )
        )
        f.write(line("event_msg", 40, type="verified_answer", call_id="c2"))
        f.write(line("event_msg", 50, type="task_complete", turn_id="t1"))
    RolloutReader(tmp_path, reader.checkpoints).scan(ledger)
    waits = ledger.sessions["s1"].turns["t1"].waits
    assert len(waits) == 1
    assert (waits[0].end - waits[0].start).total_seconds() == 20
    assert "SECRET" not in ledger.model_dump_json()


def test_partial_lines_archive_move_and_malformed_content(tmp_path: Path) -> None:
    from codex_time.ingest import RolloutReader

    terminal = line("event_msg", 20, type="task_complete", turn_id="t1")
    p = rollout(tmp_path, base() + ["SECRET bad json\n", terminal[:40]])
    ledger = Ledger()
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)
    assert ledger.sessions["s1"].turns["t1"].end is None
    with p.open("a") as f:
        f.write(terminal[40:])
    archive = tmp_path / "archived_sessions"
    archive.mkdir()
    p.rename(archive / p.name)
    reader.scan(ledger)
    assert ledger.sessions["s1"].turns["t1"].end is not None
    assert ledger.sessions["s1"].archived
    assert "SECRET" not in ledger.model_dump_json()


def test_child_source_and_missing_terminal_do_not_invent_end(tmp_path: Path) -> None:
    from codex_time.ingest import RolloutReader

    rollout(
        tmp_path,
        [
            line(
                "session_meta",
                0,
                id="s1",
                cwd="/a",
                source={"subagent": {"thread_spawn": {"parent_thread_id": "parent"}}},
            ),
            line("event_msg", 1, type="task_started", turn_id="t1"),
        ],
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    session = ledger.sessions["s1"]
    assert session.is_child and session.parent_id == "parent"
    assert session.turns["t1"].end is None
    assert "historical_upper_bound" in session.turns["t1"].quality


def test_missing_lifecycle_is_visible_and_invalid_checkpoint_is_safe(tmp_path: Path) -> None:
    from codex_time.ingest import RolloutReader

    p = rollout(tmp_path, [line("session_meta", 0, id="s1", cwd="/a", source="cli")])
    stat = p.stat()
    checkpoints = {"version": 1, "files": {f"{stat.st_dev}:{stat.st_ino}": {"offset": -1}}}
    ledger = Ledger()
    RolloutReader(tmp_path, checkpoints).scan(ledger)
    assert "no_lifecycle_events" in ledger.sessions["s1"].quality
    assert ledger.diagnostics


def test_replaced_rollout_does_not_skip_new_session(tmp_path: Path) -> None:
    from codex_time.ingest import RolloutReader

    p = rollout(tmp_path, base())
    ledger = Ledger()
    reader = RolloutReader(tmp_path)
    reader.scan(ledger)
    p.write_text(
        "".join(
            [
                line("session_meta", 0, id="s2", cwd="/b", source="cli"),
                line("event_msg", 1, type="task_started", turn_id="t2"),
                line("event_msg", 20, type="task_complete", turn_id="t2"),
            ]
        )
    )
    reader.scan(ledger)
    assert ledger.sessions["s2"].turns["t2"].end is not None


def test_verified_answer_matches_blocking_call_without_persisting_answers(tmp_path: Path) -> None:
    from codex_time.ingest import RolloutReader

    rollout(
        tmp_path,
        base()
        + [
            line(
                "response_item",
                10,
                type="function_call",
                name="functions.request_user_input",
                call_id="c1",
            ),
            line(
                "event_msg",
                30,
                type="verified_answer",
                call_id="c1",
                questions={"secret": "SECRET"},
            ),
            line("event_msg", 40, type="task_complete", turn_id="t1"),
        ],
    )
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert len(ledger.sessions["s1"].turns["t1"].waits) == 1
    assert "SECRET" not in ledger.model_dump_json()


@pytest.mark.parametrize("kind", ["session_meta", "event_msg", "turn_context", "response_item"])
def test_recognized_records_with_nonobject_payload_report_unsupported_schema(
    tmp_path: Path,
    kind: str,
) -> None:
    from codex_time.ingest import RolloutReader

    malformed = (
        json.dumps({"timestamp": "2026-10-06T12:00:00Z", "type": kind, "payload": ["SECRET"]})
        + "\n"
    )
    rollout(tmp_path, [malformed])
    ledger = Ledger()
    RolloutReader(tmp_path).scan(ledger)
    assert "unsupported rollout payload schema; record skipped" in ledger.diagnostics
    assert "SECRET" not in ledger.model_dump_json()
