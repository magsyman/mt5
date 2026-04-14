"""Spread modeling and synthetic generation (points-only)."""

from trading_supervisor.spread.spread_generator import (
    generate_synthetic_spread_points,
    generate_synthetic_spread_price,
    spread_points_to_price,
)
from trading_supervisor.spread.spread_models import (
    FOREX_DEFAULT,
    METALS_DEFAULT,
    SpreadDistributionConfig,
    SymbolClass,
)
from trading_supervisor.spread.spread_stats import (
    SpreadComparisonResult,
    SpreadStats,
    compare_spread_stats,
    compute_spread_stats,
)

__all__ = [
    "FOREX_DEFAULT",
    "METALS_DEFAULT",
    "SpreadComparisonResult",
    "SpreadDistributionConfig",
    "SpreadStats",
    "SymbolClass",
    "compare_spread_stats",
    "compute_spread_stats",
    "generate_synthetic_spread_points",
    "generate_synthetic_spread_price",
    "spread_points_to_price",
]

