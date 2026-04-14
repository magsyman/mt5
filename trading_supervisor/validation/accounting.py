from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trading_supervisor.core.enums import FinalDecision, RejectionReason, RejectionStage


class AccountingCounters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_signals: int = 0
    accepted_signals: int = 0
    rejected_signals: int = 0
    executed_signals: int = 0
    cancelled_signals: int = 0

    def acceptance_rate(self) -> float:
        if self.total_signals <= 0:
            return 0.0
        return self.accepted_signals / self.total_signals

    def execution_rate(self) -> float:
        if self.total_signals <= 0:
            return 0.0
        return self.executed_signals / self.total_signals

    def record_received(self) -> None:
        self.total_signals += 1
        self._validate_invariants()

    def record_accepted(self) -> None:
        self.accepted_signals += 1
        self._validate_invariants()

    def record_rejected(self) -> None:
        self.rejected_signals += 1
        self._validate_invariants()

    def record_executed(self) -> None:
        self.executed_signals += 1
        self._validate_invariants()

    def record_cancelled(self) -> None:
        self.cancelled_signals += 1
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        fields = (
            self.total_signals,
            self.accepted_signals,
            self.rejected_signals,
            self.executed_signals,
            self.cancelled_signals,
        )
        if any(v < 0 for v in fields):
            raise ValueError("counters must never be negative")

        if self.rejected_signals + self.accepted_signals > self.total_signals:
            raise ValueError("rejected_signals + accepted_signals cannot exceed total_signals")

        if self.accepted_signals > self.total_signals:
            raise ValueError("accepted_signals cannot exceed total_signals")
        if self.rejected_signals > self.total_signals:
            raise ValueError("rejected_signals cannot exceed total_signals")
        if self.executed_signals > self.total_signals:
            raise ValueError("executed_signals cannot exceed total_signals")
        if self.cancelled_signals > self.total_signals:
            raise ValueError("cancelled_signals cannot exceed total_signals")

        if self.executed_signals > self.accepted_signals:
            raise ValueError("executed_signals cannot exceed accepted_signals")
        if self.cancelled_signals > self.accepted_signals:
            raise ValueError("cancelled_signals cannot exceed accepted_signals")

    def validate_or_raise(self) -> None:
        self._validate_invariants()


class PerSignalAuditRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    symbol: str
    spread_price: float | None = None
    spread_points: float | None = None
    symbol_point: float | None = None
    thresholds_used: dict[str, float] = Field(default_factory=dict)
    rejection_reason: RejectionReason | None = None
    rejection_stage: RejectionStage | None = None
    final_decision: FinalDecision
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol")
    @classmethod
    def _symbol_upper_trimmed(cls, v: str) -> str:
        v2 = v.strip().upper()
        if v2 == "":
            raise ValueError("symbol must not be empty")
        return v2

    @model_validator(mode="after")
    def _rejection_fields_consistency(self) -> "PerSignalAuditRow":
        if self.final_decision == FinalDecision.ACCEPTED:
            if self.rejection_reason is not None or self.rejection_stage is not None:
                raise ValueError(
                    "rejection_reason and rejection_stage must be None when final_decision='accepted'"
                )
        if self.final_decision == FinalDecision.REJECTED:
            if self.rejection_reason is None or self.rejection_stage is None:
                raise ValueError(
                    "rejection_reason and rejection_stage required when final_decision='rejected'"
                )
        return self

