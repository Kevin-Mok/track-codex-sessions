"""Real daemon process + disposable Unix server + UI exit + restart smoke test."""

import asyncio
import json
import os
import pty
import select
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from websockets.asyncio.server import ServerConnection, unix_serve

from codex_time.accounting import segments, total_seconds
from codex_time.storage import Store


def line(kind: str, payload: dict[str, object]) -> str:
    return (
        json.dumps({"timestamp": datetime.now(UTC).isoformat(), "type": kind, "payload": payload})
        + "\n"
    )


async def until(predicate: object, timeout: float = 12) -> None:
    # Tests require a callable but use no production dependency injection.
    from collections.abc import Callable
    from typing import cast

    fn = cast(Callable[[], bool], predicate)
    async with asyncio.timeout(timeout):
        while not fn():
            await asyncio.sleep(0.05)


async def test_daemon_survives_ui_exit_restart_and_stale_checkpoint(tmp_path: Path) -> None:
    home = tmp_path / "codex"
    rollout = home / "sessions" / "fixture.jsonl"
    rollout.parent.mkdir(parents=True)
    rollout.write_text(
        line("session_meta", {"id": "one", "cwd": str(tmp_path), "source": "cli"})
        + line("event_msg", {"type": "task_started", "turn_id": "turn"})
        + line("turn_context", {"turn_id": "turn", "model": "fixture-model", "effort": "high"})
    )
    store = Store(tmp_path / "data", tmp_path / "state")
    socket_path = tmp_path / "observer.sock"
    state = "working"
    calls = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            request = json.loads(raw)
            method = request["method"]
            calls.append(method)
            if method == "initialized":
                continue
            if method == "initialize":
                result = {}
            elif method == "thread/loaded/list":
                result = {"data": ["one"], "nextCursor": None}
            else:
                assert method == "thread/read"
                assert request["params"] == {"threadId": "one", "includeTurns": False}
                result = {
                    "thread": {
                        "id": "one",
                        "cwd": str(tmp_path),
                        "status": {
                            "type": "idle" if state == "idle" else "active",
                            "activeFlags": ["waitingOnUserInput"] if state == "waiting" else [],
                        },
                    }
                }
            await ws.send(json.dumps({"id": request["id"], "result": result}))

    command = [
        sys.executable,
        "-c",
        "from codex_time.cli import main; raise SystemExit(main())",
        "--codex-home",
        str(home),
        "--data-dir",
        str(store.root),
        "--state-dir",
        str(store.runtime),
        "--socket",
        str(socket_path),
    ]
    env = dict(os.environ, TERM="xterm-256color")
    async with unix_serve(handler, str(socket_path)):
        daemon = subprocess.Popen(
            [*command, "daemon"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        try:
            await until(
                lambda: (
                    total_seconds(segments(list(store.load().sessions.get("one").turns.values())))
                    > 0.9
                    if "one" in store.load().sessions
                    else False
                )
            )
            # Open and close the actual picker while the independent daemon is alive.
            master, slave = pty.openpty()
            ui = subprocess.Popen(
                command, env=env, cwd=tmp_path, stdin=slave, stdout=slave, stderr=slave
            )
            try:
                ready = False
                async with asyncio.timeout(8):
                    while not ready:
                        if select.select([master], [], [], 0)[0]:
                            ready = b"Codex time" in os.read(master, 65536)
                        else:
                            await asyncio.sleep(0.05)
                os.write(master, b"q")
                await until(lambda: ui.poll() is not None)
                assert ui.returncode == 0
            finally:
                if ui.poll() is None:
                    ui.kill()
                    ui.wait()
                os.close(master)
                os.close(slave)
            before = total_seconds(segments(list(store.load().sessions["one"].turns.values())))
            await until(
                lambda: (
                    total_seconds(segments(list(store.load().sessions["one"].turns.values())))
                    > before + 0.9
                )
            )
            state = "waiting"
            await until(lambda: any(s.waits for s in store.load().sessions["one"].turns.values()))
            daemon.terminate()
            await until(lambda: daemon.poll() is not None)
            assert daemon.returncode == 0, daemon.stderr.read().decode()
            assert store.runtime_read()["heartbeat"] is None
            # Simulate a Git restore: same session retained, turns removed, cache stale.
            with store.writer():
                restored = store.load()
                restored.sessions["one"].turns = {}
                store.save(restored)
            state = "working"
            daemon = subprocess.Popen(
                [*command, "daemon"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            await until(lambda: "turn" in store.load().sessions["one"].turns)
            await until(
                lambda: (
                    total_seconds(segments(list(store.load().sessions["one"].turns.values()))) > 0.9
                )
            )
            state = "idle"
            with rollout.open("a") as output:
                output.write(line("event_msg", {"type": "task_complete", "turn_id": "turn"}))
            await until(lambda: store.load().sessions["one"].turns["turn"].end is not None)
            assert len(store.load().sessions["one"].turns) == 1
            context = store.load().sessions["one"].turns["turn"].model_contexts
            assert len(context) == 1 and context[0].model_id == "fixture-model"
            assert set(calls) == {"initialize", "initialized", "thread/loaded/list", "thread/read"}
        finally:
            if daemon.poll() is None:
                daemon.terminate()
                await until(lambda: daemon.poll() is not None)
            if daemon.stderr:
                daemon.stderr.close()
