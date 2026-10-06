"""Metadata-only observer of an existing Codex Unix WebSocket control socket.

No observer action loads, resumes, starts, subscribes to, or changes a thread.
An observation is a sample, not proof of continuity between samples. Callers
must preserve gaps and the uncertainty of one-second polling in accounting.
"""

import asyncio
import json
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from websockets.asyncio.client import ClientConnection, unix_connect
from websockets.exceptions import WebSocketException

from codex_time.models import Observation, RuntimeState

_RPC_ALLOWLIST = frozenset({"initialize", "thread/loaded/list", "thread/read"})
_WAIT_FLAGS = frozenset({"waitingOnApproval", "waitingOnUserInput"})


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"unsupported {label} schema")
    return cast(dict[str, object], value)


class LiveClient:
    """Reconnectable read-only client; a failed poll returns known ids as unknown."""

    def __init__(self, home: Path, socket_path: Path | None = None) -> None:
        self.home = home
        self.socket_path = socket_path
        self.timeout = 5.0
        self.diagnostic: str | None = None
        self._connection: ClientConnection | None = None
        self._request_id = 0
        self._known: dict[str, Observation] = {}

    def _discover(self) -> Path:
        if self.socket_path is not None:
            candidates = [self.socket_path]
        else:
            candidates = [self.home / "app-server-control" / "app-server-control.sock"]
        for path in candidates:
            try:
                if stat.S_ISSOCK(path.stat().st_mode):
                    return path
            except OSError:
                continue
        raise FileNotFoundError("existing Codex control socket not found")

    async def _rpc(self, method: str, params: dict[str, object]) -> dict[str, object]:
        if method not in _RPC_ALLOWLIST:
            raise ValueError("observer RPC is not in the read-only allowlist")
        connection = self._connection
        if connection is None:
            raise ConnectionError("observer is disconnected")
        self._request_id += 1
        request_id = self._request_id
        await connection.send(json.dumps({"id": request_id, "method": method, "params": params}))
        while True:
            message: object = json.loads(await connection.recv())
            response = _object(message, "RPC envelope")
            if response.get("id") != request_id:
                # Never process notification bodies, tool output, or unsolicited requests.
                continue
            if "error" in response:
                # Deliberately exclude server error text: it can contain conversation data.
                raise ValueError(f"Codex rejected read-only RPC {method}")
            return _object(response.get("result"), f"{method} result")

    async def _connect(self) -> None:
        if self._connection is not None:
            return
        self._connection = await unix_connect(
            str(self._discover()),
            uri="ws://localhost/",
            open_timeout=self.timeout,
            close_timeout=0.2,
            max_size=2**20,
        )
        await self._rpc(
            "initialize",
            {
                "clientInfo": {
                    "name": "codex-time",
                    "title": "Codex time observer",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": False, "requestAttestation": False},
            },
        )
        await self._connection.send(json.dumps({"method": "initialized", "params": {}}))

    async def _loaded(self) -> list[str]:
        ids: list[str] = []
        cursor: str | None = None
        seen: set[str] = set()
        while True:
            page = await self._rpc("thread/loaded/list", {"cursor": cursor, "limit": 100})
            data = page.get("data")
            if not isinstance(data, list) or any(not isinstance(item, str) for item in data):
                raise ValueError("unsupported loaded-thread list schema")
            ids.extend(cast(list[str], data))
            next_cursor = page.get("nextCursor")
            if next_cursor is None:
                return list(dict.fromkeys(ids))
            if not isinstance(next_cursor, str) or next_cursor in seen:
                raise ValueError("unsupported loaded-thread pagination schema")
            seen.add(next_cursor)
            cursor = next_cursor

    def _status(self, value: object) -> RuntimeState:
        status = _object(value, "thread status")
        kind = status.get("type")
        if kind == "idle":
            return "idle"
        if kind == "active":
            flags = status.get("activeFlags")
            if isinstance(flags, list) and all(
                isinstance(flag, str) and flag in _WAIT_FLAGS for flag in flags
            ):
                return "waiting" if flags else "working"
        self.diagnostic = "Codex runtime state unavailable or unsupported; timing is uncertain"
        return "unknown"

    async def poll(self) -> list[Observation]:
        """Read one bounded sample. Never extrapolate an unavailable runtime state."""
        self.diagnostic = None
        try:
            async with asyncio.timeout(self.timeout):
                await self._connect()
                observations = []
                for session_id in await self._loaded():
                    read_began = asyncio.get_running_loop().time()
                    result = await self._rpc(
                        "thread/read",
                        {
                            "threadId": session_id,
                            "includeTurns": False,
                        },
                    )
                    thread = _object(result.get("thread"), "thread metadata")
                    if thread.get("id") != session_id:
                        raise ValueError("thread metadata identity mismatch")
                    cwd = thread.get("cwd")
                    if cwd is not None and not isinstance(cwd, str):
                        raise ValueError("unsupported thread working-directory schema")
                    observations.append(
                        Observation(
                            session_id=session_id,
                            state=self._status(thread.get("status")),
                            at=datetime.now(UTC),
                            cwd=cwd,
                            uncertainty_seconds=1 + asyncio.get_running_loop().time() - read_began,
                        )
                    )
                self._known = {item.session_id: item for item in observations}
                return observations
        except (OSError, TimeoutError, WebSocketException, ValueError) as exc:
            if isinstance(exc, FileNotFoundError):
                self.diagnostic = "Existing Codex control socket unavailable; runtime is unknown"
            elif isinstance(exc, ValueError):
                # Our explicit schema errors contain no external values.
                self.diagnostic = (
                    str(exc)
                    if not isinstance(exc, json.JSONDecodeError)
                    else ("Unsupported Codex RPC JSON; runtime is unknown")
                )
            else:
                self.diagnostic = f"Codex observation unavailable ({type(exc).__name__})"
            await self.close()
            at = datetime.now(UTC)
            return [
                Observation(session_id=item.session_id, state="unknown", at=at, cwd=item.cwd)
                for item in self._known.values()
            ]

    async def close(self) -> None:
        """Close only this client's transport, preserving Codex's existing server."""
        connection, self._connection = self._connection, None
        if connection is not None:
            await connection.close()
