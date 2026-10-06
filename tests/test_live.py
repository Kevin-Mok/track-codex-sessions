"""Real disposable Unix WebSocket peers exercise the read-only wire contract."""

import asyncio
import importlib
import json
from pathlib import Path

import pytest
from websockets.asyncio.server import ServerConnection, unix_serve


def client_class():
    spec = importlib.util.find_spec("codex_time.live")
    assert spec is not None, "LiveClient must observe an existing Unix WebSocket server"
    return importlib.import_module("codex_time.live").LiveClient


@pytest.mark.asyncio
async def test_real_unix_peer_handshake_pagination_and_wait_states(tmp_path: Path):
    requests = []
    phase = 0

    async def peer(ws: ServerConnection):
        async for raw in ws:
            request = json.loads(raw)
            requests.append(request)
            method = request["method"]
            if method == "initialized":
                continue
            if method == "initialize":
                assert request["params"]["clientInfo"]["name"] == "codex-time"
                result = {"userAgent": "fixture", "platformFamily": "unix"}
            elif method == "thread/loaded/list":
                cursor = request["params"].get("cursor")
                result = {
                    "data": ["root-b"] if cursor else ["root-a"],
                    "nextCursor": None if cursor else "second-page",
                }
            elif method == "thread/read":
                assert request["params"]["includeTurns"] is False
                session_id = request["params"]["threadId"]
                flags = ["waitingOnApproval"] if phase == 1 else []
                if phase == 2:
                    flags = ["waitingOnUserInput"]
                status = (
                    {"type": "idle"}
                    if session_id == "root-b"
                    else {"type": "active", "activeFlags": flags}
                )
                result = {
                    "thread": {
                        "id": session_id,
                        "cwd": "/safe/project",
                        "status": status,
                        "turns": [],
                    }
                }
            else:
                pytest.fail(f"unsafe or unknown RPC: {method}")
            # An unsolicited notification must not be confused with the RPC response.
            await ws.send(json.dumps({"method": "thread/status/changed", "params": {}}))
            await ws.send(json.dumps({"id": request["id"], "result": result}))

    socket = tmp_path / "observer.sock"
    async with unix_serve(peer, str(socket)):
        client = client_class()(tmp_path, socket_path=socket)
        try:
            for next_phase, expected in [
                (0, "working"),
                (1, "waiting"),
                (2, "waiting"),
                (3, "working"),
            ]:
                phase = next_phase
                observations = await client.poll()
                assert {o.session_id: o.state for o in observations} == {
                    "root-a": expected,
                    "root-b": "idle",
                }
                assert all(o.turn_id is None for o in observations)
                assert all(o.at.utcoffset().total_seconds() == 0 for o in observations)
                assert all(o.cwd == "/safe/project" for o in observations)
                assert client.diagnostic is None
        finally:
            await client.close()
    assert [r["method"] for r in requests].count("initialize") == 1
    assert {r["method"] for r in requests} == {
        "initialize",
        "initialized",
        "thread/loaded/list",
        "thread/read",
    }


