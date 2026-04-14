from __future__ import annotations

from datetime import datetime, timedelta, timezone

from trading_supervisor.core.enums import Direction, RejectionReason, RejectionStage
from trading_supervisor.risk.hard_risk import run_hard_risk_checks
from trading_supervisor.signals.models import SignalInput, ValidationResult
from trading_supervisor.spread.spread_registry import get_spread_config


def _mk_signal(symbol: str = "EURUSD") -> SignalInput:
    now = datetime.now(timezone.utc)
    return SignalInput(
        signal_id="s1",
        strategy_id="stratA",
        symbol=symbol,
        direction=Direction.BUY,
        timestamp=now,
        proposed_entry=1.1,
        proposed_sl=1.09,
        proposed_tp=1.12,
    )


def _mk_market_ok(symbol: str, spread_points: float) -> ValidationResult:
    return ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": float(get_spread_config(symbol).max_points)},
        spread_points=float(spread_points),
        symbol_point=0.0001 if symbol != "XAUUSD" else 0.01,
        spread_price=float(spread_points) * (0.0001 if symbol != "XAUUSD" else 0.01),
    )


def _mk_market_failed() -> ValidationResult:
    return ValidationResult(
        success=False,
        rejection_reason=RejectionReason.INVALID_TICK,
        rejection_stage=RejectionStage.MARKET_VALIDATION,
    )


def test_all_pass_allowed_true_and_final_position_size_preserved() -> None:
    now = datetime.now(timezone.utc)
    s = _mk_signal(symbol="EURUSD")
    mv = _mk_market_ok("EURUSD", spread_points=5.0)
    rr = run_hard_risk_checks(signal=s, market_validation=mv, now=now, position_size=0.1)
    assert rr.allowed is True
    assert rr.final_position_size == 0.1
    assert rr.rule_hits == []
    assert rr.reason == "ok"


def test_stale_signal_rejected() -> None:
    now = datetime.now(timezone.utc)
    s = _mk_signal()
    s.timestamp = now - timedelta(seconds=999)  # type: ignore[misc]
    mv = _mk_market_ok("EURUSD", spread_points=5.0)
    rr = run_hard_risk_checks(signal=s, market_validation=mv, now=now, position_size=0.1)
    assert rr.allowed is False
    assert "stale_signal" in rr.rule_hits
    assert rr.final_position_size is None
    assert rr.reason == "hard_risk_rejected"


def test_spread_too_wide_rejected() -> None:
    now = datetime.now(timezone.utc)
    s = _mk_signal(symbol="XAUUSD")
    cfg = get_spread_config("XAUUSD")
    mv = _mk_market_ok("XAUUSD", spread_points=float(cfg.max_points) + 1.0)
    rr = run_hard_risk_checks(signal=s, market_validation=mv, now=now, position_size=0.1)
    assert rr.allowed is False
    assert "spread_exceeds_hard_limit" in rr.rule_hits


def test_invalid_sl_tp_rejected() -> None:
    now = datetime.now(timezone.utc)
    s = _mk_signal()
    s.proposed_sl = s.proposed_entry  # type: ignore[misc]
    mv = _mk_market_ok("EURUSD", spread_points=5.0)
    rr = run_hard_risk_checks(signal=s, market_validation=mv, now=now, position_size=0.1)
    assert rr.allowed is False
    assert "invalid_stop_loss" in rr.rule_hits


def test_non_positive_position_size_rejected() -> None:
    now = datetime.now(timezone.utc)
    s = _mk_signal()
    mv = _mk_market_ok("EURUSD", spread_points=5.0)
    rr = run_hard_risk_checks(signal=s, market_validation=mv, now=now, position_size=0.0)
    assert rr.allowed is False
    assert "non_positive_position_size" in rr.rule_hits


def test_multiple_failures_accumulate_rule_hits() -> None:
    now = datetime.now(timezone.utc)
    s = _mk_signal(symbol="XAUUSD")
    s.timestamp = now - timedelta(seconds=999)  # type: ignore[misc]
    s.proposed_tp = s.proposed_entry  # type: ignore[misc]
    cfg = get_spread_config("XAUUSD")
    mv = _mk_market_ok("XAUUSD", spread_points=float(cfg.max_points) + 1.0)
    rr = run_hard_risk_checks(signal=s, market_validation=mv, now=now, position_size=0.0)
    assert rr.allowed is False
    assert set(rr.rule_hits) >= {
        "stale_signal",
        "spread_exceeds_hard_limit",
        "invalid_take_profit",
        "non_positive_position_size",
    }

