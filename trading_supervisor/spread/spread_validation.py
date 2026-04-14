from __future__ import annotations

import random

from trading_supervisor.spread.spread_generator import generate_synthetic_spread_points
from trading_supervisor.spread.spread_models import SpreadDistributionConfig
from trading_supervisor.spread.spread_stats import (
    SpreadComparisonResult,
    SpreadStats,
    compare_spread_stats,
    compute_spread_stats,
)


def generate_sample(
    config: SpreadDistributionConfig,
    n: int,
    seed: int,
) -> list[float]:
    if n < 0:
        raise ValueError("n must be >= 0")
    rng = random.Random(seed)
    return [generate_synthetic_spread_points(config=config, rng=rng) for _ in range(n)]


def validate_synthetic_vs_observed(
    synthetic_points: list[float],
    observed_points: list[float],
) -> SpreadComparisonResult:
    synthetic_stats: SpreadStats = compute_spread_stats(synthetic_points)
    observed_stats: SpreadStats = compute_spread_stats(observed_points)
    return compare_spread_stats(synthetic=synthetic_stats, observed=observed_stats)


def is_realistic(
    comparison: SpreadComparisonResult,
    max_ratio: float = 3.0,
) -> bool:
    for ratio in comparison.ratios.values():
        if ratio > max_ratio:
            return False
    return True

