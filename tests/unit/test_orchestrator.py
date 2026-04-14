from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trading_supervisor.core.enums import Direction, FinalDecision, RejectionReason, RejectionStage
from trading_supervisor.core.mode import ModeGuard, RunMode
from trading_supervisor.pipeline.orchestrator import PipelineInputs, run_signal_pipeline
from trading_supervisor.positions.position_models import Position
from trading_supervisor.risk.system_state import SystemState
from trading_supervisor.signals.models import SignalInput, ValidationResult
from trading_supervisor.spread.spread_registry import get_spread_config


def _mk_signal(*, symbol: str = "EURUSD", direction: Direction = Direction.BUY, timestamp: datetime) -> SignalInput:
    return SignalInput(
        signal_id="sig-1",
        strategy_id="stratA",
        symbol=symbol,
        direction=direction,
        timestamp=timestamp,
        proposed_entry=1.1000,
        proposed_sl=1.0900,
        proposed_tp=1.1200,
    )


def _mk_market_ok(*, symbol_point: float, spread_points: float) -> ValidationResult:
    return ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": 999.0},
        spread_points=float(spread_points),
        symbol_point=float(symbol_point),
        spread_price=float(spread_points) * float(symbol_point),
    )


def _mk_market_failed() -> ValidationResult:
    return ValidationResult(
        success=False,
        rejection_reason=RejectionReason.INVALID_TICK,
        rejection_stage=RejectionStage.MARKET_VALIDATION,
    )


def _empty_positions() -> list[Position]:
    return []


def _system_state() -> SystemState:
    return SystemState()


def _mode_guard() -> ModeGuard:
    return ModeGuard(RunMode.SIMULATION)


def test_happy_path_accepts_and_audits() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    s = _mk_signal(symbol="EURUSD", direction=Direction.BUY, timestamp=now)
    mv = _mk_market_ok(symbol_point=0.0001, spread_points=10.0)
    inputs = PipelineInputs(
        signal=s,
        market_validation=mv,
        position_size=0.1,
        now=now,
        slippage_points=2.0,
        open_positions=_empty_positions(),
        closed_positions=_empty_positions(),
        starting_balance=10_000.0,
        current_balance=10_000.0,
        system_state=_system_state(),
        mode_guard=_mode_guard(),
    )
    r = run_signal_pipeline(inputs)
    assert r.decision == FinalDecision.ACCEPTED
    assert r.risk_result.allowed is True
    assert r.execution_result.accepted is True
    assert r.execution_result.broker_order_id == "SIM-sig-1"
    assert r.execution_result.latency_ms == 50.0

    payload = r.audit_record.payload
    assert payload["signal_id"] == "sig-1"
    assert payload["symbol"] == "EURUSD"
    assert payload["decision"] == FinalDecision.ACCEPTED.value
    assert payload["decision_reason"] == "ok"
    assert payload["risk_allowed"] is True
    assert payload["risk_rule_hits"] == []
    assert payload["execution_accepted"] is True
    assert payload["execution_error_code"] is None
    assert payload["final_position_size"] == pytest.approx(0.1)


def test_market_validation_failure_rejects_and_not_executed() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    s = _mk_signal(symbol="EURUSD", timestamp=now)
    mv = _mk_market_failed()
    r = run_signal_pipeline(
        PipelineInputs(
            signal=s,
            market_validation=mv,
            position_size=0.1,
            now=now,
            slippage_points=0.0,
            open_positions=_empty_positions(),
            closed_positions=_empty_positions(),
            starting_balance=10_000.0,
            current_balance=10_000.0,
            system_state=_system_state(),
            mode_guard=_mode_guard(),
        )
    )
    assert r.decision == FinalDecision.REJECTED
    assert r.execution_result.accepted is False
    assert r.execution_result.error_code == "not_executed"
    assert r.audit_record.payload["decision"] == FinalDecision.REJECTED.value


