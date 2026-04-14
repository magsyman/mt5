from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_supervisor.core.enums import Direction
from trading_supervisor.positions.position_models import Position
from trading_supervisor.positions.position_tracker import PositionTracker


def _mk_position(*, position_id: str, symbol: str, direction: Direction) -> Position:
    now = datetime.now(timezone.utc)
    entry = 100.0
    if direction == Direction.BUY:
        sl = 99.0
        tp = 102.0
    else:
        sl = 101.0
        tp = 98.0
    return Position(
        position_id=position_id,
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        size=2.0,
        open_timestamp=now,
        status="open",
        close_price=None,
        close_timestamp=None,
        pnl=None,
    )


def test_open_position_stored() -> None:
    t = PositionTracker()
    p = _mk_position(position_id="p1", symbol="EURUSD", direction=Direction.BUY)
    t.open_position(p)
    assert t.positions["p1"].position_id == "p1"


def test_duplicate_id_rejected() -> None:
    t = PositionTracker()
    p = _mk_position(position_id="p1", symbol="EURUSD", direction=Direction.BUY)
    t.open_position(p)
    with pytest.raises(ValueError, match="already exists"):
        t.open_position(p)


def test_close_position_sets_fields_and_buy_pnl_correct() -> None:
    t = PositionTracker()
    p = _mk_position(position_id="p1", symbol="EURUSD", direction=Direction.BUY)
    t.open_position(p)
    ts = datetime.now(timezone.utc)
    t.close_position("p1", price=101.5, timestamp=ts)
    closed = t.positions["p1"]
    assert closed.status == "closed"
    assert closed.close_price == 101.5
    assert closed.close_timestamp == ts
    assert closed.pnl == pytest.approx((101.5 - 100.0) * 2.0)


def test_sell_pnl_correct() -> None:
    t = PositionTracker()
    p = _mk_position(position_id="p1", symbol="EURUSD", direction=Direction.SELL)
    t.open_position(p)
    ts = datetime.now(timezone.utc)
    t.close_position("p1", price=99.5, timestamp=ts)
    closed = t.positions["p1"]
    assert closed.pnl == pytest.approx((100.0 - 99.5) * 2.0)


def test_sl_hit_closes_position_buy() -> None:
    t = PositionTracker()
    p = _mk_position(position_id="p1", symbol="EURUSD", direction=Direction.BUY)
    t.open_position(p)
    ts = datetime.now(timezone.utc)
    t.update_positions_with_tick("EURUSD", price=99.0, timestamp=ts)
    assert t.positions["p1"].status == "closed"


def test_tp_hit_closes_position_buy() -> None:
    t = PositionTracker()
    p = _mk_position(position_id="p1", symbol="EURUSD", direction=Direction.BUY)
    t.open_position(p)
    ts = datetime.now(timezone.utc)
    t.update_positions_with_tick("EURUSD", price=102.0, timestamp=ts)
    assert t.positions["p1"].status == "closed"


def test_sl_hit_closes_position_sell() -> None:
    t = PositionTracker()
    p = _mk_position(position_id="p1", symbol="EURUSD", direction=Direction.SELL)
    t.open_position(p)
    ts = datetime.now(timezone.utc)
    t.update_positions_with_tick("EURUSD", price=101.0, timestamp=ts)
    assert t.positions["p1"].status == "closed"


def test_tp_hit_closes_position_sell() -> None:
    t = PositionTracker()
    p = _mk_position(position_id="p1", symbol="EURUSD", direction=Direction.SELL)
    t.open_position(p)
    ts = datetime.now(timezone.utc)
    t.update_positions_with_tick("EURUSD", price=98.0, timestamp=ts)
    assert t.positions["p1"].status == "closed"


def test_get_open_positions_filter_works() -> None:
    t = PositionTracker()
    p1 = _mk_position(position_id="p1", symbol="EURUSD", direction=Direction.BUY)
    p2 = _mk_position(position_id="p2", symbol="XAUUSD", direction=Direction.BUY)
    t.open_position(p1)
    t.open_position(p2)
    assert len(t.get_open_positions()) == 2
    assert [p.position_id for p in t.get_open_positions(symbol="EURUSD")] == ["p1"]

