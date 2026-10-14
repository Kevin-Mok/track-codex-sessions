from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from codex_time.incremental_storage import IndexedStore
from codex_time.models import Ledger, QuotaObservation, Session, Turn, UsageObservation
from codex_time.recovery import export_legacy, verify_portable
from codex_time.storage import Store, StoreError


def test_streaming_export_preserves_postmigration_timing_and_embedded_evidence(
    tmp_path: Path,
) -> None:
    at = datetime(2026, 10, 14, tzinfo=UTC)
    root, state = tmp_path / "data", tmp_path / "state"
    root.mkdir()
    ledger = Ledger(
        sessions={
            "one": Session(
                id="one",
                cwd="/fixture",
                created=at,
                updated=at,
                turns={"t": Turn(id="t", cwd="/fixture", start=at, end=at + timedelta(seconds=3))},
            )
        },
        usage_observations=[UsageObservation(id="old", session_id="one", at=at)],
    )
    (root / "ledger.json").write_text(ledger.model_dump_json())
    with IndexedStore(root, state) as index:
        index.ledger.sessions["one"].turns["t"].end = at + timedelta(seconds=7)
        index.append_usage(
            UsageObservation(id="new", session_id="one", at=at + timedelta(seconds=7))
        )
        index.append_quota(
            QuotaObservation(
                at=at,
                limit_id="codex",
                bucket="primary",
                window_minutes=300,
                resets_at=2000000000,
                used_percent=7.0,
            )
        )
    expected = Store(root, state).load()
    result = export_legacy(Store(root, state), tmp_path / "export")
    assert result["verified"] is True
    assert Store(tmp_path / "export", tmp_path / "export-state").load() == expected
    assert verify_portable(root)["sessions"] == 1
    assert verify_portable(tmp_path / "export")["usage_unique"] == 2
    assert not (tmp_path / "export" / "layout.json").exists()


@pytest.mark.parametrize("kind", ["text", "json", "symlink"])
def test_direct_export_refuses_foreign_projection_files(tmp_path: Path, kind: str) -> None:
    root = tmp_path / "data"
    directory = root / "projects"
    directory.mkdir(parents=True)
    outside = tmp_path / "unrelated.txt"
    outside.write_text("unrelated fixture data")
    if kind == "symlink":
        (directory / "outside.json").symlink_to(outside)
    elif kind == "json":
        (directory / "unrelated.json").write_text('{"unrelated":"fixture"}')
    else:
        (directory / "unrelated.txt").write_text("unrelated fixture data")
    destination = tmp_path / "export"
    with pytest.raises(StoreError, match="projection"):
        export_legacy(Store(root, tmp_path / "state"), destination)
    assert not destination.exists()
    assert outside.read_text() == "unrelated fixture data"
