from __future__ import annotations

import random

from trading_supervisor.spread.spread_models import SpreadDistributionConfig


def _piecewise_linear_quantile(
    u: float,
    *,
    q0: float,
    q50: float,
    q90: float,
    q95: float,
    q100: float,
) -> float:
    # u in [0,1]. Outputs in points.
    if u <= 0.0:
        return q0
    if u >= 1.0:
        return q100

    if u <= 0.50:
        t = u / 0.50
        return q0 + t * (q50 - q0)
    if u <= 0.90:
        t = (u - 0.50) / 0.40
        return q50 + t * (q90 - q50)
    if u <= 0.95:
        t = (u - 0.90) / 0.05
        return q90 + t * (q95 - q90)
    t = (u - 0.95) / 0.05
    return q95 + t * (q100 - q95)


def generate_synthetic_spread_points(
    config: SpreadDistributionConfig,
    rng: random.Random,
) -> float:
    """
    Generate a deterministic, bounded synthetic spread in POINTS.

    Notes:
    - Generation is points-only; no price conversion here.
    - Output is always within [min_points, max_points].
    """
    # Concentrate around the median with bounded tails via quantiles.
    u = rng.betavariate(5.0, 5.0)
    points = _piecewise_linear_quantile(
        u,
        q0=config.min_points,
        q50=config.median_points,
        q90=config.p90_points,
        q95=config.p95_points,
        q100=config.max_points,
    )

    # Hard clamp for numerical safety.
    if points < config.min_points:
        return float(config.min_points)
    if points > config.max_points:
        return float(config.max_points)
    return float(points)


def spread_points_to_price(spread_points: float, symbol_point: float) -> float:
    if symbol_point <= 0:
        raise ValueError("symbol_point must be > 0")
    return float(spread_points * symbol_point)


def generate_synthetic_spread_price(
    config: SpreadDistributionConfig,
    symbol_point: float,
    rng: random.Random,
) -> tuple[float, float]:
    spread_points = generate_synthetic_spread_points(config=config, rng=rng)
    spread_price = spread_points_to_price(spread_points=spread_points, symbol_point=symbol_point)
    return (float(spread_points), float(spread_price))

