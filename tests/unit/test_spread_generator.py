from __future__ import annotations

import random

import pytest

from trading_supervisor.spread.spread_generator import (
    generate_synthetic_spread_points,
    generate_synthetic_spread_price,
    spread_points_to_price,
)
from trading_supervisor.spread.spread_models import FOREX_DEFAULT, METALS_DEFAULT


def test_generated_points_always_within_bounds() -> None:
    rng = random.Random(123)
    for _ in range(500):
        pts = generate_synthetic_spread_points(config=FOREX_DEFAULT, rng=rng)
        assert FOREX_DEFAULT.min_points <= pts <= FOREX_DEFAULT.max_points


def test_conversion_to_price_is_exact() -> None:
    assert spread_points_to_price(spread_points=12.5, symbol_point=0.0001) == 0.00125


def test_deterministic_generation_with_fixed_seed() -> None:
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    seq1 = [generate_synthetic_spread_points(config=FOREX_DEFAULT, rng=rng1) for _ in range(50)]
    seq2 = [generate_synthetic_spread_points(config=FOREX_DEFAULT, rng=rng2) for _ in range(50)]
    assert seq1 == seq2


def test_generated_price_equals_points_times_symbol_point() -> None:
    rng = random.Random(7)
    symbol_point = 0.0001
    pts, price = generate_synthetic_spread_price(
        config=FOREX_DEFAULT, symbol_point=symbol_point, rng=rng
    )
    assert price == pytest.approx(pts * symbol_point)


def test_no_huge_unrealistic_values_for_default_forex_config_moderate_sample() -> None:
    rng = random.Random(999)
    sample = [generate_synthetic_spread_points(config=FOREX_DEFAULT, rng=rng) for _ in range(2000)]
    assert min(sample) >= FOREX_DEFAULT.min_points
    assert max(sample) <= FOREX_DEFAULT.max_points


def test_no_huge_unrealistic_values_for_default_metals_config_moderate_sample() -> None:
    rng = random.Random(1001)
    sample = [generate_synthetic_spread_points(config=METALS_DEFAULT, rng=rng) for _ in range(2000)]
    assert min(sample) >= METALS_DEFAULT.min_points
    assert max(sample) <= METALS_DEFAULT.max_points

