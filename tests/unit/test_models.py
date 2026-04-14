from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_supervisor.core.enums import Direction
from trading_supervisor.execution.execution_models import ExecutionResult
from trading_supervisor.signals.models import SignalInput, ValidationResult, is_signal_stale


def test_signal_input_valid_creation() -> None:
    s = SignalInput(
        signal_id="s1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=Direction.BUY,
        timestamp=datetime.now(timezone.utc),
        proposed_entry=1.1000,
        proposed_sl=1.0900,
        proposed_tp=1.1200,
        lot=0.1,
        metadata={"source": "ea"},
    )
    assert s.symbol == "EURUSD"


def test_invalid_naive_datetime_rejected() -> None:
    with pytest.raises(Exception):
        SignalInput(
            signal_id="s1",
            strategy_id="stratA",
            symbol="EURUSD",
            direction=Direction.BUY,
            timestamp=datetime.utcnow(),  # naive
            proposed_entry=1.1,
            proposed_sl=1.09,
            proposed_tp=1.12,
        )


def test_symbol_lowercase_or_space_normalized_to_uppercase_trimmed() -> None:
    s = SignalInput(
        signal_id="s1",
        strategy_id="stratA",
        symbol="  eurusd ",
        direction=Direction.SELL,
        timestamp=datetime.now(timezone.utc),
        proposed_entry=1.1,
        proposed_sl=1.11,
        proposed_tp=1.09,
    )
    assert s.symbol == "EURUSD"


def test_non_positive_price_rejected() -> None:
    with pytest.raises(Exception):
        SignalInput(
            signal_id="s1",
            strategy_id="stratA",
            symbol="EURUSD",
            direction=Direction.BUY,
            timestamp=datetime.now(timezone.utc),
            proposed_entry=0.0,
            proposed_sl=1.0,
            proposed_tp=2.0,
        )


def test_validation_result_defaults() -> None:
    with pytest.raises(Exception):
        ValidationResult(success=True)

    vr = ValidationResult(success=True, thresholds_used={"any_threshold": 1.0})
    assert vr.thresholds_used == {"any_threshold": 1.0}
    assert vr.details == {}


def test_validation_result_spread_invariant_valid_case() -> None:
    vr = ValidationResult(
        success=True,
        thresholds_used={"max_spread_points_hard": 30.0},
        spread_points=10.0,
        symbol_point=0.0001,
        spread_price=0.001,
    )
    assert vr.spread_price == 0.001


def test_validation_result_spread_invariant_invalid_mismatch_raises() -> None:
    with pytest.raises(Exception):
        ValidationResult(
            success=True,
            thresholds_used={"max_spread_points_hard": 30.0},
            spread_points=10.0,
            symbol_point=0.0001,
            spread_price=0.002,  # mismatch
        )


def test_is_signal_stale_non_stale_case() -> None:
    s = SignalInput(
        signal_id="s1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=Direction.BUY,
        timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        proposed_entry=1.1,
        proposed_sl=1.09,
        proposed_tp=1.12,
    )
    now = datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc)
    assert is_signal_stale(s, now=now, max_age_seconds=10) is False


def test_is_signal_stale_stale_case() -> None:
    s = SignalInput(
        signal_id="s1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=Direction.BUY,
        timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        proposed_entry=1.1,
        proposed_sl=1.09,
        proposed_tp=1.12,
    )
    now = datetime(2026, 1, 1, 0, 0, 11, tzinfo=timezone.utc)
    assert is_signal_stale(s, now=now, max_age_seconds=10) is True


def test_execution_result_fill_price_validation() -> None:
    with pytest.raises(Exception):
        ExecutionResult(
            accepted=True,
            broker_order_id="123",
            fill_price=-1.0,
        )

