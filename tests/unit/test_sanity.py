from __future__ import annotations

from datetime import datetime, timezone

from trading_supervisor.core.enums import Direction
from trading_supervisor.risk.sanity import check_signal_sanity
from trading_supervisor.signals.models import SignalInput


def _signal(direction: Direction, entry: float, sl: float, tp: float) -> SignalInput:
    return SignalInput(
        signal_id="s1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=direction,
        timestamp=datetime.now(timezone.utc),
        proposed_entry=entry,
        proposed_sl=sl,
        proposed_tp=tp,
    )


def test_valid_buy_ok() -> None:
    ok, reason = check_signal_sanity(_signal(Direction.BUY, entry=1.1, sl=1.09, tp=1.12))
    assert ok is True
    assert reason == "ok"


def test_valid_sell_ok() -> None:
    ok, reason = check_signal_sanity(_signal(Direction.SELL, entry=1.1, sl=1.12, tp=1.09))
    assert ok is True
    assert reason == "ok"


def test_zero_entry_fails() -> None:
    s = SignalInput.model_construct(
        signal_id="s1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=Direction.BUY,
        timestamp=datetime.now(timezone.utc),
        proposed_entry=0.0,
        proposed_sl=1.0,
        proposed_tp=2.0,
        lot=None,
        metadata={},
    )
    ok, reason = check_signal_sanity(s)
    assert ok is False
    assert reason == "invalid_entry"


def test_negative_sl_fails() -> None:
    s = SignalInput.model_construct(
        signal_id="s1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=Direction.BUY,
        timestamp=datetime.now(timezone.utc),
        proposed_entry=1.0,
        proposed_sl=-1.0,
        proposed_tp=2.0,
        lot=None,
        metadata={},
    )
    ok, reason = check_signal_sanity(s)
    assert ok is False
    assert reason == "invalid_sl"


def test_negative_tp_fails() -> None:
    s = SignalInput.model_construct(
        signal_id="s1",
        strategy_id="stratA",
        symbol="EURUSD",
        direction=Direction.BUY,
        timestamp=datetime.now(timezone.utc),
        proposed_entry=1.0,
        proposed_sl=0.9,
        proposed_tp=-2.0,
        lot=None,
        metadata={},
    )
    ok, reason = check_signal_sanity(s)
    assert ok is False
    assert reason == "invalid_tp"


def test_wrong_buy_structure_fails() -> None:
    ok, reason = check_signal_sanity(_signal(Direction.BUY, entry=1.0, sl=1.1, tp=1.2))
    assert ok is False
    assert reason == "invalid_structure"


def test_wrong_sell_structure_fails() -> None:
    ok, reason = check_signal_sanity(_signal(Direction.SELL, entry=1.0, sl=0.9, tp=1.1))
    assert ok is False
    assert reason == "invalid_structure"

