"""Bounded Linux file notifications with explicit reconciliation on event loss.

Only source paths are queued. Notifications never contain rollout contents, and
all scanning stays in the daemon's single writer loop.
"""

from __future__ import annotations

import ctypes
import os
import struct
from pathlib import Path

_MODIFY = 0x00000002
_ATTRIB = 0x00000004
_CLOSE_WRITE = 0x00000008
_MOVED_FROM = 0x00000040
_MOVED_TO = 0x00000080
_CREATE = 0x00000100
_DELETE = 0x00000200
_DELETE_SELF = 0x00000400
_MOVE_SELF = 0x00000800
_OVERFLOW = 0x00004000
_IGNORED = 0x00008000
_ISDIR = 0x40000000
_ONLYDIR = 0x01000000
_MASK = (_MODIFY | _ATTRIB | _CLOSE_WRITE | _MOVED_FROM | _MOVED_TO | _CREATE
         | _DELETE | _DELETE_SELF | _MOVE_SELF | _ONLYDIR)
_HEADER = struct.Struct("iIII")


class ChangeWatcher:
    """Coalesce up to ``max_pending`` paths; overflow requests a safe scan.

    ``fd`` may be registered with ``loop.add_reader``. ``drain`` consumes a
    bounded number of nonblocking kernel reads. Missing inotify support or a
    watch limit leaves ``needs_reconciliation`` true, requiring the daemon's
    regular fallback scan even when no notification arrives.
    """

    def __init__(
        self, home: Path, *, max_pending: int = 4096, max_watches: int = 8192
    ) -> None:
        if max_pending < 1 or max_watches < 1:
            raise ValueError("notification limits must be positive")
        self.home = home
        self.max_pending = max_pending
        self.max_watches = max_watches
        self.fd: int | None = None
        self.needs_reconciliation = False
        self._overflow = False
        self._pending: set[Path] = set()
        self._watches: dict[int, Path] = {}
        try:
            self._lib = ctypes.CDLL(None, use_errno=True)
            self._lib.inotify_init1.argtypes = [ctypes.c_int]
            self._lib.inotify_init1.restype = ctypes.c_int
            self._lib.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
            self._lib.inotify_add_watch.restype = ctypes.c_int
            fd = int(self._lib.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC))
            if fd < 0:
                raise OSError(ctypes.get_errno(), "inotify unavailable")
            self.fd = fd
            self._watch(home)
            for name in ("sessions", "archived_sessions"):
                self._add_tree(home / name, discover=False)
        except (AttributeError, OSError):
            self.needs_reconciliation = self._overflow = True

    @property
    def available(self) -> bool:
        return self.fd is not None

    def _watch(self, path: Path) -> None:
        if self.fd is None or not path.is_dir():
            return
        if path in self._watches.values():
            return
        if len(self._watches) >= self.max_watches:
            self.needs_reconciliation = self._overflow = True
            return
        wd = int(self._lib.inotify_add_watch(self.fd, os.fsencode(path), _MASK))
        if wd < 0:
            self.needs_reconciliation = self._overflow = True
            return
        self._watches[wd] = path

    def _inside_sources(self, path: Path) -> bool:
        return any(path.is_relative_to(self.home / name)
                   for name in ("sessions", "archived_sessions"))

    def _add_tree(self, path: Path, *, discover: bool) -> None:
        if not path.is_dir() or not self._inside_sources(path):
            return
        self._watch(path)
        for child in path.rglob("*"):
            if child.is_dir():
                self._watch(child)
            elif discover and child.suffix == ".jsonl":
                self._enqueue(child)

    def _enqueue(self, path: Path) -> None:
        if path in self._pending:
            return
        if len(self._pending) >= self.max_pending:
            self._overflow = True
            return
        self._pending.add(path)

    def drain(self) -> tuple[list[Path], bool]:
        """Return queued source paths and whether notifications may be missing."""
        if self.fd is not None:
            for _ in range(4):
                try:
                    raw = os.read(self.fd, 65536)
                except BlockingIOError:
                    break
                except OSError:
                    self.needs_reconciliation = self._overflow = True
                    break
                if not raw:
                    break
                offset = 0
                while offset + _HEADER.size <= len(raw):
                    wd, mask, _, size = _HEADER.unpack_from(raw, offset)
                    offset += _HEADER.size
                    name = os.fsdecode(raw[offset:offset + size].split(b"\0", 1)[0])
                    offset += size
                    if mask & _OVERFLOW:
                        self._overflow = True
                        continue
                    parent = self._watches.get(wd)
                    if parent is None:
                        continue
                    path = parent / name if name else parent
                    if mask & _IGNORED:
                        self._watches.pop(wd, None)
                        self._overflow = True
                    elif mask & _ISDIR or not name:
                        if mask & (_CREATE | _MOVED_TO):
                            self._add_tree(path, discover=True)
                        if mask & (_DELETE_SELF | _MOVE_SELF):
                            self._overflow = True
                    elif path.suffix == ".jsonl" and self._inside_sources(path):
                        self._enqueue(path)
            else:
                # Conservatively reconcile after a burst exceeding one drain's
                # read budget. Further drains still consume the remaining events.
                self._overflow = True
        paths = sorted(self._pending)
        overflow = self._overflow
        self._pending.clear()
        self._overflow = False
        return paths, overflow

    def close(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        self._watches.clear()
        self._pending.clear()
