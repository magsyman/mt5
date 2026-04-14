from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    broker_order_id: str | None = None
    fill_price: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: float | None = None

    @field_validator("fill_price")
    @classmethod
    def _fill_price_positive(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if v <= 0:
            raise ValueError("fill_price must be > 0 when provided")
        return v

    @field_validator("latency_ms")
    @classmethod
    def _latency_non_negative(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if v < 0:
            raise ValueError("latency_ms must be >= 0 when provided")
        return v

    @model_validator(mode="after")
    def _coherent_fields(self) -> "ExecutionResult":
        if self.accepted:
            if self.broker_order_id is None:
                raise ValueError("broker_order_id required when accepted=True")
            if self.fill_price is None:
                raise ValueError("fill_price required when accepted=True")
            if self.latency_ms is None:
                raise ValueError("latency_ms required when accepted=True")
            if self.error_code is not None or self.error_message is not None:
                raise ValueError("error_code/error_message must be None when accepted=True")
        else:
            if self.broker_order_id is not None or self.fill_price is not None:
                raise ValueError("broker_order_id/fill_price must be None when accepted=False")
            if self.error_code is None:
                raise ValueError("error_code required when accepted=False")
        return self


class ExecutionRequest(BaseModel):
    """
    Minimal request container for Phase 2 wiring/tests.

    Later phases will add MT5-specific request fields and strict mapping logic.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str
    volume: float = Field(gt=0)

