from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Environment(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class RejectionStage(str, Enum):
    SIGNAL_INTAKE = "signal_intake"
    MARKET_VALIDATION = "market_validation"
    RISK_VALIDATION = "risk_validation"
    EXECUTION = "execution"


class RejectionReason(str, Enum):
    INVALID_SIGNAL = "invalid_signal"
    STALE_SIGNAL = "stale_signal"
    INVALID_SYMBOL = "invalid_symbol"
    SYMBOL_NOT_TRADEABLE = "symbol_not_tradeable"
    NO_MARKET_DATA = "no_market_data"
    INVALID_TICK = "invalid_tick"
    SPREAD_TOO_WIDE = "spread_too_wide"
    INVALID_SL_TP = "invalid_sl_tp"
    MASTER_DISABLED = "master_disabled"
    BASELINE_HALT = "baseline_halt"
    HARD_RISK_REJECT = "hard_risk_reject"
    EXECUTION_FAILED = "execution_failed"


class AuthorityState(str, Enum):
    ENABLED = "enabled"
    RESTRICTED = "restricted"
    DISABLED = "disabled"


class FinalDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class EventType(str, Enum):
    SIGNAL_RECEIVED = "signal_received"
    VALIDATION_COMPLETED = "validation_completed"
    RISK_COMPLETED = "risk_completed"
    EXECUTION_COMPLETED = "execution_completed"
    AUTHORITY_CHANGED = "authority_changed"
    OVERRIDE_APPLIED = "override_applied"
    ROLLBACK_APPLIED = "rollback_applied"

