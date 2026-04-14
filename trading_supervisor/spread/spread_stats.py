from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class SpreadStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_points: float
    median_points: float
    p90_points: float
    p95_points: float
    max_points: float

    @model_validator(mode="after")
    def _validate_ordering(self) -> "SpreadStats":
        if not (
            self.min_points
            <= self.median_points
            <= self.p90_points
            <= self.p95_points
            <= self.max_points
        ):
            raise ValueError(
                "invalid spread ordering; require "
                "min_points <= median_points <= p90_points <= p95_points <= max_points"
            )
        return self


def _quantile(sorted_points: list[float], q: float) -> float:
    if not (0.0 <= q <= 1.0):
        raise ValueError("q must be within [0, 1]")
    n = len(sorted_points)
    if n == 0:
        raise ValueError("points must not be empty")
    if n == 1:
        return float(sorted_points[0])

    # Linear interpolation between closest ranks (inclusive endpoints).
    pos = q * (n - 1)
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    if lo == hi:
        return float(sorted_points[lo])
    frac = pos - lo
    return float(sorted_points[lo] * (1.0 - frac) + sorted_points[hi] * frac)


def compute_spread_stats(points: list[float]) -> SpreadStats:
    if len(points) == 0:
        raise ValueError("points must not be empty")
    pts = sorted(float(x) for x in points)

    return SpreadStats(
        min_points=float(pts[0]),
        median_points=_quantile(pts, 0.50),
        p90_points=_quantile(pts, 0.90),
        p95_points=_quantile(pts, 0.95),
        max_points=float(pts[-1]),
    )


class SpreadComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    synthetic: SpreadStats
    observed: SpreadStats
    ratios: dict[str, float]


def compare_spread_stats(
    synthetic: SpreadStats,
    observed: SpreadStats,
) -> SpreadComparisonResult:
    observed_vals = {
        "min": observed.min_points,
        "median": observed.median_points,
        "p90": observed.p90_points,
        "p95": observed.p95_points,
        "max": observed.max_points,
    }
    nonpositive = [k for k, v in observed_vals.items() if v <= 0]
    if nonpositive:
        raise ValueError(f"observed spread stats must be > 0; non-positive: {nonpositive}")

    ratios = {
        "min_ratio": float(synthetic.min_points / observed.min_points),
        "median_ratio": float(synthetic.median_points / observed.median_points),
        "p90_ratio": float(synthetic.p90_points / observed.p90_points),
        "p95_ratio": float(synthetic.p95_points / observed.p95_points),
        "max_ratio": float(synthetic.max_points / observed.max_points),
    }
    return SpreadComparisonResult(synthetic=synthetic, observed=observed, ratios=ratios)

