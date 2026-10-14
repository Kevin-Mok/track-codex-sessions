"""Project oversized JSONL records through a bounded, content-free lexer."""

from __future__ import annotations

import codecs
import json
import re
from collections.abc import Callable
from typing import BinaryIO, cast

CHUNK_BYTES = 64 * 1024
MAX_METADATA_BYTES = 1024 * 1024
MAX_METADATA_NODES = 4096
# Disjoint chunks need no backtracking, including densely escaped tool output.
_STRING_RUN = re.compile(rb'(?:[^"\\\x00-\x1f]++|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*+')
_DELIMITERS = b" \t\r\n,]}"


class IncompleteRecord(Exception):
    """The final source line has not been committed by a newline yet."""


class _Line:
    def __init__(
        self, source: BinaryIO, first: bytes, progress: Callable[[], None] | None = None
    ) -> None:
        self.source = source
        self.progress = progress
        self.data = first
        self.pos = 0
        self.complete = first.endswith(b"\n")
        self.eof = False
        self.decoder = codecs.getincrementaldecoder("utf-8")()

    def validate(self) -> None:
        # Validate encoding in bounded chunks; never materialize a whole body.
        self.decoder.decode(self.data, final=self.complete)

    def fill(self) -> bool:
        if self.pos < len(self.data):
            return True
        if self.complete or self.eof:
            return False
        self.data = self.source.readline(CHUNK_BYTES)
        self.pos = 0
        self.eof = not self.data
        self.complete = self.data.endswith(b"\n")
        if self.data:
            self.validate()
            if self.progress is not None:
                self.progress()
        return bool(self.data)

    def peek(self) -> int | None:
        return self.data[self.pos] if self.fill() else None

    def take(self) -> int:
        value = self.peek()
        if value is None:
            raise ValueError("incomplete JSON value")
        self.pos += 1
        return value

    def space(self) -> None:
        while self.peek() in (9, 10, 13, 32):
            self.pos += 1

    def drain(self) -> bool:
        # A malformed record must not turn its remaining chunks into records.
        while not self.complete and not self.eof:
            self.data = self.source.readline(CHUNK_BYTES)
            self.pos = 0
            self.eof = not self.data
            self.complete = self.data.endswith(b"\n")
        return self.complete


class _Selector:
    def __init__(self, line: _Line) -> None:
        self.line = line
        self.metadata_bytes = 0
        self.metadata_nodes = 0

    def charge(self, size: int = 0) -> None:
        self.metadata_bytes += size
        self.metadata_nodes += 1
        if (
            self.metadata_bytes > MAX_METADATA_BYTES
            or self.metadata_nodes > MAX_METADATA_NODES
        ):
            raise ValueError("selected metadata exceeds bounded record schema")

    def string(self, capture: bool) -> str | None:
        line = self.line
        if line.take() != 34:
            raise ValueError("expected JSON string")
        saved = bytearray(b'"') if capture else None
        while line.peek() is not None:
            start = line.pos
            match = _STRING_RUN.match(line.data, start)
            assert match is not None
            line.pos = match.end()
            if saved is not None and line.pos > start:
                self.charge(line.pos - start)
                saved.extend(line.data[start:line.pos])
            if line.pos == len(line.data):
                if not line.fill():
                    break
                continue
            value = line.peek()
            if value is None:
                break
            if value == 34:
                line.pos += 1
                if saved is None:
                    return None
                saved.append(34)
                return cast(str, json.loads(bytes(saved)))
            if value == 92:
                # Only an invalid or chunk-split escape reaches this branch.
                escape = bytearray([line.take(), line.take()])
                if escape[1] == 117:
                    for _ in range(4):
                        char = line.take()
                        if char not in b"0123456789abcdefABCDEF":
                            raise ValueError("invalid JSON unicode escape")
                        escape.append(char)
                elif escape[1] not in b'"\\/bfnrt':
                    raise ValueError("invalid JSON escape")
                if saved is not None:
                    self.charge(len(escape))
                    saved.extend(escape)
            elif line.pos == start or value < 32:
                raise ValueError("invalid JSON string")
        raise ValueError("unterminated JSON string")

    def value(
        self, selector: dict[str, object] | None = None, *, capture: bool = False, depth: int = 0
    ) -> object:
        if depth > 256:
            raise ValueError("JSON nesting exceeds bounded record schema")
        line = self.line
        line.space()
        token = line.peek()
        if token is None:
            raise ValueError("missing JSON value")
        keep = capture or selector is not None
        if keep:
            self.charge()
        if token == 123:
            result: dict[str, object] = {}
            line.pos += 1
            line.space()
            if line.peek() == 125:
                line.pos += 1
                return result if keep else None
            while True:
                line.space()
                key = self.string(keep)
                line.space()
                if line.take() != 58:
                    raise ValueError("missing JSON colon")
                selected = capture or (selector is not None and key in selector)
                child = selector.get(key) if selector is not None and key is not None else None
                nested = child if isinstance(child, dict) else None
                value = self.value(
                    cast(dict[str, object] | None, nested),
                    capture=selected and nested is None,
                    depth=depth + 1,
                )
                if selected and key is not None:
                    result[key] = value
                line.space()
                char = line.take()
                if char == 125:
                    return result if keep else None
                if char != 44:
                    raise ValueError("invalid JSON object delimiter")
        if token == 91:
            values: list[object] = []
            line.pos += 1
            line.space()
            if line.peek() == 93:
                line.pos += 1
                return values if capture else []
            while True:
                value = self.value(capture=capture, depth=depth + 1)
                if capture:
                    values.append(value)
                line.space()
                char = line.take()
                if char == 93:
                    return values if capture else []
                if char != 44:
                    raise ValueError("invalid JSON array delimiter")
        if token == 34:
            return self.string(capture)
        raw = bytearray()
        while (scalar_char := line.peek()) is not None and scalar_char not in _DELIMITERS:
            if len(raw) >= 8192:
                raise ValueError("numeric or literal token exceeds bounded record schema")
            raw.append(line.take())
        if not raw:
            raise ValueError("invalid JSON scalar")
        value = json.loads(bytes(raw))
        if capture:
            self.charge(len(raw))
            return value
        return None


def read_large_record(
    source: BinaryIO, first: bytes, selectors: dict[str, object],
    *, progress: Callable[[], None] | None = None,
) -> dict[str, object]:
    """Consume one line, retaining only selected metadata and bounded buffers.

    The stream already consumed ``first``. Full malformed lines are drained;
    an unfinished final line raises IncompleteRecord without committing evidence.
    Selected metadata is limited to 1 MiB/4096 nodes, with no limit on ignored
    string lengths. Bytes and elapsed work are accounted at the complete-record
    boundary by the caller; one giant record can exceed its nominal batch size.
    """
    line = _Line(source, first, progress)
    error: ValueError | TypeError | OverflowError | RecursionError | None = None
    result: object = None
    try:
        line.validate()
        line.space()
        if line.peek() != 123:
            raise ValueError("expected JSON object")
        result = _Selector(line).value(selectors)
        line.space()
        if line.peek() is not None:
            raise ValueError("trailing JSON input")
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        error = exc
    complete = line.drain()
    if not complete:
        raise IncompleteRecord
    if error is not None:
        raise error
    return cast(dict[str, object], result)
