from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trading_supervisor.core.enums import Direction, RejectionReason, RejectionStage


def _require_tz_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt


def is_signal_stale(signal: "SignalInput", now: datetime, max_age_seconds: int) -> bool:
    _require_tz_aware(signal.timestamp)
    _require_tz_aware(now)
    return (now - signal.timestamp).total_seconds() > max_age_seconds


class SignalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)

    signal_id: str
    strategy_id: str
    symbol: str
    direction: Direction
    timestamp: datetime
    proposed_entry: float
    proposed_sl: float
    proposed_tp: float
    lot: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol")
    @classmethod
    def _symbol_upper_trimmed(cls, v: str) -> str:
        v2 = v.strip().upper()
        if v2 == "":
            raise ValueError("symbol must not be empty")
        return v2

    @field_validator("timestamp")
    @classmethod
    def _timestamp_tz_aware(cls, v: datetime) -> datetime:
        return _require_tz_aware(v)

    @field_validator("proposed_entry", "proposed_sl", "proposed_tp")
    @classmethod
    def _positive_prices(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price must be > 0")
        return v

    @field_validator("lot")
    @classmethod
    def _positive_lot(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if v <= 0:
            raise ValueError("lot must be > 0 when provided")
        return v

    @model_validator(mode="after")
    def _sl_tp_not_equal_entry(self) -> "SignalInput":
        if self.proposed_sl == self.proposed_entry:
            raise ValueError("proposed_sl must not equal proposed_entry")
        if self.proposed_tp == self.proposed_entry:
            raise ValueError("proposed_tp must not equal proposed_entry")
        return self


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    rejection_reason: RejectionReason | None = None
    rejection_stage: RejectionStage | None = None
    spread_price: float | None = None
    spread_points: float | None = None
    symbol_point: float | None = None
    thresholds_used: dict[str, float] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _coherent_rejection_fields(self) -> "ValidationResult":
        if self.success:
            if self.rejection_reason is not None or self.rejection_stage is not None:
                raise ValueError("rejection_reason/stage must be None when success=True")
            if len(self.thresholds_used) == 0:
                raise ValueError("thresholds_used must not be empty when success=True")
        else:
            if self.rejection_reason is None or self.rejection_stage is None:
                raise ValueError("rejection_reason and rejection_stage required when success=False")
        return self

    @model_validator(mode="after")
    def _spread_invariants(self) -> "ValidationResult":
        sp = self.spread_points
        pt = self.symbol_point
        pr = self.spread_price

        if (sp is None) != (pt is None):
            raise ValueError("spread_points and symbol_point must either both be set or both be None")

        if sp is not None and pt is not None:
            if not any("spread" in k.lower() for k in self.thresholds_used.keys()):
                raise ValueError("thresholds_used must include a spread-related key when spread_points is provided")
            if pr is None:
                raise ValueError("spread_price must be set when spread_points and symbol_point are set")
            expected = sp * pt
            if abs(pr - expected) >= 1e-9:
                raise ValueError("spread_price must equal spread_points * symbol_point within tolerance")

        return self


class RiskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    rule_hits: list[str] = Field(default_factory=list)
    final_position_size: float | None = None
    reason: str

    @field_validator("final_position_size")
    @classmethod
    def _positive_position_size(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if v <= 0:
            raise ValueError("final_position_size must be > 0 when provided")
        return v


class AuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    component: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def _audit_timestamp_tz_aware(cls, v: datetime) -> datetime:
        return _require_tz_aware(v)

