from __future__ import annotations

from trading_supervisor.core.config import get_settings
from trading_supervisor.core.enums import RejectionReason, RejectionStage
from trading_supervisor.market.market_models import MarketValidationInput
from trading_supervisor.market.symbol_resolver import resolve_symbol
from trading_supervisor.signals.models import ValidationResult


def validate_market(input: MarketValidationInput) -> ValidationResult:
    settings = get_settings()

    resolved = resolve_symbol(input.symbol, input.available_symbols)
    if resolved is None:
        return ValidationResult(
            success=False,
            rejection_reason=RejectionReason.INVALID_SYMBOL,
            rejection_stage=RejectionStage.MARKET_VALIDATION,
            thresholds_used={},
            details={"input_symbol": input.symbol},
        )

    if input.tick is None:
        return ValidationResult(
            success=False,
            rejection_reason=RejectionReason.NO_MARKET_DATA,
            rejection_stage=RejectionStage.MARKET_VALIDATION,
            thresholds_used={},
            details={"symbol": resolved},
        )

    tick = input.tick
    if tick.bid <= 0 or tick.ask <= 0 or tick.ask < tick.bid:
        return ValidationResult(
            success=False,
            rejection_reason=RejectionReason.INVALID_TICK,
            rejection_stage=RejectionStage.MARKET_VALIDATION,
            thresholds_used={},
            details={"symbol": resolved, "bid": tick.bid, "ask": tick.ask},
        )

    age_seconds = (input.now - tick.timestamp).total_seconds()
    if age_seconds > settings.max_signal_age_seconds:
        return ValidationResult(
            success=False,
            rejection_reason=RejectionReason.STALE_MARKET_DATA,
            rejection_stage=RejectionStage.MARKET_VALIDATION,
            thresholds_used={"max_tick_age_seconds": float(settings.max_signal_age_seconds)},
            details={"symbol": resolved, "age_seconds": float(age_seconds)},
        )

    spread_price = tick.ask - tick.bid
    if spread_price < 0:
        return ValidationResult(
            success=False,
            rejection_reason=RejectionReason.INVALID_TICK,
            rejection_stage=RejectionStage.MARKET_VALIDATION,
            thresholds_used={},
            details={"symbol": resolved, "spread_price": spread_price},
        )

    spread_points = spread_price / input.symbol_point
    if spread_points < 0:
        return ValidationResult(
            success=False,
            rejection_reason=RejectionReason.INVALID_TICK,
            rejection_stage=RejectionStage.MARKET_VALIDATION,
            thresholds_used={},
            details={"symbol": resolved, "spread_points": spread_points},
        )

    thresholds_used = {
        "max_tick_age_seconds": float(settings.max_signal_age_seconds),
        "max_spread_points_hard": float(settings.max_spread_points_forex_hard),
    }

    return ValidationResult(
        success=True,
        rejection_reason=None,
        rejection_stage=None,
        spread_price=float(spread_price),
        spread_points=float(spread_points),
        symbol_point=float(input.symbol_point),
        thresholds_used=thresholds_used,
        details={"symbol": resolved},
    )