@pytest.mark.asyncio
async def test_disconnect_reports_unknown_and_reconnects(tmp_path: Path):
    drop = False
    handshakes = 0

    async def peer(ws: ServerConnection):
        nonlocal handshakes
        async for raw in ws:
            r = json.loads(raw)
            if r["method"] == "initialized":
                continue
            if drop:
                await ws.close()
                return
            if r["method"] == "initialize":
                handshakes += 1
                result = {}
            elif r["method"] == "thread/loaded/list":
                result = {"data": ["root"], "nextCursor": None}
            else:
                result = {
                    "thread": {
                        "id": "root",
                        "cwd": "/fixture",
                        "status": {"type": "active", "activeFlags": []},
                    }
                }
            await ws.send(json.dumps({"id": r["id"], "result": result}))

    socket = tmp_path / "observer.sock"
    async with unix_serve(peer, str(socket)):
        client = client_class()(tmp_path, socket_path=socket)
        try:
            assert (await client.poll())[0].state == "working"
            drop = True
            assert (await client.poll())[0].state == "unknown"
            assert client.diagnostic
            drop = False
            assert (await client.poll())[0].state == "working"
            assert client.diagnostic is None
            assert handshakes == 2
        finally:
            await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        {"type": "active", "activeFlags": ["futureFlag"]},
        {"type": "active"},
        {"type": "futureStatus"},
        {"type": "systemError"},
        {"type": "notLoaded"},
    ],
)
async def test_unknown_status_schema_never_counts_as_work(tmp_path: Path, status):
    async def peer(ws: ServerConnection):
        async for raw in ws:
            r = json.loads(raw)
            if r["method"] == "initialized":
                continue
            result = {}
            if r["method"] == "thread/loaded/list":
                result = {"data": ["root"], "nextCursor": None}
            if r["method"] == "thread/read":
                result = {"thread": {"id": "root", "cwd": "/safe", "status": status}}
            await ws.send(json.dumps({"id": r["id"], "result": result}))

    socket = tmp_path / "observer.sock"
    async with unix_serve(peer, str(socket)):
        client = client_class()(tmp_path, socket_path=socket)
        try:
            assert (await client.poll())[0].state == "unknown"
            assert client.diagnostic
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_missing_socket_is_visible_without_starting_codex(tmp_path: Path):
    client = client_class()(tmp_path)
    assert await client.poll() == []
    assert "socket" in client.diagnostic.lower()
    await client.close()


@pytest.mark.asyncio
async def test_auto_discovery_uses_control_socket_symlink(tmp_path: Path):
    control = tmp_path / "app-server-control"
    control.mkdir()
    socket = tmp_path / "existing.sock"
    (control / "app-server-control.sock").symlink_to(socket)

    async def peer(ws: ServerConnection):
        async for raw in ws:
            r = json.loads(raw)
            if r["method"] == "initialized":
                continue
            result = {} if r["method"] == "initialize" else {"data": [], "nextCursor": None}
            await ws.send(json.dumps({"id": r["id"], "result": result}))

    async with unix_serve(peer, str(socket)):
        client = client_class()(tmp_path)
        try:
            assert await client.poll() == []
            assert client.diagnostic is None
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_timeout_never_persists_server_error_contents(tmp_path: Path):
    async def peer(ws: ServerConnection):
        await ws.recv()
        await asyncio.sleep(0.1)

    socket = tmp_path / "observer.sock"
    async with unix_serve(peer, str(socket)):
        client = client_class()(tmp_path, socket_path=socket)
        client.timeout = 0.02
        try:
            assert await client.poll() == []
            assert "TimeoutError" in client.diagnostic
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_rpc_rejection_diagnostic_discards_sensitive_server_message(tmp_path: Path):
    async def peer(ws: ServerConnection):
        r = json.loads(await ws.recv())
        await ws.send(
            json.dumps(
                {
                    "id": r["id"],
                    "error": {
                        "code": -32602,
                        "message": "private conversation body or authentication token",
                    },
                }
            )
        )

    socket = tmp_path / "observer.sock"
    async with unix_serve(peer, str(socket)):
        client = client_class()(tmp_path, socket_path=socket)
        try:
            assert await client.poll() == []
            assert "rejected" in client.diagnostic
            assert "private" not in client.diagnostic
            assert "authentication" not in client.diagnostic
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_repeated_pagination_cursor_is_visible_and_bounded(tmp_path: Path):
    async def peer(ws: ServerConnection):
        async for raw in ws:
            r = json.loads(raw)
            if r["method"] == "initialized":
                continue
            result = (
                {} if r["method"] == "initialize" else {"data": ["root"], "nextCursor": "repeated"}
            )
            await ws.send(json.dumps({"id": r["id"], "result": result}))

    socket = tmp_path / "observer.sock"
    async with unix_serve(peer, str(socket)):
        client = client_class()(tmp_path, socket_path=socket)
        try:
            assert await client.poll() == []
            assert "pagination" in client.diagnostic
        finally:
            await client.close()
