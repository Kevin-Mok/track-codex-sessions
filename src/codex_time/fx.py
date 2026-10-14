"""Bank of Canada USD→CAD observations in runtime state, never the data ledger.

Reports call read_fx only. The daemon owns one refresh task under its existing
writer lock. Only bounded network I/O runs in a thread; all atomic writes stay
on that owner task so cancellation cannot cause a later background write.
"""

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Final, Literal
from urllib.error import URLError
from urllib.request import urlopen

from pydantic import Field, ValidationError, field_validator, model_validator

from codex_time.models import Model
from codex_time.storage import atomic_json

SOURCE_URL: Final = "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1"
CACHE_NAME = "fx-usd-cad.json"
REQUEST_TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 64 * 1024


class FXSnapshot(Model):
    version: Literal[1] = 1
    rate: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    observation_date: date | None = None
    last_attempt: datetime | None = None
    last_success: datetime | None = None
    last_error: str | None = None
    source_url: Literal["https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1"] = (
        SOURCE_URL
    )
    base: Literal["USD"] = "USD"
    quote: Literal["CAD"] = "CAD"

    @field_validator("last_attempt", "last_success")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("FX cache timestamps require an explicit timezone")
            return value.astimezone(UTC)
        return value

    @model_validator(mode="after")
    def rate_and_date(self) -> "FXSnapshot":
        if (self.rate is None) != (self.observation_date is None):
            raise ValueError("FX rate and observation date must be present together")
        return self

    def convert(self, usd: Decimal) -> Decimal | None:
        if self.rate is None:
            return None
        with localcontext() as ctx:
            ctx.prec = max(28, len(usd.as_tuple().digits) + len(self.rate.as_tuple().digits))
            return usd * self.rate

    def metadata(self, now: datetime | None = None) -> dict[str, object]:
        now = _now(now)
        age = max(0, (now.date() - self.observation_date).days) if self.observation_date else None
        check_age = max(0, (now - self.last_success).total_seconds()) if self.last_success else None
        stale = self.last_error is not None or check_age is None or check_age > 86400
        return {
            **self.model_dump(mode="json"),
            "age_days": age,
            "check_age_seconds": check_age,
            "status": "unavailable" if self.rate is None else "stale" if stale else "cached",
        }


def _now(value: datetime | None) -> datetime:
    value = value or datetime.now(UTC)
    if value.tzinfo is None:
        raise ValueError("FX refresh time requires an explicit timezone")
    return value.astimezone(UTC)


def read_fx(runtime: Path) -> FXSnapshot:
    """Read without creating directories, fixing files or making network calls."""
    try:
        return FXSnapshot.model_validate_json((runtime / CACHE_NAME).read_text())
    except FileNotFoundError:
        return FXSnapshot()
    except (OSError, ValueError, ValidationError):
        return FXSnapshot(last_error="Invalid FX cache; background service will refresh it")


def refresh_due(snapshot: FXSnapshot, now: datetime | None = None) -> bool:
    now = _now(now)
    if snapshot.last_attempt is not None and now - snapshot.last_attempt < timedelta(hours=1):
        return False
    if snapshot.last_success is not None and now - snapshot.last_success < timedelta(hours=24):
        return False
    return True


def _fetch_latest(timeout: float) -> tuple[Decimal, date]:
    with urlopen(SOURCE_URL, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("Bank of Canada response exceeded size limit")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("observations"), list):
        raise ValueError("Bank of Canada response has no observations")
    observations: list[tuple[Decimal, date]] = []
    for row in payload["observations"]:
        if not isinstance(row, dict) or not isinstance(row.get("FXUSDCAD"), dict):
            continue
        value, stamp = row["FXUSDCAD"].get("v"), row.get("d")
        if not isinstance(value, str) or not isinstance(stamp, str):
            continue
        valid = FXSnapshot(rate=value, observation_date=stamp)
        assert valid.rate is not None and valid.observation_date is not None
        observations.append((valid.rate, valid.observation_date))
    if not observations:
        raise ValueError("Bank of Canada response has no valid USD/CAD observation")
    return max(observations, key=lambda pair: pair[1])


def _save(runtime: Path, snapshot: FXSnapshot) -> None:
    atomic_json(runtime / CACHE_NAME, snapshot.model_dump(mode="json"), runtime / ".staging")


async def refresh_fx(runtime: Path, now: datetime | None = None) -> FXSnapshot:
    """Refresh at most hourly after failure, daily after success, without blocking tracking.

    Caller must own the data-store writer lock and avoid concurrent refresh tasks.
    Persist the attempt before awaiting the worker, preserving retry throttling
    through cancellation and service restarts. A worker never touches the cache.
    """
    now = _now(now)
    prior = read_fx(runtime)
    if not refresh_due(prior, now):
        return prior
    pending = FXSnapshot.model_validate({**prior.model_dump(), "last_attempt": now})
    _save(runtime, pending)
    try:
        rate, stamp = await asyncio.wait_for(
            asyncio.to_thread(_fetch_latest, REQUEST_TIMEOUT_SECONDS),
            timeout=REQUEST_TIMEOUT_SECONDS + 1,
        )
        if stamp > now.date():
            raise ValueError("Bank of Canada observation is in the future")
        if prior.observation_date is not None and stamp < prior.observation_date:
            raise ValueError("Bank of Canada observation is older than the cached rate")
        updated = FXSnapshot(rate=rate, observation_date=stamp, last_attempt=now, last_success=now)
    except (OSError, URLError, ValueError, ValidationError) as exc:
        updated = FXSnapshot.model_validate(
            {
                **pending.model_dump(),
                "last_error": f"FX refresh failed: {str(exc) or type(exc).__name__}",
            }
        )
    _save(runtime, updated)
    return updated
