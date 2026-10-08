"""Compose allowance and complete model work from one selected ledger snapshot."""

from datetime import UTC, date, datetime
from typing import TypedDict
from zoneinfo import ZoneInfo

from codex_time.burn import BurnReport, burn_report
from codex_time.model_usage import ModelUsageReport, model_report
from codex_time.models import Ledger


class OverviewReport(TypedDict):
    allowance: BurnReport
    model_totals: ModelUsageReport
    reasoning: ModelUsageReport


def overview_report(
    ledger: Ledger,
    *,
    period: str = "day",
    selected_date: date | None = None,
    timezone_name: str = "America/Toronto",
    window_minutes: int = 10080,
    limit_id: str = "codex",
    max_gap_seconds: int = 600,
) -> OverviewReport:
    """Resolve today once; retain each existing report's accounting and export schema."""
    selected = selected_date or datetime.now(UTC).astimezone(ZoneInfo(timezone_name)).date()
    return {
        "allowance": burn_report(
            ledger,
            period=period,
            selected_date=selected,
            timezone_name=timezone_name,
            window_minutes=window_minutes,
            limit_id=limit_id,
            max_gap_seconds=max_gap_seconds,
        ),
        "model_totals": model_report(
            ledger,
            period=period,
            selected_date=selected,
            timezone_name=timezone_name,
            model_only=True,
        ),
        "reasoning": model_report(
            ledger,
            period=period,
            selected_date=selected,
            timezone_name=timezone_name,
        ),
    }
