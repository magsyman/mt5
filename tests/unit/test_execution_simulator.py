from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_supervisor.core.enums import Direction, FinalDecision
from trading_supervisor.core.mode import ModeGuard, RunMode
from trading_supervisor.execution.simulator import simulate_execution
from trading_supervisor.signals.models import SignalInput, ValidationResult


def _mk_signal(direction: Direction, symbol: str = "EURUSD") -> SignalInput:
    return SignalInput(
        signal_id="sig-1",
        strategy_id="stratA",
        symbol=symbol,
        direction=direction,
        timestamp=datetime.now(timezone.utc),
        proposed_entry=1.1000,
        proposed_sl=1.0900,
        proposed_tp=1.1200,
    )


def test_rejected_decision_returns_not_executed() -> None:
    s = _mk_signal(Direction.BUY)
    mv = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    r = simulate_execution(
        signal=s,
        market_validation=mv,
        decision=FinalDecision.REJECTED,
        position_size=0.1,
        slippage_points=0.0,
        mode_guard=ModeGuard(RunMode.SIMULATION),
    )
    assert r.accepted is False
    assert r.error_code == "not_executed"
    assert r.error_message == "decision_not_accepted"
    assert r.latency_ms == 0.0


def test_missing_spread_price_returns_error() -> None:
    s = _mk_signal(Direction.BUY)
    mv = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    r = simulate_execution(
        signal=s,
        market_validation=mv,
        decision=FinalDecision.ACCEPTED,
        position_size=0.1,
        slippage_points=0.0,
        mode_guard=ModeGuard(RunMode.SIMULATION),
    )
    assert r.accepted is False
    assert r.error_code == "missing_market_data"
    assert r.error_message == "no_spread_price"
    assert r.latency_ms == 0.0


def test_buy_fill_price_calculation_correct_forex() -> None:
    s = _mk_signal(Direction.BUY, symbol="EURUSD")
    mv = ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": 30.0},
        spread_points=10.0,
        symbol_point=0.0001,
        spread_price=0.001,
    )
    r = simulate_execution(
        signal=s,
        market_validation=mv,
        decision=FinalDecision.ACCEPTED,
        position_size=0.1,
        slippage_points=2.0,
        mode_guard=ModeGuard(RunMode.SIMULATION),
    )
    assert r.accepted is True
    expected = 1.1000 + 0.001 + (2.0 * 0.0001)
    assert r.fill_price == pytest.approx(expected)
    assert r.broker_order_id == "SIM-sig-1"
    assert r.latency_ms == 50.0


def test_sell_fill_price_calculation_correct_metals() -> None:
    s = _mk_signal(Direction.SELL, symbol="XAUUSD")
    mv = ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": 56.0},
        spread_points=54.0,
        symbol_point=0.01,
        spread_price=0.54,
    )
    r = simulate_execution(
        signal=s,
        market_validation=mv,
        decision=FinalDecision.ACCEPTED,
        position_size=0.1,
        slippage_points=3.0,
        mode_guard=ModeGuard(RunMode.SIMULATION),
    )
    expected = 1.1000 - (3.0 * 0.01)
    assert r.accepted is True
    assert r.fill_price == pytest.approx(expected)
    assert r.broker_order_id == "SIM-sig-1"
    assert r.latency_ms == 50.0


def test_latency_always_set_when_accepted() -> None:
    s = _mk_signal(Direction.BUY)
    mv = ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": 30.0},
        spread_points=10.0,
        symbol_point=0.0001,
        spread_price=0.001,
    )
    r = simulate_execution(
        signal=s,
        market_validation=mv,
        decision=FinalDecision.ACCEPTED,
        position_size=0.1,
        slippage_points=0.0,
        mode_guard=ModeGuard(RunMode.SIMULATION),
    )
    assert r.accepted is True
    assert r.latency_ms is not None


def test_live_mode_raises_error() -> None:
    s = _mk_signal(Direction.BUY)
    mv = ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": 30.0},
        spread_points=10.0,
        symbol_point=0.0001,
        spread_price=0.001,
    )
    with pytest.raises(RuntimeError, match="simulation_only_operation"):
        simulate_execution(
            signal=s,
            market_validation=mv,
            decision=FinalDecision.ACCEPTED,
            position_size=0.1,
            slippage_points=0.0,
            mode_guard=ModeGuard(RunMode.LIVE),
        )

