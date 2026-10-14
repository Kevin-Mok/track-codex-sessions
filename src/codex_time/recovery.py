"""Streaming portable-store verification and lossless legacy rollback export."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from collections.abc import Iterator
from pathlib import Path

import ijson  # type: ignore[import-untyped]

from codex_time.incremental_storage import layout, read_session, sha256
from codex_time.models import QuotaObservation, Session, UsageObservation
from codex_time.storage import Store, StoreError


def sessions(root: Path) -> Iterator[Session]:
    if layout(root) is not None:
        for path in (root / "sessions").glob("*.json"):
            yield read_session(path)
        return
    path = root / "ledger.json"
    if not path.exists():
        return
    try:
        with path.open("rb") as source:
            if next(ijson.items(source, "version"), None) not in (1, 2, 3, 4):
                raise ValueError("unsupported version")
        with path.open("rb") as source:
            for sid, raw in ijson.kvitems(source, "sessions", use_float=True):
                session = Session.model_validate(raw)
                if session.id != sid or any(tid != t.id for tid, t in session.turns.items()):
                    raise ValueError("identifier/key mismatch")
                yield session
    except (ValueError, ijson.JSONError) as exc:
        raise StoreError("invalid legacy ledger; restore a valid backup") from exc


def evidence(root: Path, kind: str) -> Iterator[QuotaObservation | UsageObservation]:
    model = QuotaObservation if kind == "quota" else UsageObservation
    partitioned = layout(root) is not None
    if not partitioned and (root / "ledger.json").exists():
        try:
            with (root / "ledger.json").open("rb") as source:
                for raw in ijson.items(source, kind + "_observations.item", use_float=True):
                    yield model.model_validate(raw)
        except (ValueError, ijson.JSONError) as exc:
            raise StoreError("invalid embedded legacy evidence") from exc
    names = (f"legacy-{kind}-observations.jsonl", f"{kind}-observations.jsonl")
    for name in names if partitioned else names[1:]:
        path = root / name
        if not path.exists():
            continue
        try:
            with path.open("rb") as source:
                for raw in source:
                    if not raw.endswith(b"\n"):
                        raise ValueError("partial final line")
                    yield model.model_validate_json(raw)
        except ValueError as exc:
            raise StoreError(f"invalid {name}; restore a valid backup") from exc


def _db(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA cache_size=-2048")
    connection.execute("CREATE TABLE seen(kind TEXT,id TEXT,body TEXT,PRIMARY KEY(kind,id))")
    return connection


def _new(
    connection: sqlite3.Connection, kind: str, observation: QuotaObservation | UsageObservation
) -> bool:
    body = observation.model_dump_json()
    identity = observation.id if isinstance(observation, UsageObservation) else body
    previous = connection.execute(
        "SELECT body FROM seen WHERE kind=? AND id=?", (kind, identity)
    ).fetchone()
    if previous is not None:
        if previous[0] != body:
            raise StoreError("conflicting usage identity; preserve both stores and inspect")
        return False
    connection.execute("INSERT INTO seen VALUES (?,?,?)", (kind, identity, body))
    return True


def verify_portable(root: Path) -> dict[str, object]:
    """Validate content-free history without retaining history models or keys."""
    result: dict[str, object] = {"verified": True, "sessions": 0, "turns": 0}
    with tempfile.TemporaryDirectory(prefix="codex-time-verify-") as temporary:
        connection = _db(Path(temporary) / "identities.sqlite")
        try:
            count = turns = 0
            for session in sessions(root):
                if connection.execute(
                    "SELECT 1 FROM seen WHERE kind='session' AND id=?", (session.id,)
                ).fetchone():
                    raise StoreError("duplicate session identity")
                connection.execute("INSERT INTO seen VALUES ('session',?,'')", (session.id,))
                count += 1
                turns += len(session.turns)
            result.update(sessions=count, turns=turns)
            for kind in ("quota", "usage"):
                lines = unique = 0
                for observation in evidence(root, kind):
                    lines += 1
                    unique += _new(connection, kind, observation)
                result[kind + "_lines"] = lines
                result[kind + "_unique"] = unique
        finally:
            connection.close()
    return result


def check_projections(root: Path) -> None:
    """Export copies these trees, so refuse non-tracker files before it starts."""
    for name in ("projects", "records"):
        directory = root / name
        if directory.is_symlink():
            raise StoreError("projection directory is a symlink; export refused")
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise StoreError("projection contains a symlink; export refused")
            if path.is_dir():
                continue
            if not path.is_file():
                raise StoreError("projection contains a non-regular file; export refused")
            try:
                value = json.loads(path.read_bytes()) if path.suffix == ".json" else None
            except ValueError as exc:
                raise StoreError("invalid projection; export refused") from exc
            if name == "projects":
                valid = (
                    path.parent == directory
                    and isinstance(value, dict)
                    and set(value) == {"key", "name"}
                    and isinstance(value["name"], str)
                    and isinstance(value["key"], str)
                    and path.name == value["key"] + ".json"
                )
            else:
                valid = (
                    path.parent.parent == directory
                    and path.name.startswith("codex-time-")
                    and isinstance(value, dict)
                    and set(value) == {"start", "end", "project", "is_billable", "tags"}
                    and isinstance(value["start"], str)
                    and isinstance(value["end"], str)
                    and isinstance(value["project"], dict)
                    and set(value["project"]) == {"key"}
                    and value["is_billable"] is False
                    and isinstance(value["tags"], list)
                    and all(
                        isinstance(tag, str) and tag.startswith(("session:", "turn:"))
                        for tag in value["tags"]
                    )
                )
            if not valid:
                raise StoreError(
                    "projection contains unrelated/non-tracker files; export refused"
                )


def export_legacy(store: Store, destination: Path) -> dict[str, object]:
    """Export current evidence to a verified v4 store readable by the prior build.

    The source writer must be stopped. Destination is published atomically only
    after validation. Current source files and migration backups are preserved.
    """
    destination = destination.expanduser().resolve()
    if (
        destination == store.root
        or destination.is_relative_to(store.root)
        or store.root.is_relative_to(destination)
    ):
        raise StoreError("export destination must be outside the source data directory")
    if destination.exists() and any(destination.iterdir()):
        raise StoreError("export destination must be new or empty")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".codex-time-export-", dir=destination.parent))
    try:
        with (
            store.writer(),
            tempfile.TemporaryDirectory(prefix="codex-time-export-index-") as temporary,
        ):
            check_projections(store.root)
            connection = _db(Path(temporary) / "identities.sqlite")
            try:
                meta = layout(store.root)
                diagnostics: object
                if meta is None and (store.root / "ledger.json").exists():
                    with (store.root / "ledger.json").open("rb") as source:
                        diagnostics = list(ijson.items(source, "diagnostics.item"))[-200:]
                else:
                    diagnostics = meta.get("diagnostics", []) if meta else []
                with (stage / "ledger.json").open("w") as output:
                    output.write(
                        '{"version":4,"diagnostics":' + json.dumps(diagnostics) + ',"sessions":{'
                    )
                    first = True
                    for session in sessions(store.root):
                        output.write(
                            ("" if first else ",")
                            + json.dumps(session.id)
                            + ":"
                            + session.model_dump_json()
                        )
                        first = False
                    output.write("}}\n")
                    output.flush()
                    os.fsync(output.fileno())
                for kind in ("quota", "usage"):
                    with (stage / f"{kind}-observations.jsonl").open("w") as output:
                        for observation in evidence(store.root, kind):
                            if _new(connection, kind, observation):
                                output.write(observation.model_dump_json() + "\n")
                        output.flush()
                        os.fsync(output.fileno())
                for name in ("projects", "records"):
                    if (store.root / name).exists():
                        shutil.copytree(store.root / name, stage / name)
                result = verify_portable(stage)
                source_result = verify_portable(store.root)
                if any(
                    result[name] != source_result[name]
                    for name in ("sessions", "turns", "quota_unique", "usage_unique")
                ):
                    raise StoreError("export counters differ; export not published")
                manifest = {
                    "version": 1,
                    "source_counts": source_result,
                    "export_counts": result,
                    "sha256": {
                        name: sha256(stage / name)
                        for name in (
                            "ledger.json",
                            "quota-observations.jsonl",
                            "usage-observations.jsonl",
                        )
                    },
                }
                store._write(stage / "conversion-manifest.json", manifest)
                os.replace(stage, destination)
                descriptor = os.open(destination.parent, os.O_DIRECTORY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                return {**result, "destination": str(destination)}
            finally:
                connection.close()
    finally:
        if stage.exists():
            shutil.rmtree(stage)
