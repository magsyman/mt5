from __future__ import annotations

import pytest

from scripts.collect_real_spreads import (
    compute_spread_points,
    duplicate_key,
    is_valid_tick,
)


def test_duplicate_detection_key() -> None:
    k1 = duplicate_key(raw_tick_time=123, bid=1.0, ask=1.2)
    k2 = duplicate_key(raw_tick_time=123, bid=1.0, ask=1.2)
    k3 = duplicate_key(raw_tick_time=124, bid=1.0, ask=1.2)
    assert k1 == k2
    assert k1 != k3


def test_invalid_tick_rejection_logic() -> None:
    assert is_valid_tick(bid=1.0, ask=1.0) is True
    assert is_valid_tick(bid=1.0, ask=1.1) is True
    assert is_valid_tick(bid=0.0, ask=1.1) is False
    assert is_valid_tick(bid=1.0, ask=0.0) is False
    assert is_valid_tick(bid=1.1, ask=1.0) is False


def test_spread_points_formula() -> None:
    bid = 1.2345
    ask = 1.2348
    symbol_point = 0.0001
    assert compute_spread_points(bid=bid, ask=ask, symbol_point=symbol_point) == pytest.approx(3.0)


def test_spread_points_requires_positive_symbol_point() -> None:
    with pytest.raises(ValueError, match="symbol_point must be > 0"):
        compute_spread_points(bid=1.0, ask=1.1, symbol_point=0.0)

