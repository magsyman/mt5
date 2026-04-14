from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_supervisor.core.enums import Direction
from trading_supervisor.positions.position_models import Position
from trading_supervisor.risk.exposure import check_max_open_positions


def _pos(pid: str, symbol: str) -> Position:
    now = datetime.now(timezone.utc)
    return Position(
        position_id=pid,
        symbol=symbol,
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
    )


def test_below_limits_ok() -> None:
    ok, reason = check_max_open_positions(
        open_positions=[_pos("p1", "EURUSD")],
        symbol="EURUSD",
        max_per_symbol=2,
        max_total=3,
    )
    assert ok is True
    assert reason == "ok"


def test_equal_max_total_reject() -> None:
    ok, reason = check_max_open_positions(
        open_positions=[_pos("p1", "EURUSD"), _pos("p2", "XAUUSD")],
        symbol="EURUSD",
        max_per_symbol=5,
        max_total=2,
    )
    assert ok is False
    assert reason == "max_total_positions_exceeded"


def test_above_max_total_reject() -> None:
    ok, reason = check_max_open_positions(
        open_positions=[_pos("p1", "EURUSD"), _pos("p2", "XAUUSD"), _pos("p3", "EURUSD")],
        symbol="EURUSD",
        max_per_symbol=5,
        max_total=2,
    )
    assert ok is False
    assert reason == "max_total_positions_exceeded"


def test_equal_max_symbol_reject() -> None:
    ok, reason = check_max_open_positions(
        open_positions=[_pos("p1", "EURUSD"), _pos("p2", "EURUSD")],
        symbol="EURUSD",
        max_per_symbol=2,
        max_total=10,
    )
    assert ok is False
    assert reason == "max_symbol_positions_exceeded"


def test_above_max_symbol_reject() -> None:
    ok, reason = check_max_open_positions(
        open_positions=[_pos("p1", "EURUSD"), _pos("p2", "EURUSD"), _pos("p3", "EURUSD")],
        symbol="EURUSD",
        max_per_symbol=2,
        max_total=10,
    )
    assert ok is False
    assert reason == "max_symbol_positions_exceeded"

