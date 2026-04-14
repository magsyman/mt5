from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator


class SymbolClass(str, Enum):
    FOREX = "forex"
    METALS = "metals"


class SpreadDistributionConfig(BaseModel):
    """All values are in POINTS (not price units)."""

    model_config = ConfigDict(extra="forbid")

    symbol_class: SymbolClass
    min_points: float
    median_points: float
    p90_points: float
    p95_points: float
    max_points: float

    @model_validator(mode="after")
    def _validate_points(self) -> "SpreadDistributionConfig":
        vals = {
            "min_points": self.min_points,
            "median_points": self.median_points,
            "p90_points": self.p90_points,
            "p95_points": self.p95_points,
            "max_points": self.max_points,
        }
        nonpositive = [k for k, v in vals.items() if v <= 0]
        if nonpositive:
            raise ValueError(f"all spread point values must be > 0; non-positive: {nonpositive}")

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


# Deterministic defaults (POINTS ONLY)
FOREX_DEFAULT = SpreadDistributionConfig(
    symbol_class=SymbolClass.FOREX,
    min_points=2.0,
    median_points=8.0,
    p90_points=15.0,
    p95_points=20.0,
    max_points=30.0,
)

METALS_DEFAULT = SpreadDistributionConfig(
    symbol_class=SymbolClass.METALS,
    min_points=10.0,
    median_points=35.0,
    p90_points=70.0,
    p95_points=90.0,
    max_points=140.0,
)

XAUUSD_DEFAULT = SpreadDistributionConfig(
    symbol_class=SymbolClass.METALS,
    min_points=52.0,
    median_points=54.0,
    p90_points=55.0,
    p95_points=55.0,
    max_points=56.0,
)

