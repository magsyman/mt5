from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_supervisor.core.enums import Direction
from trading_supervisor.positions.position_models import Position
from trading_supervisor.positions.position_tracker import PositionTracker
from trading_supervisor.risk.system_state import SystemState


def _mk_position(
    *,
    position_id: str,
    symbol: str,
    direction: Direction,
    entry: float,
    sl: float,
    tp: float,
    size: float,
) -> Position:
    now = datetime.now(timezone.utc)
    return Position(
        position_id=position_id,
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        size=size,
        open_timestamp=now,
        status="open",
        close_price=None,
        close_timestamp=None,
        pnl=None,
    )


def test_position_opened_then_tp_hit_closes() -> None:
    t = PositionTracker()
    p = _mk_position(
        position_id="SIM-1",
        symbol="XAUUSD",
        direction=Direction.BUY,
        entry=100.0,
        sl=99.0,
        tp=102.0,
        size=1.5,
    )
    t.open_position(p)
    assert len(t.get_open_positions("XAUUSD")) == 1

    ts = datetime.now(timezone.utc)
    t.update_positions_with_tick("XAUUSD", price=102.0, timestamp=ts)
    assert len(t.get_open_positions("XAUUSD")) == 0
    closed = t.positions["SIM-1"]
    assert closed.status == "closed"
    assert closed.close_price == 102.0
    assert closed.pnl == pytest.approx((102.0 - 100.0) * 1.5)


def test_position_opened_then_sl_hit_closes() -> None:
    t = PositionTracker()
    p = _mk_position(
        position_id="SIM-2",
        symbol="XAUUSD",
        direction=Direction.BUY,
        entry=100.0,
        sl=99.0,
        tp=102.0,
        size=2.0,
    )
    t.open_position(p)
    ts = datetime.now(timezone.utc)
    t.update_positions_with_tick("XAUUSD", price=99.0, timestamp=ts)
    closed = t.positions["SIM-2"]
    assert closed.status == "closed"
    assert closed.pnl == pytest.approx((99.0 - 100.0) * 2.0)


def test_multiple_positions_tracked_and_open_positions_count_updates() -> None:
    t = PositionTracker()
    p1 = _mk_position(
        position_id="SIM-A",
        symbol="XAUUSD",
        direction=Direction.BUY,
        entry=100.0,
        sl=99.0,
        tp=102.0,
        size=1.0,
    )
    p2 = _mk_position(
        position_id="SIM-B",
        symbol="XAUUSD",
        direction=Direction.SELL,
        entry=100.0,
        sl=103.0,
        tp=98.0,
        size=1.0,
    )
    t.open_position(p1)
    t.open_position(p2)
    assert len(t.get_open_positions("XAUUSD")) == 2

    ts = datetime.now(timezone.utc)
    t.update_positions_with_tick("XAUUSD", price=102.0, timestamp=ts)  # closes BUY at TP
    assert len(t.get_open_positions("XAUUSD")) == 1

    t.update_positions_with_tick("XAUUSD", price=98.0, timestamp=ts)  # closes SELL at TP
    assert len(t.get_open_positions("XAUUSD")) == 0


def test_no_position_opened_when_system_disabled_before_open() -> None:
    tracker = PositionTracker()
    state = SystemState()
    state.disable_trading()

    if state.is_trading_enabled() is True:
        tracker.open_position(
            _mk_position(
                position_id="SIM-NEW",
                symbol="XAUUSD",
                direction=Direction.BUY,
                entry=100.0,
                sl=99.0,
                tp=102.0,
                size=1.0,
            )
        )

    assert len(tracker.get_open_positions("XAUUSD")) == 0

