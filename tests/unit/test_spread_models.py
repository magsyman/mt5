from __future__ import annotations

import pytest

from trading_supervisor.spread.spread_models import (
    FOREX_DEFAULT,
    METALS_DEFAULT,
    SpreadDistributionConfig,
    SymbolClass,
    XAUUSD_DEFAULT,
)


def test_valid_forex_config() -> None:
    cfg = SpreadDistributionConfig(
        symbol_class=SymbolClass.FOREX,
        min_points=1.0,
        median_points=5.0,
        p90_points=10.0,
        p95_points=12.0,
        max_points=20.0,
    )
    assert cfg.symbol_class == SymbolClass.FOREX


def test_invalid_threshold_ordering_fails() -> None:
    with pytest.raises(ValueError, match="invalid spread ordering"):
        SpreadDistributionConfig(
            symbol_class=SymbolClass.FOREX,
            min_points=1.0,
            median_points=10.0,
            p90_points=9.0,
            p95_points=12.0,
            max_points=20.0,
        )


def test_metals_config_distinct_from_forex_config() -> None:
    assert METALS_DEFAULT.symbol_class != FOREX_DEFAULT.symbol_class
    assert METALS_DEFAULT.median_points != FOREX_DEFAULT.median_points
    assert METALS_DEFAULT.max_points != FOREX_DEFAULT.max_points


def test_xauusd_config_is_tighter_than_generic_metals() -> None:
    assert XAUUSD_DEFAULT.symbol_class == SymbolClass.METALS
    assert XAUUSD_DEFAULT.min_points >= METALS_DEFAULT.min_points
    assert XAUUSD_DEFAULT.max_points <= METALS_DEFAULT.max_points
    assert (XAUUSD_DEFAULT.max_points - XAUUSD_DEFAULT.min_points) < (
        METALS_DEFAULT.max_points - METALS_DEFAULT.min_points
    )

