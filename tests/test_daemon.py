from pathlib import Path

import pytest

from codex_time.daemon import runtime_status
from codex_time.storage import Store


@pytest.mark.parametrize(
    "heartbeat", ["2026-10-06T16:00:00", "wrong", "2099-01-01T00:00:00+00:00", None, 42]
)
def test_corrupt_or_stale_heartbeat_is_not_running(tmp_path: Path, heartbeat: object) -> None:
    store = Store(tmp_path / "data", tmp_path / "state")
    with store.writer():
        store.runtime_save({"heartbeat": heartbeat})
    assert runtime_status(store)["daemon"] == "stopped_or_stale"
