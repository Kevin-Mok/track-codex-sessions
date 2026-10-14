"""Exact present-rate Standard token estimates from a verified local catalog.

Only observed increments are billed. Cache reads/writes are disjoint input
subsets; reasoning is already part of output. Missing evidence leaves an
explicit unpriced portion instead of selecting an assumed billing category.
"""

from datetime import date
from decimal import Decimal, localcontext
from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from codex_time.models import Model, TokenCounts, UsageObservation

LABEL = "Estimated API token cost — Standard"
EXCLUSIONS = "Excludes tool fees, hosting, taxes and other non-token charges."


class RateTier(Model):
    input: Decimal = Field(ge=0, allow_inf_nan=False)
    cached_input: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    cache_write: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    output: Decimal = Field(ge=0, allow_inf_nan=False)


class ModelPrice(Model):
    model_id: str = Field(min_length=1)
    short: RateTier
    cache_write_mode: Literal["ordinary", "separate", "unsupported"] = "unsupported"
    long_context_threshold: int | None = Field(default=None, ge=0, strict=True)
    long: RateTier | None = None
    source_urls: list[str] = Field(min_length=1)
    verified_on: date
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def coherent_tiers(self) -> "ModelPrice":
        if (self.long is None) != (self.long_context_threshold is None):
            raise ValueError("long-context rate and request threshold must be specified together")
        return self


class PricingCatalog(Model):
    schema_version: Literal[1] = 1
    version: str = Field(min_length=1)
    verified_on: date
    source_urls: list[str] = Field(min_length=1)
    service_tier: Literal["Standard"] = "Standard"
    currency: Literal["USD"] = "USD"
    notes: list[str] = Field(default_factory=list)
    models: dict[str, ModelPrice]

    @model_validator(mode="after")
    def exact_model_ids(self) -> "PricingCatalog":
        if any(key != model.model_id for key, model in self.models.items()):
            raise ValueError("catalog key must equal exact model ID")
        return self

    def metadata(self) -> dict[str, object]:
        return {
            **self.model_dump(mode="json", exclude={"models"}),
            "label": LABEL,
            "basis": "Present-rate comparison applied to all selected history",
            "exclusions": EXCLUSIONS,
            "model_ids": sorted(self.models),
        }


class PricedUsage(Model):
    model_id: str | None
    usd: Decimal = Decimal(0)
    priced_tokens: int = 0
    unpriced_tokens: int = 0
    available: bool = True
    complete: bool = False
    reasons: list[str] = Field(default_factory=list)
    catalog_version: str
    tier: Literal["short", "long"] | None = None
    rates: RateTier | None = None
    source_urls: list[str] = Field(default_factory=list)
    verified_on: date | None = None


def load_catalog(path: Path | None = None) -> PricingCatalog:
    """Load the bundled immutable comparison snapshot, never fetch prices."""
    raw = (
        path.read_text()
        if path is not None
        else files("codex_time").joinpath("pricing-v1.json").read_text()
    )
    return PricingCatalog.model_validate_json(raw)


def known_tokens(counts: TokenCounts) -> int:
    """A lower bound that never adds cached/reasoning subsets twice."""
    inputs = counts.input_tokens
    if inputs is None:
        inputs = (counts.cached_input_tokens or 0) + (counts.cache_write_input_tokens or 0)
    outputs = counts.output_tokens
    if outputs is None:
        outputs = counts.reasoning_output_tokens or 0
    return max(counts.total_tokens or 0, inputs + outputs)


