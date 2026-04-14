from __future__ import annotations

from datetime import datetime, timedelta, timezone

from trading_supervisor.core.enums import Direction
from trading_supervisor.positions.position_models import Position
from trading_supervisor.risk.frequency import check_trade_frequency


def _closed(symbol: str, close_ts: datetime | None) -> Position:
    now = datetime.now(timezone.utc)
    return Position(
        position_id="p1",
        symbol=symbol,
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
    )


def test_no_trades_ok() -> None:
    now = datetime.now(timezone.utc)
    ok, reason = check_trade_frequency([], symbol="EURUSD", now=now, max_trades=3, window_seconds=300)
    assert ok is True
    assert reason == "ok"


def test_trades_below_limit_ok() -> None:
    now = datetime.now(timezone.utc)
    closed = [_closed("EURUSD", now - timedelta(seconds=10)), _closed("EURUSD", now - timedelta(seconds=20))]
    ok, reason = check_trade_frequency(closed, symbol="EURUSD", now=now, max_trades=3, window_seconds=300)
    assert ok is True
    assert reason == "ok"


def test_trades_equal_limit_reject() -> None:
    now = datetime.now(timezone.utc)
    closed = [
        _closed("EURUSD", now - timedelta(seconds=10)),
        _closed("EURUSD", now - timedelta(seconds=20)),
        _closed("EURUSD", now - timedelta(seconds=30)),
    ]
    ok, reason = check_trade_frequency(closed, symbol="EURUSD", now=now, max_trades=3, window_seconds=300)
    assert ok is False
    assert reason == "frequency_limit_exceeded"


def test_trades_above_limit_reject() -> None:
    now = datetime.now(timezone.utc)
    closed = [
        _closed("EURUSD", now - timedelta(seconds=10)),
        _closed("EURUSD", now - timedelta(seconds=20)),
        _closed("EURUSD", now - timedelta(seconds=30)),
        _closed("EURUSD", now - timedelta(seconds=40)),
    ]
    ok, reason = check_trade_frequency(closed, symbol="EURUSD", now=now, max_trades=3, window_seconds=300)
    assert ok is False
    assert reason == "frequency_limit_exceeded"


def test_ignore_trades_outside_window() -> None:
    now = datetime.now(timezone.utc)
    closed = [
        _closed("EURUSD", now - timedelta(seconds=301)),
        _closed("EURUSD", now - timedelta(seconds=400)),
        _closed("EURUSD", now - timedelta(seconds=10)),
    ]
    ok, reason = check_trade_frequency(closed, symbol="EURUSD", now=now, max_trades=2, window_seconds=300)
    assert ok is True
    assert reason == "ok"

