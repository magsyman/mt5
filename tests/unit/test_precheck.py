from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trading_supervisor.core.enums import Direction, FinalDecision, RejectionReason, RejectionStage
from trading_supervisor.execution.precheck import build_execution_decision
from trading_supervisor.positions.position_models import Position
from trading_supervisor.signals.models import RiskResult, SignalInput, ValidationResult


def _mk_signal() -> SignalInput:
    return SignalInput(
        signal_id="s1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=Direction.BUY,
        timestamp=datetime.now(timezone.utc),
        proposed_entry=1.1,
        proposed_sl=1.09,
        proposed_tp=1.12,
    )


def test_market_failure_rejected() -> None:
    signal = _mk_signal()
    market_validation = ValidationResult(
        success=False,
        rejection_reason=RejectionReason.INVALID_TICK,
        rejection_stage=RejectionStage.MARKET_VALIDATION,
    )
    risk = RiskResult(allowed=True, reason="ok")
    decision, reason = build_execution_decision(signal, market_validation=market_validation, risk_result=risk)
    assert decision == FinalDecision.REJECTED
    assert reason == "market_validation_failed"


def test_risk_failure_rejected() -> None:
    signal = _mk_signal()
    market_validation = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    risk = RiskResult(allowed=False, reason="nope")
    decision, reason = build_execution_decision(signal, market_validation=market_validation, risk_result=risk)
    assert decision == FinalDecision.REJECTED
    assert reason == "risk_rejected"


def test_both_valid_accepted() -> None:
    signal = _mk_signal()
    market_validation = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    risk = RiskResult(allowed=True, reason="ok")
    decision, reason = build_execution_decision(signal, market_validation=market_validation, risk_result=risk)
    assert decision == FinalDecision.ACCEPTED
    assert reason == "ok"


def test_exposure_blocks_execution() -> None:
    signal = _mk_signal()
    market_validation = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    risk = RiskResult(allowed=True, reason="ok")
    now = datetime.now(timezone.utc)
    open_positions = [
        Position(
            position_id="p1",
            symbol="EURUSD",
            direction=Direction.BUY,
            entry_price=1.0,
            stop_loss=0.9,
            take_profit=1.1,
            size=1.0,
            open_timestamp=now,
            status="open",
            close_price=None,
            close_timestamp=None,
            pnl=None,
        ),
        Position(
            position_id="p2",
            symbol="XAUUSD",
            direction=Direction.BUY,
            entry_price=1.0,
            stop_loss=0.9,
            take_profit=1.1,
            size=1.0,
            open_timestamp=now,
            status="open",
            close_price=None,
            close_timestamp=None,
            pnl=None,
        ),
        Position(
            position_id="p3",
            symbol="GBPUSD",
            direction=Direction.BUY,
            entry_price=1.0,
            stop_loss=0.9,
            take_profit=1.1,
            size=1.0,
            open_timestamp=now,
            status="open",
            close_price=None,
            close_timestamp=None,
            pnl=None,
        ),
    ]

    decision, reason = build_execution_decision(
        signal,
        market_validation=market_validation,
        risk_result=risk,
        open_positions=open_positions,
    )
    assert decision == FinalDecision.REJECTED
    assert reason == "max_total_positions_exceeded"


def test_cooldown_blocks_execution() -> None:
    signal = _mk_signal()
    market_validation = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    risk = RiskResult(allowed=True, reason="ok")
    now = datetime.now(timezone.utc)
    closed_positions = [
        Position(
            position_id="c1",
            symbol="EURUSD",
            direction=Direction.BUY,
            entry_price=1.0,
            stop_loss=0.9,
            take_profit=1.1,
            size=1.0,
            open_timestamp=now,
            status="closed",
            close_price=1.0,
            close_timestamp=now,
            pnl=1.0,
        )
    ]

    decision, reason = build_execution_decision(
        signal,
        market_validation=market_validation,
        risk_result=risk,
        closed_positions=closed_positions,
        now=now,
    )
    assert decision == FinalDecision.REJECTED
    assert reason == "cooldown_active"


def test_drawdown_blocks_execution() -> None:
    signal = _mk_signal()
    market_validation = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    risk = RiskResult(allowed=True, reason="ok")

    decision, reason = build_execution_decision(
        signal,
        market_validation=market_validation,
        risk_result=risk,
        starting_balance=1000.0,
        current_balance=800.0,
    )
    assert decision == FinalDecision.REJECTED
    assert reason == "max_drawdown_exceeded"


def test_kill_switch_blocks_execution() -> None:
    signal = _mk_signal()
    market_validation = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    risk = RiskResult(allowed=True, reason="ok")

    decision, reason = build_execution_decision(
        signal,
        market_validation=market_validation,
        risk_result=risk,
        starting_balance=10_000.0,
        current_balance=5_000.0,
    )
    assert decision == FinalDecision.REJECTED
    assert reason == "kill_switch_triggered"


def test_sanity_failure_blocks_execution() -> None:
    signal = SignalInput(
        signal_id="s1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=Direction.BUY,
        timestamp=datetime.now(timezone.utc),
        proposed_entry=1.1,
        proposed_sl=1.2,  # invalid BUY structure
        proposed_tp=1.3,
    )
    market_validation = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    risk = RiskResult(allowed=True, reason="ok")

    decision, reason = build_execution_decision(signal, market_validation=market_validation, risk_result=risk)
    assert decision == FinalDecision.REJECTED
    assert reason == "invalid_structure"


def test_frequency_limit_blocks_execution() -> None:
    signal = _mk_signal()
    market_validation = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    risk = RiskResult(allowed=True, reason="ok")
    now = datetime.now(timezone.utc)
    close_ts = now - timedelta(seconds=61)
    closed_positions = [
        Position(
            position_id="c1",
            symbol="EURUSD",
            direction=Direction.BUY,
            entry_price=1.0,
            stop_loss=0.9,
            take_profit=1.1,
            size=1.0,
            open_timestamp=now,
            status="closed",
            close_price=1.0,
            close_timestamp=close_ts,
            pnl=1.0,
        ),
        Position(
            position_id="c2",
            symbol="EURUSD",
            direction=Direction.BUY,
            entry_price=1.0,
            stop_loss=0.9,
            take_profit=1.1,
            size=1.0,
            open_timestamp=now,
            status="closed",
            close_price=1.0,
            close_timestamp=close_ts,
            pnl=1.0,
        ),
        Position(
            position_id="c3",
            symbol="EURUSD",
            direction=Direction.BUY,
            entry_price=1.0,
            stop_loss=0.9,
            take_profit=1.1,
            size=1.0,
            open_timestamp=now,
            status="closed",
            close_price=1.0,
            close_timestamp=close_ts,
            pnl=1.0,
        ),
    ]

    decision, reason = build_execution_decision(
        signal,
        market_validation=market_validation,
        risk_result=risk,
        closed_positions=closed_positions,
        now=now,
    )
    assert decision == FinalDecision.REJECTED
    assert reason == "frequency_limit_exceeded"

