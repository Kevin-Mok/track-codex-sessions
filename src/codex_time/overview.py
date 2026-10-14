"""Compose allowance and complete model work from one selected ledger snapshot."""

from datetime import UTC, date, datetime
from typing import TypedDict
from zoneinfo import ZoneInfo

from codex_time.burn import BurnReport, burn_report
from codex_time.fx import FXSnapshot
from codex_time.model_usage import ModelUsageReport, model_report
from codex_time.models import Ledger
from codex_time.periods import report_dates
from codex_time.pricing import PricingCatalog
from codex_time.token_reporting import TokenReport, token_report


class OverviewReport(TypedDict):
    allowance: BurnReport
    model_totals: ModelUsageReport
    reasoning: ModelUsageReport
    token_usage: TokenReport


def overview_report(
    ledger: Ledger,
    *,
    period: str = "day",
    fx: FXSnapshot | None = None,
    catalog: PricingCatalog | None = None,
    selected_date: date | None = None,
    timezone_name: str = "America/Toronto",
    window_minutes: int = 10080,
    limit_id: str = "codex",
    max_gap_seconds: int = 600,
) -> OverviewReport:
    """Resolve today once; retain each existing report's accounting and export schema."""
    if period == "all" and selected_date is not None:
        raise ValueError("--date cannot be combined with all")
    selected = (
        (selected_date or datetime.now(UTC).astimezone(ZoneInfo(timezone_name)).date())
        if period != "all"
        else None
    )
    first, last = report_dates(ledger, period, selected, timezone_name)
    quota_date = max(
        (
            q.at.astimezone(ZoneInfo(timezone_name)).date()
            for q in ledger.quota_observations
            if q.limit_id == limit_id and q.window_minutes == window_minutes
        ),
        default=last,
    )
    allowance = burn_report(
        ledger,
        period="day" if period == "all" else period,
        selected_date=quota_date if period == "all" else selected,
        timezone_name=timezone_name,
        window_minutes=window_minutes,
        limit_id=limit_id,
        max_gap_seconds=max_gap_seconds,
    )
    if period == "all":
        allowance["label"] = "Latest allowance snapshot"
        allowance["period"] = "all"
        allowance["rows"] = []
        allowance["from"], allowance["to"] = first.isoformat(), last.isoformat()
    return {
        "allowance": allowance,
        "token_usage": token_report(
            ledger,
            period=period,
            selected_date=selected,
            timezone_name=timezone_name,
            fx=fx,
            catalog=catalog,
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
