"""Exact present-rate costs; fixtures never read live logs or network."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest


def observation(**changes):
    from codex_time.models import TokenCounts, UsageObservation

    values = dict(
        id="observation",
        session_id="session",
        at=datetime(2026, 10, 8, tzinfo=UTC),
        model_id="synthetic",
        cwd="/work",
        request_input_tokens=1_000_000,
        delta=TokenCounts(
            input_tokens=1_000_000,
            cached_input_tokens=400_000,
            output_tokens=100_000,
            reasoning_output_tokens=25_000,
            total_tokens=1_100_000,
        ),
    )
    values.update(changes)
    return UsageObservation(**values)


def catalog(*, cache_write_mode="ordinary", long_context=False):
    from codex_time.pricing import ModelPrice, PricingCatalog, RateTier

    short = RateTier(input="2", cached_input="0.50", output="10", cache_write="2.50")
    model = ModelPrice(
        model_id="synthetic",
        short=short,
        cache_write_mode=cache_write_mode,
        source_urls=["https://example.test/pricing"],
        verified_on="2026-10-08",
        long_context_threshold=272_000 if long_context else None,
        long=RateTier(input="4", cached_input="1", output="15", cache_write="5")
        if long_context
        else None,
    )
    return PricingCatalog(
        version="test-v1",
        verified_on="2026-10-08",
        source_urls=["https://example.test/pricing"],
        models={"synthetic": model},
    )


def test_cached_input_and_reasoning_are_not_charged_twice():
    from codex_time.pricing import price_usage

    priced = price_usage(observation(), catalog())
    assert priced.usd == Decimal("2.40")
    assert priced.priced_tokens == 1_100_000
    assert priced.unpriced_tokens == 0 and priced.complete
    assert isinstance(priced.model_dump(mode="json")["usd"], str)


def test_unknown_models_keep_tokens_unpriced_without_alias_guessing():
    from codex_time.pricing import price_usage

    priced = price_usage(observation(model_id="synthetic-internal"), catalog())
    assert priced.usd == 0 and priced.priced_tokens == 0
    assert priced.unpriced_tokens == 1_100_000 and not priced.complete
    assert "model has no verified Standard price" in priced.reasons


def test_cache_write_subsets_use_their_own_rate():
    from codex_time.models import TokenCounts
    from codex_time.pricing import price_usage

    counts = TokenCounts(
        input_tokens=1_000_000,
        cached_input_tokens=400_000,
        cache_write_input_tokens=100_000,
        output_tokens=100_000,
        total_tokens=1_100_000,
    )
    priced = price_usage(observation(delta=counts), catalog(cache_write_mode="separate"))
    assert priced.usd == Decimal("2.45") and priced.complete


def test_missing_cache_write_evidence_prices_only_known_cached_input_and_output():
    from codex_time.pricing import price_usage

    priced = price_usage(observation(), catalog(cache_write_mode="separate"))
    assert priced.usd == Decimal("1.20")
    assert priced.priced_tokens == 500_000 and priced.unpriced_tokens == 600_000
    assert not priced.complete and any("cache-write" in reason for reason in priced.reasons)


def test_missing_cached_input_does_not_assume_no_discount():
    from codex_time.models import TokenCounts
    from codex_time.pricing import price_usage

    counts = TokenCounts(input_tokens=1_000_000, output_tokens=100_000, total_tokens=1_100_000)
    priced = price_usage(observation(delta=counts), catalog())
    assert priced.usd == Decimal("1") and priced.unpriced_tokens == 1_000_000
    assert not priced.complete


@pytest.mark.parametrize("request_tokens, expected", [(272_000, "0.20"), (272_001, "0.35")])
def test_long_context_uses_request_input_evidence_only(request_tokens, expected):
    from codex_time.models import TokenCounts
    from codex_time.pricing import price_usage

    counts = TokenCounts(
        input_tokens=50_000, cached_input_tokens=0, output_tokens=10_000, total_tokens=60_000
    )
    cumulative = TokenCounts(input_tokens=20_000_000, total_tokens=30_000_000)
    priced = price_usage(
        observation(delta=counts, cumulative=cumulative, request_input_tokens=request_tokens),
        catalog(long_context=True),
    )
    assert priced.usd == Decimal(expected) and priced.complete


def test_missing_request_evidence_leaves_long_context_cost_unpriced():
    from codex_time.pricing import price_usage

    priced = price_usage(observation(request_input_tokens=None), catalog(long_context=True))
    assert priced.usd == 0 and priced.unpriced_tokens == 1_100_000
    assert not priced.complete and any("request" in reason for reason in priced.reasons)


def test_zero_and_unavailable_usage_remain_distinct():
    from codex_time.models import TokenCounts
    from codex_time.pricing import price_usage

    zero = price_usage(observation(model_id=None, delta=TokenCounts(total_tokens=0)), catalog())
    missing = price_usage(observation(delta=None), catalog())
    assert zero.available and zero.complete and zero.usd == 0
    assert not missing.available and not missing.complete and missing.usd == 0


def test_inconsistent_subsets_do_not_make_negative_input_cost():
    from codex_time.models import TokenCounts
    from codex_time.pricing import price_usage

    counts = TokenCounts(input_tokens=10, cached_input_tokens=20, output_tokens=5, total_tokens=15)
    priced = price_usage(observation(delta=counts), catalog())
    assert priced.usd >= 0 and not priced.complete
    assert priced.unpriced_tokens >= 10


def test_default_catalog_prices_public_exact_id_but_not_invented_alias():
    from codex_time.models import TokenCounts
    from codex_time.pricing import load_catalog, price_usage

    counts = TokenCounts(
        input_tokens=1_000,
        cached_input_tokens=0,
        cache_write_input_tokens=0,
        output_tokens=100,
        total_tokens=1_100,
    )
    rates = load_catalog()
    priced = price_usage(
        observation(model_id="gpt-6.1-sol", delta=counts, request_input_tokens=1_000), rates
    )
    assert priced.complete and priced.usd == Decimal("0.003")
    assert not price_usage(observation(model_id="gpt-6.1-sol-internal"), rates).complete
    assert rates.metadata()["verified_on"] == "2026-10-08"


def test_zero_input_and_output_are_zero_without_redundant_total_field():
    from codex_time.models import TokenCounts
    from codex_time.pricing import price_usage

    priced = price_usage(
        observation(model_id=None, delta=TokenCounts(input_tokens=0, output_tokens=0)), catalog()
    )
    assert priced.complete and priced.available and priced.usd == 0


def test_verified_gpt41_prices_recorded_usage_without_long_context_tier():
    from codex_time.pricing import price_usage

    priced = price_usage(observation(model_id="gpt-4.1", request_input_tokens=None))
    assert priced.complete and priced.usd == Decimal("2.20")


@pytest.mark.parametrize("subset", ["cached_input_tokens", "reasoning_output_tokens"])
def test_contradictory_zero_does_not_hide_positive_token_subset(subset):
    from codex_time.models import TokenCounts
    from codex_time.pricing import price_usage

    counts = TokenCounts(input_tokens=0, output_tokens=0, total_tokens=0, **{subset: 5})
    priced = price_usage(observation(model_id=None, delta=counts), catalog())
    assert not priced.complete
    assert priced.usd == 0


def test_huge_token_integers_keep_low_order_dollars_exact():
    from codex_time.models import TokenCounts
    from codex_time.pricing import price_usage

    counts = TokenCounts(input_tokens=10**40 + 1, cached_input_tokens=0, output_tokens=0)
    priced = price_usage(observation(delta=counts), catalog())
    assert priced.usd == Decimal("20000000000000000000000000000000000.000002")
