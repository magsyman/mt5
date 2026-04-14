from __future__ import annotations

import pytest

from trading_supervisor.spread.spread_models import (
    FOREX_DEFAULT,
    METALS_DEFAULT,
    SymbolClass,
    XAUUSD_DEFAULT,
)
from trading_supervisor.spread.spread_registry import classify_symbol, get_spread_config
from trading_supervisor.spread.spread_stats import SpreadStats, compare_spread_stats, compute_spread_stats
from trading_supervisor.spread.spread_validation import (
    generate_sample,
    is_realistic,
    validate_synthetic_vs_observed,
)


def test_symbol_classification() -> None:
    assert classify_symbol("XAUUSD") == SymbolClass.METALS
    assert classify_symbol("EURUSD") == SymbolClass.FOREX


def test_config_retrieval() -> None:
    assert get_spread_config("EURUSD") is FOREX_DEFAULT
    assert get_spread_config("XAUUSD") is XAUUSD_DEFAULT


def test_xauusd_config_is_much_tighter_than_generic_metals_config() -> None:
    assert (XAUUSD_DEFAULT.max_points - XAUUSD_DEFAULT.min_points) < (
        METALS_DEFAULT.max_points - METALS_DEFAULT.min_points
    )


def test_sample_generation_size_and_bounds() -> None:
    sample = generate_sample(config=FOREX_DEFAULT, n=200, seed=123)
    assert len(sample) == 200
    assert min(sample) >= FOREX_DEFAULT.min_points
    assert max(sample) <= FOREX_DEFAULT.max_points


def test_comparison_ratios() -> None:
    observed = list(range(5, 15))  # 5..14
    synthetic = [x * 2 for x in observed]
    comp = validate_synthetic_vs_observed(synthetic_points=synthetic, observed_points=observed)
    assert set(comp.ratios.keys()) == {"min_ratio", "median_ratio", "p90_ratio", "p95_ratio", "max_ratio"}
    assert comp.ratios["min_ratio"] == pytest.approx(2.0)
    assert comp.ratios["max_ratio"] == pytest.approx(2.0)


def test_realism_check() -> None:
    observed = list(range(5, 25))  # non-MT5, manually constructed observed distribution

    # Similar distributions -> realistic
    similar_comp = validate_synthetic_vs_observed(
        synthetic_points=list(observed), observed_points=list(observed)
    )
    assert is_realistic(similar_comp, max_ratio=3.0) is True

    # Artificially inflated synthetic -> not realistic
    inflated_comp = validate_synthetic_vs_observed(
        synthetic_points=[x * 10 for x in observed], observed_points=list(observed)
    )
    assert is_realistic(inflated_comp, max_ratio=3.0) is False


def test_generated_xauusd_sample_stats_close_to_target_band() -> None:
    sample = generate_sample(config=XAUUSD_DEFAULT, n=2000, seed=123)
    stats = compute_spread_stats(sample)
    assert 53.0 <= stats.median_points <= 55.0
    assert 54.0 <= stats.p90_points <= 56.0
    assert stats.max_points <= 56.0


def test_stricter_xauusd_comparison_ratios() -> None:
    observed_points = [52.0, 52.0, 53.0, 54.0, 54.0, 55.0, 55.0, 55.0, 55.0, 55.0]
    synthetic_points = generate_sample(config=XAUUSD_DEFAULT, n=len(observed_points), seed=999)
    comp = validate_synthetic_vs_observed(
        synthetic_points=synthetic_points,
        observed_points=observed_points,
    )
    assert 0.95 <= comp.ratios["median_ratio"] <= 1.05
    assert 0.95 <= comp.ratios["p90_ratio"] <= 1.05
    assert 0.95 <= comp.ratios["max_ratio"] <= 1.10