def test_hard_risk_rejection_due_to_stale_signal() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    stale_ts = now - timedelta(seconds=999)
    s = _mk_signal(symbol="EURUSD", timestamp=stale_ts)
    mv = _mk_market_ok(symbol_point=0.0001, spread_points=10.0)
    r = run_signal_pipeline(
        PipelineInputs(
            signal=s,
            market_validation=mv,
            position_size=0.1,
            now=now,
            slippage_points=0.0,
            open_positions=_empty_positions(),
            closed_positions=_empty_positions(),
            starting_balance=10_000.0,
            current_balance=10_000.0,
            system_state=_system_state(),
            mode_guard=_mode_guard(),
        )
    )
    assert r.decision == FinalDecision.REJECTED
    assert r.execution_result.accepted is False
    assert r.execution_result.error_code == "not_executed"
    assert "stale_signal" in r.risk_result.rule_hits


def test_hard_risk_rejection_due_to_spread_too_wide_xauusd() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    s = _mk_signal(symbol="XAUUSD", timestamp=now)
    cfg = get_spread_config("XAUUSD")
    mv = _mk_market_ok(symbol_point=0.01, spread_points=float(cfg.max_points) + 10.0)
    r = run_signal_pipeline(
        PipelineInputs(
            signal=s,
            market_validation=mv,
            position_size=0.1,
            now=now,
            slippage_points=0.0,
            open_positions=_empty_positions(),
            closed_positions=_empty_positions(),
            starting_balance=10_000.0,
            current_balance=10_000.0,
            system_state=_system_state(),
            mode_guard=_mode_guard(),
        )
    )
    assert r.decision == FinalDecision.REJECTED
    assert r.execution_result.accepted is False
    assert r.execution_result.error_code == "not_executed"


def test_audit_payload_consistency_fields_present() -> None:
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    s = _mk_signal(symbol="EURUSD", timestamp=now)
    mv = _mk_market_failed()
    r = run_signal_pipeline(
        PipelineInputs(
            signal=s,
            market_validation=mv,
            position_size=0.1,
            now=now,
            slippage_points=0.0,
            open_positions=_empty_positions(),
            closed_positions=_empty_positions(),
            starting_balance=10_000.0,
            current_balance=10_000.0,
            system_state=_system_state(),
            mode_guard=_mode_guard(),
        )
    )


def test_kill_switch_disables_system_and_next_call_is_system_disabled() -> None:
    state = SystemState()
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    s = _mk_signal(symbol="EURUSD", timestamp=now)
    mv = _mk_market_ok(symbol_point=0.0001, spread_points=10.0)

    r1 = run_signal_pipeline(
        PipelineInputs(
            signal=s,
            market_validation=mv,
            position_size=0.1,
            now=now,
            slippage_points=0.0,
            open_positions=_empty_positions(),
            closed_positions=_empty_positions(),
            starting_balance=10_000.0,
            current_balance=5_000.0,
            system_state=state,
            mode_guard=_mode_guard(),
        )
    )
    assert r1.decision == FinalDecision.REJECTED
    assert r1.decision_reason == "kill_switch_triggered"
    assert state.is_trading_enabled() is False

    r2 = run_signal_pipeline(
        PipelineInputs(
            signal=s,
            market_validation=mv,
            position_size=0.1,
            now=now,
            slippage_points=0.0,
            open_positions=_empty_positions(),
            closed_positions=_empty_positions(),
            starting_balance=10_000.0,
            current_balance=10_000.0,
            system_state=state,
            mode_guard=_mode_guard(),
        )
    )
    assert r2.decision == FinalDecision.REJECTED
    assert r2.decision_reason == "system_disabled"
    assert r2.execution_result.accepted is False
    payload = r2.audit_record.payload
    assert payload["signal_id"] == "sig-1"
    assert payload["symbol"] == "EURUSD"
    assert payload["decision"] in {FinalDecision.ACCEPTED.value, FinalDecision.REJECTED.value}
    assert payload["execution_error_code"] == r2.execution_result.error_code
    assert payload["final_position_size"] == r2.risk_result.final_position_size

