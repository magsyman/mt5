from __future__ import annotations

from trading_supervisor.core.enums import Direction, FinalDecision
from trading_supervisor.core.mode import ModeGuard
from trading_supervisor.execution.execution_models import ExecutionResult
from trading_supervisor.signals.models import SignalInput, ValidationResult


def simulate_execution(
    signal: SignalInput,
    market_validation: ValidationResult,
    decision: FinalDecision,
    position_size: float,
    slippage_points: float,
    mode_guard: ModeGuard,
) -> ExecutionResult:
    mode_guard.assert_simulation_only()

    if decision != FinalDecision.ACCEPTED:
        return ExecutionResult(
            accepted=False,
            broker_order_id=None,
            fill_price=None,
            error_code="not_executed",
            error_message="decision_not_accepted",
            latency_ms=0.0,
        )

    if market_validation.spread_price is None:
        return ExecutionResult(
            accepted=False,
            broker_order_id=None,
            fill_price=None,
            error_code="missing_market_data",
            error_message="no_spread_price",
            latency_ms=0.0,
        )

    if slippage_points < 0:
        raise ValueError("slippage_points must be >= 0")

    symbol_point = market_validation.symbol_point
    if symbol_point is None:
        raise ValueError("symbol_point must be set on market_validation")

    slip_price = float(slippage_points) * float(symbol_point)

    if signal.direction == Direction.BUY:
        fill_price = float(signal.proposed_entry) + float(market_validation.spread_price) + slip_price
    else:
        fill_price = float(signal.proposed_entry) - slip_price

    return ExecutionResult(
        accepted=True,
        broker_order_id=f"SIM-{signal.signal_id}",
        fill_price=float(fill_price),
        error_code=None,
        error_message=None,
        latency_ms=50.0,
    )

