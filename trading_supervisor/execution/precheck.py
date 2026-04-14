from __future__ import annotations

from datetime import datetime

from trading_supervisor.core.enums import FinalDecision
from trading_supervisor.positions.position_models import Position
from trading_supervisor.risk.cooldown import check_symbol_cooldown
from trading_supervisor.risk.equity import check_max_drawdown
from trading_supervisor.risk.exposure import check_max_open_positions
from trading_supervisor.risk.frequency import check_trade_frequency
from trading_supervisor.risk.kill_switch import check_kill_switch
from trading_supervisor.risk.sanity import check_signal_sanity
from trading_supervisor.signals.models import RiskResult, SignalInput, ValidationResult


def build_execution_decision(
    signal: SignalInput,
    market_validation: ValidationResult,
    risk_result: RiskResult,
    open_positions: list[Position] | None = None,
    closed_positions: list[Position] | None = None,
    now: datetime | None = None,
    starting_balance: float | None = None,
    current_balance: float | None = None,
) -> tuple[FinalDecision, str]:
    ok, reason = check_signal_sanity(signal)
    if not ok:
        return (FinalDecision.REJECTED, reason)

    if market_validation.success is False:
        return (FinalDecision.REJECTED, "market_validation_failed")
    if risk_result.allowed is False:
        return (FinalDecision.REJECTED, "risk_rejected")

    positions = [] if open_positions is None else open_positions
    ok, reason = check_max_open_positions(
        open_positions=positions,
        symbol=signal.symbol,
        max_per_symbol=1,
        max_total=3,
    )
    if not ok:
        return (FinalDecision.REJECTED, reason)

    closed = [] if closed_positions is None else closed_positions
    ok, reason = check_symbol_cooldown(
        closed_positions=closed,
        symbol=signal.symbol,
        now=signal.timestamp if now is None else now,
        cooldown_seconds=60,
    )
    if not ok:
        return (FinalDecision.REJECTED, reason)

    ok, reason = check_trade_frequency(
        closed_positions=closed,
        symbol=signal.symbol,
        now=signal.timestamp if now is None else now,
        max_trades=3,
        window_seconds=300,
    )
    if not ok:
        return (FinalDecision.REJECTED, reason)

    if starting_balance is not None and current_balance is not None:
        dd_ok, dd_reason = check_max_drawdown(
            starting_balance=float(starting_balance),
            current_balance=float(current_balance),
            max_drawdown_percent=0.2,
        )
        ks_ok, ks_reason = check_kill_switch(
            current_balance=float(current_balance),
            starting_balance=float(starting_balance),
            min_balance_ratio=0.5,
        )
        if not ks_ok:
            return (FinalDecision.REJECTED, ks_reason)
        if not dd_ok:
            return (FinalDecision.REJECTED, dd_reason)
    return (FinalDecision.ACCEPTED, "ok")

