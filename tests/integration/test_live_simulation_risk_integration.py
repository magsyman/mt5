from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_supervisor.core.enums import Direction, FinalDecision
from trading_supervisor.core.mode import ModeGuard, RunMode
from trading_supervisor.performance.performance_tracker import PerformanceTracker
from trading_supervisor.pipeline.orchestrator import PipelineInputs, run_signal_pipeline
from trading_supervisor.positions.position_models import Position
from trading_supervisor.positions.position_tracker import PositionTracker
from trading_supervisor.risk.system_state import SystemState
from trading_supervisor.signals.models import SignalInput, ValidationResult


def test_balance_decreases_after_closed_trade() -> None:
    starting_balance = 10_000.0
    tracker = PositionTracker()
    perf = PerformanceTracker()
    recorded: set[str] = set()

    now = datetime.now(timezone.utc)
    p = Position(
        position_id="SIM-LOSS",
        symbol="XAUUSD",
        direction=Direction.BUY,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=110.0,
        size=2.0,
        open_timestamp=now,
        status="open",
        close_price=None,
        close_timestamp=None,
        pnl=None,
    )
    tracker.open_position(p)
    tracker.update_positions_with_tick("XAUUSD", price=99.0, timestamp=now)

    for pos in tracker.positions.values():
        if pos.status == "closed" and pos.position_id not in recorded:
            perf.record_closed_position(pos)
            recorded.add(pos.position_id)

    current_balance = starting_balance + perf.get_total_pnl()
    assert current_balance < starting_balance


def test_multiple_trades_balance_updates_correctly() -> None:
    starting_balance = 10_000.0
    tracker = PositionTracker()
    perf = PerformanceTracker()
    recorded: set[str] = set()
    now = datetime.now(timezone.utc)

    # Win +2
    p1 = Position(
        position_id="SIM-WIN",
        symbol="XAUUSD",
        direction=Direction.BUY,
        entry_price=100.0,
        stop_loss=90.0,
        take_profit=101.0,
        size=2.0,
        open_timestamp=now,
        status="open",
        close_price=None,
        close_timestamp=None,
        pnl=None,
    )
    # Loss -3
    p2 = Position(
        position_id="SIM-LOSS",
        symbol="XAUUSD",
        direction=Direction.SELL,
        entry_price=100.0,
        stop_loss=103.0,
        take_profit=90.0,
        size=1.0,
        open_timestamp=now,
        status="open",
        close_price=None,
        close_timestamp=None,
        pnl=None,
    )
    tracker.open_position(p1)
    tracker.open_position(p2)
    tracker.update_positions_with_tick("XAUUSD", price=101.0, timestamp=now)
    tracker.update_positions_with_tick("XAUUSD", price=103.0, timestamp=now)

    for pos in tracker.positions.values():
        if pos.status == "closed" and pos.position_id not in recorded:
            perf.record_closed_position(pos)
            recorded.add(pos.position_id)

    assert perf.get_total_pnl() == pytest.approx(-1.0)
    current_balance = starting_balance + perf.get_total_pnl()
    assert current_balance == pytest.approx(9_999.0)


def test_decision_blocked_when_drawdown_exceeded() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    signal = SignalInput(
        signal_id="sig-1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=Direction.BUY,
        timestamp=now,
        proposed_entry=1.1,
        proposed_sl=1.09,
        proposed_tp=1.12,
    )
    mv = ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": 30.0},
        spread_points=10.0,
        symbol_point=0.0001,
        spread_price=0.001,
    )

    r = run_signal_pipeline(
        PipelineInputs(
            signal=signal,
            market_validation=mv,
            position_size=0.1,
            now=now,
            slippage_points=0.0,
            open_positions=[],
            closed_positions=[],
            starting_balance=10_000.0,
            current_balance=8_000.0,
            system_state=SystemState(),
            mode_guard=ModeGuard(RunMode.SIMULATION),
        )
    )
    assert r.decision == FinalDecision.REJECTED
    assert r.decision_reason == "max_drawdown_exceeded"

