"""Read-only token projections; price each observation once before grouping."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import TypedDict
from zoneinfo import ZoneInfo

from codex_time.accounting import daily_microseconds, segments
from codex_time.fx import FXSnapshot
from codex_time.models import Ledger, UsageObservation
from codex_time.periods import report_dates
from codex_time.pricing import PricedUsage, PricingCatalog, load_catalog, price_usage
from codex_time.work_period import has_work_in_period

EXCLUDED_MODELS = frozenset({"codex-auto-review"})

CATEGORIES = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


class UsageSummary(TypedDict):
    status: str
    tokens: dict[str, int | None]
    observations: int
    uncertain_observations: int
    unavailable_session_count: int
    unavailable_sessions: list[str]
    priced_tokens: int
    unpriced_tokens: int
    cost_complete: bool
    usd: str
    cad: str | None
    diagnostics: list[str]


class TokenModelRow(TypedDict):
    model_id: str | None
    usage: UsageSummary


class ChildContribution(TypedDict):
    session_id: str
    model_id: str | None
    usage: UsageSummary


class TokenSessionRow(TypedDict):
    id: str
    usage: UsageSummary
    models: list[TokenModelRow]
    children: list[ChildContribution]


class TokenDirectoryRow(TypedDict):
    cwd: str
    usage: UsageSummary
    models: list[TokenModelRow]
    sessions: list[TokenSessionRow]


TokenReport = TypedDict(
    "TokenReport",
    {
        "label": str,
        "period": str,
        "from": str,
        "to": str,
        "timezone": str,
        "usage": UsageSummary,
        "models": list[TokenModelRow],
        "excluded_models": list[str],
        "directories": list[TokenDirectoryRow],
        "pricing": dict[str, object],
        "fx": dict[str, object],
    },
)


@dataclass
class Evidence:
    observation: UsageObservation
    price: PricedUsage
    diagnostics: list[str]


@dataclass
class Bucket:
    evidence: list[Evidence] = field(default_factory=list)
    unavailable: set[str] = field(default_factory=set)
    excluded: bool = False

    def summary(self, fx: FXSnapshot) -> UsageSummary:
        totals: dict[str, int | None] = dict.fromkeys(CATEGORIES)
        uncertain = 0
        reasons: set[str] = set()
        for item in self.evidence:
            delta = item.observation.delta
            if delta is None or delta.total_tokens is None:
                uncertain += 1
            if delta is not None:
                for name in CATEGORIES:
                    value = getattr(delta, name)
                    if value is not None:
                        totals[name] = (totals[name] or 0) + value
            reasons.update(item.price.reasons)
            reasons.update(item.observation.diagnostics)
            reasons.update(item.diagnostics)
        if self.unavailable:
            reasons.add("usage_unavailable_for_recorded_work")
        amounts = [item.price.usd for item in self.evidence]
        with localcontext() as context:
            if amounts:
                context.prec = max(
                    28,
                    max(value.adjusted() for value in amounts)
                    - min(int(value.as_tuple().exponent) for value in amounts)
                    + len(str(len(amounts)))
                    + 2,
                )
            usd = sum(amounts, Decimal(0))
        cad = fx.convert(usd)
        return {
            "status": ("excluded" if self.excluded and not self.unavailable else "unavailable")
            if not self.evidence
            else ("partial" if uncertain or self.unavailable else "recorded"),
            "tokens": totals,
            "observations": len(self.evidence),
            "uncertain_observations": uncertain,
            "unavailable_session_count": len(self.unavailable),
            "unavailable_sessions": sorted(self.unavailable),
            "priced_tokens": sum(item.price.priced_tokens for item in self.evidence),
            "unpriced_tokens": sum(item.price.unpriced_tokens for item in self.evidence),
            "cost_complete": bool(self.evidence)
            and not self.unavailable
            and not uncertain
            and all(item.price.complete for item in self.evidence),
            "usd": str(usd),
            "cad": str(cad) if cad is not None else None,
            "diagnostics": sorted(reasons),
        }


def root_session(ledger: Ledger, session_id: str) -> tuple[str, list[str]]:
    """Keep broken/cyclic ancestry visible under a deterministic surviving root."""
    current = session_id
    visited: list[str] = []
    while True:
        if current in visited:
            return min(visited), ["cyclic_child_ancestry"]
        visited.append(current)
        session = ledger.sessions.get(current)
        if session is None:
            return session_id, ["orphaned_child"]
        if session.parent_id is None:
            return current, ["orphaned_child"] if session.is_child else []
        if session.parent_id not in ledger.sessions:
            return current, ["orphaned_child"]
        current = session.parent_id


def _models(items: list[Evidence], fx: FXSnapshot) -> list[TokenModelRow]:
    models: dict[str | None, Bucket] = {}
    for item in items:
        models.setdefault(item.observation.model_id, Bucket()).evidence.append(item)
    return [
        {"model_id": model, "usage": bucket.summary(fx)}
        for model, bucket in sorted(
            models.items(), key=lambda pair: (pair[0] is None, pair[0] or "")
        )
    ]


def token_report(
    ledger: Ledger,
    *,
    period: str = "day",
    selected_date: date | None = None,
    timezone_name: str = "America/Toronto",
    cwd: str | None = None,
    archive: str = "all",
    session_id: str | None = None,
    fx: FXSnapshot | None = None,
    catalog: PricingCatalog | None = None,
    now: datetime | None = None,
) -> TokenReport:
    first, last = report_dates(ledger, period, selected_date, timezone_name)
    zone = ZoneInfo(timezone_name)
    start = datetime.combine(first, datetime.min.time(), zone).astimezone(UTC)
    end = datetime.combine(last + timedelta(days=1), datetime.min.time(), zone).astimezone(UTC)
    fx = fx or FXSnapshot()
    catalog = catalog or load_catalog()
    total = Bucket()
    directories: dict[str, dict[str, Bucket]] = {}
    directory_filter = Path(cwd).resolve() if cwd is not None else None
    roots: dict[str, tuple[str, list[str]]] = {}

    def root(sid: str) -> tuple[str, list[str]]:
        if sid not in roots:
            roots[sid] = root_session(ledger, sid)
        return roots[sid]

    def included(sid: str, original_cwd: str | None) -> bool:
        rid, _ = root(sid)
        owner = ledger.sessions.get(rid) or ledger.sessions.get(sid)
        if archive != "all" and (owner is None or owner.archived != (archive == "archived")):
            return False
        if session_id is not None and session_id not in (sid, rid):
            return False
        return directory_filter is None or (
            original_cwd is not None and Path(original_cwd).resolve() == directory_filter
        )

    observed_pairs: set[tuple[str, str | None]] = set()
    excluded_pairs: set[tuple[str, str | None]] = set()
    seen: set[str] = set()
    for observation in ledger.usage_observations:
        if observation.id in seen:
            continue
        seen.add(observation.id)
        if not first <= observation.at.astimezone(zone).date() <= last:
            continue
        if not included(observation.session_id, observation.cwd):
            continue
        pair = (observation.session_id, observation.cwd)
        observed_pairs.add(pair)
        if observation.model_id in EXCLUDED_MODELS:
            excluded_pairs.add(pair)
            total.excluded = True
            continue
        rid, diagnostics = root(observation.session_id)
        item = Evidence(observation, price_usage(observation, catalog), diagnostics)
        total.evidence.append(item)
        bucket = directories.setdefault(observation.cwd or "", {}).setdefault(rid, Bucket())
        bucket.evidence.append(item)

    # Retain elapsed-work rows whose rollout has no token evidence. Such rows make
    # report coverage incomplete, even if another session has completely priced usage.
    for session in ledger.sessions.values():
        if not has_work_in_period(session, start, end):
            continue
        for span in segments(list(session.turns.values())):
            if not included(session.id, span.cwd):
                continue
            if not any(
                first.isoformat() <= day <= last.isoformat() and value > 0
                for day, value in daily_microseconds([span], timezone_name).items()
            ):
                continue
            rid, _ = root(session.id)
            if (session.id, span.cwd) in excluded_pairs:
                if not (session.is_child or session.parent_id) or rid in directories.get(
                    span.cwd, {}
                ):
                    bucket = directories.setdefault(span.cwd, {}).setdefault(rid, Bucket())
                    bucket.excluded = True
            if (session.id, span.cwd) not in observed_pairs:
                total.unavailable.add(session.id)
                if (session.is_child or session.parent_id) and rid not in directories.get(
                    span.cwd, {}
                ):
                    # Missing evidence alone must not create a new child working-
                    # time row. Its identity remains in aggregate diagnostics.
                    continue
                bucket = directories.setdefault(span.cwd, {}).setdefault(rid, Bucket())
                bucket.unavailable.add(session.id)

    rows: list[TokenDirectoryRow] = []
    for directory, sessions in sorted(directories.items()):
        combined = Bucket()
        session_rows: list[TokenSessionRow] = []
        for sid, bucket in sorted(sessions.items()):
            combined.evidence.extend(bucket.evidence)
            combined.unavailable.update(bucket.unavailable)
            combined.excluded = combined.excluded or bucket.excluded
            children: dict[tuple[str, str | None], Bucket] = {}
            for item in bucket.evidence:
                observation = item.observation
                if observation.session_id != sid:
                    children.setdefault(
                        (observation.session_id, observation.model_id), Bucket()
                    ).evidence.append(item)
            for missing in bucket.unavailable - {sid}:
                children.setdefault((missing, None), Bucket()).unavailable.add(missing)
            session_rows.append(
                {
                    "id": sid,
                    "usage": bucket.summary(fx),
                    "models": _models(bucket.evidence, fx),
                    "children": [
                        {"session_id": child, "model_id": model, "usage": value.summary(fx)}
                        for (child, model), value in sorted(
                            children.items(), key=lambda p: (p[0][0], p[0][1] or "")
                        )
                    ],
                }
            )
        rows.append(
            {
                "cwd": directory,
                "usage": combined.summary(fx),
                "models": _models(combined.evidence, fx),
                "sessions": session_rows,
            }
        )
    return {
        "label": "Estimated API token cost — Standard",
        "period": period,
        "from": first.isoformat(),
        "to": last.isoformat(),
        "timezone": timezone_name,
        "usage": total.summary(fx),
        "models": _models(total.evidence, fx),
        "excluded_models": sorted(EXCLUDED_MODELS),
        "directories": rows,
        "pricing": catalog.model_dump(mode="json"),
        "fx": fx.metadata(now),
    }