def _input_parts(
    counts: TokenCounts, model: ModelPrice, rates: RateTier
) -> tuple[list[tuple[int, Decimal]], list[str]]:
    inputs, cached, writes = (
        counts.input_tokens,
        counts.cached_input_tokens,
        counts.cache_write_input_tokens,
    )
    reasons: list[str] = []
    parts: list[tuple[int, Decimal]] = []
    if inputs == 0 and not cached and not writes:
        return parts, reasons
    if inputs is not None and (cached or 0) + (writes or 0) > inputs:
        return [], ["input subsets exceed observed input; input remains unpriced"]
    if cached is None:
        reasons.append("cached-input evidence unavailable")
    elif cached:
        if rates.cached_input is None:
            reasons.append("cached-input rate unavailable")
        else:
            parts.append((cached, rates.cached_input))
    if model.cache_write_mode == "ordinary":
        # Earlier models have no additional write premium; the non-read input
        # remains ordinary input even when the write counter was not emitted.
        if inputs is not None and cached is not None:
            parts.append((inputs - cached, rates.input))
        elif writes:
            parts.append((writes, rates.input))
    else:
        if writes:
            if model.cache_write_mode == "separate" and rates.cache_write is not None:
                parts.append((writes, rates.cache_write))
            else:
                reasons.append("cache-write rate unavailable")
        if inputs is not None and cached is not None:
            remaining = inputs - cached
            if writes is None and remaining:
                reasons.append("cache-write evidence unavailable; non-cached input unpriced")
            elif writes is not None:
                parts.append((remaining - writes, rates.input))
    if inputs is None:
        reasons.append("input-token total unavailable; only known subsets can be priced")
    return parts, reasons


def price_usage(
    observation: UsageObservation, catalog: PricingCatalog | None = None
) -> PricedUsage:
    """Price one established increment; cumulative values cannot select a tier."""
    catalog = catalog or load_catalog()
    counts = observation.delta
    result = PricedUsage(model_id=observation.model_id, catalog_version=catalog.version)
    if counts is None or all(value is None for value in counts.model_dump().values()):
        result.available = False
        result.reasons = ["usage increment unavailable"]
        return result
    total = known_tokens(counts)
    result.unpriced_tokens = total
    if (
        total == 0
        and not any(value for value in counts.model_dump().values() if value is not None)
        and (counts.total_tokens == 0 or (counts.input_tokens == 0 and counts.output_tokens == 0))
    ):
        result.complete = True
        return result
    model = catalog.models.get(observation.model_id or "")
    if model is None:
        result.reasons = ["model has no verified Standard price"]
        return result
    result.source_urls = model.source_urls.copy()
    result.verified_on = model.verified_on
    result.tier = "short"
    rates = model.short
    if model.long_context_threshold is not None:
        if observation.request_input_tokens is None:
            result.reasons = ["request input size unavailable for long-context pricing"]
            result.tier = None
            return result
        if observation.request_input_tokens > model.long_context_threshold:
            assert model.long is not None  # Validated catalog invariant.
            rates, result.tier = model.long, "long"
    result.rates = rates
    inputs, outputs = counts.input_tokens, counts.output_tokens
    if counts.total_tokens is not None and inputs is not None and outputs is not None:
        if counts.total_tokens < inputs + outputs:
            result.reasons = ["total tokens conflict with input/output categories"]
            return result
    parts, result.reasons = _input_parts(counts, model, rates)
    if outputs is not None:
        if (counts.reasoning_output_tokens or 0) > outputs:
            result.reasons.append("reasoning subset exceeds output; output remains unpriced")
        else:
            parts.append((outputs, rates.output))
    else:
        result.reasons.append("output-token total unavailable; only known reasoning can be priced")
        if counts.reasoning_output_tokens:
            parts.append((counts.reasoning_output_tokens, rates.output))
    # Adapt precision to evidence size, including unusually large imported
    # integer counters. Export precision never depends on terminal rounding.
    with localcontext() as ctx:
        ctx.prec = max(28, len(str(total)) + sum(len(str(rate)) for _, rate in parts) + 12)
        result.usd = sum((Decimal(n) * rate for n, rate in parts), Decimal(0)) / 1_000_000
    result.priced_tokens = sum(n for n, _ in parts)
    result.unpriced_tokens = max(0, total - result.priced_tokens)
    if result.unpriced_tokens and not result.reasons:
        result.reasons.append("total includes tokens without a billing category")
    result.complete = result.unpriced_tokens == 0 and not result.reasons
    return result
