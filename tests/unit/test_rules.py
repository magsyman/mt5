from __future__ import annotations

from datetime import datetime, timedelta, timezone

from trading_supervisor.core.enums import Direction
from trading_supervisor.risk.rules import (
    rule_position_size_positive,
    rule_signal_not_stale,
    rule_sl_tp_structurally_valid,
    rule_spread_within_hard_limit,
)
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


def test_stale_signal_fails() -> None:
    now = datetime.now(timezone.utc)
    s = _mk_signal()
    s.timestamp = now - timedelta(seconds=100)  # type: ignore[misc]
    ok, reason = rule_signal_not_stale(s, now=now, max_age_seconds=10)
    assert ok is False
    assert reason == "stale_signal"


def test_fresh_signal_passes() -> None:
    now = datetime.now(timezone.utc)
    s = _mk_signal()
    s.timestamp = now - timedelta(seconds=1)  # type: ignore[misc]
    ok, reason = rule_signal_not_stale(s, now=now, max_age_seconds=10)
    assert ok is True
    assert reason == "ok"


def test_spread_above_hard_limit_fails_xauusd() -> None:
    s = _mk_signal(symbol="XAUUSD")
    cfg = get_spread_config("XAUUSD")
    market_validation = ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": float(cfg.max_points)},
        spread_points=float(cfg.max_points) + 0.01,
        symbol_point=0.01,
        spread_price=(float(cfg.max_points) + 0.01) * 0.01,
    )
    ok, reason = rule_spread_within_hard_limit(s, market_validation=market_validation, symbol="XAUUSD")
    assert ok is False
    assert reason == "spread_exceeds_hard_limit"


def test_spread_within_hard_limit_passes_eurusd() -> None:
    s = _mk_signal(symbol="EURUSD")
    cfg = get_spread_config("EURUSD")
    market_validation = ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": float(cfg.max_points)},
        spread_points=float(cfg.max_points),
        symbol_point=0.0001,
        spread_price=float(cfg.max_points) * 0.0001,
    )
    ok, reason = rule_spread_within_hard_limit(s, market_validation=market_validation, symbol="EURUSD")
    assert ok is True
    assert reason == "ok"


def test_invalid_sl_fails() -> None:
    s = _mk_signal()
    s.proposed_sl = s.proposed_entry  # type: ignore[misc]
    ok, reason = rule_sl_tp_structurally_valid(s)
    assert ok is False
    assert reason == "invalid_stop_loss"


def test_invalid_tp_fails() -> None:
    s = _mk_signal()
    s.proposed_tp = s.proposed_entry  # type: ignore[misc]
    ok, reason = rule_sl_tp_structurally_valid(s)
    assert ok is False
    assert reason == "invalid_take_profit"


def test_positive_position_size_passes() -> None:
    ok, reason = rule_position_size_positive(0.01)
    assert ok is True
    assert reason == "ok"


def test_zero_position_size_fails() -> None:
    ok, reason = rule_position_size_positive(0.0)
    assert ok is False
    assert reason == "non_positive_position_size"

