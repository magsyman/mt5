from __future__ import annotations

from datetime import datetime

from trading_supervisor.signals.models import SignalInput, ValidationResult, is_signal_stale
from trading_supervisor.spread.spread_registry import get_spread_config


def rule_signal_not_stale(
    signal: SignalInput,
    now: datetime,
    max_age_seconds: int,
) -> tuple[bool, str]:
    if is_signal_stale(signal, now=now, max_age_seconds=max_age_seconds):
        return (False, "stale_signal")
    return (True, "ok")


def rule_spread_within_hard_limit(
    signal: SignalInput,
    market_validation: ValidationResult,
    symbol: str,
) -> tuple[bool, str]:
    if market_validation.success is False:
        return (False, "market_validation_failed")

    spread_points = market_validation.spread_points
    if spread_points is None:
        return (False, "missing_spread_points")

    config = get_spread_config(symbol)
    hard_limit = float(config.max_points)
    if float(spread_points) > hard_limit:
        return (False, "spread_exceeds_hard_limit")
    return (True, "ok")


def rule_sl_tp_structurally_valid(signal: SignalInput) -> tuple[bool, str]:
    if signal.proposed_sl == signal.proposed_entry:
        return (False, "invalid_stop_loss")
    if signal.proposed_tp == signal.proposed_entry:
        return (False, "invalid_take_profit")
    return (True, "ok")


def rule_position_size_positive(position_size: float) -> tuple[bool, str]:
    if position_size > 0:
        return (True, "ok")
    return (False, "non_positive_position_size")

