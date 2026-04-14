from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _require_tz_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt


class TickData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    bid: float
    ask: float
    timestamp: datetime

    @field_validator("symbol")
    @classmethod
    def _symbol_upper_trimmed(cls, v: str) -> str:
        v2 = v.strip().upper()
        if v2 == "":
            raise ValueError("symbol must not be empty")
        return v2

    @field_validator("bid", "ask")
    @classmethod
    def _positive_prices(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price must be > 0")
        return v

    @field_validator("timestamp")
    @classmethod
    def _timestamp_tz_aware(cls, v: datetime) -> datetime:
        return _require_tz_aware(v)

    @field_validator("ask")
    @classmethod
    def _ask_gte_bid(cls, ask: float, info):  # type: ignore[no-untyped-def]
        bid = info.data.get("bid")
        if bid is not None and ask < bid:
            raise ValueError("ask must be >= bid")
        return ask


class MarketValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    tick: TickData | None
    now: datetime

    # Passed explicitly (no hardcoding)
    symbol_point: float = Field(gt=0)
    available_symbols: list[str] = Field(default_factory=list)

    @field_validator("symbol")
    @classmethod
    def _symbol_upper_trimmed(cls, v: str) -> str:
        v2 = v.strip().upper()
        if v2 == "":
            raise ValueError("symbol must not be empty")
        return v2

    @field_validator("now")
    @classmethod
    def _now_tz_aware(cls, v: datetime) -> datetime:
        return _require_tz_aware(v)

