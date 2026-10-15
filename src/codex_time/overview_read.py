"""Read overview evidence from a current daemon index, otherwise use authoritative journals."""

import sqlite3
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from codex_time.incremental_storage import IndexedStore
from codex_time.models import Ledger, QuotaObservation, UsageObservation
from codex_time.periods import report_dates
from codex_time.storage import Store


def load_overview(
    store: Store,
    *,
    period: str,
    selected_date: date | None,
    timezone_name: str = "America/Toronto",
    window_minutes: int = 10080,
    limit_id: str = "codex",
) -> Ledger:
    """Never open the writer API or migrate/rebuild data from a report.

    The daemon publishes the source stamp with its index transaction. Compare
    both ends of a read transaction so concurrent appends cannot pass as fresh.
    Keep all pre-period quota history: resets/conflicts require that baseline.
    """
    if period == "all" or not (store.root / "layout.json").exists():
        return store.load()
    index = IndexedStore(store.root, store.runtime)
    before = index._stamp()
    try:
        db = sqlite3.connect((store.runtime / "index.sqlite").as_uri() + "?mode=ro", uri=True)
        try:
            db.execute("BEGIN")
            saved = db.execute("SELECT value FROM meta WHERE key='sources'").fetchone()
            if saved is None or saved[0] != before:
                return store.load()
            ledger = store.load(include_evidence=False)
            first, last = report_dates(ledger, period, selected_date, timezone_name)
            zone = ZoneInfo(timezone_name)
            start = datetime.combine(first, datetime.min.time(), zone).astimezone(UTC)
            end = datetime.combine(
                last + timedelta(days=1), datetime.min.time(), zone
            ).astimezone(UTC)
            ledger.quota_observations = [
                QuotaObservation.model_validate_json(row[0])
                for row in db.execute(
                    "SELECT id FROM quotas WHERE json_extract(id,'$.limit_id')=? "
                    "AND json_extract(id,'$.window_minutes')=?",
                    (limit_id, window_minutes),
                )
            ]
            ledger.usage_observations = [
                UsageObservation.model_validate_json(row[0])
                for row in db.execute(
                    "SELECT body FROM usage WHERE at>=? AND at<? ORDER BY rowid",
                    (start.isoformat(), end.isoformat()),
                )
            ]
            if index._stamp() == before:
                return ledger
        finally:
            db.close()
    except (OSError, ValueError, sqlite3.Error):
        pass  # Missing, corrupt or incompatible acceleration is disposable.
    return store.load()
