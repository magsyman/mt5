from __future__ import annotations

import pytest

from trading_supervisor.spread.spread_stats import (
    SpreadStats,
    compare_spread_stats,
    compute_spread_stats,
)


def test_empty_list_fails() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        compute_spread_stats([])


def test_stats_monotonic() -> None:
    stats = compute_spread_stats([5.0, 1.0, 2.0, 10.0, 3.0, 4.0])
    assert stats.min_points <= stats.median_points <= stats.p90_points <= stats.p95_points <= stats.max_points


def test_compare_ratios_computed_correctly() -> None:
    synthetic = SpreadStats(min_points=2, median_points=4, p90_points=9, p95_points=10, max_points=20)
    observed = SpreadStats(min_points=1, median_points=2, p90_points=3, p95_points=5, max_points=10)
    r = compare_spread_stats(synthetic=synthetic, observed=observed)
    assert r.ratios["min_ratio"] == pytest.approx(2.0)
    assert r.ratios["median_ratio"] == pytest.approx(2.0)
    assert r.ratios["p90_ratio"] == pytest.approx(3.0)
    assert r.ratios["p95_ratio"] == pytest.approx(2.0)
    assert r.ratios["max_ratio"] == pytest.approx(2.0)

