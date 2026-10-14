"""Small responsive token/currency summaries shared by both terminal reports."""

from collections.abc import Callable
from decimal import Decimal

from codex_time.token_reporting import UsageSummary


def compact_tokens(value: int | None) -> str:
    if value is None:
        return "unavailable"
    for size, suffix in [(1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k")]:
        if value >= size:
            return f"{Decimal(value) / size:.2f}".rstrip("0").rstrip(".") + suffix
    return str(value)


def money(value: str | None, currency: str) -> str:
    if value is None:
        return f"{currency} unavailable"
    amount = Decimal(value)
    if 0 < amount < Decimal("0.01"):
        return f"{currency} <0.01"
    return f"{currency} {amount:,.2f}"


def usage_line(usage: UsageSummary) -> str:
    tokens = compact_tokens(usage["tokens"]["total_tokens"])
    if usage["status"] == "excluded":
        return "Token usage excluded | USD excluded | CAD excluded"
    if usage["status"] == "unavailable":
        return "Tokens unavailable | USD unavailable | CAD unavailable"
    if not usage["priced_tokens"] and usage["unpriced_tokens"]:
        return f"{tokens} tokens | USD unpriced / CAD " + (
            "unpriced" if usage["cad"] is not None else "unavailable"
        )
    suffix = " (subtotal)" if not usage["cost_complete"] else ""
    return f"{tokens} tokens | {money(usage['usd'], 'USD')} / {money(usage['cad'], 'CAD')}{suffix}"


def usage_details(say: Callable[[str, str], None], usage: UsageSummary) -> None:
    for category, amount in usage["tokens"].items():
        say(
            f"{category.replace('_', ' ')}: {amount if amount is not None else 'unavailable'}",
            "dim",
        )
    say(f"Exact USD: {usage['usd']}; CAD: {usage['cad'] or 'unavailable'}", "dim")
    say(f"Priced tokens: {usage['priced_tokens']}; unpriced: {usage['unpriced_tokens']}", "dim")
    say(
        f"Uncertain observations: {usage['uncertain_observations']}; "
        f"sessions without usage: {usage['unavailable_session_count']}",
        "dim",
    )
    if usage["unavailable_sessions"]:
        say("Sessions without usage: " + ", ".join(usage["unavailable_sessions"]), "dim")
    for diagnostic in usage["diagnostics"]:
        say("Usage: " + diagnostic, "dim")


def usage_warning(say: Callable[[str, str], None], usage: UsageSummary) -> None:
    if usage["status"] == "unavailable":
        say(
            "Token usage unavailable. Run import-history after upgrading, then check --details.",
            "yellow",
        )
    elif usage["status"] != "excluded" and not usage["cost_complete"]:
        say(
            "Known priced subtotal; "
            + compact_tokens(usage["unpriced_tokens"])
            + " tokens unpriced. Some evidence may be unavailable; use --details.",
            "yellow",
        )


def provenance(
    say: Callable[[str, str], None],
    pricing: dict[str, object],
    fx: dict[str, object],
    *,
    details: bool = False,
) -> None:
    rate = fx.get("rate")
    observed = fx.get("observation_date")
    if rate is None:
        say("CAD unavailable: no valid cached Bank of Canada rate.", "dim")
    else:
        say(f"USD to CAD: {rate} | Bank of Canada {observed}", "dim")
        age = fx.get("age_days")
        if age is not None:
            say(f"FX observation age: {age} days.", "dim")
        if fx.get("last_error"):
            say("FX refresh failed; using the last valid cached rate.", "yellow")
    say(
        "Present-rate comparison; excludes tool fees, hosting, taxes and other non-token charges.",
        "dim",
    )
    if details:
        verified = pricing.get("verified_at", pricing.get("verified_on", "see model entries"))
        say(
            f"Price catalog: {pricing.get('version', 'unknown')}; verified {verified}",
            "dim",
        )
        # Full structured provenance is also exported; terminal details retain
        # exact source URLs and rates without relying on guessed model aliases.
        for key, value in pricing.items():
            say(f"Pricing {key}: {value}", "dim")
        for key, value in fx.items():
            say(f"FX {key}: {value}", "dim")
