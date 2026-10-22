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
    tokens = usage["tokens"]
    say(
        f"Input: {compact_tokens(tokens.get('input_tokens'))} | "
        f"Cached: {compact_tokens(tokens.get('cached_input_tokens'))} | "
        f"Output: {compact_tokens(tokens.get('output_tokens'))}",
        "dim",
    )
    subsets = []
    for key, label in [
        ("reasoning_output_tokens", "Reasoning (within output)"),
        ("cache_write_input_tokens", "Cache writes (within input)"),
    ]:
        if tokens.get(key):
            subsets.append(f"{label}: {compact_tokens(tokens[key])}")
    if subsets:
        say(" | ".join(subsets), "dim")
    gaps = []
    if usage["unpriced_tokens"]:
        gaps.append(f"{compact_tokens(usage['unpriced_tokens'])} unpriced tokens")
    if usage["uncertain_observations"]:
        gaps.append(f"{usage['uncertain_observations']} uncertain readings")
    if usage["unavailable_session_count"]:
        gaps.append(f"{usage['unavailable_session_count']} sessions without usage")
    if gaps:
        say("Coverage: " + "; ".join(gaps) + ".", "yellow")


def usage_warning(say: Callable[[str, str], None], usage: UsageSummary) -> None:
    if usage["status"] == "unavailable":
        say(
            "Token usage unavailable. Check codex-time health or run import-history.",
            "yellow",
        )
    elif usage["status"] != "excluded" and not usage["cost_complete"]:
        reasons = []
        if usage["unpriced_tokens"]:
            reasons.append(compact_tokens(usage["unpriced_tokens"]) + " tokens unpriced")
        if usage["unavailable_session_count"]:
            count = usage["unavailable_session_count"]
            reasons.append(f"{count} {'session' if count == 1 else 'sessions'} without usage")
        if usage["uncertain_observations"]:
            reasons.append(f"{usage['uncertain_observations']} uncertain readings")
        say(
            "* Known priced subtotal; " + "; ".join(reasons or ["missing billing evidence"]) + ".",
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
        age = fx.get("age_days")
        age_label = f"; {age} {'day' if age == 1 else 'days'} old" if age is not None else ""
        say(f"FX: 1 USD = {rate} CAD | Bank of Canada {observed}{age_label}", "dim")
        if fx.get("last_error"):
            say("FX refresh failed; using the last valid cached rate.", "yellow")
    say(
        "Present-rate API estimate; excludes non-token charges, hosting and taxes.",
        "dim",
    )
    if details:
        verified = pricing.get("verified_at", pricing.get("verified_on", "see model entries"))
        say(
            f"Price catalog: {pricing.get('version', 'unknown')}; verified {verified}",
            "dim",
        )
