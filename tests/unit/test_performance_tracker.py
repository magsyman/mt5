from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_supervisor.core.enums import Direction
from trading_supervisor.performance.performance_tracker import PerformanceTracker
from trading_supervisor.positions.position_models import Position


def _mk_closed_position(*, position_id: str, pnl: float) -> Position:
    now = datetime.now(timezone.utc)
    return Position(
        position_id=position_id,
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
        pnl=pnl,
    )


def test_no_trades_win_rate_and_avg_pnl_zero() -> None:
    t = PerformanceTracker()
    assert t.get_win_rate() == 0.0
    assert t.get_average_pnl() == 0.0
    assert t.get_total_pnl() == 0.0


def test_record_winning_trade_win_rate_one() -> None:
    t = PerformanceTracker()
    t.record_closed_position(_mk_closed_position(position_id="p1", pnl=10.0))
    assert t.total_trades == 1
    assert t.winning_trades == 1
    assert t.losing_trades == 0
    assert t.get_win_rate() == pytest.approx(1.0)


def test_record_losing_trade_win_rate_correct() -> None:
    t = PerformanceTracker()
    t.record_closed_position(_mk_closed_position(position_id="p1", pnl=10.0))
    t.record_closed_position(_mk_closed_position(position_id="p2", pnl=-5.0))
    assert t.total_trades == 2
    assert t.winning_trades == 1
    assert t.losing_trades == 1
    assert t.get_win_rate() == pytest.approx(0.5)


def test_total_pnl_accumulates_and_average_correct() -> None:
    t = PerformanceTracker()
    t.record_closed_position(_mk_closed_position(position_id="p1", pnl=10.0))
    t.record_closed_position(_mk_closed_position(position_id="p2", pnl=-4.0))
    t.record_closed_position(_mk_closed_position(position_id="p3", pnl=2.0))
    assert t.get_total_pnl() == pytest.approx(8.0)
    assert t.get_average_pnl() == pytest.approx(8.0 / 3.0)


def test_reject_non_closed_positions() -> None:
    now = datetime.now(timezone.utc)
    p = Position(
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
    )
    t = PerformanceTracker()
    with pytest.raises(ValueError, match="must be closed"):
        t.record_closed_position(p)


def test_reject_closed_positions_with_pnl_none() -> None:
    now = datetime.now(timezone.utc)
    p = Position(
        position_id="p1",
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
        pnl=None,
    )
    t = PerformanceTracker()
    with pytest.raises(ValueError, match="pnl must not be None"):
        t.record_closed_position(p)

