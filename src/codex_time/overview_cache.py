"""Disposable, validated overview reports keyed by source identities and calendar options."""

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import ConfigDict

from codex_time.fx import CACHE_NAME as FX_CACHE_NAME
from codex_time.fx import read_fx
from codex_time.models import Model
from codex_time.overview import OverviewReport, overview_report
from codex_time.overview_read import load_overview
from codex_time.storage import Store

CACHE_NAME = "overview-report.json"


class ReportCache(Model):
    model_config = ConfigDict(allow_inf_nan=False)

    version: Literal[1]
    identity: str
    report: OverviewReport


def source_identity(store: Store) -> str:
    """Stat every authoritative file, including restored individual session snapshots."""
    package = Path(__file__).parent
    paths = [
        store.root / name
        for name in (
            "layout.json", "ledger.json", "quota-observations.jsonl",
            "usage-observations.jsonl", "legacy-quota-observations.jsonl",
            "legacy-usage-observations.jsonl",
        )
    ]
    paths.extend(sorted((store.root / "sessions").glob("*.json")))
    paths.extend((store.runtime / FX_CACHE_NAME, package / "pricing-v1.json"))
    paths.extend(sorted(package.glob("*.py")))
    identities: list[tuple[str, tuple[int, ...] | None]] = []
    for path in paths:
        try:
            stamp = Store._stat_key(path)
        except FileNotFoundError:
            stamp = None
        identities.append((str(path), stamp))
    return hashlib.sha256(json.dumps([str(store.root), identities]).encode()).hexdigest()


def cached_overview(
    store: Store,
    *,
    period: str = "day",
    selected_date: date | None = None,
    timezone_name: str = "America/Toronto",
    window_minutes: int = 10080,
    limit_id: str = "codex",
    max_gap_seconds: int = 600,
) -> OverviewReport:
    """Reuse complete accounting; cache failures never prevent a fresh read-only report."""
    if period == "all" and selected_date is not None:
        raise ValueError("--date cannot be combined with all")
    today = datetime.now(UTC).astimezone(ZoneInfo(timezone_name)).date()
    selected = selected_date or today
    options = (period, selected.isoformat(), timezone_name, window_minutes, limit_id,
               max_gap_seconds)
    try:
        before = source_identity(store)
    except OSError:
        before = None
    identity = hashlib.sha256(json.dumps([before, options]).encode()).hexdigest()
    cache_path = store.runtime / CACHE_NAME
    if before is not None:
        try:
            cached = ReportCache.model_validate_json(cache_path.read_bytes(), strict=True)
            fx = read_fx(store.runtime)
            if cached.identity == identity and source_identity(store) == before:
                cached.report["token_usage"]["fx"] = fx.metadata()
                return cached.report
        except (OSError, ValueError):
            pass
    result = overview_report(
        load_overview(
            store,
            period=period,
            selected_date=None if period == "all" else selected,
            timezone_name=timezone_name,
            window_minutes=window_minutes,
            limit_id=limit_id,
        ),
        fx=read_fx(store.runtime),
        period=period,
        selected_date=None if period == "all" else selected,
        timezone_name=timezone_name,
        window_minutes=window_minutes,
        limit_id=limit_id,
        max_gap_seconds=max_gap_seconds,
    )
    if before is not None:
        try:
            if source_identity(store) == before:
                cache = ReportCache(version=1, identity=identity, report=result)
                store.runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
                store._write(cache_path, cache.model_dump(mode="json"))
        except (OSError, ValueError):
            pass
    return result
